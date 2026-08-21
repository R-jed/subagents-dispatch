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
