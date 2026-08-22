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


def install_running_reader(tmp_path: Path):
    state = load_module("orch_state_running", "dispatch_state_v4.py")
    graph = load_module("orch_graph_running", "work_graph_v4.py")
    lifecycle = load_module("orch_lifecycle_running", "execution_lifecycle_v4.py")
    state.write_state(state.new_state(thread_id="thread-control"), temp_root=tmp_path)
    unit = graph.make_work_unit(
        unit_id="U1", intent="inspect", goal="inspect one bounded target", output="evidence", done_when="Main can verify the evidence"
    )
    graph.install_single_work_unit("thread-control", unit=unit, temp_root=tmp_path)
    lifecycle.allocate_execution(
        "thread-control", unit_id="U1", execution_id="exec-1", native_task_name="sd_u1_a1", profile_id="reader", granted_authority="none", temp_root=tmp_path
    )
    basis = lifecycle.fresh_observation_basis("thread-control", execution_id="exec-1", temp_root=tmp_path)
    lifecycle.persist_host_observation(
        "thread-control", basis=basis, host_state="running", agent_id="agent-1", temp_root=tmp_path
    )
    return state


def test_orchestrate_and_doctor_are_the_public_surface():
    skills = sorted(path.name for path in (ROOT / "skills").iterdir() if path.is_dir())
    assert skills == ["doctor", "orchestrate"]


def test_main_selects_one_fixed_profile_explicitly():
    orchestrate = load_module("orch_explicit_profile", "orchestrate_v4.py")
    roles = json.loads(POLICY.read_text(encoding="utf-8"))["roles"]
    for profile_id in ("reader", "worker", "investigator", "solver", "advisor"):
        selected = orchestrate.select_profile(profile_id=profile_id, intent="bounded work")
        assert selected["profile_id"] == profile_id
        assert selected["model"] == roles[profile_id]["model"]
        assert selected["effort"] == roles[profile_id]["effort"]
    with pytest.raises(orchestrate.OrchestrateError, match="fixed managed profiles"):
        orchestrate.select_profile(profile_id="automatic-best-agent", intent="work")


def test_plan_only_requires_explicit_profile_and_never_creates_runtime_state(tmp_path: Path):
    orchestrate = load_module("orch_plan", "orchestrate_v4.py")
    state = load_module("orch_plan_state", "dispatch_state_v4.py")
    preview = orchestrate.plan_only_preview(
        goal="plan a safe change",
        responsibilities=[
            {"intent": "inspect", "goal": "map code", "profile_id": "reader"},
            {"intent": "implement", "goal": "change code", "profile_id": "worker"},
        ],
    )
    assert preview["mode"] == "PLAN_ONLY"
    assert preview["state_created"] is False
    assert preview["writer_lease_acquired"] is False
    assert preview["host_actions"] == []
    assert [item["profile"]["profile_id"] for item in preview["work_units"]] == ["reader", "worker"]
    assert state.load_state("thread-plan", temp_root=tmp_path) is None
    with pytest.raises(orchestrate.OrchestrateError, match="explicit profile_id"):
        orchestrate.plan_only_preview(
            goal="ambiguous profile",
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
    graph.install_work_graph("thread-active", team_plan_revision=1, units=[unit], temp_root=tmp_path)
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
    graph.install_work_graph("thread-status", team_plan_revision=1, units=units, temp_root=tmp_path)
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
    graph.install_single_work_unit("thread-reconcile", unit=unit, temp_root=tmp_path)
    snapshot = host.normalize_host_capabilities({
        "surface": "multi_agent_v2",
        "tools": ["spawn_agent", "followup_task", "interrupt_agent", "list_agents", "wait_agent"],
        "fork_turns_none": True,
        "max_spawned_threads": 4,
    })
    decision = orchestrate.reconcile_once(
        "thread-reconcile", orchestration_id="thread-reconcile", capability_snapshot=snapshot,
        wakeup_reason="USER_INPUT", temp_root=tmp_path
    )
    assert decision["selection_owner"] == "main"
    assert decision["ready_frontier"] == ["U1"]
    assert decision["actions"] == []
    assert decision["available_launch_slots"] == 4


def test_running_steer_is_transient(tmp_path: Path):
    state = install_running_reader(tmp_path)
    orchestrate = load_module("orch_steer", "orchestrate_v4.py")
    before = state.load_state("thread-control", temp_root=tmp_path)
    prepared = orchestrate.prepare_steer(
        "thread-control", orchestration_id="thread-control", execution_id="exec-1",
        tool_input={"target": "sd_u1_a1", "message": "Focus on the pagination boundary."},
        temp_root=tmp_path,
    )
    assert prepared["operation"] == "STEER"
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
        tool_input={"target": "sd_u1_a1", "message": "Correct the verified edge case."},
        correction_basis_ref="correction:verified-edge-case",
        temp_root=tmp_path,
    )

    assert prepared["operation"] == "FOLLOWUP"
    current = state.load_state("thread-control", temp_root=tmp_path)
    assert current is not None
    execution = next(item for item in current["executions"] if item["execution_id"] == "exec-1")
    assert execution["lifecycle"] == "SPAWN_PENDING"
    assert execution["followup_count"] == 1
