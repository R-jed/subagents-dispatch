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
sys.path.insert(0, str(SCRIPTS))
from calibration_profile_contract import materialized_agent_type, role_contract_digest  # noqa: E402
sys.path.pop(0)


def assurance_requirements(claim_kind: str = "model_effort") -> dict:
    return {
        "claim_kind": claim_kind,
        "required": ["route", "permission_state"],
        "allow_unknown": ["permission_provenance"],
    }


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


def canonical_hash(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def text_hash(text: str) -> str:
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
        "task_sha256": text_hash(task),
        "reset_procedure": ["git reset --hard BASE", "git clean -fdx"],
        "acceptance": {
            "rubric_id": "rubric-W1-v1",
            "oracle_kind": "deterministic",
            "verification": ["pytest focused-test"],
        },
        "controls": controls(),
    }
    if role is not None:
        packet = "OBJECTIVE\nChange one bounded behavior.\nVERIFICATION\npytest focused-test"
        payload["calibration_role"] = role
        payload["responsibility_packet_sha256"] = text_hash(packet)
        payload["responsibility_packet_ref"] = "fixture:calibration-packet-v1"
    if stratum is not None:
        payload["benchmark_stratum"] = stratum
    return payload


def product_campaign(*, stage: str = "exploratory") -> dict:
    return {
        "schema_version": "2.0",
        "campaign_id": "product-campaign",
        "stage": stage,
        "materialization_mode": "shared_config",
        "plugin_candidate_sha": head_sha(),
        "host_target": {"product": "Codex", "version": "test-host-1", "platform": "linux-test"},
        "repeat_policy": {
            "minimum_completed_per_arm": 3 if stage == "formal" else 1,
            "ordering": "interleaved",
        },
        "assurance_requirements": assurance_requirements("product_behavior"),
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
    profile = __import__("tomllib").loads((ROOT / "agent-profiles" / "subagents-dispatch-reader.toml").read_text())
    digest = role_contract_digest("reader", profile["description"], profile["developer_instructions"], "none")
    control = {
        "id": "reader-control",
        "model": reader["model"],
        "effort": reader["effort"],
        "mutation_authority": reader["mutation_authority"],
        "semantic_role": "reader", "configured_model": reader["model"], "configured_effort": reader["effort"], "materialized_agent_type": materialized_agent_type("calibration-campaign", "reader", "reader-control"), "role_contract_digest": digest,
    }
    challenger_effort = "xhigh"
    challenger = {
        "id": "reader-challenger",
        "model": "gpt-5.6-terra",
        "effort": challenger_effort,
        "mutation_authority": reader["mutation_authority"],
        "semantic_role": "reader", "configured_model": "gpt-5.6-terra", "configured_effort": challenger_effort, "materialized_agent_type": materialized_agent_type("calibration-campaign", "reader", "reader-challenger"), "role_contract_digest": digest,
    }
    return {
        "schema_version": "2.0",
        "campaign_id": "calibration-campaign",
        "stage": "exploratory",
        "materialization_mode": "profile_only",
        "plugin_candidate_sha": head_sha(),
        "host_target": {"product": "Codex", "version": "test-host-1", "platform": "linux-test"},
        "repeat_policy": {"minimum_completed_per_arm": 1, "ordering": "randomized"},
        "assurance_requirements": assurance_requirements(),
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


def scalar_input(value: str | None, *, verdict: str = "verified", ref: str | None = "evidence:scalar") -> dict:
    return {"observed_value": value, "verdict": verdict, "evidence_ref": ref}


def scalar_control(value: str | None, *, verdict: str = "verified", ref: str | None = "evidence:control") -> dict:
    return {"observed_fingerprint": value, "verdict": verdict, "evidence_ref": ref}


def input_evidence(campaign: dict, *, mode: str = "single_agent") -> dict:
    item = campaign["workloads"][0]
    calibration = campaign["experiment"]["type"] == "role_calibration"
    plugin_state = (
        "absent"
        if campaign["experiment"]["type"] == "product_benchmark" and mode == "single_agent"
        else campaign["plugin_candidate_sha"]
    )
    packet = (
        scalar_input(item["responsibility_packet_sha256"], ref="artifact:responsibility-packet")
        if calibration
        else scalar_input(None, verdict="not_applicable", ref=None)
    )
    return {
        "plugin_candidate": scalar_input(plugin_state, ref="plugin:observed-state"),
        "host": {
            "observed": campaign["host_target"],
            "verdict": "verified",
            "evidence_ref": "host:version-platform",
        },
        "repository": {
            "observed": {
                "repository_url": item["repository_url"],
                "base_revision": item["base_revision"],
            },
            "verdict": "verified",
            "evidence_ref": "git:remote-and-head",
        },
        "task_sha256": scalar_input(item["task_sha256"], ref="rollout:user-task-sha256"),
        "reset_procedure_sha256": scalar_input(
            canonical_hash(item["reset_procedure"]), ref="workspace:reset-procedure"
        ),
        "acceptance_sha256": scalar_input(
            canonical_hash(item["acceptance"]), ref="oracle:acceptance-contract"
        ),
        "responsibility_packet_sha256": packet,
        "controls": {
            "main_session_route": scalar_control(
                item["controls"]["main_session_route_fingerprint"], ref="host:main-route"
            ),
            "permissions": scalar_control(
                item["controls"]["permissions_fingerprint"], ref="host:permissions"
            ),
            "tool_surface": scalar_control(
                item["controls"]["tool_surface_fingerprint"], ref="host:tool-surface"
            ),
            "project_rules": {
                "observed_refs": item["controls"]["project_rule_refs"],
                "verdict": "verified",
                "evidence_ref": "workspace:project-rules",
            },
        },
    }


def materialization(count: int | None, *, source: str | None = "host:child-set") -> dict:
    return {
        "status": "observed" if count is not None else "unavailable",
        "count": count,
        "source_ref": source if count is not None else source,
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
        "root_thread_id": "root-thread-1",
        "input_assurance": "verified",
        "input_evidence": input_evidence(campaign, mode=mode),
        "child_materialization": materialization(0),
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
        "permission_state_assurance": "not_applicable",
        "permission_provenance_assurance": "not_applicable",
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
        "sandbox_policy_type": "danger-full-access",
        "permission_profile_type": "disabled",
    }
    return {
        "child_thread_id": f"child-{role}-1",
        "parent_thread_id": "root-thread-1",
        "agent_type": spec["agent_type"],
        "role": role,
        "observed": observed,
        "permission_state_verdict": "verified",
        "permission_provenance": {
            "source_kind": "parent_turn",
            "source_id": "root-thread-1",
            "sandbox_policy_type": "danger-full-access",
            "permission_profile_type": "disabled",
            "evidence_source": "native",
            "evidence_ref": "host:permission-source",
            "selection_evidence_ref": "host:permission-selection",
            "verdict": "verified",
        },
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


def add_one_child(run: dict, route: dict | None = None) -> None:
    run["child_routes"] = [route or child_route()]
    run["child_materialization"] = materialization(1)
    run["route_assurance"] = run["child_routes"][0]["verdict"]
    run["permission_state_assurance"] = run["child_routes"][0]["permission_state_verdict"]
    run["permission_provenance_assurance"] = run["child_routes"][0]["permission_provenance"]["verdict"]
    run["metrics"] = metrics(children=True)


def test_product_single_agent_run_binds_exact_campaign_without_child_routes(tmp_path: Path):
    campaign = product_campaign()
    result = validate(tmp_path, campaign, base_run(campaign))
    assert result["run_valid"] is True
    assert result["input_assurance"] == "verified"
    assert result["materialized_children"] == 0
    assert result["route_assurance"] == "not_applicable"


def test_product_dispatch_run_accepts_verified_policy_route(tmp_path: Path):
    campaign = product_campaign()
    run = base_run(campaign, mode="dispatch")
    add_one_child(run)
    result = validate(tmp_path, campaign, run)
    assert result["materialized_children"] == 1
    assert result["route_assurance"] == "verified"


def test_zero_child_dispatch_requires_observed_zero_materialization(tmp_path: Path):
    campaign = product_campaign()
    run = base_run(campaign, mode="dispatch")
    result = validate(tmp_path, campaign, run)
    assert result["run_valid"] is True
    assert result["materialized_children"] == 0

    run["child_materialization"] = materialization(None, source="host:child-set-unavailable")
    run["route_assurance"] = "unknown"
    run["permission_state_assurance"] = "unknown"
    run["permission_provenance_assurance"] = "unknown"
    run["metrics"]["child_total_tokens"] = metric("unavailable")
    run["metrics"]["aggregate_total_tokens"] = metric("unavailable")
    result = validate(tmp_path, campaign, run)
    assert result["run_valid"] is True
    assert result["materialized_children"] is None
    assert result["route_assurance"] == "unknown"


def test_materialized_child_count_cannot_omit_or_invent_route_rows(tmp_path: Path):
    campaign = product_campaign()
    run = base_run(campaign, mode="dispatch")
    run["child_materialization"] = materialization(1)
    run["route_assurance"] = "unknown"
    run["permission_state_assurance"] = "unknown"
    run["permission_provenance_assurance"] = "unknown"
    run["metrics"]["child_total_tokens"] = metric("unavailable")
    run["metrics"]["aggregate_total_tokens"] = metric("unavailable")
    with pytest.raises(SystemExit, match="count must equal the number of child_routes"):
        validate(tmp_path, campaign, run)

    run = base_run(campaign, mode="dispatch")
    run["child_routes"] = [child_route()]
    with pytest.raises(SystemExit, match="count must equal the number of child_routes"):
        validate(tmp_path, campaign, run)


def test_single_agent_requires_observed_zero_project_children(tmp_path: Path):
    campaign = product_campaign()
    run = base_run(campaign)
    run["child_materialization"] = materialization(1)
    run["child_routes"] = [child_route()]
    run["route_assurance"] = "verified"
    run["metrics"] = metrics(children=True)
    with pytest.raises(SystemExit, match="single_agent benchmark arm requires observed project child count = 0"):
        validate(tmp_path, campaign, run)


def test_formal_failed_run_is_preserved_as_valid_evidence(tmp_path: Path):
    campaign = product_campaign(stage="formal")
    run = base_run(campaign)
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


def test_non_completed_execution_cannot_claim_passed_acceptance(tmp_path: Path):
    campaign = product_campaign()
    for status in ["failed", "interrupted", "unknown"]:
        run = base_run(campaign)
        run["execution"]["status"] = status
        run["execution"]["failure_ref"] = "run:not-complete" if status != "unknown" else None
        with pytest.raises(SystemExit, match="non-completed execution"):
            validate(tmp_path, campaign, run)


def test_run_rejects_wrong_campaign_hash(tmp_path: Path):
    campaign = product_campaign()
    run = base_run(campaign)
    run["campaign_sha256"] = "f" * 64
    with pytest.raises(SystemExit, match="campaign_sha256"):
        validate(tmp_path, campaign, run)


def test_frozen_inputs_cannot_be_copied_into_observed_without_evidence_refs(tmp_path: Path):
    campaign = product_campaign()
    run = base_run(campaign)
    run["input_evidence"]["controls"]["tool_surface"]["evidence_ref"] = None
    with pytest.raises(SystemExit, match="tool_surface.evidence_ref"):
        validate(tmp_path, campaign, run)

    run = base_run(campaign)
    run["input_evidence"]["host"]["evidence_ref"] = None
    with pytest.raises(SystemExit, match="input_evidence.host.evidence_ref"):
        validate(tmp_path, campaign, run)


def test_single_agent_baseline_must_attest_plugin_absence(tmp_path: Path):
    campaign = product_campaign()
    run = base_run(campaign)
    plugin = run["input_evidence"]["plugin_candidate"]
    plugin["observed_value"] = campaign["plugin_candidate_sha"]
    with pytest.raises(SystemExit, match="plugin_candidate.*verdict=failed"):
        validate(tmp_path, campaign, run)

    plugin["verdict"] = "failed"
    run["input_assurance"] = "failed"
    result = validate(tmp_path, campaign, run)
    assert result["run_valid"] is True
    assert result["input_assurance"] == "failed"


def test_dispatch_must_attest_exact_plugin_candidate(tmp_path: Path):
    campaign = product_campaign()
    run = base_run(campaign, mode="dispatch")
    plugin = run["input_evidence"]["plugin_candidate"]
    plugin["observed_value"] = "absent"
    with pytest.raises(SystemExit, match="plugin_candidate.*verdict=failed"):
        validate(tmp_path, campaign, run)


def test_reset_and_acceptance_inputs_are_attested_not_assumed(tmp_path: Path):
    campaign = product_campaign()
    run = base_run(campaign)
    reset = run["input_evidence"]["reset_procedure_sha256"]
    reset["observed_value"] = "0" * 64
    with pytest.raises(SystemExit, match="reset_procedure_sha256.*verdict=failed"):
        validate(tmp_path, campaign, run)

    run = base_run(campaign)
    acceptance = run["input_evidence"]["acceptance_sha256"]
    acceptance["observed_value"] = "f" * 64
    with pytest.raises(SystemExit, match="acceptance_sha256.*verdict=failed"):
        validate(tmp_path, campaign, run)


def test_unknown_input_evidence_is_preserved_and_derives_unknown_assurance(tmp_path: Path):
    campaign = product_campaign()
    run = base_run(campaign)
    item = run["input_evidence"]["controls"]["main_session_route"]
    item.update(observed_fingerprint=None, verdict="unknown", evidence_ref="host:route-unavailable")
    run["input_assurance"] = "unknown"
    result = validate(tmp_path, campaign, run)
    assert result["run_valid"] is True
    assert result["input_assurance"] == "unknown"


def test_observed_input_drift_must_be_recorded_as_failed_not_hidden(tmp_path: Path):
    campaign = product_campaign()
    run = base_run(campaign)
    item = run["input_evidence"]["controls"]["tool_surface"]
    item["observed_fingerprint"] = "tools:drifted"
    with pytest.raises(SystemExit, match="requires verdict=failed"):
        validate(tmp_path, campaign, run)

    item["verdict"] = "failed"
    run["input_assurance"] = "failed"
    result = validate(tmp_path, campaign, run)
    assert result["run_valid"] is True
    assert result["input_assurance"] == "failed"


def test_host_repository_and_task_evidence_bind_actual_inputs(tmp_path: Path):
    campaign = product_campaign()
    run = base_run(campaign)
    run["input_evidence"]["repository"]["observed"]["base_revision"] = "b" * 40
    with pytest.raises(SystemExit, match="repository.*verdict=failed"):
        validate(tmp_path, campaign, run)

    run = base_run(campaign)
    run["input_evidence"]["task_sha256"]["observed_value"] = "0" * 64
    with pytest.raises(SystemExit, match="task_sha256.*verdict=failed"):
        validate(tmp_path, campaign, run)


def test_product_benchmark_packet_evidence_is_explicitly_not_applicable(tmp_path: Path):
    campaign = product_campaign()
    run = base_run(campaign)
    packet = run["input_evidence"]["responsibility_packet_sha256"]
    packet.update(observed_value="c" * 64, verdict="verified", evidence_ref="fake:packet")
    with pytest.raises(SystemExit, match="must be not_applicable"):
        validate(tmp_path, campaign, run)


def test_configured_or_self_reported_route_source_cannot_be_observed_evidence(tmp_path: Path):
    campaign = product_campaign()
    run = base_run(campaign, mode="dispatch")
    route = child_route()
    route["evidence_source"] = "configured"
    add_one_child(run, route)
    with pytest.raises(SystemExit, match="schema validation"):
        validate(tmp_path, campaign, run)


def test_evidence_source_none_cannot_carry_observed_route_values(tmp_path: Path):
    campaign = product_campaign()
    run = base_run(campaign, mode="dispatch")
    route = child_route(verdict="unknown")
    add_one_child(run, route)
    with pytest.raises(SystemExit, match="evidence_source=none must keep all observed route fields null"):
        validate(tmp_path, campaign, run)


def test_observed_route_mismatch_cannot_be_marked_verified(tmp_path: Path):
    campaign = product_campaign()
    run = base_run(campaign, mode="dispatch")
    route = child_route()
    route["observed"]["model"] = "gpt-5.6-sol"
    add_one_child(run, route)
    with pytest.raises(SystemExit, match="mismatch requires verdict=failed"):
        validate(tmp_path, campaign, run)


def test_permission_provenance_mismatch_cannot_be_marked_verified(tmp_path: Path):
    campaign = product_campaign()
    run = base_run(campaign, mode="dispatch")
    route = child_route()
    route["permission_provenance"]["sandbox_policy_type"] = "read-only"
    add_one_child(run, route)
    with pytest.raises(SystemExit, match="permission provenance verdict must be 'failed'"):
        validate(tmp_path, campaign, run)


def test_unknown_permission_provenance_does_not_erase_verified_route_or_state(tmp_path: Path):
    campaign = product_campaign()
    run = base_run(campaign, mode="dispatch")
    route = child_route()
    route["permission_provenance"] = {
        "source_kind": None,
        "source_id": None,
        "sandbox_policy_type": None,
        "permission_profile_type": None,
        "evidence_source": "none",
        "evidence_ref": None,
        "selection_evidence_ref": None,
        "verdict": "unknown",
    }
    route["evidence_source"] = "native"
    route["evidence_ref"] = "runtime:permission-source-unavailable"
    add_one_child(run, route)
    result = validate(tmp_path, campaign, run)
    assert result["route_assurance"] == "verified"
    assert result["permission_state_assurance"] == "verified"
    assert result["permission_provenance_assurance"] == "unknown"
    assert result["claim_eligible"] is True


def test_unknown_permission_provenance_cannot_support_a_source_claim(tmp_path: Path):
    campaign = product_campaign()
    campaign["assurance_requirements"] = {
        "claim_kind": "product_behavior",
        "required": ["route", "permission_state", "permission_provenance"],
        "allow_unknown": [],
    }
    run = base_run(campaign, mode="dispatch")
    route = child_route()
    route["permission_provenance"] = {
        "source_kind": "parent_turn",
        "source_id": run["root_thread_id"],
        "sandbox_policy_type": "danger-full-access",
        "permission_profile_type": "disabled",
        "evidence_source": "native",
        "evidence_ref": "host:permission-source",
        "selection_evidence_ref": None,
        "verdict": "unknown",
    }
    add_one_child(run, route)

    result = validate(tmp_path, campaign, run)

    assert result["route_assurance"] == "verified"
    assert result["permission_state_assurance"] == "verified"
    assert result["permission_provenance_assurance"] == "unknown"
    assert result["claim_eligible"] is False

    route["permission_provenance"]["verdict"] = "verified"
    run["permission_provenance_assurance"] = "verified"
    with pytest.raises(SystemExit, match="permission provenance verdict must be 'unknown'"):
        validate(tmp_path, campaign, run)


def test_duplicate_child_identity_and_forged_route_assurance_fail_closed(tmp_path: Path):
    campaign = product_campaign()
    run = base_run(campaign, mode="dispatch")
    first = child_route()
    second = child_route(role="reader")
    second["child_thread_id"] = first["child_thread_id"]
    run["child_routes"] = [first, second]
    run["child_materialization"] = materialization(2)
    run["route_assurance"] = "verified"
    run["metrics"] = metrics(children=True)
    with pytest.raises(SystemExit, match="duplicates child_thread_id"):
        validate(tmp_path, campaign, run)

    run = base_run(campaign, mode="dispatch")
    unknown = child_route(verdict="unknown")
    unknown["observed"] = {
        "model": None,
        "effort": None,
        "sandbox_policy_type": None,
        "permission_profile_type": None,
    }
    unknown["permission_state_verdict"] = "unknown"
    unknown["permission_provenance"] = {
        "source_kind": None,
        "source_id": None,
        "sandbox_policy_type": None,
        "permission_profile_type": None,
        "evidence_source": "none",
        "evidence_ref": None,
        "selection_evidence_ref": None,
        "verdict": "unknown",
    }
    add_one_child(run, unknown)
    run["route_assurance"] = "verified"
    with pytest.raises(SystemExit, match="route_assurance must be 'unknown'"):
        validate(tmp_path, campaign, run)


def calibration_run(campaign: dict) -> dict:
    challenger = campaign["experiment"]["roles"][0]["challengers"][0]
    run = base_run(campaign)
    run.update(
        run_id="run-reader-challenger-1",
        experiment_type="role_calibration",
        arm={"kind": "role_calibration", "role": "reader", "route_id": challenger["id"]},
        route_assurance="verified",
        permission_state_assurance="verified",
        permission_provenance_assurance="verified",
        child_materialization=materialization(1),
        metrics=metrics(children=True),
    )
    run["child_routes"] = [
        {
            "child_thread_id": "child-reader-1",
            "parent_thread_id": "root-thread-1",
            "agent_type": challenger["materialized_agent_type"],
            "requested_agent_type": challenger["materialized_agent_type"],
            "accepted_agent_type": challenger["materialized_agent_type"],
            "accepted_agent_type_verdict": "verified",
            "accepted_agent_type_evidence_ref": "host:accepted-agent",
            "observed_agent_type": challenger["materialized_agent_type"],
            "semantic_role": "reader",
            "materialized_agent_type": challenger["materialized_agent_type"],
            "role_contract_digest": challenger["role_contract_digest"],
            "configured_model": challenger["configured_model"],
            "configured_effort": challenger["configured_effort"],
            "role": "reader",
            "observed": {
                "model": challenger["model"],
                "effort": challenger["effort"],
                "sandbox_policy_type": "danger-full-access",
                "permission_profile_type": "disabled",
            },
            "permission_state_verdict": "verified",
            "permission_provenance": {
                "source_kind": "parent_turn",
                "source_id": "root-thread-1",
                "sandbox_policy_type": "danger-full-access",
                "permission_profile_type": "disabled",
                "evidence_source": "both",
                "evidence_ref": "host:permission-source",
                "selection_evidence_ref": "host:permission-selection",
                "verdict": "verified",
            },
            "verdict": "verified",
            "evidence_source": "both",
            "evidence_ref": "runtime:reader-challenger",
        }
    ]
    run["fresh_root_evidence"] = {
        "provisioning_root_id": "provisioning-root-1",
        "execution_root_id": "execution-root-1",
        "fork_turns": "none",
        "host_restart_evidence_ref": "host:full-app-restart",
    }
    return run


def test_role_calibration_run_binds_packet_and_declared_challenger(tmp_path: Path):
    campaign = calibration_campaign()
    run = calibration_run(campaign)
    result = validate(tmp_path, campaign, run)
    assert result["run_valid"] is True
    assert result["input_assurance"] == "verified"
    assert result["materialized_children"] == 1

    run["arm"]["route_id"] = "undeclared-route"
    with pytest.raises(SystemExit, match="not a declared route"):
        validate(tmp_path, campaign, run)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("materialized_agent_type", "subagents_dispatch_calibration_reader_wrong_0000000000000000"),
        ("role_contract_digest", "0" * 64),
        ("configured_model", "gpt-5.6-sol"),
        ("configured_effort", "low"),
    ],
)
def test_role_calibration_child_identity_and_configured_metadata_must_match_campaign(
    tmp_path: Path, field: str, value: str
):
    campaign = calibration_campaign()
    run = calibration_run(campaign)
    run["child_routes"][0][field] = value
    with pytest.raises(SystemExit, match=f"calibration child {field}"):
        validate(tmp_path, campaign, run)


def test_observed_calibration_route_mismatch_is_failed_without_overwriting_observation(tmp_path: Path):
    campaign = calibration_campaign()
    run = calibration_run(campaign)
    route = run["child_routes"][0]
    route["observed"]["model"] = "gpt-5.6-sol"
    with pytest.raises(SystemExit, match="mismatch requires verdict=failed"):
        validate(tmp_path, campaign, run)

    route["verdict"] = "failed"
    run["route_assurance"] = "failed"
    result = validate(tmp_path, campaign, run)
    assert result["route_assurance"] == "failed"
    assert route["observed"]["model"] == "gpt-5.6-sol"


def test_product_run_rejects_calibration_agent_identity_prefix(tmp_path: Path):
    campaign = product_campaign()
    run = base_run(campaign, mode="dispatch")
    route = child_route()
    route["materialized_agent_type"] = "subagents_dispatch_calibration_reader_fake"
    add_one_child(run, route)
    with pytest.raises(SystemExit, match="cannot use calibration materialized_agent_type"):
        validate(tmp_path, campaign, run)


def test_calibration_requires_distinct_fresh_roots_and_verified_agent_identity(tmp_path: Path):
    campaign = calibration_campaign()
    run = calibration_run(campaign)
    run["fresh_root_evidence"]["execution_root_id"] = run["fresh_root_evidence"]["provisioning_root_id"]
    with pytest.raises(SystemExit, match="different provisioning and execution roots"):
        validate(tmp_path, campaign, run)

    run = calibration_run(campaign)
    run["child_routes"][0]["accepted_agent_type"] = "wrong"
    with pytest.raises(SystemExit, match="accepted_agent_type"):
        validate(tmp_path, campaign, run)

    for invalid_ref in (None, "", "TBD"):
        run = calibration_run(campaign)
        run["child_routes"][0]["accepted_agent_type_evidence_ref"] = invalid_ref
        with pytest.raises(SystemExit, match="accepted_agent_type_evidence_ref"):
            validate(tmp_path, campaign, run)


def test_role_calibration_requires_observed_exactly_one_child(tmp_path: Path):
    campaign = calibration_campaign()
    run = calibration_run(campaign)
    run["child_materialization"] = materialization(None, source="host:child-set-unavailable")
    with pytest.raises(SystemExit, match="requires an observed materialized child count"):
        validate(tmp_path, campaign, run)


def test_calibration_packet_drift_cannot_be_attributed_to_model_effort(tmp_path: Path):
    campaign = calibration_campaign()
    run = calibration_run(campaign)
    run["input_evidence"]["responsibility_packet_sha256"]["observed_value"] = "d" * 64
    with pytest.raises(SystemExit, match="responsibility_packet_sha256.*verdict=failed"):
        validate(tmp_path, campaign, run)

    run["input_evidence"]["responsibility_packet_sha256"]["verdict"] = "failed"
    run["input_assurance"] = "failed"
    result = validate(tmp_path, campaign, run)
    assert result["run_valid"] is True
    assert result["input_assurance"] == "failed"


def test_measurements_require_provenance_and_reported_token_totals_must_reconcile(tmp_path: Path):
    campaign = product_campaign()
    run = base_run(campaign)
    run["metrics"]["wall_clock_ms"] = metric("observed", 1000, None)
    with pytest.raises(SystemExit, match="source_ref"):
        validate(tmp_path, campaign, run)

    run = base_run(campaign, mode="dispatch")
    add_one_child(run)
    run["metrics"]["aggregate_total_tokens"]["value"] = 999
    with pytest.raises(SystemExit, match="aggregate_total_tokens"):
        validate(tmp_path, campaign, run)


def test_unavailable_materialization_cannot_mark_child_tokens_not_applicable(tmp_path: Path):
    campaign = product_campaign()
    run = base_run(campaign, mode="dispatch")
    run["child_materialization"] = materialization(None, source="host:child-set-unavailable")
    run["route_assurance"] = "unknown"
    run["permission_state_assurance"] = "unknown"
    run["permission_provenance_assurance"] = "unknown"
    with pytest.raises(SystemExit, match="unavailable child materialization"):
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
