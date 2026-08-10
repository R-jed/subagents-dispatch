from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT
GUARDRAILS = PLUGIN / "contracts" / "guardrails.md"
RUNTIME_DOC = ROOT / "docs" / "native-subagent-runtime.md"
RUNTIME_VERIFIER = PLUGIN / "scripts" / "runtime-evidence.py"
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


def test_runtime_assurance_uses_one_optional_normalized_verifier():
    assert RUNTIME_VERIFIER.is_file()
    guardrails = GUARDRAILS.read_text(encoding="utf-8").lower()
    runtime = RUNTIME_DOC.read_text(encoding="utf-8").lower()
    assert "runtime-evidence.py" in guardrails
    assert "runtime-evidence.py" in runtime
    assert "diagnostic" in runtime
    assert "do not run these checks as routine ceremony" in runtime
    assert "runtime evidence is on demand" in guardrails


def test_project_does_not_scrape_runtime_internals_for_proof():
    runtime = RUNTIME_DOC.read_text(encoding="utf-8").lower()
    assert "profile matching proves configuration intent only" in runtime
    assert "never become observed values by assumption" in runtime
    for forbidden in ["--sessions-dir", "rollout-2026-", "sessions root"]:
        assert forbidden not in runtime


def test_missing_native_permission_evidence_remains_fail_closed():
    guardrails = GUARDRAILS.read_text(encoding="utf-8")
    assert "When hard read-only isolation is required, demand native evidence" in guardrails
    assert "keep the responsibility in the main session/blocked" in guardrails
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


def test_runtime_observation_required_needs_native_identity_and_ancestry():
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

    local_identity_only = run_runtime_evidence(
        {
            "subject": "child",
            "expected": expected,
            "native": route,
            "local": local,
        }
    )
    assert local_identity_only["status"] == "not_exposed"
    assert local_identity_only["decision"] == "return_to_main_session"
    assert local_identity_only["ancestry_evidence"] == {"status": "matched", "source": "local"}

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
