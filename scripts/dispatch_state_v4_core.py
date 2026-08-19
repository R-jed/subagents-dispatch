#!/usr/bin/env python3
"""V4 bounded orchestration state foundation.

This module owns the V4 schema and reconciliation contract used by Orchestrate.
It currently reuses the hardened storage boundary, locking, and atomic replace
helpers from legacy ``dispatch_state``. Legacy V3.x state remains available only
for compatibility diagnostics and explicit migration handling.
"""

from __future__ import annotations

import copy
import json
import os
import re
import stat
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping

import dispatch_state as storage


SCHEMA_VERSION = "4.0"
DEFAULT_MAX_BYTES = 64 * 1024
CANONICAL_WORKSPACE_ID = "canonical"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")

TOP_LEVEL_FIELDS = {
    "schema_version",
    "root_session_id",
    "state_revision",
    "team_plan_revision",
    "work_units",
    "executions",
    "writer_lease",
    "pending_controls",
    "accounting_refs",
    "created_at",
    "updated_at",
    "locale",
}
WORK_UNIT_REQUIRED_FIELDS = {
    "unit_id",
    "intent",
    "goal",
    "output",
    "depends_on",
    "state",
    "ownership",
    "authority_ceiling",
    "write_scope_ceiling",
    "done_when",
    "accepted_result_ref",
    "accepted_execution_id",
    "accepted_control_epoch",
}
WORK_UNIT_FIELDS = WORK_UNIT_REQUIRED_FIELDS | {"responsibility_context"}
RESPONSIBILITY_CONTEXT_FIELDS = {
    "interfaces",
    "invariants",
    "decision_boundary",
    "accepted_evidence_refs",
    "do_not_redo",
    "stop_boundary",
}
EXECUTION_FIELDS = {
    "execution_id",
    "unit_id",
    "team_plan_revision",
    "attempt_no",
    "profile_id",
    "agent_id",
    "native_task_name",
    "model",
    "effort",
    "granted_authority",
    "granted_write_scope",
    "workspace_id",
    "lifecycle",
    "control_epoch",
    "followup_count",
    "failure_origin",
    "blocker",
    "quarantine_reason",
}
WRITER_LEASE_FIELDS = {
    "lease_id",
    "lease_epoch",
    "workspace_id",
    "unit_id",
    "owner_kind",
    "owner_id",
    "state",
}
PENDING_CONTROL_FIELDS = {
    "control_id",
    "unit_id",
    "execution_id",
    "operation",
    "target",
    "payload_digest",
    "expected_team_plan_revision",
    "expected_control_epoch",
    "next_control_epoch",
    "expected_lease_epoch",
    "writer_effect",
    "state",
    "tool_use_id",
}
OWNERSHIP_FIELDS = {"write", "forbidden"}

WORK_UNIT_STATES = {
    "BLOCKED",
    "READY",
    "EXECUTING",
    "RESULT_READY",
    "VERIFYING",
    "ACCEPTED",
    "REJECTED",
    "CANCELLED",
}
EXECUTION_STATES = {
    "SPAWN_PENDING",
    "RUNNING",
    "INTERRUPTED",
    "COMPLETED",
    "FAILED",
    "UNKNOWN",
    "CLOSED",
}
WRITER_LEASE_STATES = {"RESERVED", "HELD", "REVOKING", "UNKNOWN", "RELEASED"}
WRITER_BLOCKING_STATES = {"RESERVED", "HELD", "REVOKING", "UNKNOWN"}
PENDING_CONTROL_STATES = {"PREPARED", "IN_FLIGHT", "ACKED", "UNKNOWN", "CANCELLED"}
UNRESOLVED_CONTROL_STATES = {"PREPARED", "IN_FLIGHT", "UNKNOWN"}
CONTROL_OPERATIONS = {"SPAWN", "FOLLOWUP", "CONTINUE", "INTERRUPT"}
WRITER_EFFECTS = {"NONE", "RESERVE", "RETAIN", "REVOKE"}
WRITER_OWNER_KINDS = {"main", "execution"}
WORK_INTENTS = {"inspect", "implement", "verify", "review"}
MUTATION_AUTHORITIES = {"none", "declared-output-only", "bounded-source-write"}
AUTHORITY_RANK = {"none": 0, "declared-output-only": 1, "bounded-source-write": 2}
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
PROFILE_CONTRACT = {
    "reader": ("gpt-5.6-luna", "max", "none"),
    "worker": ("gpt-5.6-luna", "max", "bounded-source-write"),
    "investigator": ("gpt-5.6-terra", "high", "none"),
    "solver": ("gpt-5.6-sol", "high", "bounded-source-write"),
    "advisor": ("gpt-5.6-sol", "high", "none"),
}
HOST_STATE_MAP = {
    "pending_init": "RUNNING",
    "pendingInit": "RUNNING",
    "running": "RUNNING",
    "interrupted": "INTERRUPTED",
    "completed": "COMPLETED",
    "errored": "FAILED",
    "shutdown": "CLOSED",
}
HOST_UNCERTAIN_STATES = {"not_found", "notFound"}


