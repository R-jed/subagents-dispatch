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


def unit(*, state_name: str = "RESULT_READY") -> dict:
    accepted = state_name == "ACCEPTED"
    return {
        "unit_id": "U1",
        "intent": "inspect",
        "goal": "inspect",
        "output": "facts",
        "depends_on": [],
        "state": state_name,
        "ownership": {"write": [], "forbidden": []},
        "authority_ceiling": "none",
        "write_scope_ceiling": [],
        "done_when": "Main verifies facts",
        "accepted_result_ref": "result:1" if accepted else None,
        "accepted_execution_id": "exec-1" if accepted else None,
        "accepted_control_epoch": 0 if accepted else None,
    }


def execution(
    execution_id: str,
    *,
    attempt_no: int = 1,
    lifecycle: str = "COMPLETED",
    control_epoch: int = 0,
) -> dict:
    return {
        "execution_id": execution_id,
        "unit_id": "U1",
        "team_plan_revision": 1,
        "attempt_no": attempt_no,
        "profile_id": "reader",
        "agent_id": None,
        "native_task_name": f"sd-u1-a{attempt_no}",
        "model": "gpt-5.6-luna",
        "effort": "max",
        "granted_authority": "none",
        "granted_write_scope": [],
        "workspace_id": "canonical",
        "lifecycle": lifecycle,
        "control_epoch": control_epoch,
        "followup_count": 0,
        "failure_origin": "none",
        "blocker": "none",
        "quarantine_reason": None,
    }


def install(state, tmp_path: Path, *, executions: list[dict], state_name: str = "RESULT_READY") -> None:
    payload = state.new_state(thread_id="thread-rc3-truth")
    payload["team_plan_revision"] = 1
    payload["work_units"] = [unit(state_name=state_name)]
    payload["executions"] = executions
    state.write_state(payload, temp_root=tmp_path)


def test_reused_tool_use_id_cannot_turn_new_control_into_old_idempotent_ack(tmp_path: Path):
    state = load_module("rc3_truth_state_replay", "dispatch_state_v4.py")
    control = load_module("rc3_truth_control_replay", "dispatch_control_v4.py")
    install(state, tmp_path, executions=[execution("exec-1")])
    tool_input = {"target": "sd-u1-a1", "message": "same correction"}

    control.prepare_control(
        "thread-rc3-truth",
        control_id="c1",
        execution_id="exec-1",
        operation="FOLLOWUP",
        tool_input=tool_input,
        temp_root=tmp_path,
    )
    control.consume_prepared_control(
        "thread-rc3-truth",
        tool_name="followup_task",
        tool_input=tool_input,
        tool_use_id="T",
        temp_root=tmp_path,
    )
    first = control.acknowledge_control(
        "thread-rc3-truth",
        tool_name="followup_task",
        tool_input=tool_input,
        tool_response={},
        tool_use_id="T",
        temp_root=tmp_path,
    )
    assert first["idempotent"] is False

    control.prepare_control(
        "thread-rc3-truth",
        control_id="c2",
        execution_id="exec-1",
        operation="FOLLOWUP",
        tool_input=tool_input,
        temp_root=tmp_path,
    )
    control.consume_prepared_control(
        "thread-rc3-truth",
        tool_name="followup_task",
        tool_input=tool_input,
        tool_use_id="T",
        temp_root=tmp_path,
    )
    second = control.acknowledge_control(
        "thread-rc3-truth",
        tool_name="followup_task",
        tool_input=tool_input,
        tool_response={},
        tool_use_id="T",
        temp_root=tmp_path,
    )
    assert second["idempotent"] is False

    current = state.load_state("thread-rc3-truth", temp_root=tmp_path)
    assert current is not None
    ack_events = [event for event in current["accounting_refs"] if event.get("kind") == "control_ack"]
    assert {event["control_id"] for event in ack_events} == {"c1", "c2"}
    assert len({event["ref"] for event in ack_events}) == 2


