from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT
GUARDRAILS = PLUGIN / "contracts" / "guardrails.md"
RUNTIME_DOC = ROOT / "docs" / "native-subagent-runtime.md"
ATTESTATION_DOC = ROOT / "docs" / "runtime-attestation.md"
RUNTIME_VERIFIER = PLUGIN / "scripts" / "runtime-evidence.py"
RUNTIME_INSPECTOR = PLUGIN / "scripts" / "inspect-agent-runtime.py"
RUNTIME_CASES = ROOT / "evals" / "runtime-assurance-cases.json"


def run_runtime_evidence(payload: dict) -> dict:
    result = subprocess.run(
        [sys.executable, str(RUNTIME_VERIFIER)],
        cwd=ROOT,
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_runtime_assurance_uses_explicit_inspector_and_normalized_verifier():
    assert RUNTIME_VERIFIER.is_file()
    assert RUNTIME_INSPECTOR.is_file()
    assert ATTESTATION_DOC.is_file()
    guardrails = GUARDRAILS.read_text(encoding="utf-8").lower()
    runtime = RUNTIME_DOC.read_text(encoding="utf-8").lower()
    attestation = ATTESTATION_DOC.read_text(encoding="utf-8").lower()
    assert "runtime-evidence.py" in guardrails
    assert "runtime-evidence.py" in runtime
    assert "inspect-agent-runtime.py" in guardrails
    assert "inspect-agent-runtime.py" in attestation
    assert "diagnostic" in runtime
    assert "do not run these checks as routine ceremony" in runtime
    assert "runtime evidence is on demand" in guardrails
    assert "ordinary dispatch does not run" in attestation


def test_exact_runtime_inspector_is_allowlisted_and_not_a_transcript_collector():
    source = RUNTIME_INSPECTOR.read_text(encoding="utf-8")
    attestation = ATTESTATION_DOC.read_text(encoding="utf-8")
    for field in [
        "thread_id",
        "parent_thread_id",
        "agent_role",
        "model",
        "effort",
        "sandbox_policy_type",
        "permission_profile_type",
        "runtime_version",
    ]:
        assert field in source
        assert field in attestation
    assert 'record_type == "session_meta"' in source
    assert 'record_type == "turn_context"' in source
    assert 'record_type == "event_msg"' not in source
    assert 'record_type == "response_item"' not in source
    assert "The inspector does not emit prompts" in attestation
    assert "assistant messages" in attestation
    assert "hidden reasoning" in attestation
    assert "tool payloads" in attestation


def test_runtime_configuration_cannot_impersonate_host_observation():
    guardrails = GUARDRAILS.read_text(encoding="utf-8")
    attestation = ATTESTATION_DOC.read_text(encoding="utf-8")
    assert "Configured/requested is not accepted. Accepted is not observed." in guardrails
    assert "A child describing its own model or reasoning level in prose is not runtime evidence" in guardrails
    assert "Configured is not Observed" in attestation
    assert "A child's prose claim" in attestation
    assert "manually copied local data cannot be relabeled as runtime observation" in guardrails


def test_hard_read_only_requires_actual_host_runtime_evidence():
    guardrails = GUARDRAILS.read_text(encoding="utf-8")
    assert "When hard read-only isolation is required, demand actual Host runtime evidence" in guardrails
    assert "configured/accepted values and child self-report are insufficient" in guardrails
    assert "configured read-only profile is intent, not proof" in guardrails


def test_runtime_evidence_keeps_route_ancestry_and_permission_typed():
    runtime = RUNTIME_DOC.read_text(encoding="utf-8")
    verifier = RUNTIME_VERIFIER.read_text(encoding="utf-8")
    for field in ["route_evidence", "ancestry_evidence", "permission_evidence"]:
        assert field in runtime
        assert field in verifier
    for grade in [
        "C1_configuration_only",
        "L1_local_record_observed",
        "R1_runtime_reported",
        "R2_runtime_reported_and_local_record_agree",
        "X0_conflicted",
    ]:
        assert grade in verifier


def test_runtime_observation_required_accepts_exact_local_identity_and_ancestry():
    expected = {
        "agent_role": "subagents_dispatch_reader",
        "model": "gpt-5.6-luna",
        "effort": "max",
        "thread_id": "child-1",
        "parent_thread_id": "main-1",
        "runtime_observation_required": True,
        "requires_enforced_read_only": False,
    }
    route = {
        "agent_role": "subagents_dispatch_reader",
        "model": "gpt-5.6-luna",
        "effort": "max",
    }
    local = {**route, "thread_id": "child-1", "parent_thread_id": "main-1"}

    local_identity_fallback = run_runtime_evidence(
        {
            "subject": "child",
            "expected": expected,
            "native": route,
            "local": local,
        }
    )
    assert local_identity_fallback["status"] == "matched"
    assert local_identity_fallback["decision"] == "continue"
    assert local_identity_fallback["runtime_observation_complete"] is True
    assert local_identity_fallback["ancestry_evidence"] == {
        "status": "matched",
        "source": "local",
    }

    native_identity = run_runtime_evidence(
        {
            "subject": "child",
            "expected": expected,
            "native": local,
            "local": local,
        }
    )
    assert native_identity["status"] == "matched"
    assert native_identity["decision"] == "continue"
    assert native_identity["ancestry_evidence"] == {"status": "matched", "source": "both"}


def test_runtime_assurance_fixture_uses_current_return_target():
    payload = json.loads(RUNTIME_CASES.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "2.0"
    decisions = {
        case["expected"].get("decision")
        for case in payload["cases"]
        if "decision" in case["expected"]
    }
    assert "return_to_main_session" in decisions
    assert "return_to_root" not in decisions
