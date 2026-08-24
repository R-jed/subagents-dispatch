from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
MODULE = SCRIPTS / "dispatch_state_v4.py"


def load_state_module():
    scripts = str(SCRIPTS)
    sys.path.insert(0, scripts)
    try:
        spec = importlib.util.spec_from_file_location("state_lifecycle_boundary_v4", MODULE)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts)


def work_unit(*, state: str = "CANCELLED", authority: str = "none") -> dict:
    scope = ["src/owned.py"] if authority != "none" else []
    return {
        "unit_id": "U1",
        "intent": "implement" if authority != "none" else "inspect",
        "goal": "bounded responsibility",
        "output": "verified result",
        "depends_on": [],
        "state": state,
        "ownership": {"write": scope, "forbidden": []},
        "authority_ceiling": authority,
        "write_scope_ceiling": scope,
        "done_when": "Main verifies the result",
        "accepted_result_ref": None,
        "accepted_execution_id": None,
        "accepted_control_epoch": None,
    }


def execution(*, lifecycle: str, authority: str = "none") -> dict:
    profile_id = "worker" if authority != "none" else "reader"
    model = "gpt-5.6-luna"
    return {
        "execution_id": "exec-1",
        "unit_id": "U1",
        "attempt_no": 1,
        "profile_id": profile_id,
        "agent_id": "agent-1",
        "native_task_name": "sd_u1_a1",
        "model": model,
        "effort": "max",
        "granted_authority": authority,
        "granted_write_scope": ["src/owned.py"] if authority != "none" else [],
        "workspace_id": "canonical",
        "lifecycle": lifecycle,
        "control_epoch": 0,
        "followup_count": 0,
        "failure_origin": "runtime_ambiguous" if lifecycle == "UNKNOWN" else (
            "tool_failure" if lifecycle == "FAILED" else "none"
        ),
        "blocker": "investigation" if lifecycle == "UNKNOWN" else "none",
        "quarantine_reason": "host_identity_ambiguous" if lifecycle == "UNKNOWN" else None,
    }


def persist_with_records(
    module,
    tmp_path: Path,
    *,
    unit_state: str,
    lifecycle: str,
    writer: bool = False,
    writer_state: str = "HELD",
):
    payload = module.new_state(thread_id="thread-1")
    payload["work_units"] = [
        work_unit(state=unit_state, authority="bounded-source-write" if writer else "none")
    ]
    payload["executions"] = [
        execution(lifecycle=lifecycle, authority="bounded-source-write" if writer else "none")
    ]
    if writer:
        payload["writer_lease"] = {
            "lease_id": "lease-1",
            "lease_epoch": 1,
            "workspace_id": "canonical",
            "unit_id": "U1",
            "owner_kind": "execution",
            "owner_id": "exec-1",
            "state": writer_state,
        }
    module.validate_state_payload(payload)
    module.create_state_if_absent(payload, temp_root=tmp_path)
    return payload


def test_create_state_if_absent_rejects_existing_active_state(tmp_path: Path):
    module = load_state_module()
    persist_with_records(module, tmp_path, unit_state="EXECUTING", lifecycle="RUNNING")

    with pytest.raises(module.StatePayloadError, match="already exists"):
        module.create_state_if_absent(
            module.new_state(thread_id="thread-1"),
            temp_root=tmp_path,
        )

    current = module.load_state("thread-1", temp_root=tmp_path)
    assert current is not None
    assert current["executions"][0]["lifecycle"] == "RUNNING"


def test_create_state_if_absent_preserves_existing_held_writer(tmp_path: Path):
    module = load_state_module()
    persist_with_records(
        module,
        tmp_path,
        unit_state="EXECUTING",
        lifecycle="RUNNING",
        writer=True,
    )

    with pytest.raises(module.StatePayloadError, match="already exists"):
        module.create_state_if_absent(
            module.new_state(thread_id="thread-1"),
            temp_root=tmp_path,
        )

    current = module.load_state("thread-1", temp_root=tmp_path)
    assert current is not None
    assert current["writer_lease"]["state"] == "HELD"
    assert current["writer_lease"]["owner_id"] == "exec-1"


