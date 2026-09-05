#!/usr/bin/env python3
"""Native Core ExecutionBinding lifecycle helpers.

Lifecycle authorization is Main-owned and lifecycle truth is Host-owned. These
helpers mutate only project state. They do not depend on Plugin Hook callbacks,
PendingControl, synthetic acknowledgements, or Host tool-use identifiers.
"""

from __future__ import annotations

import copy
import hashlib
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

import dispatch_state_v4 as state
import managed_execution_v4 as managed_execution
import policy as policy_contract
import writer_lease_v4 as writer


_SETTLED_EXECUTION_STATES = {"COMPLETED", "FAILED", "CLOSED"}
_HISTORY_KIND = "execution_history"
_RECOVERY_BASIS_KIND = "recovery_basis"


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


def _history(current: Mapping[str, Any], unit_id: str) -> dict[str, Any] | None:
    matches = [
        event
        for event in current.get("accounting_refs", [])
        if isinstance(event, dict)
        and event.get("kind") == _HISTORY_KIND
        and event.get("unit_id") == unit_id
    ]
    if len(matches) > 1:
        raise ExecutionLifecycleError("WorkUnit execution history is ambiguous")
    return matches[0] if matches else None


def _retained_executions(current: Mapping[str, Any], unit_id: str) -> list[dict[str, Any]]:
    return [
        item
        for item in current.get("executions", [])
        if isinstance(item, dict) and item.get("unit_id") == unit_id
    ]


def _next_attempt_no(current: Mapping[str, Any], unit_id: str) -> int:
    retained = _retained_executions(current, unit_id)
    greatest = max((int(item.get("attempt_no", 0)) for item in retained), default=0)
    history = _history(current, unit_id)
    if history is not None:
        greatest = max(greatest, int(history["max_attempt_no"]))
    return greatest + 1


def _prior_execution_basis_refs(current: Mapping[str, Any], unit_id: str) -> set[str]:
    refs = {
        str(item["execution_basis_ref"])
        for item in _retained_executions(current, unit_id)
        if _nonempty(item.get("execution_basis_ref"))
    }
    history = _history(current, unit_id)
    if history is not None and _nonempty(history.get("last_basis_ref")):
        refs.add(str(history["last_basis_ref"]))
    return refs


def _compact_settled_execution_history(current: dict[str, Any], unit_id: str) -> None:
    """Retain the newest execution and summarize older safely settled attempts."""
    retained = sorted(
        _retained_executions(current, unit_id),
        key=lambda item: int(item.get("attempt_no", 0)),
    )
    if len(retained) <= 1:
        return

    lease = current.get("writer_lease")
    pinned_execution_id = (
        lease.get("owner_id")
        if isinstance(lease, Mapping)
        and lease.get("owner_kind") == "execution"
        and lease.get("state") == "RELEASED"
        else None
    )
    compacted = [
        item
        for item in retained[:-1]
        if item.get("execution_id") != pinned_execution_id
    ]
    if not compacted:
        return
    if any(item.get("lifecycle") not in _SETTLED_EXECUTION_STATES for item in compacted):
        raise ExecutionLifecycleError("only safely settled historical executions can be compacted")

    last = compacted[-1]
    prior_history = _history(current, unit_id)
    compacted_count = len(compacted)
    if prior_history is not None:
        compacted_count += int(prior_history["compacted_attempts"])

    summary = {
        "ref": f"execution-history:{unit_id}",
        "kind": _HISTORY_KIND,
        "unit_id": unit_id,
        "compacted_attempts": compacted_count,
        "max_attempt_no": int(last["attempt_no"]),
        "last_execution_id": last["execution_id"],
        "last_lifecycle": last["lifecycle"],
        "last_basis_ref": last.get("execution_basis_ref"),
        "last_followup_count": int(last["followup_count"]),
    }

    compacted_ids = {item["execution_id"] for item in compacted}
    remaining_refs = [
        event
        for event in current["accounting_refs"]
        if not (
            isinstance(event, Mapping)
            and (
                (event.get("kind") == _HISTORY_KIND and event.get("unit_id") == unit_id)
                or (
                    event.get("kind") in {"host_observation", _RECOVERY_BASIS_KIND}
                    and event.get("execution_id") in compacted_ids
                )
            )
        )
    ]
    remaining_refs.append(summary)
    current["accounting_refs"] = remaining_refs
    current["executions"] = [
        item for item in current["executions"] if item.get("execution_id") not in compacted_ids
    ]


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


