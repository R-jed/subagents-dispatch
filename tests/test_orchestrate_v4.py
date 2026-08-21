from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
POLICY = ROOT / "contracts" / "policy.json"


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


def install_read_execution(tmp_path: Path, *, host_state: str):
    state = load_module(f"p7_state_control_{host_state}", "dispatch_state_v4.py")
    graph = load_module(f"p7_graph_control_{host_state}", "work_graph_v4.py")
    lifecycle = load_module(f"p7_lifecycle_control_{host_state}", "execution_lifecycle_v4.py")
    state.write_state(state.new_state(thread_id="thread-control"), temp_root=tmp_path)
    unit = graph.make_work_unit(
        unit_id="U1",
        intent="inspect",
        goal="inspect one bounded target",
        output="evidence",
        done_when="Main can verify the evidence",
    )
    graph.install_single_work_unit("thread-control", unit=unit, temp_root=tmp_path)
    lifecycle.allocate_execution(
        "thread-control",
        unit_id="U1",
        execution_id="exec-1",
        native_task_name="sd_u1_a1",
        profile_id="reader",
        granted_authority="none",
        temp_root=tmp_path,
    )
    basis = lifecycle.fresh_observation_basis(
        "thread-control", execution_id="exec-1", temp_root=tmp_path
    )
    lifecycle.persist_host_observation(
        "thread-control",
        basis=basis,
        host_state="running",
        agent_id="agent-1",
        temp_root=tmp_path,
    )
    if host_state != "running":
        basis = lifecycle.fresh_observation_basis(
            "thread-control", execution_id="exec-1", temp_root=tmp_path
        )
        lifecycle.persist_host_observation(
            "thread-control",
            basis=basis,
            host_state=host_state,
            agent_id="agent-1",
            temp_root=tmp_path,
        )
    return state, lifecycle


def test_orchestrate_and_doctor_are_the_final_public_surface():
    skills = sorted(path.name for path in (ROOT / "skills").iterdir() if path.is_dir())
    assert skills == ["doctor", "orchestrate"]


def test_fixed_profile_routing_uses_the_policy_model_effort_contract():
    orchestrate = load_module("p7_orchestrate_routes", "orchestrate_v4.py")
    roles = json.loads(POLICY.read_text(encoding="utf-8"))["roles"]
    cases = [
        ({"intent": "inspect"}, "reader"),
        ({"intent": "implement", "requires_write": True}, "worker"),
        ({"intent": "investigate", "broad_investigation": True}, "investigator"),
        ({"intent": "solve", "stalled_or_high_judgment": True, "requires_write": True}, "solver"),
        ({"intent": "review", "review": True}, "advisor"),
    ]
    for kwargs, profile_id in cases:
        route = orchestrate.route_profile(**kwargs)
        spec = roles[profile_id]
        assert route["profile_id"] == profile_id
        assert route["model"] == spec["model"]
        assert route["effort"] == spec["effort"]


def test_plan_only_does_not_create_state_or_lease(tmp_path: Path):
    orchestrate = load_module("p7_orchestrate_plan", "orchestrate_v4.py")
    state = load_module("p7_state_plan", "dispatch_state_v4.py")
    preview = orchestrate.plan_only_preview(
        goal="plan a safe change",
        responsibilities=[
            {"intent": "inspect", "goal": "map code"},
            {"intent": "implement", "goal": "change code", "requires_write": True},
        ],
    )
    assert preview["mode"] == "PLAN_ONLY"
    assert preview["state_created"] is False
    assert preview["writer_lease_acquired"] is False
    assert preview["host_actions"] == []
    assert state.load_state("thread-plan", temp_root=tmp_path) is None
    assert not (tmp_path / "subagents-dispatch").exists()


def test_unrelated_request_cannot_silently_attach_to_active_orchestration(tmp_path: Path):
    orchestrate = load_module("p7_orchestrate_admission", "orchestrate_v4.py")
    state = load_module("p7_state_admission", "dispatch_state_v4.py")
    graph = load_module("p7_graph_admission", "work_graph_v4.py")
    state.write_state(state.new_state(thread_id="thread-active"), temp_root=tmp_path)
    unit = graph.make_work_unit(
        unit_id="U1", intent="inspect", goal="active work", output="evidence", done_when="accepted"
    )
    graph.install_work_graph("thread-active", team_plan_revision=1, units=[unit], temp_root=tmp_path)
    blocked = orchestrate.admission_decision(
        "thread-active", orchestration_id=None, new_task=True, temp_root=tmp_path
    )
    assert blocked["decision"] == "BLOCK_ACTIVE_ORCHESTRATION"
    assert blocked["requires_explicit_target"] is True
    resumed = orchestrate.admission_decision(
        "thread-active", orchestration_id="thread-active", new_task=False, temp_root=tmp_path
    )
    assert resumed["decision"] == "RESUME_ALLOWED"


