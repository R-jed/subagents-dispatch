from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
STATE_PATH = SCRIPTS / "dispatch_state_v4.py"
CONTROL_PATH = SCRIPTS / "dispatch_control_v4.py"


def load_module(name: str, path: Path):
    scripts = str(SCRIPTS)
    sys.path.insert(0, scripts)
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts)


def unit(*, authority: str = "none") -> dict:
    scope = [] if authority == "none" else ["src/owned.py"]
    return {
        "unit_id": "U1",
        "intent": "inspect" if authority == "none" else "implement",
        "goal": "complete bounded work",
        "output": "verified result",
        "depends_on": [],
        "state": "EXECUTING",
        "ownership": {"write": scope, "forbidden": []},
        "authority_ceiling": authority,
        "write_scope_ceiling": scope,
        "done_when": "Main verifies the result",
        "accepted_result_ref": None,
        "accepted_execution_id": None,
        "accepted_control_epoch": None,
    }


def execution(*, lifecycle: str = "SPAWN_PENDING", authority: str = "none", epoch: int = 0) -> dict:
    profile = "reader" if authority == "none" else "worker"
    return {
        "execution_id": "exec-1",
        "unit_id": "U1",
        "team_plan_revision": None,
        "attempt_no": 1,
        "profile_id": profile,
        "agent_id": None,
        "native_task_name": "sd-u1-a1",
        "model": "gpt-5.6-luna",
        "effort": "max",
        "granted_authority": authority,
        "granted_write_scope": [] if authority == "none" else ["src/owned.py"],
        "workspace_id": "canonical",
        "lifecycle": lifecycle,
        "control_epoch": epoch,
        "followup_count": 0,
        "failure_origin": "none",
        "blocker": "none",
        "quarantine_reason": None,
    }


def persist(state_module, tmp_path: Path, *, lifecycle: str = "SPAWN_PENDING", authority: str = "none"):
    payload = state_module.new_state(thread_id="thread-1")
    payload["work_units"] = [unit(authority=authority)]
    payload["executions"] = [execution(lifecycle=lifecycle, authority=authority)]
    if authority != "none":
        payload["writer_lease"] = {
            "lease_id": "lease-1",
            "lease_epoch": 3,
            "workspace_id": "canonical",
            "unit_id": "U1",
            "owner_kind": "execution",
            "owner_id": "exec-1",
            "state": "RESERVED" if lifecycle == "SPAWN_PENDING" else "HELD",
        }
    state_module.write_state(payload, temp_root=tmp_path)


def test_spawn_control_is_prepared_consumed_and_acknowledged_once(tmp_path: Path):
    state_module = load_module("control_state_spawn", STATE_PATH)
    control = load_module("control_v4_spawn", CONTROL_PATH)
    persist(state_module, tmp_path)
    tool_input = {
        "task_name": "sd-u1-a1",
        "message": "read one bounded area",
        "agent_type": "subagents_dispatch_reader",
        "fork_turns": "none",
    }

    prepared = control.prepare_control(
        "thread-1",
        control_id="control-1",
        execution_id="exec-1",
        operation="SPAWN",
        tool_input=tool_input,
        temp_root=tmp_path,
    )
    assert prepared["state"] == "PREPARED"

    consumed = control.consume_prepared_control(
        "thread-1",
        tool_name="spawn_agent",
        tool_input=tool_input,
        tool_use_id="tool-1",
        temp_root=tmp_path,
    )
    assert consumed["state"] == "IN_FLIGHT"
    assert consumed["tool_use_id"] == "tool-1"

    with pytest.raises(control.ControlError, match="PREPARED"):
        control.consume_prepared_control(
            "thread-1",
            tool_name="spawn_agent",
            tool_input=tool_input,
            tool_use_id="tool-2",
            temp_root=tmp_path,
        )

    acknowledged = control.acknowledge_control(
        "thread-1",
        tool_name="spawn_agent",
        tool_input=tool_input,
        tool_response={"task_name": "sd-u1-a1"},
        tool_use_id="tool-1",
        temp_root=tmp_path,
    )
    assert acknowledged["state"] == "ACKED"
    assert acknowledged["idempotent"] is False

    current = state_module.load_state("thread-1", temp_root=tmp_path)
    assert current is not None
    assert current["pending_controls"] == []
    assert current["executions"][0]["control_epoch"] == 0
    assert any(
        event["ref"] == "control-ack:control-1:tool-1"
        and event.get("control_id") == "control-1"
        and event.get("tool_use_id") == "tool-1"
        for event in current["accounting_refs"]
    )

    duplicate = control.acknowledge_control(
        "thread-1",
        tool_name="spawn_agent",
        tool_input=tool_input,
        tool_response={"task_name": "sd-u1-a1"},
        tool_use_id="tool-1",
        temp_root=tmp_path,
    )
    assert duplicate == {"state": "ACKED", "tool_use_id": "tool-1", "idempotent": True}


