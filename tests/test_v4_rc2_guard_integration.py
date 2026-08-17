from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


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


def test_actual_guard_posttool_path_promotes_reserved_writer(tmp_path: Path):
    state = load_module("rc2_guard_state", "dispatch_state_v4.py")
    control = load_module("rc2_guard_control", "dispatch_control_v4.py")
    guard = load_module("rc2_guard", "orchestration_guard.py")
    managed = load_module("rc2_guard_managed", "managed_execution_v4.py")

    payload = state.new_state(thread_id="thread-guard")
    payload["team_plan_revision"] = 1
    payload["work_units"] = [
        {
            "unit_id": "U1",
            "intent": "implement",
            "goal": "bounded write",
            "output": "patch",
            "depends_on": [],
            "state": "EXECUTING",
            "ownership": {"write": ["src/u1.py"], "forbidden": []},
            "authority_ceiling": "bounded-source-write",
            "write_scope_ceiling": ["src/u1.py"],
            "done_when": "tests pass",
            "accepted_result_ref": None,
            "accepted_execution_id": None,
            "accepted_control_epoch": None,
        }
    ]
    payload["executions"] = [
        {
            "execution_id": "exec-1",
            "unit_id": "U1",
            "team_plan_revision": 1,
            "attempt_no": 1,
            "profile_id": "worker",
            "agent_id": None,
            "native_task_name": "sd-u1-a1",
            "model": "gpt-5.6-luna",
            "effort": "max",
            "granted_authority": "bounded-source-write",
            "granted_write_scope": ["src/u1.py"],
            "workspace_id": "canonical",
            "lifecycle": "SPAWN_PENDING",
            "control_epoch": 0,
            "followup_count": 0,
            "failure_origin": "none",
            "blocker": "none",
            "quarantine_reason": None,
        }
    ]
    payload["writer_lease"] = {
        "lease_id": "lease-1",
        "lease_epoch": 1,
        "workspace_id": "canonical",
        "unit_id": "U1",
        "owner_kind": "execution",
        "owner_id": "exec-1",
        "state": "RESERVED",
    }
    state.write_state(payload, temp_root=tmp_path)

    current = state.load_state("thread-guard", temp_root=tmp_path)
    assert current is not None
    tool_input = managed.expected_spawn_input_for_execution(current, execution_id="exec-1")
    control.prepare_control(
        "thread-guard",
        control_id="spawn:exec-1",
        execution_id="exec-1",
        operation="SPAWN",
        tool_input=tool_input,
        writer_effect="RESERVE",
        temp_root=tmp_path,
    )

    pre = {
        "session_id": "thread-guard",
        "hook_event_name": "PreToolUse",
        "tool_name": "spawn_agent",
        "tool_input": tool_input,
        "tool_use_id": "tool-spawn",
    }
    assert guard.evaluate_pre_tool_use(pre, temp_root=tmp_path) is None
    inflight = state.load_state("thread-guard", temp_root=tmp_path)
    assert inflight is not None
    assert inflight["pending_controls"][0]["state"] == "IN_FLIGHT"
    assert inflight["writer_lease"]["state"] == "RESERVED"

    post = {
        "session_id": "thread-guard",
        "hook_event_name": "PostToolUse",
        "tool_name": "spawn_agent",
        "tool_input": tool_input,
        "tool_use_id": "tool-spawn",
        "tool_response": {"task_name": "sd-u1-a1"},
    }
    assert guard.evaluate_post_tool_use(post, temp_root=tmp_path) is None
    acknowledged = state.load_state("thread-guard", temp_root=tmp_path)
    assert acknowledged is not None
    assert acknowledged["pending_controls"] == []
    assert acknowledged["writer_lease"]["state"] == "HELD"
    assert any(
        item.get("ref") == "control-ack:spawn:exec-1:tool-spawn"
        and item.get("control_id") == "spawn:exec-1"
        for item in acknowledged["accounting_refs"]
    )
