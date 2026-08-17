#!/usr/bin/env python3
"""V4 WriterLease and epoch-bound Host observation settlement.

WriterLease is an orchestration-level mutual-exclusion permit for the canonical
workspace. It does not claim to be an operating-system or filesystem lock.
"""

from __future__ import annotations

import copy
import os
import re
from pathlib import Path
from typing import Any, Mapping

import dispatch_state_v4 as state


SETTLED_EXECUTION_STATES = {"INTERRUPTED", "COMPLETED", "FAILED", "CLOSED"}
GUARD_COVERAGE_FIELDS = {
    "schema_version",
    "session_id",
    "manifest_sha256",
    "trusted_current_definition",
    "pre_tool_use",
    "post_tool_use",
    "subagent_stop_veto",
    "evidence_ref",
}
HEX64 = re.compile(r"[0-9a-f]{64}")


class WriterLeaseError(RuntimeError):
    """A WriterLease transition would weaken the V4 single-writer invariant."""


class StaleObservation(RuntimeError):
    """A Host observation was captured against an older execution generation."""


def _execution(current: Mapping[str, Any], execution_id: str) -> dict[str, Any]:
    matches = [
        item
        for item in current.get("executions", [])
        if isinstance(item, dict) and item.get("execution_id") == execution_id
    ]
    if len(matches) != 1:
        raise WriterLeaseError("execution_id does not resolve exactly once")
    return matches[0]


def _unit(current: Mapping[str, Any], unit_id: str) -> dict[str, Any]:
    matches = [
        item
        for item in current.get("work_units", [])
        if isinstance(item, dict) and item.get("unit_id") == unit_id
    ]
    if len(matches) != 1:
        raise WriterLeaseError("unit_id does not resolve exactly once")
    return matches[0]


def _next_lease_epoch(current: Mapping[str, Any]) -> int:
    lease = current.get("writer_lease")
    if lease is None:
        return 1
    if not isinstance(lease, Mapping):
        raise WriterLeaseError("writer_lease is malformed")
    if lease.get("state") in state.WRITER_BLOCKING_STATES:
        raise WriterLeaseError("canonical workspace already has a blocking WriterLease")
    epoch = lease.get("lease_epoch")
    if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 1:
        raise WriterLeaseError("writer_lease has invalid lease_epoch")
    return epoch + 1


