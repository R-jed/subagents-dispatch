#!/usr/bin/env python3
"""V4 state facade with RC3 correctness-bearing truth and bounded accounting.

This module owns the V4 schema facade and persisted correctness truth. The
storage/schema implementation lives in ``dispatch_state_v4_core``. This facade
preserves the public V4 state API while making persisted correctness facts at
least as strict as the mutation paths that create them and compacting consumed
Host evidence before the bounded state capsule can wedge on valid history.
"""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Callable, Mapping

import dispatch_state_v4_core as _core


ACCOUNTING_FILTER_BITS = 16_384
ACCOUNTING_FILTER_HEX = ACCOUNTING_FILTER_BITS // 4
ACCOUNTING_FILTER_HASHES = 4
RECENT_CONTROL_ACKS = 64
RECENT_OBSERVATION_RECEIPTS = 64
CONTROL_ACK_FILTER_KIND = "control_ack_filter"
OBSERVATION_RECEIPT_FILTER_KIND = "host_observation_receipt_filter"
CONTROL_ACK_FILTER_REF = "control-ack-filter:v1"
OBSERVATION_RECEIPT_FILTER_REF = "host-observation-receipt-filter:v1"


# Dynamic test loading imports this facade more than once under different module
# names. Preserve stable pointers to the original core functions so wrappers do
# not recursively wrap themselves across those imports.
if not hasattr(_core, "_rc3_base_validate_state_payload"):
    _core._rc3_base_validate_state_payload = _core.validate_state_payload
if not hasattr(_core, "_rc3_base_mutate_state"):
    _core._rc3_base_mutate_state = _core.mutate_state
_BASE_VALIDATE_STATE_PAYLOAD = _core._rc3_base_validate_state_payload
_BASE_MUTATE_STATE = _core._rc3_base_mutate_state


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


def _canonical_scope(value: str) -> str:
    normalized = value.replace("\\", "/")
    canonical = _core.PurePosixPath(normalized).as_posix()
    if value != canonical:
        raise _core.StatePayloadError(
            f"write scope {value!r} must use canonical repository-relative POSIX form"
        )
    return canonical


def _prevalidate_scope_canonical(payload: Any) -> None:
    """Reject lexical aliases before any set/subset authority comparison."""
    if not isinstance(payload, Mapping):
        return
    for unit in payload.get("work_units", []):
        if not isinstance(unit, Mapping):
            continue
        ownership = unit.get("ownership")
        if isinstance(ownership, Mapping):
            for field in ("write", "forbidden"):
                values = ownership.get(field)
                if isinstance(values, list):
                    for value in values:
                        if isinstance(value, str):
                            _canonical_scope(value)
        ceiling = unit.get("write_scope_ceiling")
        if isinstance(ceiling, list):
            for value in ceiling:
                if isinstance(value, str):
                    _canonical_scope(value)
    for execution in payload.get("executions", []):
        if not isinstance(execution, Mapping):
            continue
        granted = execution.get("granted_write_scope")
        if isinstance(granted, list):
            for value in granted:
                if isinstance(value, str):
                    _canonical_scope(value)


def _scope_overlaps(left: str, right: str) -> bool:
    left_parts = _core.PurePosixPath(left).parts
    right_parts = _core.PurePosixPath(right).parts
    shortest = min(len(left_parts), len(right_parts))
    return left_parts[:shortest] == right_parts[:shortest]


def _validate_scope_truth(state: Mapping[str, Any]) -> None:
    for unit in state.get("work_units", []):
        if not isinstance(unit, Mapping):
            continue
        ownership = unit.get("ownership")
        if not isinstance(ownership, Mapping):
            continue
        write = [_canonical_scope(value) for value in ownership.get("write", [])]
        forbidden = [_canonical_scope(value) for value in ownership.get("forbidden", [])]
        for value in unit.get("write_scope_ceiling", []):
            _canonical_scope(value)
        if any(_scope_overlaps(writable, denied) for writable in write for denied in forbidden):
            raise _core.StatePayloadError(
                f"work unit {unit.get('unit_id')} write and forbidden scopes overlap by ancestry"
            )
    for execution in state.get("executions", []):
        if not isinstance(execution, Mapping):
            continue
        for value in execution.get("granted_write_scope", []):
            _canonical_scope(value)


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


def _filter_positions(value: str) -> tuple[int, ...]:
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    return tuple(
        int.from_bytes(digest[index * 2 : index * 2 + 2], "big") % ACCOUNTING_FILTER_BITS
        for index in range(ACCOUNTING_FILTER_HASHES)
    )


def _filter_bits(value: Any) -> int:
    if not isinstance(value, str) or len(value) != ACCOUNTING_FILTER_HEX:
        return 0
    try:
        return int(value, 16)
    except ValueError:
        return 0


def _filter_add(bits: int, value: str) -> int:
    for position in _filter_positions(value):
        bits |= 1 << position
    return bits


def accounting_filter_contains(
    payload: Mapping[str, Any], *, kind: str, value: str
) -> bool:
    """Return whether a compacted consumed-call filter contains one Host id."""
    if not isinstance(value, str) or not value:
        return False
    matches = [
        event
        for event in payload.get("accounting_refs", [])
        if isinstance(event, Mapping) and event.get("kind") == kind
    ]
    if len(matches) != 1:
        return False
    bits = _filter_bits(matches[0].get("bits"))
    if bits == 0:
        return False
    return all(bits & (1 << position) for position in _filter_positions(value))


