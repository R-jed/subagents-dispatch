from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "scripts" / "runtime-evidence.py"
THREAD = "11111111-1111-7111-8111-111111111111"
PARENT = "00000000-0000-7000-8000-000000000000"


def run_verifier(payload: dict):
    result = subprocess.run(
        [sys.executable, str(VERIFIER)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )
    return result, json.loads(result.stdout) if result.returncode == 0 else None


def expected(**overrides):
    value = {
        "thread_id": THREAD,
        "parent_thread_id": PARENT,
        "agent_role": "subagents_dispatch_worker",
        "model": "gpt-5.6-luna",
        "effort": "max",
        "runtime_observation_required": False,
        "requires_enforced_read_only": False,
    }
    value.update(overrides)
    return value


def observation(**overrides):
    value = {
        "thread_id": THREAD,
        "parent_thread_id": PARENT,
        "agent_role": "subagents_dispatch_worker",
        "model": "gpt-5.6-luna",
        "effort": "max",
        "sandbox_policy_type": "danger-full-access",
        "permission_profile_type": "disabled",
    }
    value.update(overrides)
    return value


def test_child_configuration_only_stays_c1():
    result, data = run_verifier({"expected": expected(), "native": None, "local": None})
    assert result.returncode == 0
    assert data["subject"] == "child"
    assert data["decision"] == "continue_configuration_only"
    assert data["evidence_grade"] == "C1_configuration_only"
    assert data["route_evidence"]["status"] == "not_observed"
    assert data["truth_layers"]["requested"]["status"] == "declared"
    assert data["truth_layers"]["accepted"]["status"] == "not_reported"
    assert data["truth_layers"]["observed"]["status"] == "not_observed"


def test_platform_acceptance_never_counts_as_observed_runtime_proof():
    result, data = run_verifier(
        {"expected": expected(), "accepted": observation(), "native": None, "local": None}
    )
    assert result.returncode == 0
    assert data["truth_layers"]["accepted"]["status"] == "matched"
    assert data["truth_layers"]["observed"]["status"] == "not_observed"
    assert data["runtime_reported"] is False
    assert data["evidence_grade"] == "C1_configuration_only"
    assert data["decision"] == "continue_configuration_only"


def test_accepted_route_mismatch_or_accepted_observed_drift_is_quarantined():
    result, data = run_verifier(
        {"expected": expected(), "accepted": observation(model="gpt-5.6-terra", effort="xhigh")}
    )
    assert result.returncode == 0
    assert data["decision"] == "quarantine"
    assert data["truth_layers"]["accepted"]["status"] == "conflict"
    assert "accepted:model_mismatch" in data["violations"]

    result, data = run_verifier(
        {
            "expected": expected(),
            "accepted": observation(),
            "native": observation(model="gpt-5.6-terra", effort="xhigh"),
        }
    )
    assert result.returncode == 0
    assert data["decision"] == "quarantine"
    assert data["truth_layers"]["observed"]["status"] == "conflict"
    assert "accepted_observed_conflict:model" in data["violations"]


def test_complete_native_child_route_is_r1_and_complete_agreement_is_r2():
    result, data = run_verifier({"subject": "child", "expected": expected(), "native": observation()})
    assert result.returncode == 0 and data["evidence_grade"] == "R1_runtime_reported"
    assert data["truth_layers"]["observed"]["status"] == "matched"
    result, data = run_verifier(
        {"subject": "child", "expected": expected(), "native": observation(), "local": observation()}
    )
    assert result.returncode == 0 and data["evidence_grade"] == "R2_runtime_reported_and_local_record_agree"


def test_partial_native_child_route_never_counts_as_runtime_proof():
    result, data = run_verifier(
        {"expected": expected(), "native": {"agent_role": "subagents_dispatch_worker"}}
    )
    assert result.returncode == 0
    assert data["evidence_grade"] == "C1_configuration_only"
    assert data["route_evidence"]["status"] == "partial"
    assert data["truth_layers"]["observed"]["status"] == "partial"


def test_runtime_required_rejects_partial_native_child_route():
    result, data = run_verifier(
        {
            "expected": expected(runtime_observation_required=True),
            "native": {"agent_role": "subagents_dispatch_worker", "model": "gpt-5.6-luna"},
        }
    )
    assert result.returncode == 0 and data["decision"] == "return_to_main_session"


def test_incomplete_expected_child_route_fails_closed():
    value = expected()
    del value["effort"]
    result, data = run_verifier({"expected": value, "native": observation()})
    assert result.returncode != 0 and data is None


def test_child_route_ancestry_and_permission_conflicts_remain_typed():
    result, data = run_verifier(
        {
            "expected": expected(),
            "native": observation(),
            "local": observation(model="gpt-5.6-terra", effort="xhigh"),
        }
    )
    assert result.returncode == 0
    assert data["decision"] == "quarantine"
    assert data["route_evidence"]["status"] == "conflict"

    result, data = run_verifier(
        {
            "expected": expected(),
            "native": observation(),
            "local": observation(parent_thread_id="22222222-2222-7222-8222-222222222222"),
        }
    )
    assert result.returncode == 0
    assert data["route_evidence"]["status"] == "matched"
    assert data["ancestry_evidence"]["status"] == "conflict"

    result, data = run_verifier(
        {
            "expected": expected(requires_enforced_read_only=True),
            "native": observation(),
            "effective_permission_source": {
                "source_kind": "parent_turn",
                "sandbox_policy_type": "danger-full-access",
                "permission_profile_type": "disabled",
            },
        }
    )
    assert result.returncode == 0
    assert data["permission_evidence"]["status"] == "broader_than_required"


def test_native_sol_main_provides_covered_judgment_state():
    result, data = run_verifier(
        {
            "subject": "main_session",
            "native": {"model": "gpt-5.6-sol", "effort": "high"},
        }
    )
    assert result.returncode == 0
    assert data["subject"] == "main_session"
    assert data["main_judgment_coverage"] == "covered"
    assert data["coverage_source"] == "trusted_session_metadata"
    assert data["evidence_grade"] == "R1_runtime_reported"
    assert data["truth_layers"]["observed"]["status"] == "matched"


def test_official_gpt_5_6_alias_is_treated_as_sol_coverage():
    result, data = run_verifier(
        {
            "subject": "main_session",
            "native": {"model": "gpt-5.6", "effort": "high"},
        }
    )
    assert result.returncode == 0
    assert data["main_judgment_coverage"] == "covered"
    assert data["coverage_source"] == "trusted_session_metadata"
    assert data["observed_main_model"] == "gpt-5.6"


def test_accepted_sol_main_without_native_observation_remains_unknown():
    result, data = run_verifier(
        {
            "subject": "main_session",
            "requested": {"model": "gpt-5.6-sol", "effort": "high"},
            "accepted": {"model": "gpt-5.6-sol", "effort": "high"},
        }
    )
    assert result.returncode == 0
    assert data["truth_layers"]["requested"]["status"] == "declared"
    assert data["truth_layers"]["accepted"]["status"] == "matched"
    assert data["truth_layers"]["observed"]["status"] == "not_observed"
    assert data["main_judgment_coverage"] == "unknown"
    assert data["coverage_source"] == "not_observed"


def test_native_non_sol_main_provides_uncovered_judgment_state():
    result, data = run_verifier(
        {
            "subject": "main_session",
            "native": {"model": "gpt-5.6-luna", "effort": "max"},
        }
    )
    assert result.returncode == 0
    assert data["main_judgment_coverage"] == "uncovered"
    assert data["observed_main_model"] == "gpt-5.6-luna"


def test_missing_partial_or_local_only_main_route_remains_unknown():
    for payload in [
        {"subject": "main_session"},
        {"subject": "main_session", "native": {"model": "gpt-5.6-sol"}},
        {
            "subject": "main_session",
            "local": {"model": "gpt-5.6-sol", "effort": "high"},
        },
    ]:
        result, data = run_verifier(payload)
        assert result.returncode == 0
        assert data["main_judgment_coverage"] == "unknown"
        assert data["coverage_source"] == "not_observed"


def test_conflicting_main_route_is_quarantined_and_unknown():
    result, data = run_verifier(
        {
            "subject": "main_session",
            "native": {"model": "gpt-5.6-sol", "effort": "high"},
            "local": {"model": "gpt-5.6-luna", "effort": "max"},
        }
    )
    assert result.returncode == 0
    assert data["status"] == "conflict"
    assert data["decision"] == "quarantine_main_route_claim"
    assert data["main_judgment_coverage"] == "unknown"
    assert data["evidence_grade"] == "X0_conflicted"


def test_unknown_subject_fails_closed():
    result, data = run_verifier({"subject": "mystery"})
    assert result.returncode != 0 and data is None
