from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tomllib


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
POLICY = ROOT / "contracts" / "policy.json"
EXPECTED = {
    "programmer": ("gpt-5.6-luna", ("max",)),
    "product_manager": ("gpt-5.6-sol", ("medium", "high")),
    "department_director": ("gpt-6-astra", ("high",)),
}


def load_module(name: str, filename: str):
    sys.path.insert(0, str(SCRIPTS))
    try:
        spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPTS))


def test_three_role_model_effort_authority_is_exact():
    module = load_module("model_effort_policy", "policy.py")
    payload = module.load_policy_contract()
    assert "fixed_execution_profiles" not in payload
    assert "capability_dedup" not in payload
    roles = module.role_contracts()
    assert {
        role: (spec["model"], spec["allowed_efforts"])
        for role, spec in roles.items()
    } == EXPECTED


def test_profiles_do_not_duplicate_model_effort_route_truth():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    architecture = json.loads((ROOT / "docs" / "v4" / "architecture.json").read_text(encoding="utf-8"))

    assert set(architecture["profiles"]) == set(EXPECTED)
    for role, (model, efforts) in EXPECTED.items():
        spec = policy["roles"][role]
        profile = tomllib.loads(
            (ROOT / "agent-profiles" / spec["profile_file"]).read_text(encoding="utf-8")
        )
        assert "model" not in profile
        assert "model_reasoning_effort" not in profile
        assert architecture["profiles"][role]["model"] == model
        assert tuple(architecture["profiles"][role]["allowed_efforts"]) == efforts


def test_routing_evals_use_only_exact_policy_routes():
    module = load_module("model_effort_policy_eval", "policy.py")
    cases = json.loads((ROOT / "evals" / "routing-cases.json").read_text(encoding="utf-8"))["cases"]
    for case in cases:
        for node in case["expected"].get("nodes", []):
            route = module.resolve_managed_route(
                role_id=node["role"], reasoning_effort=node["effort"]
            )
            assert node["agent_type"] == route["agent_type"]
            assert node["model"] == route["model"]


def test_department_director_is_exact_astra_high_release_route():
    module = load_module("model_effort_policy_director", "policy.py")
    assert module.resolve_managed_route(role_id="department_director") == {
        "role_id": "department_director",
        "agent_type": "subagents_dispatch_department_director",
        "model": "gpt-6-astra",
        "reasoning_effort": "high",
    }
