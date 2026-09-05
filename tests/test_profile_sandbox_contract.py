from __future__ import annotations

import json
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT / "contracts" / "policy.json").read_text(encoding="utf-8"))
PROFILES = ROOT / "agent-profiles"


def test_profile_sandbox_intent_matches_three_role_semantics():
    for role_id, spec in POLICY["roles"].items():
        profile = tomllib.loads((PROFILES / spec["profile_file"]).read_text(encoding="utf-8"))
        if role_id == "department_director":
            assert profile.get("sandbox_mode") == "read-only"
        else:
            assert "sandbox_mode" not in profile
        assert "model" not in profile
        assert "model_reasoning_effort" not in profile
