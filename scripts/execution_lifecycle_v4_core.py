#!/usr/bin/env python3
"""Native Core ExecutionBinding lifecycle helpers.

Lifecycle authorization is Main-owned and lifecycle truth is Host-owned. These
helpers mutate only project state. They do not depend on Plugin Hook callbacks,
PendingControl, synthetic acknowledgements, or Host tool-use identifiers.
"""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

import dispatch_state_v4 as state
import managed_execution_v4 as managed_execution
import policy as policy_contract
import writer_lease_v4 as writer


_PROFILE_SPECS = policy_contract.profile_contracts()


class ExecutionLifecycleError(RuntimeError):
    """An ExecutionBinding lifecycle request violates the V4 Native Core contract."""


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


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_fresh_plan_binding(current: Mapping[str, Any], unit: Mapping[str, Any]) -> None:
    if current.get("team_plan_revision") is not None:
        return
    work_units = current.get("work_units", [])
    if len(work_units) != 1 or work_units[0].get("unit_id") != unit.get("unit_id"):
        raise ExecutionLifecycleError(
            "fresh execution without TeamPlan requires exactly one WorkUnit"
        )
    if unit.get("depends_on"):
        raise ExecutionLifecycleError(
            "fresh execution without TeamPlan cannot carry delegated dependencies"
        )


def _fresh_execution_state_is_eligible(
    unit: Mapping[str, Any], prior: Sequence[Mapping[str, Any]]
) -> bool:
    if not prior:
        return unit.get("state") == "READY"
    current = max(prior, key=lambda item: int(item.get("attempt_no", 0)))
    if unit.get("state") == "READY":
        return True
    if unit.get("state") == "REJECTED":
        return current.get("lifecycle") == "COMPLETED"
    if unit.get("state") == "EXECUTING":
        return current.get("lifecycle") in {"FAILED", "CLOSED"}
    return False


