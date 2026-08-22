#!/usr/bin/env python3
"""Supported V4 ExecutionBinding lifecycle facade.

Lifecycle transitions live in ``execution_lifecycle_v4_core``. This module keeps
one explicit public surface and enforces product-wide admission constraints before
a managed child can reach the Host.
"""

from __future__ import annotations

import os as _os
from typing import Mapping as _Mapping, Sequence as _Sequence

import dispatch_state_v4 as _state
import execution_lifecycle_v4_core as _core
import policy as _policy


ExecutionLifecycleError = _core.ExecutionLifecycleError
_PRODUCT_CHILD_LIMIT = _policy.managed_child_limit()
_ACTIVE_MANAGED_STATES = {"SPAWN_PENDING", "RUNNING", "INTERRUPTED", "UNKNOWN"}


def _active_managed_count(current: dict | None) -> int:
    if current is None:
        return 0
    return sum(
        1
        for execution in current.get("executions", [])
        if isinstance(execution, dict)
        and execution.get("lifecycle") in _ACTIVE_MANAGED_STATES
    )


def _next_attempt_no(current: _Mapping | None, unit_id: str) -> int:
    if current is None:
        return 1
    greatest = max(
        (
            int(item.get("attempt_no", 0))
            for item in current.get("executions", [])
            if isinstance(item, _Mapping) and item.get("unit_id") == unit_id
        ),
        default=0,
    )
    for event in current.get("accounting_refs", []):
        if (
            isinstance(event, _Mapping)
            and event.get("kind") == "execution_history"
            and event.get("unit_id") == unit_id
        ):
            greatest = max(greatest, int(event.get("max_attempt_no", 0)))
    return greatest + 1


def allocate_execution(
    thread_id: str,
    *,
    unit_id: str,
    execution_id: str,
    native_task_name: str,
    profile_id: str,
    granted_authority: str,
    granted_write_scope: _Sequence[str] = (),
    execution_basis_ref: str | None = None,
    writer_lease_id: str | None = None,
    temp_root: str | _os.PathLike[str] | None = None,
) -> dict:
    """Allocate one provisional execution without exceeding the product child ceiling."""
    current = _state.load_state(thread_id, temp_root=temp_root)
    if _active_managed_count(current) >= _PRODUCT_CHILD_LIMIT:
        raise ExecutionLifecycleError(
            f"product managed child limit {_PRODUCT_CHILD_LIMIT} is reached"
        )
    if current is None:
        raise ExecutionLifecycleError("active V4 state is unavailable")
    attempt_no = _next_attempt_no(current, unit_id)
    try:
        expected_task_name = _state.native_task_name_for(
            current,
            unit_id=unit_id,
            attempt_no=attempt_no,
        )
    except _state.StatePayloadError as exc:
        raise ExecutionLifecycleError(str(exc)) from exc
    if native_task_name != expected_task_name:
        raise ExecutionLifecycleError(
            f"native_task_name must match WorkUnit attempt generation: {expected_task_name}"
        )

    result = _core.allocate_execution(
        thread_id,
        unit_id=unit_id,
        execution_id=execution_id,
        native_task_name=native_task_name,
        profile_id=profile_id,
        granted_authority=granted_authority,
        granted_write_scope=granted_write_scope,
        execution_basis_ref=execution_basis_ref,
        writer_lease_id=writer_lease_id,
        temp_root=temp_root,
    )

    persisted = _state.load_state(thread_id, temp_root=temp_root)
    if _active_managed_count(persisted) > _PRODUCT_CHILD_LIMIT:
        try:
            _core.rollback_pre_materialization_spawn(
                thread_id,
                execution_id=execution_id,
                temp_root=temp_root,
            )
        except Exception as exc:
            raise ExecutionLifecycleError(
                "product child ceiling was exceeded and provisional rollback failed"
            ) from exc
        raise ExecutionLifecycleError(
            f"product managed child limit {_PRODUCT_CHILD_LIMIT} is reached"
        )
    return result


build_managed_spawn_tool_input = _core.build_managed_spawn_tool_input
prepare_spawn = _core.prepare_spawn
rollback_pre_materialization_spawn = _core.rollback_pre_materialization_spawn
prepare_same_child_followup = _core.prepare_same_child_followup
prepare_same_child_continue = _core.prepare_same_child_continue
prepare_interrupt = _core.prepare_interrupt
mark_execution_unknown = _core.mark_execution_unknown
fresh_observation_basis = _core.fresh_observation_basis
persist_host_observation = _core.persist_host_observation
takeover_to_main = _core.takeover_to_main
runtime_temp_root = _core.runtime_temp_root


__all__ = [
    "ExecutionLifecycleError",
    "allocate_execution",
    "build_managed_spawn_tool_input",
    "fresh_observation_basis",
    "mark_execution_unknown",
    "persist_host_observation",
    "prepare_interrupt",
    "prepare_same_child_continue",
    "prepare_same_child_followup",
    "prepare_spawn",
    "rollback_pre_materialization_spawn",
    "runtime_temp_root",
    "takeover_to_main",
]
