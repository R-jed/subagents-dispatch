#!/usr/bin/env python3
"""V4 Native Core orchestration state and Host reconciliation.

Schema-neutral private storage lives in ``state_storage``. This module owns only
V4 orchestration schema and Host lifecycle reconciliation; it has no dependency
on the retired V3 orchestration engine.
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

import policy as policy_contract
import state_storage as storage


SCHEMA_VERSION = "4.0"
DEFAULT_MAX_BYTES = 64 * 1024
CANONICAL_WORKSPACE_ID = "canonical"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
HOST_AGENT_NAME_PATTERN = re.compile(r"[a-z0-9_]+\Z")
HOST_RESERVED_AGENT_NAMES = {"root", ".", ".."}

TOP_LEVEL_FIELDS = {
    "schema_version",
    "root_session_id",
    "state_revision",
    "team_plan_revision",
    "work_units",
    "executions",
    "writer_lease",
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
EXECUTION_REQUIRED_FIELDS = {
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
EXECUTION_FIELDS = EXECUTION_REQUIRED_FIELDS | {"execution_basis_ref"}
WRITER_LEASE_FIELDS = {
    "lease_id",
    "lease_epoch",
    "workspace_id",
    "unit_id",
    "owner_kind",
    "owner_id",
    "state",
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
PROFILE_CONTRACT = policy_contract.profile_contract_tuples()
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


def _validate_string_list(value: Any, *, label: str) -> list[str]:
    if not isinstance(value, list) or not all(_nonempty(item) for item in value):
        raise StatePayloadError(f"{label} must be an array of non-empty strings")
    if len(value) != len(set(value)):
        raise StatePayloadError(f"{label} must not contain duplicates")
    return value


def _canonical_scope(value: str, *, label: str) -> str:
    if not _nonempty(value):
        raise StatePayloadError(f"{label} must be a non-empty relative path")
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise StatePayloadError(f"{label} must be a safe relative path")
    canonical = path.as_posix()
    if canonical != value:
        raise StatePayloadError(f"{label} must use canonical repository-relative POSIX form")
    return canonical


def _validate_scope_list(value: Any, *, label: str) -> list[str]:
    values = _validate_string_list(value, label=label)
    for item in values:
        _canonical_scope(item, label=label)
    return values


def _scope_overlaps(left: str, right: str) -> bool:
    left_parts = PurePosixPath(left).parts
    right_parts = PurePosixPath(right).parts
    shortest = min(len(left_parts), len(right_parts))
    return left_parts[:shortest] == right_parts[:shortest]


def _validate_ownership(value: Any, *, label: str) -> dict[str, Any]:
    ownership = _require_exact_fields(value, OWNERSHIP_FIELDS, label=label)
    write = _validate_scope_list(ownership["write"], label=f"{label}.write")
    forbidden = _validate_scope_list(ownership["forbidden"], label=f"{label}.forbidden")
    if any(_scope_overlaps(writable, denied) for writable in write for denied in forbidden):
        raise StatePayloadError(f"{label} write and forbidden scopes overlap by ancestry")
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


def validate_native_task_name(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value in HOST_RESERVED_AGENT_NAMES
        or HOST_AGENT_NAME_PATTERN.fullmatch(value) is None
    ):
        raise StatePayloadError(
            "native_task_name must match Host agent name grammar: lowercase letters, digits, underscores"
        )
    return value


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
) -> dict[str, dict[str, Any]]:
    if not isinstance(executions, list):
        raise StatePayloadError("executions must be an array")
    by_id: dict[str, dict[str, Any]] = {}
    native_names: set[str] = set()
    agent_ids: set[str] = set()
    attempts_by_unit: dict[str, list[int]] = {}
    for index, raw in enumerate(executions):
        execution = _require_allowed_fields(
            raw,
            EXECUTION_REQUIRED_FIELDS,
            EXECUTION_FIELDS,
            label=f"execution {index}",
        )
        execution_id = execution["execution_id"]
        unit_id = execution["unit_id"]
        if not _nonempty(execution_id) or execution_id in by_id:
            raise StatePayloadError(f"execution {index} has invalid or duplicate execution_id")
        if unit_id not in work_units:
            raise StatePayloadError(f"execution {execution_id} references unknown work unit")
        basis_ref = execution.get("execution_basis_ref")
        if basis_ref is not None and not _nonempty(basis_ref):
            raise StatePayloadError(f"execution {execution_id} has invalid execution_basis_ref")
        revision = execution["team_plan_revision"]
        if revision is not None and not _strict_int(revision, minimum=1):
            raise StatePayloadError(f"execution {execution_id} has invalid compatibility revision")
        attempt = execution["attempt_no"]
        if not _strict_int(attempt, minimum=1):
            raise StatePayloadError(f"execution {execution_id} attempt_no must be positive")
        attempts_by_unit.setdefault(unit_id, []).append(attempt)
        profile = execution["profile_id"]
        if profile not in PROFILE_CONTRACT:
            raise StatePayloadError(f"execution {execution_id} has invalid profile_id")
        model, effort, profile_authority = PROFILE_CONTRACT[profile]
        if execution["model"] != model or execution["effort"] != effort:
            raise StatePayloadError(f"execution {execution_id} model/effort drift from fixed profile")
        task_name = validate_native_task_name(execution["native_task_name"])
        if task_name in native_names:
            raise StatePayloadError(f"execution {execution_id} duplicates native_task_name")
        native_names.add(task_name)
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
        if not _strict_int(execution["followup_count"]):
            raise StatePayloadError(f"execution {execution_id} has invalid followup_count")
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
        if len(attempts) != len(set(attempts)) or attempts != sorted(attempts):
            raise StatePayloadError(f"work unit {unit_id} execution attempts must be unique and increasing")
    return by_id


def current_execution_for_unit(
    payload: Mapping[str, Any], *, unit_id: str
) -> Mapping[str, Any] | None:
    executions = [
        item
        for item in payload.get("executions", [])
        if isinstance(item, Mapping) and item.get("unit_id") == unit_id
    ]
    if not executions:
        return None
    greatest = max(item.get("attempt_no", 0) for item in executions)
    matches = [item for item in executions if item.get("attempt_no") == greatest]
    if len(matches) != 1:
        raise StatePayloadError(f"work unit {unit_id} current execution is ambiguous")
    return matches[0]


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


def _has_completed_observation(
    state: Mapping[str, Any], *, execution_id: str, control_epoch: int
) -> bool:
    return any(
        isinstance(event, Mapping)
        and event.get("kind") == "host_observation"
        and event.get("execution_id") == execution_id
        and event.get("control_epoch") == control_epoch
        and event.get("lifecycle") == "COMPLETED"
        for event in state.get("accounting_refs", [])
    )


def _validate_acceptance_truth(
    state: Mapping[str, Any],
    work_units: Mapping[str, Mapping[str, Any]],
    executions: Mapping[str, Mapping[str, Any]],
) -> None:
    for unit_id, unit in work_units.items():
        if unit["state"] != "ACCEPTED":
            continue
        producer = current_execution_for_unit(state, unit_id=unit_id)
        if producer is None:
            raise StatePayloadError(f"accepted work unit {unit_id} requires a producing execution")
        if unit["accepted_execution_id"] != producer["execution_id"]:
            raise StatePayloadError(f"accepted work unit {unit_id} must reference current execution")
        if unit["accepted_control_epoch"] != producer["control_epoch"]:
            raise StatePayloadError(f"accepted work unit {unit_id} control epoch must match current producer")
        if producer["lifecycle"] == "COMPLETED":
            continue
        if producer["lifecycle"] == "CLOSED" and _has_completed_observation(
            state,
            execution_id=str(producer["execution_id"]),
            control_epoch=int(producer["control_epoch"]),
        ):
            continue
        raise StatePayloadError(
            f"accepted work unit {unit_id} producer must be COMPLETED or proven CLOSED"
        )


def _validate_accounting_refs(value: Any, executions: Mapping[str, Mapping[str, Any]]) -> None:
    if not isinstance(value, list):
        raise StatePayloadError("accounting_refs must be an array")
    refs: set[str] = set()
    history_units: set[str] = set()
    for index, event in enumerate(value):
        if not isinstance(event, dict) or not _nonempty(event.get("ref")):
            raise StatePayloadError(f"accounting_refs[{index}] requires stable ref")
        ref = event["ref"]
        if ref in refs:
            raise StatePayloadError("accounting_refs must contain unique stable refs")
        refs.add(ref)
        kind = event.get("kind")
        if kind == "host_observation":
            required = {
                "ref",
                "kind",
                "execution_id",
                "control_epoch",
                "lease_epoch",
                "lifecycle",
            }
            if set(event) != required:
                raise StatePayloadError("host_observation accounting ref has invalid fields")
            execution = executions.get(event["execution_id"])
            if execution is None:
                raise StatePayloadError("host_observation references unknown execution")
            if not _strict_int(event["control_epoch"]):
                raise StatePayloadError("host_observation has invalid control_epoch")
            if event["lease_epoch"] is not None and not _strict_int(event["lease_epoch"], minimum=1):
                raise StatePayloadError("host_observation has invalid lease_epoch")
            if event["lifecycle"] not in EXECUTION_STATES:
                raise StatePayloadError("host_observation has invalid lifecycle")
        elif kind == "execution_history":
            required = {
                "ref",
                "kind",
                "unit_id",
                "compacted_attempts",
                "max_attempt_no",
                "last_execution_id",
                "last_lifecycle",
                "last_basis_ref",
                "last_followup_count",
            }
            if set(event) != required:
                raise StatePayloadError("execution_history accounting ref has invalid fields")
            unit_id = event["unit_id"]
            if not _nonempty(unit_id) or unit_id in history_units:
                raise StatePayloadError("execution_history requires one unique record per WorkUnit")
            history_units.add(unit_id)
            if not _strict_int(event["compacted_attempts"], minimum=1):
                raise StatePayloadError("execution_history compacted_attempts must be positive")
            if not _strict_int(event["max_attempt_no"], minimum=1):
                raise StatePayloadError("execution_history max_attempt_no must be positive")
            if event["max_attempt_no"] < event["compacted_attempts"]:
                raise StatePayloadError("execution_history max_attempt_no is inconsistent")
            if not _nonempty(event["last_execution_id"]):
                raise StatePayloadError("execution_history requires last_execution_id")
            if event["last_lifecycle"] not in {"COMPLETED", "FAILED", "CLOSED"}:
                raise StatePayloadError("execution_history requires settled last_lifecycle")
            if event["last_basis_ref"] is not None and not _nonempty(event["last_basis_ref"]):
                raise StatePayloadError("execution_history last_basis_ref must be null or non-empty")
            if not _strict_int(event["last_followup_count"]):
                raise StatePayloadError("execution_history last_followup_count must be non-negative")
        elif kind == "recovery_basis":
            required = {
                "ref",
                "kind",
                "execution_id",
                "action",
                "basis_hash",
                "control_epoch",
            }
            if set(event) != required:
                raise StatePayloadError("recovery_basis accounting ref has invalid fields")
            if event["execution_id"] not in executions:
                raise StatePayloadError("recovery_basis references unknown execution")
            if event["action"] != "FOLLOWUP":
                raise StatePayloadError("recovery_basis action is unsupported")
            if not isinstance(event["basis_hash"], str) or HEX64.fullmatch(event["basis_hash"]) is None:
                raise StatePayloadError("recovery_basis basis_hash must be sha256 hex")
            if not _strict_int(event["control_epoch"], minimum=1):
                raise StatePayloadError("recovery_basis control_epoch must be positive")


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
    identity = storage.resolve_thread_id(
        thread_id if thread_id is not None else state["root_session_id"]
    )
    if state["root_session_id"] != identity:
        raise StatePayloadError("root_session_id does not match active orchestration identity")
    if state["locale"] not in {"zh", "en"}:
        raise StatePayloadError("locale must be zh or en")
    if not _strict_int(state["state_revision"]):
        raise StatePayloadError("state_revision must be a non-negative integer")
    revision = state["team_plan_revision"]
    if revision is not None and not _strict_int(revision, minimum=1):
        raise StatePayloadError("team_plan_revision compatibility marker must be null or positive")
    work_units = _validate_work_units(state["work_units"])
    executions = _validate_executions(state["executions"], work_units=work_units)
    _validate_writer_lease(
        state["writer_lease"],
        root_session_id=identity,
        work_units=work_units,
        executions=executions,
    )
    _validate_accounting_refs(state["accounting_refs"], executions)
    _validate_acceptance_truth(state, work_units, executions)
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


def _execution_writer_lease_epoch(
    current: Mapping[str, Any], execution: Mapping[str, Any]
) -> int | None:
    if execution.get("granted_authority") == "none":
        return None
    lease = current.get("writer_lease")
    if not isinstance(lease, Mapping):
        return None
    if (
        lease.get("owner_kind") != "execution"
        or lease.get("owner_id") != execution.get("execution_id")
        or lease.get("workspace_id") != execution.get("workspace_id")
    ):
        return None
    epoch = lease.get("lease_epoch")
    return epoch if isinstance(epoch, int) and not isinstance(epoch, bool) else None


def observation_basis(payload: Mapping[str, Any], *, execution_id: str) -> dict[str, Any]:
    current = validate_state_payload(copy.deepcopy(dict(payload)))
    matches = [item for item in current["executions"] if item["execution_id"] == execution_id]
    if len(matches) != 1:
        raise StatePayloadError("observation execution_id does not resolve exactly")
    execution = matches[0]
    return {
        "execution_id": execution_id,
        "control_epoch": execution["control_epoch"],
        "lease_epoch": _execution_writer_lease_epoch(current, execution),
    }


def _basis_is_current(current: Mapping[str, Any], basis: Mapping[str, Any]) -> bool:
    if not isinstance(basis, Mapping):
        return False
    execution_id = basis.get("execution_id")
    matches = [item for item in current["executions"] if item["execution_id"] == execution_id]
    if len(matches) != 1:
        return False
    execution = matches[0]
    if basis.get("control_epoch") != execution["control_epoch"]:
        return False
    return basis.get("lease_epoch") == _execution_writer_lease_epoch(current, execution)


def reconcile_execution_observation(
    payload: Mapping[str, Any],
    *,
    basis: Mapping[str, Any],
    host_state: str,
    agent_id: str | None = None,
    failure_origin: str = "tool_failure",
    now: datetime | str | None = None,
) -> dict[str, Any]:
    """Apply one Host observation only while its ExecutionBinding basis is current."""
    current = copy.deepcopy(dict(payload))
    validate_state_payload(current)
    if not _basis_is_current(current, basis):
        return {"reconcile_status": "stale", "state": current}
    before = copy.deepcopy(current)
    execution = next(
        item for item in current["executions"] if item["execution_id"] == basis["execution_id"]
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
                unit = next(
                    item for item in current["work_units"] if item["unit_id"] == execution["unit_id"]
                )
                if unit["state"] == "EXECUTING":
                    unit["state"] = "RESULT_READY"
    if current == before:
        return {"reconcile_status": "noop", "state": current}
    current["state_revision"] += 1
    current["updated_at"] = storage._utc_text(now)
    validate_state_payload(current)
    return {"reconcile_status": "applied", "state": current}
