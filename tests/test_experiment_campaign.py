from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate-experiment-campaign.py"
POLICY = json.loads((ROOT / "contracts" / "policy.json").read_text(encoding="utf-8"))


def head_sha() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip()


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def assurance(claim_kind: str) -> dict:
    return {
        "claim_kind": claim_kind,
        "required": ["route", "permission_state"],
        "allow_unknown": ["permission_provenance"],
    }


def workload(*, calibration_role: str | None = None, formal: bool = False) -> dict:
    task = "Inspect one frozen responsibility and verify its exact acceptance oracle."
    item = {
        "id": "fixture-workload",
        "repository_url": "https://github.com/example/repo.git" if formal else "https://example.invalid/repo.git",
        "base_revision": "b" * 40,
        "source_task_ref": None,
        "task_text": task,
        "task_sha256": digest(task),
        "reset_procedure": ["reset to base revision"],
        "acceptance": {"rubric_id": "fixture-v1", "oracle_kind": "deterministic", "verification": ["verify fixture"]},
        "controls": {
            "main_session_route_fingerprint": "main-v1",
            "permissions_fingerprint": "permissions-v1",
            "tool_surface_fingerprint": "tools-v1",
            "project_rule_refs": [],
        },
    }
    if calibration_role is None:
        item["benchmark_stratum"] = "small_bounded"
    else:
        packet = "OBJECTIVE\nBounded calibration responsibility\nRETURN\nEvidence"
        item.update(
            calibration_role=calibration_role,
            responsibility_packet_sha256=digest(packet),
            responsibility_packet_ref="fixture:packet",
        )
    return item


def calibration_campaign(*, role_id: str = "programmer", stage: str = "exploratory", promotion: bool = False) -> dict:
    spec = POLICY["roles"][role_id]
    control_effort = spec["allowed_efforts"][0]
    challenger = {
        "id": "challenger",
        "model": "gpt-5.6-sol" if role_id == "programmer" else "gpt-5.6-luna",
        "effort": "high" if role_id == "programmer" else "max",
        "mutation_authority": "none",
    }
    return {
        "schema_version": "3.0",
        "campaign_id": f"{role_id}-calibration",
        "stage": stage,
        "model_provider_control": "openai",
        "plugin_candidate_sha": head_sha(),
        "host_target": {"product": "Codex", "version": "fixture", "platform": "fixture"},
        "repeat_policy": {
            "minimum_completed_per_arm": 3 if stage == "formal" else 1,
            "ordering": "interleaved",
            "fixed_order_reason": None,
        },
        "assurance_requirements": assurance("model_effort"),
        "experiment": {
            "type": "role_calibration",
            "policy_promotion": promotion,
            "promotion_criteria_ref": "evals/criteria/promotion.md" if promotion else None,
            "roles": [{
                "role": role_id,
                "contract_ref": f"contracts/routing.md#{role_id}",
                "control": {"id": "control", "model": spec["model"], "effort": control_effort, "mutation_authority": "none"},
                "challengers": [challenger],
            }],
        },
        "workloads": [workload(calibration_role=role_id, formal=stage == "formal")],
    }


def product_campaign(*, stage: str = "formal") -> dict:
    return {
        "schema_version": "3.0",
        "campaign_id": "product-benchmark",
        "stage": stage,
        "plugin_candidate_sha": head_sha(),
        "host_target": {"product": "Codex", "version": "fixture", "platform": "fixture"},
        "repeat_policy": {
            "minimum_completed_per_arm": 3 if stage == "formal" else 1,
            "ordering": "randomized",
            "fixed_order_reason": None,
        },
        "assurance_requirements": assurance("product_behavior"),
        "experiment": {"type": "product_benchmark", "baseline_mode": "single_agent", "candidate_mode": "dispatch"},
        "workloads": [workload(formal=stage == "formal")],
    }


def validate(tmp_path: Path, payload: dict) -> subprocess.CompletedProcess[str]:
    path = tmp_path / "campaign.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return subprocess.run([sys.executable, str(VALIDATOR), str(path), "--json"], cwd=ROOT, text=True, capture_output=True)


