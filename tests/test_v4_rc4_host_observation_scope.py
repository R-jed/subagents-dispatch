from __future__ import annotations

import importlib.util
import json
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


def official_list_agents_wire(agents: list[dict]) -> str:
    return json.dumps({"agents": agents}, separators=(",", ":"))


def make_state(state, graph, *, thread_id: str, ready: bool = False) -> dict:
    payload = state.new_state(thread_id=thread_id)
    payload["team_plan_revision"] = 1
    payload["work_units"] = [
        graph.make_work_unit(
            unit_id="U1",
            intent="inspect",
            goal="inspect U1",
            output="facts",
            done_when="Main verifies facts",
        )
    ]
    if not ready:
        payload["work_units"][0]["state"] = "EXECUTING"
        payload["executions"] = [
            {
                "execution_id": "exec_1",
                "unit_id": "U1",
                "team_plan_revision": 1,
                "attempt_no": 1,
                "profile_id": "reader",
                "agent_id": "agent-exec-1",
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
        ]
    return payload


def pre_payload(thread_id: str, tool_use_id: str, *, tool_input: dict) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "session_id": thread_id,
        "turn_id": f"turn-{tool_use_id}",
        "tool_name": "list_agents",
        "tool_use_id": tool_use_id,
        "tool_input": tool_input,
    }


def test_authoritative_capacity_rejects_filtered_list_agents_pre(tmp_path: Path):
    state = load_module("scope_pre_state", "dispatch_state_v4.py")
    graph = load_module("scope_pre_graph", "work_graph_v4.py")
    guard = load_module("scope_pre_guard", "orchestration_guard.py")
    thread_id = "thread-scope-pre"
    state.write_state(make_state(state, graph, thread_id=thread_id), temp_root=tmp_path)

    result = guard.evaluate_pre_tool_use(
        pre_payload(thread_id, "tool-filtered", tool_input={"path_prefix": "sd_u1_a1"}),
        temp_root=tmp_path,
    )

    assert result is not None
    assert result["decision"] == "block"
    assert "unfiltered" in result["reason"] or "tool_input" in result["reason"]


def test_authoritative_capacity_rejects_nonroot_hook_caller(tmp_path: Path):
    state = load_module("scope_caller_state", "dispatch_state_v4.py")
    graph = load_module("scope_caller_graph", "work_graph_v4.py")
    guard = load_module("scope_caller_guard", "orchestration_guard.py")
    thread_id = "thread-scope-caller"
    state.write_state(make_state(state, graph, thread_id=thread_id), temp_root=tmp_path)
    payload = pre_payload(thread_id, "tool-child", tool_input={})
    payload["agent_id"] = "child-agent-id"
    payload["agent_type"] = "custom_child"

    result = guard.evaluate_pre_tool_use(payload, temp_root=tmp_path)

    assert result is not None
    assert result["decision"] == "block"
    assert "root" in result["reason"]


def test_post_tool_input_must_match_pre_binding(tmp_path: Path):
    state = load_module("scope_bind_state", "dispatch_state_v4.py")
    graph = load_module("scope_bind_graph", "work_graph_v4.py")
    guard = load_module("scope_bind_guard", "orchestration_guard.py")
    thread_id = "thread-scope-bind"
    state.write_state(make_state(state, graph, thread_id=thread_id), temp_root=tmp_path)
    pre = pre_payload(thread_id, "tool-bind", tool_input={})
    assert guard.evaluate_pre_tool_use(pre, temp_root=tmp_path) is None
    post = {
        **pre,
        "hook_event_name": "PostToolUse",
        "tool_input": {"path_prefix": "sd_u1_a1"},
        "tool_response": official_list_agents_wire(
            [{"agent_name": "/root/sd_u1_a1", "agent_status": "running"}]
        ),
    }

    result = guard.evaluate_post_tool_use(post, temp_root=tmp_path)

    assert result is not None
    assert result["continue"] is False
    current = state.load_state(thread_id, temp_root=tmp_path)
    assert current is not None
    assert not any(
        event.get("kind") == "host_capacity_observation"
        for event in current["accounting_refs"]
    )


