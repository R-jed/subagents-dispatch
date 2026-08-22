from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load_module(name: str, filename: str):
    scripts = str(SCRIPTS)
    sys.path.insert(0, scripts)
    try:
        spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts)


def unit(graph, unit_id: str) -> dict:
    return graph.make_work_unit(
        unit_id=unit_id,
        intent="inspect",
        goal=f"inspect {unit_id}",
        output="evidence",
        done_when="verified",
    )


def persist(lifecycle, thread_id: str, execution_id: str, tmp_path: Path, host_state: str) -> None:
    basis = lifecycle.fresh_observation_basis(
        thread_id, execution_id=execution_id, temp_root=tmp_path
    )
    lifecycle.persist_host_observation(
        thread_id,
        basis=basis,
        host_state=host_state,
        agent_id=f"agent-{execution_id}",
        failure_origin="tool_failure",
        temp_root=tmp_path,
    )


def test_fresh_attempt_task_name_is_derived_from_unit_and_attempt(tmp_path: Path):
    state = load_module("task_name_state", "dispatch_state_v4.py")
    graph = load_module("task_name_graph", "work_graph_v4.py")
    lifecycle = load_module("task_name_lifecycle", "execution_lifecycle_v4.py")
    thread_id = "task-name-generation"

    state.write_state(state.new_state(thread_id=thread_id), temp_root=tmp_path)
    graph.install_work_graph(thread_id, units=[unit(graph, "U1")], temp_root=tmp_path)

    with pytest.raises(lifecycle.ExecutionLifecycleError, match="WorkUnit attempt generation"):
        lifecycle.allocate_execution(
            thread_id,
            unit_id="U1",
            execution_id="exec-1",
            native_task_name="arbitrary_name",
            profile_id="reader",
            granted_authority="none",
            temp_root=tmp_path,
        )

    created = lifecycle.allocate_execution(
        thread_id,
        unit_id="U1",
        execution_id="exec-1",
        native_task_name="sd_u1_a1",
        profile_id="reader",
        granted_authority="none",
        temp_root=tmp_path,
    )
    assert created["execution"]["attempt_no"] == 1
    assert created["execution"]["native_task_name"] == "sd_u1_a1"


def test_compaction_cannot_reuse_older_task_name(tmp_path: Path):
    state = load_module("task_compaction_state", "dispatch_state_v4.py")
    graph = load_module("task_compaction_graph", "work_graph_v4.py")
    lifecycle = load_module("task_compaction_lifecycle", "execution_lifecycle_v4.py")
    thread_id = "task-name-compaction"

    state.write_state(state.new_state(thread_id=thread_id), temp_root=tmp_path)
    graph.install_work_graph(thread_id, units=[unit(graph, "U1")], temp_root=tmp_path)

    for attempt in range(1, 4):
        lifecycle.allocate_execution(
            thread_id,
            unit_id="U1",
            execution_id=f"exec-{attempt}",
            native_task_name=f"sd_u1_a{attempt}",
            profile_id="reader",
            granted_authority="none",
            execution_basis_ref=f"basis:{attempt}",
            temp_root=tmp_path,
        )
        persist(lifecycle, thread_id, f"exec-{attempt}", tmp_path, "errored")

    current = state.load_state(thread_id, temp_root=tmp_path)
    assert current is not None
    assert any(
        event.get("kind") == "execution_history" and event.get("max_attempt_no") >= 1
        for event in current["accounting_refs"]
    )

    with pytest.raises(lifecycle.ExecutionLifecycleError, match="sd_u1_a4"):
        lifecycle.allocate_execution(
            thread_id,
            unit_id="U1",
            execution_id="exec-4",
            native_task_name="sd_u1_a1",
            profile_id="reader",
            granted_authority="none",
            execution_basis_ref="basis:4",
            temp_root=tmp_path,
        )

    created = lifecycle.allocate_execution(
        thread_id,
        unit_id="U1",
        execution_id="exec-4",
        native_task_name="sd_u1_a4",
        profile_id="reader",
        granted_authority="none",
        execution_basis_ref="basis:4",
        temp_root=tmp_path,
    )
    assert created["execution"]["attempt_no"] == 4


def test_casefold_colliding_unit_ids_cannot_share_host_task_namespace(tmp_path: Path):
    state = load_module("task_collision_state", "dispatch_state_v4.py")
    graph = load_module("task_collision_graph", "work_graph_v4.py")
    lifecycle = load_module("task_collision_lifecycle", "execution_lifecycle_v4.py")
    thread_id = "task-name-collision"

    state.write_state(state.new_state(thread_id=thread_id), temp_root=tmp_path)
    graph.install_work_graph(
        thread_id,
        units=[unit(graph, "U1"), unit(graph, "u1")],
        temp_root=tmp_path,
    )

    with pytest.raises(lifecycle.ExecutionLifecycleError, match="case-folded Host task naming"):
        lifecycle.allocate_execution(
            thread_id,
            unit_id="U1",
            execution_id="exec-u1",
            native_task_name="sd_u1_a1",
            profile_id="reader",
            granted_authority="none",
            temp_root=tmp_path,
        )


def test_state_boundary_rejects_execution_task_name_generation_drift():
    state = load_module("task_state_binding", "dispatch_state_v4.py")
    graph = load_module("task_state_graph", "work_graph_v4.py")
    payload = state.new_state(thread_id="task-name-state-binding")
    payload["work_units"] = [unit(graph, "U1")]
    payload["work_units"][0]["state"] = "EXECUTING"
    payload["executions"] = [
        {
            "execution_id": "exec-1",
            "unit_id": "U1",
            "team_plan_revision": None,
            "attempt_no": 2,
            "profile_id": "reader",
            "agent_id": None,
            "native_task_name": "sd_u1_a1",
            "model": "gpt-5.6-luna",
            "effort": "max",
            "granted_authority": "none",
            "granted_write_scope": [],
            "workspace_id": "canonical",
            "lifecycle": "SPAWN_PENDING",
            "control_epoch": 0,
            "followup_count": 0,
            "failure_origin": "none",
            "blocker": "none",
            "quarantine_reason": None,
            "execution_basis_ref": "basis:2",
        }
    ]

    with pytest.raises(state.StatePayloadError, match="WorkUnit and attempt generation"):
        state.validate_state_payload(payload)