def test_role_calibration_uses_canonical_profile_identity_but_explicit_route_challengers(tmp_path: Path):
    for role_id in ("programmer", "product_manager", "department_director"):
        result = validate(tmp_path, calibration_campaign(role_id=role_id))
        assert result.returncode == 0, result.stderr
        summary = json.loads(result.stdout)
        assert summary["roles"] == [role_id]
        assert len(summary["campaign_sha256"]) == 64


def test_control_must_be_current_production_route(tmp_path: Path):
    payload = calibration_campaign(role_id="product_manager")
    payload["experiment"]["roles"][0]["control"]["effort"] = "xhigh"
    result = validate(tmp_path, payload)
    assert result.returncode != 0
    assert "current production policy route" in result.stderr


def test_challenger_may_be_outside_production_but_must_preserve_mutation_authority(tmp_path: Path):
    payload = calibration_campaign()
    challenger = payload["experiment"]["roles"][0]["challengers"][0]
    assert challenger["model"] != POLICY["roles"]["programmer"]["model"]
    assert validate(tmp_path, payload).returncode == 0
    challenger["mutation_authority"] = "bounded-source-write"
    result = validate(tmp_path, payload)
    assert result.returncode != 0
    assert "changes mutation_authority" in result.stderr


def test_duplicate_route_or_second_calibration_role_is_rejected(tmp_path: Path):
    payload = calibration_campaign()
    control = payload["experiment"]["roles"][0]["control"]
    payload["experiment"]["roles"][0]["challengers"][0] = {**control, "id": "other"}
    result = validate(tmp_path, payload)
    assert result.returncode != 0
    assert "identical" in result.stderr

    payload = calibration_campaign()
    payload["experiment"]["roles"].append(payload["experiment"]["roles"][0])
    assert validate(tmp_path, payload).returncode != 0


def test_formal_promotion_requires_formal_campaign_and_three_repeats(tmp_path: Path):
    result = validate(tmp_path, calibration_campaign(promotion=True))
    assert result.returncode != 0
    assert "policy promotion requires a formal campaign" in result.stderr
    payload = calibration_campaign(stage="formal", promotion=True)
    payload["repeat_policy"]["minimum_completed_per_arm"] = 2
    assert validate(tmp_path, payload).returncode != 0


def test_campaign_binds_current_candidate_and_exact_task_bytes(tmp_path: Path):
    payload = calibration_campaign()
    payload["plugin_candidate_sha"] = "0" * 40
    assert "exact current Git HEAD" in validate(tmp_path, payload).stderr
    payload = calibration_campaign()
    payload["workloads"][0]["task_sha256"] = "0" * 64
    assert "task_sha256" in validate(tmp_path, payload).stderr


def test_product_benchmark_rejects_calibration_fields_and_calibration_rejects_benchmark_fields(tmp_path: Path):
    payload = product_campaign()
    payload["workloads"][0]["calibration_role"] = "programmer"
    assert validate(tmp_path, payload).returncode != 0
    payload = calibration_campaign()
    payload["workloads"][0]["benchmark_stratum"] = "small_bounded"
    result = validate(tmp_path, payload)
    assert result.returncode != 0
    assert "benchmark_stratum" in result.stderr


def test_campaign_requires_complete_assurance_classification_and_frozen_provider(tmp_path: Path):
    payload = calibration_campaign()
    payload["assurance_requirements"]["allow_unknown"] = []
    assert "classify every assurance dimension" in validate(tmp_path, payload).stderr
    payload = calibration_campaign()
    payload["model_provider_control"] = "TBD"
    assert "model_provider_control" in validate(tmp_path, payload).stderr


def test_formal_workload_cannot_use_placeholder_repository(tmp_path: Path):
    payload = product_campaign()
    payload["workloads"][0]["repository_url"] = "https://example.invalid/repo.git"
    result = validate(tmp_path, payload)
    assert result.returncode != 0
    assert "real repository" in result.stderr
