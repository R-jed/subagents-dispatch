#!/usr/bin/env python3
"""V4 wakeup-driven reconcile scheduler.

The scheduler is a deterministic decision engine. It has no daemon, timer, or
background polling loop. Every call starts from persisted V4 state plus an
explicit Host capability snapshot and returns bounded next actions.
"""

from __future__ import annotations

import copy
from typing import Any, Mapping

import dispatch_state_v4 as state
import host_capabilities
import work_graph_v4 as work_graph


WAKEUP_REASONS = {
    "USER_INPUT",
    "AGENT_UPDATE",
    "AGENT_COMPLETED",
    "AGENT_BLOCKED",
    "CAPACITY_RELEASED",
    "REVIEW_FAILED",
    "USER_CANCEL",
}
ACTIVE_TURN_STATES = {"SPAWN_PENDING", "RUNNING", "UNKNOWN"}
OPEN_THREAD_STATES = {
    "SPAWN_PENDING",
    "RUNNING",
    "INTERRUPTED",
    "COMPLETED",
    "FAILED",
    "UNKNOWN",
}
RESULT_BACKLOG_STATES = {"RESULT_READY", "VERIFYING"}
PRODUCT_CHILD_LIMIT = 3
INITIAL_CHILD_LIMIT = 2
BACKPRESSURE_THRESHOLD = 2


class SchedulerError(RuntimeError):
    """Scheduler input is malformed or violates the frozen V4 policy."""


def _snapshot_capacity(snapshot: Mapping[str, Any] | None) -> tuple[int, bool, list[str]]:
    if snapshot is None:
        return 0, False, ["host_capabilities_unavailable"]
    if not isinstance(snapshot, Mapping):
        raise SchedulerError("Host capability snapshot must be an object")
    execution_ready = snapshot.get("execution_ready") is True
    missing_raw = snapshot.get("missing", [])
    missing = list(missing_raw) if isinstance(missing_raw, list) else ["invalid_host_snapshot"]
    if not execution_ready:
        return 0, False, missing or ["host_not_execution_ready"]
    try:
        effective = host_capabilities.effective_managed_child_limit(
            snapshot, product_limit=PRODUCT_CHILD_LIMIT
        )
    except host_capabilities.HostCapabilityError as exc:
        raise SchedulerError(str(exc)) from exc
    return (1 if effective is None else effective), True, []


def _execution_counts(payload: Mapping[str, Any]) -> tuple[int, dict[str, list[dict[str, Any]]]]:
    """Count Host thread slots conservatively until an execution is CLOSED."""
    by_unit: dict[str, list[dict[str, Any]]] = {}
    open_threads = 0
    for execution in payload.get("executions", []):
        if not isinstance(execution, dict):
            continue
        by_unit.setdefault(execution["unit_id"], []).append(execution)
        if execution["lifecycle"] in OPEN_THREAD_STATES:
            open_threads += 1
    return open_threads, by_unit


