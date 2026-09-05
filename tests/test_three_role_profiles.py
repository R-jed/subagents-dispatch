from __future__ import annotations

import json
from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT / "contracts" / "policy.json").read_text(encoding="utf-8"))
PROFILE_DIR = ROOT / "agent-profiles"


def test_package_ships_exactly_three_behavior_profiles_without_route_pins():
    expected_files = {
        "subagents-dispatch-programmer.toml",
        "subagents-dispatch-product-manager.toml",
        "subagents-dispatch-department-director.toml",
    }
    assert {path.name for path in PROFILE_DIR.glob("*.toml")} == expected_files
    assert set(POLICY["roles"]) == {"programmer", "product_manager", "department_director"}

    for role_id, spec in POLICY["roles"].items():
        profile = tomllib.loads((PROFILE_DIR / spec["profile_file"]).read_text(encoding="utf-8"))
        assert profile["name"] == spec["agent_type"]
        assert "model" not in profile
        assert "model_reasoning_effort" not in profile
        assert profile["agents"]["enabled"] is False
        assert profile["features"]["multi_agent_v2"] is False
        assert "create further subagents" in profile["developer_instructions"].lower()
        assert profile["description"].strip()


def test_only_department_director_requests_read_only_profile_sandbox():
    profiles = {
        role_id: tomllib.loads((PROFILE_DIR / spec["profile_file"]).read_text(encoding="utf-8"))
        for role_id, spec in POLICY["roles"].items()
    }
    assert "sandbox_mode" not in profiles["programmer"]
    assert "sandbox_mode" not in profiles["product_manager"]
    assert profiles["department_director"]["sandbox_mode"] == "read-only"
