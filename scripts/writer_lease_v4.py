#!/usr/bin/env python3
"""V4 WriterLease facade with authoritative Host-observation settlement.

The stable reservation/revocation primitives live in ``writer_lease_v4_core``.
RC3 owns Host observation provenance and settlement authority in this facade so
ordinary callers cannot manufacture WriterLease release evidence from booleans,
digests, or lifecycle strings.
"""

from __future__ import annotations

import copy
import os
from typing import Any, Mapping

import dispatch_state_v4 as state
import writer_lease_v4_core as _core


WriterLeaseError = _core.WriterLeaseError
StaleObservation = _core.StaleObservation
SETTLED_EXECUTION_STATES = _core.SETTLED_EXECUTION_STATES
AUTHORITATIVE_OBSERVATION_SOURCE = "post_tool_use:list_agents"


def _execution(current: Mapping[str, Any], execution_id: str) -> dict[str, Any]:
    return _core._execution(current, execution_id)


def _unit(current: Mapping[str, Any], unit_id: str) -> dict[str, Any]:
    return _core._unit(current, unit_id)


def _ack_event(current: Mapping[str, Any], *, tool_use_id: str, control_id: str) -> Mapping[str, Any]:
    matches = [
        event
        for event in current.get("accounting_refs", [])
        if isinstance(event, Mapping)
        and event.get("kind") == "control_ack"
        and event.get("control_id") == control_id
        and event.get("tool_use_id") == tool_use_id
    ]
    if len(matches) != 1:
        raise WriterLeaseError("WriterLease transition lacks exact Host control acknowledgement")
    return matches[0]


