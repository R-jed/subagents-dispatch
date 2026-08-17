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


def capability_snapshot(*, capacity: int | None = 3, ready: bool = True) -> dict:
    host = load_module(f"p4_host_snapshot_{capacity}_{ready}", "host_capabilities.py")
    lifecycle = ["spawn_agent", "followup_task", "interrupt_agent"]
    guarded = lifecycle + ["list_agents"]
    post = list(guarded)
    if not ready:
        post.remove("interrupt_agent")
    return host.normalize_host_capabilities(
        {
            "surface": "multi_agent_v2",
            "tools": lifecycle + ["list_agents", "wait_agent"],
            "hooks": {
                "PreToolUse": guarded,
                "PostToolUse": post,
                "SubagentStop": True,
            },
            "fork_turns_none": ready,
            "max_spawned_threads": capacity,
        }
    )


def observe_capacity(payload: dict) -> None:
    residents = [
        item
        for item in payload.get("executions", [])
        if item.get("lifecycle") != "CLOSED"
    ]
    settled = sum(
        item.get("lifecycle") in {"COMPLETED", "FAILED", "INTERRUPTED"}
        for item in residents
    )
    payload["accounting_refs"] = [
        event
        for event in payload.get("accounting_refs", [])
        if event.get("kind") != "host_capacity_observation"
    ]
    payload["accounting_refs"].append(
        {
            "ref": "host-capacity-observation:test",
            "kind": "host_capacity_observation",
            "source": "post_tool_use:list_agents",
            "turn_id": "turn-capacity-test",
            "tool_use_id": "tool-capacity-test",
            "resident_children": len(residents),
            "settled_children": settled,
            "active_children": len(residents) - settled,
            "managed_resident_children": len(residents),
            "unmanaged_resident_children": 0,
            "response_digest": "a" * 64,
        }
    )


def make_execution(
    *,
    unit_id: str,
    execution_id: str,
    lifecycle: str,
    attempt_no: int = 1,
    profile_id: str = "reader",
) -> dict:
    model, effort, authority = {
        "reader": ("gpt-5.6-luna", "max", "none"),
        "worker": ("gpt-5.6-luna", "max", "bounded-source-write"),
        "investigator": ("gpt-5.6-terra", "high", "none"),
        "solver": ("gpt-5.6-sol", "high", "bounded-source-write"),
        "advisor": ("gpt-5.6-sol", "high", "none"),
    }[profile_id]
    return {
        "execution_id": execution_id,
        "unit_id": unit_id,
        "team_plan_revision": 1,
        "attempt_no": attempt_no,
        "profile_id": profile_id,
        "agent_id": f"agent-{execution_id}",
        "native_task_name": f"sd_{unit_id.lower()}_a{attempt_no}",
        "model": model,
        "effort": effort,
        "granted_authority": authority,
        "granted_write_scope": ["src/owned.py"] if authority != "none" else [],
        "workspace_id": "canonical",
        "lifecycle": lifecycle,
        "control_epoch": 0,
        "followup_count": 0,
        "failure_origin": "none" if lifecycle != "FAILED" else "quality_failure",
        "blocker": "none",
        "quarantine_reason": None,
    }


def test_dependencies_unlock_only_after_work_unit_acceptance(tmp_path: Path):
    state = load_module("p4_state_accept", "dispatch_state_v4.py")
    graph = load_module("p4_graph_accept", "work_graph_v4.py")

    payload = state.new_state(thread_id="thread-p4")
    state.write_state(payload, temp_root=tmp_path)
    u1 = graph.make_work_unit(
        unit_id="U1",
        intent="inspect",
        goal="produce evidence",
        output="evidence",
        done_when="evidence is verified",
    )
    u2 = graph.make_work_unit(
        unit_id="U2",
        intent="verify",
        goal="consume accepted evidence",
        output="verified conclusion",
        depends_on=["U1"],
        done_when="conclusion is accepted",
    )
    graph.install_work_graph(
        "thread-p4",
        team_plan_revision=1,
        units=[u1, u2],
        temp_root=tmp_path,
    )
    state.mutate_state(
        "thread-p4",
        lambda current: (
            current["executions"].append(
                make_execution(unit_id="U1", execution_id="exec-1", lifecycle="COMPLETED")
            ),
            current["work_units"][0].update({"state": "RESULT_READY"}),
        ),
        temp_root=tmp_path,
    )
    before = state.load_state("thread-p4", temp_root=tmp_path)
    assert before is not None
    assert graph.refresh_dependency_states(before)["work_units"][1]["state"] == "BLOCKED"

    accepted = graph.accept_work_unit(
        "thread-p4",
        unit_id="U1",
        execution_id="exec-1",
        result_ref="result:sha256:abc",
        control_epoch=0,
        temp_root=tmp_path,
    )
    assert accepted["work_units"][0]["state"] == "ACCEPTED"
    assert accepted["work_units"][1]["state"] == "READY"


