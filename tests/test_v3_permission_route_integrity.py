from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_VERIFIER = ROOT / "scripts" / "runtime-evidence.py"
DOCTOR = ROOT / "scripts" / "doctor.py"
POLICY = ROOT / "contracts" / "policy.json"
RUNTIME_CASES = ROOT / "evals" / "runtime-assurance-cases.json"
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


def load_doctor_module():
    scripts = str(ROOT / "scripts")
    sys.path.insert(0, scripts)
    try:
        spec = importlib.util.spec_from_file_location("doctor_permission_under_test", DOCTOR)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts)


def managed_routes() -> list[dict]:
    payload = json.loads(POLICY.read_text(encoding="utf-8"))
    return list(payload["roles"].values())


def expected_for(route: dict) -> dict:
    return {
        "thread_id": THREAD,
        "parent_thread_id": PARENT,
        "agent_role": route["agent_type"],
        "model": route["model"],
        "effort": route["effort"],
        "runtime_observation_required": True,
        "requires_enforced_read_only": False,
        "requires_permission_observation": True,
    }


def native_for(
    route: dict,
    *,
    sandbox: str = "danger-full-access",
    profile: str = "disabled",
) -> dict:
    value = {
        "thread_id": THREAD,
        "parent_thread_id": PARENT,
        "agent_role": route["agent_type"],
        "model": route["model"],
        "effort": route["effort"],
        "sandbox_policy_type": sandbox,
        "permission_profile_type": profile,
    }
    return value


def host_permission_source(
    *,
    source_kind: str = "parent_turn",
    source_id: str | None = None,
    sandbox: str = "danger-full-access",
    profile: str = "disabled",
) -> dict:
    return {
        "source_kind": source_kind,
        "source_id": source_id or (PARENT if source_kind == "parent_turn" else "environment:test"),
        "sandbox_policy_type": sandbox,
        "permission_profile_type": profile,
        "evidence_ref": "host:effective-permission-source",
        "selection_evidence_ref": "host:permission-source-selection",
    }


@pytest.mark.parametrize("route", managed_routes(), ids=lambda route: route["agent_type"])
def test_live_route_permission_matches_host_observed_source_for_all_managed_roles(route: dict):
    data = run_runtime_evidence(
        {
            "subject": "child",
            "expected": expected_for(route),
            "native": native_for(route),
            "native_permission_source": host_permission_source(),
        }
    )

    assert data["status"] == "matched"
    assert data["decision"] == "continue"
    assert data["permission_state_assurance"]["status"] == "verified"
    assert data["permission_state_assurance"]["observed_sandbox"] == "danger-full-access"
    assert data["permission_provenance_assurance"]["status"] == "verified"
    assert data["permission_provenance_assurance"]["source_kind"] == "parent_turn"
    assert data["permission_provenance_assurance"]["source_id"] == PARENT


@pytest.mark.parametrize("route", managed_routes(), ids=lambda route: route["agent_type"])
def test_read_only_environment_source_is_host_observed_for_all_managed_roles(route: dict):
    data = run_runtime_evidence(
        {
            "subject": "child",
            "expected": expected_for(route),
            "native": native_for(route, sandbox="read-only", profile="default"),
            "native_permission_source": host_permission_source(
                source_kind="selected_environment",
                sandbox="read-only",
                profile="default",
            ),
        }
    )
    assert data["permission_state_assurance"]["status"] == "verified"
    assert data["permission_provenance_assurance"]["status"] == "verified"
    assert data["permission_provenance_assurance"]["source_id"] == "environment:test"
    assert data["decision"] == "continue"


def test_permission_profile_mismatch_quarantines_even_when_sandbox_matches():
    route = managed_routes()[0]
    data = run_runtime_evidence(
        {
            "subject": "child",
            "expected": expected_for(route),
            "native": native_for(route),
            "native_permission_source": host_permission_source(profile="default"),
        }
    )
    assert data["permission_state_assurance"]["status"] == "verified"
    assert data["permission_provenance_assurance"]["status"] == "failed"
    assert data["decision"] == "quarantine"


def test_incomplete_host_permission_source_remains_unknown():
    route = managed_routes()[0]
    source = host_permission_source()
    del source["permission_profile_type"]
    data = run_runtime_evidence(
        {
            "subject": "child",
            "expected": expected_for(route),
            "native": native_for(route),
            "native_permission_source": source,
        }
    )
    assert data["permission_state_assurance"]["status"] == "verified"
    assert data["permission_provenance_assurance"]["status"] == "unknown"
    assert data["decision"] == "continue"


def test_permission_source_without_provenance_cannot_close_a_provenance_gate():
    route = managed_routes()[0]
    source = host_permission_source()
    del source["evidence_ref"]
    data = run_runtime_evidence(
        {
            "subject": "child",
            "expected": expected_for(route),
            "native": native_for(route),
            "native_permission_source": source,
        }
    )
    assert data["permission_state_assurance"]["status"] == "verified"
    assert data["permission_provenance_assurance"]["status"] == "unknown"
    assert data["decision"] == "continue"


def test_parent_permission_source_identity_mismatch_quarantines():
    route = managed_routes()[0]
    data = run_runtime_evidence(
        {
            "subject": "child",
            "expected": expected_for(route),
            "native": native_for(route),
            "native_permission_source": host_permission_source(
                source_id="22222222-2222-7222-8222-222222222222"
            ),
        }
    )
    assert data["permission_state_assurance"]["status"] == "verified"
    assert data["permission_provenance_assurance"]["status"] == "failed"
    assert data["decision"] == "quarantine"
    assert "permission:source_identity_mismatch" in data["violations"]