def test_control_operations_require_exact_active_orchestration_id(tmp_path: Path):
    orchestrate = load_module("p7_orchestrate_target", "orchestrate_v4.py")
    state = load_module("p7_state_target", "dispatch_state_v4.py")
    state.write_state(state.new_state(thread_id="thread-target"), temp_root=tmp_path)
    with pytest.raises(orchestrate.OrchestrateError, match="does not target"):
        orchestrate.require_control_session(
            "thread-target", orchestration_id="other-thread", temp_root=tmp_path
        )
    current = orchestrate.require_control_session(
        "thread-target", orchestration_id="thread-target", temp_root=tmp_path
    )
    assert current["root_session_id"] == "thread-target"


def test_status_view_surfaces_waiting_blockers_writer_and_acceptance(tmp_path: Path):
    orchestrate = load_module("p7_orchestrate_status", "orchestrate_v4.py")
    state = load_module("p7_state_status", "dispatch_state_v4.py")
    graph = load_module("p7_graph_status", "work_graph_v4.py")
    state.write_state(state.new_state(thread_id="thread-status"), temp_root=tmp_path)
    units = [
        graph.make_work_unit(unit_id="U1", intent="inspect", goal="root", output="evidence", done_when="accepted"),
        graph.make_work_unit(unit_id="U2", intent="review", goal="dependent", output="verdict", depends_on=["U1"], done_when="accepted"),
    ]
    graph.install_work_graph("thread-status", team_plan_revision=1, units=units, temp_root=tmp_path)
    view = orchestrate.status_view(
        "thread-status", orchestration_id="thread-status", temp_root=tmp_path
    )
    assert view["orchestration_id"] == "thread-status"
    assert any(item["unit_id"] == "U2" for item in view["waiting"])
    assert any(item["kind"] == "dependency" and item["unit_id"] == "U2" for item in view["blockers"])
    assert view["writer_lease"] is None
    assert {item["unit_id"] for item in view["acceptance"]} == {"U1", "U2"}


def test_running_steer_is_transient_and_does_not_spend_correction_generation(tmp_path: Path):
    state, _lifecycle = install_read_execution(tmp_path, host_state="running")
    orchestrate = load_module("p7_orchestrate_steer", "orchestrate_v4.py")
    before = state.load_state("thread-control", temp_root=tmp_path)
    assert before is not None

    prepared = orchestrate.prepare_steer(
        "thread-control",
        orchestration_id="thread-control",
        execution_id="exec-1",
        tool_input={"target": "sd_u1_a1", "message": "Focus on the pagination boundary."},
        temp_root=tmp_path,
    )
    after = state.load_state("thread-control", temp_root=tmp_path)

    assert prepared["operation"] == "STEER"
    assert prepared["control_epoch"] == 0
    assert prepared["observation_basis"] == {
        "execution_id": "exec-1",
        "control_epoch": 0,
        "lease_epoch": None,
    }
    assert after == before
    assert after["executions"][0]["followup_count"] == 0
    assert after["executions"][0]["lifecycle"] == "RUNNING"


def test_completed_execution_cannot_be_mislabeled_as_running_steer(tmp_path: Path):
    state, _lifecycle = install_read_execution(tmp_path, host_state="completed")
    orchestrate = load_module("p7_orchestrate_steer_completed", "orchestrate_v4.py")
    before = state.load_state("thread-control", temp_root=tmp_path)

    with pytest.raises(orchestrate.OrchestrateError, match="RUNNING"):
        orchestrate.prepare_steer(
            "thread-control",
            orchestration_id="thread-control",
            execution_id="exec-1",
            tool_input={"target": "sd_u1_a1", "message": "Try one correction."},
            temp_root=tmp_path,
        )

    assert state.load_state("thread-control", temp_root=tmp_path) == before


def test_correction_uses_completed_same_child_followup_and_spends_one_budget(tmp_path: Path):
    state, _lifecycle = install_read_execution(tmp_path, host_state="completed")
    orchestrate = load_module("p7_orchestrate_correction", "orchestrate_v4.py")

    prepared = orchestrate.prepare_correction(
        "thread-control",
        orchestration_id="thread-control",
        execution_id="exec-1",
        tool_input={"target": "sd_u1_a1", "message": "Correct the one failed acceptance point."},
        temp_root=tmp_path,
    )
    current = state.load_state("thread-control", temp_root=tmp_path)
    assert current is not None
    execution = current["executions"][0]

    assert prepared["operation"] == "FOLLOWUP"
    assert execution["lifecycle"] == "SPAWN_PENDING"
    assert execution["control_epoch"] == 1
    assert execution["followup_count"] == 1


def test_continue_reactivates_interrupted_child_without_spending_correction_budget(tmp_path: Path):
    state, _lifecycle = install_read_execution(tmp_path, host_state="interrupted")
    orchestrate = load_module("p7_orchestrate_continue", "orchestrate_v4.py")

    prepared = orchestrate.prepare_continue(
        "thread-control",
        orchestration_id="thread-control",
        execution_id="exec-1",
        tool_input={"target": "sd_u1_a1", "message": "Continue the same bounded responsibility."},
        temp_root=tmp_path,
    )
    current = state.load_state("thread-control", temp_root=tmp_path)
    assert current is not None
    execution = current["executions"][0]

    assert prepared["operation"] == "CONTINUE"
    assert execution["lifecycle"] == "SPAWN_PENDING"
    assert execution["control_epoch"] == 1
    assert execution["followup_count"] == 0
