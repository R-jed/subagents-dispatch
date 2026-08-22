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


def capability_snapshot(*, capacity: int | None = 4, ready: bool = True) -> dict:
    host = load_module(f"constraint_host_{capacity}_{ready}", "host_capabilities.py")
    tools = ["spawn_agent", "followup_task", "interrupt_agent", "list_agents", "wait_agent"]
    if not ready:
        tools.remove("interrupt_agent")
    return host.normalize_host_capabilities(
        {
            "surface": "multi_agent_v2",
            "tools": tools,
            "fork_turns_none": ready,
            "max_concurrent_threads_per_session": capacity,
        }
    )


def test_dependencies_unlock_only_after_work_unit_acceptance(tmp_path: Path):
    state = load_module("constraint_state_accept", "dispatch_state_v4.py")
    graph = load_module("constraint_graph_accept", "work_graph_v4.py")
    lifecycle = load_module("constraint_lifecycle_accept", "execution_lifecycle_v4.py")

    state.write_state(state.new_state(thread_id="thread-accept"), temp_root=tmp_path)
    u1 = graph.make_work_unit(
        unit_id="U1", intent="inspect", goal="produce evidence", output="evidence", done_when="verified"
    )
    u2 = graph.make_work_unit(
        unit_id="U2", intent="verify", goal="consume accepted evidence", output="conclusion", depends_on=["U1"], done_when="accepted"
    )
    graph.install_work_graph("thread-accept", team_plan_revision=1, units=[u1, u2], temp_root=tmp_path)
    lifecycle.allocate_execution(
        "thread-accept", unit_id="U1", execution_id="exec-1", native_task_name="sd_u1_a1", profile_id="reader", granted_authority="none", temp_root=tmp_path
    )
    basis = lifecycle.fresh_observation_basis("thread-accept", execution_id="exec-1", temp_root=tmp_path)
    lifecycle.persist_host_observation(
        "thread-accept", basis=basis, host_state="completed", agent_id="agent-1", temp_root=tmp_path
    )

    before = state.load_state("thread-accept", temp_root=tmp_path)
    assert before is not None
    assert graph.refresh_dependency_states(before)["work_units"][1]["state"] == "BLOCKED"

    accepted = graph.accept_work_unit(
        "thread-accept", unit_id="U1", execution_id="exec-1", result_ref="result:verified", control_epoch=0, temp_root=tmp_path
    )
    assert accepted["work_units"][1]["state"] == "READY"


def test_constraint_snapshot_exposes_capacity_without_selecting_work():
    state = load_module("constraint_state_snapshot", "dispatch_state_v4.py")
    graph = load_module("constraint_graph_snapshot", "work_graph_v4.py")
    scheduler = load_module("constraint_scheduler_snapshot", "scheduler_v4.py")
    payload = state.new_state(thread_id="thread-snapshot")
    payload["team_plan_revision"] = 1
    payload["work_units"] = [
        graph.make_work_unit(unit_id=f"U{i}", intent="inspect", goal=f"g{i}", output="evidence", done_when="done")
        for i in range(1, 4)
    ]
    state.validate_state_payload(payload)

    decision = scheduler.constraint_snapshot(
        payload, capability_snapshot=capability_snapshot(capacity=4), wakeup_reason="USER_INPUT"
    )
    assert decision["selection_owner"] == "main"
    assert decision["product_child_limit"] == 4
    assert decision["ready_frontier"] == ["U1", "U2", "U3"]
    assert decision["host_session_capacity"] == 4
    assert decision["available_launch_slots"] == 3
    assert decision["actions"] == []


def test_known_host_capacity_reduces_available_slots_and_unknown_capacity_is_not_guessed():
    state = load_module("constraint_state_capacity", "dispatch_state_v4.py")
    graph = load_module("constraint_graph_capacity", "work_graph_v4.py")
    scheduler = load_module("constraint_scheduler_capacity", "scheduler_v4.py")
    payload = state.new_state(thread_id="thread-capacity")
    payload["team_plan_revision"] = 1
    payload["work_units"] = [
        graph.make_work_unit(unit_id=f"U{i}", intent="inspect", goal=f"g{i}", output="evidence", done_when="done")
        for i in range(1, 3)
    ]

    known = scheduler.constraint_snapshot(
        payload, capability_snapshot=capability_snapshot(capacity=2), wakeup_reason="USER_INPUT"
    )
    unknown = scheduler.constraint_snapshot(
        payload, capability_snapshot=capability_snapshot(capacity=None), wakeup_reason="USER_INPUT"
    )
    assert known["host_session_capacity"] == 2
    assert known["available_launch_slots"] == 1
    assert unknown["host_session_capacity"] is None
    assert unknown["available_launch_slots"] == 4


