from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_VERIFIER = ROOT / "scripts" / "runtime-evidence.py"
RUNTIME_INSPECTOR = ROOT / "scripts" / "inspect-agent-runtime.py"
POLICY = json.loads((ROOT / "contracts" / "policy.json").read_text(encoding="utf-8"))
ORCHESTRATE = ROOT / "skills" / "orchestrate" / "SKILL.md"
GUARDRAILS = ROOT / "contracts" / "guardrails.md"
ATTESTATION = ROOT / "docs" / "runtime-attestation.md"
THREAD = "11111111-1111-7111-8111-111111111111"
PARENT = "00000000-0000-7000-8000-000000000000"


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


def managed_routes() -> list[dict]:
    return list(POLICY["roles"].values())


def expected_for(route: dict) -> dict:
    return {
        "thread_id": THREAD,
        "parent_thread_id": PARENT,
        "agent_role": route["agent_type"],
        "model": route["model"],
        "effort": route["effort"],
        "runtime_observation_required": True,
        "requires_permission_observation": True,
    }


def observed_for(route: dict, *, sandbox: str = "danger-full-access", profile: str = "disabled") -> dict:
    return {
        "thread_id": THREAD,
        "parent_thread_id": PARENT,
        "agent_role": route["agent_type"],
        "model": route["model"],
        "effort": route["effort"],
        "sandbox_policy_type": sandbox,
        "permission_profile_type": profile,
    }


def permission_source(*, source_kind: str = "parent_turn", source_id: str | None = None) -> dict:
    return {
        "source_kind": source_kind,
        "source_id": source_id or (PARENT if source_kind == "parent_turn" else "environment:test"),
        "sandbox_policy_type": "danger-full-access",
        "permission_profile_type": "disabled",
        "evidence_ref": "host:permission-source",
        "selection_evidence_ref": "host:permission-source-selection",
    }


def test_runtime_evidence_remains_explicit_diagnostic_not_default_hot_path():
    assert RUNTIME_VERIFIER.is_file() and RUNTIME_INSPECTOR.is_file()
    guardrails = GUARDRAILS.read_text(encoding="utf-8")
    orchestrate = ORCHESTRATE.read_text(encoding="utf-8")
    assert "Runtime evidence is on demand" in guardrails
    assert "Offline tests cannot satisfy this gate" in orchestrate
    assert "Configured/requested is not accepted. Accepted is not observed." in guardrails


def test_inspector_is_allowlisted_and_not_transcript_collection():
    source = RUNTIME_INSPECTOR.read_text(encoding="utf-8")
    doc = ATTESTATION.read_text(encoding="utf-8")
    for field in (
        "thread_id",
        "parent_thread_id",
        "agent_role",
        "model",
        "effort",
        "sandbox_policy_type",
        "permission_profile_type",
        "runtime_version",
    ):
        assert field in source
        assert field in doc
    assert 'record_type == "event_msg"' not in source
    assert "hidden reasoning" in doc
    assert "not cryptographically signed by the Host" in doc


@pytest.mark.parametrize("route", managed_routes(), ids=lambda route: route["agent_type"])
def test_exact_observed_route_and_permission_can_close_formal_attestation(route: dict):
    data = run_runtime_evidence(
        {
            "subject": "child",
            "expected": expected_for(route),
            "local": observed_for(route),
            "local_permission_source": permission_source(),
        }
    )
    assert data["status"] == "matched"
    assert data["decision"] == "continue"
    assert data["runtime_observation_complete"] is True
    assert data["permission_state_assurance"]["status"] == "verified"
    assert data["permission_provenance_assurance"]["status"] == "verified"


def test_configured_or_accepted_route_does_not_impersonate_observed_route():
    route = POLICY["roles"]["worker"]
    data = run_runtime_evidence(
        {"subject": "child", "expected": expected_for(route), "accepted": observed_for(route)}
    )
    assert data["truth_layers"]["accepted"]["status"] == "matched"
    assert data["truth_layers"]["observed"]["status"] == "not_observed"
    assert data["runtime_observation_complete"] is False
    assert data["decision"] == "return_to_main_session"


def test_cross_source_route_conflict_quarantines():
    route = POLICY["roles"]["worker"]
    native = observed_for(route)
    local = observed_for(route)
    local["model"] = "gpt-5.6-terra"
    data = run_runtime_evidence(
        {"subject": "child", "expected": expected_for(route), "native": native, "local": local}
    )
    assert data["status"] == "mismatch"
    assert data["decision"] == "quarantine"
    assert "source_conflict:model" in data["violations"]


def test_permission_source_identity_mismatch_is_independent_and_quarantined():
    route = POLICY["roles"]["reader"]
    data = run_runtime_evidence(
        {
            "subject": "child",
            "expected": expected_for(route),
            "local": observed_for(route),
            "local_permission_source": permission_source(source_id="22222222-2222-7222-8222-222222222222"),
        }
    )
    assert data["permission_state_assurance"]["status"] == "verified"
    assert data["permission_provenance_assurance"]["status"] == "failed"
    assert data["decision"] == "quarantine"


def test_fresh_context_and_exact_project_roles_remain_fixed():
    guardrails = GUARDRAILS.read_text(encoding="utf-8")
    assert "`fork_turns` is present and exactly `none`" in guardrails
    assert set(spec["agent_type"] for spec in POLICY["roles"].values()) == {
        "subagents_dispatch_reader",
        "subagents_dispatch_worker",
        "subagents_dispatch_solver",
        "subagents_dispatch_investigator",
        "subagents_dispatch_advisor",
    }
    metadata = (ROOT / "skills" / "orchestrate" / "agents" / "openai.yaml").read_text(encoding="utf-8")
    assert "allow_implicit_invocation: false" in metadata
