from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate-experiment-campaign.py"
POLICY = json.loads((ROOT / "contracts" / "policy.json").read_text(encoding="utf-8"))
sys.path.insert(0, str(ROOT / "scripts"))
from calibration_profile_contract import materialized_agent_type, role_contract_digest  # noqa: E402
sys.path.pop(0)


def assurance_requirements(claim_kind: str = "model_effort") -> dict:
    return {
        "claim_kind": claim_kind,
        "required": ["route", "permission_state"],
        "allow_unknown": ["permission_provenance"],
    }


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
    payload = {
        "id": route_id,
        "model": (
            configured["model"]
            if not challenger or role != "reader"
            else "gpt-5.6-terra"
        ),
        "effort": "xhigh" if challenger and role == "reader" else configured["effort"],
        "mutation_authority": configured["mutation_authority"],
    }
    if role == "reader":
        profile = tomllib.loads((ROOT / "agent-profiles" / "subagents-dispatch-reader.toml").read_text())
        payload.update(
            semantic_role="reader",
            configured_model=payload["model"],
            configured_effort=payload["effort"],
            materialized_agent_type=materialized_agent_type("reader-calibration-fixture", "reader", route_id),
            role_contract_digest=role_contract_digest(
                "reader", profile["description"], profile["developer_instructions"], "none"
            ),
        )
    return payload


def workload(
    *,
    formal: bool,
    calibration_role: str | None = None,
    benchmark_stratum: str | None = None,
) -> dict:
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
        packet = "OBJECTIVE\nTrace the exact bounded call path.\nRETURN\nEvidence refs only."
        payload["calibration_role"] = calibration_role
        payload["responsibility_packet_sha256"] = task_hash(packet)
        payload["responsibility_packet_ref"] = "fixture:responsibility-packet-v1"
    if benchmark_stratum is not None:
        payload["benchmark_stratum"] = benchmark_stratum
    return payload


