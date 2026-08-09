from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT
CONTRACTS = PLUGIN / "contracts"
ROUTER = CONTRACTS / "routing.md"
GUARDRAILS = CONTRACTS / "guardrails.md"
POLICY = PLUGIN / "contracts" / "policy.json"
ROUTING_CASES = ROOT / "evals" / "routing-cases.json"


def policy() -> dict:
    return json.loads(POLICY.read_text())


def routing_cases() -> dict[str, dict]:
    payload = json.loads(ROUTING_CASES.read_text())
    assert payload["schema_version"] == "2.0"
    return {case["id"]: case for case in payload["cases"]}


def test_machine_contract_keeps_depth_and_semantic_writer_coordination():
    assert policy()["delegation"] == {"max_depth": 1}
    assert policy()["write_coordination"] == {
        "mode": "single_writer",
        "scope": "canonical_workspace",
    }


def test_static_cases_cover_adaptive_fanout_and_material_compute_consent():
    cases = routing_cases()
    parallel = cases["three-independent-readers-can-fanout"]
    assert parallel["expected"]["action"] == "delegate"
    assert len(parallel["expected"]["nodes"]) == 3
    assert all(node["agent_type"] == "subagents_dispatch_reader" for node in parallel["expected"]["nodes"])

    consent = cases["material-compute-expansion-needs-consent"]
    assert consent["expected"]["action"] == "ask_consent"
    assert consent["expected"]["consent_reason"] == "material_compute_expansion"


def test_router_and_guardrails_own_adaptive_scheduling_and_writer_safety():
    router = ROUTER.read_text().lower()
    guardrails = GUARDRAILS.read_text().lower()

    for concept in ["ready frontier", "progressive fan-out", "native codex capacity"]:
        assert concept in router
    for concept in [
        "one writer per canonical checkout",
        "filesystem isolation",
        "semantic independence",
        "child count by itself is not a consent trigger",
        "delegation depth is one",
    ]:
        assert concept in guardrails


def test_installer_lock_is_a_local_profile_lifecycle_mechanism():
    installer = (PLUGIN / "scripts" / "install-agents.py").read_text().lower()
    assert 'lock_name = ".subagents-dispatch-agents.lock"' in installer
    assert "def managed_lock(" in installer
    assert "def installation_locks(" in installer
    assert "def installer_lock(" not in installer
    assert "lock_file(fd)" in installer
