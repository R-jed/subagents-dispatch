from __future__ import annotations

import copy
import importlib.util
import json
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


def raw_host_evidence(*, capacity: int = 3) -> dict:
    lifecycle = ["spawn_agent", "followup_task", "interrupt_agent"]
    guarded = lifecycle + ["list_agents"]
    return {
        "surface": "multi_agent_v2",
        "tools": lifecycle + ["list_agents", "wait_agent"],
        "hooks": {
            "PreToolUse": guarded,
            "PostToolUse": guarded,
            "SubagentStop": True,
        },
        "fork_turns_none": True,
        "max_spawned_threads": capacity,
    }


def work_unit(unit_id: str, *, state_name: str = "READY") -> dict:
    return {
        "unit_id": unit_id,
        "intent": "inspect",
        "goal": f"inspect {unit_id}",
        "output": "facts",
        "depends_on": [],
        "state": state_name,
        "ownership": {"write": [], "forbidden": []},
        "authority_ceiling": "none",
        "write_scope_ceiling": [],
        "done_when": "Main verifies facts",
        "accepted_result_ref": None,
        "accepted_execution_id": None,
        "accepted_control_epoch": None,
    }


def execution(
    unit_id: str,
    *,
    execution_id: str,
    task_name: str,
    lifecycle: str = "RUNNING",
) -> dict:
    return {
        "execution_id": execution_id,
        "unit_id": unit_id,
        "team_plan_revision": 1,
        "attempt_no": 1,
        "profile_id": "reader",
        "agent_id": f"agent-{execution_id}",
        "native_task_name": task_name,
        "model": "gpt-5.6-luna",
        "effort": "max",
        "granted_authority": "none",
        "granted_write_scope": [],
        "workspace_id": "canonical",
        "lifecycle": lifecycle,
        "control_epoch": 0,
        "followup_count": 0,
        "failure_origin": "none",
        "blocker": "none",
        "quarantine_reason": None,
    }


def accepted_unit(unit_id: str, execution_id: str) -> dict:
    unit = work_unit(unit_id, state_name="ACCEPTED")
    unit["accepted_result_ref"] = f"result:{unit_id.lower()}"
    unit["accepted_execution_id"] = execution_id
    unit["accepted_control_epoch"] = 0
    return unit


def completed_proof(execution_id: str) -> dict:
    return {
        "ref": f"host-observation:{execution_id}",
        "kind": "host_observation",
        "source": "post_tool_use:list_agents",
        "execution_id": execution_id,
        "control_epoch": 0,
        "lease_epoch": None,
        "lifecycle": "COMPLETED",
    }


def capacity_observation(
    *,
    resident: int,
    settled: int,
    managed: int,
    unmanaged: int,
) -> dict:
    return {
        "ref": "host-capacity-observation:tool-capacity-1",
        "kind": "host_capacity_observation",
        "source": "post_tool_use:list_agents",
        "turn_id": "turn-capacity-1",
        "tool_use_id": "tool-capacity-1",
        "resident_children": resident,
        "settled_children": settled,
        "active_children": resident - settled,
        "managed_resident_children": managed,
        "unmanaged_resident_children": unmanaged,
        "response_digest": "a" * 64,
    }


def official_list_agents_wire(agents: list[dict]) -> str:
    # Current official Codex V2 list_agents uses generic FunctionToolOutput
    # fallback for PostToolUse. The hook response is therefore the text body,
    # whose contents are serialized ListAgentsResult JSON.
    return json.dumps({"agents": agents}, separators=(",", ":"))


