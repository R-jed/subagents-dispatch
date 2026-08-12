#!/usr/bin/env python3
"""Validate and deterministically identify a subagents-dispatch experiment campaign."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tomllib
from typing import Any, NoReturn

import jsonschema

from policy import load_policy_contract
from calibration_profile_contract import materialized_agent_type, role_contract_digest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "evals" / "experiment-campaign.schema.json"
PLACEHOLDERS = {"unknown", "tbd", "todo", "placeholder"}
CALIBRATION_PROFILE = ROOT / "agent-profiles" / "subagents-dispatch-reader.toml"


def fail(message: str) -> NoReturn:
    raise SystemExit(f"ERROR: {message}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and hash a subagents-dispatch experiment campaign."
    )
    parser.add_argument("campaign", type=Path)
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


def canonical_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def task_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_role_contract_digest(role: str) -> str:
    if role != "reader":
        fail("initial calibration profile materialization supports only the Reader role")
    try:
        profile = tomllib.loads(CALIBRATION_PROFILE.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        fail(f"could not load canonical Reader profile: {exc}")
    return role_contract_digest(
        role,
        str(profile.get("description", "")),
        str(profile.get("developer_instructions", "")),
        "none",
    )


def current_head() -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--verify", "HEAD"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        fail(f"could not resolve current Git HEAD: {result.stderr.strip() or result.returncode}")
    head = result.stdout.strip()
    if len(head) != 40:
        fail("current Git HEAD is not a full 40-character commit id")
    return head


def route_tuple(route: dict[str, Any]) -> tuple[str, str, str]:
    return route["model"], route["effort"], route["mutation_authority"]


def expected_control(policy: dict[str, Any], role: str) -> tuple[str, str, str]:
    try:
        configured = policy["roles"][role]
        return (
            configured["model"],
            configured["effort"],
            configured["mutation_authority"],
        )
    except (KeyError, TypeError) as exc:
        fail(f"policy does not define a complete route for role {role!r}: {exc}")


def unresolved(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip().lower()
    return not normalized or normalized in PLACEHOLDERS


def require_frozen_text(value: Any, label: str) -> None:
    if unresolved(value):
        fail(f"{label} must be a concrete non-placeholder value")


def validate_common_workloads(campaign: dict[str, Any]) -> None:
    seen: set[str] = set()
    formal = campaign["stage"] == "formal"
    for workload in campaign["workloads"]:
        workload_id = workload["id"]
        require_frozen_text(workload_id, "workload id")
        if workload_id in seen:
            fail(f"campaign duplicates workload id {workload_id!r}")
        seen.add(workload_id)

        require_frozen_text(workload["repository_url"], f"workload {workload_id!r} repository_url")
        source_task_ref = workload.get("source_task_ref")
        if source_task_ref is not None:
            require_frozen_text(source_task_ref, f"workload {workload_id!r} source_task_ref")
        require_frozen_text(workload["task_text"], f"workload {workload_id!r} task_text")

        expected_hash = task_sha256(workload["task_text"])
        if workload["task_sha256"] != expected_hash:
            fail(
                f"workload {workload_id!r} task_sha256 does not match exact UTF-8 task_text"
            )

        for index, step in enumerate(workload["reset_procedure"]):
            require_frozen_text(step, f"workload {workload_id!r} reset_procedure[{index}]")

        acceptance = workload["acceptance"]
        require_frozen_text(acceptance["rubric_id"], f"workload {workload_id!r} acceptance.rubric_id")
        for index, check in enumerate(acceptance["verification"]):
            require_frozen_text(
                check,
                f"workload {workload_id!r} acceptance.verification[{index}]",
            )

        controls = workload["controls"]
        for field in (
            "main_session_route_fingerprint",
            "permissions_fingerprint",
            "tool_surface_fingerprint",
        ):
            if unresolved(controls[field]):
                fail(
                    f"workload {workload_id!r} uses unresolved {field}; "
                    "freeze actual controlled inputs before running the campaign"
                )
        for index, ref in enumerate(controls["project_rule_refs"]):
            require_frozen_text(ref, f"workload {workload_id!r} project_rule_refs[{index}]")

        if formal:
            repository_url = workload["repository_url"].strip().lower()
            if unresolved(repository_url) or ".invalid" in repository_url:
                fail(
                    f"formal workload {workload_id!r} must bind a real repository, "
                    "not a placeholder repository_url"
                )


def validate_role_calibration(
    campaign: dict[str, Any], experiment: dict[str, Any], policy: dict[str, Any]
) -> list[str]:
    if experiment["policy_promotion"] and campaign["stage"] != "formal":
        fail("policy promotion requires a formal campaign")
    promotion_ref = experiment.get("promotion_criteria_ref")
    if promotion_ref is not None:
        require_frozen_text(promotion_ref, "promotion_criteria_ref")

    role_specs: dict[str, dict[str, Any]] = {}
    identities: set[str] = set()
    for spec in experiment["roles"]:
        role = spec["role"]
        if role != "reader":
            fail("initial calibration profile materialization supports only the Reader role")
        if role in role_specs:
            fail(f"campaign duplicates role {role!r}")
        role_specs[role] = spec
        require_frozen_text(spec["contract_ref"], f"role {role!r} contract_ref")

        control = spec["control"]
        require_frozen_text(control["id"], f"role {role!r} control id")
        require_frozen_text(control["model"], f"role {role!r} control model")
        if route_tuple(control) != expected_control(policy, role):
            fail(
                f"role {role!r} control must exactly match the current policy route; "
                "calibration cannot rewrite its baseline"
            )
        if len(spec["challengers"]) != 1:
            fail("Reader calibration currently requires exactly one challenger arm")
        challenger = spec["challengers"][0]
        if (challenger["model"], challenger["effort"], challenger["mutation_authority"]) != (
            "gpt-5.6-terra",
            "xhigh",
            "none",
        ):
            fail("Reader calibration challenger must be exactly Terra XHigh with mutation_authority=none")
        # Detect duplicate route shapes before optional materialization metadata,
        # preserving the original campaign error for malformed challengers.
        for challenger in spec["challengers"]:
            if route_tuple(challenger) == route_tuple(control):
                fail(f"role {role!r} contains a challenger identical to another route")
        if role == "reader":
            expected_digest = canonical_role_contract_digest(role)
            for route_label, route in [("control", control), *[(f"challenger {item['id']!r}", item) for item in spec["challengers"]]]:
                if route.get("semantic_role") not in {None, role}:
                    fail(f"role {role!r} {route_label} semantic_role must equal {role!r}")
                if route.get("configured_model", route["model"]) != route["model"] or route.get("configured_effort", route["effort"]) != route["effort"]:
                    fail(f"role {role!r} {route_label} configured route must match model/effort")
                expected_identity = materialized_agent_type(campaign["campaign_id"], role, route["id"])
                if route.get("materialized_agent_type", expected_identity) != expected_identity:
                    fail(f"role {role!r} {route_label} materialized_agent_type is not deterministic")
                materialized = route.get("materialized_agent_type", expected_identity)
                if materialized in identities:
                    fail(f"campaign duplicates materialized_agent_type {materialized!r}")
                identities.add(materialized)
                if route.get("role_contract_digest", expected_digest) != expected_digest:
                    fail(f"role {role!r} {route_label} role_contract_digest does not match canonical contract")

        route_ids = {control["id"]}
        route_shapes = {route_tuple(control)}
        for challenger in spec["challengers"]:
            challenger_id = challenger["id"]
            require_frozen_text(challenger_id, f"role {role!r} challenger id")
            require_frozen_text(challenger["model"], f"role {role!r} challenger {challenger_id!r} model")
            if challenger_id in route_ids:
                fail(f"role {role!r} duplicates route id {challenger_id!r}")
            route_ids.add(challenger_id)

            shape = route_tuple(challenger)
            if shape in route_shapes:
                fail(f"role {role!r} contains a challenger identical to another route")
            route_shapes.add(shape)

            if challenger["mutation_authority"] != control["mutation_authority"]:
                fail(
                    f"role {role!r} challenger {challenger_id!r} changes mutation_authority; "
                    "route calibration must keep the behavioral authority contract fixed"
                )
            if (challenger["model"], challenger["effort"]) == (control["model"], control["effort"]):
                fail(f"role {role!r} challenger {challenger_id!r} must change model and/or effort")

    workloads_by_role = {role: 0 for role in role_specs}
    for workload in campaign["workloads"]:
        workload_id = workload["id"]
        role = workload["calibration_role"]
        if "benchmark_stratum" in workload:
            fail(
                f"role-calibration workload {workload_id!r} must not carry a product benchmark_stratum"
            )
        if role not in role_specs:
            fail(
                f"workload {workload_id!r} targets calibration role {role!r}, "
                "which is not declared in experiment.roles"
            )
        require_frozen_text(
            workload["responsibility_packet_ref"],
            f"workload {workload_id!r} responsibility_packet_ref",
        )
        workloads_by_role[role] += 1

    missing = [role for role, count in workloads_by_role.items() if count == 0]
    if missing:
        fail(
            "role-calibration campaign has no workload for roles: "
            + ", ".join(sorted(missing))
        )

    return list(role_specs)


def validate_product_benchmark(campaign: dict[str, Any]) -> list[str]:
    for workload in campaign["workloads"]:
        workload_id = workload["id"]
        if "calibration_role" in workload:
            fail(
                f"product-benchmark workload {workload_id!r} must not predeclare a calibration role; "
                "actual Dispatch role use is result/runtime evidence"
            )
        if "responsibility_packet_sha256" in workload or "responsibility_packet_ref" in workload:
            fail(
                f"product-benchmark workload {workload_id!r} must not freeze a delegated responsibility packet; "
                "Dispatch decomposition is part of the product behavior under test"
            )
    return []


def validate_semantics(campaign: dict[str, Any], policy: dict[str, Any]) -> list[str]:
    require_frozen_text(campaign["campaign_id"], "campaign_id")
    require_frozen_text(campaign["host_target"]["version"], "host_target.version")
    require_frozen_text(campaign["host_target"]["platform"], "host_target.platform")

    if campaign["plugin_candidate_sha"] != current_head():
        fail(
            "plugin_candidate_sha must equal the exact current Git HEAD so the campaign control "
            "policy and tested plugin candidate cannot drift apart"
        )

    fixed_reason = campaign["repeat_policy"].get("fixed_order_reason")
    if fixed_reason is not None:
        require_frozen_text(fixed_reason, "fixed_order_reason")
    if campaign["repeat_policy"]["ordering"] == "fixed_with_reason" and fixed_reason is None:
        fail("fixed_with_reason ordering requires a concrete fixed_order_reason")

    assurance = campaign["assurance_requirements"]
    experiment = campaign["experiment"]
    claim_kind = assurance["claim_kind"]
    required = set(assurance["required"])
    allow_unknown = set(assurance["allow_unknown"])
    if required & allow_unknown:
        fail("assurance dimensions cannot be both required and allowed unknown")
    if not {"route", "permission_state"} <= required:
        fail("current model/effort and product claims require route and permission_state assurance")
    dimensions = {"route", "permission_state", "permission_provenance"}
    if required | allow_unknown != dimensions:
        fail("campaign must classify every assurance dimension as required or allowed unknown")
    if allow_unknown - {"permission_provenance"}:
        fail("route and permission_state cannot be allowed unknown")
    expected_claim = {
        "role_calibration": "model_effort",
        "product_benchmark": "product_behavior",
    }[experiment["type"]]
    if claim_kind != expected_claim:
        fail(
            f"{experiment['type']} campaign must declare claim_kind={expected_claim!r}; "
            "current experiment types cannot support a Host permission-source claim"
        )
    if experiment["type"] == "role_calibration" and claim_kind == "model_effort":
        if campaign["materialization_mode"] != "profile_only":
            fail("model_effort role calibration requires materialization_mode='profile_only'")

    validate_common_workloads(campaign)
    if experiment["type"] == "role_calibration":
        return validate_role_calibration(campaign, experiment, policy)
    if experiment["type"] == "product_benchmark":
        return validate_product_benchmark(campaign)
    fail(f"unsupported experiment type {experiment.get('type')!r}")


def validate_campaign(campaign: dict[str, Any]) -> dict[str, Any]:
    schema = load_json(SCHEMA, "experiment campaign schema")
    try:
        jsonschema.Draft202012Validator(schema).validate(campaign)
    except jsonschema.ValidationError as exc:
        path = ".".join(str(item) for item in exc.absolute_path) or "<root>"
        fail(f"campaign schema validation failed at {path}: {exc.message}")

    policy = load_policy_contract()
    roles = validate_semantics(campaign, policy)
    return {
        "campaign_id": campaign["campaign_id"],
        "stage": campaign["stage"],
        "experiment_type": campaign["experiment"]["type"],
        "materialization_mode": campaign["materialization_mode"],
        "campaign_sha256": canonical_sha256(campaign),
        "roles": roles,
        "workload_count": len(campaign["workloads"]),
        "minimum_completed_per_arm": campaign["repeat_policy"]["minimum_completed_per_arm"],
        "plugin_candidate_sha": campaign["plugin_candidate_sha"],
    }


def main() -> None:
    args = parse_args()
    campaign = load_json(args.campaign, "campaign")
    summary = validate_campaign(campaign)
    if args.json:
        json.dump(summary, sys.stdout, sort_keys=True, separators=(",", ":"))
        sys.stdout.write("\n")
        return
    print("EXPERIMENT CAMPAIGN: VALID")
    print(f"Campaign: {summary['campaign_id']}")
    print(f"Stage: {summary['stage']}")
    print(f"Experiment: {summary['experiment_type']}")
    print(f"Candidate: {summary['plugin_candidate_sha']}")
    print(f"SHA256: {summary['campaign_sha256']}")
    if summary["roles"]:
        print(f"Roles: {', '.join(summary['roles'])}")
    print(f"Workloads: {summary['workload_count']}")
    print(f"Minimum completed per arm: {summary['minimum_completed_per_arm']}")


if __name__ == "__main__":
    main()
