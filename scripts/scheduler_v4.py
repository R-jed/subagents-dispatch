#!/usr/bin/env python3
"""V4 orchestration constraint and status projection.

This module does not choose work, rank responsibilities, or issue launch actions.
The main session owns dispatch judgment. This module only projects machine-checkable
capacity, readiness, and state constraints from authoritative project and Host facts.
"""

from __future__ import annotations

import copy
from typing import Any, Mapping

import dispatch_state_v4 as state
import host_capabilities
import policy as policy_contract
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
ACTIVE_MANAGED_STATES = {"SPAWN_PENDING", "RUNNING", "INTERRUPTED", "UNKNOWN"}
RESULT_BACKLOG_STATES = {"RESULT_READY", "VERIFYING"}
PRODUCT_CHILD_LIMIT = policy_contract.managed_child_limit()


class SchedulerError(RuntimeError):
    """A constraint projection request is malformed."""


def _snapshot_capacity(snapshot: Mapping[str, Any] | None) -> tuple[int | None, bool, list[str]]:
    if snapshot is None:
        return None, False, ["capability_snapshot"]
    try:
        normalized = host_capabilities.validate_normalized_snapshot(snapshot)
    except host_capabilities.HostCapabilityError as exc:
        raise SchedulerError(str(exc)) from exc
    capacity = normalized.get("max_concurrent_threads_per_session")
    if normalized.get("execution_ready") is not True:
        return capacity, False, list(normalized.get("missing", []))
    return capacity, True, []


def _active_executions(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        execution
        for execution in payload.get("executions", [])
        if isinstance(execution, dict)
        and execution.get("lifecycle") in ACTIVE_MANAGED_STATES
    ]


def constraint_snapshot(
    payload: Mapping[str, Any],
    *,
    capability_snapshot: Mapping[str, Any] | None,
    wakeup_reason: str,
    plan_only: bool = False,
) -> dict[str, Any]:
    """Project deterministic constraints without choosing which WorkUnit to launch."""
    if wakeup_reason not in WAKEUP_REASONS:
        raise SchedulerError("unsupported orchestration wakeup reason")
    current = work_graph.refresh_dependency_states(copy.deepcopy(dict(payload)))
    state.validate_state_payload(current)

    host_session_capacity, host_ready, host_missing = _snapshot_capacity(capability_snapshot)
    active = _active_executions(current)
    active_count = len(active)
    product_free = max(0, PRODUCT_CHILD_LIMIT - active_count)
    host_free = (
        None
        if host_session_capacity is None
        else max(0, int(host_session_capacity) - 1 - active_count)
    )
    available_slots = product_free if host_free is None else min(product_free, host_free)
    if not host_ready or plan_only or wakeup_reason == "USER_CANCEL":
        available_slots = 0

    ready_ids = [
        unit["unit_id"]
        for unit in current["work_units"]
        if unit["state"] == "READY"
    ]
    result_backlog = sum(
        1 for unit in current["work_units"] if unit["state"] in RESULT_BACKLOG_STATES
    )

    stop_reason: str | None = None
    if plan_only:
        stop_reason = "plan_only"
    elif wakeup_reason == "USER_CANCEL":
        stop_reason = "user_cancel"
    elif not host_ready:
        stop_reason = "host_not_execution_ready"
    elif available_slots == 0 and ready_ids:
        stop_reason = "product_or_known_host_capacity_full"

    return {
        "mode": "constraint_snapshot",
        "wakeup_reason": wakeup_reason,
        "plan_only": plan_only,
        "selection_owner": "main",
        "host_ready": host_ready,
        "host_missing": host_missing,
        "host_session_capacity": host_session_capacity,
        "product_child_limit": PRODUCT_CHILD_LIMIT,
        "active_managed_executions": active_count,
        "available_launch_slots": available_slots,
        "launch_budget": available_slots,
        "ready_frontier": ready_ids,
        "result_backlog": result_backlog,
        "stop_reason": stop_reason,
        "actions": [],
        "writer_lease": copy.deepcopy(current["writer_lease"]),
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
        for execution in _active_executions(current)
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
        "selection_owner": "main",
        "product_child_limit": PRODUCT_CHILD_LIMIT,
        "active": active,
        "waiting": waiting,
        "writer_lease": copy.deepcopy(current["writer_lease"]),
        "acceptance_backlog": sum(
            1 for unit in current["work_units"] if unit["state"] in RESULT_BACKLOG_STATES
        ),
    }
