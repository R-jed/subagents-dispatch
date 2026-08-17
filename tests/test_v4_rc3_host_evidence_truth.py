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


def capability_evidence(*, surface: str = "multi_agent_v2", include_list_hook: bool = True) -> dict:
    lifecycle = ["spawn_agent", "followup_task", "interrupt_agent"]
    post = lifecycle + (["list_agents"] if include_list_hook else [])
    return {
        "surface": surface,
        "tools": lifecycle + ["list_agents", "wait_agent"],
        "hooks": {
            "PreToolUse": lifecycle,
            "PostToolUse": post,
            "SubagentStop": True,
        },
        "fork_turns_none": True,
        "max_spawned_threads": 3,
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
        "team_plan_revision": 1,
        "attempt_no": 1,
        "profile_id": "reader",
        "agent_id": "agent-id-1",
        "native_task_name": "sd-u1-a1",
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
    payload["team_plan_revision"] = 1
    payload["work_units"] = [work_unit()]
    payload["executions"] = [execution()]
    state.write_state(payload, temp_root=tmp_path)


def list_agents_post(*, status: object = "running", session_id: str = "thread-host") -> dict:
    return {
        "hook_event_name": "PostToolUse",
        "session_id": session_id,
        "turn_id": "turn-observe-1",
        "tool_name": "list_agents",
        "tool_use_id": "tool-observe-1",
        "tool_input": {},
        "tool_response": [
            {
                "agent_name": "/root/sd-u1-a1",
                "status": status,
            }
        ],
    }


def test_host_surface_must_be_exact_multi_agent_v2():
    host = load_module("rc3_host_surface", "host_capabilities.py")
    with pytest.raises(host.HostCapabilityError, match="multi_agent_v2|surface"):
        host.normalize_host_capabilities(capability_evidence(surface="multi_agent_v2-ish"))


def test_execution_ready_requires_list_agents_posttool_observation_coverage():
    host = load_module("rc3_host_observe_hook", "host_capabilities.py")
    snapshot = host.normalize_host_capabilities(capability_evidence(include_list_hook=False))
    assert snapshot["execution_ready"] is False
    assert "host_observation_guard" in snapshot["missing"]


def test_lifecycle_layer_does_not_accept_caller_supplied_host_state():
    lifecycle = load_module("rc3_host_lifecycle_public", "execution_lifecycle_v4.py")
    assert not hasattr(lifecycle, "persist_host_observation")


def test_list_agents_posttool_is_authoritative_observation_path(tmp_path: Path):
    state = load_module("rc3_host_state_ingest", "dispatch_state_v4.py")
    guard = load_module("rc3_host_guard_ingest", "orchestration_guard.py")
    install(state, tmp_path)

    assert guard.evaluate_post_tool_use(
        list_agents_post(status={"completed": "done"}), temp_root=tmp_path
    ) is None
    current = state.load_state("thread-host", temp_root=tmp_path)
    assert current is not None
    assert current["executions"][0]["lifecycle"] == "COMPLETED"
    observations = [
        event
        for event in current["accounting_refs"]
        if event.get("kind") == "host_observation"
    ]
    assert len(observations) == 1
    assert observations[0]["source"] == "post_tool_use:list_agents"
    assert observations[0]["turn_id"] == "turn-observe-1"
    assert observations[0]["tool_use_id"] == "tool-observe-1"


def test_list_agents_observation_rejects_wrong_root_session_without_mutation(tmp_path: Path):
    state = load_module("rc3_host_state_session", "dispatch_state_v4.py")
    guard = load_module("rc3_host_guard_session", "orchestration_guard.py")
    install(state, tmp_path)

    result = guard.evaluate_post_tool_use(
        list_agents_post(status={"completed": "done"}, session_id="other-root"),
        temp_root=tmp_path,
    )
    assert result is not None
    assert result["continue"] is False
    current = state.load_state("thread-host", temp_root=tmp_path)
    assert current is not None
    assert current["executions"][0]["lifecycle"] == "RUNNING"


def test_duplicate_list_agents_posttool_is_idempotent(tmp_path: Path):
    state = load_module("rc3_host_state_dup", "dispatch_state_v4.py")
    guard = load_module("rc3_host_guard_dup", "orchestration_guard.py")
    install(state, tmp_path)
    post = list_agents_post(status="running")

    assert guard.evaluate_post_tool_use(post, temp_root=tmp_path) is None
    assert guard.evaluate_post_tool_use(post, temp_root=tmp_path) is None
    current = state.load_state("thread-host", temp_root=tmp_path)
    assert current is not None
    observations = [
        event
        for event in current["accounting_refs"]
        if event.get("kind") == "host_observation"
    ]
    assert len(observations) == 1