StateError = storage.StateError
StateIdentityError = storage.StateIdentityError
StatePathError = storage.StatePathError
StatePayloadError = storage.StatePayloadError
StateCorruptError = storage.StateCorruptError
StateLockError = storage.StateLockError


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _strict_int(value: Any, *, minimum: int = 0) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def _require_exact_fields(value: Any, fields: set[str], *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise StatePayloadError(f"{label} must be an object")
    extra = set(value) - fields
    missing = fields - set(value)
    if extra:
        raise StatePayloadError(f"{label} has unsupported fields: {', '.join(sorted(extra))}")
    if missing:
        raise StatePayloadError(f"{label} is missing fields: {', '.join(sorted(missing))}")
    return value


def _require_allowed_fields(
    value: Any,
    required: set[str],
    allowed: set[str],
    *,
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise StatePayloadError(f"{label} must be an object")
    extra = set(value) - allowed
    missing = required - set(value)
    if extra:
        raise StatePayloadError(f"{label} has unsupported fields: {', '.join(sorted(extra))}")
    if missing:
        raise StatePayloadError(f"{label} is missing fields: {', '.join(sorted(missing))}")
    return value


def _validate_string_list(value: Any, *, label: str, unique: bool = True) -> list[str]:
    if not isinstance(value, list) or not all(_nonempty(item) for item in value):
        raise StatePayloadError(f"{label} must be an array of non-empty strings")
    if unique and len(value) != len(set(value)):
        raise StatePayloadError(f"{label} must not contain duplicates")
    return value


def _validate_relative_scope(value: str, *, label: str) -> None:
    if not _nonempty(value):
        raise StatePayloadError(f"{label} must be a non-empty relative path")
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise StatePayloadError(f"{label} must be a safe relative path")


def _validate_scope_list(value: Any, *, label: str) -> list[str]:
    values = _validate_string_list(value, label=label)
    for item in values:
        _validate_relative_scope(item, label=label)
    return values


def _validate_ownership(value: Any, *, label: str) -> dict[str, Any]:
    ownership = _require_exact_fields(value, OWNERSHIP_FIELDS, label=label)
    write = _validate_scope_list(ownership["write"], label=f"{label}.write")
    forbidden = _validate_scope_list(ownership["forbidden"], label=f"{label}.forbidden")
    if set(write) & set(forbidden):
        raise StatePayloadError(f"{label} write and forbidden scopes must not overlap")
    return ownership


def _validate_responsibility_context(value: Any, *, label: str) -> dict[str, Any] | None:
    if value is None:
        return None
    context = _require_exact_fields(value, RESPONSIBILITY_CONTEXT_FIELDS, label=label)
    for field in ("interfaces", "invariants", "accepted_evidence_refs", "do_not_redo"):
        _validate_string_list(context[field], label=f"{label}.{field}")
    for field in ("decision_boundary", "stop_boundary"):
        if not _nonempty(context[field]):
            raise StatePayloadError(f"{label}.{field} must be non-empty text")
    return context


def _validate_work_units(units: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(units, list):
        raise StatePayloadError("work_units must be an array")
    by_id: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(units):
        unit = _require_allowed_fields(
            raw,
            WORK_UNIT_REQUIRED_FIELDS,
            WORK_UNIT_FIELDS,
            label=f"work unit {index}",
        )
        unit_id = unit["unit_id"]
        if not _nonempty(unit_id) or unit_id in by_id:
            raise StatePayloadError(f"work unit {index} has invalid or duplicate unit_id")
        if unit["intent"] not in WORK_INTENTS:
            raise StatePayloadError(f"work unit {unit_id} has invalid intent")
        for field in ("goal", "output", "done_when"):
            if not _nonempty(unit[field]):
                raise StatePayloadError(f"work unit {unit_id} has invalid {field}")
        depends_on = _validate_string_list(unit["depends_on"], label=f"work unit {unit_id}.depends_on")
        if unit_id in depends_on:
            raise StatePayloadError(f"work unit {unit_id} cannot depend on itself")
        if unit["state"] not in WORK_UNIT_STATES:
            raise StatePayloadError(f"work unit {unit_id} has invalid state")
        _validate_responsibility_context(
            unit.get("responsibility_context"),
            label=f"work unit {unit_id}.responsibility_context",
        )
        ownership = _validate_ownership(unit["ownership"], label=f"work unit {unit_id}.ownership")
        authority = unit["authority_ceiling"]
        if authority not in MUTATION_AUTHORITIES:
            raise StatePayloadError(f"work unit {unit_id} has invalid authority_ceiling")
        ceiling = _validate_scope_list(
            unit["write_scope_ceiling"], label=f"work unit {unit_id}.write_scope_ceiling"
        )
        if not set(ceiling).issubset(set(ownership["write"])):
            raise StatePayloadError(
                f"work unit {unit_id} write_scope_ceiling must be inside ownership.write"
            )
        if authority == "none" and ceiling:
            raise StatePayloadError(f"work unit {unit_id} authority none requires empty write scope")
        accepted = unit["state"] == "ACCEPTED"
        accepted_fields = (
            unit["accepted_result_ref"],
            unit["accepted_execution_id"],
            unit["accepted_control_epoch"],
        )
        if accepted:
            if not _nonempty(accepted_fields[0]) or not _nonempty(accepted_fields[1]):
                raise StatePayloadError(f"accepted work unit {unit_id} requires accepted result and execution")
            if not _strict_int(accepted_fields[2]):
                raise StatePayloadError(f"accepted work unit {unit_id} requires accepted_control_epoch")
        elif any(value is not None for value in accepted_fields):
            raise StatePayloadError(f"work unit {unit_id} cannot carry accepted refs before ACCEPTED")
        by_id[unit_id] = unit

    for unit_id, unit in by_id.items():
        missing = [dependency for dependency in unit["depends_on"] if dependency not in by_id]
        if missing:
            raise StatePayloadError(f"work unit {unit_id} depends on unknown unit {missing[0]}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(unit_id: str) -> None:
        if unit_id in visited:
            return
        if unit_id in visiting:
            raise StatePayloadError("work_units dependency graph must be acyclic")
        visiting.add(unit_id)
        for dependency in by_id[unit_id]["depends_on"]:
            visit(dependency)
        visiting.remove(unit_id)
        visited.add(unit_id)

    for unit_id in by_id:
        visit(unit_id)
    return by_id


def _validate_executions(
    executions: Any,
    *,
    work_units: Mapping[str, Mapping[str, Any]],
    active_team_plan_revision: int | None,
) -> dict[str, dict[str, Any]]:
    if not isinstance(executions, list):
        raise StatePayloadError("executions must be an array")
    by_id: dict[str, dict[str, Any]] = {}
    native_names: set[str] = set()
    agent_ids: set[str] = set()
    attempts_by_unit: dict[str, list[int]] = {}
    for index, raw in enumerate(executions):
        execution = _require_exact_fields(raw, EXECUTION_FIELDS, label=f"execution {index}")
        execution_id = execution["execution_id"]
        unit_id = execution["unit_id"]
        if not _nonempty(execution_id) or execution_id in by_id:
            raise StatePayloadError(f"execution {index} has invalid or duplicate execution_id")
        if unit_id not in work_units:
            raise StatePayloadError(f"execution {execution_id} references unknown work unit")
        revision = execution["team_plan_revision"]
        if revision is not None and not _strict_int(revision, minimum=1):
            raise StatePayloadError(f"execution {execution_id} has invalid team_plan_revision")
        if active_team_plan_revision is None and revision is not None:
            raise StatePayloadError(f"execution {execution_id} cannot bind a TeamPlan revision without TeamPlan")
        if active_team_plan_revision is not None and revision is None:
            raise StatePayloadError(f"execution {execution_id} requires team_plan_revision")
        if active_team_plan_revision is not None and revision > active_team_plan_revision:
            raise StatePayloadError(f"execution {execution_id} references a future TeamPlan revision")
        attempt = execution["attempt_no"]
        if not _strict_int(attempt, minimum=1) or attempt > 2:
            raise StatePayloadError(f"execution {execution_id} attempt_no must be 1 or 2")
        attempts_by_unit.setdefault(unit_id, []).append(attempt)
        profile = execution["profile_id"]
        if profile not in PROFILE_CONTRACT:
            raise StatePayloadError(f"execution {execution_id} has invalid profile_id")
        model, effort, profile_authority = PROFILE_CONTRACT[profile]
        if execution["model"] != model or execution["effort"] != effort:
            raise StatePayloadError(f"execution {execution_id} model/effort drift from fixed profile")
        if not _nonempty(execution["native_task_name"]) or execution["native_task_name"] in native_names:
            raise StatePayloadError(f"execution {execution_id} has invalid or duplicate native_task_name")
        native_names.add(execution["native_task_name"])
        lifecycle = execution["lifecycle"]
        if lifecycle not in EXECUTION_STATES:
            raise StatePayloadError(f"execution {execution_id} has invalid lifecycle")
        agent_id = execution["agent_id"]
        if agent_id is not None and not _nonempty(agent_id):
            raise StatePayloadError(f"execution {execution_id} has invalid agent_id")
        if isinstance(agent_id, str):
            if agent_id in agent_ids:
                raise StatePayloadError(f"execution {execution_id} duplicates agent_id")
            agent_ids.add(agent_id)
        granted = execution["granted_authority"]
        if granted not in MUTATION_AUTHORITIES:
            raise StatePayloadError(f"execution {execution_id} has invalid granted_authority")
        if AUTHORITY_RANK[granted] > AUTHORITY_RANK[work_units[unit_id]["authority_ceiling"]]:
            raise StatePayloadError(f"execution {execution_id} exceeds WorkUnit authority ceiling")
        if AUTHORITY_RANK[granted] > AUTHORITY_RANK[profile_authority]:
            raise StatePayloadError(f"execution {execution_id} exceeds profile mutation authority")
        granted_scope = _validate_scope_list(
            execution["granted_write_scope"], label=f"execution {execution_id}.granted_write_scope"
        )
        if not set(granted_scope).issubset(set(work_units[unit_id]["write_scope_ceiling"])):
            raise StatePayloadError(f"execution {execution_id} exceeds WorkUnit write scope ceiling")
        if granted == "none" and granted_scope:
            raise StatePayloadError(f"execution {execution_id} authority none requires empty write scope")
        if execution["workspace_id"] != CANONICAL_WORKSPACE_ID:
            raise StatePayloadError(f"execution {execution_id} must use canonical workspace in V4.0.0")
        if not _strict_int(execution["control_epoch"]):
            raise StatePayloadError(f"execution {execution_id} has invalid control_epoch")
        if not _strict_int(execution["followup_count"]) or execution["followup_count"] > 1:
            raise StatePayloadError(f"execution {execution_id} followup_count must be 0 or 1")
        if execution["failure_origin"] not in FAILURE_ORIGINS:
            raise StatePayloadError(f"execution {execution_id} has invalid failure_origin")
        if execution["blocker"] not in TASK_BLOCKERS:
            raise StatePayloadError(f"execution {execution_id} has invalid blocker")
        if lifecycle == "UNKNOWN":
            if execution["failure_origin"] != "runtime_ambiguous":
                raise StatePayloadError(f"execution {execution_id} UNKNOWN requires runtime_ambiguous")
        elif execution["failure_origin"] == "runtime_ambiguous":
            raise StatePayloadError(f"execution {execution_id} runtime_ambiguous requires UNKNOWN")
        if lifecycle == "FAILED" and execution["failure_origin"] == "none":
            raise StatePayloadError(f"execution {execution_id} FAILED requires failure_origin")
        if lifecycle not in {"FAILED", "UNKNOWN"} and execution["failure_origin"] != "none":
            raise StatePayloadError(f"execution {execution_id} non-failure state requires failure_origin=none")
        if lifecycle not in {"FAILED", "UNKNOWN"} and execution["blocker"] != "none":
            raise StatePayloadError(f"execution {execution_id} blocker belongs only on FAILED or UNKNOWN")
        quarantine = execution["quarantine_reason"]
        if quarantine is not None and not _nonempty(quarantine):
            raise StatePayloadError(f"execution {execution_id} has invalid quarantine_reason")
        if lifecycle != "UNKNOWN" and quarantine is not None:
            raise StatePayloadError(f"execution {execution_id} quarantine_reason requires UNKNOWN")
        by_id[execution_id] = execution

    for unit_id, attempts in attempts_by_unit.items():
        ordered = sorted(attempts)
        if ordered != list(range(1, len(ordered) + 1)) or len(ordered) != len(set(ordered)):
            raise StatePayloadError(f"work unit {unit_id} execution attempts must be contiguous from 1")
    return by_id


def _validate_writer_lease(
    value: Any,
    *,
    root_session_id: str,
    work_units: Mapping[str, Mapping[str, Any]],
    executions: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any] | None:
    if value is None:
        return None
    lease = _require_exact_fields(value, WRITER_LEASE_FIELDS, label="writer_lease")
    if not _nonempty(lease["lease_id"]):
        raise StatePayloadError("writer_lease requires lease_id")
    if not _strict_int(lease["lease_epoch"], minimum=1):
        raise StatePayloadError("writer_lease requires positive lease_epoch")
    if lease["workspace_id"] != CANONICAL_WORKSPACE_ID:
        raise StatePayloadError("writer_lease must use canonical workspace in V4.0.0")
    if lease["unit_id"] not in work_units:
        raise StatePayloadError("writer_lease must reference an existing WorkUnit")
    if lease["owner_kind"] not in WRITER_OWNER_KINDS:
        raise StatePayloadError("writer_lease has invalid owner_kind")
    if lease["state"] not in WRITER_LEASE_STATES:
        raise StatePayloadError("writer_lease has invalid state")
    owner_id = lease["owner_id"]
    if lease["owner_kind"] == "main":
        if owner_id != root_session_id:
            raise StatePayloadError("main writer lease owner_id must be root_session_id")
    else:
        execution = executions.get(owner_id)
        if execution is None or execution["unit_id"] != lease["unit_id"]:
            raise StatePayloadError("execution writer lease must reference matching ExecutionBinding")
        if execution["granted_authority"] == "none":
            raise StatePayloadError("read-only ExecutionBinding cannot own WriterLease")
    return lease


def _validate_pending_controls(
    value: Any,
    *,
    work_units: Mapping[str, Mapping[str, Any]],
    executions: Mapping[str, Mapping[str, Any]],
    active_team_plan_revision: int | None,
    lease: Mapping[str, Any] | None,
) -> None:
    if not isinstance(value, list):
        raise StatePayloadError("pending_controls must be an array")
    control_ids: set[str] = set()
    tool_use_ids: set[str] = set()
    unresolved_by_execution: set[str] = set()
    for index, raw in enumerate(value):
        control = _require_exact_fields(raw, PENDING_CONTROL_FIELDS, label=f"pending control {index}")
        control_id = control["control_id"]
        execution_id = control["execution_id"]
        unit_id = control["unit_id"]
        if not _nonempty(control_id) or control_id in control_ids:
            raise StatePayloadError(f"pending control {index} has invalid or duplicate control_id")
        control_ids.add(control_id)
        execution = executions.get(execution_id)
        if execution is None or unit_id not in work_units or execution["unit_id"] != unit_id:
            raise StatePayloadError(f"pending control {control_id} has invalid execution/unit binding")
        if control["operation"] not in CONTROL_OPERATIONS:
            raise StatePayloadError(f"pending control {control_id} has invalid operation")
        if control["target"] != execution["native_task_name"]:
            raise StatePayloadError(f"pending control {control_id} target must match native_task_name")
        digest = control["payload_digest"]
        if not isinstance(digest, str) or HEX64.fullmatch(digest) is None:
            raise StatePayloadError(f"pending control {control_id} has invalid payload_digest")
        revision = control["expected_team_plan_revision"]
        if revision != active_team_plan_revision:
            raise StatePayloadError(f"pending control {control_id} uses stale TeamPlan revision")
        expected_epoch = control["expected_control_epoch"]
        next_epoch = control["next_control_epoch"]
        if not _strict_int(expected_epoch) or not _strict_int(next_epoch):
            raise StatePayloadError(f"pending control {control_id} has invalid control epoch")
        if expected_epoch != execution["control_epoch"]:
            raise StatePayloadError(f"pending control {control_id} uses stale control_epoch")
        expected_next = expected_epoch if control["operation"] == "SPAWN" else expected_epoch + 1
        if next_epoch != expected_next:
            raise StatePayloadError(f"pending control {control_id} has invalid next_control_epoch")
        lease_epoch = control["expected_lease_epoch"]
        if lease_epoch is not None and not _strict_int(lease_epoch, minimum=1):
            raise StatePayloadError(f"pending control {control_id} has invalid expected_lease_epoch")
        if lease_epoch is not None and (lease is None or lease_epoch != lease["lease_epoch"]):
            raise StatePayloadError(f"pending control {control_id} uses stale lease_epoch")
        if control["writer_effect"] not in WRITER_EFFECTS:
            raise StatePayloadError(f"pending control {control_id} has invalid writer_effect")
        if control["state"] not in PENDING_CONTROL_STATES:
            raise StatePayloadError(f"pending control {control_id} has invalid state")
        tool_use_id = control["tool_use_id"]
        if control["state"] == "PREPARED":
            if tool_use_id is not None:
                raise StatePayloadError(f"pending control {control_id} PREPARED cannot bind tool_use_id")
        elif control["state"] in {"IN_FLIGHT", "ACKED"}:
            if not _nonempty(tool_use_id):
                raise StatePayloadError(f"pending control {control_id} requires tool_use_id")
        elif tool_use_id is not None and not _nonempty(tool_use_id):
            raise StatePayloadError(f"pending control {control_id} has invalid tool_use_id")
        if isinstance(tool_use_id, str):
            if tool_use_id in tool_use_ids:
                raise StatePayloadError(f"pending control {control_id} duplicates tool_use_id")
            tool_use_ids.add(tool_use_id)
        if control["state"] in UNRESOLVED_CONTROL_STATES:
            if execution_id in unresolved_by_execution:
                raise StatePayloadError(f"execution {execution_id} has multiple unresolved controls")
            unresolved_by_execution.add(execution_id)


def _validate_acceptance_bindings(
    work_units: Mapping[str, Mapping[str, Any]], executions: Mapping[str, Mapping[str, Any]]
) -> None:
    for unit_id, unit in work_units.items():
        if unit["state"] != "ACCEPTED":
            continue
        execution = executions.get(unit["accepted_execution_id"])
        if execution is None or execution["unit_id"] != unit_id:
            raise StatePayloadError(f"accepted work unit {unit_id} references invalid execution")
        if unit["accepted_control_epoch"] > execution["control_epoch"]:
            raise StatePayloadError(f"accepted work unit {unit_id} references future control epoch")


def _validate_accounting_refs(value: Any) -> None:
    if not isinstance(value, list):
        raise StatePayloadError("accounting_refs must be an array")
    refs: set[str] = set()
    for index, event in enumerate(value):
        if not isinstance(event, dict) or not _nonempty(event.get("ref")):
            raise StatePayloadError(f"accounting_refs[{index}] requires stable ref")
        ref = event["ref"]
        if ref in refs:
            raise StatePayloadError("accounting_refs must contain unique stable refs")
        refs.add(ref)


def _serialized_payload(payload: Mapping[str, Any], *, max_bytes: int) -> bytes:
    try:
        encoded = json.dumps(
            payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise StatePayloadError(f"state must be JSON serializable: {exc}") from exc
    if len(encoded) > max_bytes:
        raise StatePayloadError(f"state exceeds {max_bytes} bytes")
    return encoded


def validate_state_payload(
    payload: Any,
    *,
    thread_id: str | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> dict[str, Any]:
    state = _require_exact_fields(payload, TOP_LEVEL_FIELDS, label="V4 state")
    _serialized_payload(state, max_bytes=max_bytes)
    storage._reject_forbidden_persisted_fields(state)
    if state["schema_version"] != SCHEMA_VERSION:
        raise StatePayloadError("unsupported V4 state schema_version")
    identity = storage.resolve_thread_id(thread_id if thread_id is not None else state["root_session_id"])
    if state["root_session_id"] != identity:
        raise StatePayloadError("root_session_id does not match CODEX_THREAD_ID")
    if state["locale"] not in {"zh", "en"}:
        raise StatePayloadError("locale must be zh or en")
    if not _strict_int(state["state_revision"]):
        raise StatePayloadError("state_revision must be a non-negative integer")
    revision = state["team_plan_revision"]
    if revision is not None and not _strict_int(revision, minimum=1):
        raise StatePayloadError("team_plan_revision must be null or a positive integer")
    work_units = _validate_work_units(state["work_units"])
    executions = _validate_executions(
        state["executions"], work_units=work_units, active_team_plan_revision=revision
    )
    _validate_acceptance_bindings(work_units, executions)
    lease = _validate_writer_lease(
        state["writer_lease"],
        root_session_id=identity,
        work_units=work_units,
        executions=executions,
    )
    _validate_pending_controls(
        state["pending_controls"],
        work_units=work_units,
        executions=executions,
        active_team_plan_revision=revision,
        lease=lease,
    )
    _validate_accounting_refs(state["accounting_refs"])
    for field in ("created_at", "updated_at"):
        try:
            storage._parse_timestamp(state[field])
        except (TypeError, ValueError) as exc:
            raise StatePayloadError(f"{field} must be an ISO-8601 timestamp") from exc
    return state


def new_state(
    *,
    thread_id: str | None = None,
    locale: str = "en",
    now: datetime | str | None = None,
) -> dict[str, Any]:
    identity = storage.resolve_thread_id(thread_id)
    if locale not in {"zh", "en"}:
        raise StatePayloadError("locale must be zh or en")
    timestamp = storage._utc_text(now)
    state = {
        "schema_version": SCHEMA_VERSION,
        "root_session_id": identity,
        "state_revision": 0,
        "team_plan_revision": None,
        "work_units": [],
        "executions": [],
        "writer_lease": None,
        "pending_controls": [],
        "accounting_refs": [],
        "created_at": timestamp,
        "updated_at": timestamp,
        "locale": locale,
    }
    validate_state_payload(state, thread_id=identity)
    return state


def state_path(
    thread_id: str | None = None, *, temp_root: str | os.PathLike[str] | None = None
) -> Path:
    return storage.state_path(thread_id, temp_root=temp_root)


def write_state(
    payload: Mapping[str, Any],
    *,
    thread_id: str | None = None,
    temp_root: str | os.PathLike[str] | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> Path:
    identity = storage.resolve_thread_id(
        thread_id if thread_id is not None else payload.get("root_session_id")
    )
    validate_state_payload(dict(payload), thread_id=identity, max_bytes=max_bytes)
    encoded = _serialized_payload(payload, max_bytes=max_bytes)
    with storage.state_lock(identity, temp_root=temp_root):
        _, _, path, _ = storage._paths(identity, temp_root, create=True)
        storage._write_unlocked(path, encoded)
    return path


def load_state(
    thread_id: str | None = None,
    *,
    temp_root: str | os.PathLike[str] | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> dict[str, Any] | None:
    identity, _, path, _ = storage._paths(thread_id, temp_root, create=False)
    if not path.exists():
        return None
    mode = path.lstat().st_mode
    if not stat.S_ISREG(mode):
        raise StateCorruptError("state file must be a regular file")
    if os.name != "nt" and mode & 0o077:
        raise StateCorruptError("state file must be private")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise StateCorruptError(f"cannot read state: {exc}") from exc
    if len(raw) > max_bytes:
        raise StateCorruptError(f"state exceeds {max_bytes} bytes")
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StateCorruptError(f"state contains invalid JSON: {exc}") from exc
    try:
        validate_state_payload(payload, thread_id=identity, max_bytes=max_bytes)
    except (StateIdentityError, StatePayloadError) as exc:
        raise StateCorruptError(str(exc)) from exc
    return payload


def mutate_state(
    thread_id: str | None,
    mutator: Callable[[dict[str, Any]], None],
    *,
    expected_state_revision: int | None = None,
    temp_root: str | os.PathLike[str] | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
    now: datetime | str | None = None,
) -> dict[str, Any]:
    """Atomically mutate V4 state with optional state-revision compare-and-swap."""
    identity = storage.resolve_thread_id(thread_id)
    with storage.state_lock(identity, temp_root=temp_root):
        current = load_state(identity, temp_root=temp_root, max_bytes=max_bytes)
        if current is None:
            raise StatePayloadError("active V4 state is unavailable")
        if expected_state_revision is not None and current["state_revision"] != expected_state_revision:
            raise StatePayloadError("state_revision compare-and-swap failed")
        updated = copy.deepcopy(current)
        mutator(updated)
        updated["state_revision"] = current["state_revision"] + 1
        updated["updated_at"] = storage._utc_text(now)
        validate_state_payload(updated, thread_id=identity, max_bytes=max_bytes)
        encoded = _serialized_payload(updated, max_bytes=max_bytes)
        _, _, path, _ = storage._paths(identity, temp_root, create=True)
        storage._write_unlocked(path, encoded)
        return updated


def observation_basis(payload: Mapping[str, Any], *, execution_id: str) -> dict[str, Any]:
    state = validate_state_payload(copy.deepcopy(dict(payload)))
    matches = [item for item in state["executions"] if item["execution_id"] == execution_id]
    if len(matches) != 1:
        raise StatePayloadError("observation execution_id does not resolve exactly")
    execution = matches[0]
    lease_epoch = state["writer_lease"]["lease_epoch"] if state["writer_lease"] is not None else None
    return {
        "execution_id": execution_id,
        "control_epoch": execution["control_epoch"],
        "lease_epoch": lease_epoch,
    }


def _basis_is_current(state: Mapping[str, Any], basis: Mapping[str, Any]) -> bool:
    if not isinstance(basis, Mapping):
        return False
    execution_id = basis.get("execution_id")
    matches = [item for item in state["executions"] if item["execution_id"] == execution_id]
    if len(matches) != 1:
        return False
    execution = matches[0]
    if basis.get("control_epoch") != execution["control_epoch"]:
        return False
    current_lease_epoch = (
        state["writer_lease"]["lease_epoch"] if state["writer_lease"] is not None else None
    )
    return basis.get("lease_epoch") == current_lease_epoch


def reconcile_execution_observation(
    payload: Mapping[str, Any],
    *,
    basis: Mapping[str, Any],
    host_state: str,
    agent_id: str | None = None,
    failure_origin: str = "tool_failure",
    now: datetime | str | None = None,
) -> dict[str, Any]:
    """Apply one normalized Host snapshot when its captured basis is current.

    ``native_task_name`` is the required V2 execution identity. ``agent_id`` is
    optional reinforcing evidence because V2 spawn/list tools do not guarantee a
    thread id. A stale observation is discarded. Reconciliation never releases
    WriterLease and never marks WorkUnit ACCEPTED.
    """
    state = copy.deepcopy(dict(payload))
    validate_state_payload(state)
    if not _basis_is_current(state, basis):
        return {"reconcile_status": "stale", "state": state}
    before = copy.deepcopy(state)
    execution = next(
        item for item in state["executions"] if item["execution_id"] == basis["execution_id"]
    )
    if host_state in HOST_UNCERTAIN_STATES:
        execution["lifecycle"] = "UNKNOWN"
        execution["failure_origin"] = "runtime_ambiguous"
        execution["blocker"] = "investigation"
        execution["quarantine_reason"] = "native_identity_not_found"
    elif host_state not in HOST_STATE_MAP:
        execution["lifecycle"] = "UNKNOWN"
        execution["failure_origin"] = "runtime_ambiguous"
        execution["blocker"] = "investigation"
        execution["quarantine_reason"] = "invalid_native_observation"
    else:
        mapped = HOST_STATE_MAP[host_state]
        if agent_id is not None:
            if not _nonempty(agent_id):
                raise StatePayloadError("Host observation agent_id must be non-empty")
            if execution["agent_id"] is not None and execution["agent_id"] != agent_id:
                execution["lifecycle"] = "UNKNOWN"
                execution["failure_origin"] = "runtime_ambiguous"
                execution["blocker"] = "investigation"
                execution["quarantine_reason"] = "native_identity_conflict"
                mapped = "UNKNOWN"
            else:
                execution["agent_id"] = agent_id
        if mapped != "UNKNOWN":
            execution["lifecycle"] = mapped
            execution["quarantine_reason"] = None
            if mapped == "FAILED":
                execution["failure_origin"] = (
                    failure_origin
                    if failure_origin in FAILURE_ORIGINS - {"none", "runtime_ambiguous"}
                    else "tool_failure"
                )
                execution["blocker"] = "none"
            else:
                execution["failure_origin"] = "none"
                execution["blocker"] = "none"
            if mapped == "COMPLETED":
                work_unit = next(
                    unit for unit in state["work_units"] if unit["unit_id"] == execution["unit_id"]
                )
                if work_unit["state"] == "EXECUTING":
                    work_unit["state"] = "RESULT_READY"
    if state == before:
        return {"reconcile_status": "noop", "state": state}
    state["state_revision"] += 1
    state["updated_at"] = storage._utc_text(now)
    validate_state_payload(state)
    return {"reconcile_status": "applied", "state": state}
