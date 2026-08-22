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
    "reader": ("gpt-5.6-luna", "max", "none"),
    "worker": ("gpt-5.6-luna", "max", "bounded-source-write"),
    "investigator": ("gpt-5.6-terra", "high", "none"),
    "solver": ("gpt-5.6-sol", "high", "bounded-source-write"),
    "advisor": ("gpt-5.6-sol", "high", "none"),
}
CURRENT_DOCS = (
    "README.md",
    "README_EN.md",
    "README_AI.md",
    "CHANGELOG.md",
    "docs/architecture.md",
    "docs/native-subagent-runtime.md",
    "docs/release-checklist.md",
    "evals/README.md",
)


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


def test_fixed_model_effort_authority_is_exact():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    assert policy["fixed_execution_profiles"] == {
        "luna": "max",
        "terra": "high",
        "sol": "high",
        "dynamic_effort_routing": False,
    }
    actual = {
        role: (spec["model"], spec["effort"], spec["mutation_authority"])
        for role, spec in policy["roles"].items()
    }
    assert actual == EXPECTED


def test_profiles_runtime_doctor_and_machine_architecture_match_policy():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    architecture = json.loads((ROOT / "docs" / "v4" / "architecture.json").read_text(encoding="utf-8"))
    state = load_module("model_effort_state", "dispatch_state_v4.py")
    doctor = load_module("model_effort_doctor", "doctor.py")

    assert state.PROFILE_CONTRACT == EXPECTED
    assert not hasattr(doctor, "EXPECTED_PROFILES")
    doctor_profiles = doctor.policy_contract.profile_contracts()
    assert {
        role: (spec["model"], spec["effort"], spec["mutation_authority"])
        for role, spec in doctor_profiles.items()
    } == EXPECTED

    for role, expected in EXPECTED.items():
        spec = policy["roles"][role]
        profile = tomllib.loads(
            (ROOT / "agent-profiles" / spec["profile_file"]).read_text(encoding="utf-8")
        )
        architecture_profile = architecture["profiles"][role]
        assert (profile["model"], profile["model_reasoning_effort"]) == expected[:2]
        assert (
            architecture_profile["model"],
            architecture_profile["effort"],
            architecture_profile["mutation_authority"],
        ) == expected


def test_routing_evals_use_current_production_profiles():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    cases = json.loads((ROOT / "evals" / "routing-cases.json").read_text(encoding="utf-8"))["cases"]
    for case in cases:
        for node in case["expected"].get("nodes", []):
            spec = policy["roles"][node["role"]]
            assert (node["model"], node["effort"], node["mutation_authority"]) == (
                spec["model"],
                spec["effort"],
                spec["mutation_authority"],
            )


def test_current_product_docs_keep_terra_high():
    for relative in CURRENT_DOCS:
        text = (ROOT / relative).read_text(encoding="utf-8")
        lowered = text.lower()
        assert "terra" in lowered, relative
        assert "xhigh" not in lowered, relative

    machine = json.loads((ROOT / "docs" / "v4" / "orchestrate.json").read_text(encoding="utf-8"))
    assert machine["routing"]["investigator"] == ["gpt-5.6-terra", "high"]
