#!/usr/bin/env python3
"""V4 wakeup-driven reconcile scheduler with authoritative Host occupancy."""

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
CAPACITY_KIND = state.HOST_CAPACITY_OBSERVATION_KIND


class SchedulerError(RuntimeError):
    """Scheduler input is malformed or violates the frozen V4 contract."""


def _snapshot_capacity(snapshot: Mapping[str, Any] | None) -> tuple[int | None, bool, list[str]]:
    if snapshot is None:
        return None, False, ["host_capabilities_unavailable"]
    try:
        normalized = host_capabilities.validate_normalized_snapshot(snapshot)
    except host_capabilities.HostCapabilityError as exc:
        raise SchedulerError(str(exc)) from exc
    if normalized.get("execution_ready") is not True:
        missing = normalized.get("missing", [])
        return None, False, list(missing) or ["host_not_execution_ready"]
    return normalized["max_spawned_threads"], True, []


def _execution_counts(payload: Mapping[str, Any]) -> tuple[int, dict[str, list[dict[str, Any]]]]:
    by_unit: dict[str, list[dict[str, Any]]] = {}
    active = 0
    for execution in payload.get("executions", []):
        if not isinstance(execution, dict):
            continue
        by_unit.setdefault(execution["unit_id"], []).append(execution)
        if execution["lifecycle"] in ACTIVE_TURN_STATES:
            active += 1
    return active, by_unit


def _capacity_observation(payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
    matches = [
        event
        for event in payload.get("accounting_refs", [])
        if isinstance(event, Mapping) and event.get("kind") == CAPACITY_KIND
    ]
    if len(matches) > 1:
        raise SchedulerError("multiple current Host capacity observations are unsafe")
    return matches[0] if matches else None


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

    host_capacity, host_ready, host_missing = _snapshot_capacity(capability_snapshot)
    active_managed, executions_by_unit = _execution_counts(current)
    capacity_observation = _capacity_observation(current)
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
    product_ceiling = INITIAL_CHILD_LIMIT if initial else PRODUCT_CHILD_LIMIT
    product_free = max(0, product_ceiling - active_managed)

    resident = 0
    settled = 0
    managed_resident = 0
    unmanaged_resident = 0
    observation_required = bool(eligible) and capacity_observation is None
    if capacity_observation is not None:
        resident = int(capacity_observation["resident_children"])
        settled = int(capacity_observation["settled_children"])
        managed_resident = int(capacity_observation["managed_resident_children"])
        unmanaged_resident = int(capacity_observation["unmanaged_resident_children"])

    host_reclaim_attempt = False
    if capacity_observation is None:
        host_free = 0
    elif host_capacity is None:
        host_free = 1 if resident == 0 else 0
    else:
        host_free = max(0, host_capacity - resident)

    launch_budget = min(product_free, host_free)
    if (
        capacity_observation is not None
        and host_capacity is not None
        and resident >= host_capacity
        and settled > 0
        and product_free > 0
        and eligible
    ):
        # Current V2 performs the precise active-turn/mailbox unloadability check
        # inside the next spawn. Permit exactly one attempt; do not claim the
        # settled resident is guaranteed reclaimable.
        launch_budget = 1
        host_reclaim_attempt = True

    stop_reason: str | None = None
    if plan_only:
        launch_budget = 0
        host_reclaim_attempt = False
        stop_reason = "plan_only"
    elif not host_ready:
        launch_budget = 0
        host_reclaim_attempt = False
        stop_reason = "host_not_execution_ready"
    elif backpressure:
        launch_budget = 0
        host_reclaim_attempt = False
        stop_reason = "acceptance_backpressure"
    elif wakeup_reason == "USER_CANCEL":
        launch_budget = 0
        host_reclaim_attempt = False
        stop_reason = "user_cancel"
    elif product_free == 0 and eligible:
        launch_budget = 0
        host_reclaim_attempt = False
        stop_reason = "product_capacity_full"
    elif observation_required:
        launch_budget = 0
        host_reclaim_attempt = False
        stop_reason = "host_occupancy_observation_required"
    elif host_capacity is None and resident > 0 and eligible:
        launch_budget = 0
        host_reclaim_attempt = False
        stop_reason = "host_capacity_unknown_with_residents"
    elif host_capacity is not None and resident >= host_capacity and settled == 0 and eligible:
        launch_budget = 0
        stop_reason = "host_capacity_full"

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

    effective_capacity = (
        1 if host_capacity is None else min(PRODUCT_CHILD_LIMIT, host_capacity)
    )
    return {
        "mode": "wakeup_reconcile",
        "wakeup_reason": wakeup_reason,
        "plan_only": plan_only,
        "host_ready": host_ready,
        "host_missing": host_missing,
        "effective_capacity": effective_capacity,
        "host_capacity": host_capacity,
        "initial_fanout": initial,
        "active_managed_executions": active_managed,
        "occupied_slots": active_managed,
        "occupied_open_threads": resident if capacity_observation is not None else active_managed,
        "occupied_host_residents": resident,
        "settled_host_residents": settled,
        "managed_host_residents": managed_resident,
        "unmanaged_host_residents": unmanaged_resident,
        "requires_host_observation": observation_required,
        "host_reclaim_attempt": host_reclaim_attempt,
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
