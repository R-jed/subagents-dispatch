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


def make_work_unit(unit_id: str, *, authority: str = "none", state_name: str = "READY") -> dict:
    scope = [] if authority == "none" else [f"src/{unit_id.lower()}.py"]
    return {
        "unit_id": unit_id,
        "intent": "inspect" if authority == "none" else "implement",
        "goal": f"complete {unit_id}",
        "output": "verified result",
        "depends_on": [],
        "state": state_name,
        "ownership": {"write": scope, "forbidden": []},
        "authority_ceiling": authority,
        "write_scope_ceiling": scope,
        "done_when": "Main verifies the result",
        "responsibility_context": {
            "interfaces": [],
            "invariants": [],
            "decision_boundary": "Escalate material decisions to Main.",
            "accepted_evidence_refs": [],
            "do_not_redo": [],
            "stop_boundary": "Stop and report blockers to Main.",
        },
        "accepted_result_ref": None,
        "accepted_execution_id": None,
        "accepted_control_epoch": None,
    }


def make_execution(
    unit_id: str,
    *,
    execution_id: str,
    profile_id: str = "reader",
    lifecycle: str = "SPAWN_PENDING",
    attempt_no: int = 1,
    control_epoch: int = 0,
) -> dict:
    authority = {
        "reader": "none",
        "worker": "bounded-source-write",
        "investigator": "none",
        "solver": "bounded-source-write",
        "advisor": "none",
    }[profile_id]
    return {
        "execution_id": execution_id,
        "unit_id": unit_id,
        "team_plan_revision": 1,
        "attempt_no": attempt_no,
        "profile_id": profile_id,
        "agent_id": None,
        "native_task_name": f"sd_{unit_id.lower()}_a{attempt_no}",
        "model": "gpt-5.6-luna",
        "effort": "max",
        "granted_authority": authority,
        "granted_write_scope": [f"src/{unit_id.lower()}.py"] if authority != "none" else [],
        "workspace_id": "canonical",
        "lifecycle": lifecycle,
        "control_epoch": control_epoch,
        "followup_count": 0,
        "failure_origin": "none",
        "blocker": "none",
        "quarantine_reason": None,
    }


def host_snapshot(capacity: int = 4) -> dict:
    host = load_module(f"runtime_host_{capacity}", "host_capabilities.py")
    return host.normalize_host_capabilities(
        {
            "surface": "multi_agent_v2",
            "tools": ["spawn_agent", "followup_task", "interrupt_agent", "list_agents", "wait_agent"],
            "fork_turns_none": True,
            "managed_child_containment": "verified",
            "max_concurrent_threads_per_session": capacity,
        }
    )


def test_reader_binding_cannot_prepare_worker_agent_type(tmp_path: Path):
    state = load_module("native_state_profile", "dispatch_state_v4.py")
    lifecycle = load_module("native_lifecycle_profile", "execution_lifecycle_v4.py")

    payload = state.new_state(thread_id="thread-profile")
    payload["team_plan_revision"] = 1
    payload["work_units"] = [make_work_unit("U1", state_name="EXECUTING")]
    payload["executions"] = [make_execution("U1", execution_id="exec-1", profile_id="reader")]
    state.write_state(payload, temp_root=tmp_path)

    mismatched = {
        "task_name": "sd_u1_a1",
        "message": "inspect only",
        "agent_type": "subagents_dispatch_worker",
        "fork_turns": "none",
    }
    with pytest.raises(Exception, match="profile|managed spawn|does not match"):
        lifecycle.prepare_spawn(
            "thread-profile",
            execution_id="exec-1",
            tool_input=mismatched,
            temp_root=tmp_path,
        )


def test_managed_spawn_requires_fork_turns_none_at_prepare_boundary(tmp_path: Path):
    state = load_module("native_state_fork", "dispatch_state_v4.py")
    lifecycle = load_module("native_lifecycle_fork", "execution_lifecycle_v4.py")

    payload = state.new_state(thread_id="thread-fork")
    payload["team_plan_revision"] = 1
    payload["work_units"] = [make_work_unit("U1", state_name="EXECUTING")]
    payload["executions"] = [make_execution("U1", execution_id="exec-1", profile_id="reader")]
    state.write_state(payload, temp_root=tmp_path)

    bad = {
        "task_name": "sd_u1_a1",
        "message": "inspect only",
        "agent_type": "subagents_dispatch_reader",
        "fork_turns": "all",
    }
    with pytest.raises(Exception, match="fresh-context|managed spawn|does not match"):
        lifecycle.prepare_spawn(
            "thread-fork",
            execution_id="exec-1",
            tool_input=bad,
            temp_root=tmp_path,
        )


def test_corrupt_accepted_state_requires_completed_current_producer():
    state = load_module("native_state_accept", "dispatch_state_v4.py")

    payload = state.new_state(thread_id="thread-accept")
    payload["team_plan_revision"] = 1
    unit = make_work_unit("U1", state_name="ACCEPTED")
    unit["accepted_result_ref"] = "result:sha256:abc"
    unit["accepted_execution_id"] = "exec-1"
    unit["accepted_control_epoch"] = 0
    payload["work_units"] = [unit]
    payload["executions"] = [
        make_execution("U1", execution_id="exec-1", profile_id="reader", lifecycle="RUNNING")
    ]

    with pytest.raises(state.StatePayloadError, match="accepted|COMPLETED|producer"):
        state.validate_state_payload(payload)


def test_old_attempt_cannot_be_accepted_after_new_attempt_exists(tmp_path: Path):
    state = load_module("native_state_attempt", "dispatch_state_v4.py")
    graph = load_module("native_graph_attempt", "work_graph_v4.py")

    payload = state.new_state(thread_id="thread-attempt")
    payload["team_plan_revision"] = 1
    payload["work_units"] = [make_work_unit("U1", state_name="RESULT_READY")]
    payload["executions"] = [
        make_execution("U1", execution_id="exec-1", lifecycle="COMPLETED", attempt_no=1),
        make_execution("U1", execution_id="exec-2", lifecycle="RUNNING", attempt_no=2),
    ]
    state.write_state(payload, temp_root=tmp_path)

    with pytest.raises(Exception, match="current|attempt|supersed"):
        graph.accept_work_unit(
            "thread-attempt",
            unit_id="U1",
            execution_id="exec-1",
            result_ref="result:old",
            control_epoch=0,
            temp_root=tmp_path,
        )


def test_constraint_snapshot_reports_remaining_slots_without_selecting_work():
    state = load_module("native_state_fanout", "dispatch_state_v4.py")
    scheduler = load_module("native_scheduler_fanout", "scheduler_v4.py")

    payload = state.new_state(thread_id="thread-fanout")
    payload["team_plan_revision"] = 1
    payload["work_units"] = [make_work_unit(f"U{i}") for i in range(1, 5)]
    payload["work_units"][0]["state"] = "EXECUTING"
    payload["executions"] = [
        make_execution("U1", execution_id="exec-1", profile_id="reader", lifecycle="RUNNING")
    ]
    state.validate_state_payload(payload)

    decision = scheduler.scheduler_decision(
        payload,
        capability_snapshot=host_snapshot(4),
        wakeup_reason="AGENT_UPDATE",
    )
    assert decision["selection_owner"] == "main"
    assert decision["host_session_capacity"] == 4
    assert decision["product_child_limit"] == 4
    assert decision["active_managed_executions"] == 1
    assert decision["available_launch_slots"] == 2
    assert decision["launch_budget"] == 2
    assert decision["actions"] == []
