from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

import test_experiment_campaign as campaign_fixture

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate-experiment-run.py"


def load_validator():
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        spec = importlib.util.spec_from_file_location("experiment_run_validator", VALIDATOR_PATH)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(ROOT / "scripts"))


VALIDATOR = load_validator()


def canonical(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")).hexdigest()


def scalar(value, *, verdict: str = "verified", ref: str | None = "evidence:scalar") -> dict:
    return {"observed_value": value, "verdict": verdict, "evidence_ref": ref}


def measurement(status: str, value: int | None = None, ref: str | None = None) -> dict:
    if status == "observed":
        return {"status": status, "value": value, "source_ref": ref or "metrics:source"}
    return {"status": status, "value": None, "source_ref": None}


def input_evidence(campaign: dict, workload: dict, *, plugin_value: str, calibration: bool) -> dict:
    packet = (
        scalar(workload["responsibility_packet_sha256"], ref="input:packet")
        if calibration
        else scalar(None, verdict="not_applicable", ref=None)
    )
    return {
        "plugin_candidate": scalar(plugin_value, ref="input:plugin"),
        "host": {"observed": campaign["host_target"], "verdict": "verified", "evidence_ref": "input:host"},
        "repository": {
            "observed": {"repository_url": workload["repository_url"], "base_revision": workload["base_revision"]},
            "verdict": "verified",
            "evidence_ref": "input:repo",
        },
        "task_sha256": scalar(workload["task_sha256"], ref="input:task"),
        "reset_procedure_sha256": scalar(canonical(workload["reset_procedure"]), ref="input:reset"),
        "acceptance_sha256": scalar(canonical(workload["acceptance"]), ref="input:acceptance"),
        "responsibility_packet_sha256": packet,
        "controls": {
            "main_session_route": scalar(workload["controls"]["main_session_route_fingerprint"], ref="input:main-route"),
            "permissions": scalar(workload["controls"]["permissions_fingerprint"], ref="input:permissions"),
            "tool_surface": scalar(workload["controls"]["tool_surface_fingerprint"], ref="input:tools"),
            "project_rules": {
                "observed_refs": workload["controls"]["project_rule_refs"],
                "verdict": "verified",
                "evidence_ref": "input:rules",
            },
        },
    }


def metrics(*, children: int | None) -> dict:
    child = measurement("unavailable") if children is None else (
        measurement("not_applicable") if children == 0 else measurement("observed", 20, "metrics:child")
    )
    aggregate = measurement("unavailable") if children is None else measurement(
        "observed", 100 if children == 0 else 120, "metrics:aggregate"
    )
    return {
        "wall_clock_ms": measurement("observed", 1000, "metrics:clock"),
        "main_total_tokens": measurement("observed", 100, "metrics:main"),
        "child_total_tokens": child,
        "aggregate_total_tokens": aggregate,
        "main_context_peak_tokens": measurement("observed", 50, "metrics:context"),
        "user_interventions": measurement("observed", 0, "metrics:user"),
        "semantic_reworks": measurement("observed", 0, "metrics:rework"),
        "retries": measurement("observed", 0, "metrics:retry"),
        "review_rounds": measurement("observed", 0, "metrics:review"),
        "compactions": measurement("observed", 0, "metrics:compact"),
    }


def permission_provenance(root: str, *, verdict: str = "verified") -> dict:
    if verdict == "unknown":
        return {
            "source_kind": None, "source_id": None, "sandbox_policy_type": None,
            "permission_profile_type": None, "evidence_source": "none",
            "evidence_ref": None, "selection_evidence_ref": None, "verdict": "unknown",
        }
    return {
        "source_kind": "parent_turn", "source_id": root,
        "sandbox_policy_type": "danger-full-access", "permission_profile_type": "disabled",
        "evidence_source": "native", "evidence_ref": "permission:source",
        "selection_evidence_ref": "permission:selection", "verdict": verdict,
    }


def child_route(*, role: str, model: str, effort: str, root: str, provider: str | None = None) -> dict:
    agent_type = {
        "programmer": "subagents_dispatch_programmer",
        "product_manager": "subagents_dispatch_product_manager",
        "department_director": "subagents_dispatch_department_director",
    }[role]
    return {
        "child_thread_id": f"child-{role}",
        "parent_thread_id": root,
        "role": role,
        "requested": {"agent_type": agent_type, "model": model, "effort": effort, "evidence_ref": "route:request"},
        "accepted": {"agent_type": agent_type, "model": model, "effort": effort, "verdict": "verified", "evidence_ref": "route:accepted"},
        "observed": {
            "agent_type": agent_type, "model": model, "effort": effort,
            "sandbox_policy_type": "danger-full-access", "permission_profile_type": "disabled",
            "model_provider": provider, "evidence_source": "native", "evidence_ref": "route:observed",
        },
        "permission_state_verdict": "verified",
        "permission_provenance": permission_provenance(root),
        "verdict": "verified",
    }


def campaign_hash(campaign: dict) -> str:
    return canonical(campaign)


def base_run(campaign: dict, *, mode: str = "single_agent") -> dict:
    workload = campaign["workloads"][0]
    calibration = campaign["experiment"]["type"] == "role_calibration"
    root = "root-thread"
    if calibration:
        role = campaign["experiment"]["roles"][0]["role"]
        arm = {"kind": "role_calibration", "role": role, "route_id": campaign["experiment"]["roles"][0]["challengers"][0]["id"]}
        plugin = campaign["plugin_candidate_sha"]
        provider = "unknown"
    else:
        arm = {"kind": "product_benchmark", "mode": mode}
        plugin = "absent" if mode == "single_agent" else campaign["plugin_candidate_sha"]
        provider = "not_applicable"
    return {
        "schema_version": "2.0",
        "run_id": "run-1",
        "campaign_id": campaign["campaign_id"],
        "campaign_sha256": campaign_hash(campaign),
        "plugin_candidate_sha": campaign["plugin_candidate_sha"],
        "stage": campaign["stage"],
        "experiment_type": campaign["experiment"]["type"],
        "workload_id": workload["id"],
        "repeat_index": 1,
        "arm": arm,
        "root_thread_id": root,
        "input_assurance": "verified",
        "input_evidence": input_evidence(campaign, workload, plugin_value=plugin, calibration=calibration),
        "child_materialization": {"status": "observed", "count": 0, "source_ref": "host:children"},
        "execution": {
            "status": "completed", "acceptance_status": "passed", "oracle_refs": ["oracle:1"],
            "quality_score": None, "quality_score_ref": None, "result_ref": "result:1", "failure_ref": None,
        },
        "route_assurance": "not_applicable" if mode == "single_agent" and not calibration else "unknown",
        "permission_state_assurance": "not_applicable" if mode == "single_agent" and not calibration else "unknown",
        "permission_provenance_assurance": "not_applicable" if mode == "single_agent" and not calibration else "unknown",
        "provider_control_assurance": provider,
        "child_routes": [],
        "metrics": metrics(children=0),
        "evidence_artifact_ref": "artifact:run-1",
    }


def write_campaign(tmp_path: Path, campaign: dict) -> Path:
    path = tmp_path / "campaign.json"
    path.write_text(json.dumps(campaign), encoding="utf-8")
    return path


def validate(tmp_path: Path, campaign: dict, run: dict) -> dict:
    return VALIDATOR.validate_run(run, write_campaign(tmp_path, campaign))


def add_route(run: dict, route: dict) -> None:
    run["child_routes"] = [route]
    run["child_materialization"] = {"status": "observed", "count": 1, "source_ref": "host:children"}
    run["route_assurance"] = route["verdict"]
    run["permission_state_assurance"] = route["permission_state_verdict"]
    run["permission_provenance_assurance"] = route["permission_provenance"]["verdict"]
    run["metrics"] = metrics(children=1)


def test_single_agent_product_run_is_valid_without_child_routes(tmp_path: Path):
    campaign = campaign_fixture.product_campaign(stage="exploratory")
    result = validate(tmp_path, campaign, base_run(campaign))
    assert result["run_valid"] is True
    assert result["materialized_children"] == 0
    assert result["route_assurance"] == "not_applicable"
    assert result["claim_eligible"] is True


def test_dispatch_accepts_programmer_and_both_product_manager_production_efforts(tmp_path: Path):
    campaign = campaign_fixture.product_campaign(stage="exploratory")
    for role, model, effort in (
        ("programmer", "gpt-5.6-luna", "max"),
        ("product_manager", "gpt-5.6-sol", "medium"),
        ("product_manager", "gpt-5.6-sol", "high"),
        ("department_director", "gpt-6-astra", "high"),
    ):
        run = base_run(campaign, mode="dispatch")
        route = child_route(role=role, model=model, effort=effort, root=run["root_thread_id"])
        add_route(run, route)
        run["provider_control_assurance"] = "not_applicable"
        result = validate(tmp_path, campaign, run)
        assert result["route_assurance"] == "verified"


def test_product_dispatch_rejects_route_outside_production_policy(tmp_path: Path):
    campaign = campaign_fixture.product_campaign(stage="exploratory")
    run = base_run(campaign, mode="dispatch")
    add_route(run, child_route(role="product_manager", model="gpt-5.6-sol", effort="xhigh", root=run["root_thread_id"]))
    run["provider_control_assurance"] = "not_applicable"
    with pytest.raises(SystemExit, match="outside production policy"):
        validate(tmp_path, campaign, run)


def test_calibration_accepts_frozen_challenger_without_temporary_profile_identity(tmp_path: Path):
    campaign = campaign_fixture.calibration_campaign(role_id="programmer")
    challenger = campaign["experiment"]["roles"][0]["challengers"][0]
    run = base_run(campaign)
    route = child_route(
        role="programmer", model=challenger["model"], effort=challenger["effort"],
        root=run["root_thread_id"], provider=campaign["model_provider_control"],
    )
    add_route(run, route)
    run["provider_control_assurance"] = "verified"
    result = validate(tmp_path, campaign, run)
    assert result["claim_eligible"] is True
    assert "materialization_manifest_ref" not in run
    assert "materialized_agent_type" not in route


def test_calibration_route_mismatch_is_failed_not_rewritten(tmp_path: Path):
    campaign = campaign_fixture.calibration_campaign()
    challenger = campaign["experiment"]["roles"][0]["challengers"][0]
    run = base_run(campaign)
    route = child_route(role="programmer", model=challenger["model"], effort=challenger["effort"], root=run["root_thread_id"], provider="openai")
    route["observed"]["model"] = "wrong-model"
    add_route(run, route)
    run["provider_control_assurance"] = "verified"
    with pytest.raises(SystemExit, match="route verdict"):
        validate(tmp_path, campaign, run)
    route["verdict"] = "failed"
    run["route_assurance"] = "failed"
    result = validate(tmp_path, campaign, run)
    assert result["route_assurance"] == "failed"
    assert route["observed"]["model"] == "wrong-model"
    assert result["claim_eligible"] is False


def test_calibration_provider_control_is_observed_and_claim_gating(tmp_path: Path):
    campaign = campaign_fixture.calibration_campaign()
    challenger = campaign["experiment"]["roles"][0]["challengers"][0]
    run = base_run(campaign)
    route = child_route(role="programmer", model=challenger["model"], effort=challenger["effort"], root=run["root_thread_id"], provider=None)
    add_route(run, route)
    run["provider_control_assurance"] = "unknown"
    result = validate(tmp_path, campaign, run)
    assert result["provider_control_assurance"] == "unknown"
    assert result["claim_eligible"] is False

    run = base_run(campaign)
    route = child_route(role="programmer", model=challenger["model"], effort=challenger["effort"], root=run["root_thread_id"], provider="other-provider")
    add_route(run, route)
    run["provider_control_assurance"] = "failed"
    result = validate(tmp_path, campaign, run)
    assert result["provider_control_assurance"] == "failed"
    assert result["claim_eligible"] is False


def test_materialized_child_count_and_duplicate_identity_fail_closed(tmp_path: Path):
    campaign = campaign_fixture.product_campaign(stage="exploratory")
    run = base_run(campaign, mode="dispatch")
    run["child_materialization"] = {"status": "observed", "count": 1, "source_ref": "host:children"}
    with pytest.raises(SystemExit, match="count must equal"):
        validate(tmp_path, campaign, run)

    run = base_run(campaign, mode="dispatch")
    first = child_route(role="programmer", model="gpt-5.6-luna", effort="max", root=run["root_thread_id"])
    second = json.loads(json.dumps(first))
    run["child_routes"] = [first, second]
    run["child_materialization"] = {"status": "observed", "count": 2, "source_ref": "host:children"}
    run["route_assurance"] = run["permission_state_assurance"] = run["permission_provenance_assurance"] = "verified"
    run["provider_control_assurance"] = "not_applicable"
    run["metrics"] = metrics(children=1)
    with pytest.raises(SystemExit, match="duplicates child_thread_id"):
        validate(tmp_path, campaign, run)


def test_unavailable_materialization_preserves_unknown_assurance(tmp_path: Path):
    campaign = campaign_fixture.product_campaign(stage="exploratory")
    run = base_run(campaign, mode="dispatch")
    run["child_materialization"] = {"status": "unavailable", "count": None, "source_ref": "host:children-unavailable"}
    run["route_assurance"] = run["permission_state_assurance"] = run["permission_provenance_assurance"] = "unknown"
    run["provider_control_assurance"] = "not_applicable"
    run["metrics"] = metrics(children=None)
    result = validate(tmp_path, campaign, run)
    assert result["materialized_children"] is None
    assert result["route_assurance"] == "unknown"


def test_input_drift_must_be_recorded_as_failed_and_packet_is_real_calibration_input(tmp_path: Path):
    campaign = campaign_fixture.calibration_campaign()
    run = base_run(campaign)
    run["input_evidence"]["task_sha256"]["observed_value"] = "0" * 64
    with pytest.raises(SystemExit, match="mismatch requires verdict=failed"):
        validate(tmp_path, campaign, run)
    run["input_evidence"]["task_sha256"]["verdict"] = "failed"
    run["input_assurance"] = "failed"
    run["child_materialization"] = {"status": "unavailable", "count": None, "source_ref": "host:none"}
    run["route_assurance"] = run["permission_state_assurance"] = run["permission_provenance_assurance"] = "unknown"
    run["provider_control_assurance"] = "unknown"
    run["metrics"] = metrics(children=None)
    result = validate(tmp_path, campaign, run)
    assert result["input_assurance"] == "failed"

    run = base_run(campaign)
    run["input_evidence"]["responsibility_packet_sha256"]["observed_value"] = "f" * 64
    with pytest.raises(SystemExit, match="responsibility_packet_sha256"):
        validate(tmp_path, campaign, run)


def test_failed_execution_is_preserved_but_cannot_be_claim_eligible(tmp_path: Path):
    campaign = campaign_fixture.product_campaign(stage="exploratory")
    run = base_run(campaign)
    run["execution"] = {
        "status": "failed", "acceptance_status": "unknown", "oracle_refs": [],
        "quality_score": None, "quality_score_ref": None, "result_ref": None, "failure_ref": "failure:1",
    }
    result = validate(tmp_path, campaign, run)
    assert result["run_valid"] is True
    assert result["execution_status"] == "failed"
    assert result["claim_eligible"] is False


def test_noncompleted_cannot_claim_passed_acceptance_and_pass_requires_oracle_result(tmp_path: Path):
    campaign = campaign_fixture.product_campaign(stage="exploratory")
    run = base_run(campaign)
    run["execution"]["status"] = "interrupted"
    with pytest.raises(SystemExit, match="non-completed"):
        validate(tmp_path, campaign, run)
    run = base_run(campaign)
    run["execution"]["oracle_refs"] = []
    with pytest.raises(SystemExit, match="oracle_ref"):
        validate(tmp_path, campaign, run)


def test_measurement_provenance_and_token_reconciliation_are_required(tmp_path: Path):
    campaign = campaign_fixture.product_campaign(stage="exploratory")
    run = base_run(campaign)
    run["metrics"]["wall_clock_ms"] = {"status": "observed", "value": 1, "source_ref": None}
    with pytest.raises(SystemExit, match="source_ref"):
        validate(tmp_path, campaign, run)

    run = base_run(campaign, mode="dispatch")
    route = child_route(role="programmer", model="gpt-5.6-luna", effort="max", root=run["root_thread_id"])
    add_route(run, route)
    run["provider_control_assurance"] = "not_applicable"
    run["metrics"]["aggregate_total_tokens"]["value"] = 999
    with pytest.raises(SystemExit, match="aggregate_total_tokens"):
        validate(tmp_path, campaign, run)


def test_run_binds_exact_campaign_hash_and_actual_evidence_refs(tmp_path: Path):
    campaign = campaign_fixture.product_campaign(stage="exploratory")
    run = base_run(campaign)
    run["campaign_sha256"] = "0" * 64
    with pytest.raises(SystemExit, match="campaign_sha256"):
        validate(tmp_path, campaign, run)
    run = base_run(campaign)
    run["input_evidence"]["host"]["evidence_ref"] = None
    with pytest.raises(SystemExit, match="evidence_ref"):
        validate(tmp_path, campaign, run)
