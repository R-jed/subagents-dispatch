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


def capability_evidence(*, surface: str = "multi_agent_v2") -> dict:
    return {
        "surface": surface,
        "tools": ["spawn_agent", "followup_task", "interrupt_agent", "list_agents", "wait_agent"],
        "fork_turns_none": True,
        "managed_child_containment": "verified",
        "max_concurrent_threads_per_session": 4,
    }


def work_unit() -> dict:
    return {
        "unit_id": "U1",
        "intent": "inspect",
        "goal": "inspect exact scope",
        "output": "facts",
        "depends_on": [],
        "state": "EXECUTING",
        "ownership": {"write": [], "forbidden": []},
        "authority_ceiling": "none",
        "write_scope_ceiling": [],
        "done_when": "Main verifies facts",
        "accepted_result_ref": None,
        "accepted_execution_id": None,
        "accepted_control_epoch": None,
    }


def execution() -> dict:
    return {
        "execution_id": "exec-1",
        "unit_id": "U1",
        "attempt_no": 1,
        "profile_id": "reader",
        "agent_id": "agent-id-1",
        "native_task_name": "sd_u1_a1",
        "model": "gpt-5.6-luna",
        "effort": "max",
        "granted_authority": "none",
        "granted_write_scope": [],
        "workspace_id": "canonical",
        "lifecycle": "RUNNING",
        "control_epoch": 0,
        "followup_count": 0,
        "failure_origin": "none",
        "blocker": "none",
        "quarantine_reason": None,
    }


def install(state, tmp_path: Path) -> None:
    payload = state.new_state(thread_id="thread-host")
    payload["work_units"] = [work_unit()]
    payload["executions"] = [execution()]
    state.write_state(payload, temp_root=tmp_path)


def test_host_surface_must_be_exact_multi_agent_v2_and_hook_fields_are_rejected():
    host = load_module("native_host_surface", "host_capabilities.py")
    with pytest.raises(host.HostCapabilityError, match="surface"):
        host.normalize_host_capabilities(capability_evidence(surface="multi_agent_v2-ish"))

    payload = capability_evidence()
    payload["hooks"] = {"PreToolUse": []}
    with pytest.raises(host.HostCapabilityError, match="unsupported fields"):
        host.normalize_host_capabilities(payload)


def test_lifecycle_facade_exposes_direct_host_observation_reconciliation():
    lifecycle = load_module("native_host_lifecycle_public", "execution_lifecycle_v4.py")

    assert hasattr(lifecycle, "persist_host_observation")
    assert not (SCRIPTS / "orchestration_guard.py").exists()
    assert not (SCRIPTS / "dispatch_control_v4.py").exists()


def test_current_generation_observation_updates_lifecycle_and_persists_compact_proof(tmp_path: Path):
    state = load_module("native_host_state_ingest", "dispatch_state_v4.py")
    writer = load_module("native_host_writer_ingest", "writer_lease_v4.py")
    install(state, tmp_path)
    current = state.load_state("thread-host", temp_root=tmp_path)
    assert current is not None
    basis = state.observation_basis(current, execution_id="exec-1")
    assert basis == {
        "execution_id": "exec-1",
        "unit_id": "U1",
        "attempt_no": 1,
        "control_epoch": 0,
        "lease_epoch": None,
    }

    result = writer.persist_host_observation(
        "thread-host",
        basis=basis,
        host_state="completed",
        agent_id="agent-id-1",
        temp_root=tmp_path,
    )

    assert result["reconcile_status"] == "applied"
    assert result["lifecycle"] == "COMPLETED"
    current = result["state"]
    assert current["executions"][0]["lifecycle"] == "COMPLETED"
    assert current["work_units"][0]["state"] == "RESULT_READY"
    observations = [event for event in current["accounting_refs"] if event.get("kind") == "host_observation"]
    assert observations == [
        {
            "ref": "host-observation:exec-1:0:none:COMPLETED",
            "kind": "host_observation",
            "execution_id": "exec-1",
            "control_epoch": 0,
            "lease_epoch": None,
            "lifecycle": "COMPLETED",
        }
    ]


def test_stale_observation_basis_cannot_mutate_current_generation(tmp_path: Path):
    state = load_module("native_host_state_stale", "dispatch_state_v4.py")
    writer = load_module("native_host_writer_stale", "writer_lease_v4.py")
    install(state, tmp_path)
    current = state.load_state("thread-host", temp_root=tmp_path)
    assert current is not None
    stale_basis = state.observation_basis(current, execution_id="exec-1")

    def advance(payload: dict) -> None:
        payload["executions"][0]["control_epoch"] += 1

    state.mutate_state("thread-host", advance, temp_root=tmp_path)
    result = writer.persist_host_observation(
        "thread-host",
        basis=stale_basis,
        host_state="completed",
        agent_id="agent-id-1",
        temp_root=tmp_path,
    )

    assert result["reconcile_status"] == "stale"
    assert result["state"]["executions"][0]["lifecycle"] == "RUNNING"
    assert result["state"]["executions"][0]["control_epoch"] == 1


def test_duplicate_current_generation_observation_is_idempotent(tmp_path: Path):
    state = load_module("native_host_state_dup", "dispatch_state_v4.py")
    writer = load_module("native_host_writer_dup", "writer_lease_v4.py")
    install(state, tmp_path)
    current = state.load_state("thread-host", temp_root=tmp_path)
    assert current is not None
    basis = state.observation_basis(current, execution_id="exec-1")

    first = writer.persist_host_observation(
        "thread-host", basis=basis, host_state="running", agent_id="agent-id-1", temp_root=tmp_path
    )
    second = writer.persist_host_observation(
        "thread-host", basis=basis, host_state="running", agent_id="agent-id-1", temp_root=tmp_path
    )

    assert first["idempotent"] is False
    assert second["idempotent"] is True
    observations = [
        event for event in second["state"]["accounting_refs"] if event.get("kind") == "host_observation"
    ]
    assert len(observations) == 1