def test_superseded_attempt_cannot_prepare_followup(tmp_path: Path):
    state = load_module("rc3_truth_state_superseded", "dispatch_state_v4.py")
    control = load_module("rc3_truth_control_superseded", "dispatch_control_v4.py")
    install(
        state,
        tmp_path,
        executions=[execution("exec-1", attempt_no=1), execution("exec-2", attempt_no=2)],
    )
    with pytest.raises(control.ControlError, match="superseded|current"):
        control.prepare_control(
            "thread-rc3-truth",
            control_id="old-followup",
            execution_id="exec-1",
            operation="FOLLOWUP",
            tool_input={"target": "sd-u1-a1", "message": "stale"},
            temp_root=tmp_path,
        )


def test_accepted_unit_rejects_unresolved_control_even_when_producer_is_completed():
    state = load_module("rc3_truth_state_unresolved", "dispatch_state_v4.py")
    payload = state.new_state(thread_id="thread-rc3-truth")
    payload["team_plan_revision"] = 1
    payload["work_units"] = [unit(state_name="ACCEPTED")]
    payload["executions"] = [execution("exec-1")]
    payload["pending_controls"] = [
        {
            "control_id": "c1",
            "unit_id": "U1",
            "execution_id": "exec-1",
            "operation": "FOLLOWUP",
            "target": "sd-u1-a1",
            "payload_digest": "a" * 64,
            "expected_team_plan_revision": 1,
            "expected_control_epoch": 0,
            "next_control_epoch": 1,
            "expected_lease_epoch": None,
            "writer_effect": "NONE",
            "state": "PREPARED",
            "tool_use_id": None,
        }
    ]
    with pytest.raises(state.StatePayloadError, match="accepted|PendingControl"):
        state.validate_state_payload(payload)


def test_accepted_closed_producer_requires_prior_completed_observation():
    state = load_module("rc3_truth_state_closed", "dispatch_state_v4.py")
    payload = state.new_state(thread_id="thread-rc3-truth")
    payload["team_plan_revision"] = 1
    payload["work_units"] = [unit(state_name="ACCEPTED")]
    payload["executions"] = [execution("exec-1", lifecycle="CLOSED")]

    with pytest.raises(state.StatePayloadError, match="COMPLETED proof"):
        state.validate_state_payload(payload)

    payload["accounting_refs"] = [
        {
            "ref": "host-observation:exec-1:0:none:COMPLETED",
            "kind": "host_observation",
            "execution_id": "exec-1",
            "control_epoch": 0,
            "lease_epoch": None,
            "lifecycle": "COMPLETED",
        }
    ]
    state.validate_state_payload(payload)


def test_duplicate_posttooluse_is_idempotent_at_production_guard(tmp_path: Path):
    state = load_module("rc3_truth_state_guard", "dispatch_state_v4.py")
    control = load_module("rc3_truth_control_guard", "dispatch_control_v4.py")
    guard = load_module("rc3_truth_guard", "orchestration_guard.py")
    managed = load_module("rc3_truth_managed", "managed_execution_v4.py")

    payload = state.new_state(thread_id="thread-rc3-truth")
    payload["team_plan_revision"] = 1
    payload["work_units"] = [unit(state_name="EXECUTING")]
    payload["executions"] = [execution("exec-1", lifecycle="SPAWN_PENDING")]
    state.write_state(payload, temp_root=tmp_path)
    current = state.load_state("thread-rc3-truth", temp_root=tmp_path)
    assert current is not None
    tool_input = managed.expected_spawn_input_for_execution(current, execution_id="exec-1")
    control.prepare_control(
        "thread-rc3-truth",
        control_id="spawn:exec-1",
        execution_id="exec-1",
        operation="SPAWN",
        tool_input=tool_input,
        temp_root=tmp_path,
    )
    pre = {
        "session_id": "thread-rc3-truth",
        "hook_event_name": "PreToolUse",
        "tool_name": "spawn_agent",
        "tool_input": tool_input,
        "tool_use_id": "tool-1",
    }
    post = {
        "session_id": "thread-rc3-truth",
        "hook_event_name": "PostToolUse",
        "tool_name": "spawn_agent",
        "tool_input": tool_input,
        "tool_use_id": "tool-1",
        "tool_response": {"task_name": "sd-u1-a1"},
    }
    assert guard.evaluate_pre_tool_use(pre, temp_root=tmp_path) is None
    assert guard.evaluate_post_tool_use(post, temp_root=tmp_path) is None
    assert guard.evaluate_post_tool_use(post, temp_root=tmp_path) is None
