from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
RUN_VALIDATOR = SCRIPTS / "validate-experiment-run.py"
POLICY = ROOT / "contracts" / "policy.json"


def load_run_validator():
    sys.path.insert(0, str(SCRIPTS))
    try:
        spec = importlib.util.spec_from_file_location("experiment_run_validator", RUN_VALIDATOR)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPTS))


VALIDATOR = load_run_validator()


def head_sha() -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def canonical_hash(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def task_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def controls() -> dict:
    return {
        "main_session_route_fingerprint": "main:sol-high",
        "permissions_fingerprint": "permissions:workspace-write",
        "tool_surface_fingerprint": "tools:fixed-v1",
        "project_rule_refs": ["AGENTS.md@sha256:abc"],
    }


def workload(*, role: str | None = None, stratum: str | None = "small_bounded") -> dict:
    task = "Change one bounded behavior and verify it."
    payload = {
        "id": "W1",
        "repository_url": "https://github.com/example/example.git",
        "base_revision": "a" * 40,
        "source_task_ref": "fixture:W1",
        "task_text": task,
        "task_sha256": task_hash(task),
        "reset_procedure": ["git reset --hard BASE", "git clean -fdx"],
        "acceptance": {
            "rubric_id": "rubric-W1-v1",
            "oracle_kind": "deterministic",
            "verification": ["pytest focused-test"],
        },
        "controls": controls(),
    }
    if role is not None:
        payload["calibration_role"] = role
    if stratum is not None:
        payload["benchmark_stratum"] = stratum
    return payload


def product_campaign(*, stage: str = "exploratory") -> dict:
    return {
        "schema_version": "2.0",
        "campaign_id": "product-campaign",
        "stage": stage,
        "plugin_candidate_sha": head_sha(),
        "host_target": {"product": "Codex", "version": "test-host-1", "platform": "linux-test"},
        "repeat_policy": {
            "minimum_completed_per_arm": 3 if stage == "formal" else 1,
            "ordering": "interleaved",
        },
        "experiment": {
            "type": "product_benchmark",
            "baseline_mode": "single_agent",
            "candidate_mode": "dispatch",
        },
        "workloads": [workload()],
    }


def calibration_campaign() -> dict:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    reader = policy["roles"]["reader"]
    control = {
        "id": "reader-control",
        "model": reader["model"],
        "effort": reader["effort"],
        "sandbox_intent": reader["sandbox_intent"],
    }
    challenger_effort = "xhigh" if reader["effort"] != "xhigh" else "high"
    challenger = {
        "id": "reader-challenger",
        "model": reader["model"],
        "effort": challenger_effort,
        "sandbox_intent": reader["sandbox_intent"],
    }
    return {
        "schema_version": "2.0",
        "campaign_id": "calibration-campaign",
        "stage": "exploratory",
        "plugin_candidate_sha": head_sha(),
        "host_target": {"product": "Codex", "version": "test-host-1", "platform": "linux-test"},
        "repeat_policy": {"minimum_completed_per_arm": 1, "ordering": "randomized"},
        "experiment": {
            "type": "role_calibration",
            "policy_promotion": False,
            "promotion_criteria_ref": None,
            "roles": [
                {
                    "role": "reader",
                    "contract_ref": "contracts/routing.md#reader",
                    "control": control,
                    "challengers": [challenger],
                }
            ],
        },
        "workloads": [workload(role="reader", stratum=None)],
    }


def metric(status: str = "unavailable", value: int | None = None, source: str | None = None) -> dict:
    return {"status": status, "value": value, "source_ref": source}


def metrics(*, children: bool = False) -> dict:
    main = metric("observed", 100, "rollout:main:tokens")
    child = metric("observed", 40, "rollout:children:tokens") if children else metric("not_applicable")
    aggregate = metric("observed", 140 if children else 100, "derived:reported-token-sum")
    return {
        "wall_clock_ms": metric("observed", 2500, "clock:run"),
        "main_total_tokens": main,
        "child_total_tokens": child,
        "aggregate_total_tokens": aggregate,
        "main_context_peak_tokens": metric(),
        "user_interventions": metric("observed", 0, "run:user-interventions"),
        "semantic_reworks": metric("observed", 0, "receipt:semantic-reworks"),
        "retries": metric("observed", 0, "receipt:retries"),
        "review_rounds": metric("observed", 0, "receipt:review-rounds"),
        "compactions": metric(),
    }


def base_run(campaign: dict, *, mode: str = "single_agent") -> dict:
    return {
        "schema_version": "1.0",
        "run_id": f"run-W1-{mode}-1",
        "campaign_id": campaign["campaign_id"],
        "campaign_sha256": canonical_hash(campaign),
        "plugin_candidate_sha": campaign["plugin_candidate_sha"],
        "stage": campaign["stage"],
        "experiment_type": campaign["experiment"]["type"],
        "workload_id": "W1",
        "repeat_index": 1,
        "arm": {"kind": "product_benchmark", "mode": mode},
        "host_target": campaign["host_target"],
        "root_thread_id": "root-thread-1",
        "observed_controls": controls(),
        "execution": {
            "status": "completed",
            "acceptance_status": "passed",
            "oracle_refs": ["pytest:focused-test:PASS"],
            "quality_score": None,
            "quality_score_ref": None,
            "result_ref": "git:result-sha",
            "failure_ref": None,
        },
        "route_assurance": "not_applicable",
        "child_routes": [],
        "metrics": metrics(children=False),
        "evidence_artifact_ref": "artifact:run-W1-1",
    }


def child_route(role: str = "worker", *, verdict: str = "verified") -> dict:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    spec = policy["roles"][role]
    observed = {
        "model": spec["model"],
        "effort": spec["effort"],
        "sandbox_intent": spec["sandbox_intent"],
    }
    return {
        "child_thread_id": f"child-{role}-1",
        "parent_thread_id": "root-thread-1",
        "agent_type": spec["agent_type"],
        "role": role,
        "observed": observed,
        "verdict": verdict,
        "evidence_source": "native" if verdict != "unknown" else "none",
        "evidence_ref": "runtime:child-1" if verdict != "unknown" else None,
    }


def write_campaign(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "campaign.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def validate(tmp_path: Path, campaign: dict, run: dict) -> dict:
    return VALIDATOR.validate_run(run, write_campaign(tmp_path, campaign))


def test_product_single_agent_run_binds_exact_campaign_without_child_routes(tmp_path: Path):
    campaign = product_campaign()
    result = validate(tmp_path, campaign, base_run(campaign))
    assert result["run_valid"] is True
    assert result["materialized_children"] == 0
    assert result["route_assurance"] == "not_applicable"


def test_product_dispatch_run_accepts_verified_policy_route(tmp_path: Path):
    campaign = product_campaign()
    run = base_run(campaign, mode="dispatch")
    run["child_routes"] = [child_route()]
    run["route_assurance"] = "verified"
    run["metrics"] = metrics(children=True)
    result = validate(tmp_path, campaign, run)
    assert result["materialized_children"] == 1
    assert result["route_assurance"] == "verified"


def test_zero_child_dispatch_is_valid_and_keeps_route_assurance_not_applicable(tmp_path: Path):
    campaign = product_campaign()
    run = base_run(campaign, mode="dispatch")
    result = validate(tmp_path, campaign, run)
    assert result["run_valid"] is True
    assert result["materialized_children"] == 0


def test_formal_failed_run_is_valid_evidence_instead_of_being_dropped(tmp_path: Path):
    campaign = product_campaign(stage="formal")
    run = base_run(campaign)
    run["stage"] = "formal"
    run["execution"].update(
        status="failed",
        acceptance_status="unknown",
        oracle_refs=[],
        result_ref=None,
        failure_ref="run:tool-failure",
    )
    result = validate(tmp_path, campaign, run)
    assert result["run_valid"] is True
    assert result["execution_status"] == "failed"
    assert result["acceptance_status"] == "unknown"


def test_run_rejects_campaign_hash_or_control_drift(tmp_path: Path):
    campaign = product_campaign()
    run = base_run(campaign)
    run["campaign_sha256"] = "f" * 64
    with pytest.raises(SystemExit, match="campaign_sha256"):
        validate(tmp_path, campaign, run)

    run = base_run(campaign)
    run["observed_controls"]["tool_surface_fingerprint"] = "tools:drifted"
    with pytest.raises(SystemExit, match="observed_controls"):
        validate(tmp_path, campaign, run)


def test_single_agent_cannot_smuggle_project_child_route_evidence(tmp_path: Path):
    campaign = product_campaign()
    run = base_run(campaign)
    run["child_routes"] = [child_route()]
    run["route_assurance"] = "verified"
    run["metrics"] = metrics(children=True)
    with pytest.raises(SystemExit, match="single_agent"):
        validate(tmp_path, campaign, run)


def test_configured_or_self_reported_route_source_cannot_be_observed_evidence(tmp_path: Path):
    campaign = product_campaign()
    run = base_run(campaign, mode="dispatch")
    route = child_route()
    route["evidence_source"] = "configured"
    run["child_routes"] = [route]
    run["route_assurance"] = "verified"
    run["metrics"] = metrics(children=True)
    with pytest.raises(SystemExit, match="schema validation"):
        validate(tmp_path, campaign, run)


def test_observed_route_mismatch_cannot_be_marked_verified(tmp_path: Path):
    campaign = product_campaign()
    run = base_run(campaign, mode="dispatch")
    route = child_route()
    route["observed"]["model"] = "gpt-5.6-sol"
    run["child_routes"] = [route]
    run["route_assurance"] = "verified"
    run["metrics"] = metrics(children=True)
    with pytest.raises(SystemExit, match="mismatch requires verdict=failed"):
        validate(tmp_path, campaign, run)


def test_duplicate_child_identity_and_forged_route_assurance_fail_closed(tmp_path: Path):
    campaign = product_campaign()
    run = base_run(campaign, mode="dispatch")
    first = child_route()
    second = child_route(role="reader")
    second["child_thread_id"] = first["child_thread_id"]
    run["child_routes"] = [first, second]
    run["route_assurance"] = "verified"
    run["metrics"] = metrics(children=True)
    with pytest.raises(SystemExit, match="duplicates child_thread_id"):
        validate(tmp_path, campaign, run)

    run = base_run(campaign, mode="dispatch")
    unknown = child_route(verdict="unknown")
    unknown["observed"] = {"model": None, "effort": None, "sandbox_intent": None}
    run["child_routes"] = [unknown]
    run["route_assurance"] = "verified"
    run["metrics"] = metrics(children=True)
    with pytest.raises(SystemExit, match="route_assurance must be 'unknown'"):
        validate(tmp_path, campaign, run)


def test_role_calibration_run_binds_exact_declared_challenger(tmp_path: Path):
    campaign = calibration_campaign()
    challenger = campaign["experiment"]["roles"][0]["challengers"][0]
    policy = json.loads(POLICY.read_text(encoding="utf-8"))["roles"]["reader"]
    run = {
        **base_run(product_campaign()),
        "run_id": "run-reader-challenger-1",
        "campaign_id": campaign["campaign_id"],
        "campaign_sha256": canonical_hash(campaign),
        "plugin_candidate_sha": campaign["plugin_candidate_sha"],
        "stage": campaign["stage"],
        "experiment_type": "role_calibration",
        "arm": {"kind": "role_calibration", "role": "reader", "route_id": challenger["id"]},
        "host_target": campaign["host_target"],
        "route_assurance": "verified",
        "metrics": metrics(children=True),
    }
    route = {
        "child_thread_id": "child-reader-1",
        "parent_thread_id": "root-thread-1",
        "agent_type": policy["agent_type"],
        "role": "reader",
        "observed": {
            "model": challenger["model"],
            "effort": challenger["effort"],
            "sandbox_intent": challenger["sandbox_intent"],
        },
        "verdict": "verified",
        "evidence_source": "both",
        "evidence_ref": "runtime:reader-challenger",
    }
    run["child_routes"] = [route]
    result = validate(tmp_path, campaign, run)
    assert result["run_valid"] is True

    run["arm"]["route_id"] = "undeclared-route"
    with pytest.raises(SystemExit, match="not a declared route"):
        validate(tmp_path, campaign, run)


def test_measurements_require_provenance_and_reported_token_totals_must_reconcile(tmp_path: Path):
    campaign = product_campaign()
    run = base_run(campaign)
    run["metrics"]["wall_clock_ms"] = metric("observed", 1000, None)
    with pytest.raises(SystemExit, match="source_ref"):
        validate(tmp_path, campaign, run)

    run = base_run(campaign, mode="dispatch")
    run["child_routes"] = [child_route()]
    run["route_assurance"] = "verified"
    run["metrics"] = metrics(children=True)
    run["metrics"]["aggregate_total_tokens"]["value"] = 999
    with pytest.raises(SystemExit, match="aggregate_total_tokens"):
        validate(tmp_path, campaign, run)


def test_passed_acceptance_requires_oracle_and_result_refs(tmp_path: Path):
    campaign = product_campaign()
    run = base_run(campaign)
    run["execution"]["oracle_refs"] = []
    with pytest.raises(SystemExit, match="oracle_ref"):
        validate(tmp_path, campaign, run)

    run = base_run(campaign)
    run["execution"]["result_ref"] = None
    with pytest.raises(SystemExit, match="result_ref"):
        validate(tmp_path, campaign, run)
