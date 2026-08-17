from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tomllib


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
POLICY = ROOT / "contracts" / "policy.json"
ROUTING_CASES = ROOT / "evals" / "routing-cases.json"


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


def test_v4_policy_freezes_depth_writer_and_model_effort_profiles():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    assert policy["schema_version"] == 9
    assert policy["delegation"] == {"max_depth": 1, "fork_turns": "none"}
    assert policy["write_coordination"] == {"mode": "single_writer", "scope": "canonical_workspace"}
    assert policy["fixed_execution_profiles"] == {
        "luna": "max",
        "terra": "high",
        "sol": "high",
        "dynamic_effort_routing": False,
    }
    expected = {
        "reader": ("gpt-5.6-luna", "max", "none"),
        "worker": ("gpt-5.6-luna", "max", "bounded-source-write"),
        "investigator": ("gpt-5.6-terra", "high", "none"),
        "solver": ("gpt-5.6-sol", "high", "bounded-source-write"),
        "advisor": ("gpt-5.6-sol", "high", "none"),
    }
    for role, (model, effort, authority) in expected.items():
        spec = policy["roles"][role]
        assert (spec["model"], spec["effort"], spec["mutation_authority"]) == (model, effort, authority)
        profile = tomllib.loads(
            (ROOT / "agent-profiles" / spec["profile_file"]).read_text(encoding="utf-8")
        )
        assert profile["model"] == model
        assert profile["model_reasoning_effort"] == effort


def test_routing_evals_match_the_frozen_profile_contract():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    cases = json.loads(ROUTING_CASES.read_text(encoding="utf-8"))["cases"]
    for case in cases:
        for node in case["expected"].get("nodes", []):
            role = node["role"]
            spec = policy["roles"][role]
            assert node["agent_type"] == spec["agent_type"]
            assert node["model"] == spec["model"]
            assert node["effort"] == spec["effort"]
            assert node["mutation_authority"] == spec["mutation_authority"]


def test_orchestrate_keeps_zero_child_and_plan_only_as_valid_outcomes():
    skill = (ROOT / "skills" / "orchestrate" / "SKILL.md").read_text(encoding="utf-8")
    assert "plan-only" in skill
    assert "without creating `active.json`" in skill
    orchestrate = load_module("coord_orchestrate", "orchestrate_v4.py")
    plan = orchestrate.plan_only_preview(goal="small task", responsibilities=[])
    assert plan["mode"] == "PLAN_ONLY"
    assert plan["host_actions"] == []


def test_scheduler_uses_acceptance_gated_dependencies_and_bounded_fanout():
    scheduler = load_module("coord_scheduler", "scheduler_v4.py")
    assert scheduler.INITIAL_CHILD_LIMIT == 2
    assert scheduler.PRODUCT_CHILD_LIMIT == 3
    assert scheduler.BACKPRESSURE_THRESHOLD == 2
    assert callable(scheduler.scheduler_decision)
    graph = (SCRIPTS / "work_graph_v4.py").read_text(encoding="utf-8")
    assert "ACCEPTED" in graph
    assert "RESULT_READY" in graph


def test_v4_runtime_separates_workunit_execution_control_and_writer_truth():
    state = load_module("coord_state", "dispatch_state_v4.py")
    payload = state.new_state(thread_id="coord-thread")
    assert payload["work_units"] == []
    assert payload["executions"] == []
    assert payload["pending_controls"] == []
    assert payload["writer_lease"] is None
    assert "control_epoch" in state.EXECUTION_FIELDS


def test_same_child_reuse_and_takeover_are_not_fresh_attempt_shortcuts():
    lifecycle = load_module("coord_lifecycle", "execution_lifecycle_v4.py")
    assert callable(lifecycle.prepare_same_child_followup)
    assert callable(lifecycle.prepare_same_child_continue)
    assert callable(lifecycle.prepare_interrupt)
    assert callable(lifecycle.takeover_to_main)
    source = (SCRIPTS / "execution_lifecycle_v4.py").read_text(encoding="utf-8")
    assert "followup_count" in source
    writer = (SCRIPTS / "writer_lease_v4.py").read_text(encoding="utf-8")
    assert "guard_coverage" in writer
    assert "observation" in writer.lower()


def test_public_v4_surface_is_two_skills_and_review_identity_is_retained():
    assert sorted(path.name for path in (ROOT / "skills").iterdir() if path.is_dir()) == ["doctor", "orchestrate"]
    review = (ROOT / "contracts" / "final-review.md").read_text(encoding="utf-8")
    assert "review_artifact_id" in review
    assert "sha256" in review.lower() or "git" in review.lower()