def role_campaign(*, stage: str = "exploratory", repeats: int = 1, promotion: bool = False) -> dict:
    role_name = "reader"
    return {
        "schema_version": "2.0",
        "campaign_id": "reader-calibration-fixture",
        "stage": stage,
        "materialization_mode": "profile_only",
        "model_provider_control": "openai",
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
        "assurance_requirements": assurance_requirements(),
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
        "materialization_mode": "shared_config",
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
        "assurance_requirements": assurance_requirements("product_behavior"),
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


def test_campaign_hash_binds_materialization_mode(tmp_path: Path):
    profile_only = role_campaign()
    valid = run_validator(tmp_path, profile_only)
    assert valid.returncode == 0, valid.stderr
    profile_hash = json.loads(valid.stdout)["campaign_sha256"]

    changed = {**profile_only, "materialization_mode": "shared_config"}
    assert task_hash(json.dumps(profile_only, sort_keys=True, separators=(",", ":"))) != task_hash(
        json.dumps(changed, sort_keys=True, separators=(",", ":"))
    )
    assert profile_hash != task_hash(
        json.dumps(changed, sort_keys=True, separators=(",", ":"))
    )


def test_model_effort_campaign_requires_frozen_provider_control(tmp_path: Path):
    payload = role_campaign()
    payload.pop("model_provider_control")
    assert run_validator(tmp_path, payload).returncode != 0

    payload["model_provider_control"] = "TBD"
    result = run_validator(tmp_path, payload)
    assert result.returncode != 0
    assert "model_provider_control" in result.stderr


def test_model_effort_role_calibration_requires_profile_only(tmp_path: Path):
    payload = role_campaign(stage="formal", repeats=3)
    payload.pop("materialization_mode")
    missing = run_validator(tmp_path, payload)
    assert missing.returncode != 0
    assert "materialization_mode" in missing.stderr

    payload["materialization_mode"] = "shared_config"
    wrong = run_validator(tmp_path, payload)
    assert wrong.returncode != 0
    assert "profile_only" in wrong.stderr


def test_valid_product_benchmark_does_not_predeclare_role_challengers(tmp_path: Path):
    result = run_validator(tmp_path, product_campaign())
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["experiment_type"] == "product_benchmark"
    assert summary["roles"] == []
    assert summary["minimum_completed_per_arm"] == 3


def test_campaign_can_require_stronger_permission_provenance(tmp_path: Path):
    payload = role_campaign()
    payload["assurance_requirements"] = {
        "claim_kind": "model_effort",
        "required": ["route", "permission_state", "permission_provenance"],
        "allow_unknown": [],
    }

    result = run_validator(tmp_path, payload)

    assert result.returncode == 0, result.stderr


def test_current_experiment_types_cannot_claim_host_permission_source(tmp_path: Path):
    payload = role_campaign()
    payload["assurance_requirements"] = {
        "claim_kind": "host_permission_provenance",
        "required": ["route", "permission_state", "permission_provenance"],
        "allow_unknown": [],
    }

    result = run_validator(tmp_path, payload)

    assert result.returncode != 0
    assert "cannot support a Host permission-source claim" in result.stderr


def test_campaign_must_declare_how_unknown_provenance_affects_its_claim(tmp_path: Path):
    payload = role_campaign()
    payload["assurance_requirements"]["allow_unknown"] = []

    result = run_validator(tmp_path, payload)

    assert result.returncode != 0
    assert "must classify every assurance dimension" in result.stderr


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


def test_challenger_cannot_change_mutation_authority_contract(tmp_path: Path):
    payload = role_campaign()
    control = payload["experiment"]["roles"][0]["control"]
    challenger = payload["experiment"]["roles"][0]["challengers"][0]
    challenger["mutation_authority"] = (
        "bounded-source-write" if control["mutation_authority"] == "none" else "none"
    )
    result = run_validator(tmp_path, payload)
    assert result.returncode != 0
    assert "must be exactly Terra XHigh" in result.stderr


def test_task_hash_binds_exact_task_bytes(tmp_path: Path):
    payload = role_campaign()
    payload["workloads"][0]["task_sha256"] = "0" * 64
    result = run_validator(tmp_path, payload)
    assert result.returncode != 0
    assert "task_sha256 does not match exact UTF-8 task_text" in result.stderr


def test_placeholder_task_text_cannot_be_frozen_even_with_matching_hash(tmp_path: Path):
    payload = role_campaign()
    payload["workloads"][0]["task_text"] = "TBD"
    payload["workloads"][0]["task_sha256"] = task_hash("TBD")
    result = run_validator(tmp_path, payload)
    assert result.returncode != 0
    assert "task_text must be a concrete non-placeholder value" in result.stderr


def test_unresolved_control_fingerprints_cannot_be_frozen(tmp_path: Path):
    payload = role_campaign()
    payload["workloads"][0]["controls"]["tool_surface_fingerprint"] = "TBD"
    result = run_validator(tmp_path, payload)
    assert result.returncode != 0
    assert "unresolved tool_surface_fingerprint" in result.stderr


def test_whitespace_control_fingerprints_cannot_be_frozen(tmp_path: Path):
    payload = role_campaign()
    payload["workloads"][0]["controls"]["permissions_fingerprint"] = "   "
    result = run_validator(tmp_path, payload)
    assert result.returncode != 0
    assert "unresolved permissions_fingerprint" in result.stderr


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
        "model": "gpt-5.6-terra",
        "effort": control["effort"],
        "mutation_authority": control["mutation_authority"],
        "semantic_role": control["semantic_role"],
        "configured_model": control["configured_model"],
        "configured_effort": control["configured_effort"],
        "materialized_agent_type": "subagents_dispatch_calibration_reader_different_id_0000000000000000",
        "role_contract_digest": control["role_contract_digest"],
    }
    result = run_validator(tmp_path, payload)
    assert result.returncode != 0
    assert "must be exactly Terra XHigh" in result.stderr


def test_reader_calibration_rejects_contract_identity_and_configured_route_drift(tmp_path: Path):
    cases = [
        ("role_contract_digest", "0" * 64, "role_contract_digest does not match"),
        (
            "materialized_agent_type",
            "subagents_dispatch_calibration_reader_wrong_0000000000000000",
            "materialized_agent_type is not deterministic",
        ),
        ("configured_model", "gpt-5.6-sol", "configured route must match model/effort"),
        ("configured_effort", "low", "configured route must match model/effort"),
    ]
    for field, value, message in cases:
        payload = role_campaign()
        payload["experiment"]["roles"][0]["challengers"][0][field] = value
        result = run_validator(tmp_path, payload)
        assert result.returncode != 0
        assert message in result.stderr