@pytest.mark.parametrize(
    ("agent_type", "wrong_sandbox"),
    [
        ("subagents_dispatch_reader", "read-only"),
        ("subagents_dispatch_worker", "read-only"),
    ],
)
def test_routes_quarantine_observed_provenance_state_mismatch(
    agent_type: str,
    wrong_sandbox: str,
):
    route = next(item for item in managed_routes() if item["agent_type"] == agent_type)
    data = run_runtime_evidence(
        {
            "subject": "child",
            "expected": expected_for(route),
            "native": native_for(route, sandbox=wrong_sandbox),
            "native_permission_source": host_permission_source(),
        }
    )

    assert data["route_evidence"]["status"] == "matched"
    assert data["permission_state_assurance"]["status"] == "verified"
    assert data["permission_state_assurance"]["observed_sandbox"] == wrong_sandbox
    assert data["permission_provenance_assurance"]["status"] == "failed"
    assert data["permission_provenance_assurance"]["source_sandbox"] == "danger-full-access"
    assert data["status"] == "mismatch"
    assert data["decision"] == "quarantine"
    assert data["evidence_grade"] == "X0_conflicted"
    assert "permission:provenance_state_mismatch" in data["violations"]


def test_observed_permission_state_stays_verified_when_provenance_is_absent():
    route = next(
        item
        for item in managed_routes()
        if item["agent_type"] == "subagents_dispatch_worker"
    )
    data = run_runtime_evidence(
        {
            "subject": "child",
            "expected": expected_for(route),
            "native": native_for(route),
        }
    )

    assert data["route_evidence"]["status"] == "matched"
    assert data["permission_state_assurance"]["status"] == "verified"
    assert data["permission_provenance_assurance"]["status"] == "unknown"
    assert data["decision"] == "continue"
    assert data["violations"] == []

    doctor = load_doctor_module()
    status, _ = doctor._runtime_status(data)
    assert status == "OK"


def test_doctor_live_route_contract_keeps_permission_state_and_provenance_separate():
    skill = (ROOT / "skills" / "doctor" / "SKILL.md").read_text(encoding="utf-8")
    assert "requires_permission_observation=true" in skill
    assert "requires_permission_provenance=true" in skill
    assert "native_permission_source" in skill
    assert "candidate source kinds" in skill
    assert "Never infer a source from equal permission values" in skill
    assert "contracts/policy.json" in skill


def test_runtime_assurance_cases_cover_permission_provenance_fail_closed():
    payload = json.loads(RUNTIME_CASES.read_text(encoding="utf-8"))
    ids = {case["id"] for case in payload["cases"]}
    assert {
        "required-permission-provenance-unobserved",
        "required-permission-provenance-unbound",
        "required-permission-provenance-identity-mismatch",
        "required-permission-provenance-state-mismatch",
    } <= ids


def test_accepted_permission_override_is_non_blocking_and_does_not_relabel_route_truth_layers():
    route = next(
        item
        for item in managed_routes()
        if item["agent_type"] == "subagents_dispatch_worker"
    )
    accepted = native_for(route, sandbox="read-only")
    native = native_for(route)

    data = run_runtime_evidence(
        {
            "subject": "child",
            "expected": expected_for(route),
            "accepted": accepted,
            "native": native,
            "native_permission_source": host_permission_source(),
        }
    )

    assert data["route_evidence"]["status"] == "matched"
    assert data["truth_layers"]["accepted"]["status"] == "matched"
    assert data["truth_layers"]["observed"]["status"] == "matched"
    assert data["permission_state_assurance"]["status"] == "verified"
    assert data["permission_provenance_assurance"]["status"] == "verified"
    assert data["status"] == "matched"
    assert data["decision"] == "continue"


def test_permission_observation_requires_both_child_permission_fields():
    route = next(
        item
        for item in managed_routes()
        if item["agent_type"] == "subagents_dispatch_worker"
    )
    native = native_for(route)
    del native["permission_profile_type"]

    data = run_runtime_evidence(
        {
            "subject": "child",
            "expected": expected_for(route),
            "native": native,
            "native_permission_source": host_permission_source(),
        }
    )

    assert data["route_evidence"]["status"] == "matched"
    assert data["permission_state_assurance"]["status"] == "unknown"
    assert data["permission_provenance_assurance"]["status"] == "unknown"
    assert data["status"] == "not_exposed"
    assert data["decision"] == "return_to_main_session"


def test_enforced_read_only_remains_an_independent_security_gate():
    route = next(item for item in managed_routes() if item["agent_type"] == "subagents_dispatch_reader")
    expected = expected_for(route)
    expected["requires_enforced_read_only"] = True
    data = run_runtime_evidence(
        {
            "subject": "child",
            "expected": expected,
            "native": native_for(route),
            "native_permission_source": host_permission_source(),
        }
    )
    assert data["permission_state_assurance"]["status"] == "failed"
    assert data["permission_provenance_assurance"]["status"] == "verified"
    assert data["status"] == "mismatch"
    assert data["decision"] == "quarantine"


def test_hard_read_only_documentation_blocks_when_main_is_not_host_enforced_read_only():
    guardrails = (ROOT / "contracts" / "guardrails.md").read_text(encoding="utf-8")
    assert "Main itself is proven Host-enforced read-only" in guardrails
    assert "otherwise the responsibility remains blocked" in guardrails