def ensure_execution_writer_reserved(
    thread_id: str,
    *,
    execution_id: str,
    lease_id: str,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Reserve the canonical writer before a writing Host activation can occur."""
    if not isinstance(lease_id, str) or not lease_id.strip():
        raise WriterLeaseError("lease_id must be non-empty")
    reserved: dict[str, Any] = {}

    def mutate(current: dict[str, Any]) -> None:
        execution = _execution(current, execution_id)
        if execution["granted_authority"] == "none":
            raise WriterLeaseError("read-only ExecutionBinding cannot reserve WriterLease")
        existing = current.get("writer_lease")
        if isinstance(existing, dict) and existing.get("state") in state.WRITER_BLOCKING_STATES:
            if existing.get("owner_kind") != "execution" or existing.get("owner_id") != execution_id:
                raise WriterLeaseError("canonical workspace already has another managed writer")
            if existing.get("state") not in {"RESERVED", "HELD"}:
                raise WriterLeaseError("existing writer lease cannot be reused for activation")
            reserved.update(copy.deepcopy(existing))
            return
        lease = {
            "lease_id": lease_id,
            "lease_epoch": _next_lease_epoch(current),
            "workspace_id": state.CANONICAL_WORKSPACE_ID,
            "unit_id": execution["unit_id"],
            "owner_kind": "execution",
            "owner_id": execution_id,
            "state": "RESERVED",
        }
        current["writer_lease"] = lease
        reserved.update(copy.deepcopy(lease))

    state.mutate_state(thread_id, mutate, temp_root=temp_root)
    return reserved


def begin_revoke_execution_writer(
    thread_id: str,
    *,
    execution_id: str,
    lease_id: str,
    lease_epoch: int,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Enter REVOKING before the Host interrupt request is authorized."""
    revoked: dict[str, Any] = {}

    def mutate(current: dict[str, Any]) -> None:
        execution = _execution(current, execution_id)
        if execution["lifecycle"] != "RUNNING":
            raise WriterLeaseError("writer revoke requires RUNNING execution")
        lease = current.get("writer_lease")
        if not isinstance(lease, dict):
            raise WriterLeaseError("writer revoke requires WriterLease")
        if (
            lease.get("lease_id") != lease_id
            or lease.get("lease_epoch") != lease_epoch
            or lease.get("owner_kind") != "execution"
            or lease.get("owner_id") != execution_id
        ):
            raise WriterLeaseError("writer revoke uses stale lease identity")
        if lease["state"] not in {"RESERVED", "HELD", "REVOKING"}:
            raise WriterLeaseError("writer revoke requires RESERVED or HELD lease")
        lease["state"] = "REVOKING"
        revoked.update(copy.deepcopy(lease))

    state.mutate_state(thread_id, mutate, temp_root=temp_root)
    return revoked


def mark_execution_writer_unknown(
    thread_id: str,
    *,
    execution_id: str,
    lease_id: str,
    lease_epoch: int,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    quarantined: dict[str, Any] = {}

    def mutate(current: dict[str, Any]) -> None:
        lease = current.get("writer_lease")
        if not isinstance(lease, dict):
            raise WriterLeaseError("writer quarantine requires WriterLease")
        if (
            lease.get("lease_id") != lease_id
            or lease.get("lease_epoch") != lease_epoch
            or lease.get("owner_kind") != "execution"
            or lease.get("owner_id") != execution_id
        ):
            raise WriterLeaseError("writer quarantine uses stale lease identity")
        if lease["state"] == "RELEASED":
            raise WriterLeaseError("released lease cannot become UNKNOWN")
        lease["state"] = "UNKNOWN"
        quarantined.update(copy.deepcopy(lease))

    state.mutate_state(thread_id, mutate, temp_root=temp_root)
    return quarantined


def _ack_event(current: Mapping[str, Any], *, tool_use_id: str, control_id: str) -> Mapping[str, Any]:
    ref = f"control-ack:{tool_use_id}"
    matches = [
        event
        for event in current.get("accounting_refs", [])
        if isinstance(event, Mapping)
        and event.get("ref") == ref
        and event.get("kind") == "control_ack"
        and event.get("control_id") == control_id
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
    """Verify the exact ACK and preserve the execution-owned HELD WriterLease."""
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
    *, execution_id: str, control_epoch: int, lease_epoch: int | None, lifecycle: str
) -> str:
    lease_text = "none" if lease_epoch is None else str(lease_epoch)
    return f"host-observation:{execution_id}:{control_epoch}:{lease_text}:{lifecycle}"


def _normalized_host_lifecycle(host_state: str) -> str:
    if host_state in state.HOST_UNCERTAIN_STATES:
        return "UNKNOWN"
    return state.HOST_STATE_MAP.get(host_state, "UNKNOWN")


def _same_epoch_observation_regresses(existing: str, incoming: str) -> bool:
    """Classify lifecycle movement that is invalid after current-generation proof exists."""
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
        and event.get("execution_id") == execution["execution_id"]
        and event.get("control_epoch") == execution["control_epoch"]
        and event.get("lifecycle") == execution["lifecycle"]
        for event in current.get("accounting_refs", [])
    )


def persist_host_observation(
    thread_id: str,
    *,
    basis: Mapping[str, Any],
    host_state: str,
    agent_id: str | None = None,
    failure_origin: str = "tool_failure",
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Atomically reconcile one fresh Host snapshot and persist its epoch-bound proof."""
    outcome: dict[str, Any] = {}

    def mutate(current: dict[str, Any]) -> None:
        execution_id = basis.get("execution_id") if isinstance(basis, Mapping) else None
        if not isinstance(execution_id, str):
            raise StaleObservation("Host observation basis has no execution identity")
        current_basis = state.observation_basis(current, execution_id=execution_id)
        if dict(current_basis) != dict(basis):
            raise StaleObservation("Host observation basis is stale")
        current_execution = _execution(current, execution_id)
        existing = current_execution["lifecycle"]
        incoming = _normalized_host_lifecycle(host_state)
        if (
            _lifecycle_is_proven_in_current_epoch(current, current_execution)
            and _same_epoch_observation_regresses(existing, incoming)
        ):
            raise StaleObservation("Host observation regresses lifecycle within one control epoch")
        reconciled = state.reconcile_execution_observation(
            current,
            basis=basis,
            host_state=host_state,
            agent_id=agent_id,
            failure_origin=failure_origin,
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
        )
        if not any(event.get("ref") == ref for event in next_state["accounting_refs"]):
            next_state["accounting_refs"].append(
                {
                    "ref": ref,
                    "kind": "host_observation",
                    "execution_id": execution_id,
                    "control_epoch": basis["control_epoch"],
                    "lease_epoch": basis.get("lease_epoch"),
                    "lifecycle": lifecycle,
                }
            )
        current.clear()
        current.update(next_state)
        outcome.update(
            {
                "reconcile_status": reconciled["reconcile_status"],
                "lifecycle": lifecycle,
                "proof_ref": ref,
            }
        )

    try:
        persisted = state.mutate_state(thread_id, mutate, temp_root=temp_root)
    except StaleObservation:
        current = state.load_state(thread_id, temp_root=temp_root)
        return {"reconcile_status": "stale", "state": current}
    outcome["state"] = persisted
    return outcome


def _has_current_observation_proof(
    current: Mapping[str, Any], *, execution: Mapping[str, Any], lease_epoch: int
) -> bool:
    ref = _observation_ref(
        execution_id=execution["execution_id"],
        control_epoch=execution["control_epoch"],
        lease_epoch=lease_epoch,
        lifecycle=execution["lifecycle"],
    )
    return any(
        isinstance(event, Mapping)
        and event.get("ref") == ref
        and event.get("kind") == "host_observation"
        for event in current.get("accounting_refs", [])
    )


def _validate_guard_coverage_proof(
    current: Mapping[str, Any], proof: Mapping[str, Any] | Any
) -> None:
    if not isinstance(proof, Mapping):
        raise WriterLeaseError("writer settlement requires structured Guard coverage proof")
    if set(proof) != GUARD_COVERAGE_FIELDS:
        raise WriterLeaseError("Guard coverage proof has invalid fields")
    if proof.get("schema_version") != "4.0":
        raise WriterLeaseError("Guard coverage proof has unsupported schema_version")
    if proof.get("session_id") != current.get("root_session_id"):
        raise WriterLeaseError("Guard coverage proof is bound to another root session")
    digest = proof.get("manifest_sha256")
    if not isinstance(digest, str) or HEX64.fullmatch(digest) is None:
        raise WriterLeaseError("Guard coverage proof has invalid manifest SHA-256")
    for field in (
        "trusted_current_definition",
        "pre_tool_use",
        "post_tool_use",
        "subagent_stop_veto",
    ):
        if proof.get(field) is not True:
            raise WriterLeaseError(f"Guard coverage proof does not establish {field}")
    evidence_ref = proof.get("evidence_ref")
    if not isinstance(evidence_ref, str) or not evidence_ref.strip():
        raise WriterLeaseError("Guard coverage proof requires evidence_ref")


def _verify_settlement(
    current: Mapping[str, Any],
    *,
    execution_id: str,
    lease_id: str,
    lease_epoch: int,
    guard_coverage: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_guard_coverage_proof(current, guard_coverage)
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
        raise WriterLeaseError("writer settlement lacks fresh current-epoch Host observation proof")
    return execution, lease


def release_settled_execution_writer(
    thread_id: str,
    *,
    execution_id: str,
    lease_id: str,
    lease_epoch: int,
    guard_coverage: Mapping[str, Any],
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    released: dict[str, Any] = {}

    def mutate(current: dict[str, Any]) -> None:
        _, lease = _verify_settlement(
            current,
            execution_id=execution_id,
            lease_id=lease_id,
            lease_epoch=lease_epoch,
            guard_coverage=guard_coverage,
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
    guard_coverage: Mapping[str, Any],
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Atomically settle the old writer and acquire Main without an unleased gap."""
    if not isinstance(main_lease_id, str) or not main_lease_id.strip():
        raise WriterLeaseError("main_lease_id must be non-empty")
    transferred: dict[str, Any] = {}

    def mutate(current: dict[str, Any]) -> None:
        execution, _ = _verify_settlement(
            current,
            execution_id=execution_id,
            lease_id=lease_id,
            lease_epoch=lease_epoch,
            guard_coverage=guard_coverage,
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


def acquire_main_writer(
    thread_id: str,
    *,
    unit_id: str,
    lease_id: str,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    if not isinstance(lease_id, str) or not lease_id.strip():
        raise WriterLeaseError("lease_id must be non-empty")
    acquired: dict[str, Any] = {}

    def mutate(current: dict[str, Any]) -> None:
        _unit(current, unit_id)
        epoch = _next_lease_epoch(current)
        lease = {
            "lease_id": lease_id,
            "lease_epoch": epoch,
            "workspace_id": state.CANONICAL_WORKSPACE_ID,
            "unit_id": unit_id,
            "owner_kind": "main",
            "owner_id": current["root_session_id"],
            "state": "HELD",
        }
        current["writer_lease"] = lease
        acquired.update(copy.deepcopy(lease))

    state.mutate_state(thread_id, mutate, temp_root=temp_root)
    return acquired


def release_main_writer(
    thread_id: str,
    *,
    lease_id: str,
    lease_epoch: int,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    released: dict[str, Any] = {}

    def mutate(current: dict[str, Any]) -> None:
        lease = current.get("writer_lease")
        if not isinstance(lease, dict):
            raise WriterLeaseError("Main release requires WriterLease")
        if (
            lease.get("lease_id") != lease_id
            or lease.get("lease_epoch") != lease_epoch
            or lease.get("owner_kind") != "main"
            or lease.get("owner_id") != current["root_session_id"]
            or lease.get("state") != "HELD"
        ):
            raise WriterLeaseError("Main release uses stale or invalid lease identity")
        lease["state"] = "RELEASED"
        released.update(copy.deepcopy(lease))

    state.mutate_state(thread_id, mutate, temp_root=temp_root)
    return released


def runtime_temp_root() -> Path | None:
    raw = os.environ.get("SUBAGENTS_DISPATCH_TEMP_ROOT")
    if raw is None or not raw.strip():
        return None
    return Path(raw)