def test_current_official_list_agents_hook_wire_is_accepted(tmp_path: Path):
    state = load_module("rc4_wire_state", "dispatch_state_v4.py")
    guard = load_module("rc4_wire_guard", "orchestration_guard.py")

    payload = state.new_state(thread_id="thread-rc4-wire")
    payload["team_plan_revision"] = 1
    payload["work_units"] = [work_unit("U1", state_name="EXECUTING")]
    payload["executions"] = [
        execution("U1", execution_id="exec_1", task_name="sd_u1_a1")
    ]
    state.write_state(payload, temp_root=tmp_path)

    pre = {
        "hook_event_name": "PreToolUse",
        "session_id": "thread-rc4-wire",
        "turn_id": "turn-observe-1",
        "tool_name": "list_agents",
        "tool_use_id": "tool-observe-1",
        "tool_input": {},
    }
    post = {
        **pre,
        "hook_event_name": "PostToolUse",
        "tool_response": official_list_agents_wire(
            [
                {
                    "agent_name": "/root/sd_u1_a1",
                    "agent_status": {"completed": "done"},
                }
            ]
        ),
    }

    assert guard.evaluate_pre_tool_use(pre, temp_root=tmp_path) is None
    assert guard.evaluate_post_tool_use(post, temp_root=tmp_path) is None
    current = state.load_state("thread-rc4-wire", temp_root=tmp_path)
    assert current is not None
    assert current["executions"][0]["lifecycle"] == "COMPLETED"
    capacity = [
        event
        for event in current["accounting_refs"]
        if event.get("kind") == "host_capacity_observation"
    ]
    assert len(capacity) == 1
    assert capacity[0]["resident_children"] == 1
    assert capacity[0]["settled_children"] == 1


def test_legacy_invented_bare_list_host_wire_is_rejected(tmp_path: Path):
    state = load_module("rc4_legacy_wire_state", "dispatch_state_v4.py")
    guard = load_module("rc4_legacy_wire_guard", "orchestration_guard.py")

    payload = state.new_state(thread_id="thread-rc4-legacy-wire")
    payload["team_plan_revision"] = 1
    payload["work_units"] = [work_unit("U1", state_name="EXECUTING")]
    payload["executions"] = [
        execution("U1", execution_id="exec_1", task_name="sd_u1_a1")
    ]
    state.write_state(payload, temp_root=tmp_path)

    pre = {
        "hook_event_name": "PreToolUse",
        "session_id": "thread-rc4-legacy-wire",
        "turn_id": "turn-observe-1",
        "tool_name": "list_agents",
        "tool_use_id": "tool-observe-1",
        "tool_input": {},
    }
    post = {
        **pre,
        "hook_event_name": "PostToolUse",
        "tool_response": [
            {"agent_name": "/root/sd_u1_a1", "status": {"completed": "done"}}
        ],
    }
    assert guard.evaluate_pre_tool_use(pre, temp_root=tmp_path) is None
    result = guard.evaluate_post_tool_use(post, temp_root=tmp_path)
    assert result is not None
    assert result["continue"] is False


def test_execution_binding_rejects_host_invalid_native_task_name():
    state = load_module("rc4_name_state", "dispatch_state_v4.py")
    payload = state.new_state(thread_id="thread-rc4-name")
    payload["team_plan_revision"] = 1
    payload["work_units"] = [work_unit("U1", state_name="EXECUTING")]
    payload["executions"] = [
        execution("U1", execution_id="exec_1", task_name="sd-u1-a1")
    ]
    with pytest.raises(state.StatePayloadError, match="native_task_name|agent name|Host"):
        state.validate_state_payload(payload)


@pytest.mark.parametrize("bad_name", ["sd-u1-a1", "BadName", "root", "a/b", " a "])
def test_allocate_execution_rejects_host_invalid_task_names(tmp_path: Path, bad_name: str):
    state = load_module(f"rc4_allocate_state_{bad_name!r}", "dispatch_state_v4.py")
    lifecycle = load_module(f"rc4_allocate_lifecycle_{bad_name!r}", "execution_lifecycle_v4.py")
    payload = state.new_state(thread_id="thread-rc4-allocate")
    payload["team_plan_revision"] = 1
    payload["work_units"] = [work_unit("U1")]
    state.write_state(payload, temp_root=tmp_path)

    with pytest.raises(Exception, match="native_task_name|agent name|Host"):
        lifecycle.allocate_execution(
            "thread-rc4-allocate",
            unit_id="U1",
            execution_id="exec_1",
            native_task_name=bad_name,
            profile_id="reader",
            granted_authority="none",
            temp_root=tmp_path,
        )


