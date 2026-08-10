from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate-role-calibration.py"
POLICY = json.loads((ROOT / "contracts" / "policy.json").read_text(encoding="utf-8"))


def task_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def route(role: str, *, route_id: str, challenger: bool = False) -> dict:
    configured = POLICY["roles"][role]
    model = configured["model"] if not challenger else f"{configured['model']}-candidate"
    return {
        "id": route_id,
        "model": model,
        "effort": configured["effort"],
        "sandbox_intent": configured["sandbox_intent"],
    }


def campaign(*, purpose: str = "exploratory", repeats: int = 1) -> dict:
    role_name = "reader"
    task = "Trace one exact call path in the frozen repository and cite the defining symbols."
    payload = {
        "schema_version": "1.0",
        "campaign_id": "reader-calibration-fixture",
        "purpose": purpose,
        "plugin_candidate_sha": "a" * 40,
        "host_target": {
            "product": "Codex",
            "version": "fixture-runtime",
            "platform": "fixture-platform",
        },
        "repeat_policy": {
            "minimum_completed_per_arm": repeats,
            "ordering": "interleaved",
            "fixed_order_reason": None,
        },
        "roles": [
            {
                "role": role_name,
                "contract_ref": "contracts/routing.md#narrow-read-only-factual-work",
                "control": route(role_name, route_id="current"),
                "challengers": [route(role_name, route_id="candidate", challenger=True)],
            }
        ],
        "workloads": [
            {
                "id": "real-repo-reader-fixture",
                "role": role_name,
                "repository_url": "https://example.invalid/repository.git",
                "base_revision": "b" * 40,
                "source_task_ref": None,
                "task_text": task,
                "task_sha256": task_hash(task),
                "reset_procedure": ["reset to the immutable base revision"],
                "acceptance": {
                    "rubric_id": "reader-fixture-v1",
                    "oracle_kind": "deterministic",
                    "verification": ["inspect the frozen expected symbol map"],
                },
                "controls": {
                    "permissions_fingerprint": "fixture-read-only-v1",
                    "tool_surface_fingerprint": "fixture-tools-v1",
                    "project_rule_refs": [],
                },
            }
        ],
        "promotion_criteria_ref": None,
    }
    if purpose == "policy_promotion":
        payload["promotion_criteria_ref"] = "evals/criteria/fixture.md"
    return payload


def run_validator(tmp_path: Path, payload: dict) -> subprocess.CompletedProcess[str]:
    path = tmp_path / "campaign.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(path), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_valid_exploratory_campaign_is_frozen_with_sha256(tmp_path: Path):
    result = run_validator(tmp_path, campaign())
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["campaign_id"] == "reader-calibration-fixture"
    assert summary["purpose"] == "exploratory"
    assert summary["roles"] == ["reader"]
    assert summary["workload_count"] == 1
    assert len(summary["campaign_sha256"]) == 64


def test_policy_promotion_requires_three_repeats(tmp_path: Path):
    result = run_validator(tmp_path, campaign(purpose="policy_promotion", repeats=2))
    assert result.returncode != 0
    assert "minimum_completed_per_arm" in result.stderr


def test_control_must_match_current_policy(tmp_path: Path):
    payload = campaign()
    payload["roles"][0]["control"]["model"] = "not-the-current-policy-model"
    result = run_validator(tmp_path, payload)
    assert result.returncode != 0
    assert "control must exactly match the current policy route" in result.stderr


def test_challenger_cannot_change_sandbox_contract(tmp_path: Path):
    payload = campaign()
    challenger = payload["roles"][0]["challengers"][0]
    challenger["sandbox_intent"] = "workspace-write"
    result = run_validator(tmp_path, payload)
    assert result.returncode != 0
    assert "changes sandbox_intent" in result.stderr


def test_task_hash_binds_exact_task_bytes(tmp_path: Path):
    payload = campaign()
    payload["workloads"][0]["task_sha256"] = "0" * 64
    result = run_validator(tmp_path, payload)
    assert result.returncode != 0
    assert "task_sha256 does not match exact UTF-8 task_text" in result.stderr


def test_unresolved_control_fingerprints_cannot_be_frozen(tmp_path: Path):
    payload = campaign()
    payload["workloads"][0]["controls"]["tool_surface_fingerprint"] = "TBD"
    result = run_validator(tmp_path, payload)
    assert result.returncode != 0
    assert "unresolved tool_surface_fingerprint" in result.stderr


def test_duplicate_route_shape_is_rejected(tmp_path: Path):
    payload = campaign()
    control = payload["roles"][0]["control"]
    payload["roles"][0]["challengers"][0] = {
        "id": "different-id",
        "model": control["model"],
        "effort": control["effort"],
        "sandbox_intent": control["sandbox_intent"],
    }
    result = run_validator(tmp_path, payload)
    assert result.returncode != 0
    assert "challenger identical to another route" in result.stderr
