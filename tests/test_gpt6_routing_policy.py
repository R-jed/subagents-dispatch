from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
POLICY = ROOT / "contracts" / "policy.json"


def load_policy_module():
    sys.path.insert(0, str(SCRIPTS))
    try:
        spec = importlib.util.spec_from_file_location("gpt6_policy_under_test", SCRIPTS / "policy.py")
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPTS))


def test_three_role_policy_is_the_only_production_route_truth():
    module = load_policy_module()
    payload = module.load_policy_contract()
    roles = module.role_contracts()

    assert set(roles) == {"programmer", "product_manager", "department_director"}
    assert "capability_dedup" not in payload
    assert "fixed_execution_profiles" not in payload
    assert roles["programmer"]["model"] == "gpt-5.6-luna"
    assert roles["programmer"]["allowed_efforts"] == ("max",)
    assert roles["product_manager"]["model"] == "gpt-5.6-sol"
    assert roles["product_manager"]["allowed_efforts"] == ("medium", "high")
    assert roles["department_director"]["model"] == "gpt-6-astra"
    assert roles["department_director"]["allowed_efforts"] == ("high",)


def test_policy_resolves_exact_routes_without_parent_inheritance_or_fallback():
    module = load_policy_module()

    assert module.resolve_managed_route(role_id="programmer") == {
        "role_id": "programmer",
        "agent_type": "subagents_dispatch_programmer",
        "model": "gpt-5.6-luna",
        "reasoning_effort": "max",
    }
    assert module.resolve_managed_route(
        role_id="product_manager", reasoning_effort="medium"
    )["reasoning_effort"] == "medium"
    assert module.resolve_managed_route(
        role_id="product_manager", reasoning_effort="high"
    )["reasoning_effort"] == "high"
    assert module.resolve_managed_route(role_id="department_director") == {
        "role_id": "department_director",
        "agent_type": "subagents_dispatch_department_director",
        "model": "gpt-6-astra",
        "reasoning_effort": "high",
    }

    with pytest.raises(RuntimeError, match="explicit reasoning_effort"):
        module.resolve_managed_route(role_id="product_manager")
    with pytest.raises(RuntimeError, match="outside the policy route"):
        module.resolve_managed_route(role_id="product_manager", reasoning_effort="xhigh")
    with pytest.raises(RuntimeError, match="unknown managed role"):
        module.resolve_managed_route(role_id="reader")


def test_decision_and_review_tiers_are_deterministic_from_confirmed_triggers():
    module = load_policy_module()

    assert module.resolve_product_manager_effort([]) == "medium"
    assert module.resolve_product_manager_effort(["architecture_boundary"]) == "high"
    assert module.resolve_product_manager_effort(["migration"]) == "high"
    with pytest.raises(RuntimeError, match="unknown decision trigger"):
        module.resolve_product_manager_effort(["many_files"])

    assert module.resolve_review_route([]) is None
    standard = module.resolve_review_route(["public_contract_change"])
    assert standard == {
        "tier": "standard",
        "role_id": "product_manager",
        "agent_type": "subagents_dispatch_product_manager",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "high",
    }
    highest = module.resolve_review_route(["authorization_boundary"])
    assert highest == {
        "tier": "highest",
        "role_id": "department_director",
        "agent_type": "subagents_dispatch_department_director",
        "model": "gpt-6-astra",
        "reasoning_effort": "high",
    }
    # Highest applicable tier substitutes for standard review.
    assert module.resolve_review_route(
        ["public_contract_change", "authorization_boundary"]
    )["tier"] == "highest"
    with pytest.raises(RuntimeError, match="unknown review trigger"):
        module.resolve_review_route(["solver_used"])


def test_policy_trigger_sets_are_explicit_and_non_overlapping():
    payload = json.loads(POLICY.read_text(encoding="utf-8"))
    review = payload["review_routing"]
    standard = set(review["standard"]["triggers"])
    highest = set(review["highest"]["triggers"])
    assert standard.isdisjoint(highest)
    assert highest == {
        "security_boundary",
        "authorization_boundary",
        "data_integrity",
        "critical_concurrency_or_ownership",
        "migration",
        "irreversible_external_effect",
        "release",
        "user_requested_highest_assurance",
    }


def test_routing_eval_routes_are_exact_policy_routes_and_use_only_three_roles():
    module = load_policy_module()
    cases = json.loads((ROOT / "evals" / "routing-cases.json").read_text(encoding="utf-8"))["cases"]
    seen_roles: set[str] = set()
    for case in cases:
        for node in case["expected"].get("nodes", []):
            role_id = node["role"]
            seen_roles.add(role_id)
            route = module.resolve_managed_route(
                role_id=role_id,
                reasoning_effort=node["effort"],
            )
            assert node["agent_type"] == route["agent_type"]
            assert node["model"] == route["model"]
    assert seen_roles == {"programmer", "product_manager", "department_director"}
