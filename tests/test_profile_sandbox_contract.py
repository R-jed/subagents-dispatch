from __future__ import annotations

import json
from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT / "contracts" / "policy.json").read_text(encoding="utf-8"))
PROFILES = ROOT / "agent-profiles"


def test_read_only_roles_pin_read_only_sandbox_and_writers_inherit_host_permission():
    for role, spec in POLICY["roles"].items():
        profile = tomllib.loads((PROFILES / spec["profile_file"]).read_text(encoding="utf-8"))
        if spec["mutation_authority"] == "none":
            assert spec.get("sandbox_mode") == "read-only", role
            assert profile.get("sandbox_mode") == "read-only", role
        else:
            assert "sandbox_mode" not in spec, role
            assert "sandbox_mode" not in profile, role