def test_followup_advances_local_control_epoch_only_after_ack(tmp_path: Path):
    state_module = load_module("control_state_followup", STATE_PATH)
    control = load_module("control_v4_followup", CONTROL_PATH)
    persist(state_module, tmp_path, lifecycle="COMPLETED")
    tool_input = {"target": "sd-u1-a1", "message": "fix the one acceptance miss"}

    control.prepare_control(
        "thread-1",
        control_id="control-followup",
        execution_id="exec-1",
        operation="FOLLOWUP",
        tool_input=tool_input,
        temp_root=tmp_path,
    )
    control.consume_prepared_control(
        "thread-1",
        tool_name="followup_task",
        tool_input=tool_input,
        tool_use_id="tool-followup",
        temp_root=tmp_path,
    )
    inflight = state_module.load_state("thread-1", temp_root=tmp_path)
    assert inflight is not None
    assert inflight["executions"][0]["control_epoch"] == 0

    control.acknowledge_control(
        "thread-1",
        tool_name="followup_task",
        tool_input=tool_input,
        tool_response={},
        tool_use_id="tool-followup",
        temp_root=tmp_path,
    )
    acknowledged = state_module.load_state("thread-1", temp_root=tmp_path)
    assert acknowledged is not None
    assert acknowledged["executions"][0]["control_epoch"] == 1


def test_payload_drift_cannot_ack_and_inflight_control_can_be_quarantined(tmp_path: Path):
    state_module = load_module("control_state_drift", STATE_PATH)
    control = load_module("control_v4_drift", CONTROL_PATH)
    persist(state_module, tmp_path)
    original = {
        "task_name": "sd-u1-a1",
        "message": "read bounded scope",
        "agent_type": "subagents_dispatch_reader",
        "fork_turns": "none",
    }
    control.prepare_control(
        "thread-1",
        control_id="control-drift",
        execution_id="exec-1",
        operation="SPAWN",
        tool_input=original,
        temp_root=tmp_path,
    )
    control.consume_prepared_control(
        "thread-1",
        tool_name="spawn_agent",
        tool_input=original,
        tool_use_id="tool-drift",
        temp_root=tmp_path,
    )

    changed = dict(original)
    changed["message"] = "different payload"
    with pytest.raises(control.ControlError, match="IN_FLIGHT"):
        control.acknowledge_control(
            "thread-1",
            tool_name="spawn_agent",
            tool_input=changed,
            tool_response={"task_name": "sd-u1-a1"},
            tool_use_id="tool-drift",
            temp_root=tmp_path,
        )
    assert control.mark_control_unknown(
        "thread-1", tool_use_id="tool-drift", temp_root=tmp_path
    )
    current = state_module.load_state("thread-1", temp_root=tmp_path)
    assert current is not None
    assert current["pending_controls"][0]["state"] == "UNKNOWN"


def test_writer_control_requires_matching_lease_state_and_effect(tmp_path: Path):
    state_module = load_module("control_state_writer", STATE_PATH)
    control = load_module("control_v4_writer", CONTROL_PATH)
    persist(state_module, tmp_path, authority="bounded-source-write")
    tool_input = {
        "task_name": "sd-u1-a1",
        "message": "write bounded scope",
        "agent_type": "subagents_dispatch_worker",
        "fork_turns": "none",
    }

    with pytest.raises(control.ControlError, match="writer_effect=RESERVE"):
        control.prepare_control(
            "thread-1",
            control_id="control-writer-bad",
            execution_id="exec-1",
            operation="SPAWN",
            tool_input=tool_input,
            writer_effect="NONE",
            temp_root=tmp_path,
        )

    prepared = control.prepare_control(
        "thread-1",
        control_id="control-writer",
        execution_id="exec-1",
        operation="SPAWN",
        tool_input=tool_input,
        writer_effect="RESERVE",
        temp_root=tmp_path,
    )
    assert prepared["expected_lease_epoch"] == 3


def test_continue_and_followup_are_distinct_semantics_on_same_host_tool(tmp_path: Path):
    state_module = load_module("control_state_continue", STATE_PATH)
    control = load_module("control_v4_continue", CONTROL_PATH)
    persist(state_module, tmp_path, lifecycle="INTERRUPTED")
    tool_input = {"target": "sd-u1-a1", "message": "continue the unchanged assignment"}

    prepared = control.prepare_control(
        "thread-1",
        control_id="control-continue",
        execution_id="exec-1",
        operation="CONTINUE",
        tool_input=tool_input,
        temp_root=tmp_path,
    )
    assert prepared["operation"] == "CONTINUE"
    assert prepared["next_control_epoch"] == 1

    with pytest.raises(control.ControlError, match="unresolved"):
        control.prepare_control(
            "thread-1",
            control_id="control-followup",
            execution_id="exec-1",
            operation="FOLLOWUP",
            tool_input=tool_input,
            temp_root=tmp_path,
        )
