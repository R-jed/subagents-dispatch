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
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()


def task_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def route(role: str, *, route_id: str, challenger: bool = False) -> dict:
    configured = POLICY["roles"][role]
    return {
        "id": route_id,
        "model": configured["model"] if not challenger else f"{configured['model']}-candidate",
        "effort": configured["effort"],
        "sandbox_intent": configured["sandbox_intent"],
    }


def workload(*, formal: bool, calibration_role: str | None = None, benchmark_stratum: str | None = None) -> dict:
    task = "Trace one exact call path in the frozen repository and verify the expected defining symbols."
    payload = {
        "id": "real-repo-fixture",
        "repository_url": (
            "https://github.com/example/repository.git"
            if formal
            else "https://example.invalid/repository.git"
        ),
        "base_revision": "b" * 40,
        "source_task_ref": None,
        "task_text": task,
        "task_sha256": task_hash(task),
        "reset_procedure": ["reset to the immutable base revision"],
        "acceptance": {
            "rubric_id": "fixture-v1",
            "oracle_kind": "deterministic",
            "verification": ["inspect the frozen expected symbol map"],
        },
        "controls": {
            "main_session_route_fingerprint": "fixture-main-route-v1",
            "permissions_fingerprint": "fixture-read-only-v1",
            "tool_surface_fingerprint": "fixture-tools-v1",
            "project_rule_refs": [],
        },
    }
    if calibration_role is not None:
        payload["calibration_role"] = calibration_role
    if benchmark_stratum is not None:
        payload["benchmark_stratum"] = benchmark_stratum
    return payload


def role_campaign(*, stage: str = "exploratory", repeats: int = 1, promotion: bool = False) -> dict:
    role_name = "reader"
    return {
        "schema_version": "2.0",
        "campaign_id": "reader-calibration-fixture",
        "stage": stage,
        "plugin_candidate_sha": head_sha(),
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
        "experiment": {
            "type": "role_calibration",
            "policy_promotion": promotion,
            "promotion_criteria_ref": "evals/criteria/fixture.md" if promotion else None,
            "roles": [
                {
                    "role": role_name,
                    "contract_ref": "contracts/routing.md#narrow-read-only-factual-work",
                    "control": route(role_name, route_id="current"),
                    "challengers": [route(role_name, route_id="candidate", challenger=True)],
                }
            ],
        },
        "workloads": [workload(formal=stage == "formal", calibration_role=role_name)],
    }


def product_campaign(*, stage: str = "formal", repeats: int = 3) -> dict:
    return {
        "schema_version": "2.0",
        "campaign_id": "single-vs-dispatch-fixture",
        "stage": stage,
        "plugin_candidate_sha": head_sha(),
        "host_target": {
            "product": "Codex",
            "version": "fixture-runtime",
            "platform": "fixture-platform",
        },
        "repeat_policy": {
            "minimum_completed_per_arm": repeats,
            "ordering": "randomized",
            "fixed_order_reason": None,
        },
        "experiment": {
            "type": "product_benchmark",
            "baseline_mode": "single_agent",
            "candidate_mode": "dispatch",
        },
        "workloads": [
            workload(
                formal=stage == "formal",
                benchmark_stratum="small_bounded",
            )
        ],
    }


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


def test_valid_exploratory_role_calibration_is_frozen_with_sha256(tmp_path: Path):
    result = run_validator(tmp_path, role_campaign())
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["campaign_id"] == "reader-calibration-fixture"
    assert summary["stage"] == "exploratory"
    assert summary["experiment_type"] == "role_calibration"
    assert summary["roles"] == ["reader"]
    assert summary["plugin_candidate_sha"] == head_sha()
    assert len(summary["campaign_sha256"]) == 64


def test_valid_product_benchmark_does_not_predeclare_role_challengers(tmp_path: Path):
    result = run_validator(tmp_path, product_campaign())
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["experiment_type"] == "product_benchmark"
    assert summary["roles"] == []
    assert summary["minimum_completed_per_arm"] == 3