def _require_no_conflicting_writer(current: Mapping[str, Any]) -> None:
    lease = current.get("writer_lease")
    if isinstance(lease, Mapping) and lease.get("state") in state.WRITER_BLOCKING_STATES:
        raise ExecutionLifecycleError(
            "blocking WriterLease must settle before another canonical-workspace execution"
        )


def allocate_execution(
    thread_id: str,
    *,
    unit_id: str,
    execution_id: str,
    native_task_name: str,
    role_id: str,
    reasoning_effort: str | None,
    granted_authority: str,
    granted_write_scope: Sequence[str] = (),
    execution_basis_ref: str | None = None,
    writer_lease_id: str | None = None,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Allocate one evidence-bound fresh activation and reserve writer ownership atomically."""
    try:
        route = policy_contract.resolve_managed_route(
            role_id=role_id,
            reasoning_effort=reasoning_effort,
        )
    except RuntimeError as exc:
        raise ExecutionLifecycleError(str(exc)) from exc
    if not isinstance(execution_id, str) or not execution_id.strip():
        raise ExecutionLifecycleError("execution_id must be non-empty")
    if not isinstance(native_task_name, str) or not native_task_name.strip():
        raise ExecutionLifecycleError("native_task_name must be non-empty")
    if execution_basis_ref is not None and not _nonempty(execution_basis_ref):
        raise ExecutionLifecycleError("execution_basis_ref must be non-empty when supplied")
    model = route["model"]
    agent_type = route["agent_type"]
    selected_effort = route["reasoning_effort"]
    scope = list(granted_write_scope)
    allocated: dict[str, Any] = {}

    def mutate(current: dict[str, Any]) -> None:
        unit = _unit(current, unit_id)
        if any(item["execution_id"] == execution_id for item in current["executions"]):
            raise ExecutionLifecycleError("execution_id is already present")
        if any(item["native_task_name"] == native_task_name for item in current["executions"]):
            raise ExecutionLifecycleError("native_task_name is already present")

        prior = _retained_executions(current, unit_id)
        if not _fresh_execution_state_is_eligible(unit, prior):
            raise ExecutionLifecycleError(
                "fresh execution requires READY work or a safely settled unresolved current execution"
            )
        if any(item["lifecycle"] not in _SETTLED_EXECUTION_STATES for item in prior):
            raise ExecutionLifecycleError("prior fresh attempt is not settled")

        _require_no_conflicting_writer(current)

        attempt_no = _next_attempt_no(current, unit_id)
        basis_ref = execution_basis_ref
        if attempt_no == 1:
            if basis_ref is None:
                basis_ref = f"initial:{execution_id}"
        elif basis_ref is None:
            raise ExecutionLifecycleError("fresh retry requires a new execution_basis_ref")
        if basis_ref in _prior_execution_basis_refs(current, unit_id):
            raise ExecutionLifecycleError(
                "fresh retry execution_basis_ref must differ from retained recovery evidence"
            )

        if granted_authority not in state.MUTATION_AUTHORITIES:
            raise ExecutionLifecycleError("granted_authority is invalid")
        if _authority_rank(granted_authority) > _authority_rank(unit["authority_ceiling"]):
            raise ExecutionLifecycleError("granted authority exceeds WorkUnit ceiling")
        if role_id == "department_director" and granted_authority != "none":
            raise ExecutionLifecycleError("Department Director is semantically read-only")
        if not state.scopes_within(scope, unit["write_scope_ceiling"]):
            raise ExecutionLifecycleError("granted write scope exceeds WorkUnit ceiling")
        if granted_authority == "none" and scope:
            raise ExecutionLifecycleError("read-only execution requires empty write scope")
        if granted_authority == "none" and writer_lease_id is not None:
            raise ExecutionLifecycleError("read-only fresh execution cannot request WriterLease")
        if granted_authority != "none" and (
            not isinstance(writer_lease_id, str) or not writer_lease_id.strip()
        ):
            raise ExecutionLifecycleError("writable fresh execution requires writer_lease_id")

        _compact_settled_execution_history(current, unit_id)

        execution = {
            "execution_id": execution_id,
            "unit_id": unit_id,
            "attempt_no": attempt_no,
            "role_id": role_id,
            "agent_type": agent_type,
            "agent_id": None,
            "native_task_name": native_task_name,
            "model": model,
            "reasoning_effort": selected_effort,
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

        if granted_authority != "none":
            previous_lease = current.get("writer_lease")
            lease_epoch = 1 if previous_lease is None else previous_lease["lease_epoch"] + 1
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
            "managed spawn tool_input does not match role, exact route, fresh-context, or assignment contract"
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


def _followup_basis_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def prepare_same_child_followup(
    thread_id: str,
    *,
    execution_id: str,
    tool_input: Mapping[str, Any],
    correction_basis_ref: str,
    writer_lease_id: str | None = None,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Advance the same execution only for a new, explicit correction basis."""
    if not _nonempty(correction_basis_ref):
        raise ExecutionLifecycleError("FOLLOWUP requires a non-empty correction_basis_ref")
    basis_hash = _followup_basis_hash(correction_basis_ref)
    prepared: dict[str, Any] = {}

    def mutate(current: dict[str, Any]) -> None:
        execution = _execution(current, execution_id)
        _same_child_unit_is_mutable(current, execution)
        if execution["lifecycle"] != "COMPLETED":
            raise ExecutionLifecycleError("same-child FOLLOWUP requires COMPLETED execution")
        _validate_target(tool_input, target=execution["native_task_name"], message_required=True)
        if any(
            isinstance(event, Mapping)
            and event.get("kind") == _RECOVERY_BASIS_KIND
            and event.get("execution_id") == execution_id
            and event.get("action") == "FOLLOWUP"
            and event.get("basis_hash") == basis_hash
            for event in current.get("accounting_refs", [])
        ):
            raise ExecutionLifecycleError("same-child FOLLOWUP correction basis was already used")
        if execution["granted_authority"] != "none":
            lease_id = writer_lease_id
            if not isinstance(lease_id, str) or not lease_id.strip():
                lease_id = f"lease-followup-{execution_id}-{execution['control_epoch'] + 1}"
            _reserve_writer_for_reactivation(current, execution, lease_id)
        execution["control_epoch"] += 1
        execution["followup_count"] += 1
        execution["lifecycle"] = "SPAWN_PENDING"
        execution["failure_origin"] = "none"
        execution["blocker"] = "none"
        execution["quarantine_reason"] = None
        unit = _unit(current, execution["unit_id"])
        unit["state"] = "EXECUTING"
        current["accounting_refs"].append(
            {
                "ref": f"recovery-basis:{execution_id}:FOLLOWUP:{basis_hash}",
                "kind": _RECOVERY_BASIS_KIND,
                "execution_id": execution_id,
                "action": "FOLLOWUP",
                "basis_hash": basis_hash,
                "control_epoch": execution["control_epoch"],
            }
        )
        prepared.update(
            {
                "operation": "FOLLOWUP",
                "execution_id": execution_id,
                "tool_input": copy.deepcopy(dict(tool_input)),
                "control_epoch": execution["control_epoch"],
                "correction_basis_hash": basis_hash,
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