def test_critical_path_priority_prefers_longest_downstream_chain():
    state = load_module("p4_state_priority", "dispatch_state_v4.py")
    graph = load_module("p4_graph_priority", "work_graph_v4.py")
    scheduler = load_module("p4_scheduler_priority", "scheduler_v4.py")

    payload = state.new_state(thread_id="thread-p4")
    payload["team_plan_revision"] = 1
    payload["work_units"] = [
        graph.make_work_unit(unit_id="U1", intent="inspect", goal="root long chain", output="evidence", done_when="done"),
        graph.make_work_unit(unit_id="U2", intent="inspect", goal="root short chain", output="evidence", done_when="done"),
        graph.make_work_unit(unit_id="U3", intent="verify", goal="middle", output="evidence", depends_on=["U1"], done_when="done"),
        graph.make_work_unit(unit_id="U4", intent="review", goal="tail", output="verdict", depends_on=["U3"], done_when="done"),
        graph.make_work_unit(unit_id="U5", intent="review", goal="short tail", output="verdict", depends_on=["U2"], done_when="done"),
    ]
    observe_capacity(payload)
    state.validate_state_payload(payload)

    decision = scheduler.scheduler_decision(
        payload,
        capability_snapshot=capability_snapshot(capacity=3),
        wakeup_reason="USER_INPUT",
    )
    assert decision["ranked_frontier"][:2] == ["U1", "U2"]
    assert [item["unit_id"] for item in decision["actions"]] == ["U1"]
    assert decision["launch_budget"] == 1


def test_initial_fanout_ceiling_two_refills_one_spawn_per_host_observation():
    state = load_module("p4_state_refill", "dispatch_state_v4.py")
    graph = load_module("p4_graph_refill", "work_graph_v4.py")
    scheduler = load_module("p4_scheduler_refill", "scheduler_v4.py")

    payload = state.new_state(thread_id="thread-p4")
    payload["team_plan_revision"] = 1
    payload["work_units"] = [
        graph.make_work_unit(
            unit_id=f"U{index}",
            intent="inspect",
            goal=f"work {index}",
            output="evidence",
            done_when="done",
        )
        for index in range(1, 5)
    ]
    observe_capacity(payload)
    state.validate_state_payload(payload)
    initial = scheduler.scheduler_decision(
        payload,
        capability_snapshot=capability_snapshot(capacity=3),
        wakeup_reason="USER_INPUT",
    )
    assert initial["effective_capacity"] == 3
    assert initial["initial_fanout"] is True
    assert initial["launch_budget"] == 1
    assert len(initial["actions"]) == 1

    payload["executions"] = [
        make_execution(unit_id="U1", execution_id="exec-1", lifecycle="RUNNING"),
    ]
    payload["work_units"][0]["state"] = "EXECUTING"
    observe_capacity(payload)
    state.validate_state_payload(payload)
    no_progress = scheduler.scheduler_decision(
        payload,
        capability_snapshot=capability_snapshot(capacity=3),
        wakeup_reason="AGENT_UPDATE",
    )
    assert no_progress["initial_fanout"] is True
    assert no_progress["active_managed_executions"] == 1
    assert no_progress["launch_budget"] == 1
    assert len(no_progress["actions"]) == 1

    payload["executions"][0]["lifecycle"] = "COMPLETED"
    payload["work_units"][0].update(
        {
            "state": "ACCEPTED",
            "accepted_result_ref": "result:u1",
            "accepted_execution_id": "exec-1",
            "accepted_control_epoch": 0,
        }
    )
    observe_capacity(payload)
    state.validate_state_payload(payload)
    progressed = scheduler.scheduler_decision(
        payload,
        capability_snapshot=capability_snapshot(capacity=3),
        wakeup_reason="AGENT_COMPLETED",
    )
    assert progressed["initial_fanout"] is False
    assert progressed["active_managed_executions"] == 0
    assert progressed["occupied_host_residents"] == 1
    assert progressed["launch_budget"] == 1
    assert len(progressed["actions"]) == 1


def test_acceptance_backpressure_stops_refill_at_two_unaccepted_results():
    state = load_module("p4_state_backpressure", "dispatch_state_v4.py")
    graph = load_module("p4_graph_backpressure", "work_graph_v4.py")
    scheduler = load_module("p4_scheduler_backpressure", "scheduler_v4.py")

    payload = state.new_state(thread_id="thread-p4")
    payload["team_plan_revision"] = 1
    payload["work_units"] = [
        graph.make_work_unit(unit_id="U1", intent="inspect", goal="r1", output="evidence", done_when="done"),
        graph.make_work_unit(unit_id="U2", intent="inspect", goal="r2", output="evidence", done_when="done"),
        graph.make_work_unit(unit_id="U3", intent="inspect", goal="new", output="evidence", done_when="done"),
    ]
    payload["work_units"][0]["state"] = "RESULT_READY"
    payload["work_units"][1]["state"] = "VERIFYING"
    payload["executions"] = [
        make_execution(unit_id="U1", execution_id="exec-1", lifecycle="COMPLETED"),
        make_execution(unit_id="U2", execution_id="exec-2", lifecycle="COMPLETED"),
    ]
    observe_capacity(payload)
    state.validate_state_payload(payload)

    decision = scheduler.scheduler_decision(
        payload,
        capability_snapshot=capability_snapshot(capacity=3),
        wakeup_reason="AGENT_COMPLETED",
    )
    assert decision["backpressure"] is True
    assert decision["result_backlog"] == 2
    assert decision["actions"] == []
    assert decision["stop_reason"] == "acceptance_backpressure"