def test_scheduler_blocks_when_unmanaged_host_occupancy_consumes_last_slot():
    state = load_module("rc4_mixed_state", "dispatch_state_v4.py")
    host = load_module("rc4_mixed_host", "host_capabilities.py")
    scheduler = load_module("rc4_mixed_scheduler", "scheduler_v4.py")

    payload = state.new_state(thread_id="thread-rc4-mixed")
    payload["team_plan_revision"] = 1
    payload["work_units"] = [
        accepted_unit("U0", "exec_0"),
        work_unit("U1", state_name="EXECUTING"),
        work_unit("U2", state_name="EXECUTING"),
        work_unit("U3"),
    ]
    payload["executions"] = [
        execution("U0", execution_id="exec_0", task_name="sd_u0_a1", lifecycle="CLOSED"),
        execution("U1", execution_id="exec_1", task_name="sd_u1_a1"),
        execution("U2", execution_id="exec_2", task_name="sd_u2_a1"),
    ]
    payload["accounting_refs"] = [
        completed_proof("exec_0"),
        capacity_observation(resident=3, settled=0, managed=2, unmanaged=1),
    ]
    state.validate_state_payload(payload)
    snapshot = host.normalize_host_capabilities(raw_host_evidence(capacity=3))

    decision = scheduler.scheduler_decision(
        payload,
        capability_snapshot=snapshot,
        wakeup_reason="AGENT_UPDATE",
    )
    assert decision["occupied_host_residents"] == 3
    assert decision["unmanaged_host_residents"] == 1
    assert decision["actions"] == []
    assert decision["stop_reason"] == "host_capacity_full"


def test_scheduler_can_attempt_one_host_reclaim_after_three_settled_residents():
    state = load_module("rc4_reclaim_state", "dispatch_state_v4.py")
    host = load_module("rc4_reclaim_host", "host_capabilities.py")
    scheduler = load_module("rc4_reclaim_scheduler", "scheduler_v4.py")

    payload = state.new_state(thread_id="thread-rc4-reclaim")
    payload["team_plan_revision"] = 1
    payload["work_units"] = [
        accepted_unit("U1", "exec_1"),
        accepted_unit("U2", "exec_2"),
        accepted_unit("U3", "exec_3"),
        work_unit("U4"),
    ]
    payload["executions"] = [
        execution("U1", execution_id="exec_1", task_name="sd_u1_a1", lifecycle="COMPLETED"),
        execution("U2", execution_id="exec_2", task_name="sd_u2_a1", lifecycle="COMPLETED"),
        execution("U3", execution_id="exec_3", task_name="sd_u3_a1", lifecycle="COMPLETED"),
    ]
    payload["accounting_refs"] = [
        capacity_observation(resident=3, settled=3, managed=3, unmanaged=0)
    ]
    state.validate_state_payload(payload)
    snapshot = host.normalize_host_capabilities(raw_host_evidence(capacity=3))

    decision = scheduler.scheduler_decision(
        payload,
        capability_snapshot=snapshot,
        wakeup_reason="AGENT_COMPLETED",
    )
    assert decision["active_managed_executions"] == 0
    assert decision["occupied_host_residents"] == 3
    assert decision["host_reclaim_attempt"] is True
    assert decision["launch_budget"] == 1
    assert [item["unit_id"] for item in decision["actions"]] == ["U4"]


def test_scheduler_rejects_caller_shaped_inconsistent_normalized_snapshot():
    state = load_module("rc4_snapshot_state", "dispatch_state_v4.py")
    scheduler = load_module("rc4_snapshot_scheduler", "scheduler_v4.py")

    payload = state.new_state(thread_id="thread-rc4-snapshot")
    payload["team_plan_revision"] = 1
    payload["work_units"] = [work_unit("U1")]
    forged = {
        "surface": "multi_agent_v2",
        "capabilities": {
            "spawn": True,
            "observe": True,
            "wait_or_wakeup": True,
            "followup": True,
            "interrupt": True,
            "pre_tool_use_guard": True,
            "post_tool_use_guard": True,
            "subagent_stop_veto": True,
        },
        "fork_turns_none": True,
        "max_spawned_threads": 3,
        "capacity_excludes_primary": True,
        "execution_ready": True,
        "missing": [],
    }
    with pytest.raises(scheduler.SchedulerError, match="normalized|snapshot|host_observation_guard"):
        scheduler.scheduler_decision(
            payload,
            capability_snapshot=forged,
            wakeup_reason="USER_INPUT",
        )


def test_release_identity_binds_machine_readable_host_contract_digest():
    release = load_module("rc4_release_contract", "release_evidence_v4.py")
    identity = release.current_candidate_identity(ROOT)
    assert release.HOST_CAMPAIGN_CONTRACT_VERSION == "4.0.0-host-smoke-7"
    assert "host_contract_sha256" in identity
    assert len(identity["host_contract_sha256"]) == 64
