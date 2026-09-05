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


def context() -> dict:
    return {
        "interfaces": [],
        "invariants": [],
        "decision_boundary": "Escalate material decisions to Main.",
        "accepted_evidence_refs": [],
        "do_not_redo": [],
        "stop_boundary": "Stop and report blockers to Main.",
    }


def install_read_execution(state, lifecycle, tmp_path: Path) -> None:
    payload = state.new_state(thread_id="root-thread")
    payload["work_units"] = [
        {
            "unit_id": "U1",
            "intent": "inspect",
            "goal": "bounded read",
            "output": "facts",
            "depends_on": [],
            "state": "READY",
            "ownership": {"write": [], "forbidden": []},
            "authority_ceiling": "none",
            "write_scope_ceiling": [],
            "done_when": "Main verifies facts",
            "responsibility_context": context(),
            "accepted_result_ref": None,
            "accepted_execution_id": None,
            "accepted_control_epoch": None,
        }
    ]
    state.write_state(payload, temp_root=tmp_path)
    lifecycle.allocate_execution(
        "root-thread",
        unit_id="U1",
        execution_id="exec-1",
        native_task_name="sd_u1_a1",
        role_id="programmer", reasoning_effort="max",
        granted_authority="none",
        temp_root=tmp_path,
    )


def test_managed_spawn_input_must_match_exact_profile_and_fresh_context_contract(tmp_path: Path):
    state = load_module("runtime_safety_state_spawn", "dispatch_state_v4.py")
    lifecycle = load_module("runtime_safety_lifecycle_spawn", "execution_lifecycle_v4.py")
    install_read_execution(state, lifecycle, tmp_path)

    expected = lifecycle.build_managed_spawn_tool_input(
        "root-thread", execution_id="exec-1", temp_root=tmp_path
    )
    assert expected["fork_turns"] == "none"
    tampered = dict(expected)
    tampered["fork_turns"] = "all"

    with pytest.raises(lifecycle.ExecutionLifecycleError, match="does not match"):
        lifecycle.prepare_spawn(
            "root-thread",
            execution_id="exec-1",
            tool_input=tampered,
            temp_root=tmp_path,
        )


def test_ambiguous_native_result_fails_closed_without_acceptance(tmp_path: Path):
    state = load_module("runtime_safety_state_unknown", "dispatch_state_v4.py")
    lifecycle = load_module("runtime_safety_lifecycle_unknown", "execution_lifecycle_v4.py")
    install_read_execution(state, lifecycle, tmp_path)

    lifecycle.mark_execution_unknown(
        "root-thread",
        execution_id="exec-1",
        reason="spawn_result_lost",
        temp_root=tmp_path,
    )
    current = state.load_state("root-thread", temp_root=tmp_path)
    assert current is not None
    execution = current["executions"][0]
    unit = current["work_units"][0]
    assert execution["lifecycle"] == "UNKNOWN"
    assert execution["quarantine_reason"] == "spawn_result_lost"
    assert unit["state"] == "EXECUTING"
    assert unit["accepted_result_ref"] is None


def test_stale_host_observation_cannot_rewrite_newer_control_generation(tmp_path: Path):
    state = load_module("runtime_safety_state_stale", "dispatch_state_v4.py")
    lifecycle = load_module("runtime_safety_lifecycle_stale", "execution_lifecycle_v4.py")
    install_read_execution(state, lifecycle, tmp_path)
    initial = lifecycle.fresh_observation_basis(
        "root-thread", execution_id="exec-1", temp_root=tmp_path
    )

    lifecycle.persist_host_observation(
        "root-thread",
        basis=initial,
        host_state="running",
        agent_id="agent-1",
        temp_root=tmp_path,
    )
    prepared = lifecycle.prepare_interrupt(
        "root-thread",
        execution_id="exec-1",
        tool_input={"target": "/root/sd_u1_a1"},
        temp_root=tmp_path,
    )
    stale = lifecycle.persist_host_observation(
        "root-thread",
        basis=initial,
        host_state="completed",
        agent_id="agent-1",
        temp_root=tmp_path,
    )

    assert stale["reconcile_status"] == "stale"
    current = stale["state"]
    assert current["executions"][0]["control_epoch"] == prepared["control_epoch"]
    assert current["executions"][0]["lifecycle"] == "RUNNING"


def test_writer_settlement_requires_exact_current_generation_proof(tmp_path: Path):
    state = load_module("runtime_safety_state_writer", "dispatch_state_v4.py")
    lifecycle = load_module("runtime_safety_lifecycle_writer", "execution_lifecycle_v4.py")

    payload = state.new_state(thread_id="root-thread")
    payload["work_units"] = [
        {
            "unit_id": "U1",
            "intent": "implement",
            "goal": "bounded write",
            "output": "patch",
            "depends_on": [],
            "state": "READY",
            "ownership": {"write": ["src/a.py"], "forbidden": []},
            "authority_ceiling": "bounded-source-write",
            "write_scope_ceiling": ["src/a.py"],
            "done_when": "tests pass",
            "responsibility_context": context(),
            "accepted_result_ref": None,
            "accepted_execution_id": None,
            "accepted_control_epoch": None,
        }
    ]
    state.write_state(payload, temp_root=tmp_path)
    lifecycle.allocate_execution(
        "root-thread",
        unit_id="U1",
        execution_id="exec-1",
        native_task_name="sd_u1_a1",
        role_id="programmer", reasoning_effort="max",
        granted_authority="bounded-source-write",
        granted_write_scope=["src/a.py"],
        writer_lease_id="lease-1",
        temp_root=tmp_path,
    )
    basis = lifecycle.fresh_observation_basis(
        "root-thread", execution_id="exec-1", temp_root=tmp_path
    )
    completed = lifecycle.persist_host_observation(
        "root-thread",
        basis=basis,
        host_state="completed",
        agent_id="agent-1",
        temp_root=tmp_path,
    )
    lease = completed["state"]["writer_lease"]

    takeover = lifecycle.takeover_to_main(
        "root-thread",
        execution_id="exec-1",
        old_lease_id=lease["lease_id"],
        old_lease_epoch=lease["lease_epoch"],
        main_lease_id="lease-main",
        temp_root=tmp_path,
    )
    assert takeover["owner_kind"] == "main"
    assert takeover["lease_epoch"] == lease["lease_epoch"] + 1