def test_unknown_execution_counts_against_product_and_host_capacity():
    state = load_module("constraint_state_unknown", "dispatch_state_v4.py")
    graph = load_module("constraint_graph_unknown", "work_graph_v4.py")
    scheduler = load_module("constraint_scheduler_unknown", "scheduler_v4.py")
    payload = state.new_state(thread_id="thread-unknown")
    payload["work_units"] = [
        graph.make_work_unit(unit_id="U1", intent="inspect", goal="ambiguous", output="evidence", done_when="done")
    ]
    payload["work_units"][0]["state"] = "EXECUTING"
    payload["executions"] = [{
        "execution_id": "exec-1", "unit_id": "U1", "team_plan_revision": None,
        "attempt_no": 1, "profile_id": "reader", "agent_id": "agent-1",
        "native_task_name": "sd_u1_a1", "model": "gpt-5.6-luna", "effort": "max",
        "granted_authority": "none", "granted_write_scope": [], "workspace_id": "canonical",
        "lifecycle": "UNKNOWN", "control_epoch": 0, "followup_count": 0,
        "failure_origin": "runtime_ambiguous", "blocker": "investigation", "quarantine_reason": "host_ambiguous"
    }]
    state.validate_state_payload(payload)

    decision = scheduler.constraint_snapshot(
        payload, capability_snapshot=capability_snapshot(capacity=4), wakeup_reason="AGENT_UPDATE"
    )
    assert decision["active_managed_executions"] == 1
    assert decision["available_launch_slots"] == 2


def test_execution_facade_enforces_single_product_child_ceiling(tmp_path: Path):
    state = load_module("constraint_state_limit", "dispatch_state_v4.py")
    graph = load_module("constraint_graph_limit", "work_graph_v4.py")
    lifecycle = load_module("constraint_lifecycle_limit", "execution_lifecycle_v4.py")
    state.write_state(state.new_state(thread_id="thread-limit"), temp_root=tmp_path)
    units = [
        graph.make_work_unit(unit_id=f"U{i}", intent="inspect", goal=f"g{i}", output="evidence", done_when="done")
        for i in range(1, 6)
    ]
    graph.install_work_graph("thread-limit", team_plan_revision=1, units=units, temp_root=tmp_path)

    for i in range(1, 5):
        lifecycle.allocate_execution(
            "thread-limit", unit_id=f"U{i}", execution_id=f"exec-{i}", native_task_name=f"sd_u{i}_a1",
            profile_id="reader", granted_authority="none", temp_root=tmp_path
        )

    with pytest.raises(lifecycle.ExecutionLifecycleError, match="child limit 4"):
        lifecycle.allocate_execution(
            "thread-limit", unit_id="U5", execution_id="exec-5", native_task_name="sd_u5_a1",
            profile_id="reader", granted_authority="none", temp_root=tmp_path
        )
    current = state.load_state("thread-limit", temp_root=tmp_path)
    assert current is not None
    assert len(current["executions"]) == 4


def test_plan_only_missing_host_and_cancel_never_offer_launch_slots():
    state = load_module("constraint_state_stop", "dispatch_state_v4.py")
    graph = load_module("constraint_graph_stop", "work_graph_v4.py")
    scheduler = load_module("constraint_scheduler_stop", "scheduler_v4.py")
    payload = state.new_state(thread_id="thread-stop")
    payload["work_units"] = [
        graph.make_work_unit(unit_id="U1", intent="inspect", goal="plan", output="evidence", done_when="done")
    ]
    planned = scheduler.constraint_snapshot(payload, capability_snapshot=capability_snapshot(), wakeup_reason="USER_INPUT", plan_only=True)
    missing = scheduler.constraint_snapshot(payload, capability_snapshot=capability_snapshot(ready=False), wakeup_reason="USER_INPUT")
    absent = scheduler.constraint_snapshot(payload, capability_snapshot=None, wakeup_reason="USER_INPUT")
    cancelled = scheduler.constraint_snapshot(payload, capability_snapshot=capability_snapshot(), wakeup_reason="USER_CANCEL")
    assert planned["available_launch_slots"] == 0
    assert missing["available_launch_slots"] == 0
    assert absent["available_launch_slots"] == 0
    assert absent["host_missing"] == ["capability_snapshot"]
    assert cancelled["available_launch_slots"] == 0
    assert planned["actions"] == missing["actions"] == absent["actions"] == cancelled["actions"] == []


def test_constraint_projection_rejects_unrecognized_wakeup_reason():
    state = load_module("constraint_state_bad_wakeup", "dispatch_state_v4.py")
    scheduler = load_module("constraint_scheduler_bad_wakeup", "scheduler_v4.py")
    payload = state.new_state(thread_id="thread-wakeup")
    with pytest.raises(scheduler.SchedulerError, match="wakeup"):
        scheduler.constraint_snapshot(
            payload, capability_snapshot=capability_snapshot(), wakeup_reason="POLL_FOREVER"
        )
