#!/usr/bin/env python3
# Portions incorporate MIT-licensed third-party validation logic.
# Copyright (c) 2026 Zhijian AI / Dapeng. MIT licensed.
# See ../THIRD_PARTY_NOTICES.md.
from __future__ import annotations

import argparse
import json
from typing import Any

from policy import load_policy_contract
from validate_team_plan import (
    load_input,
    nonempty_string,
    valid_int,
    validate_team_plan_payload,
)


CURRENT_SCHEMA_VERSION = "1.0"
TOP_LEVEL_FIELDS = {"schema_version", "team_plans", "active_team_plan_revision", "attempts"}
CONTROL_STATES = {
    "PLANNED",
    "SPAWN_PENDING",
    "RUNNING",
    "INTERRUPTED",
    "COMPLETED",
    "FAILED",
    "UNKNOWN",
    "CLOSED",
}
FAILURE_ORIGINS = {
    "none",
    "runtime_unavailable",
    "permission_failure",
    "tool_failure",
    "timeout",
    "quality_failure",
    "runtime_ambiguous",
}
TASK_BLOCKERS = {"none", "contract", "judgment", "investigation", "stalled"}
ATTEMPT_FIELDS = {
    "unit_id",
    "team_plan_revision",
    "task_id",
    "attempt",
    "agent_type",
    "agent_id",
    "control_state",
    "followup_count",
    "adopted",
    "accepted",
    "failure_origin",
    "task_blocker",
}


def load_role_agent_types() -> dict[str, str]:
    try:
        roles = load_policy_contract()["roles"]
    except (RuntimeError, KeyError, TypeError) as exc:
        raise RuntimeError(f"invalid policy contract: {exc}") from exc
    if not isinstance(roles, dict) or not roles:
        raise RuntimeError("policy contract must define recovery-ledger roles")
    mapping: dict[str, str] = {}
    for role, spec in roles.items():
        if not isinstance(role, str) or not role or not isinstance(spec, dict):
            raise RuntimeError("policy contract contains invalid role definitions")
        agent_type = spec.get("agent_type")
        if not isinstance(agent_type, str) or not agent_type:
            raise RuntimeError(f"policy contract role {role!r} has invalid agent_type")
        mapping[role] = agent_type
    if len(set(mapping.values())) != len(mapping):
        raise RuntimeError("policy contract contains duplicate agent_type values")
    return mapping


ROLE_AGENT_TYPES = load_role_agent_types()


