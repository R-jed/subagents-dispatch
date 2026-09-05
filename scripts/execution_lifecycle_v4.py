#!/usr/bin/env python3
"""Supported V4 ExecutionBinding lifecycle facade.

Lifecycle transitions live in ``execution_lifecycle_v4_core``. This module keeps
one explicit public surface. Product-wide state invariants, including the managed
child ceiling, are enforced atomically by ``dispatch_state_v4.mutate_state``.
"""

from __future__ import annotations

import os as _os
from typing import Mapping as _Mapping, Sequence as _Sequence

import dispatch_state_v4 as _state
import execution_lifecycle_v4_core as _core


ExecutionLifecycleError = _core.ExecutionLifecycleError


def allocate_execution(
    thread_id: str,
    *,
    unit_id: str,
    execution_id: str,
    native_task_name: str,
    role_id: str,
    reasoning_effort: str | None,
    granted_authority: str,
    granted_write_scope: _Sequence[str] = (),
    execution_basis_ref: str | None = None,
    writer_lease_id: str | None = None,
    temp_root: str | _os.PathLike[str] | None = None,
) -> dict:
    """Allocate one provisional execution under the atomic state invariants."""
    current = _state.load_state(thread_id, temp_root=temp_root)
    if current is None:
        raise ExecutionLifecycleError("active V4 state is unavailable")
    attempt_no = _core._next_attempt_no(current, unit_id)
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

    try:
        return _core.allocate_execution(
            thread_id,
            unit_id=unit_id,
            execution_id=execution_id,
            native_task_name=native_task_name,
            role_id=role_id,
            reasoning_effort=reasoning_effort,
            granted_authority=granted_authority,
            granted_write_scope=granted_write_scope,
            execution_basis_ref=execution_basis_ref,
            writer_lease_id=writer_lease_id,
            temp_root=temp_root,
        )
    except _state.StatePayloadError as exc:
        if "product managed child limit" in str(exc):
            raise ExecutionLifecycleError(str(exc)) from exc
        raise


def _internal_same_child_tool_input(
    thread_id: str,
    *,
    execution_id: str,
    tool_input: _Mapping[str, object],
    temp_root: str | _os.PathLike[str] | None,
) -> dict:
    """Bind the public Host task address to the retained bare task segment."""
    current = _state.load_state(thread_id, temp_root=temp_root)
    if current is None:
        raise ExecutionLifecycleError("active V4 state is unavailable")
    execution = _core._execution(current, execution_id)
    canonical_target = f"/root/{execution['native_task_name']}"
    if not isinstance(tool_input, _Mapping) or tool_input.get("target") != canonical_target:
        raise ExecutionLifecycleError(
            "native lifecycle target must match canonical Host task address"
        )
    internal = dict(tool_input)
    internal["target"] = execution["native_task_name"]
    return internal


def _restore_host_tool_input(prepared: dict, tool_input: _Mapping[str, object]) -> dict:
    prepared["tool_input"] = dict(tool_input)
    return prepared


def prepare_same_child_followup(
    thread_id: str,
    *,
    execution_id: str,
    tool_input: _Mapping[str, object],
    correction_basis_ref: str,
    writer_lease_id: str | None = None,
    temp_root: str | _os.PathLike[str] | None = None,
) -> dict:
    internal = _internal_same_child_tool_input(
        thread_id,
        execution_id=execution_id,
        tool_input=tool_input,
        temp_root=temp_root,
    )
    prepared = _core.prepare_same_child_followup(
        thread_id,
        execution_id=execution_id,
        tool_input=internal,
        correction_basis_ref=correction_basis_ref,
        writer_lease_id=writer_lease_id,
        temp_root=temp_root,
    )
    return _restore_host_tool_input(prepared, tool_input)


def prepare_same_child_continue(
    thread_id: str,
    *,
    execution_id: str,
    tool_input: _Mapping[str, object],
    writer_lease_id: str | None = None,
    temp_root: str | _os.PathLike[str] | None = None,
) -> dict:
    internal = _internal_same_child_tool_input(
        thread_id,
        execution_id=execution_id,
        tool_input=tool_input,
        temp_root=temp_root,
    )
    prepared = _core.prepare_same_child_continue(
        thread_id,
        execution_id=execution_id,
        tool_input=internal,
        writer_lease_id=writer_lease_id,
        temp_root=temp_root,
    )
    return _restore_host_tool_input(prepared, tool_input)


def prepare_interrupt(
    thread_id: str,
    *,
    execution_id: str,
    tool_input: _Mapping[str, object],
    temp_root: str | _os.PathLike[str] | None = None,
) -> dict:
    internal = _internal_same_child_tool_input(
        thread_id,
        execution_id=execution_id,
        tool_input=tool_input,
        temp_root=temp_root,
    )
    prepared = _core.prepare_interrupt(
        thread_id,
        execution_id=execution_id,
        tool_input=internal,
        temp_root=temp_root,
    )
    return _restore_host_tool_input(prepared, tool_input)


build_managed_spawn_tool_input = _core.build_managed_spawn_tool_input
prepare_spawn = _core.prepare_spawn
rollback_pre_materialization_spawn = _core.rollback_pre_materialization_spawn
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
