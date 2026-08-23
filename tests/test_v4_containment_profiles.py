from __future__ import annotations

import json
from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "contracts" / "policy.json"
ARCHITECTURE = ROOT / "docs" / "v4" / "architecture.json"
HOST_SMOKE = ROOT / "docs" / "v4" / "host-smoke.json"
PROFILES = ROOT / "agent-profiles"

ROLES = {"reader", "worker", "investigator", "solver", "advisor"}
MODEL = "gpt-5.6-luna"
EFFORT = "max"


def test_managed_profiles_use_containment_safe_model_contract():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))

    assert policy["schema_version"] >= 10
    assert set(policy["roles"]) == ROLES
    assert policy["containment"] == {
        "managed_model_multi_agent_version": "v1",
        "v2_capable_managed_child_models_allowed": False,
        "behavioral_leaf_instruction": "defense_only",
    }

    for role, spec in policy["roles"].items():
        assert spec["model"] == MODEL, role
        assert spec["effort"] == EFFORT, role

        profile_path = PROFILES / spec["profile_file"]
        profile = tomllib.loads(profile_path.read_text(encoding="utf-8"))

        assert profile["name"] == spec["agent_type"], role
        assert profile["model"] == MODEL, role
        assert profile["model_reasoning_effort"] == EFFORT, role
        assert "agents" not in profile, role
        assert "features" not in profile, role
        assert "Do not create further subagents" in profile["developer_instructions"], role


def test_architecture_and_host_gate_mirror_containment_contract():
    architecture = json.loads(ARCHITECTURE.read_text(encoding="utf-8"))
    host_smoke = json.loads(HOST_SMOKE.read_text(encoding="utf-8"))

    assert architecture["delegation"]["managed_model_multi_agent_version"] == "v1"
    assert architecture["delegation"]["v2_capable_managed_child_models_allowed"] is False

    for role in ROLES:
        assert architecture["profiles"][role]["model"] == MODEL
        assert architecture["profiles"][role]["effort"] == EFFORT

    n0 = next(item for item in host_smoke["required_probes"] if item["id"] == "N0")
    n1 = next(item for item in host_smoke["required_probes"] if item["id"] == "N1")

    assert any(
        "Reader, Worker, Investigator, Solver, and Advisor all use gpt-5.6-luna max"
        in requirement
        for requirement in n0["requires"]
    )
    assert any(
        "gpt-5.6-luna multi_agent_version v1" in requirement
        for requirement in n0["requires"]
    )
    assert any(
        "active Host model metadata" in requirement
        for requirement in n1["requires"]
    )
    assert host_smoke["status"] == "PENDING"
    assert host_smoke["results"] == {}