def test_write_state_cannot_overwrite_existing_state(tmp_path: Path):
    module = load_state_module()
    first = module.new_state(thread_id="thread-1")
    module.write_state(first, temp_root=tmp_path)

    replacement = module.new_state(thread_id="thread-1", locale="zh")
    with pytest.raises(module.StatePayloadError, match="already exists"):
        module.write_state(replacement, temp_root=tmp_path)

    assert module.load_state("thread-1", temp_root=tmp_path) == first
    assert "write_state" not in module.__all__


def test_terminal_cleanup_rejects_unresolved_work(tmp_path: Path):
    module = load_state_module()
    persist_with_records(module, tmp_path, unit_state="EXECUTING", lifecycle="FAILED")

    with pytest.raises(module.StatePayloadError, match="unresolved WorkUnit"):
        module.remove_terminal_state("thread-1", temp_root=tmp_path)


def test_terminal_cleanup_rejects_unknown_execution(tmp_path: Path):
    module = load_state_module()
    persist_with_records(module, tmp_path, unit_state="CANCELLED", lifecycle="UNKNOWN")

    with pytest.raises(module.StatePayloadError, match="unsettled or ambiguous execution"):
        module.remove_terminal_state("thread-1", temp_root=tmp_path)


def test_terminal_cleanup_rejects_blocking_writer(tmp_path: Path):
    module = load_state_module()
    persist_with_records(
        module,
        tmp_path,
        unit_state="CANCELLED",
        lifecycle="FAILED",
        writer=True,
    )

    with pytest.raises(module.StatePayloadError, match="blocking WriterLease"):
        module.remove_terminal_state("thread-1", temp_root=tmp_path)


def test_terminal_cleanup_rejects_unknown_writer(tmp_path: Path):
    module = load_state_module()
    persist_with_records(
        module,
        tmp_path,
        unit_state="CANCELLED",
        lifecycle="FAILED",
        writer=True,
        writer_state="UNKNOWN",
    )

    with pytest.raises(module.StatePayloadError, match="blocking WriterLease"):
        module.remove_terminal_state("thread-1", temp_root=tmp_path)

    current = module.load_state("thread-1", temp_root=tmp_path)
    assert current is not None
    assert current["writer_lease"]["state"] == "UNKNOWN"


def test_terminal_cleanup_requires_current_revision(tmp_path: Path):
    module = load_state_module()
    persist_with_records(module, tmp_path, unit_state="CANCELLED", lifecycle="FAILED")

    with pytest.raises(module.StatePayloadError, match="compare-and-swap"):
        module.remove_terminal_state(
            "thread-1",
            expected_state_revision=99,
            temp_root=tmp_path,
        )
    assert module.load_state("thread-1", temp_root=tmp_path) is not None


def test_terminal_cleanup_succeeds_after_settlement(tmp_path: Path):
    module = load_state_module()
    persist_with_records(module, tmp_path, unit_state="CANCELLED", lifecycle="FAILED")

    assert module.remove_terminal_state("thread-1", temp_root=tmp_path) is True
    assert module.load_state("thread-1", temp_root=tmp_path) is None
    assert module.remove_terminal_state("thread-1", temp_root=tmp_path) is False


def test_concurrent_state_creation_has_one_winner(tmp_path: Path):
    module = load_state_module()

    def create(locale: str) -> str:
        try:
            module.create_state_if_absent(
                module.new_state(thread_id="thread-1", locale=locale),
                temp_root=tmp_path,
            )
            return "created"
        except module.StatePayloadError as exc:
            assert "already exists" in str(exc)
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(create, ["en", "zh"]))

    assert sorted(results) == ["created", "rejected"]
    assert module.load_state("thread-1", temp_root=tmp_path) is not None