def validate_team_ledger_payload(payload: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "fail",
        "ledger_valid": False,
        "record_count": 0,
        "unit_count": 0,
        "errors": [],
        "warnings": [],
    }
    errors: list[str] = result["errors"]

    if not isinstance(payload, dict):
        errors.append("ledger must be a JSON object")
        return result

    missing_fields = TOP_LEVEL_FIELDS - set(payload)
    extra_fields = set(payload) - TOP_LEVEL_FIELDS
    if missing_fields:
        errors.append("ledger is missing fields: " + ", ".join(sorted(missing_fields)))
    if extra_fields:
        errors.append("ledger has unsupported fields: " + ", ".join(sorted(extra_fields)))

    if payload.get("schema_version") != CURRENT_SCHEMA_VERSION:
        errors.append("unsupported ledger schema_version")

    team_plans = payload.get("team_plans", [])
    active_revision = payload.get("active_team_plan_revision")
    if not isinstance(team_plans, list):
        errors.append("team_plans must be an array")
        team_plans = []

    plans_by_revision: dict[int, dict[str, Any]] = {}
    units_by_revision: dict[int, dict[str, dict[str, Any]]] = {}
    stable_unit_identity: dict[str, tuple[str, str]] = {}
    if team_plans:
        revisions: list[int] = []
        for index, team_plan in enumerate(team_plans):
            validation = validate_team_plan_payload(team_plan)
            if not validation["team_plan_valid"]:
                for error in validation["errors"]:
                    errors.append(f"team_plans[{index}] is invalid: {error}")
                continue
            revision = team_plan["revision"]
            revisions.append(revision)
            plans_by_revision[revision] = team_plan
            units = {unit["unit_id"]: unit for unit in team_plan["units"]}
            units_by_revision[revision] = units
            for unit_id, unit in units.items():
                identity = (unit["goal"].strip(), unit["output"].strip())
                prior = stable_unit_identity.get(unit_id)
                if prior is not None and prior != identity:
                    errors.append(
                        f"{unit_id} changes goal/output across TeamPlan revisions; use a new unit_id"
                    )
                else:
                    stable_unit_identity[unit_id] = identity

        if revisions and revisions != list(range(1, len(revisions) + 1)):
            errors.append("TeamPlan revisions must be ordered and contiguous from 1")
        if not valid_int(active_revision, minimum=1) or active_revision not in plans_by_revision:
            errors.append("active_team_plan_revision must name an available revision")
        elif revisions and active_revision != revisions[-1]:
            errors.append("active_team_plan_revision must name the latest revision")
    elif active_revision is not None:
        errors.append("active_team_plan_revision must be null when no TeamPlan exists")

    records = payload.get("attempts")
    if not isinstance(records, list):
        errors.append("attempts must be an array")
        return result
    result["record_count"] = len(records)

    task_ids: set[str] = set()
    agent_ids: set[str] = set()
    records_by_unit: dict[str, list[dict[str, Any]]] = {}
    seen_units: set[str] = set()

    for index, record in enumerate(records):
        prefix = f"attempt {index}"
        if not isinstance(record, dict):
            errors.append(f"{prefix} must be an object")
            continue

        missing = ATTEMPT_FIELDS - set(record)
        if missing:
            errors.append(f"{prefix} is missing fields: {', '.join(sorted(missing))}")
            continue
        extra = set(record) - ATTEMPT_FIELDS
        if extra:
            errors.append(f"{prefix} has unsupported fields: {', '.join(sorted(extra))}")

        unit_id = record.get("unit_id")
        if not nonempty_string(unit_id):
            errors.append(f"{prefix} has invalid unit_id")
            continue
        seen_units.add(unit_id)
        records_by_unit.setdefault(unit_id, []).append(record)

        task_id = record.get("task_id")
        if not nonempty_string(task_id):
            errors.append(f"{prefix} has invalid task_id")
        elif task_id in task_ids:
            errors.append(f"{prefix} duplicates task_id {task_id}")
        else:
            task_ids.add(task_id)

        attempt = record.get("attempt")
        if not valid_int(attempt, minimum=1) or attempt > 2:
            errors.append(f"{prefix} attempt must be 1 or 2")

        followup_count = record.get("followup_count")
        if not valid_int(followup_count) or followup_count > 1:
            errors.append(f"{prefix} followup_count must be 0 or 1")

        if not isinstance(record.get("adopted"), bool):
            errors.append(f"{prefix} adopted must be boolean")
        if not isinstance(record.get("accepted"), bool):
            errors.append(f"{prefix} accepted must be boolean")

        state = record.get("control_state")
        state_valid = isinstance(state, str) and state in CONTROL_STATES
        if not state_valid:
            errors.append(f"{prefix} has invalid control_state")

        failure_origin = record.get("failure_origin")
        failure_origin_valid = isinstance(failure_origin, str) and failure_origin in FAILURE_ORIGINS
        if not failure_origin_valid:
            errors.append(f"{prefix} has invalid failure_origin")

        task_blocker = record.get("task_blocker")
        task_blocker_valid = isinstance(task_blocker, str) and task_blocker in TASK_BLOCKERS
        if not task_blocker_valid:
            errors.append(f"{prefix} has invalid task_blocker")

        agent_type = record.get("agent_type")
        if not isinstance(agent_type, str) or agent_type not in ROLE_AGENT_TYPES.values():
            errors.append(f"{prefix} has unsupported agent_type")

        agent_id = record.get("agent_id")
        if agent_id is not None and not nonempty_string(agent_id):
            errors.append(f"{prefix} has invalid agent_id")
        elif isinstance(agent_id, str):
            if agent_id in agent_ids:
                errors.append(f"{prefix} duplicates agent_id {agent_id}")
            else:
                agent_ids.add(agent_id)

        revision = record.get("team_plan_revision")
        if team_plans:
            if not valid_int(revision, minimum=1) or revision not in units_by_revision:
                errors.append(f"{prefix} has invalid team_plan_revision")
            elif unit_id not in units_by_revision[revision]:
                errors.append(f"{prefix} unit_id is not present in its TeamPlan revision")
            else:
                role = units_by_revision[revision][unit_id]["role"]
                expected_agent = ROLE_AGENT_TYPES[role]
                if agent_type != expected_agent:
                    errors.append(f"{prefix} agent_type does not match TeamPlan role")
        elif revision is not None:
            errors.append(f"{prefix} team_plan_revision must be null without TeamPlan")

        if state_valid and state in {"PLANNED", "SPAWN_PENDING"} and agent_id is not None:
            errors.append(f"{prefix} must not claim agent_id before RUNNING")
        if state_valid and state in {"RUNNING", "INTERRUPTED", "COMPLETED", "FAILED", "CLOSED"} and agent_id is None:
            errors.append(f"{prefix} requires agent_id in {state}")

        adopted = record.get("adopted")
        accepted = record.get("accepted")
        if adopted is True and (not state_valid or state not in {"COMPLETED", "CLOSED"}):
            errors.append(f"{prefix} cannot be adopted before completion")
        if adopted is True and accepted is not True:
            errors.append(f"{prefix} adopted=true requires accepted evidence")
        if accepted is True and (not state_valid or state not in {"COMPLETED", "CLOSED"}):
            errors.append(f"{prefix} accepted evidence requires completed or closed state")

        if state == "UNKNOWN":
            if failure_origin != "runtime_ambiguous":
                errors.append(f"{prefix} UNKNOWN requires failure_origin=runtime_ambiguous")
            if adopted is True:
                errors.append(f"{prefix} UNKNOWN cannot be adopted")
        elif failure_origin == "runtime_ambiguous":
            errors.append(f"{prefix} runtime_ambiguous requires UNKNOWN state")

        if state == "FAILED":
            if failure_origin == "none":
                errors.append(f"{prefix} FAILED requires a failure_origin")
        elif state_valid and state in {"PLANNED", "SPAWN_PENDING", "RUNNING", "INTERRUPTED", "COMPLETED", "CLOSED"}:
            if failure_origin_valid and failure_origin != "none":
                errors.append(f"{prefix} non-failure state requires failure_origin=none")

        if state_valid and state not in {"FAILED", "UNKNOWN"} and task_blocker_valid and task_blocker != "none":
            errors.append(f"{prefix} task_blocker belongs only on FAILED or UNKNOWN state")

    result["unit_count"] = len(seen_units)
    if not team_plans and len(seen_units) > 1:
        errors.append("multiple delegated units require TeamPlan binding")

    def attempt_sort_key(record: dict[str, Any]) -> int:
        value = record.get("attempt")
        return value if valid_int(value, minimum=1) else 3

    for unit_id, unit_records in records_by_unit.items():
        ordered = sorted(unit_records, key=attempt_sort_key)
        attempts = [item.get("attempt") for item in ordered]
        if attempts != list(range(1, len(ordered) + 1)):
            errors.append(f"{unit_id} attempts must be contiguous from 1")
        if len(ordered) > 2:
            errors.append(f"{unit_id} exceeds the two-Agent-attempt recovery bound")

        if team_plans:
            prior_revision: int | None = None
            for item in ordered:
                revision = item.get("team_plan_revision")
                if not valid_int(revision, minimum=1) or revision not in units_by_revision:
                    continue
                if prior_revision is not None and revision < prior_revision:
                    errors.append(f"{unit_id} attempt TeamPlan revisions must not move backward")
                    break
                prior_revision = revision

        if len(ordered) >= 2:
            first = ordered[0]
            if first.get("control_state") == "UNKNOWN":
                errors.append(f"{unit_id} UNKNOWN attempt forbids a replacement attempt")
            elif first.get("control_state") != "FAILED":
                errors.append(f"{unit_id} second attempt requires the first attempt to be FAILED")

    if not errors:
        result["status"] = "pass"
        result["ledger_valid"] = True
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate subagents-dispatch TeamPlan and native recovery ledger invariants."
    )
    parser.add_argument("ledger", help="ledger JSON path, or - to read JSON from stdin")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = load_input(args.ledger)
    except (OSError, json.JSONDecodeError) as exc:
        result = {
            "status": "fail",
            "ledger_valid": False,
            "errors": [f"JSON load failed: {exc}"],
            "warnings": [],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    result = validate_team_ledger_payload(payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ledger_valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