def _blocking_writer(payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
    lease = payload.get("writer_lease")
    if not isinstance(lease, Mapping):
        return None
    if lease.get("state") in state.WRITER_BLOCKING_STATES:
        return lease
    return None


def _eligible_fresh_start(
    unit: Mapping[str, Any],
    *,
    executions: list[Mapping[str, Any]],
    blocking_writer: Mapping[str, Any] | None,
) -> tuple[bool, str | None]:
    if unit["state"] != "READY":
        return False, "not_ready"
    if len(executions) >= 2:
        return False, "fresh_attempt_limit"
    if any(item["lifecycle"] in ACTIVE_TURN_STATES for item in executions):
        return False, "execution_active_or_unknown"
    if any(item["lifecycle"] not in {"COMPLETED", "FAILED", "CLOSED"} for item in executions):
        return False, "prior_execution_not_settled_for_fresh"
    if unit["authority_ceiling"] != "none" and blocking_writer is not None:
        return False, "writer_lease_blocked"
    return True, None


def _has_accepted_progress(payload: Mapping[str, Any]) -> bool:
    """Initial fan-out ends only after Main has accepted at least one result."""
    return any(
        isinstance(unit, Mapping) and unit.get("state") == "ACCEPTED"
        for unit in payload.get("work_units", [])
    )


def scheduler_decision(
    payload: Mapping[str, Any],
    *,
    capability_snapshot: Mapping[str, Any] | None,
    wakeup_reason: str,
    plan_only: bool = False,
) -> dict[str, Any]:
    """Return one bounded scheduling decision for an explicit wakeup."""
    if wakeup_reason not in WAKEUP_REASONS:
        raise SchedulerError("unsupported scheduler wakeup reason")
    current = work_graph.refresh_dependency_states(copy.deepcopy(dict(payload)))
    state.validate_state_payload(current)

    effective_capacity, host_ready, host_missing = _snapshot_capacity(capability_snapshot)
    occupied, executions_by_unit = _execution_counts(current)
    result_backlog = sum(
        1 for unit in current["work_units"] if unit["state"] in RESULT_BACKLOG_STATES
    )
    backpressure = result_backlog >= BACKPRESSURE_THRESHOLD
    blocking_writer = _blocking_writer(current)
    critical_lengths = work_graph.critical_path_lengths(current)

    ready_ids = [unit["unit_id"] for unit in current["work_units"] if unit["state"] == "READY"]
    ranked_ready = sorted(
        ready_ids,
        key=lambda unit_id: (-critical_lengths[unit_id], unit_id),
    )

    waiting: list[dict[str, str]] = []
    eligible: list[str] = []
    by_id = {unit["unit_id"]: unit for unit in current["work_units"]}
    for unit_id in ranked_ready:
        ok, reason = _eligible_fresh_start(
            by_id[unit_id],
            executions=executions_by_unit.get(unit_id, []),
            blocking_writer=blocking_writer,
        )
        if ok:
            eligible.append(unit_id)
        else:
            waiting.append({"unit_id": unit_id, "reason": reason or "ineligible"})

    initial = not _has_accepted_progress(current)
    concurrency_ceiling = min(
        effective_capacity,
        INITIAL_CHILD_LIMIT if initial else PRODUCT_CHILD_LIMIT,
    )
    launch_budget = max(0, concurrency_ceiling - occupied)

    stop_reason: str | None = None
    if plan_only:
        launch_budget = 0
        stop_reason = "plan_only"
    elif not host_ready:
        launch_budget = 0
        stop_reason = "host_not_execution_ready"
    elif backpressure:
        launch_budget = 0
        stop_reason = "acceptance_backpressure"
    elif wakeup_reason == "USER_CANCEL":
        launch_budget = 0
        stop_reason = "user_cancel"
    elif occupied >= concurrency_ceiling:
        launch_budget = 0
        stop_reason = "capacity_full"

    selected = eligible[:launch_budget]
    actions = [
        {
            "action": "START_FRESH",
            "unit_id": unit_id,
            "priority": critical_lengths[unit_id],
        }
        for unit_id in selected
    ]

    for unit_id in eligible[len(selected):]:
        waiting.append(
            {
                "unit_id": unit_id,
                "reason": "capacity_or_initial_fanout_limit",
            }
        )

    blocked = [
        {
            "unit_id": unit["unit_id"],
            "reason": "dependencies_unaccepted",
        }
        for unit in current["work_units"]
        if unit["state"] == "BLOCKED"
    ]

    return {
        "mode": "wakeup_reconcile",
        "wakeup_reason": wakeup_reason,
        "plan_only": plan_only,
        "host_ready": host_ready,
        "host_missing": host_missing,
        "effective_capacity": effective_capacity,
        "initial_fanout": initial,
        "occupied_slots": occupied,
        "occupied_open_threads": occupied,
        "result_backlog": result_backlog,
        "backpressure": backpressure,
        "ready_frontier": ready_ids,
        "ranked_frontier": ranked_ready,
        "launch_budget": launch_budget,
        "stop_reason": stop_reason,
        "actions": actions,
        "waiting": waiting,
        "blocked": blocked,
    }


def scheduler_status(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return user-visible structural status without Host polling."""
    current = work_graph.refresh_dependency_states(copy.deepcopy(dict(payload)))
    state.validate_state_payload(current)
    active = [
        {
            "execution_id": execution["execution_id"],
            "unit_id": execution["unit_id"],
            "lifecycle": execution["lifecycle"],
        }
        for execution in current["executions"]
        if execution["lifecycle"] in ACTIVE_TURN_STATES
    ]
    waiting = [
        {
            "unit_id": unit["unit_id"],
            "state": unit["state"],
            "depends_on": list(unit["depends_on"]),
        }
        for unit in current["work_units"]
        if unit["state"] in {"BLOCKED", "READY", "RESULT_READY", "VERIFYING"}
    ]
    lease = copy.deepcopy(current["writer_lease"])
    return {
        "active": active,
        "waiting": waiting,
        "writer_lease": lease,
        "acceptance_backlog": sum(
            1 for unit in current["work_units"] if unit["state"] in RESULT_BACKLOG_STATES
        ),
    }