def test_unknown_host_capacity_uses_conservative_single_child_path():
    state = load_module("p4_state_unknown_capacity", "dispatch_state_v4.py")
    graph = load_module("p4_graph_unknown_capacity", "work_graph_v4.py")
    scheduler = load_module("p4_scheduler_unknown_capacity", "scheduler_v4.py")

    payload = state.new_state(thread_id="thread-p4")
    payload["team_plan_revision"] = 1
    payload["work_units"] = [
        graph.make_work_unit(unit_id="U1", intent="inspect", goal="a", output="evidence", done_when="done"),
        graph.make_work_unit(unit_id="U2", intent="inspect", goal="b", output="evidence", done_when="done"),
    ]
    observe_capacity(payload)
    state.validate_state_payload(payload)
    decision = scheduler.scheduler_decision(
        payload,
        capability_snapshot=capability_snapshot(capacity=None),
        wakeup_reason="USER_INPUT",
    )
    assert decision["effective_capacity"] == 1
    assert len(decision["actions"]) == 1


def test_unknown_execution_occupies_capacity_and_fails_closed():
    state = load_module("p4_state_unknown_exec", "dispatch_state_v4.py")
    graph = load_module("p4_graph_unknown_exec", "work_graph_v4.py")
    scheduler = load_module("p4_scheduler_unknown_exec", "scheduler_v4.py")

    payload = state.new_state(thread_id="thread-p4")
    payload["team_plan_revision"] = 1
    payload["work_units"] = [
        graph.make_work_unit(unit_id="U1", intent="inspect", goal="ambiguous", output="evidence", done_when="done"),
        graph.make_work_unit(unit_id="U2", intent="inspect", goal="other", output="evidence", done_when="done"),
    ]
    payload["work_units"][0]["state"] = "EXECUTING"
    unknown = make_execution(unit_id="U1", execution_id="exec-1", lifecycle="RUNNING")
    unknown["lifecycle"] = "UNKNOWN"
    unknown["failure_origin"] = "runtime_ambiguous"
    unknown["blocker"] = "investigation"
    unknown["quarantine_reason"] = "host_ambiguous"
    payload["executions"] = [unknown]
    observe_capacity(payload)
    state.validate_state_payload(payload)

    decision = scheduler.scheduler_decision(
        payload,
        capability_snapshot=capability_snapshot(capacity=1),
        wakeup_reason="AGENT_UPDATE",
    )
    assert decision["active_managed_executions"] == 1
    assert decision["occupied_host_residents"] == 1
    assert decision["actions"] == []
    assert decision["stop_reason"] == "host_capacity_full"


def test_plan_only_and_missing_host_never_return_launch_actions():
    state = load_module("p4_state_planonly", "dispatch_state_v4.py")
    graph = load_module("p4_graph_planonly", "work_graph_v4.py")
    scheduler = load_module("p4_scheduler_planonly", "scheduler_v4.py")

    payload = state.new_state(thread_id="thread-p4")
    payload["team_plan_revision"] = 1
    payload["work_units"] = [
        graph.make_work_unit(unit_id="U1", intent="inspect", goal="plan", output="evidence", done_when="done")
    ]
    observe_capacity(payload)
    state.validate_state_payload(payload)

    planned = scheduler.scheduler_decision(
        payload,
        capability_snapshot=capability_snapshot(capacity=3),
        wakeup_reason="USER_INPUT",
        plan_only=True,
    )
    assert planned["actions"] == []
    assert planned["stop_reason"] == "plan_only"

    missing = scheduler.scheduler_decision(
        payload,
        capability_snapshot=None,
        wakeup_reason="USER_INPUT",
    )
    assert missing["actions"] == []
    assert missing["stop_reason"] == "host_not_execution_ready"


def test_scheduler_rejects_unrecognized_wakeup_reason():
    state = load_module("p4_state_bad_wakeup", "dispatch_state_v4.py")
    scheduler = load_module("p4_scheduler_bad_wakeup", "scheduler_v4.py")
    payload = state.new_state(thread_id="thread-p4")

    with pytest.raises(scheduler.SchedulerError, match="wakeup"):
        scheduler.scheduler_decision(
            payload,
            capability_snapshot=capability_snapshot(),
            wakeup_reason="POLL_FOREVER",
        )