def allocate_execution(
    thread_id: str,
    *,
    unit_id: str,
    execution_id: str,
    native_task_name: str,
    profile_id: str,
    granted_authority: str,
    granted_write_scope: Sequence[str] = (),
    execution_basis_ref: str | None = None,
    writer_lease_id: str | None = None,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Allocate one provisional fresh activation and reserve writer ownership atomically."""
    if profile_id not in _PROFILE_SPECS:
        raise ExecutionLifecycleError("profile_id is outside fixed V4 profiles")
    if not isinstance(execution_id, str) or not execution_id.strip():
        raise ExecutionLifecycleError("execution_id must be non-empty")
    if not isinstance(native_task_name, str) or not native_task_name.strip():
        raise ExecutionLifecycleError("native_task_name must be non-empty")
    if execution_basis_ref is not None and not _nonempty(execution_basis_ref):
        raise ExecutionLifecycleError("execution_basis_ref must be non-empty when supplied")
    profile = _PROFILE_SPECS[profile_id]
    model = profile["model"]
    effort = profile["effort"]
    profile_authority = profile["mutation_authority"]
    scope = list(granted_write_scope)
    allocated: dict[str, Any] = {}

    def mutate(current: dict[str, Any]) -> None:
        unit = _unit(current, unit_id)
        _validate_fresh_plan_binding(current, unit)
        if any(item["execution_id"] == execution_id for item in current["executions"]):
            raise ExecutionLifecycleError("execution_id is already present")
        if any(item["native_task_name"] == native_task_name for item in current["executions"]):
            raise ExecutionLifecycleError("native_task_name is already present")
        prior = [item for item in current["executions"] if item["unit_id"] == unit_id]
        if not _fresh_execution_state_is_eligible(unit, prior):
            raise ExecutionLifecycleError(
                "fresh execution requires READY work or a settled unresolved current execution"
            )
        attempt_no = len(prior) + 1
        if attempt_no > 2:
            raise ExecutionLifecycleError("fresh Agent attempt limit is exhausted")
        if any(item["lifecycle"] not in {"COMPLETED", "FAILED", "CLOSED"} for item in prior):
            raise ExecutionLifecycleError("prior fresh attempt is not settled")

        basis_ref = execution_basis_ref
        if prior:
            prior_basis_refs = {
                item.get("execution_basis_ref")
                for item in prior
                if _nonempty(item.get("execution_basis_ref"))
            }
            if basis_ref is None:
                if unit.get("state") == "READY" and not prior_basis_refs:
                    basis_ref = f"legacy-reopen:{execution_id}"
                else:
                    raise ExecutionLifecycleError(
                        "fresh retry requires a new execution_basis_ref"
                    )
            if basis_ref in prior_basis_refs:
                raise ExecutionLifecycleError(
                    "fresh retry execution_basis_ref must differ from prior attempts"
                )
        elif basis_ref is None:
            basis_ref = f"initial:{execution_id}"

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
            "execution_basis_ref": basis_ref,
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
    tool_input: Mapping[str, Any],
    control_id: str | None = None,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Validate the direct native spawn input and return a transient action summary."""
    current = state.load_state(thread_id, temp_root=temp_root)
    if current is None:
        raise ExecutionLifecycleError("active V4 state is unavailable")
    execution = _execution(current, execution_id)
    if execution["lifecycle"] != "SPAWN_PENDING":
        raise ExecutionLifecycleError("direct spawn requires SPAWN_PENDING execution")
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
    return {
        "operation": "SPAWN",
        "execution_id": execution_id,
        "tool_input": copy.deepcopy(expected),
        "observation_basis": state.observation_basis(current, execution_id=execution_id),
    }


def rollback_pre_materialization_spawn(
    thread_id: str,
    *,
    execution_id: str,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Remove a provisional fresh attempt only after Main proves no child materialized."""
    rolled_back: dict[str, Any] = {}

    def mutate(current: dict[str, Any]) -> None:
        execution = _execution(current, execution_id)
        unit = _unit(current, execution["unit_id"])
        current_execution = state.current_execution_for_unit(
            current, unit_id=execution["unit_id"]
        )
        if current_execution is None or current_execution.get("execution_id") != execution_id:
            raise ExecutionLifecycleError("only the current provisional execution may roll back")
        if execution["lifecycle"] != "SPAWN_PENDING" or execution["agent_id"] is not None:
            raise ExecutionLifecycleError("spawn rollback requires unmaterialized SPAWN_PENDING execution")
        if any(
            isinstance(event, Mapping)
            and event.get("kind") == "host_observation"
            and event.get("execution_id") == execution_id
            for event in current.get("accounting_refs", [])
        ):
            raise ExecutionLifecycleError("spawn rollback is unsafe after Host materialization evidence")
        lease = current.get("writer_lease")
        if isinstance(lease, Mapping) and lease.get("owner_id") == execution_id:
            if lease.get("owner_kind") != "execution" or lease.get("state") != "RESERVED":
                raise ExecutionLifecycleError("spawn rollback requires merely RESERVED WriterLease")
            current["writer_lease"] = None
        current["executions"].remove(execution)
        unit["state"] = "READY"
        unit["accepted_result_ref"] = None
        unit["accepted_execution_id"] = None
        unit["accepted_control_epoch"] = None
        rolled_back.update(copy.deepcopy(execution))

    state.mutate_state(thread_id, mutate, temp_root=temp_root)
    return rolled_back


def _same_child_unit_is_mutable(current: Mapping[str, Any], execution: Mapping[str, Any]) -> None:
    unit = _unit(current, execution["unit_id"])
    if unit["state"] in {"ACCEPTED", "CANCELLED"}:
        raise ExecutionLifecycleError("accepted or cancelled WorkUnit cannot reactivate same child")
    current_execution = state.current_execution_for_unit(current, unit_id=execution["unit_id"])
    if current_execution is None or current_execution.get("execution_id") != execution.get("execution_id"):
        raise ExecutionLifecycleError("superseded execution cannot reactivate same child")


def _validate_target(tool_input: Mapping[str, Any], *, target: str, message_required: bool) -> None:
    if not isinstance(tool_input, Mapping):
        raise ExecutionLifecycleError("native lifecycle tool_input must be an object")
    expected = {"target", "message"} if message_required else {"target"}
    if set(tool_input) != expected or tool_input.get("target") != target:
        raise ExecutionLifecycleError("native lifecycle tool_input does not match ExecutionBinding")
    if message_required and (
        not isinstance(tool_input.get("message"), str) or not tool_input["message"].strip()
    ):
        raise ExecutionLifecycleError("same-child activation requires non-empty message")


def _reserve_writer_for_reactivation(
    current: dict[str, Any], execution: Mapping[str, Any], lease_id: str
) -> None:
    existing = current.get("writer_lease")
    if isinstance(existing, dict) and existing.get("state") in state.WRITER_BLOCKING_STATES:
        if existing.get("owner_kind") != "execution" or existing.get("owner_id") != execution["execution_id"]:
            raise ExecutionLifecycleError("canonical workspace already has another managed writer")
        if existing.get("state") not in {"RESERVED", "HELD"}:
            raise ExecutionLifecycleError("existing WriterLease cannot reactivate this execution")
        return
    epoch = 1 if existing is None else existing["lease_epoch"] + 1
    current["writer_lease"] = {
        "lease_id": lease_id,
        "lease_epoch": epoch,
        "workspace_id": state.CANONICAL_WORKSPACE_ID,
        "unit_id": execution["unit_id"],
        "owner_kind": "execution",
        "owner_id": execution["execution_id"],
        "state": "RESERVED",
    }


def prepare_same_child_followup(
    thread_id: str,
    *,
    execution_id: str,
    tool_input: Mapping[str, Any],
    writer_lease_id: str | None = None,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Advance the same execution generation for its single focused correction."""
    prepared: dict[str, Any] = {}

    def mutate(current: dict[str, Any]) -> None:
        execution = _execution(current, execution_id)
        _same_child_unit_is_mutable(current, execution)
        if execution["lifecycle"] != "COMPLETED":
            raise ExecutionLifecycleError("same-child FOLLOWUP requires COMPLETED execution")
        if execution["followup_count"] >= 1:
            raise ExecutionLifecycleError("focused same-child followup budget is exhausted")
        _validate_target(tool_input, target=execution["native_task_name"], message_required=True)
        if execution["granted_authority"] != "none":
            lease_id = writer_lease_id
            if not isinstance(lease_id, str) or not lease_id.strip():
                lease_id = f"lease-followup-{execution_id}-{execution['control_epoch'] + 1}"
            _reserve_writer_for_reactivation(current, execution, lease_id)
        execution["control_epoch"] += 1
        execution["followup_count"] = 1
        execution["lifecycle"] = "SPAWN_PENDING"
        execution["failure_origin"] = "none"
        execution["blocker"] = "none"
        execution["quarantine_reason"] = None
        unit = _unit(current, execution["unit_id"])
        unit["state"] = "EXECUTING"
        prepared.update(
            {
                "operation": "FOLLOWUP",
                "execution_id": execution_id,
                "tool_input": copy.deepcopy(dict(tool_input)),
                "control_epoch": execution["control_epoch"],
            }
        )

    persisted = state.mutate_state(thread_id, mutate, temp_root=temp_root)
    prepared["observation_basis"] = state.observation_basis(
        persisted, execution_id=execution_id
    )
    return prepared


def prepare_same_child_continue(
    thread_id: str,
    *,
    execution_id: str,
    tool_input: Mapping[str, Any],
    writer_lease_id: str | None = None,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    prepared: dict[str, Any] = {}

    def mutate(current: dict[str, Any]) -> None:
        execution = _execution(current, execution_id)
        _same_child_unit_is_mutable(current, execution)
        if execution["lifecycle"] != "INTERRUPTED":
            raise ExecutionLifecycleError("CONTINUE requires INTERRUPTED same child")
        _validate_target(tool_input, target=execution["native_task_name"], message_required=True)
        if execution["granted_authority"] != "none":
            lease_id = writer_lease_id
            if not isinstance(lease_id, str) or not lease_id.strip():
                lease_id = f"lease-continue-{execution_id}-{execution['control_epoch'] + 1}"
            _reserve_writer_for_reactivation(current, execution, lease_id)
        execution["control_epoch"] += 1
        execution["lifecycle"] = "SPAWN_PENDING"
        execution["failure_origin"] = "none"
        execution["blocker"] = "none"
        execution["quarantine_reason"] = None
        unit = _unit(current, execution["unit_id"])
        unit["state"] = "EXECUTING"
        prepared.update(
            {
                "operation": "CONTINUE",
                "execution_id": execution_id,
                "tool_input": copy.deepcopy(dict(tool_input)),
                "control_epoch": execution["control_epoch"],
            }
        )

    persisted = state.mutate_state(thread_id, mutate, temp_root=temp_root)
    prepared["observation_basis"] = state.observation_basis(
        persisted, execution_id=execution_id
    )
    return prepared


def prepare_interrupt(
    thread_id: str,
    *,
    execution_id: str,
    tool_input: Mapping[str, Any],
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Advance generation and revoke writer authority before native interrupt."""
    prepared: dict[str, Any] = {}

    def mutate(current: dict[str, Any]) -> None:
        execution = _execution(current, execution_id)
        if execution["lifecycle"] != "RUNNING":
            raise ExecutionLifecycleError("INTERRUPT requires RUNNING execution")
        _validate_target(tool_input, target=execution["native_task_name"], message_required=False)
        if execution["granted_authority"] != "none":
            lease = current.get("writer_lease")
            if not isinstance(lease, dict):
                raise ExecutionLifecycleError("writing INTERRUPT requires WriterLease")
            if lease.get("owner_kind") != "execution" or lease.get("owner_id") != execution_id:
                raise ExecutionLifecycleError("writing INTERRUPT requires execution-owned WriterLease")
            if lease.get("state") not in {"RESERVED", "HELD", "REVOKING"}:
                raise ExecutionLifecycleError("writing INTERRUPT requires active WriterLease")
            lease["state"] = "REVOKING"
        execution["control_epoch"] += 1
        prepared.update(
            {
                "operation": "INTERRUPT",
                "execution_id": execution_id,
                "tool_input": copy.deepcopy(dict(tool_input)),
                "control_epoch": execution["control_epoch"],
            }
        )

    persisted = state.mutate_state(thread_id, mutate, temp_root=temp_root)
    prepared["observation_basis"] = state.observation_basis(
        persisted, execution_id=execution_id
    )
    return prepared


def mark_execution_unknown(
    thread_id: str,
    *,
    execution_id: str,
    reason: str = "native_lifecycle_ambiguous",
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Fail closed after a native call whose materialization or lifecycle is ambiguous."""
    changed: dict[str, Any] = {}

    def mutate(current: dict[str, Any]) -> None:
        execution = _execution(current, execution_id)
        execution["lifecycle"] = "UNKNOWN"
        execution["failure_origin"] = "runtime_ambiguous"
        execution["blocker"] = "investigation"
        execution["quarantine_reason"] = reason
        lease = current.get("writer_lease")
        if (
            execution["granted_authority"] != "none"
            and isinstance(lease, dict)
            and lease.get("owner_kind") == "execution"
            and lease.get("owner_id") == execution_id
            and lease.get("state") != "RELEASED"
        ):
            lease["state"] = "UNKNOWN"
        changed.update(copy.deepcopy(execution))

    state.mutate_state(thread_id, mutate, temp_root=temp_root)
    return changed


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
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    return writer.transfer_settled_execution_writer_to_main(
        thread_id,
        execution_id=execution_id,
        lease_id=old_lease_id,
        lease_epoch=old_lease_epoch,
        main_lease_id=main_lease_id,
        temp_root=temp_root,
    )


def runtime_temp_root() -> Path | None:
    raw = os.environ.get("SUBAGENTS_DISPATCH_TEMP_ROOT")
    if raw is None or not raw.strip():
        return None
    return Path(raw)
