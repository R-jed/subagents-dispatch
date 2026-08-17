#!/usr/bin/env python3
"""V4 ExecutionBinding lifecycle helpers for fresh starts and same-child reuse."""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

import dispatch_control_v4 as control
import dispatch_state_v4 as state
import managed_execution_v4 as managed_execution
import writer_lease_v4 as writer


class ExecutionLifecycleError(RuntimeError):
    """An ExecutionBinding lifecycle request violates the frozen V4 contract."""


def _execution(current: Mapping[str, Any], execution_id: str) -> dict[str, Any]:
    matches = [
        item
        for item in current.get("executions", [])
        if isinstance(item, dict) and item.get("execution_id") == execution_id
    ]
    if len(matches) != 1:
        raise ExecutionLifecycleError("execution_id does not resolve exactly once")
    return matches[0]


def _unit(current: Mapping[str, Any], unit_id: str) -> dict[str, Any]:
    matches = [
        item
        for item in current.get("work_units", [])
        if isinstance(item, dict) and item.get("unit_id") == unit_id
    ]
    if len(matches) != 1:
        raise ExecutionLifecycleError("unit_id does not resolve exactly once")
    return matches[0]


def _authority_rank(value: str) -> int:
    try:
        return state.AUTHORITY_RANK[value]
    except KeyError as exc:
        raise ExecutionLifecycleError("invalid mutation authority") from exc


