from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
V4 = ROOT / "docs" / "v4"


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


def load_json(name: str) -> dict:
    return json.loads((V4 / name).read_text(encoding="utf-8"))


def test_architecture_host_capability_contract_matches_runtime_owner():
    architecture = load_json("architecture.json")
    host = load_module("rc4_drift_host", "host_capabilities.py")
    assert architecture["host_capability_requirements"] == list(host.REQUIRED_CAPABILITIES)
    assert "host_observation_guard" in architecture["host_capability_requirements"]


def test_phase_status_uses_external_candidate_bound_h00_h20_release_truth():
    status = load_json("phase-status.json")
    phase8 = status["phases"]["phase8"]
    assert phase8["repository_candidate_branch"] == "v4/rc4-host-contract-closure"
    assert phase8["tracked_host_contract_status"] == "PENDING_REQUIRED"
    assert phase8["external_host_campaign"] == "REQUIRED_H00_H20"
    rule = status["release_rule"]
    assert "external candidate-bound H00-H20" in rule
    assert "host-smoke.json is not PASS" not in rule


def test_orchestrate_contract_describes_current_two_skill_surface_without_coexistence():
    contract = load_json("orchestrate.json")
    assert contract["schema_version"] == "4.0.0-orchestrate-2"
    assert contract["public_target"] == ["orchestrate", "doctor"]
    assert "coexistence_skills" not in contract
    assert set(contract["retired_public_skills"]) == {
        "dispatch",
        "preview",
        "status",
        "steer",
        "takeover",
    }


def test_scheduler_contract_names_authoritative_host_occupancy_rules():
    contract = load_json("scheduler.json")
    assert (
        contract["host_occupancy_truth"]
        == "latest_authoritative_unfiltered_root_list_agents_observation"
    )
    assert contract["authoritative_list_agents_tool_input"] == {}
    assert contract["one_host_observation_fresh_spawn_max"] == 1
    assert contract["mixed_managed_unmanaged_occupancy"] is True
    assert contract["settled_resident_reclaim"] == "one_bounded_host_attempt"


def test_host_campaign_requires_unfiltered_root_occupancy_and_input_binding():
    smoke = load_json("host-smoke.json")
    probes = {probe["id"]: probe for probe in smoke["required_probes"]}
    assert any("unfiltered root list_agents" in item for item in probes["H09"]["requires"])
    assert any("tool_input binding" in item for item in probes["H17"]["requires"])
    assert any("filtered path_prefix" in item for item in probes["H18"]["requires"])


def test_technical_debt_release_policy_tracks_current_h00_h20_gate():
    debt = load_json("technical-debt.json")
    policy = debt["release_policy"]
    assert "H00-H20" in policy
    assert "H01-H07" not in policy


def test_doctor_core_fallback_uses_the_same_static_host_contract_as_release_owner():
    release = load_module("rc4_drift_release", "release_evidence_v4.py")
    core = load_module("rc4_drift_doctor_core", "doctor_runtime_core.py")
    smoke = load_json("host-smoke.json")
    assert core.EXPECTED_HOST_PROBES == release.REQUIRED_HOST_PROBES
    valid, complete, reason = core._validate_host_smoke_evidence(smoke)
    assert valid is True, reason
    assert complete is False

    spoofed = dict(smoke)
    spoofed["status"] = "PASS"
    valid, complete, reason = core._validate_host_smoke_evidence(spoofed)
    assert valid is False
    assert complete is False
    assert reason and "PENDING" in reason
