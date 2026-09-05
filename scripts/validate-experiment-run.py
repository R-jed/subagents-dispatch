#!/usr/bin/env python3
"""Validate one frozen subagents-dispatch experiment run.

The validator proves campaign/input/route/result/measurement provenance. It does not
materialize Agent profiles, run Codex, rank routes, or promote production policy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Mapping, NoReturn

import jsonschema

from policy import role_contracts

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "evals" / "experiment-run.schema.json"
CAMPAIGN_VALIDATOR = ROOT / "scripts" / "validate-experiment-campaign.py"
PLACEHOLDERS = {"unknown", "tbd", "todo", "placeholder"}


def fail(message: str) -> NoReturn:
    raise SystemExit(f"ERROR: {message}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate one subagents-dispatch experiment run.")
    parser.add_argument("run", type=Path)
    parser.add_argument("--campaign", required=True, type=Path)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(f"could not load {label}: {exc}")
    if not isinstance(value, dict):
        fail(f"{label} must be a JSON object")
    return value


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def unresolved(value: Any) -> bool:
    return isinstance(value, str) and (not value.strip() or value.strip().lower() in PLACEHOLDERS)


def require_ref(value: Any, label: str) -> None:
    if not isinstance(value, str) or unresolved(value):
        fail(f"{label} requires concrete evidence_ref")


def validated_campaign(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = path.read_bytes()
    fd, name = tempfile.mkstemp(prefix=".frozen-campaign-", suffix=".json", dir=path.parent)
    frozen = Path(name)
    try:
        with open(fd, "wb", closefd=True) as handle:
            handle.write(raw)
            handle.flush()
        result = subprocess.run(
            [sys.executable, str(CAMPAIGN_VALIDATOR), str(frozen), "--json"],
            cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
    finally:
        frozen.unlink(missing_ok=True)
    if result.returncode != 0:
        fail(f"campaign validation failed: {result.stderr.strip() or result.stdout.strip()}")
    try:
        summary = json.loads(result.stdout)
        campaign = json.loads(raw)
    except (json.JSONDecodeError, UnicodeError) as exc:
        fail(f"could not decode validated campaign: {exc}")
    if path.read_bytes() != raw:
        fail("campaign changed while validating the run")
    if not isinstance(summary, dict) or not isinstance(campaign, dict):
        fail("validated campaign is malformed")
    return summary, campaign


def validate_schema(run: dict[str, Any]) -> None:
    schema = load_json(SCHEMA, "experiment run schema")
    try:
        jsonschema.Draft202012Validator(schema).validate(run)
    except jsonschema.ValidationError as exc:
        where = ".".join(str(item) for item in exc.absolute_path) or "<root>"
        fail(f"run schema validation failed at {where}: {exc.message}")


def workload_by_id(campaign: Mapping[str, Any], workload_id: str) -> Mapping[str, Any]:
    matches = [item for item in campaign["workloads"] if item["id"] == workload_id]
    if len(matches) != 1:
        fail(f"workload_id {workload_id!r} does not resolve exactly once")
    return matches[0]


def calibration_route(campaign: Mapping[str, Any], role_id: str, route_id: str) -> Mapping[str, Any]:
    specs = [item for item in campaign["experiment"]["roles"] if item["role"] == role_id]
    if len(specs) != 1:
        fail(f"calibration role {role_id!r} does not resolve exactly once")
    routes = [specs[0]["control"], *specs[0]["challengers"]]
    matches = [item for item in routes if item["id"] == route_id]
    if len(matches) != 1:
        fail(f"route_id {route_id!r} is not a declared route for calibration role {role_id!r}")
    return matches[0]


def evidence_verdict(actual: Any, expected: Any, verdict: str, *, label: str, evidence_ref: Any) -> str:
    if verdict == "not_applicable":
        if actual is not None or evidence_ref is not None:
            fail(f"{label} not_applicable must not carry observed evidence")
        return verdict
    if verdict == "unknown":
        if actual is not None:
            fail(f"{label} unknown must not invent an observed value")
        require_ref(evidence_ref, f"{label}.evidence_ref")
        return verdict
    require_ref(evidence_ref, f"{label}.evidence_ref")
    matches = actual == expected
    if matches and verdict != "verified":
        fail(f"{label} exact match requires verdict=verified")
    if not matches and verdict != "failed":
        fail(f"{label} mismatch requires verdict=failed")
    return verdict


def input_assurance(run: Mapping[str, Any], campaign: Mapping[str, Any], workload: Mapping[str, Any]) -> str:
    evidence = run["input_evidence"]
    verdicts: list[str] = []
    arm = run["arm"]
    expected_plugin = "absent" if arm.get("kind") == "product_benchmark" and arm.get("mode") == "single_agent" else campaign["plugin_candidate_sha"]
    verdicts.append(evidence_verdict(
        evidence["plugin_candidate"]["observed_value"], expected_plugin,
        evidence["plugin_candidate"]["verdict"], label="input_evidence.plugin_candidate",
        evidence_ref=evidence["plugin_candidate"]["evidence_ref"],
    ))
    for field, expected in (
        ("task_sha256", workload["task_sha256"]),
        ("reset_procedure_sha256", canonical_sha256(workload["reset_procedure"])),
        ("acceptance_sha256", canonical_sha256(workload["acceptance"])),
    ):
        item = evidence[field]
        verdicts.append(evidence_verdict(item["observed_value"], expected, item["verdict"], label=f"input_evidence.{field}", evidence_ref=item["evidence_ref"]))

    packet = evidence["responsibility_packet_sha256"]
    if run["experiment_type"] == "role_calibration":
        verdicts.append(evidence_verdict(packet["observed_value"], workload["responsibility_packet_sha256"], packet["verdict"], label="input_evidence.responsibility_packet_sha256", evidence_ref=packet["evidence_ref"]))
    else:
        verdicts.append(evidence_verdict(packet["observed_value"], None, packet["verdict"], label="input_evidence.responsibility_packet_sha256", evidence_ref=packet["evidence_ref"]))
        if packet["verdict"] != "not_applicable":
            fail("product benchmark responsibility_packet_sha256 must be not_applicable")

    host = evidence["host"]
    verdicts.append(evidence_verdict(host["observed"], campaign["host_target"], host["verdict"], label="input_evidence.host", evidence_ref=host["evidence_ref"]))
    repo = evidence["repository"]
    expected_repo = {"repository_url": workload["repository_url"], "base_revision": workload["base_revision"]}
    verdicts.append(evidence_verdict(repo["observed"], expected_repo, repo["verdict"], label="input_evidence.repository", evidence_ref=repo["evidence_ref"]))

    controls = evidence["controls"]
    for field, expected in (
        ("main_session_route", workload["controls"]["main_session_route_fingerprint"]),
        ("permissions", workload["controls"]["permissions_fingerprint"]),
        ("tool_surface", workload["controls"]["tool_surface_fingerprint"]),
    ):
        item = controls[field]
        verdicts.append(evidence_verdict(item["observed_value"], expected, item["verdict"], label=f"input_evidence.controls.{field}", evidence_ref=item["evidence_ref"]))
    rules = controls["project_rules"]
    verdicts.append(evidence_verdict(rules["observed_refs"], workload["controls"]["project_rule_refs"], rules["verdict"], label="input_evidence.controls.project_rules", evidence_ref=rules["evidence_ref"]))
    derived = "failed" if "failed" in verdicts else "unknown" if "unknown" in verdicts else "verified"
    if run["input_assurance"] != derived:
        fail(f"input_assurance must be {derived!r}")
    return derived


def validate_materialization(run: Mapping[str, Any]) -> int | None:
    item = run["child_materialization"]
    if item["status"] == "unavailable":
        if item["count"] is not None:
            fail("unavailable child materialization must keep count null")
        require_ref(item["source_ref"], "child_materialization.source_ref")
        return None
    if item["count"] is None:
        fail("observed child materialization requires count")
    require_ref(item["source_ref"], "child_materialization.source_ref")
    if item["count"] != len(run["child_routes"]):
        fail("observed materialized child count must equal the number of child_routes")
    return int(item["count"])


def expected_production_request(role_id: str, requested: Mapping[str, Any]) -> bool:
    roles = role_contracts()
    spec = roles[role_id]
    return (
        requested["agent_type"] == spec["agent_type"]
        and requested["model"] == spec["model"]
        and requested["effort"] in spec["allowed_efforts"]
    )


def validate_route_layers(route: Mapping[str, Any], *, expected_agent_type: str, expected_model: str, expected_effort: str, provider_control: str | None) -> tuple[str, str, str, str]:
    requested = route["requested"]
    require_ref(requested["evidence_ref"], "child route requested.evidence_ref")
    if (requested["agent_type"], requested["model"], requested["effort"]) != (expected_agent_type, expected_model, expected_effort):
        fail("child requested route does not match the frozen expected route")

    accepted = route["accepted"]
    accepted_tuple = (accepted["agent_type"], accepted["model"], accepted["effort"])
    expected_tuple = (expected_agent_type, expected_model, expected_effort)
    if accepted["verdict"] == "unknown":
        if any(value is not None for value in accepted_tuple):
            fail("unknown accepted route must not invent accepted values")
        require_ref(accepted["evidence_ref"], "child route accepted.evidence_ref")
    else:
        require_ref(accepted["evidence_ref"], "child route accepted.evidence_ref")
        matches = accepted_tuple == expected_tuple
        if matches != (accepted["verdict"] == "verified"):
            fail("accepted route mismatch requires verdict=failed")

    observed = route["observed"]
    observed_tuple = (observed["agent_type"], observed["model"], observed["effort"])
    if observed["evidence_source"] == "none":
        if any(value is not None for value in observed_tuple) or observed["evidence_ref"] is not None:
            fail("evidence_source=none must not carry observed route values")
        observed_status = "unknown"
    else:
        require_ref(observed["evidence_ref"], "child route observed.evidence_ref")
        observed_status = "verified" if observed_tuple == expected_tuple else "failed"

    expected_route_status = "failed" if "failed" in {accepted["verdict"], observed_status} else "unknown" if "unknown" in {accepted["verdict"], observed_status} else "verified"
    if route["verdict"] != expected_route_status:
        fail(f"child route verdict must be {expected_route_status!r}")

    permission_state = route["permission_state_verdict"]
    if permission_state == "verified":
        if observed["sandbox_policy_type"] is None or observed["permission_profile_type"] is None:
            fail("verified permission state requires observed sandbox and permission profile")
    provenance = route["permission_provenance"]
    if provenance["verdict"] == "verified":
        for field in ("source_kind", "source_id", "sandbox_policy_type", "permission_profile_type", "evidence_ref", "selection_evidence_ref"):
            if provenance[field] is None:
                fail("verified permission provenance is incomplete")
    elif provenance["verdict"] == "unknown" and provenance["evidence_source"] == "none":
        if provenance["evidence_ref"] is not None or provenance["selection_evidence_ref"] is not None:
            fail("unknown permission provenance with no evidence source must not invent evidence refs")

    provider = "not_applicable"
    if provider_control is not None:
        if observed["evidence_source"] == "none" or observed["model_provider"] is None:
            provider = "unknown"
        else:
            provider = "verified" if observed["model_provider"] == provider_control else "failed"
    return expected_route_status, permission_state, provenance["verdict"], provider


def aggregate_status(values: list[str], *, empty: str = "not_applicable") -> str:
    if not values:
        return empty
    if "failed" in values:
        return "failed"
    if "unknown" in values:
        return "unknown"
    return "verified"


def validate_routes(run: Mapping[str, Any], campaign: Mapping[str, Any], count: int | None) -> tuple[str, str, str, str]:
    rows = run["child_routes"]
    seen_children: set[str] = set()
    route_values: list[str] = []
    permission_values: list[str] = []
    provenance_values: list[str] = []
    provider_values: list[str] = []

    if run["experiment_type"] == "product_benchmark" and run["arm"]["mode"] == "single_agent":
        if count != 0 or rows:
            fail("single_agent benchmark arm requires observed project child count = 0")
        return "not_applicable", "not_applicable", "not_applicable", "not_applicable"
    if count is None:
        if rows:
            fail("unavailable child materialization cannot carry child_routes")
        return "unknown", "unknown", "unknown", "unknown" if run["experiment_type"] == "role_calibration" else "not_applicable"

    if run["experiment_type"] == "role_calibration" and count != 1:
        fail("role_calibration requires exactly one observed materialized child")

    for route in rows:
        child = route["child_thread_id"]
        if child in seen_children:
            fail("child_routes duplicates child_thread_id")
        seen_children.add(child)
        if route["parent_thread_id"] != run["root_thread_id"]:
            fail("child route parent_thread_id must equal root_thread_id")
        role_id = route["role"]
        roles = role_contracts()
        if run["experiment_type"] == "role_calibration":
            if role_id != run["arm"]["role"]:
                fail("calibration child role does not match run arm")
            frozen = calibration_route(campaign, role_id, run["arm"]["route_id"])
            expected_agent_type = roles[role_id]["agent_type"]
            expected_model = frozen["model"]
            expected_effort = frozen["effort"]
            provider_control = campaign["model_provider_control"]
        else:
            if not expected_production_request(role_id, route["requested"]):
                fail("product benchmark child requested route is outside production policy")
            expected_agent_type = roles[role_id]["agent_type"]
            expected_model = route["requested"]["model"]
            expected_effort = route["requested"]["effort"]
            provider_control = None
        route_status, permission, provenance, provider = validate_route_layers(
            route,
            expected_agent_type=expected_agent_type,
            expected_model=expected_model,
            expected_effort=expected_effort,
            provider_control=provider_control,
        )
        route_values.append(route_status)
        permission_values.append(permission)
        provenance_values.append(provenance)
        if provider != "not_applicable":
            provider_values.append(provider)
    return (
        aggregate_status(route_values),
        aggregate_status(permission_values),
        aggregate_status(provenance_values),
        aggregate_status(provider_values),
    )


def validate_execution(run: Mapping[str, Any]) -> None:
    execution = run["execution"]
    if execution["status"] != "completed" and execution["acceptance_status"] == "passed":
        fail("non-completed execution cannot claim passed acceptance")
    if execution["acceptance_status"] == "passed":
        if not execution["oracle_refs"]:
            fail("passed acceptance requires at least one oracle_ref")
        require_ref(execution["result_ref"], "execution.result_ref")
    if execution["status"] == "failed":
        require_ref(execution["failure_ref"], "execution.failure_ref")
    if execution["quality_score"] is not None:
        require_ref(execution["quality_score_ref"], "execution.quality_score_ref")


def validate_measurement(item: Mapping[str, Any], label: str) -> None:
    if item["status"] == "observed":
        if item["value"] is None:
            fail(f"{label} observed requires value")
        require_ref(item["source_ref"], f"{label}.source_ref")
    else:
        if item["value"] is not None or item["source_ref"] is not None:
            fail(f"{label} {item['status']} must not carry value/source_ref")


def validate_metrics(run: Mapping[str, Any], count: int | None) -> None:
    metrics = run["metrics"]
    for name, item in metrics.items():
        validate_measurement(item, f"metrics.{name}")
    child = metrics["child_total_tokens"]
    if count == 0 and child["status"] != "not_applicable":
        fail("observed zero children requires child_total_tokens not_applicable")
    if count is None and child["status"] == "not_applicable":
        fail("unavailable child materialization cannot mark child_total_tokens not_applicable")
    main = metrics["main_total_tokens"]
    total = metrics["aggregate_total_tokens"]
    if child["status"] == main["status"] == total["status"] == "observed":
        if total["value"] != main["value"] + child["value"]:
            fail("aggregate_total_tokens must equal main_total_tokens + child_total_tokens")


def validate_run(run: dict[str, Any], campaign_path: Path) -> dict[str, Any]:
    validate_schema(run)
    summary, campaign = validated_campaign(campaign_path)
    for field in ("campaign_id", "plugin_candidate_sha", "stage"):
        if run[field] != campaign[field]:
            fail(f"run {field} does not match frozen campaign")
    if run["campaign_sha256"] != summary["campaign_sha256"]:
        fail("run campaign_sha256 does not match frozen campaign")
    if run["experiment_type"] != campaign["experiment"]["type"]:
        fail("run experiment_type does not match frozen campaign")
    workload = workload_by_id(campaign, run["workload_id"])
    input_status = input_assurance(run, campaign, workload)
    count = validate_materialization(run)
    route, permission, provenance, provider = validate_routes(run, campaign, count)
    for field, derived in (
        ("route_assurance", route),
        ("permission_state_assurance", permission),
        ("permission_provenance_assurance", provenance),
        ("provider_control_assurance", provider),
    ):
        if run[field] != derived:
            fail(f"{field} must be {derived!r}")
    validate_execution(run)
    validate_metrics(run, count)
    require_ref(run["evidence_artifact_ref"], "evidence_artifact_ref")

    required = set(campaign["assurance_requirements"]["required"])
    assurance_map = {
        "route": route,
        "permission_state": permission,
        "permission_provenance": provenance,
    }
    single_agent_baseline = (
        run["experiment_type"] == "product_benchmark"
        and run["arm"].get("mode") == "single_agent"
    )
    assurance_ok = all(
        assurance_map[item] == "verified"
        or (single_agent_baseline and assurance_map[item] == "not_applicable")
        for item in required
    )
    claim_eligible = (
        input_status == "verified"
        and assurance_ok
        and (provider == "verified" if run["experiment_type"] == "role_calibration" else True)
        and run["execution"]["status"] == "completed"
        and run["execution"]["acceptance_status"] == "passed"
    )
    return {
        "run_valid": True,
        "run_id": run["run_id"],
        "campaign_id": run["campaign_id"],
        "input_assurance": input_status,
        "materialized_children": count,
        "route_assurance": route,
        "permission_state_assurance": permission,
        "permission_provenance_assurance": provenance,
        "provider_control_assurance": provider,
        "execution_status": run["execution"]["status"],
        "claim_eligible": claim_eligible,
    }


def main() -> None:
    args = parse_args()
    result = validate_run(load_json(args.run, "run"), args.campaign)
    if args.json:
        json.dump(result, sys.stdout, sort_keys=True, separators=(",", ":"))
        sys.stdout.write("\n")
    else:
        print("EXPERIMENT RUN: VALID")
        print(f"Run: {result['run_id']}")
        print(f"Claim eligible: {result['claim_eligible']}")


if __name__ == "__main__":
    main()
