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
ROUTING = ROOT / "contracts" / "routing.md"
GUARDRAILS = ROOT / "contracts" / "guardrails.md"
ORCHESTRATE_SKILL = ROOT / "skills" / "orchestrate" / "SKILL.md"
ARCHITECTURE = ROOT / "docs" / "v4" / "architecture.json"


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


def test_v4_policy_freezes_depth_child_ceiling_writer_and_profiles():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    assert policy["schema_version"] == 10
    assert policy["delegation"] == {
        "max_depth": 1,
        "fork_turns": "none",
        "max_managed_children": 4,
    }
    assert policy["write_coordination"] == {"mode": "single_writer", "scope": "canonical_workspace"}
    assert "fixed_execution_profiles" not in policy
    expected = {
        "programmer": ("gpt-5.6-luna", ["max"]),
        "product_manager": ("gpt-5.6-sol", ["medium", "high"]),
        "department_director": ("gpt-6-astra", ["high"]),
    }
    for role, (model, efforts) in expected.items():
        spec = policy["roles"][role]
        assert (spec["model"], spec["allowed_efforts"]) == (model, efforts)
        profile = tomllib.loads((ROOT / "agent-profiles" / spec["profile_file"]).read_text(encoding="utf-8"))
        assert "model" not in profile
        assert "model_reasoning_effort" not in profile
        assert profile["agents"]["enabled"] is False
        assert profile["features"]["multi_agent_v2"] is False


def test_routing_evals_match_the_frozen_profile_contract():
    policy_module = load_module("coord_policy", "policy.py")
    cases = json.loads(ROUTING_CASES.read_text(encoding="utf-8"))["cases"]
    for case in cases:
        for node in case["expected"].get("nodes", []):
            route = policy_module.resolve_managed_route(
                role_id=node["role"], reasoning_effort=node["effort"]
            )
            assert node["agent_type"] == route["agent_type"]
            assert node["model"] == route["model"]


def test_plan_only_keeps_zero_child_as_a_valid_nonexecuting_outcome():
    orchestrate = load_module("coord_orchestrate", "orchestrate_v4.py")
    plan = orchestrate.plan_only_preview(goal="small task", responsibilities=[])
    assert plan["mode"] == "PLAN_ONLY"
    assert plan["state_created"] is False
    assert plan["writer_lease_acquired"] is False
    assert plan["host_actions"] == []
    assert plan["work_units"] == []


def test_minimum_useful_fanout_contract_preserves_zero_one_and_parallel_shapes():
    cases = {case["id"]: case for case in json.loads(ROUTING_CASES.read_text(encoding="utf-8"))["cases"]}
    assert cases["single-file-clear-fix"]["expected"]["nodes"] == []
    assert len(cases["bounded-read-uses-programmer"]["expected"]["nodes"]) == 1
    assert len(cases["three-independent-programmers-can-fanout-read-only"]["expected"]["nodes"]) == 3

    routing = ROUTING.read_text(encoding="utf-8")
    guardrails = GUARDRAILS.read_text(encoding="utf-8")
    skill = ORCHESTRATE_SKILL.read_text(encoding="utf-8")
    for text in (routing, guardrails, skill):
        assert "minimum useful fanout" in text
    assert "Delegated work substitutes for Main doing that same responsibility" in routing
    assert "Do not impose one-child-first" in guardrails
    assert "Do not hard-code one-child-first" in skill


def test_route_rationale_is_presentation_only_not_runtime_state():
    routing = ROUTING.read_text(encoding="utf-8")
    skill = ORCHESTRATE_SKILL.read_text(encoding="utf-8")
    architecture = json.loads(ARCHITECTURE.read_text(encoding="utf-8"))

    assert "brief route rationale" in routing
    assert "one brief route rationale" in skill
    assert "presentation creates no scheduler or state authority" in routing
    assert "presentation only" in skill
    assert "route_mode" not in architecture["routing"]
    assert architecture["routing"]["route_rationale_persisted"] is False


def test_v4_runtime_separates_workunit_execution_and_writer_truth():
    state = load_module("coord_state", "dispatch_state_v4.py")
    payload = state.new_state(thread_id="coord-thread")
    assert payload["work_units"] == []
    assert payload["executions"] == []
    assert payload["writer_lease"] is None
    assert "pending_controls" not in payload
    assert state.validate_state_payload(payload) == payload


def test_public_surface_contains_only_the_two_supported_skills():
    assert sorted(path.name for path in (ROOT / "skills").iterdir() if path.is_dir()) == ["doctor", "orchestrate"]
