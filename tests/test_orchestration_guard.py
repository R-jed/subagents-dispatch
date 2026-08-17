from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
STATE_V4 = SCRIPTS / "dispatch_state_v4.py"
CONTROL_V4 = SCRIPTS / "dispatch_control_v4.py"
GUARD = SCRIPTS / "orchestration_guard.py"
MANAGED = SCRIPTS / "managed_execution_v4.py"


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


def v4_state(state_module, tmp_path: Path) -> None:
    payload = state_module.new_state(thread_id="root-thread")
    payload["work_units"] = [
        {
            "unit_id": "U1",
            "intent": "inspect",
            "goal": "read bounded scope",
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
    ]
    payload["executions"] = [
        {
            "execution_id": "exec-1",
            "unit_id": "U1",
            "team_plan_revision": None,
            "attempt_no": 1,
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
        }
    ]
    state_module.write_state(payload, temp_root=tmp_path)


def canonical_spawn(state_module, tmp_path: Path, *, module_name: str) -> dict:
    managed = load_module(module_name, MANAGED)
    current = state_module.load_state("root-thread", temp_root=tmp_path)
    assert current is not None
    return managed.expected_spawn_input_for_execution(current, execution_id="exec-1")


def pre_payload(tool_input: dict, *, tool_name: str = "spawn_agent", caller: str | None = None) -> dict:
    payload = {
        "hook_event_name": "PreToolUse",
        "session_id": "root-thread",
        "turn_id": "turn-1",
        "tool_name": tool_name,
        "tool_use_id": "tool-1",
        "tool_input": tool_input,
    }
    if caller is not None:
        payload["agent_id"] = "child-id"
        payload["agent_type"] = caller
    return payload


def post_payload(tool_input: dict, *, tool_name: str = "spawn_agent") -> dict:
    return {
        "hook_event_name": "PostToolUse",
        "session_id": "root-thread",
        "turn_id": "turn-1",
        "tool_name": tool_name,
        "tool_use_id": "tool-1",
        "tool_input": tool_input,
        "tool_response": {"task_name": "sd_u1_a1"},
    }


def test_v4_managed_spawn_requires_and_consumes_prepared_control(tmp_path: Path):
    state_module = load_module("guard_state_v4", STATE_V4)
    control = load_module("guard_control_v4", CONTROL_V4)
    guard = load_module("guard_under_test_v4", GUARD)
    v4_state(state_module, tmp_path)
    tool_input = canonical_spawn(state_module, tmp_path, module_name="guard_managed_v4")

    with pytest.raises(guard.control.ControlError, match="PREPARED"):
        guard.evaluate_pre_tool_use(pre_payload(tool_input), temp_root=tmp_path)

    control.prepare_control(
        "root-thread",
        control_id="control-1",
        execution_id="exec-1",
        operation="SPAWN",
        tool_input=tool_input,
        temp_root=tmp_path,
    )
    assert guard.evaluate_pre_tool_use(pre_payload(tool_input), temp_root=tmp_path) is None
    current = state_module.load_state("root-thread", temp_root=tmp_path)
    assert current is not None
    assert current["pending_controls"][0]["state"] == "IN_FLIGHT"
    assert current["pending_controls"][0]["tool_use_id"] == "tool-1"

    second = pre_payload(tool_input)
    second["tool_use_id"] = "tool-2"
    with pytest.raises(guard.control.ControlError, match="PREPARED"):
        guard.evaluate_pre_tool_use(second, temp_root=tmp_path)


def test_post_tool_use_acknowledges_exact_control(tmp_path: Path):
    state_module = load_module("guard_state_post", STATE_V4)
    control = load_module("guard_control_post", CONTROL_V4)
    guard = load_module("guard_under_test_post", GUARD)
    v4_state(state_module, tmp_path)
    tool_input = canonical_spawn(state_module, tmp_path, module_name="guard_managed_post")
    control.prepare_control(
        "root-thread",
        control_id="control-1",
        execution_id="exec-1",
        operation="SPAWN",
        tool_input=tool_input,
        temp_root=tmp_path,
    )
    assert guard.evaluate_pre_tool_use(pre_payload(tool_input), temp_root=tmp_path) is None
    assert guard.evaluate_post_tool_use(post_payload(tool_input), temp_root=tmp_path) is None

    current = state_module.load_state("root-thread", temp_root=tmp_path)
    assert current is not None
    assert current["pending_controls"] == []
    assert any(
        event.get("ref") == "control-ack:control-1:tool-1"
        and event.get("control_id") == "control-1"
        for event in current["accounting_refs"]
    )


def test_post_payload_drift_stops_and_quarantines_control(tmp_path: Path):
    state_module = load_module("guard_state_drift", STATE_V4)
    control = load_module("guard_control_drift", CONTROL_V4)
    guard = load_module("guard_under_test_drift", GUARD)
    v4_state(state_module, tmp_path)
    original = canonical_spawn(state_module, tmp_path, module_name="guard_managed_drift")
    control.prepare_control(
        "root-thread",
        control_id="control-1",
        execution_id="exec-1",
        operation="SPAWN",
        tool_input=original,
        temp_root=tmp_path,
    )
    assert guard.evaluate_pre_tool_use(pre_payload(original), temp_root=tmp_path) is None

    changed = dict(original)
    changed["message"] = "changed after pre hook"
    stopped = guard.evaluate_post_tool_use(post_payload(changed), temp_root=tmp_path)
    assert stopped is not None
    assert stopped["continue"] is False
    current = state_module.load_state("root-thread", temp_root=tmp_path)
    assert current is not None
    assert current["pending_controls"][0]["state"] == "UNKNOWN"


def test_managed_child_cannot_use_any_lifecycle_tool_even_for_unrelated_target(tmp_path: Path):
    guard = load_module("guard_under_test_child", GUARD)
    caller = "subagents_dispatch_reader"
    calls = [
        ("spawn_agent", {"task_name": "other", "message": "x", "agent_type": "default"}),
        ("followup_task", {"target": "other", "message": "x"}),
        ("interrupt_agent", {"target": "other"}),
    ]
    for tool_name, tool_input in calls:
        result = guard.evaluate_pre_tool_use(
            pre_payload(tool_input, tool_name=tool_name, caller=caller), temp_root=tmp_path
        )
        assert result is not None
        assert result["decision"] == "block"


def test_subagent_stop_forces_managed_leaf_to_stop():
    guard = load_module("guard_under_test_stop", GUARD)
    result = guard.evaluate_subagent_stop(
        {
            "hook_event_name": "SubagentStop",
            "session_id": "root-thread",
            "turn_id": "child-turn",
            "agent_id": "child-id",
            "agent_type": "subagents_dispatch_worker",
        }
    )
    assert result is not None
    assert result["continue"] is False
    assert "PendingControl" in result["stopReason"]


def test_unrelated_root_lifecycle_call_passes_through_without_dispatch_state(tmp_path: Path):
    guard = load_module("guard_under_test_unrelated", GUARD)
    result = guard.evaluate_pre_tool_use(
        pre_payload(
            {"target": "unrelated_agent", "message": "hello"}, tool_name="followup_task"
        ),
        temp_root=tmp_path,
    )
    assert result is None


def test_cli_post_failure_stops_instead_of_failing_open(monkeypatch, capsys):
    guard = load_module("guard_under_test_cli", GUARD)
    payload = {
        "hook_event_name": "PostToolUse",
        "session_id": "root-thread",
        "tool_name": "spawn_agent",
        "tool_use_id": "tool-1",
        "tool_input": {},
        "tool_response": {},
    }
    fake_stdin = io.TextIOWrapper(io.BytesIO(json.dumps(payload).encode()), encoding="utf-8")
    monkeypatch.setattr(guard.sys, "stdin", fake_stdin)
    monkeypatch.setattr(
        guard,
        "evaluate_hook",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    guard.main()
    captured = capsys.readouterr()
    rendered = json.loads(captured.out)
    assert rendered["continue"] is False
    assert "boom" not in captured.out
