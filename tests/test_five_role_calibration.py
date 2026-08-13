from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tomllib

import pytest

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate-experiment-campaign.py"
POLICY = json.loads((ROOT / "contracts" / "policy.json").read_text(encoding="utf-8"))
ROLES = ("worker", "solver", "investigator", "advisor")

sys.path.insert(0, str(ROOT / "scripts"))
from calibration_profile_contract import materialized_agent_type, role_contract_digest  # noqa: E402
from calibration_profiles import _load_policy, _profile_records  # noqa: E402
sys.path.pop(0)


def head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip()


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def profile(role: str) -> dict:
    path = ROOT / "agent-profiles" / POLICY["roles"][role]["profile_file"]
    return tomllib.loads(path.read_text(encoding="utf-8"))


def contract(role: str) -> str:
    item = profile(role)
    return role_contract_digest(role, item["description"], item["developer_instructions"], POLICY["roles"][role]["mutation_authority"])


def arm(role: str, campaign_id: str, route_id: str, challenger: bool) -> dict:
    current = POLICY["roles"][role]
    model = "gpt-5.6-terra" if challenger else current["model"]
    effort = "high" if challenger else current["effort"]
    return {
        "id": route_id,
        "semantic_role": role,
        "model": model,
        "effort": effort,
        "configured_model": model,
        "configured_effort": effort,
        "materialized_agent_type": materialized_agent_type(campaign_id, role, route_id),
        "role_contract_digest": contract(role),
        "mutation_authority": current["mutation_authority"],
    }


def campaign(role: str) -> dict:
    campaign_id = f"{role}-calibration-fixture"
    task = f"Exercise one bounded {role} responsibility."
    packet = f"OBJECTIVE\nBounded {role} responsibility.\nRETURN\nEvidence."
    return {
        "schema_version": "2.0",
        "campaign_id": campaign_id,
        "stage": "exploratory",
        "materialization_mode": "profile_only",
        "model_provider_control": "openai",
        "plugin_candidate_sha": head(),
        "host_target": {"product": "Codex", "version": "fixture", "platform": "fixture"},
        "repeat_policy": {"minimum_completed_per_arm": 1, "ordering": "interleaved", "fixed_order_reason": None},
        "assurance_requirements": {"claim_kind": "model_effort", "required": ["route", "permission_state"], "allow_unknown": ["permission_provenance"]},
        "experiment": {
            "type": "role_calibration",
            "policy_promotion": False,
            "promotion_criteria_ref": None,
            "roles": [{
                "role": role,
                "contract_ref": f"contracts/routing.md#{role}",
                "control": arm(role, campaign_id, "current", False),
                "challengers": [arm(role, campaign_id, "terra-high", True)],
            }],
        },
        "workloads": [{
            "id": f"{role}-fixture",
            "calibration_role": role,
            "responsibility_packet_sha256": digest(packet),
            "responsibility_packet_ref": f"fixture:{role}",
            "repository_url": "https://example.invalid/repository.git",
            "base_revision": "b" * 40,
            "source_task_ref": None,
            "task_text": task,
            "task_sha256": digest(task),
            "reset_procedure": ["reset immutable fixture"],
            "acceptance": {"rubric_id": "fixture-v1", "oracle_kind": "deterministic", "verification": ["inspect expected fixture"]},
            "controls": {"main_session_route_fingerprint": "main-v1", "permissions_fingerprint": "permissions-v1", "tool_surface_fingerprint": "tools-v1", "project_rule_refs": []},
        }],
    }


def validate(tmp_path: Path, payload: dict) -> subprocess.CompletedProcess[str]:
    path = tmp_path / "campaign.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return subprocess.run([sys.executable, str(VALIDATOR), str(path), "--json"], cwd=ROOT, text=True, capture_output=True)


@pytest.mark.parametrize("role", ROLES)
def test_non_reader_role_uses_exact_canonical_contract(tmp_path: Path, role: str):
    payload = campaign(role)
    result = validate(tmp_path, payload)
    assert result.returncode == 0, result.stderr
    records, contract_data = _profile_records(payload, _load_policy())
    assert len(records) == 2
    assert contract_data["digest"] == contract(role)
    canonical = profile(role)
    for record in records:
        generated = tomllib.loads(record["profile_bytes"].decode())
        assert generated["description"] == canonical["description"]
        assert generated["developer_instructions"] == canonical["developer_instructions"]
        assert generated["name"] == record["materialized_agent_type"]
        assert generated["model"] == record["configured_model"]
        assert generated["model_reasoning_effort"] == record["configured_effort"]


@pytest.mark.parametrize("role", ROLES)
def test_non_reader_challenger_cannot_change_authority(tmp_path: Path, role: str):
    payload = campaign(role)
    challenger = payload["experiment"]["roles"][0]["challengers"][0]
    challenger["mutation_authority"] = "none" if challenger["mutation_authority"] != "none" else "bounded-source-write"
    result = validate(tmp_path, payload)
    assert result.returncode != 0
    assert "changes mutation_authority" in result.stderr


def test_profile_only_campaign_is_one_role(tmp_path: Path):
    payload = campaign("worker")
    payload["experiment"]["roles"].append(campaign("solver")["experiment"]["roles"][0])
    result = validate(tmp_path, payload)
    assert result.returncode != 0
    assert "requires exactly one semantic role" in result.stderr
