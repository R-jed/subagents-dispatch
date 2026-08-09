from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT
SKILL = PLUGIN / "skills" / "dispatch"
CONTRACTS = PLUGIN / "contracts"
POLICY = PLUGIN / "contracts" / "policy.json"


def test_runtime_evidence_is_diagnostic_not_default_hot_path():
    guardrails = (CONTRACTS / "guardrails.md").read_text(encoding="utf-8")
    router = (CONTRACTS / "routing.md").read_text(encoding="utf-8")
    assert "Runtime evidence is on demand" in guardrails
    assert "Do not run runtime-evidence diagnostics for every ordinary child" in guardrails
    assert "Main-session Sol dedup is an optimization" in router
    assert "Missing telemetry is allowed to remain missing" in router


def test_runtime_verifier_supports_main_and_child_subjects_and_policy_reference():
    verifier = (PLUGIN / "scripts" / "runtime-evidence.py").read_text(encoding="utf-8")
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    assert 'subject == "main_session"' in verifier
    assert 'subject == "child"' in verifier
    assert "load_main_coverage_policy" in verifier
    assert policy["capability_dedup"]["reference_role"] == "solver"
    assert 'coverage = "unknown"' in verifier
    assert "quarantine_main_route_claim" in verifier


def test_exact_project_roles_have_no_cross_role_fallback():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    guardrails = (CONTRACTS / "guardrails.md").read_text(encoding="utf-8")
    assert "Host/configuration limitation and fail closed" in guardrails
    assert "Do not substitute another role" in guardrails
    assert set(spec["agent_type"] for spec in policy["roles"].values()) == {
        "subagents_dispatch_reader",
        "subagents_dispatch_worker",
        "subagents_dispatch_solver",
        "subagents_dispatch_investigator",
        "subagents_dispatch_advisor",
    }


def test_new_project_children_use_explicit_fresh_context():
    guardrails = (CONTRACTS / "guardrails.md").read_text(encoding="utf-8")
    runtime = (ROOT / "docs" / "native-subagent-runtime.md").read_text(encoding="utf-8")
    assert "`fork_turns` is present and exactly `none`" in guardrails
    assert "omitted `fork_turns` are forbidden" in guardrails
    assert "fork_turns=none" in runtime


def test_consent_writer_and_explicit_invocation_are_guardrail_owned():
    guardrails = (CONTRACTS / "guardrails.md").read_text(encoding="utf-8")
    for phrase in [
        "Project policy does not impose an ordinary numeric child ceiling",
        "Child count by itself is not a consent trigger",
        "One writer per canonical checkout",
        "main session when mutating the checkout",
        "Explicit invocation only",
        "Routine first-use provisioning is not a separate consent prompt",
    ]:
        assert phrase in guardrails

    openai = (SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8")
    assert "allow_implicit_invocation: false" in openai


def test_first_use_readiness_occurs_before_delegated_execution():
    guardrails = (CONTRACTS / "guardrails.md").read_text(encoding="utf-8")
    skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "First-use readiness before delegated execution" in guardrails
    assert "../../contracts/guardrails.md" in skill
    assert "RESTART_REQUIRED" in guardrails
    assert "without attempting `spawn_agent`" in guardrails
    assert "no child attempt has been created yet" in guardrails


def test_profile_lifecycle_comes_from_policy_and_installer_not_user_docs():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    profiles = PLUGIN / "agent-profiles"
    installer = (PLUGIN / "scripts" / "install-agents.py").read_text(encoding="utf-8")
    policy_loader = (PLUGIN / "scripts" / "policy.py").read_text(encoding="utf-8")
    expected_files = {spec["profile_file"] for spec in policy["roles"].values()}
    assert {path.name for path in profiles.glob("*.toml")} == expected_files
    assert 'MANIFEST_NAME = ".subagents-dispatch-agents.json"' in installer
    assert 'LOCK_NAME = ".subagents-dispatch-agents.lock"' in installer
    assert "from policy import load_policy_contract" in installer
    assert 'POLICY_CONTRACT_PATH = ROOT / "contracts" / "policy.json"' in policy_loader


def test_process_history_is_not_a_final_review_trigger():
    final_review = (CONTRACTS / "final-review.md").read_text(encoding="utf-8")
    for phrase in ["Terra use", "Solver use", "recovery", "a large diff"]:
        assert phrase in final_review
    assert "is not a trigger by itself" in final_review


def test_behavioral_evals_remain_measurement_not_runtime_policy():
    docs = (ROOT / "docs" / "behavioral-evals.md").read_text(encoding="utf-8").lower()
    for phrase in [
        "controlled paired workloads",
        "measurement surface",
        "experiment labels only",
    ]:
        assert phrase in docs
