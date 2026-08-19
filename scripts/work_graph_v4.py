#!/usr/bin/env python3
"""V4 compact Work Graph mutations.

The Work Graph owns dependency and acceptance truth. Host lifecycle completion is
only execution evidence; a dependency becomes ready only after the predecessor
WorkUnit reaches ACCEPTED.
"""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

import dispatch_state_v4 as state


class WorkGraphError(RuntimeError):
    """A Work Graph transition would violate the V4 contract."""


TERMINAL_UNIT_STATES = {"ACCEPTED", "CANCELLED"}
FRESH_RETRY_EXECUTION_STATES = {"COMPLETED", "FAILED", "CLOSED"}
ACTIVE_OR_AMBIGUOUS_EXECUTION_STATES = {"SPAWN_PENDING", "RUNNING", "UNKNOWN"}


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _unit(current: Mapping[str, Any], unit_id: str) -> dict[str, Any]:
    matches = [
        item
        for item in current.get("work_units", [])
        if isinstance(item, dict) and item.get("unit_id") == unit_id
    ]
    if len(matches) != 1:
        raise WorkGraphError("unit_id does not resolve exactly once")
    return matches[0]


def _executions(current: Mapping[str, Any], unit_id: str) -> list[dict[str, Any]]:
    return [
        item
        for item in current.get("executions", [])
        if isinstance(item, dict) and item.get("unit_id") == unit_id
    ]


def _current_execution(current: Mapping[str, Any], unit_id: str) -> dict[str, Any]:
    executions = _executions(current, unit_id)
    if not executions:
        raise WorkGraphError("WorkUnit has no producing execution")
    greatest = max(item.get("attempt_no", 0) for item in executions)
    matches = [item for item in executions if item.get("attempt_no") == greatest]
    if len(matches) != 1:
        raise WorkGraphError("WorkUnit current execution is ambiguous")
    return matches[0]


def _require_current_execution(
    current: Mapping[str, Any], *, unit_id: str, execution_id: str
) -> dict[str, Any]:
    execution = _current_execution(current, unit_id)
    if execution.get("execution_id") != execution_id:
        raise WorkGraphError("execution is superseded by a newer current attempt")
    return execution


def make_work_unit(
    *,
    unit_id: str,
    intent: str,
    goal: str,
    output: str,
    depends_on: Sequence[str] = (),
    ownership_write: Sequence[str] = (),
    ownership_forbidden: Sequence[str] = (),
    authority_ceiling: str = "none",
    write_scope_ceiling: Sequence[str] = (),
    done_when: str,
) -> dict[str, Any]:
    """Build one compact WorkUnit with dependency-derived initial state."""
    dependencies = list(depends_on)
    return {
        "unit_id": unit_id,
        "intent": intent,
        "goal": goal,
        "output": output,
        "depends_on": dependencies,
        "state": "BLOCKED" if dependencies else "READY",
        "ownership": {
            "write": list(ownership_write),
            "forbidden": list(ownership_forbidden),
        },
        "authority_ceiling": authority_ceiling,
        "write_scope_ceiling": list(write_scope_ceiling),
        "done_when": done_when,
        "accepted_result_ref": None,
        "accepted_execution_id": None,
        "accepted_control_epoch": None,
    }


