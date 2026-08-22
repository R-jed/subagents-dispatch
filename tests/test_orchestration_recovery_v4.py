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


def work_unit(*, writable: bool = False) -> dict:
    scope = ["src/u1.py"] if writable else []
    return {
        "unit_id": "U1",
        "intent": "implement" if writable else "inspect",
        "goal": "complete U1",
        "output": "verified result",
        "depends_on": [],
        "state": "READY",
        "ownership": {"write": scope, "forbidden": []},
        "authority_ceiling": "bounded-source-write" if writable else "none",
        "write_scope_ceiling": scope,
        "done_when": "Main verifies the result",
        "accepted_result_ref": None,
        "accepted_execution_id": None,
        "accepted_control_epoch": None,
    }


def native_host_snapshot(host, capacity: int | None = 4) -> dict:
    return host.normalize_host_capabilities(
        {
            "surface": "multi_agent_v2",
            "tools": ["spawn_agent", "followup_task", "interrupt_agent", "list_agents", "wait_agent"],
            "fork_turns_none": True,
            "max_concurrent_threads_per_session": capacity,
        }
    )


def install_unit(state, tmp_path: Path, *, writable: bool = False) -> None:
    payload = state.new_state(thread_id="thread-recovery")
    payload["work_units"] = [work_unit(writable=writable)]
    state.write_state(payload, temp_root=tmp_path)


def test_current_host_running_observation_promotes_reserved_writer_without_ack_protocol(tmp_path: Path):
    state = load_module("recovery_state_running", "dispatch_state_v4.py")
    lifecycle = load_module("recovery_lifecycle_running", "execution_lifecycle_v4.py")
    install_unit(state, tmp_path, writable=True)

    lifecycle.allocate_execution(
        "thread-recovery",
        unit_id="U1",
        execution_id="exec-1",
        native_task_name="sd_u1_a1",
        profile_id="worker",
        granted_authority="bounded-source-write",
        granted_write_scope=["src/u1.py"],
        writer_lease_id="lease-1",
        temp_root=tmp_path,
    )
    basis = lifecycle.fresh_observation_basis(
        "thread-recovery", execution_id="exec-1", temp_root=tmp_path
    )
    result = lifecycle.persist_host_observation(
        "thread-recovery",
        basis=basis,
        host_state="running",
        agent_id="agent-1",
        temp_root=tmp_path,
    )

    assert result["lifecycle"] == "RUNNING"
    current = result["state"]
    assert current["executions"][0]["agent_id"] == "agent-1"
    assert current["writer_lease"]["state"] == "HELD"
    assert "pending_controls" not in current


def test_ambiguous_native_spawn_quarantines_execution_and_writer(tmp_path: Path):
    state = load_module("recovery_state_unknown", "dispatch_state_v4.py")
    lifecycle = load_module("recovery_lifecycle_unknown", "execution_lifecycle_v4.py")
    install_unit(state, tmp_path, writable=True)

    lifecycle.allocate_execution(
        "thread-recovery",
        unit_id="U1",
        execution_id="exec-1",
        native_task_name="sd_u1_a1",
        profile_id="worker",
        granted_authority="bounded-source-write",
        granted_write_scope=["src/u1.py"],
        writer_lease_id="lease-1",
        temp_root=tmp_path,
    )
    lifecycle.mark_execution_unknown(
        "thread-recovery", execution_id="exec-1", temp_root=tmp_path
    )
    current = state.load_state("thread-recovery", temp_root=tmp_path)
    assert current is not None
    assert current["executions"][0]["lifecycle"] == "UNKNOWN"
    assert current["writer_lease"]["state"] == "UNKNOWN"

    with pytest.raises(lifecycle.ExecutionLifecycleError):
        lifecycle.allocate_execution(
            "thread-recovery",
            unit_id="U1",
            execution_id="exec-2",
            native_task_name="sd_u1_a2",
            profile_id="worker",
            granted_authority="bounded-source-write",
            granted_write_scope=["src/u1.py"],
            writer_lease_id="lease-2",
            temp_root=tmp_path,
        )

    blocked = state.load_state("thread-recovery", temp_root=tmp_path)
    assert blocked is not None
    assert [item["execution_id"] for item in blocked["executions"]] == ["exec-1"]
    assert blocked["executions"][0]["lifecycle"] == "UNKNOWN"
    assert blocked["writer_lease"]["owner_id"] == "exec-1"
    assert blocked["writer_lease"]["state"] == "UNKNOWN"


def test_interrupt_result_does_not_release_writer_until_current_host_settlement(tmp_path: Path):
    state = load_module("recovery_state_interrupt", "dispatch_state_v4.py")
    lifecycle = load_module("recovery_lifecycle_interrupt", "execution_lifecycle_v4.py")
    install_unit(state, tmp_path, writable=True)

    lifecycle.allocate_execution(
        "thread-recovery",
        unit_id="U1",
        execution_id="exec-1",
        native_task_name="sd_u1_a1",
        profile_id="worker",
        granted_authority="bounded-source-write",
        granted_write_scope=["src/u1.py"],
        writer_lease_id="lease-1",
        temp_root=tmp_path,
    )
    running_basis = lifecycle.fresh_observation_basis(
        "thread-recovery", execution_id="exec-1", temp_root=tmp_path
    )
    lifecycle.persist_host_observation(
        "thread-recovery",
        basis=running_basis,
        host_state="running",
        agent_id="agent-1",
        temp_root=tmp_path,
    )
    prepared = lifecycle.prepare_interrupt(
        "thread-recovery",
        execution_id="exec-1",
        tool_input={"target": "sd_u1_a1"},
        temp_root=tmp_path,
    )
    current = state.load_state("thread-recovery", temp_root=tmp_path)
    assert current is not None
    assert current["writer_lease"]["state"] == "REVOKING"

    with pytest.raises(Exception, match="settled|observation"):
        lifecycle.takeover_to_main(
            "thread-recovery",
            execution_id="exec-1",
            old_lease_id="lease-1",
            old_lease_epoch=current["writer_lease"]["lease_epoch"],
            main_lease_id="lease-main",
            temp_root=tmp_path,
        )

    settled = lifecycle.persist_host_observation(
        "thread-recovery",
        basis=prepared["observation_basis"],
        host_state="interrupted",
        agent_id="agent-1",
        temp_root=tmp_path,
    )
    lease_epoch = settled["state"]["writer_lease"]["lease_epoch"]
    takeover = lifecycle.takeover_to_main(
        "thread-recovery",
        execution_id="exec-1",
        old_lease_id="lease-1",
        old_lease_epoch=lease_epoch,
        main_lease_id="lease-main",
        temp_root=tmp_path,
    )
    assert takeover["owner_kind"] == "main"
    assert takeover["state"] == "HELD"


def test_scheduler_uses_native_snapshot_only_and_has_no_persisted_capacity_token_requirement():
    state = load_module("recovery_state_scheduler", "dispatch_state_v4.py")
    host = load_module("recovery_host_scheduler", "host_capabilities.py")
    scheduler = load_module("recovery_scheduler_native", "scheduler_v4.py")

    payload = state.new_state(thread_id="thread-recovery")
    payload["team_plan_revision"] = 1
    payload["work_units"] = [work_unit(), {**work_unit(), "unit_id": "U2"}]
    state.validate_state_payload(payload)

    decision = scheduler.scheduler_decision(
        payload,
        capability_snapshot=native_host_snapshot(host, capacity=2),
        wakeup_reason="USER_INPUT",
    )
    assert decision["host_session_capacity"] == 2
    assert decision["launch_budget"] == 1
    assert payload["accounting_refs"] == []
