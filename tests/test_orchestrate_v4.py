from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
POLICY = ROOT / "contracts" / "policy.json"
ORCHESTRATE_SKILL = ROOT / "skills" / "orchestrate" / "SKILL.md"


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


def install_spawn_pending_reader(tmp_path: Path):
    state = load_module("orch_state_spawn", "dispatch_state_v4.py")
    graph = load_module("orch_graph_spawn", "work_graph_v4.py")
    lifecycle = load_module("orch_lifecycle_spawn", "execution_lifecycle_v4.py")
    state.write_state(state.new_state(thread_id="thread-spawn"), temp_root=tmp_path)
    unit = graph.make_work_unit(
        unit_id="U1",
        intent="inspect",
        goal="inspect one bounded target",
        output="evidence",
        done_when="Main can verify the evidence",
        interfaces=["README_AI.md"],
        invariants=["repository remains unchanged"],
        decision_boundary="Return only bounded evidence to Main.",
        stop_boundary="Stop and report any scope or safety blocker to Main.",
    )
    graph.install_work_graph("thread-spawn", units=[unit], temp_root=tmp_path)
    lifecycle.allocate_execution(
        "thread-spawn",
        unit_id="U1",
        execution_id="exec-1",
        native_task_name="sd_u1_a1",
        role_id="programmer", reasoning_effort="max",
        granted_authority="none",
        temp_root=tmp_path,
    )
    return state


def install_running_reader(tmp_path: Path):
    state = load_module("orch_state_running", "dispatch_state_v4.py")
    graph = load_module("orch_graph_running", "work_graph_v4.py")
    lifecycle = load_module("orch_lifecycle_running", "execution_lifecycle_v4.py")
    state.write_state(state.new_state(thread_id="thread-control"), temp_root=tmp_path)
    unit = graph.make_work_unit(
        unit_id="U1", intent="inspect", goal="inspect one bounded target", output="evidence", done_when="Main can verify the evidence"
    )
    graph.install_work_graph("thread-control", units=[unit], temp_root=tmp_path)
    lifecycle.allocate_execution(
        "thread-control", unit_id="U1", execution_id="exec-1", native_task_name="sd_u1_a1", role_id="programmer", reasoning_effort="max", granted_authority="none", temp_root=tmp_path
    )
    basis = lifecycle.fresh_observation_basis("thread-control", execution_id="exec-1", temp_root=tmp_path)
    lifecycle.persist_host_observation(
        "thread-control", basis=basis, host_state="running", agent_id="agent-1", temp_root=tmp_path
    )
    return state


def test_orchestrate_and_doctor_are_the_public_surface():
    skills = sorted(path.name for path in (ROOT / "skills").iterdir() if path.is_dir())
    assert skills == ["doctor", "orchestrate"]


def test_main_selects_one_managed_role_and_policy_exact_route():
    orchestrate = load_module("orch_explicit_role", "orchestrate_v4.py")
    roles = json.loads(POLICY.read_text(encoding="utf-8"))["roles"]
    selections = {
        "programmer": "max",
        "product_manager": "medium",
        "department_director": "high",
    }
    for role_id, effort in selections.items():
        selected = orchestrate.select_role(
            role_id=role_id, intent="bounded work", reasoning_effort=effort
        )
        assert selected["role_id"] == role_id
        assert selected["agent_type"] == roles[role_id]["agent_type"]
        assert selected["model"] == roles[role_id]["model"]
        assert selected["reasoning_effort"] == effort
    with pytest.raises(orchestrate.OrchestrateError, match="unknown managed role"):
        orchestrate.select_role(
            role_id="automatic-best-agent", intent="work", reasoning_effort="high"
        )


def test_orchestrate_skill_names_every_exact_managed_agent_type():
    roles = json.loads(POLICY.read_text(encoding="utf-8"))["roles"]
    text = ORCHESTRATE_SKILL.read_text(encoding="utf-8")
    for role_id in ("programmer", "product_manager", "department_director"):
        assert f"`{roles[role_id]['agent_type']}`" in text
    assert "Never substitute" in text
    assert "another role, another model, or another effort" in text
    assert "prepare_managed_spawn" in text
    assert "Do not handwrite" in text


