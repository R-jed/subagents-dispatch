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


def native_for(route: dict, *, sandbox: str | None = None) -> dict:
    value = {
        "thread_id": THREAD,
        "parent_thread_id": PARENT,
        "agent_role": route["agent_type"],
        "model": route["model"],
        "effort": route["effort"],
        "sandbox_policy_type": route["sandbox_intent"] if sandbox is None else sandbox,
        "permission_profile_type": "default",
    }
    return value


@pytest.mark.parametrize("route", managed_routes(), ids=lambda route: route["agent_type"])
def test_live_route_permission_matches_policy_for_all_managed_roles(route: dict):
    data = run_runtime_evidence(
        {
            "subject": "child",
            "expected": expected_for(route),
            "native": native_for(route),
        }
    )

    assert data["status"] == "matched"
    assert data["decision"] == "continue"
    assert data["permission_evidence"]["status"] == "matched"
    assert data["permission_evidence"]["expected_sandbox"] == route["sandbox_intent"]
    assert data["permission_evidence"]["observed_sandbox"] == route["sandbox_intent"]
    assert data["permission_match"] is True


@pytest.mark.parametrize(
    ("agent_type", "wrong_sandbox"),
    [
        ("subagents_dispatch_worker", "read-only"),
        ("subagents_dispatch_solver", "read-only"),
    ],
)
def test_workspace_write_routes_quarantine_observed_sandbox_mismatch(
    agent_type: str,
    wrong_sandbox: str,
):
    route = next(item for item in managed_routes() if item["agent_type"] == agent_type)
    data = run_runtime_evidence(
        {
            "subject": "child",
            "expected": expected_for(route),
            "native": native_for(route, sandbox=wrong_sandbox),
        }
    )

    assert data["route_evidence"]["status"] == "matched"
    assert data["permission_evidence"]["status"] == "mismatch"
    assert data["permission_evidence"]["expected_sandbox"] == "workspace-write"
    assert data["permission_evidence"]["observed_sandbox"] == wrong_sandbox
    assert data["permission_match"] is False
    assert data["status"] == "mismatch"
    assert data["decision"] == "quarantine"
    assert data["evidence_grade"] == "X0_conflicted"
    assert "permission:sandbox_intent_mismatch" in data["violations"]


def test_required_permission_absence_stays_unknown_in_doctor_classification():
    route = next(
        item
        for item in managed_routes()
        if item["agent_type"] == "subagents_dispatch_worker"
    )
    native = native_for(route)
    del native["sandbox_policy_type"]

    data = run_runtime_evidence(
        {
            "subject": "child",
            "expected": expected_for(route),
            "native": native,
        }
    )

    assert data["route_evidence"]["status"] == "matched"
    assert data["permission_evidence"] == {
        "expected_sandbox": "workspace-write",
        "status": "not_observed",
        "source": "none",
    }
    assert data["permission_match"] is None
    assert data["status"] == "not_exposed"
    assert data["decision"] == "return_to_main_session"
    assert data["violations"] == []

    doctor = load_doctor_module()
    status, _ = doctor._runtime_status(data)
    assert status == "UNKNOWN"


def test_doctor_live_route_contract_requires_permission_observation():
    skill = (ROOT / "skills" / "doctor" / "SKILL.md").read_text(encoding="utf-8")
    assert "requires_permission_observation=true" in skill
    assert "sandbox_intent" in skill
    assert "contracts/policy.json" in skill


def test_runtime_assurance_cases_cover_workspace_write_permission_fail_closed():
    payload = json.loads(RUNTIME_CASES.read_text(encoding="utf-8"))
    ids = {case["id"] for case in payload["cases"]}
    assert {
        "required-workspace-write-native-unobserved",
        "required-workspace-write-mismatch",
    } <= ids
