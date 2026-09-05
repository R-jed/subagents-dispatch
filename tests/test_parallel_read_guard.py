from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load_module(name: str, filename: str):
    sys.path.insert(0, str(SCRIPTS))
    try:
        spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPTS))


def unit(graph, unit_id: str):
    return graph.make_work_unit(
        unit_id=unit_id,
        intent="inspect",
        goal=f"inspect {unit_id}",
        output="evidence",
        done_when="Main verifies evidence",
    )


def init_repo(path: Path) -> None:
    path.mkdir()
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    (path / "a.txt").write_text("baseline\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "a.txt"], check=True)


def setup_read_batch(tmp_path: Path):
    state = load_module("guard_state", "dispatch_state_v4.py")
    graph = load_module("guard_graph", "work_graph_v4.py")
    lifecycle = load_module("guard_lifecycle", "execution_lifecycle_v4.py")
    thread = "guard-thread"
    state.write_state(state.new_state(thread_id=thread), temp_root=tmp_path)
    graph.install_work_graph(thread, units=[unit(graph, "U1"), unit(graph, "U2")], temp_root=tmp_path)
    for index in (1, 2):
        lifecycle.allocate_execution(
            thread,
            unit_id=f"U{index}",
            execution_id=f"exec-{index}",
            native_task_name=f"sd_u{index}_a1",
            role_id="programmer",
            reasoning_effort="max",
            granted_authority="none",
            temp_root=tmp_path,
        )
    return state, thread


def test_parallel_semantic_read_guard_accepts_unchanged_workspace(tmp_path: Path):
    _, thread = setup_read_batch(tmp_path)
    guard = load_module("parallel_guard_ok", "parallel_read_guard.py")
    repo = tmp_path / "repo"
    init_repo(repo)

    token = guard.begin_parallel_read_batch(
        thread,
        execution_ids=["exec-1", "exec-2"],
        repo=repo,
        temp_root=tmp_path,
    )
    result = guard.verify_parallel_read_batch(token, repo=repo, temp_root=tmp_path)
    assert result["status"] == "verified"
    assert result["artifact_unchanged"] is True


def test_parallel_semantic_read_guard_quarantines_whole_batch_on_artifact_drift(tmp_path: Path):
    state, thread = setup_read_batch(tmp_path)
    guard = load_module("parallel_guard_drift", "parallel_read_guard.py")
    repo = tmp_path / "repo"
    init_repo(repo)

    token = guard.begin_parallel_read_batch(
        thread,
        execution_ids=["exec-1", "exec-2"],
        repo=repo,
        temp_root=tmp_path,
    )
    (repo / "a.txt").write_text("drift\n", encoding="utf-8")
    result = guard.verify_parallel_read_batch(token, repo=repo, temp_root=tmp_path)
    assert result["status"] == "quarantined"
    assert result["artifact_unchanged"] is False
    assert result["pause_managed_mutation"] is True

    current = state.load_state(thread, temp_root=tmp_path)
    assert current is not None
    executions = {item["execution_id"]: item for item in current["executions"]}
    for execution_id in ("exec-1", "exec-2"):
        assert executions[execution_id]["lifecycle"] == "UNKNOWN"
        assert executions[execution_id]["quarantine_reason"] == "workspace_baseline_drift"


def test_parallel_semantic_read_guard_rejects_active_writer(tmp_path: Path):
    state, thread = setup_read_batch(tmp_path)
    guard = load_module("parallel_guard_writer", "parallel_read_guard.py")
    repo = tmp_path / "repo"
    init_repo(repo)

    def install_writer(current: dict) -> None:
        current["writer_lease"] = {
            "lease_id": "lease-main",
            "lease_epoch": 1,
            "workspace_id": "canonical",
            "unit_id": "U1",
            "owner_kind": "main",
            "owner_id": thread,
            "state": "HELD",
        }

    state.mutate_state(thread, install_writer, temp_root=tmp_path)
    with pytest.raises(guard.ParallelReadGuardError, match="active canonical WriterLease"):
        guard.begin_parallel_read_batch(
            thread,
            execution_ids=["exec-1", "exec-2"],
            repo=repo,
            temp_root=tmp_path,
        )
