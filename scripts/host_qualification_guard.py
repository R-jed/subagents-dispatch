#!/usr/bin/env python3
"""Fail-close guard for maintainer real-Host qualification probes.

This module is intentionally maintainer-only and excluded from the Plugin runtime
package manifest. It prevents qualification bookkeeping mistakes from being
repaired by silently creating a second managed attempt for the same probe.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping, Sequence

import dispatch_state_v4 as state
import execution_lifecycle_v4 as lifecycle
import orchestrate_v4 as orchestrate


class QualificationGuardError(RuntimeError):
    """A real-Host qualification probe would violate single-use authorization."""


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _load_state(
    thread_id: str, temp_root: str | os.PathLike[str] | None
) -> dict[str, Any]:
    current = state.load_state(thread_id, temp_root=temp_root)
    if current is None:
        raise QualificationGuardError("active V4 state is unavailable")
    return current


def _preflight_ref(value: str) -> str:
    if not _nonempty(value):
        raise QualificationGuardError("qualification preflight ref must be non-empty")
    normalized = value.strip()
    if not normalized.startswith("preflight:issue-91-comment-") or not normalized.endswith(":RERUN"):
        raise QualificationGuardError(
            "qualification preflight ref must identify one Issue #91 RERUN authorization"
        )
    return normalized


def _unit(current: Mapping[str, Any], unit_id: str) -> Mapping[str, Any]:
    matches = [
        item
        for item in current.get("work_units", [])
        if isinstance(item, Mapping) and item.get("unit_id") == unit_id
    ]
    if len(matches) != 1:
        raise QualificationGuardError("qualification unit_id does not resolve exactly once")
    return matches[0]


def _unit_executions(current: Mapping[str, Any], unit_id: str) -> list[Mapping[str, Any]]:
    return [
        item
        for item in current.get("executions", [])
        if isinstance(item, Mapping) and item.get("unit_id") == unit_id
    ]


def _has_execution_history(current: Mapping[str, Any], unit_id: str) -> bool:
    return any(
        isinstance(item, Mapping)
        and item.get("kind") == "execution_history"
        and item.get("unit_id") == unit_id
        for item in current.get("accounting_refs", [])
    )


def _require_pristine_probe_unit(current: Mapping[str, Any], unit_id: str) -> None:
    unit = _unit(current, unit_id)
    if unit.get("state") != "READY":
        raise QualificationGuardError("single qualification probe requires a READY WorkUnit")
    if _unit_executions(current, unit_id) or _has_execution_history(current, unit_id):
        raise QualificationGuardError(
            "single qualification probe authorization is already consumed by prior execution history"
        )


def allocate_single_probe_execution(
    thread_id: str,
    *,
    unit_id: str,
    execution_id: str,
    native_task_name: str,
    profile_id: str,
    granted_authority: str,
    preflight_ref: str,
    granted_write_scope: Sequence[str] = (),
    writer_lease_id: str | None = None,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Allocate the only fresh attempt authorized for one qualification WorkUnit."""
    basis_ref = _preflight_ref(preflight_ref)
    current = _load_state(thread_id, temp_root)
    _require_pristine_probe_unit(current, unit_id)

    allocated = lifecycle.allocate_execution(
        thread_id,
        unit_id=unit_id,
        execution_id=execution_id,
        native_task_name=native_task_name,
        profile_id=profile_id,
        granted_authority=granted_authority,
        granted_write_scope=granted_write_scope,
        execution_basis_ref=basis_ref,
        writer_lease_id=writer_lease_id,
        temp_root=temp_root,
    )
    execution = allocated.get("execution")
    if not isinstance(execution, Mapping):
        raise QualificationGuardError("qualification allocation returned no ExecutionBinding")
    if (
        execution.get("attempt_no") != 1
        or execution.get("execution_basis_ref") != basis_ref
        or execution.get("lifecycle") != "SPAWN_PENDING"
    ):
        raise QualificationGuardError("qualification allocation drifted from single-probe contract")
    return allocated


def prepare_single_probe_spawn(
    thread_id: str,
    *,
    orchestration_id: str,
    unit_id: str,
    execution_id: str,
    preflight_ref: str,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Prepare a Host spawn only while the one authorized attempt remains pristine."""
    basis_ref = _preflight_ref(preflight_ref)
    current = _load_state(thread_id, temp_root)
    unit = _unit(current, unit_id)
    executions = _unit_executions(current, unit_id)

    if _has_execution_history(current, unit_id) or len(executions) != 1:
        raise QualificationGuardError(
            "qualification spawn requires exactly one retained first attempt and no history"
        )
    execution = executions[0]
    if execution.get("execution_id") != execution_id:
        raise QualificationGuardError("qualification spawn execution_id does not match the probe")
    if execution.get("attempt_no") != 1:
        raise QualificationGuardError("qualification spawn refuses a retry attempt")
    if execution.get("execution_basis_ref") != basis_ref:
        raise QualificationGuardError(
            "qualification spawn execution basis does not match the Issue #91 preflight"
        )
    if execution.get("lifecycle") != "SPAWN_PENDING" or execution.get("agent_id") is not None:
        raise QualificationGuardError(
            "qualification spawn requires the untouched pre-materialization ExecutionBinding"
        )
    if unit.get("state") != "EXECUTING":
        raise QualificationGuardError("qualification WorkUnit is not in its initial executing state")

    return orchestrate.prepare_managed_spawn(
        thread_id,
        orchestration_id=orchestration_id,
        execution_id=execution_id,
        temp_root=temp_root,
    )


def runtime_temp_root() -> Path | None:
    raw = os.environ.get("SUBAGENTS_DISPATCH_TEMP_ROOT")
    if raw is None or not raw.strip():
        return None
    return Path(raw)


__all__ = [
    "QualificationGuardError",
    "allocate_single_probe_execution",
    "prepare_single_probe_spawn",
    "runtime_temp_root",
]
