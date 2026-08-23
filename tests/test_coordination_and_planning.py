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


def test_v4_policy_freezes_depth_child_ceiling_writer_and_profiles():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    assert policy["schema_version"] == 10
    assert policy["delegation"] == {
        "max_depth": 1,
        "fork_turns": "none",
        "max_managed_children": 4,
    }
    assert policy["containment"] == {
        "managed_model_multi_agent_version": "v1",
        "v2_capable_managed_child_models_allowed": False,
        "behavioral_leaf_instruction": "defense_only",
    }
    assert policy["write_coordination"] == {"mode": "single_writer", "scope": "canonical_workspace"}
    assert policy["fixed_execution_profiles"] == {
        "luna": "max",
        "dynamic_effort_routing": False,
    }
    expected = {
        "reader": ("gpt-5.6-luna", "max", "none"),
        "worker": ("gpt-5.6-luna", "max", "bounded-source-write"),
        "investigator": ("gpt-5.6-luna", "max", "none"),
        "solver": ("gpt-5.6-luna", "max", "bounded-source-write"),
        "advisor": ("gpt-5.6-luna", "max", "none"),
    }
    for role, (model, effort, authority) in expected.items():
        spec = policy["roles"][role]
        assert (spec["model"], spec["effort"], spec["mutation_authority"]) == (model, effort, authority)
        profile = tomllib.loads((ROOT / "agent-profiles" / spec["profile_file"]).read_text(encoding="utf-8"))
        assert profile["model"] == model
        assert profile["model_reasoning_effort"] == effort
        assert "agents" not in profile
        assert "features" not in profile
        assert "create further subagents" in profile["developer_instructions"].lower()


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


def test_plan_only_keeps_zero_child_as_a_valid_nonexecuting_outcome():
    orchestrate = load_module("coord_orchestrate", "orchestrate_v4.py")
    plan = orchestrate.plan_only_preview(goal="small task", responsibilities=[])
    assert plan["mode"] == "PLAN_ONLY"
    assert plan["state_created"] is False
    assert plan["writer_lease_acquired"] is False
    assert plan["host_actions"] == []
    assert plan["work_units"] == []


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