def confirm_execution_writer_activation(
    thread_id: str,
    *,
    execution_id: str,
    lease_id: str,
    lease_epoch: int,
    control_id: str,
    tool_use_id: str,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Verify the exact control-bound ACK and preserve the HELD WriterLease."""
    held: dict[str, Any] = {}

    def mutate(current: dict[str, Any]) -> None:
        _execution(current, execution_id)
        _ack_event(current, tool_use_id=tool_use_id, control_id=control_id)
        lease = current.get("writer_lease")
        if not isinstance(lease, dict):
            raise WriterLeaseError("writer activation requires WriterLease")
        if (
            lease.get("lease_id") != lease_id
            or lease.get("lease_epoch") != lease_epoch
            or lease.get("owner_kind") != "execution"
            or lease.get("owner_id") != execution_id
        ):
            raise WriterLeaseError("writer activation uses stale lease identity")
        if lease["state"] == "RESERVED":
            lease["state"] = "HELD"
        elif lease["state"] != "HELD":
            raise WriterLeaseError("writer activation requires RESERVED or HELD lease")
        held.update(copy.deepcopy(lease))

    state.mutate_state(thread_id, mutate, temp_root=temp_root)
    return held


def _observation_ref(
    *,
    execution_id: str,
    control_epoch: int,
    lease_epoch: int | None,
    lifecycle: str,
    tool_use_id: str,
) -> str:
    lease_text = "none" if lease_epoch is None else str(lease_epoch)
    return (
        f"host-observation:{execution_id}:{control_epoch}:{lease_text}:"
        f"{lifecycle}:{tool_use_id}"
    )


def _normalized_host_lifecycle(host_state: str) -> str:
    if host_state in state.HOST_UNCERTAIN_STATES:
        return "UNKNOWN"
    return state.HOST_STATE_MAP.get(host_state, "UNKNOWN")


def _same_epoch_observation_regresses(existing: str, incoming: str) -> bool:
    if existing == "UNKNOWN":
        return False
    if existing == "CLOSED":
        return incoming != "CLOSED"
    if existing in {"COMPLETED", "FAILED"}:
        return incoming not in {existing, "CLOSED", "UNKNOWN"}
    if existing == "INTERRUPTED":
        return incoming in {"SPAWN_PENDING", "RUNNING"}
    return False


def _lifecycle_is_proven_in_current_epoch(
    current: Mapping[str, Any], execution: Mapping[str, Any]
) -> bool:
    return any(
        isinstance(event, Mapping)
        and event.get("kind") == "host_observation"
        and event.get("source") == AUTHORITATIVE_OBSERVATION_SOURCE
        and event.get("execution_id") == execution["execution_id"]
        and event.get("control_epoch") == execution["control_epoch"]
        and event.get("lifecycle") == execution["lifecycle"]
        for event in current.get("accounting_refs", [])
    )


def persist_authoritative_host_observation(
    thread_id: str,
    *,
    basis: Mapping[str, Any],
    host_state: str,
    turn_id: str,
    tool_use_id: str,
    agent_name: str,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Persist one list_agents PostToolUse observation with Hook provenance."""
    for label, value in (
        ("turn_id", turn_id),
        ("tool_use_id", tool_use_id),
        ("agent_name", agent_name),
    ):
        if not isinstance(value, str) or not value.strip():
            raise WriterLeaseError(f"authoritative Host observation requires {label}")
    outcome: dict[str, Any] = {}

    def mutate(current: dict[str, Any]) -> None:
        execution_id = basis.get("execution_id") if isinstance(basis, Mapping) else None
        if not isinstance(execution_id, str):
            raise StaleObservation("Host observation basis has no execution identity")
        current_basis = state.observation_basis(current, execution_id=execution_id)
        if dict(current_basis) != dict(basis):
            raise StaleObservation("Host observation basis is stale")
        execution_before = _execution(current, execution_id)
        expected_name = f"/root/{execution_before['native_task_name']}"
        if agent_name != expected_name:
            raise WriterLeaseError("Host observation agent name does not match ExecutionBinding")
        existing = execution_before["lifecycle"]
        incoming = _normalized_host_lifecycle(host_state)
        if (
            _lifecycle_is_proven_in_current_epoch(current, execution_before)
            and _same_epoch_observation_regresses(existing, incoming)
        ):
            raise StaleObservation("Host observation regresses lifecycle within one control epoch")
        reconciled = state.reconcile_execution_observation(
            current,
            basis=basis,
            host_state=host_state,
        )
        if reconciled["reconcile_status"] == "stale":
            raise StaleObservation("Host observation became stale")
        next_state = reconciled["state"]
        execution = _execution(next_state, execution_id)
        lifecycle = execution["lifecycle"]
        if lifecycle == "RUNNING":
            unit = _unit(next_state, execution["unit_id"])
            if unit["state"] in {"READY", "REJECTED", "RESULT_READY", "VERIFYING"}:
                unit["state"] = "EXECUTING"
                unit["accepted_result_ref"] = None
                unit["accepted_execution_id"] = None
                unit["accepted_control_epoch"] = None
        ref = _observation_ref(
            execution_id=execution_id,
            control_epoch=basis["control_epoch"],
            lease_epoch=basis.get("lease_epoch"),
            lifecycle=lifecycle,
            tool_use_id=tool_use_id,
        )
        duplicate = any(event.get("ref") == ref for event in next_state["accounting_refs"])
        if not duplicate:
            next_state["accounting_refs"].append(
                {
                    "ref": ref,
                    "kind": "host_observation",
                    "source": AUTHORITATIVE_OBSERVATION_SOURCE,
                    "execution_id": execution_id,
                    "control_epoch": basis["control_epoch"],
                    "lease_epoch": basis.get("lease_epoch"),
                    "lifecycle": lifecycle,
                    "turn_id": turn_id,
                    "tool_use_id": tool_use_id,
                    "agent_name": agent_name,
                }
            )
        current.clear()
        current.update(next_state)
        outcome.update(
            {
                "reconcile_status": "noop" if duplicate else reconciled["reconcile_status"],
                "lifecycle": lifecycle,
                "proof_ref": ref,
                "idempotent": duplicate,
            }
        )

    try:
        persisted = state.mutate_state(thread_id, mutate, temp_root=temp_root)
    except StaleObservation:
        current = state.load_state(thread_id, temp_root=temp_root)
        return {"reconcile_status": "stale", "state": current}
    outcome["state"] = persisted
    return outcome


def _observation_receipt_present(current: Mapping[str, Any], tool_use_id: str) -> bool:
    """Require an exact retained receipt; probabilistic history never grants authority."""
    return any(
        isinstance(event, Mapping)
        and event.get("kind") == "host_observation_receipt"
        and event.get("tool_use_id") == tool_use_id
        for event in current.get("accounting_refs", [])
    )


def _has_current_observation_proof(
    current: Mapping[str, Any], *, execution: Mapping[str, Any], lease_epoch: int
) -> bool:
    return any(
        isinstance(event, Mapping)
        and event.get("kind") == "host_observation"
        and event.get("source") == AUTHORITATIVE_OBSERVATION_SOURCE
        and event.get("execution_id") == execution["execution_id"]
        and event.get("control_epoch") == execution["control_epoch"]
        and event.get("lease_epoch") == lease_epoch
        and event.get("lifecycle") == execution["lifecycle"]
        and isinstance(event.get("turn_id"), str)
        and bool(event.get("turn_id"))
        and isinstance(event.get("tool_use_id"), str)
        and bool(event.get("tool_use_id"))
        and _observation_receipt_present(current, event["tool_use_id"])
        for event in current.get("accounting_refs", [])
    )


def _verify_settlement(
    current: Mapping[str, Any],
    *,
    execution_id: str,
    lease_id: str,
    lease_epoch: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    execution = _execution(current, execution_id)
    lease = current.get("writer_lease")
    if not isinstance(lease, dict):
        raise WriterLeaseError("writer settlement requires WriterLease")
    if (
        lease.get("lease_id") != lease_id
        or lease.get("lease_epoch") != lease_epoch
        or lease.get("owner_kind") != "execution"
        or lease.get("owner_id") != execution_id
    ):
        raise WriterLeaseError("writer settlement uses stale lease identity")
    if lease["state"] == "UNKNOWN":
        raise WriterLeaseError("UNKNOWN WriterLease cannot be released or transferred")
    if lease["state"] not in {"HELD", "REVOKING"}:
        raise WriterLeaseError("writer settlement requires HELD or REVOKING lease")
    if execution["lifecycle"] not in SETTLED_EXECUTION_STATES:
        raise WriterLeaseError("writer execution is not settled")
    if any(
        control["execution_id"] == execution_id
        and control["state"] in state.UNRESOLVED_CONTROL_STATES
        for control in current["pending_controls"]
    ):
        raise WriterLeaseError("writer settlement is blocked by unresolved PendingControl")
    if not _has_current_observation_proof(
        current, execution=execution, lease_epoch=lease_epoch
    ):
        raise WriterLeaseError(
            "writer settlement lacks exact authoritative current-epoch list_agents observation receipt"
        )
    return execution, lease


def release_settled_execution_writer(
    thread_id: str,
    *,
    execution_id: str,
    lease_id: str,
    lease_epoch: int,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    released: dict[str, Any] = {}

    def mutate(current: dict[str, Any]) -> None:
        _, lease = _verify_settlement(
            current,
            execution_id=execution_id,
            lease_id=lease_id,
            lease_epoch=lease_epoch,
        )
        lease["state"] = "RELEASED"
        released.update(copy.deepcopy(lease))

    state.mutate_state(thread_id, mutate, temp_root=temp_root)
    return released


def transfer_settled_execution_writer_to_main(
    thread_id: str,
    *,
    execution_id: str,
    lease_id: str,
    lease_epoch: int,
    main_lease_id: str,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Atomically settle the observed writer and acquire Main without a gap."""
    if not isinstance(main_lease_id, str) or not main_lease_id.strip():
        raise WriterLeaseError("main_lease_id must be non-empty")
    transferred: dict[str, Any] = {}

    def mutate(current: dict[str, Any]) -> None:
        execution, _ = _verify_settlement(
            current,
            execution_id=execution_id,
            lease_id=lease_id,
            lease_epoch=lease_epoch,
        )
        new_lease = {
            "lease_id": main_lease_id,
            "lease_epoch": lease_epoch + 1,
            "workspace_id": state.CANONICAL_WORKSPACE_ID,
            "unit_id": execution["unit_id"],
            "owner_kind": "main",
            "owner_id": current["root_session_id"],
            "state": "HELD",
        }
        current["writer_lease"] = new_lease
        transferred.update(copy.deepcopy(new_lease))

    state.mutate_state(thread_id, mutate, temp_root=temp_root)
    return transferred


# Re-export the stable WriterLease primitives while excluding RC2 authority paths
# that the RC3 facade replaces above.
_EXCLUDED = {
    "persist_host_observation",
    "release_settled_execution_writer",
    "transfer_settled_execution_writer_to_main",
    "confirm_execution_writer_activation",
    "_ack_event",
    "_verify_settlement",
    "_validate_guard_coverage_proof",
    "_has_current_observation_proof",
}
for _name in dir(_core):
    if not _name.startswith("__") and _name not in _EXCLUDED and _name not in globals():
        globals()[_name] = getattr(_core, _name)
