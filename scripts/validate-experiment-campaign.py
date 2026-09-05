#!/usr/bin/env python3
"""Validate and deterministically identify a subagents-dispatch experiment campaign."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, NoReturn

import jsonschema

from policy import role_contracts

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "evals" / "experiment-campaign.schema.json"
PLACEHOLDERS = {"unknown", "tbd", "todo", "placeholder"}


def fail(message: str) -> NoReturn:
    raise SystemExit(f"ERROR: {message}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate and hash a subagents-dispatch experiment campaign.")
    parser.add_argument("campaign", type=Path)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(f"could not load {label}: {exc}")
    if not isinstance(payload, dict):
        fail(f"{label} must be a JSON object")
    return payload


def canonical_sha256(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def current_head() -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--verify", "HEAD"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if result.returncode != 0:
        fail(f"could not resolve current Git HEAD: {result.stderr.strip() or result.returncode}")
    value = result.stdout.strip()
    if len(value) != 40:
        fail("current Git HEAD is not a full 40-character commit id")
    return value


def unresolved(value: Any) -> bool:
    return isinstance(value, str) and (not value.strip() or value.strip().lower() in PLACEHOLDERS)


def require_text(value: Any, label: str) -> None:
    if not isinstance(value, str) or unresolved(value):
        fail(f"{label} must be a concrete non-placeholder string")


def route_shape(route: Mapping[str, Any]) -> tuple[str, str, str]:
    return str(route["model"]), str(route["effort"]), str(route["mutation_authority"])


def validate_assurance(campaign: Mapping[str, Any]) -> None:
    assurance = campaign["assurance_requirements"]
    required = set(assurance["required"])
    allowed_unknown = set(assurance["allow_unknown"])
    dimensions = {"route", "permission_state", "permission_provenance"}
    if required & allowed_unknown:
        fail("assurance dimensions cannot be both required and allowed unknown")
    if required | allowed_unknown != dimensions:
        fail("campaign must classify every assurance dimension as required or allowed unknown")
    if not {"route", "permission_state"} <= required:
        fail("route and permission_state assurance are required")
    experiment_type = campaign["experiment"]["type"]
    expected_claim = "model_effort" if experiment_type == "role_calibration" else "product_behavior"
    if assurance["claim_kind"] != expected_claim:
        fail(f"{experiment_type} campaign must declare claim_kind={expected_claim!r}")


def validate_workloads(campaign: Mapping[str, Any], *, calibration_role: str | None) -> None:
    seen: set[str] = set()
    for workload in campaign["workloads"]:
        workload_id = workload["id"]
        require_text(workload_id, "workload id")
        if workload_id in seen:
            fail(f"campaign duplicates workload id {workload_id!r}")
        seen.add(workload_id)
        for field in ("repository_url", "task_text"):
            require_text(workload[field], f"workload {workload_id!r} {field}")
        if workload["task_sha256"] != text_sha256(workload["task_text"]):
            fail(f"workload {workload_id!r} task_sha256 does not match exact UTF-8 task_text")
        for step in workload["reset_procedure"]:
            require_text(step, f"workload {workload_id!r} reset_procedure")
        require_text(workload["acceptance"]["rubric_id"], f"workload {workload_id!r} acceptance.rubric_id")
        for check in workload["acceptance"]["verification"]:
            require_text(check, f"workload {workload_id!r} acceptance.verification")
        controls = workload["controls"]
        for field in ("main_session_route_fingerprint", "permissions_fingerprint", "tool_surface_fingerprint"):
            require_text(controls[field], f"workload {workload_id!r} {field}")
        for ref in controls["project_rule_refs"]:
            require_text(ref, f"workload {workload_id!r} project_rule_refs")
        if campaign["stage"] == "formal" and ".invalid" in workload["repository_url"].lower():
            fail(f"formal workload {workload_id!r} must bind a real repository")
        if calibration_role is None:
            if "calibration_role" in workload or "responsibility_packet_sha256" in workload or "responsibility_packet_ref" in workload:
                fail(f"product-benchmark workload {workload_id!r} must not freeze calibration responsibility fields")
        else:
            if workload["calibration_role"] != calibration_role:
                fail(f"workload {workload_id!r} calibration_role must equal {calibration_role!r}")
            require_text(workload["responsibility_packet_ref"], f"workload {workload_id!r} responsibility_packet_ref")
            if "benchmark_stratum" in workload:
                fail(f"role-calibration workload {workload_id!r} must not carry benchmark_stratum")


def validate_role_calibration(campaign: Mapping[str, Any]) -> list[str]:
    experiment = campaign["experiment"]
    if experiment["policy_promotion"] and campaign["stage"] != "formal":
        fail("policy promotion requires a formal campaign")
    if experiment.get("promotion_criteria_ref") is not None:
        require_text(experiment["promotion_criteria_ref"], "promotion_criteria_ref")
    require_text(campaign.get("model_provider_control"), "model_provider_control")

    spec = experiment["roles"][0]
    role_id = spec["role"]
    require_text(spec["contract_ref"], f"role {role_id!r} contract_ref")
    roles = role_contracts()
    production = roles[role_id]
    control = spec["control"]
    if control["model"] != production["model"] or control["effort"] not in production["allowed_efforts"]:
        fail(f"role {role_id!r} control must be a current production policy route")
    ids = {control["id"]}
    shapes = {route_shape(control)}
    for challenger in spec["challengers"]:
        if challenger["id"] in ids:
            fail(f"role {role_id!r} duplicates route id {challenger['id']!r}")
        ids.add(challenger["id"])
        shape = route_shape(challenger)
        if shape in shapes:
            fail(f"role {role_id!r} contains a challenger identical to another route")
        shapes.add(shape)
        if challenger["mutation_authority"] != control["mutation_authority"]:
            fail(f"role {role_id!r} challenger changes mutation_authority")
    validate_workloads(campaign, calibration_role=role_id)
    return [role_id]


def validate_campaign(campaign: dict[str, Any]) -> dict[str, Any]:
    schema = load_json(SCHEMA, "experiment campaign schema")
    try:
        jsonschema.Draft202012Validator(schema).validate(campaign)
    except jsonschema.ValidationError as exc:
        where = ".".join(str(item) for item in exc.absolute_path) or "<root>"
        fail(f"campaign schema validation failed at {where}: {exc.message}")
    require_text(campaign["campaign_id"], "campaign_id")
    require_text(campaign["host_target"]["version"], "host_target.version")
    require_text(campaign["host_target"]["platform"], "host_target.platform")
    if campaign["plugin_candidate_sha"] != current_head():
        fail("plugin_candidate_sha must equal the exact current Git HEAD")
    fixed_reason = campaign["repeat_policy"].get("fixed_order_reason")
    if fixed_reason is not None:
        require_text(fixed_reason, "fixed_order_reason")
    validate_assurance(campaign)
    if campaign["experiment"]["type"] == "role_calibration":
        roles = validate_role_calibration(campaign)
    else:
        validate_workloads(campaign, calibration_role=None)
        roles = []
    return {
        "campaign_id": campaign["campaign_id"],
        "stage": campaign["stage"],
        "experiment_type": campaign["experiment"]["type"],
        "campaign_sha256": canonical_sha256(campaign),
        "roles": roles,
        "workload_count": len(campaign["workloads"]),
        "minimum_completed_per_arm": campaign["repeat_policy"]["minimum_completed_per_arm"],
        "plugin_candidate_sha": campaign["plugin_candidate_sha"],
    }


def main() -> None:
    args = parse_args()
    summary = validate_campaign(load_json(args.campaign, "campaign"))
    if args.json:
        json.dump(summary, sys.stdout, sort_keys=True, separators=(",", ":"))
        sys.stdout.write("\n")
    else:
        print("EXPERIMENT CAMPAIGN: VALID")
        print(f"Campaign: {summary['campaign_id']}")
        print(f"SHA256: {summary['campaign_sha256']}")


if __name__ == "__main__":
    main()
