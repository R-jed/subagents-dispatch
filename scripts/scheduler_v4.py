#!/usr/bin/env python3
"""Wakeup-driven V4 Native Core scheduler.

The scheduler owns product fanout, dependency readiness, acceptance backpressure,
and simple canonical-checkout phase isolation. Actual native thread capacity is
Host-owned and may reject a bounded spawn attempt.
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
RESULT_BACKLOG_STATES = {"RESULT_READY", "VERIFYING"}
PRODUCT_CHILD_LIMIT = 3
INITIAL_CHILD_LIMIT = 2
BACKPRESSURE_THRESHOLD = 2


class SchedulerError(RuntimeError):
    """Scheduler input is malformed or violates the V4 Native Core contract."""


def _snapshot_capacity(snapshot: Mapping[str, Any] | None) -> tuple[int | None, bool, list[str]]:
    if snapshot is None:
        return None, True, []
    try:
        normalized = host_capabilities.validate_normalized_snapshot(snapshot)
    except host_capabilities.HostCapabilityError as exc:
        raise SchedulerError(str(exc)) from exc
    if normalized.get("execution_ready") is not True:
        return normalized.get("max_spawned_threads"), False, list(normalized.get("missing", []))
    return normalized.get("max_spawned_threads"), True, []


def _execution_counts(
    payload: Mapping[str, Any],
) -> tuple[int, int, int, dict[str, list[dict[str, Any]]]]:
    by_unit: dict[str, list[dict[str, Any]]] = {}
    active = 0
    active_read = 0
    active_write = 0
    for execution in payload.get("executions", []):
        if not isinstance(execution, dict):
            continue
        by_unit.setdefault(execution["unit_id"], []).append(execution)
        if execution["lifecycle"] in ACTIVE_TURN_STATES:
            active += 1
            if execution["granted_authority"] == "none":
                active_read += 1
            else:
                active_write += 1
    return active, active_read, active_write, by_unit


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
    active_managed: int,
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

    writable = unit["authority_ceiling"] != "none"
    if writable:
        if blocking_writer is not None:
            return False, "writer_lease_blocked"
        if active_managed:
            return False, "read_phase_not_settled"
    elif blocking_writer is not None:
        return False, "writer_phase_active"
    return True, None


def _has_accepted_progress(payload: Mapping[str, Any]) -> bool:
    return any(
        isinstance(unit, Mapping) and unit.get("state") == "ACCEPTED"
        for unit in payload.get("work_units", [])
    )


def _phase_batch(
    eligible: list[str],
    *,
    by_id: Mapping[str, Mapping[str, Any]],
    launch_budget: int,
) -> tuple[list[str], list[str]]:
    """Choose one canonical-checkout phase for this scheduling decision.

    A writer is always a singleton batch. A read batch may contain multiple
    independent read-oriented units. Read and write work never share one launch
    batch because all actions in a scheduler decision can be acted on before the
    next reconciliation observes a newly reserved WriterLease.
    """
    if launch_budget <= 0 or not eligible:
        return [], list(eligible)

    first = eligible[0]
    first_writable = by_id[first]["authority_ceiling"] != "none"
    if first_writable:
        return [first], eligible[1:]

    read_eligible = [
        unit_id for unit_id in eligible if by_id[unit_id]["authority_ceiling"] == "none"
    ]
    selected = read_eligible[:launch_budget]
    selected_set = set(selected)
    deferred = [unit_id for unit_id in eligible if unit_id not in selected_set]
    return selected, deferred


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

    host_capacity, host_ready, host_missing = _snapshot_capacity(capability_snapshot)
    active_managed, active_read, active_write, executions_by_unit = _execution_counts(current)
    result_backlog = sum(
        1 for unit in current["work_units"] if unit["state"] in RESULT_BACKLOG_STATES
    )
    backpressure = result_backlog >= BACKPRESSURE_THRESHOLD
    blocking_writer = _blocking_writer(current)
    critical_lengths = work_graph.critical_path_lengths(current)

    ready_ids = [unit["unit_id"] for unit in current["work_units"] if unit["state"] == "READY"]
    ranked_ready = sorted(ready_ids, key=lambda unit_id: (-critical_lengths[unit_id], unit_id))
    by_id = {unit["unit_id"]: unit for unit in current["work_units"]}

    waiting: list[dict[str, str]] = []
    eligible: list[str] = []
    for unit_id in ranked_ready:
        ok, reason = _eligible_fresh_start(
            by_id[unit_id],
            executions=executions_by_unit.get(unit_id, []),
            active_managed=active_managed,
            blocking_writer=blocking_writer,
        )
        if ok:
            eligible.append(unit_id)
        else:
            waiting.append({"unit_id": unit_id, "reason": reason or "ineligible"})

    initial = not _has_accepted_progress(current)
    product_ceiling = INITIAL_CHILD_LIMIT if initial else PRODUCT_CHILD_LIMIT
    effective_capacity = product_ceiling
    if host_capacity is not None:
        effective_capacity = min(effective_capacity, host_capacity)
    product_free = max(0, effective_capacity - active_managed)
    launch_budget = min(product_free, len(eligible))

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
    elif product_free == 0 and eligible:
        launch_budget = 0
        stop_reason = "product_or_known_host_capacity_full"

    selected, deferred = _phase_batch(
        eligible,
        by_id=by_id,
        launch_budget=launch_budget,
    )
    actions = [
        {
            "action": "START_FRESH",
            "unit_id": unit_id,
            "priority": critical_lengths[unit_id],
        }
        for unit_id in selected
    ]
    selected_writable = bool(selected) and by_id[selected[0]]["authority_ceiling"] != "none"
    for unit_id in deferred:
        if selected_writable or (
            selected and by_id[unit_id]["authority_ceiling"] != "none"
        ):
            reason = "phase_batch_boundary"
        else:
            reason = "product_fanout_limit"
        waiting.append({"unit_id": unit_id, "reason": reason})

    blocked = [
        {"unit_id": unit["unit_id"], "reason": "dependencies_unaccepted"}
        for unit in current["work_units"]
        if unit["state"] == "BLOCKED"
    ]

    return {
        "mode": "wakeup_reconcile",
        "wakeup_reason": wakeup_reason,
        "plan_only": plan_only,
        "host_ready": host_ready,
        "host_missing": host_missing,
        "host_capacity": host_capacity,
        "effective_capacity": effective_capacity,
        "initial_fanout": initial,
        "active_managed_executions": active_managed,
        "active_read_executions": active_read,
        "active_write_executions": active_write,
        "result_backlog": result_backlog,
        "backpressure": backpressure,
        "ready_frontier": ready_ids,
        "ranked_frontier": ranked_ready,
        "launch_budget": len(selected),
        "stop_reason": stop_reason,
        "actions": actions,
        "waiting": waiting,
        "blocked": blocked,
    }


def scheduler_status(payload: Mapping[str, Any]) -> dict[str, Any]:
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
    return {
        "active": active,
        "waiting": waiting,
        "writer_lease": copy.deepcopy(current["writer_lease"]),
        "acceptance_backlog": sum(
            1 for unit in current["work_units"] if unit["state"] in RESULT_BACKLOG_STATES
        ),
    }