def test_prepare_managed_spawn_owns_exact_host_payload(tmp_path: Path):
    state = install_spawn_pending_reader(tmp_path)
    orchestrate = load_module("orch_spawn", "orchestrate_v4.py")
    before = state.load_state("thread-spawn", temp_root=tmp_path)

    prepared = orchestrate.prepare_managed_spawn(
        "thread-spawn",
        orchestration_id="thread-spawn",
        execution_id="exec-1",
        temp_root=tmp_path,
    )

    assert prepared["operation"] == "SPAWN"
    assert prepared["execution_id"] == "exec-1"
    tool_input = prepared["tool_input"]
    assert set(tool_input) == {"task_name", "message", "agent_type", "model", "reasoning_effort", "fork_turns"}
    assert tool_input["task_name"] == "sd_u1_a1"
    assert tool_input["agent_type"] == "subagents_dispatch_programmer"
    assert tool_input["model"] == "gpt-5.6-luna"
    assert tool_input["reasoning_effort"] == "max"
    assert tool_input["fork_turns"] == "none"
    assert isinstance(tool_input["message"], str) and tool_input["message"]
    packet = json.loads(tool_input["message"])
    assert packet["objective"]["goal"] == "inspect one bounded target"
    assert state.load_state("thread-spawn", temp_root=tmp_path) == before


def test_prepare_managed_spawn_rejects_wrong_orchestration(tmp_path: Path):
    install_spawn_pending_reader(tmp_path)
    orchestrate = load_module("orch_spawn_wrong_session", "orchestrate_v4.py")
    with pytest.raises(orchestrate.OrchestrateError, match="active orchestration"):
        orchestrate.prepare_managed_spawn(
            "thread-spawn",
            orchestration_id="wrong-thread",
            execution_id="exec-1",
            temp_root=tmp_path,
        )


def test_plan_only_requires_explicit_profile_and_never_creates_runtime_state(tmp_path: Path):
    orchestrate = load_module("orch_plan", "orchestrate_v4.py")
    state = load_module("orch_plan_state", "dispatch_state_v4.py")
    preview = orchestrate.plan_only_preview(
        goal="plan a safe change",
        responsibilities=[
            {"intent": "inspect", "goal": "map code", "role_id": "programmer", "reasoning_effort": "max"},
            {"intent": "implement", "goal": "change code", "role_id": "programmer", "reasoning_effort": "max"},
        ],
    )
    assert preview["mode"] == "PLAN_ONLY"
    assert preview["state_created"] is False
    assert preview["writer_lease_acquired"] is False
    assert preview["host_actions"] == []
    assert [item["route"]["role_id"] for item in preview["work_units"]] == ["programmer", "programmer"]
    assert state.load_state("thread-plan", temp_root=tmp_path) is None
    with pytest.raises(orchestrate.OrchestrateError, match="explicit role_id"):
        orchestrate.plan_only_preview(
            goal="ambiguous role",
            responsibilities=[{"intent": "inspect", "goal": "map code"}],
        )


def test_unrelated_request_cannot_attach_to_active_orchestration(tmp_path: Path):
    orchestrate = load_module("orch_admission", "orchestrate_v4.py")
    state = load_module("orch_admission_state", "dispatch_state_v4.py")
    graph = load_module("orch_admission_graph", "work_graph_v4.py")
    state.write_state(state.new_state(thread_id="thread-active"), temp_root=tmp_path)
    unit = graph.make_work_unit(
        unit_id="U1", intent="inspect", goal="active work", output="evidence", done_when="accepted"
    )
    graph.install_work_graph("thread-active", units=[unit], temp_root=tmp_path)
    blocked = orchestrate.admission_decision(
        "thread-active", orchestration_id=None, new_task=True, temp_root=tmp_path
    )
    assert blocked["decision"] == "BLOCK_ACTIVE_ORCHESTRATION"
    resumed = orchestrate.admission_decision(
        "thread-active", orchestration_id="thread-active", new_task=False, temp_root=tmp_path
    )
    assert resumed["decision"] == "RESUME_ALLOWED"