def test_formal_campaign_requires_three_repeats(tmp_path: Path):
    result = run_validator(tmp_path, product_campaign(repeats=2))
    assert result.returncode != 0
    assert "minimum_completed_per_arm" in result.stderr


def test_policy_promotion_requires_formal_stage(tmp_path: Path):
    result = run_validator(tmp_path, role_campaign(promotion=True))
    assert result.returncode != 0
    assert "policy promotion requires a formal campaign" in result.stderr


def test_control_must_match_current_policy(tmp_path: Path):
    payload = role_campaign()
    payload["experiment"]["roles"][0]["control"]["model"] = "not-the-current-policy-model"
    result = run_validator(tmp_path, payload)
    assert result.returncode != 0
    assert "control must exactly match the current policy route" in result.stderr


def test_challenger_cannot_change_sandbox_contract(tmp_path: Path):
    payload = role_campaign()
    control = payload["experiment"]["roles"][0]["control"]
    challenger = payload["experiment"]["roles"][0]["challengers"][0]
    challenger["sandbox_intent"] = (
        "workspace-write" if control["sandbox_intent"] == "read-only" else "read-only"
    )
    result = run_validator(tmp_path, payload)
    assert result.returncode != 0
    assert "changes sandbox_intent" in result.stderr


def test_task_hash_binds_exact_task_bytes(tmp_path: Path):
    payload = role_campaign()
    payload["workloads"][0]["task_sha256"] = "0" * 64
    result = run_validator(tmp_path, payload)
    assert result.returncode != 0
    assert "task_sha256 does not match exact UTF-8 task_text" in result.stderr


def test_unresolved_control_fingerprints_cannot_be_frozen(tmp_path: Path):
    payload = role_campaign()
    payload["workloads"][0]["controls"]["tool_surface_fingerprint"] = "TBD"
    result = run_validator(tmp_path, payload)
    assert result.returncode != 0
    assert "unresolved tool_surface_fingerprint" in result.stderr


def test_campaign_candidate_must_equal_current_head(tmp_path: Path):
    payload = role_campaign()
    payload["plugin_candidate_sha"] = "0" * 40
    result = run_validator(tmp_path, payload)
    assert result.returncode != 0
    assert "plugin_candidate_sha must equal the exact current Git HEAD" in result.stderr


def test_duplicate_route_shape_is_rejected(tmp_path: Path):
    payload = role_campaign()
    control = payload["experiment"]["roles"][0]["control"]
    payload["experiment"]["roles"][0]["challengers"][0] = {
        "id": "different-id",
        "model": control["model"],
        "effort": control["effort"],
        "sandbox_intent": control["sandbox_intent"],
    }
    result = run_validator(tmp_path, payload)
    assert result.returncode != 0
    assert "challenger identical to another route" in result.stderr


def test_product_benchmark_rejects_predeclared_calibration_role(tmp_path: Path):
    payload = product_campaign()
    payload["workloads"][0]["calibration_role"] = "reader"
    result = run_validator(tmp_path, payload)
    assert result.returncode != 0
    assert "must not predeclare a calibration role" in result.stderr


def test_role_calibration_rejects_product_benchmark_stratum(tmp_path: Path):
    payload = role_campaign()
    payload["workloads"][0]["benchmark_stratum"] = "small_bounded"
    result = run_validator(tmp_path, payload)
    assert result.returncode != 0
    assert "must not carry a product benchmark_stratum" in result.stderr


def test_formal_campaign_rejects_placeholder_repository(tmp_path: Path):
    payload = product_campaign()
    payload["workloads"][0]["repository_url"] = "https://example.invalid/repository.git"
    result = run_validator(tmp_path, payload)
    assert result.returncode != 0
    assert "must bind a real repository" in result.stderr
