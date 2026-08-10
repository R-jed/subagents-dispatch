from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
NORMALIZER = ROOT / "scripts" / "runtime-evidence.py"
POLICY = json.loads((ROOT / "contracts" / "policy.json").read_text(encoding="utf-8"))
THREAD = "11111111-1111-7111-8111-111111111111"
PARENT = "00000000-0000-7000-8000-000000000000"
WORKER = POLICY["roles"]["worker"]


def expected() -> dict:
    return {
        "thread_id": THREAD,
        "parent_thread_id": PARENT,
        "agent_role": WORKER["agent_type"],
        "model": WORKER["model"],
        "effort": WORKER["effort"],
        "runtime_observation_required": True,
        "requires_permission_observation": True,
    }


def full_observation() -> dict:
    return {
        "thread_id": THREAD,
        "parent_thread_id": PARENT,
        "agent_role": WORKER["agent_type"],
        "model": WORKER["model"],
        "effort": WORKER["effort"],
        "sandbox_policy_type": WORKER["sandbox_intent"],
        "permission_profile_type": "default",
        "runtime_version": "0.999.0-test",
    }


def normalize(payload: dict) -> dict:
    result = subprocess.run(
        [sys.executable, str(NORMALIZER)],
        cwd=ROOT,
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_exact_local_rollout_can_close_formal_runtime_observation():
    data = normalize(
        {
            "subject": "child",
            "expected": expected(),
            "local": full_observation(),
        }
    )

    assert data["status"] == "matched"
    assert data["decision"] == "continue"
    assert data["evidence_grade"] == "L1_local_record_observed"
    assert data["route_evidence"]["status"] == "matched"
    assert data["route_evidence"]["source"] == "local"
    assert data["truth_layers"]["observed"]["status"] == "matched"
    assert data["truth_layers"]["observed"]["fields"] == {
        "agent_role": WORKER["agent_type"],
        "model": WORKER["model"],
        "effort": WORKER["effort"],
    }
    assert data["truth_layers"]["observed"]["source_by_field"] == {
        "agent_role": "local",
        "model": "local",
        "effort": "local",
    }
    assert data["permission_evidence"] == {
        "expected_sandbox": WORKER["sandbox_intent"],
        "observed_sandbox": WORKER["sandbox_intent"],
        "source": "local",
        "status": "matched",
    }
    assert data["runtime_observation_complete"] is True
    assert data["runtime_reported"] is False
    assert data["local_record_observed"] is True


def test_public_and_local_runtime_sources_can_collectively_close_required_fields():
    native = {
        "thread_id": THREAD,
        "agent_role": WORKER["agent_type"],
        "model": WORKER["model"],
    }
    local = full_observation()
    del local["model"]

    data = normalize(
        {
            "subject": "child",
            "expected": expected(),
            "native": native,
            "local": local,
        }
    )

    assert data["status"] == "matched"
    assert data["decision"] == "continue"
    assert data["route_evidence"]["status"] == "matched"
    assert data["route_evidence"]["source"] == "both"
    assert data["truth_layers"]["observed"]["source_by_field"] == {
        "agent_role": "both",
        "model": "native",
        "effort": "local",
    }
    assert data["ancestry_evidence"] == {"status": "matched", "source": "local"}
    assert data["permission_evidence"]["source"] == "local"
    assert data["runtime_observation_complete"] is True


def test_public_and_local_runtime_conflict_quarantines_the_route():
    native = full_observation()
    local = full_observation()
    local["model"] = "gpt-5.6-terra"

    data = normalize(
        {
            "subject": "child",
            "expected": expected(),
            "native": native,
            "local": local,
        }
    )

    assert data["status"] == "mismatch"
    assert data["decision"] == "quarantine"
    assert data["evidence_grade"] == "X0_conflicted"
    assert data["route_evidence"]["status"] == "conflict"
    assert data["truth_layers"]["observed"]["status"] == "conflict"
    assert "model" in data["truth_layers"]["observed"]["conflict_fields"]
    assert "source_conflict:model" in data["violations"]
    assert "local:model_mismatch" in data["violations"]


def test_host_accepted_route_without_runtime_observation_never_closes_live_gate():
    data = normalize(
        {
            "subject": "child",
            "expected": expected(),
            "accepted": full_observation(),
        }
    )

    assert data["truth_layers"]["accepted"]["status"] == "matched"
    assert data["truth_layers"]["observed"]["status"] == "not_observed"
    assert data["status"] == "not_exposed"
    assert data["decision"] == "return_to_main_session"
    assert data["runtime_observation_complete"] is False
    assert data["evidence_grade"] == "C1_configuration_only"


def test_local_rollout_missing_effort_remains_unknown_for_formal_live_gate():
    local = full_observation()
    local["effort"] = None

    data = normalize(
        {
            "subject": "child",
            "expected": expected(),
            "local": local,
        }
    )

    assert data["route_evidence"]["status"] == "partial"
    assert data["truth_layers"]["observed"]["status"] == "partial"
    assert data["status"] == "not_exposed"
    assert data["decision"] == "return_to_main_session"
    assert data["runtime_observation_complete"] is False
    assert data["local_record_observed"] is False


def test_accepted_and_local_conflict_is_not_hidden_when_public_metadata_is_absent():
    accepted = full_observation()
    local = full_observation()
    accepted["effort"] = "high"

    data = normalize(
        {
            "subject": "child",
            "expected": expected(),
            "accepted": accepted,
            "local": local,
        }
    )

    assert data["status"] == "mismatch"
    assert data["decision"] == "quarantine"
    assert data["truth_layers"]["accepted"]["status"] == "conflict"
    assert data["truth_layers"]["observed"]["status"] == "conflict"
    assert "accepted:effort_mismatch" in data["violations"]
    assert "accepted_observed_conflict:effort" in data["violations"]