def test_filtered_list_agents_cannot_replace_full_capacity_truth(tmp_path: Path):
    state = load_module("scope_replace_state", "dispatch_state_v4.py")
    graph = load_module("scope_replace_graph", "work_graph_v4.py")
    guard = load_module("scope_replace_guard", "orchestration_guard.py")
    thread_id = "thread-scope-replace"
    state.write_state(make_state(state, graph, thread_id=thread_id), temp_root=tmp_path)

    full_pre = pre_payload(thread_id, "tool-full", tool_input={})
    full_post = {
        **full_pre,
        "hook_event_name": "PostToolUse",
        "tool_response": official_list_agents_wire(
            [
                {"agent_name": "/root", "agent_status": "running"},
                {"agent_name": "/root/sd_u1_a1", "agent_status": "running"},
                {"agent_name": "/root/manual_a", "agent_status": "running"},
                {"agent_name": "/root/manual_b", "agent_status": {"completed": "done"}},
            ]
        ),
    }
    assert guard.evaluate_pre_tool_use(full_pre, temp_root=tmp_path) is None
    assert guard.evaluate_post_tool_use(full_post, temp_root=tmp_path) is None
    before = state.load_state(thread_id, temp_root=tmp_path)
    assert before is not None
    capacity_before = [
        event for event in before["accounting_refs"] if event.get("kind") == "host_capacity_observation"
    ]
    assert len(capacity_before) == 1
    assert capacity_before[0]["resident_children"] == 3

    filtered_pre = pre_payload(
        thread_id,
        "tool-filtered-replace",
        tool_input={"path_prefix": "manual_a"},
    )
    result = guard.evaluate_pre_tool_use(filtered_pre, temp_root=tmp_path)
    assert result is not None
    assert result["decision"] == "block"

    after = state.load_state(thread_id, temp_root=tmp_path)
    assert after is not None
    capacity_after = [
        event for event in after["accounting_refs"] if event.get("kind") == "host_capacity_observation"
    ]
    assert capacity_after == capacity_before


def test_filtered_list_agents_cannot_authorize_fresh_spawn(tmp_path: Path):
    state = load_module("scope_spawn_state", "dispatch_state_v4.py")
    graph = load_module("scope_spawn_graph", "work_graph_v4.py")
    host = load_module("scope_spawn_host", "host_capabilities.py")
    scheduler = load_module("scope_spawn_scheduler", "scheduler_v4.py")
    guard = load_module("scope_spawn_guard", "orchestration_guard.py")
    thread_id = "thread-scope-spawn"
    state.write_state(
        make_state(state, graph, thread_id=thread_id, ready=True),
        temp_root=tmp_path,
    )

    filtered_pre = pre_payload(
        thread_id,
        "tool-filtered-spawn",
        tool_input={"path_prefix": "manual_a"},
    )
    result = guard.evaluate_pre_tool_use(filtered_pre, temp_root=tmp_path)
    assert result is not None
    assert result["decision"] == "block"

    current = state.load_state(thread_id, temp_root=tmp_path)
    assert current is not None
    assert not any(
        event.get("kind") == "host_capacity_observation"
        for event in current["accounting_refs"]
    )
    snapshot = host.normalize_host_capabilities(
        {
            "surface": "multi_agent_v2",
            "tools": ["spawn_agent", "followup_task", "interrupt_agent", "list_agents", "wait_agent"],
            "hooks": {
                "PreToolUse": ["spawn_agent", "followup_task", "interrupt_agent", "list_agents"],
                "PostToolUse": ["spawn_agent", "followup_task", "interrupt_agent", "list_agents"],
                "SubagentStop": True,
            },
            "fork_turns_none": True,
            "max_spawned_threads": 3,
        }
    )
    decision = scheduler.scheduler_decision(
        current,
        capability_snapshot=snapshot,
        wakeup_reason="USER_INPUT",
    )
    assert decision["actions"] == []
    assert decision["launch_budget"] == 0
