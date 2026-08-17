#!/usr/bin/env python3
"""V4 state facade with RC3 correctness-bearing truth invariants.

This module owns the V4 schema facade and persisted correctness truth. The
storage/schema implementation lives in ``dispatch_state_v4_core``. This facade
preserves the public V4 state API while making persisted correctness facts at
least as strict as the mutation paths that create them.
"""

from __future__ import annotations

from typing import Any, Mapping

import dispatch_state_v4_core as _core


# Dynamic test loading imports this facade more than once under different module
# names. Preserve one stable pointer to the original schema validator so the
# truth layer does not recursively wrap itself across those imports.
if not hasattr(_core, "_rc3_base_validate_state_payload"):
    _core._rc3_base_validate_state_payload = _core.validate_state_payload
_BASE_VALIDATE_STATE_PAYLOAD = _core._rc3_base_validate_state_payload


def current_execution_for_unit(
    payload: Mapping[str, Any], *, unit_id: str
) -> Mapping[str, Any] | None:
    """Return the unique greatest-attempt ExecutionBinding for one WorkUnit."""
    executions = [
        item
        for item in payload.get("executions", [])
        if isinstance(item, Mapping) and item.get("unit_id") == unit_id
    ]
    if not executions:
        return None
    greatest = max(item.get("attempt_no", 0) for item in executions)
    matches = [item for item in executions if item.get("attempt_no") == greatest]
    if len(matches) != 1:
        raise _core.StatePayloadError(
            f"work unit {unit_id} current execution is ambiguous"
        )
    return matches[0]


def _has_completed_observation(
    state: Mapping[str, Any], *, execution_id: str, control_epoch: int
) -> bool:
    return any(
        isinstance(event, Mapping)
        and event.get("kind") == "host_observation"
        and event.get("execution_id") == execution_id
        and event.get("control_epoch") == control_epoch
        and event.get("lifecycle") == "COMPLETED"
        for event in state.get("accounting_refs", [])
    )


def _validate_acceptance_truth(state: Mapping[str, Any]) -> None:
    unresolved = _core.UNRESOLVED_CONTROL_STATES
    for unit in state.get("work_units", []):
        if not isinstance(unit, Mapping) or unit.get("state") != "ACCEPTED":
            continue
        unit_id = unit["unit_id"]
        producer = current_execution_for_unit(state, unit_id=unit_id)
        if producer is None:
            raise _core.StatePayloadError(
                f"accepted work unit {unit_id} requires a current producing execution"
            )
        if unit.get("accepted_execution_id") != producer.get("execution_id"):
            raise _core.StatePayloadError(
                f"accepted work unit {unit_id} must reference the current execution attempt"
            )
        accepted_epoch = unit.get("accepted_control_epoch")
        if accepted_epoch != producer.get("control_epoch"):
            raise _core.StatePayloadError(
                f"accepted work unit {unit_id} control epoch must match current producer"
            )
        lifecycle = producer.get("lifecycle")
        if lifecycle == "COMPLETED":
            pass
        elif lifecycle == "CLOSED":
            if not _has_completed_observation(
                state,
                execution_id=str(producer["execution_id"]),
                control_epoch=int(accepted_epoch),
            ):
                raise _core.StatePayloadError(
                    f"accepted work unit {unit_id} closed producer lacks prior COMPLETED proof"
                )
        else:
            raise _core.StatePayloadError(
                f"accepted work unit {unit_id} producer must be COMPLETED or proven CLOSED"
            )
        execution_ids = {
            item.get("execution_id")
            for item in state.get("executions", [])
            if isinstance(item, Mapping) and item.get("unit_id") == unit_id
        }
        if any(
            isinstance(control, Mapping)
            and control.get("execution_id") in execution_ids
            and control.get("state") in unresolved
            for control in state.get("pending_controls", [])
        ):
            raise _core.StatePayloadError(
                f"accepted work unit {unit_id} cannot retain unresolved PendingControl"
            )


def validate_state_payload(
    payload: Any,
    *,
    thread_id: str | None = None,
    max_bytes: int = _core.DEFAULT_MAX_BYTES,
) -> dict[str, Any]:
    """Validate schema/storage safety and all RC3 correctness-bearing truths."""
    state = _BASE_VALIDATE_STATE_PAYLOAD(
        payload,
        thread_id=thread_id,
        max_bytes=max_bytes,
    )
    _validate_acceptance_truth(state)
    return state


# Core functions resolve their module-global ``validate_state_payload`` at call
# time. Point that name at the facade validator so load/write/mutate/reconcile
# paths cannot bypass the RC3 truth kernel.
_core.validate_state_payload = validate_state_payload

# Preserve the established dispatch_state_v4 public surface for existing callers.
for _name in dir(_core):
    if not _name.startswith("__") and _name != "validate_state_payload":
        globals()[_name] = getattr(_core, _name)