def test_status_is_state_projection_not_a_launch_plan(tmp_path: Path):
    orchestrate = load_module("orch_status", "orchestrate_v4.py")
    state = load_module("orch_status_state", "dispatch_state_v4.py")
    graph = load_module("orch_status_graph", "work_graph_v4.py")
    state.write_state(state.new_state(thread_id="thread-status"), temp_root=tmp_path)
    units = [
        graph.make_work_unit(unit_id="U1", intent="inspect", goal="root", output="evidence", done_when="accepted"),
        graph.make_work_unit(unit_id="U2", intent="review", goal="dependent", output="verdict", depends_on=["U1"], done_when="accepted"),
    ]
    graph.install_work_graph("thread-status", units=units, temp_root=tmp_path)
    view = orchestrate.status_view(
        "thread-status", orchestration_id="thread-status", temp_root=tmp_path
    )
    assert view["selection_owner"] == "main"
    assert view["product_child_limit"] == 4
    assert any(item["unit_id"] == "U2" for item in view["waiting"])
    assert any(item["kind"] == "dependency" and item["unit_id"] == "U2" for item in view["blockers"])


def test_reconcile_returns_constraints_without_selecting_work(tmp_path: Path):
    orchestrate = load_module("orch_reconcile", "orchestrate_v4.py")
    state = load_module("orch_reconcile_state", "dispatch_state_v4.py")
    graph = load_module("orch_reconcile_graph", "work_graph_v4.py")
    host = load_module("orch_reconcile_host", "host_capabilities.py")
    state.write_state(state.new_state(thread_id="thread-reconcile"), temp_root=tmp_path)
    unit = graph.make_work_unit(
        unit_id="U1", intent="inspect", goal="read", output="evidence", done_when="accepted"
    )
    graph.install_work_graph("thread-reconcile", units=[unit], temp_root=tmp_path)
    snapshot = host.normalize_host_capabilities({
        "surface": "multi_agent_v2",
        "tools": ["spawn_agent", "followup_task", "interrupt_agent", "list_agents", "wait_agent"],
        "fork_turns_none": True,
        "managed_child_containment": "verified",
        "max_concurrent_threads_per_session": 4,
    })
    decision = orchestrate.reconcile_once(
        "thread-reconcile", orchestration_id="thread-reconcile", capability_snapshot=snapshot,
        wakeup_reason="USER_INPUT", temp_root=tmp_path
    )
    assert decision["selection_owner"] == "main"
    assert decision["ready_frontier"] == ["U1"]
    assert decision["actions"] == []
    assert decision["host_session_capacity"] == 4
    assert decision["available_launch_slots"] == 3


def test_running_steer_is_transient(tmp_path: Path):
    state = install_running_reader(tmp_path)
    orchestrate = load_module("orch_steer", "orchestrate_v4.py")
    before = state.load_state("thread-control", temp_root=tmp_path)
    prepared = orchestrate.prepare_steer(
        "thread-control", orchestration_id="thread-control", execution_id="exec-1",
        tool_input={"target": "/root/sd_u1_a1", "message": "Focus on the pagination boundary."},
        temp_root=tmp_path,
    )
    assert prepared["operation"] == "STEER"
    assert prepared["tool_input"]["target"] == "/root/sd_u1_a1"
    assert state.load_state("thread-control", temp_root=tmp_path) == before


def test_completed_correction_threads_explicit_recovery_basis(tmp_path: Path):
    state = install_running_reader(tmp_path)
    lifecycle = load_module("orch_lifecycle_correction", "execution_lifecycle_v4.py")
    completion_basis = lifecycle.fresh_observation_basis(
        "thread-control", execution_id="exec-1", temp_root=tmp_path
    )
    lifecycle.persist_host_observation(
        "thread-control",
        basis=completion_basis,
        host_state="completed",
        agent_id="agent-1",
        temp_root=tmp_path,
    )
    orchestrate = load_module("orch_correction", "orchestrate_v4.py")
    prepared = orchestrate.prepare_correction(
        "thread-control",
        orchestration_id="thread-control",
        execution_id="exec-1",
        tool_input={"target": "/root/sd_u1_a1", "message": "Correct the verified edge case."},
        correction_basis_ref="correction:verified-edge-case",
        temp_root=tmp_path,
    )

    assert prepared["operation"] == "FOLLOWUP"
    assert prepared["tool_input"]["target"] == "/root/sd_u1_a1"
    current = state.load_state("thread-control", temp_root=tmp_path)
    assert current is not None
    execution = next(item for item in current["executions"] if item["execution_id"] == "exec-1")
    assert execution["lifecycle"] == "SPAWN_PENDING"
    assert execution["followup_count"] == 1