def test_reader_calibration_rejects_duplicate_materialized_identity(tmp_path: Path):
    payload = role_campaign()
    role_spec = payload["experiment"]["roles"][0]
    role_spec["challengers"][0]["id"] = role_spec["control"]["id"]
    role_spec["challengers"][0]["materialized_agent_type"] = role_spec["control"]["materialized_agent_type"]
    result = run_validator(tmp_path, payload)
    assert result.returncode != 0
    assert "duplicates materialized_agent_type" in result.stderr


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


def test_role_calibration_requires_frozen_responsibility_packet_identity(tmp_path: Path):
    payload = role_campaign()
    del payload["workloads"][0]["responsibility_packet_sha256"]
    result = run_validator(tmp_path, payload)
    assert result.returncode != 0
    assert "responsibility_packet_sha256" in result.stderr

    payload = role_campaign()
    payload["workloads"][0]["responsibility_packet_ref"] = "TBD"
    result = run_validator(tmp_path, payload)
    assert result.returncode != 0
    assert "responsibility_packet_ref must be a concrete non-placeholder value" in result.stderr


def test_product_benchmark_rejects_frozen_delegated_responsibility_packet(tmp_path: Path):
    payload = product_campaign()
    payload["workloads"][0]["responsibility_packet_sha256"] = "c" * 64
    payload["workloads"][0]["responsibility_packet_ref"] = "fixture:packet"
    result = run_validator(tmp_path, payload)
    assert result.returncode != 0
    assert "must not freeze a delegated responsibility packet" in result.stderr


def test_formal_campaign_rejects_placeholder_repository(tmp_path: Path):
    payload = product_campaign()
    payload["workloads"][0]["repository_url"] = "https://example.invalid/repository.git"
    result = run_validator(tmp_path, payload)
    assert result.returncode != 0
    assert "must bind a real repository" in result.stderr


def test_campaign_rejects_placeholder_host_target(tmp_path: Path):
    payload = product_campaign()
    payload["host_target"]["version"] = "TBD"
    result = run_validator(tmp_path, payload)
    assert result.returncode != 0
    assert "host_target.version must be a concrete non-placeholder value" in result.stderr


def test_campaign_rejects_blank_oracle_identity(tmp_path: Path):
    payload = product_campaign()
    payload["workloads"][0]["acceptance"]["rubric_id"] = " "
    result = run_validator(tmp_path, payload)
    assert result.returncode != 0
    assert "acceptance.rubric_id must be a concrete non-placeholder value" in result.stderr


def test_optional_fixed_order_reason_cannot_carry_placeholder_garbage(tmp_path: Path):
    payload = product_campaign()
    payload["repeat_policy"]["fixed_order_reason"] = "TODO"
    result = run_validator(tmp_path, payload)
    assert result.returncode != 0
    assert "fixed_order_reason must be a concrete non-placeholder value" in result.stderr


def test_optional_promotion_ref_cannot_carry_placeholder_garbage(tmp_path: Path):
    payload = role_campaign()
    payload["experiment"]["promotion_criteria_ref"] = "placeholder"
    result = run_validator(tmp_path, payload)
    assert result.returncode != 0
    assert "promotion_criteria_ref must be a concrete non-placeholder value" in result.stderr


def test_role_calibration_rejects_declared_role_without_workload(tmp_path: Path):
    payload = role_campaign()
    payload["experiment"]["roles"].append(
        {
            "role": "worker",
            "contract_ref": "contracts/routing.md#bounded-execution",
            "control": route("worker", route_id="current-worker"),
            "challengers": [route("worker", route_id="candidate-worker", challenger=True)],
        }
    )
    result = run_validator(tmp_path, payload)
    assert result.returncode != 0
    assert "initial calibration profile materialization supports only the Reader role" in result.stderr
