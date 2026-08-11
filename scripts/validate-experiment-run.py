#!/usr/bin/env python3
"""Validate one campaign-bound subagents-dispatch experiment run.

This helper validates evidence identity and provenance only. It does not run Codex,
score quality, aggregate campaigns, rank routes, or mutate policy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, NoReturn

import jsonschema

from policy import load_policy_contract

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "evals" / "experiment-run.schema.json"
CAMPAIGN_VALIDATOR = ROOT / "scripts" / "validate-experiment-campaign.py"
PLACEHOLDERS = {"unknown", "tbd", "todo", "placeholder"}


def fail(message: str) -> NoReturn:
    raise SystemExit(f"ERROR: {message}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate one experiment run against its frozen campaign."
    )
    parser.add_argument("run", type=Path)
    parser.add_argument("--campaign", required=True, type=Path)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable summary.")
    return parser.parse_args()


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(f"could not load {label}: {exc}")
    if not isinstance(payload, dict):
        fail(f"{label} must be a JSON object")
    return payload


def unresolved(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip().lower()
    return not normalized or normalized in PLACEHOLDERS


def require_text(value: Any, label: str) -> None:
    if not isinstance(value, str) or unresolved(value):
        fail(f"{label} must be a concrete non-placeholder string")


def canonical_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def validated_campaign_summary(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, str(CAMPAIGN_VALIDATOR), str(path), "--json"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or str(result.returncode)
        fail(f"campaign validation failed: {detail}")
    try:
        summary = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        fail(f"campaign validator returned invalid JSON: {exc}")
    if not isinstance(summary, dict):
        fail("campaign validator summary must be a JSON object")
    return summary


def validate_schema(run: dict[str, Any]) -> None:
    schema = load_json(SCHEMA, "experiment run schema")
    try:
        jsonschema.Draft202012Validator(schema).validate(run)
    except jsonschema.ValidationError as exc:
        path = ".".join(str(item) for item in exc.absolute_path) or "<root>"
        fail(f"run schema validation failed at {path}: {exc.message}")


def workload_by_id(campaign: dict[str, Any], workload_id: str) -> dict[str, Any]:
    matches = [item for item in campaign["workloads"] if item["id"] == workload_id]
    if len(matches) != 1:
        fail(f"workload_id {workload_id!r} does not resolve exactly once in the campaign")
    return matches[0]


def calibration_route(
    campaign: dict[str, Any], role: str, route_id: str
) -> dict[str, Any]:
    specs = [item for item in campaign["experiment"]["roles"] if item["role"] == role]
    if len(specs) != 1:
        fail(f"calibration role {role!r} does not resolve exactly once in experiment.roles")
    spec = specs[0]
    routes = [spec["control"], *spec["challengers"]]
    matches = [route for route in routes if route["id"] == route_id]
    if len(matches) != 1:
        fail(f"route_id {route_id!r} is not a declared route for calibration role {role!r}")
    return matches[0]


def validate_measurement(measurement: dict[str, Any], label: str) -> None:
    status = measurement["status"]
    value = measurement["value"]
    source_ref = measurement["source_ref"]
    if status == "observed":
        if value is None:
            fail(f"{label} observed measurement requires a value")
        require_text(source_ref, f"{label}.source_ref")
        return
    if value is not None or source_ref is not None:
        fail(f"{label} {status} measurement must keep value and source_ref null")


def validate_execution(run: dict[str, Any]) -> None:
    execution = run["execution"]
    for index, ref in enumerate(execution["oracle_refs"]):
        require_text(ref, f"execution.oracle_refs[{index}]")

    if execution["acceptance_status"] in {"passed", "failed"} and not execution["oracle_refs"]:
        fail("passed/failed acceptance requires at least one concrete oracle_ref")

    score = execution["quality_score"]
    score_ref = execution["quality_score_ref"]
    if score is None:
        if score_ref is not None:
            fail("quality_score_ref must be null when quality_score is unavailable")
    else:
        require_text(score_ref, "execution.quality_score_ref")

    result_ref = execution["result_ref"]
    if result_ref is not None:
        require_text(result_ref, "execution.result_ref")
    if execution["acceptance_status"] == "passed" and result_ref is None:
        fail("passed acceptance requires a concrete result_ref")

    failure_ref = execution["failure_ref"]
    if execution["status"] == "completed":
        if failure_ref is not None:
            fail("completed execution must keep failure_ref null")
    elif execution["status"] in {"failed", "interrupted"}:
        require_text(failure_ref, "execution.failure_ref")
    elif failure_ref is not None:
        require_text(failure_ref, "execution.failure_ref")


def expected_policy_route(policy: dict[str, Any], role: str) -> dict[str, Any]:
    try:
        spec = policy["roles"][role]
        return {
            "agent_type": spec["agent_type"],
            "model": spec["model"],
            "effort": spec["effort"],
            "sandbox_intent": spec["sandbox_intent"],
        }
    except (KeyError, TypeError) as exc:
        fail(f"policy does not define complete route truth for role {role!r}: {exc}")


def validate_child_route(
    route: dict[str, Any],
    *,
    root_thread_id: str,
    expected: dict[str, Any],
) -> None:
    for field in ("child_thread_id", "parent_thread_id", "agent_type"):
        require_text(route[field], f"child route {field}")
    if route["parent_thread_id"] != root_thread_id:
        fail("child route parent_thread_id must equal the run root_thread_id")
    if route["agent_type"] != expected["agent_type"]:
        fail(
            f"child route agent_type {route['agent_type']!r} does not match expected "
            f"{expected['agent_type']!r}"
        )

    observed = route["observed"]
    mismatches: list[str] = []
    for field in ("model", "effort", "sandbox_intent"):
        value = observed[field]
        if value is not None and value != expected[field]:
            mismatches.append(field)

    if mismatches and route["verdict"] != "failed":
        fail(
            "observed route mismatch requires verdict=failed for fields: "
            + ", ".join(mismatches)
        )

    source = route["evidence_source"]
    evidence_ref = route["evidence_ref"]
    if route["verdict"] in {"verified", "failed"}:
        if source == "none":
            fail(f"{route['verdict']} child route requires actual runtime evidence")
        require_text(evidence_ref, "child route evidence_ref")
    elif source == "none":
        if evidence_ref is not None:
            fail("unknown child route with evidence_source=none must keep evidence_ref null")
    else:
        require_text(evidence_ref, "child route evidence_ref")

    if route["verdict"] == "verified":
        missing = [field for field in ("model", "effort", "sandbox_intent") if observed[field] is None]
        if missing:
            fail("verified child route is missing observed fields: " + ", ".join(missing))
        if mismatches:
            fail("verified child route cannot contain observed route mismatches")


def derived_route_assurance(routes: list[dict[str, Any]]) -> str:
    if not routes:
        return "not_applicable"
    verdicts = {route["verdict"] for route in routes}
    if "failed" in verdicts:
        return "failed"
    if "unknown" in verdicts:
        return "unknown"
    return "verified"


def validate_product_arm(
    run: dict[str, Any], campaign: dict[str, Any], policy: dict[str, Any]
) -> None:
    arm = run["arm"]
    if arm["kind"] != "product_benchmark":
        fail("product_benchmark campaign requires a product_benchmark run arm")
    allowed_modes = {
        campaign["experiment"]["baseline_mode"],
        campaign["experiment"]["candidate_mode"],
    }
    if arm["mode"] not in allowed_modes:
        fail(f"run arm mode {arm['mode']!r} is not declared by the product benchmark campaign")

    routes = run["child_routes"]
    if arm["mode"] == "single_agent" and routes:
        fail("single_agent benchmark arm must not contain project child route evidence")

    seen_children: set[str] = set()
    for route in routes:
        child_id = route["child_thread_id"]
        if child_id in seen_children:
            fail(f"run duplicates child_thread_id {child_id!r}")
        seen_children.add(child_id)
        expected = expected_policy_route(policy, route["role"])
        validate_child_route(route, root_thread_id=run["root_thread_id"], expected=expected)


def validate_calibration_arm(
    run: dict[str, Any], campaign: dict[str, Any], workload: dict[str, Any], policy: dict[str, Any]
) -> None:
    arm = run["arm"]
    if arm["kind"] != "role_calibration":
        fail("role_calibration campaign requires a role_calibration run arm")
    if arm["role"] != workload["calibration_role"]:
        fail("calibration run arm role must match the workload calibration_role")

    selected = calibration_route(campaign, arm["role"], arm["route_id"])
    routes = run["child_routes"]
    if len(routes) != 1:
        fail("role_calibration run must bind exactly one materialized project child")
    route = routes[0]
    if route["role"] != arm["role"]:
        fail("calibration child role must match the selected calibration arm role")

    policy_route = expected_policy_route(policy, arm["role"])
    expected = {
        "agent_type": policy_route["agent_type"],
        "model": selected["model"],
        "effort": selected["effort"],
        "sandbox_intent": selected["sandbox_intent"],
    }
    validate_child_route(route, root_thread_id=run["root_thread_id"], expected=expected)


def validate_metrics(run: dict[str, Any]) -> None:
    metrics = run["metrics"]
    for name, measurement in metrics.items():
        validate_measurement(measurement, f"metrics.{name}")

    main = metrics["main_total_tokens"]
    child = metrics["child_total_tokens"]
    aggregate = metrics["aggregate_total_tokens"]
    has_children = bool(run["child_routes"])

    if not has_children and child["status"] != "not_applicable":
        fail("run without materialized children must mark child_total_tokens not_applicable")
    if has_children and child["status"] == "not_applicable":
        fail("run with materialized children cannot mark child_total_tokens not_applicable")

    if main["status"] == "observed" and child["status"] == "observed":
        if aggregate["status"] != "observed":
            fail("observed main and child token totals require an observed aggregate_total_tokens")
        if aggregate["value"] != main["value"] + child["value"]:
            fail("aggregate_total_tokens must equal observed main_total_tokens + child_total_tokens")
    elif not has_children and main["status"] == "observed":
        if aggregate["status"] != "observed" or aggregate["value"] != main["value"]:
            fail("run without children must keep observed aggregate_total_tokens equal to main_total_tokens")


def validate_run(run: dict[str, Any], campaign_path: Path) -> dict[str, Any]:
    validate_schema(run)
    campaign_summary = validated_campaign_summary(campaign_path)
    campaign = load_json(campaign_path, "campaign")

    for field, expected in (
        ("campaign_id", campaign_summary["campaign_id"]),
        ("campaign_sha256", campaign_summary["campaign_sha256"]),
        ("plugin_candidate_sha", campaign_summary["plugin_candidate_sha"]),
        ("stage", campaign_summary["stage"]),
        ("experiment_type", campaign_summary["experiment_type"]),
    ):
        if run[field] != expected:
            fail(f"run {field} does not match the validated campaign")

    for field in ("run_id", "workload_id", "root_thread_id", "evidence_artifact_ref"):
        require_text(run[field], field)

    if run["host_target"] != campaign["host_target"]:
        fail("run host_target must exactly match the frozen campaign host_target")

    workload = workload_by_id(campaign, run["workload_id"])
    if run["observed_controls"] != workload["controls"]:
        fail("run observed_controls must exactly match the workload's frozen controls")

    validate_execution(run)
    policy = load_policy_contract()
    if campaign["experiment"]["type"] == "product_benchmark":
        validate_product_arm(run, campaign, policy)
    else:
        validate_calibration_arm(run, campaign, workload, policy)

    expected_assurance = derived_route_assurance(run["child_routes"])
    if run["route_assurance"] != expected_assurance:
        fail(
            f"route_assurance must be {expected_assurance!r} for the recorded child route verdicts"
        )

    validate_metrics(run)
    return {
        "run_valid": True,
        "run_id": run["run_id"],
        "run_sha256": canonical_sha256(run),
        "campaign_id": run["campaign_id"],
        "campaign_sha256": run["campaign_sha256"],
        "experiment_type": run["experiment_type"],
        "workload_id": run["workload_id"],
        "repeat_index": run["repeat_index"],
        "route_assurance": run["route_assurance"],
        "execution_status": run["execution"]["status"],
        "acceptance_status": run["execution"]["acceptance_status"],
        "materialized_children": len(run["child_routes"]),
    }


def main() -> None:
    args = parse_args()
    run = load_json(args.run, "experiment run")
    summary = validate_run(run, args.campaign)
    if args.json:
        json.dump(summary, sys.stdout, sort_keys=True, separators=(",", ":"))
        sys.stdout.write("\n")
        return
    print("EXPERIMENT RUN: VALID")
    print(f"Run: {summary['run_id']}")
    print(f"Campaign: {summary['campaign_id']} ({summary['campaign_sha256']})")
    print(f"Experiment: {summary['experiment_type']}")
    print(f"Workload: {summary['workload_id']}")
    print(f"Repeat: {summary['repeat_index']}")
    print(f"Route assurance: {summary['route_assurance']}")
    print(f"Execution: {summary['execution_status']}")
    print(f"Acceptance: {summary['acceptance_status']}")
    print(f"Materialized children: {summary['materialized_children']}")
    print(f"SHA256: {summary['run_sha256']}")


if __name__ == "__main__":
    main()