def allocate_execution(
    thread_id: str,
    *,
    unit_id: str,
    execution_id: str,
    native_task_name: str,
    profile_id: str,
    granted_authority: str,
    granted_write_scope: Sequence[str] = (),
    writer_lease_id: str | None = None,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Allocate one fresh attempt and reserve WriterLease atomically when writable."""
    if profile_id not in state.PROFILE_CONTRACT:
        raise ExecutionLifecycleError("profile_id is outside fixed V4 profiles")
    if not isinstance(execution_id, str) or not execution_id.strip():
        raise ExecutionLifecycleError("execution_id must be non-empty")
    if not isinstance(native_task_name, str) or not native_task_name.strip():
        raise ExecutionLifecycleError("native_task_name must be non-empty")
    model, effort, profile_authority = state.PROFILE_CONTRACT[profile_id]
    scope = list(granted_write_scope)
    allocated: dict[str, Any] = {}

    def mutate(current: dict[str, Any]) -> None:
        unit = _unit(current, unit_id)
        if unit["state"] != "READY":
            raise ExecutionLifecycleError("fresh execution requires READY WorkUnit")
        if current["team_plan_revision"] is None:
            raise ExecutionLifecycleError("fresh execution requires TeamPlan revision")
        if any(item["execution_id"] == execution_id for item in current["executions"]):
            raise ExecutionLifecycleError("execution_id is already present")
        if any(item["native_task_name"] == native_task_name for item in current["executions"]):
            raise ExecutionLifecycleError("native_task_name is already present")
        prior = [item for item in current["executions"] if item["unit_id"] == unit_id]
        attempt_no = len(prior) + 1
        if attempt_no > 2:
            raise ExecutionLifecycleError("fresh Agent attempt limit is exhausted")
        if any(item["lifecycle"] not in {"COMPLETED", "FAILED", "CLOSED"} for item in prior):
            raise ExecutionLifecycleError("prior fresh attempt is not settled")
        if granted_authority not in state.MUTATION_AUTHORITIES:
            raise ExecutionLifecycleError("granted_authority is invalid")
        if _authority_rank(granted_authority) > _authority_rank(unit["authority_ceiling"]):
            raise ExecutionLifecycleError("granted authority exceeds WorkUnit ceiling")
        if _authority_rank(granted_authority) > _authority_rank(profile_authority):
            raise ExecutionLifecycleError("granted authority exceeds fixed profile capability")
        if not set(scope).issubset(set(unit["write_scope_ceiling"])):
            raise ExecutionLifecycleError("granted write scope exceeds WorkUnit ceiling")
        if granted_authority == "none" and scope:
            raise ExecutionLifecycleError("read-only execution requires empty write scope")

        execution = {
            "execution_id": execution_id,
            "unit_id": unit_id,
            "team_plan_revision": current["team_plan_revision"],
            "attempt_no": attempt_no,
            "profile_id": profile_id,
            "agent_id": None,
            "native_task_name": native_task_name,
            "model": model,
            "effort": effort,
            "granted_authority": granted_authority,
            "granted_write_scope": scope,
            "workspace_id": state.CANONICAL_WORKSPACE_ID,
            "lifecycle": "SPAWN_PENDING",
            "control_epoch": 0,
            "followup_count": 0,
            "failure_origin": "none",
            "blocker": "none",
            "quarantine_reason": None,
        }
        current["executions"].append(execution)
        unit["state"] = "EXECUTING"

        lease = current.get("writer_lease")
        if granted_authority == "none":
            if writer_lease_id is not None:
                raise ExecutionLifecycleError("read-only fresh execution cannot request WriterLease")
        else:
            if not isinstance(writer_lease_id, str) or not writer_lease_id.strip():
                raise ExecutionLifecycleError("writable fresh execution requires writer_lease_id")
            if isinstance(lease, Mapping) and lease.get("state") in state.WRITER_BLOCKING_STATES:
                raise ExecutionLifecycleError("canonical workspace already has a managed writer")
            lease_epoch = 1 if lease is None else lease["lease_epoch"] + 1
            current["writer_lease"] = {
                "lease_id": writer_lease_id,
                "lease_epoch": lease_epoch,
                "workspace_id": state.CANONICAL_WORKSPACE_ID,
                "unit_id": unit_id,
                "owner_kind": "execution",
                "owner_id": execution_id,
                "state": "RESERVED",
            }
        allocated.update(copy.deepcopy(execution))

    persisted = state.mutate_state(thread_id, mutate, temp_root=temp_root)
    return {
        "execution": allocated,
        "writer_lease": copy.deepcopy(persisted["writer_lease"]),
    }


def build_managed_spawn_tool_input(
    thread_id: str,
    *,
    execution_id: str,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Return the one canonical Host spawn payload for an ExecutionBinding."""
    current = state.load_state(thread_id, temp_root=temp_root)
    if current is None:
        raise ExecutionLifecycleError("active V4 state is unavailable")
    try:
        return managed_execution.expected_spawn_input_for_execution(
            current, execution_id=execution_id
        )
    except managed_execution.ManagedExecutionContractError as exc:
        raise ExecutionLifecycleError(str(exc)) from exc


def prepare_spawn(
    thread_id: str,
    *,
    execution_id: str,
    control_id: str,
    tool_input: Mapping[str, Any],
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    current = state.load_state(thread_id, temp_root=temp_root)
    if current is None:
        raise ExecutionLifecycleError("active V4 state is unavailable")
    execution = _execution(current, execution_id)
    try:
        expected = managed_execution.expected_spawn_input_for_execution(
            current, execution_id=execution_id
        )
    except managed_execution.ManagedExecutionContractError as exc:
        raise ExecutionLifecycleError(str(exc)) from exc
    if dict(tool_input) != expected:
        raise ExecutionLifecycleError(
            "managed spawn tool_input does not match profile, fresh-context, or assignment contract"
        )
    effect = "NONE" if execution["granted_authority"] == "none" else "RESERVE"
    return control.prepare_control(
        thread_id,
        control_id=control_id,
        execution_id=execution_id,
        operation="SPAWN",
        tool_input=expected,
        writer_effect=effect,
        temp_root=temp_root,
    )


def _same_child_unit_is_mutable(current: Mapping[str, Any], execution: Mapping[str, Any]) -> None:
    unit = _unit(current, execution["unit_id"])
    if unit["state"] in {"ACCEPTED", "CANCELLED"}:
        raise ExecutionLifecycleError("accepted or cancelled WorkUnit cannot reactivate same child")


def _has_historical_followup(current: Mapping[str, Any], execution_id: str) -> bool:
    if any(
        item["execution_id"] == execution_id and item["operation"] == "FOLLOWUP"
        for item in current["pending_controls"]
    ):
        return True
    prefix = f"followup:{execution_id}:"
    return any(
        isinstance(event, Mapping)
        and event.get("kind") == "control_ack"
        and isinstance(event.get("control_id"), str)
        and event["control_id"].startswith(prefix)
        for event in current["accounting_refs"]
    )


def prepare_same_child_followup(
    thread_id: str,
    *,
    execution_id: str,
    tool_input: Mapping[str, Any],
    writer_lease_id: str | None = None,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Prepare the single focused correction without consuming a fresh attempt."""
    current = state.load_state(thread_id, temp_root=temp_root)
    if current is None:
        raise ExecutionLifecycleError("active V4 state is unavailable")
    execution = _execution(current, execution_id)
    _same_child_unit_is_mutable(current, execution)
    if execution["lifecycle"] != "COMPLETED":
        raise ExecutionLifecycleError("same-child FOLLOWUP requires COMPLETED execution")
    if execution["followup_count"] >= 1 or _has_historical_followup(current, execution_id):
        raise ExecutionLifecycleError("focused same-child followup budget is exhausted")

    if execution["granted_authority"] != "none":
        if not isinstance(writer_lease_id, str) or not writer_lease_id.strip():
            writer_lease_id = f"lease-followup-{execution_id}-{execution['control_epoch'] + 1}"
        writer.ensure_execution_writer_reserved(
            thread_id,
            execution_id=execution_id,
            lease_id=writer_lease_id,
            temp_root=temp_root,
        )
        effect = "RETAIN"
    else:
        effect = "NONE"

    control_id = f"followup:{execution_id}:e{execution['control_epoch'] + 1}"
    prepared = control.prepare_control(
        thread_id,
        control_id=control_id,
        execution_id=execution_id,
        operation="FOLLOWUP",
        tool_input=tool_input,
        writer_effect=effect,
        temp_root=temp_root,
    )

    def reserve_budget(updated: dict[str, Any]) -> None:
        target = _execution(updated, execution_id)
        if target["followup_count"] == 0:
            target["followup_count"] = 1

    state.mutate_state(thread_id, reserve_budget, temp_root=temp_root)
    return prepared


def prepare_same_child_continue(
    thread_id: str,
    *,
    execution_id: str,
    tool_input: Mapping[str, Any],
    writer_lease_id: str | None = None,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    current = state.load_state(thread_id, temp_root=temp_root)
    if current is None:
        raise ExecutionLifecycleError("active V4 state is unavailable")
    execution = _execution(current, execution_id)
    _same_child_unit_is_mutable(current, execution)
    if execution["lifecycle"] != "INTERRUPTED":
        raise ExecutionLifecycleError("CONTINUE requires INTERRUPTED same child")
    if execution["granted_authority"] != "none":
        if not isinstance(writer_lease_id, str) or not writer_lease_id.strip():
            writer_lease_id = f"lease-continue-{execution_id}-{execution['control_epoch'] + 1}"
        writer.ensure_execution_writer_reserved(
            thread_id,
            execution_id=execution_id,
            lease_id=writer_lease_id,
            temp_root=temp_root,
        )
        effect = "RETAIN"
    else:
        effect = "NONE"
    control_id = f"continue:{execution_id}:e{execution['control_epoch'] + 1}"
    return control.prepare_control(
        thread_id,
        control_id=control_id,
        execution_id=execution_id,
        operation="CONTINUE",
        tool_input=tool_input,
        writer_effect=effect,
        temp_root=temp_root,
    )


def prepare_interrupt(
    thread_id: str,
    *,
    execution_id: str,
    tool_input: Mapping[str, Any],
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    current = state.load_state(thread_id, temp_root=temp_root)
    if current is None:
        raise ExecutionLifecycleError("active V4 state is unavailable")
    execution = _execution(current, execution_id)
    if execution["lifecycle"] != "RUNNING":
        raise ExecutionLifecycleError("INTERRUPT requires RUNNING execution")
    if execution["granted_authority"] == "none":
        effect = "NONE"
    else:
        lease = current.get("writer_lease")
        if not isinstance(lease, Mapping):
            raise ExecutionLifecycleError("writing INTERRUPT requires WriterLease")
        writer.begin_revoke_execution_writer(
            thread_id,
            execution_id=execution_id,
            lease_id=lease["lease_id"],
            lease_epoch=lease["lease_epoch"],
            temp_root=temp_root,
        )
        effect = "REVOKE"
    current = state.load_state(thread_id, temp_root=temp_root)
    assert current is not None
    execution = _execution(current, execution_id)
    control_id = f"interrupt:{execution_id}:e{execution['control_epoch'] + 1}"
    return control.prepare_control(
        thread_id,
        control_id=control_id,
        execution_id=execution_id,
        operation="INTERRUPT",
        tool_input=tool_input,
        writer_effect=effect,
        temp_root=temp_root,
    )


def acknowledge_lifecycle_control(
    thread_id: str,
    *,
    tool_name: str,
    tool_input: Mapping[str, Any],
    tool_response: Any,
    tool_use_id: str,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Persist the Host ACK and authorized WriterLease effect in one transaction."""
    return control.acknowledge_control(
        thread_id,
        tool_name=tool_name,
        tool_input=tool_input,
        tool_response=tool_response,
        tool_use_id=tool_use_id,
        temp_root=temp_root,
    )


def fresh_observation_basis(
    thread_id: str,
    *,
    execution_id: str,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    current = state.load_state(thread_id, temp_root=temp_root)
    if current is None:
        raise ExecutionLifecycleError("active V4 state is unavailable")
    return state.observation_basis(current, execution_id=execution_id)


def persist_host_observation(
    thread_id: str,
    *,
    basis: Mapping[str, Any],
    host_state: str,
    agent_id: str | None = None,
    failure_origin: str = "tool_failure",
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    return writer.persist_host_observation(
        thread_id,
        basis=basis,
        host_state=host_state,
        agent_id=agent_id,
        failure_origin=failure_origin,
        temp_root=temp_root,
    )


def takeover_to_main(
    thread_id: str,
    *,
    execution_id: str,
    old_lease_id: str,
    old_lease_epoch: int,
    main_lease_id: str,
    guard_coverage: Mapping[str, Any],
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    return writer.transfer_settled_execution_writer_to_main(
        thread_id,
        execution_id=execution_id,
        lease_id=old_lease_id,
        lease_epoch=old_lease_epoch,
        main_lease_id=main_lease_id,
        guard_coverage=guard_coverage,
        temp_root=temp_root,
    )


def runtime_temp_root() -> Path | None:
    raw = os.environ.get("SUBAGENTS_DISPATCH_TEMP_ROOT")
    if raw is None or not raw.strip():
        return None
    return Path(raw)