def _filter_event(*, kind: str, ref: str, bits: int, count: int) -> dict[str, Any]:
    return {
        "ref": ref,
        "kind": kind,
        "bits": f"{bits:0{ACCOUNTING_FILTER_HEX}x}",
        "count": count,
    }


def _compact_accounting_refs(payload: dict[str, Any]) -> None:
    events = payload.get("accounting_refs")
    if not isinstance(events, list):
        return

    control_filter_bits = 0
    control_filter_count = 0
    receipt_filter_bits = 0
    receipt_filter_count = 0
    control_acks: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    preserved: list[dict[str, Any]] = []

    for raw in events:
        if not isinstance(raw, dict):
            preserved.append(raw)
            continue
        kind = raw.get("kind")
        if kind == CONTROL_ACK_FILTER_KIND:
            control_filter_bits |= _filter_bits(raw.get("bits"))
            count = raw.get("count")
            if isinstance(count, int) and not isinstance(count, bool) and count >= 0:
                control_filter_count += count
        elif kind == OBSERVATION_RECEIPT_FILTER_KIND:
            receipt_filter_bits |= _filter_bits(raw.get("bits"))
            count = raw.get("count")
            if isinstance(count, int) and not isinstance(count, bool) and count >= 0:
                receipt_filter_count += count
        elif kind == "control_ack":
            control_acks.append(raw)
        elif kind == "host_observation_receipt":
            receipts.append(raw)
        elif kind == "host_observation":
            observations.append(raw)
        else:
            preserved.append(raw)

    if len(control_acks) > RECENT_CONTROL_ACKS:
        compacted = control_acks[:-RECENT_CONTROL_ACKS]
        control_acks = control_acks[-RECENT_CONTROL_ACKS:]
        for event in compacted:
            tool_use_id = event.get("tool_use_id")
            if isinstance(tool_use_id, str) and tool_use_id:
                control_filter_bits = _filter_add(control_filter_bits, tool_use_id)
                control_filter_count += 1

    if len(receipts) > RECENT_OBSERVATION_RECEIPTS:
        compacted = receipts[:-RECENT_OBSERVATION_RECEIPTS]
        receipts = receipts[-RECENT_OBSERVATION_RECEIPTS:]
        for event in compacted:
            tool_use_id = event.get("tool_use_id")
            if isinstance(tool_use_id, str) and tool_use_id:
                receipt_filter_bits = _filter_add(receipt_filter_bits, tool_use_id)
                receipt_filter_count += 1

    latest_observation: dict[tuple[Any, ...], dict[str, Any]] = {}
    observation_order: list[tuple[Any, ...]] = []
    for event in observations:
        key = (
            event.get("source"),
            event.get("execution_id"),
            event.get("control_epoch"),
            event.get("lease_epoch"),
            event.get("lifecycle"),
        )
        if key not in latest_observation:
            observation_order.append(key)
        latest_observation[key] = event
    observations = [latest_observation[key] for key in observation_order]

    compacted_events = preserved
    if control_filter_count:
        compacted_events.append(
            _filter_event(
                kind=CONTROL_ACK_FILTER_KIND,
                ref=CONTROL_ACK_FILTER_REF,
                bits=control_filter_bits,
                count=control_filter_count,
            )
        )
    if receipt_filter_count:
        compacted_events.append(
            _filter_event(
                kind=OBSERVATION_RECEIPT_FILTER_KIND,
                ref=OBSERVATION_RECEIPT_FILTER_REF,
                bits=receipt_filter_bits,
                count=receipt_filter_count,
            )
        )
    compacted_events.extend(control_acks)
    compacted_events.extend(receipts)
    compacted_events.extend(observations)
    payload["accounting_refs"] = compacted_events


def validate_state_payload(
    payload: Any,
    *,
    thread_id: str | None = None,
    max_bytes: int = _core.DEFAULT_MAX_BYTES,
) -> dict[str, Any]:
    """Validate schema/storage safety and all RC3 correctness-bearing truths."""
    _prevalidate_scope_canonical(payload)
    state = _BASE_VALIDATE_STATE_PAYLOAD(
        payload,
        thread_id=thread_id,
        max_bytes=max_bytes,
    )
    _validate_scope_truth(state)
    _validate_acceptance_truth(state)
    return state


def mutate_state(
    thread_id: str | None,
    mutator: Callable[[dict[str, Any]], None],
    *,
    expected_state_revision: int | None = None,
    temp_root: str | Any | None = None,
    max_bytes: int = _core.DEFAULT_MAX_BYTES,
    now: Any = None,
) -> dict[str, Any]:
    """Atomically mutate state and compact consumed accounting history first."""

    def bounded_mutator(current: dict[str, Any]) -> None:
        mutator(current)
        _compact_accounting_refs(current)

    return _BASE_MUTATE_STATE(
        thread_id,
        bounded_mutator,
        expected_state_revision=expected_state_revision,
        temp_root=temp_root,
        max_bytes=max_bytes,
        now=now,
    )


# Core functions resolve their module-global helpers at call time. Point those
# names at the facade wrappers so load/write/mutate/reconcile paths cannot bypass
# the RC3 truth kernel or accounting compaction.
_core.validate_state_payload = validate_state_payload
_core.mutate_state = mutate_state

# Preserve the established dispatch_state_v4 public surface for existing callers.
for _name in dir(_core):
    if not _name.startswith("__") and _name not in {"validate_state_payload", "mutate_state"}:
        globals()[_name] = getattr(_core, _name)