def refresh_dependency_states(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy whose BLOCKED/READY states reflect ACCEPTED dependencies."""
    current = copy.deepcopy(dict(payload))
    state.validate_state_payload(current)
    by_id = {unit["unit_id"]: unit for unit in current["work_units"]}
    for unit in current["work_units"]:
        if unit["state"] not in {"BLOCKED", "READY"}:
            continue
        ready = all(by_id[dependency]["state"] == "ACCEPTED" for dependency in unit["depends_on"])
        unit["state"] = "READY" if ready else "BLOCKED"
    state.validate_state_payload(current)
    return current


def ready_frontier(payload: Mapping[str, Any]) -> list[str]:
    refreshed = refresh_dependency_states(payload)
    return [unit["unit_id"] for unit in refreshed["work_units"] if unit["state"] == "READY"]


def critical_path_lengths(payload: Mapping[str, Any]) -> dict[str, int]:
    """Return downstream critical-path lengths for the current compact DAG."""
    current = refresh_dependency_states(payload)
    by_id = {unit["unit_id"]: unit for unit in current["work_units"]}
    children: dict[str, list[str]] = {unit_id: [] for unit_id in by_id}
    for unit in current["work_units"]:
        for dependency in unit["depends_on"]:
            children[dependency].append(unit["unit_id"])

    memo: dict[str, int] = {}

    def length(unit_id: str) -> int:
        if unit_id in memo:
            return memo[unit_id]
        descendants = [
            child
            for child in children[unit_id]
            if by_id[child]["state"] not in TERMINAL_UNIT_STATES
        ]
        memo[unit_id] = 1 + max((length(child) for child in descendants), default=0)
        return memo[unit_id]

    return {unit_id: length(unit_id) for unit_id in by_id}


def install_single_work_unit(
    thread_id: str,
    *,
    unit: Mapping[str, Any],
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Install one dependency-free WorkUnit without creating TeamPlan truth."""
    supplied = copy.deepcopy(dict(unit))
    if supplied.get("depends_on") != []:
        raise WorkGraphError("single WorkUnit path cannot carry a dependency")
    if supplied.get("state") != "READY":
        raise WorkGraphError("single WorkUnit path requires a READY WorkUnit")

    def mutate(current: dict[str, Any]) -> None:
        if current["team_plan_revision"] is not None:
            raise WorkGraphError("single WorkUnit path cannot attach to TeamPlan")
        if current["work_units"] or current["executions"]:
            raise WorkGraphError("single WorkUnit can only be installed into an empty orchestration")
        if current["writer_lease"] is not None or current["pending_controls"]:
            raise WorkGraphError("single WorkUnit requires no lease or PendingControl")
        current["work_units"] = [supplied]

    return state.mutate_state(thread_id, mutate, temp_root=temp_root)


def install_work_graph(
    thread_id: str,
    *,
    team_plan_revision: int,
    units: Sequence[Mapping[str, Any]],
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Install the initial TeamPlan Work Graph into an empty V4 orchestration."""
    if (
        not isinstance(team_plan_revision, int)
        or isinstance(team_plan_revision, bool)
        or team_plan_revision < 1
    ):
        raise WorkGraphError("team_plan_revision must be a positive integer")
    supplied = copy.deepcopy([dict(unit) for unit in units])
    if not supplied:
        raise WorkGraphError("Work Graph must contain at least one WorkUnit")

    def mutate(current: dict[str, Any]) -> None:
        if current["work_units"] or current["executions"]:
            raise WorkGraphError("initial Work Graph can only be installed into an empty orchestration")
        if current["writer_lease"] is not None or current["pending_controls"]:
            raise WorkGraphError("initial Work Graph requires no lease or PendingControl")
        current["team_plan_revision"] = team_plan_revision
        current["work_units"] = supplied
        refreshed = refresh_dependency_states(current)
        current["work_units"] = refreshed["work_units"]

    return state.mutate_state(thread_id, mutate, temp_root=temp_root)


def begin_verification(
    thread_id: str,
    *,
    unit_id: str,
    execution_id: str,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Move RESULT_READY to VERIFYING without accepting dependency truth."""

    def mutate(current: dict[str, Any]) -> None:
        unit = _unit(current, unit_id)
        if unit["state"] != "RESULT_READY":
            raise WorkGraphError("verification requires RESULT_READY")
        execution = _require_current_execution(
            current, unit_id=unit_id, execution_id=execution_id
        )
        if execution["lifecycle"] != "COMPLETED":
            raise WorkGraphError("verification requires the completed current producing execution")
        unit["state"] = "VERIFYING"

    return state.mutate_state(thread_id, mutate, temp_root=temp_root)


def accept_work_unit(
    thread_id: str,
    *,
    unit_id: str,
    execution_id: str,
    result_ref: str,
    control_epoch: int,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Accept one exact current execution generation and unlock only its dependents."""
    if not _nonempty(result_ref):
        raise WorkGraphError("result_ref must be non-empty")
    if not isinstance(control_epoch, int) or isinstance(control_epoch, bool) or control_epoch < 0:
        raise WorkGraphError("control_epoch must be a non-negative integer")

    def mutate(current: dict[str, Any]) -> None:
        unit = _unit(current, unit_id)
        if unit["state"] not in {"RESULT_READY", "VERIFYING"}:
            raise WorkGraphError("acceptance requires RESULT_READY or VERIFYING")
        execution = _require_current_execution(
            current, unit_id=unit_id, execution_id=execution_id
        )
        if execution["lifecycle"] != "COMPLETED":
            raise WorkGraphError("accepted execution must be current and Host COMPLETED")
        if execution["control_epoch"] != control_epoch:
            raise WorkGraphError("acceptance control_epoch is stale")
        execution_ids = {item["execution_id"] for item in _executions(current, unit_id)}
        if any(
            control["execution_id"] in execution_ids
            and control["state"] in state.UNRESOLVED_CONTROL_STATES
            for control in current["pending_controls"]
        ):
            raise WorkGraphError("acceptance is blocked by unresolved PendingControl")
        unit["state"] = "ACCEPTED"
        unit["accepted_result_ref"] = result_ref
        unit["accepted_execution_id"] = execution_id
        unit["accepted_control_epoch"] = control_epoch
        refreshed = refresh_dependency_states(current)
        current["work_units"] = refreshed["work_units"]

    return state.mutate_state(thread_id, mutate, temp_root=temp_root)


def reject_work_unit(
    thread_id: str,
    *,
    unit_id: str,
    execution_id: str,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Reject a produced candidate without unlocking dependencies."""

    def mutate(current: dict[str, Any]) -> None:
        unit = _unit(current, unit_id)
        if unit["state"] not in {"RESULT_READY", "VERIFYING"}:
            raise WorkGraphError("rejection requires RESULT_READY or VERIFYING")
        execution = _require_current_execution(
            current, unit_id=unit_id, execution_id=execution_id
        )
        if execution["lifecycle"] != "COMPLETED":
            raise WorkGraphError("rejection requires the completed current producing execution")
        unit["state"] = "REJECTED"

    return state.mutate_state(thread_id, mutate, temp_root=temp_root)


def reopen_rejected_work_unit(
    thread_id: str,
    *,
    unit_id: str,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Reopen a rejected unit for one remaining fresh Agent attempt."""

    def mutate(current: dict[str, Any]) -> None:
        unit = _unit(current, unit_id)
        if unit["state"] != "REJECTED":
            raise WorkGraphError("only REJECTED WorkUnit can be reopened")
        executions = _executions(current, unit_id)
        if len(executions) >= 2:
            raise WorkGraphError("fresh Agent attempt limit is exhausted")
        if any(item["lifecycle"] not in FRESH_RETRY_EXECUTION_STATES for item in executions):
            raise WorkGraphError("fresh retry requires all prior executions to be settled")
        if any(
            control["execution_id"] in {item["execution_id"] for item in executions}
            and control["state"] in state.UNRESOLVED_CONTROL_STATES
            for control in current["pending_controls"]
        ):
            raise WorkGraphError("fresh retry is blocked by unresolved PendingControl")
        by_id = {item["unit_id"]: item for item in current["work_units"]}
        unit["state"] = (
            "READY"
            if all(by_id[dependency]["state"] == "ACCEPTED" for dependency in unit["depends_on"])
            else "BLOCKED"
        )

    return state.mutate_state(thread_id, mutate, temp_root=temp_root)


def cancel_work_unit(
    thread_id: str,
    *,
    unit_id: str,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Cancel work only when no active or ambiguous execution/control remains."""

    def mutate(current: dict[str, Any]) -> None:
        unit = _unit(current, unit_id)
        if unit["state"] == "ACCEPTED":
            raise WorkGraphError("accepted WorkUnit cannot be cancelled")
        executions = _executions(current, unit_id)
        if any(item["lifecycle"] in ACTIVE_OR_AMBIGUOUS_EXECUTION_STATES for item in executions):
            raise WorkGraphError("cannot cancel WorkUnit with active or ambiguous execution")
        execution_ids = {item["execution_id"] for item in executions}
        if any(
            control["execution_id"] in execution_ids
            and control["state"] in state.UNRESOLVED_CONTROL_STATES
            for control in current["pending_controls"]
        ):
            raise WorkGraphError("cannot cancel WorkUnit with unresolved PendingControl")
        unit["state"] = "CANCELLED"

    return state.mutate_state(thread_id, mutate, temp_root=temp_root)


def runtime_temp_root() -> Path | None:
    raw = os.environ.get("SUBAGENTS_DISPATCH_TEMP_ROOT")
    if raw is None or not raw.strip():
        return None
    return Path(raw)
