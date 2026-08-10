#!/usr/bin/env python3
"""Validate and deterministically identify a role-calibration campaign definition."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, NoReturn

import jsonschema

from policy import load_policy_contract

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "evals" / "role-calibration-campaign.schema.json"


def fail(message: str) -> NoReturn:
    raise SystemExit(f"ERROR: {message}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and hash a subagents-dispatch role-calibration campaign."
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


def route_tuple(route: dict[str, Any]) -> tuple[str, str, str]:
    return route["model"], route["effort"], route["sandbox_intent"]


def expected_control(policy: dict[str, Any], role: str) -> tuple[str, str, str]:
    try:
        configured = policy["roles"][role]
        return (
            configured["model"],
            configured["effort"],
            configured["sandbox_intent"],
        )
    except (KeyError, TypeError) as exc:
        fail(f"policy does not define a complete route for role {role!r}: {exc}")


def validate_semantics(campaign: dict[str, Any], policy: dict[str, Any]) -> None:
    role_specs: dict[str, dict[str, Any]] = {}
    for index, spec in enumerate(campaign["roles"]):
        role = spec["role"]
        if role in role_specs:
            fail(f"campaign duplicates role {role!r}")
        role_specs[role] = spec

        control = spec["control"]
        if route_tuple(control) != expected_control(policy, role):
            fail(
                f"role {role!r} control must exactly match the current policy route; "
                "calibration cannot rewrite its baseline"
            )

        route_ids = {control["id"]}
        route_shapes = {route_tuple(control)}
        for challenger_index, challenger in enumerate(spec["challengers"]):
            challenger_id = challenger["id"]
            if challenger_id in route_ids:
                fail(
                    f"role {role!r} duplicates route id {challenger_id!r} "
                    f"at challenger index {challenger_index}"
                )
            route_ids.add(challenger_id)

            shape = route_tuple(challenger)
            if shape in route_shapes:
                fail(f"role {role!r} contains a challenger identical to another route")
            route_shapes.add(shape)

            if challenger["sandbox_intent"] != control["sandbox_intent"]:
                fail(
                    f"role {role!r} challenger {challenger_id!r} changes sandbox_intent; "
                    "route calibration must keep the role authority/isolation contract fixed"
                )

    workload_ids: set[str] = set()
    workloads_by_role = {role: 0 for role in role_specs}
    for index, workload in enumerate(campaign["workloads"]):
        workload_id = workload["id"]
        if workload_id in workload_ids:
            fail(f"campaign duplicates workload id {workload_id!r}")
        workload_ids.add(workload_id)

        role = workload["role"]
        if role not in role_specs:
            fail(
                f"workload {workload_id!r} targets role {role!r}, which is not declared "
                "in campaign roles"
            )
        workloads_by_role[role] += 1

        expected_hash = task_sha256(workload["task_text"])
        if workload["task_sha256"] != expected_hash:
            fail(
                f"workload {workload_id!r} task_sha256 does not match exact UTF-8 task_text"
            )

        controls = workload["controls"]
        for field in ("permissions_fingerprint", "tool_surface_fingerprint"):
            if controls[field].strip().lower() in {"unknown", "tbd", "todo", "placeholder"}:
                fail(
                    f"workload {workload_id!r} uses unresolved {field}; "
                    "freeze actual controlled inputs before running the campaign"
                )

    if campaign["purpose"] == "policy_promotion":
        missing = [role for role, count in workloads_by_role.items() if count == 0]
        if missing:
            fail(
                "policy-promotion campaign has no real workload for roles: "
                + ", ".join(sorted(missing))
            )

    if campaign["repeat_policy"]["ordering"] == "fixed_with_reason":
        reason = campaign["repeat_policy"].get("fixed_order_reason")
        if not isinstance(reason, str) or not reason.strip():
            fail("fixed_with_reason ordering requires a concrete fixed_order_reason")


def validate_campaign(campaign: dict[str, Any]) -> dict[str, Any]:
    schema = load_json(SCHEMA, "role calibration schema")
    try:
        jsonschema.Draft202012Validator(schema).validate(campaign)
    except jsonschema.ValidationError as exc:
        path = ".".join(str(item) for item in exc.absolute_path) or "<root>"
        fail(f"campaign schema validation failed at {path}: {exc.message}")

    policy = load_policy_contract()
    validate_semantics(campaign, policy)
    return {
        "campaign_id": campaign["campaign_id"],
        "purpose": campaign["purpose"],
        "campaign_sha256": canonical_sha256(campaign),
        "roles": [spec["role"] for spec in campaign["roles"]],
        "workload_count": len(campaign["workloads"]),
        "minimum_completed_per_arm": campaign["repeat_policy"]["minimum_completed_per_arm"],
    }


def main() -> None:
    args = parse_args()
    campaign = load_json(args.campaign, "campaign")
    summary = validate_campaign(campaign)
    if args.json:
        json.dump(summary, sys.stdout, sort_keys=True, separators=(",", ":"))
        sys.stdout.write("\n")
        return
    print("ROLE CALIBRATION CAMPAIGN: VALID")
    print(f"Campaign: {summary['campaign_id']}")
    print(f"Purpose: {summary['purpose']}")
    print(f"SHA256: {summary['campaign_sha256']}")
    print(f"Roles: {', '.join(summary['roles'])}")
    print(f"Workloads: {summary['workload_count']}")
    print(f"Minimum completed per arm: {summary['minimum_completed_per_arm']}")


if __name__ == "__main__":
    main()
