#!/usr/bin/env python3
"""V4 PendingControl preparation and single-use Host binding.

This module owns lifecycle-control authorization. It does not route work,
acquire WriterLease, or infer Host lifecycle completion.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

import dispatch_state_v4 as state


TOOL_OPERATIONS = {
    "spawn_agent": {"SPAWN"},
    "followup_task": {"FOLLOWUP", "CONTINUE"},
    "interrupt_agent": {"INTERRUPT"},
}
OPERATION_TOOL = {
    "SPAWN": "spawn_agent",
    "FOLLOWUP": "followup_task",
    "CONTINUE": "followup_task",
    "INTERRUPT": "interrupt_agent",
}
EXPECTED_LIFECYCLE = {
    "SPAWN": {"SPAWN_PENDING"},
    "FOLLOWUP": {"COMPLETED"},
    "CONTINUE": {"INTERRUPTED"},
    "INTERRUPT": {"RUNNING"},
}


class ControlError(RuntimeError):
    """PendingControl could not be prepared, consumed, or acknowledged safely."""


class ControlAlreadyAcknowledged(ControlError):
    """The exact PostToolUse acknowledgement was already persisted."""


def canonical_tool_input_digest(tool_input: Any) -> str:
    try:
        encoded = json.dumps(
            tool_input,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ControlError(f"tool_input is not canonical JSON: {exc}") from exc
    return hashlib.sha256(encoded).hexdigest()


def _target_for(tool_name: str, tool_input: Any) -> str:
    if tool_name not in TOOL_OPERATIONS:
        raise ControlError(f"unsupported managed lifecycle tool {tool_name!r}")
    if not isinstance(tool_input, Mapping):
        raise ControlError("managed lifecycle tool_input must be an object")
    key = "task_name" if tool_name == "spawn_agent" else "target"
    target = tool_input.get(key)
    if not isinstance(target, str) or not target.strip():
        raise ControlError(f"{tool_name} requires non-empty {key}")
    return target


def _execution(current: Mapping[str, Any], execution_id: str) -> dict[str, Any]:
    matches = [
        item
        for item in current.get("executions", [])
        if isinstance(item, dict) and item.get("execution_id") == execution_id
    ]
    if len(matches) != 1:
        raise ControlError("execution_id does not resolve exactly once")
    return matches[0]


def _require_current_execution(
    current: Mapping[str, Any], execution: Mapping[str, Any], *, operation: str
) -> None:
    if operation not in {"FOLLOWUP", "CONTINUE"}:
        return
    current_execution = state.current_execution_for_unit(
        current, unit_id=execution["unit_id"]
    )
    if (
        current_execution is None
        or current_execution.get("execution_id") != execution.get("execution_id")
    ):
        raise ControlError("superseded execution cannot receive lifecycle continuation")


def _writer_requirements(
    current: Mapping[str, Any],
    execution: Mapping[str, Any],
    *,
    operation: str,
    writer_effect: str,
) -> int | None:
    writing = execution.get("granted_authority") != "none"
    if not writing:
        if writer_effect != "NONE":
            raise ControlError("read-only execution requires writer_effect=NONE")
        return None

    expected_effect = {
        "SPAWN": "RESERVE",
        "FOLLOWUP": "RETAIN",
        "CONTINUE": "RETAIN",
        "INTERRUPT": "REVOKE",
    }[operation]
    if writer_effect != expected_effect:
        raise ControlError(
            f"writing {operation} requires writer_effect={expected_effect}"
        )
    lease = current.get("writer_lease")
    if not isinstance(lease, Mapping):
        raise ControlError("writing lifecycle control requires WriterLease")
    if lease.get("owner_kind") != "execution" or lease.get("owner_id") != execution.get(
        "execution_id"
    ):
        raise ControlError("WriterLease is not owned by the target execution")
    if lease.get("unit_id") != execution.get("unit_id"):
        raise ControlError("WriterLease unit does not match target execution")
    allowed_states = {
        "SPAWN": {"RESERVED"},
        "FOLLOWUP": {"RESERVED", "HELD"},
        "CONTINUE": {"RESERVED", "HELD"},
        "INTERRUPT": {"REVOKING"},
    }[operation]
    if lease.get("state") not in allowed_states:
        raise ControlError(
            f"WriterLease state {lease.get('state')!r} is unsafe for {operation}"
        )
    lease_epoch = lease.get("lease_epoch")
    if not isinstance(lease_epoch, int) or isinstance(lease_epoch, bool) or lease_epoch < 1:
        raise ControlError("WriterLease has invalid lease_epoch")
    return lease_epoch


def prepare_control(
    thread_id: str,
    *,
    control_id: str,
    execution_id: str,
    operation: str,
    tool_input: Mapping[str, Any],
    writer_effect: str = "NONE",
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Persist one PREPARED control against the current execution generation."""
    if not isinstance(control_id, str) or not control_id.strip():
        raise ControlError("control_id must be non-empty")
    if operation not in OPERATION_TOOL:
        raise ControlError("unsupported PendingControl operation")
    if writer_effect not in state.WRITER_EFFECTS:
        raise ControlError("unsupported writer_effect")
    tool_name = OPERATION_TOOL[operation]
    target = _target_for(tool_name, tool_input)
    digest = canonical_tool_input_digest(tool_input)
    prepared: dict[str, Any] = {}

    def mutate(current: dict[str, Any]) -> None:
        execution = _execution(current, execution_id)
        _require_current_execution(current, execution, operation=operation)
        if execution["native_task_name"] != target:
            raise ControlError("tool target does not match ExecutionBinding native_task_name")
        unresolved = [
            control
            for control in current["pending_controls"]
            if control["execution_id"] == execution_id
            and control["state"] in state.UNRESOLVED_CONTROL_STATES
        ]
        if unresolved:
            raise ControlError("execution already has unresolved PendingControl")
        if execution["lifecycle"] not in EXPECTED_LIFECYCLE[operation]:
            raise ControlError(
                f"execution lifecycle {execution['lifecycle']} is not eligible for {operation}"
            )
        if any(control["control_id"] == control_id for control in current["pending_controls"]):
            raise ControlError("control_id is already present")
        lease_epoch = _writer_requirements(
            current,
            execution,
            operation=operation,
            writer_effect=writer_effect,
        )
        expected_epoch = execution["control_epoch"]
        next_epoch = expected_epoch if operation == "SPAWN" else expected_epoch + 1
        control = {
            "control_id": control_id,
            "unit_id": execution["unit_id"],
            "execution_id": execution_id,
            "operation": operation,
            "target": target,
            "payload_digest": digest,
            "expected_team_plan_revision": current["team_plan_revision"],
            "expected_control_epoch": expected_epoch,
            "next_control_epoch": next_epoch,
            "expected_lease_epoch": lease_epoch,
            "writer_effect": writer_effect,
            "state": "PREPARED",
            "tool_use_id": None,
        }
        current["pending_controls"].append(control)
        prepared.update(copy.deepcopy(control))

    state.mutate_state(thread_id, mutate, temp_root=temp_root)
    return prepared


def _matching_controls(
    current: Mapping[str, Any],
    *,
    tool_name: str,
    tool_input: Mapping[str, Any],
    control_state: str,
    tool_use_id: str | None = None,
) -> list[dict[str, Any]]:
    operations = TOOL_OPERATIONS.get(tool_name)
    if operations is None:
        raise ControlError("unsupported managed lifecycle tool")
    target = _target_for(tool_name, tool_input)
    digest = canonical_tool_input_digest(tool_input)
    matches = []
    for control in current.get("pending_controls", []):
        if not isinstance(control, dict):
            continue
        if control.get("state") != control_state:
            continue
        if control.get("operation") not in operations:
            continue
        if control.get("target") != target or control.get("payload_digest") != digest:
            continue
        if tool_use_id is not None and control.get("tool_use_id") != tool_use_id:
            continue
        matches.append(control)
    return matches


def _tool_use_id_was_acknowledged(current: Mapping[str, Any], tool_use_id: str) -> bool:
    if state.accounting_filter_contains(
        current,
        kind=state.CONTROL_ACK_FILTER_KIND,
        value=tool_use_id,
    ):
        return True
    return any(
        isinstance(event, Mapping)
        and event.get("kind") == "control_ack"
        and event.get("tool_use_id") == tool_use_id
        for event in current.get("accounting_refs", [])
    )


def consume_prepared_control(
    thread_id: str,
    *,
    tool_name: str,
    tool_input: Mapping[str, Any],
    tool_use_id: str,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Atomically consume exactly one PREPARED control for one Host tool call."""
    if not isinstance(tool_use_id, str) or not tool_use_id.strip():
        raise ControlError("tool_use_id must be non-empty")
    consumed: dict[str, Any] = {}

    def mutate(current: dict[str, Any]) -> None:
        matches = _matching_controls(
            current,
            tool_name=tool_name,
            tool_input=tool_input,
            control_state="PREPARED",
        )
        if len(matches) != 1:
            raise ControlError("tool call does not resolve to exactly one PREPARED control")
        if _tool_use_id_was_acknowledged(current, tool_use_id):
            raise ControlError("tool_use_id was already acknowledged and cannot be reused")
        if any(
            control.get("tool_use_id") == tool_use_id
            for control in current["pending_controls"]
            if control is not matches[0]
        ):
            raise ControlError("tool_use_id is already bound to another PendingControl")
        control = matches[0]
        execution = _execution(current, control["execution_id"])
        _require_current_execution(current, execution, operation=control["operation"])
        if control["expected_team_plan_revision"] != current["team_plan_revision"]:
            raise ControlError("PendingControl TeamPlan revision is stale")
        if control["expected_control_epoch"] != execution["control_epoch"]:
            raise ControlError("PendingControl control_epoch is stale")
        expected_lease_epoch = control["expected_lease_epoch"]
        if expected_lease_epoch is not None:
            lease = current.get("writer_lease")
            if not isinstance(lease, Mapping) or lease.get("lease_epoch") != expected_lease_epoch:
                raise ControlError("PendingControl WriterLease epoch is stale")
        control["state"] = "IN_FLIGHT"
        control["tool_use_id"] = tool_use_id
        consumed.update(copy.deepcopy(control))

    state.mutate_state(thread_id, mutate, temp_root=temp_root)
    return consumed


def _ack_ref(control_id: str, tool_use_id: str) -> str:
    return f"control-ack:{control_id}:{tool_use_id}"


def _historical_ack_matches(
    current: Mapping[str, Any],
    *,
    tool_name: str,
    tool_input: Mapping[str, Any],
    tool_use_id: str,
) -> list[Mapping[str, Any]]:
    digest = canonical_tool_input_digest(tool_input)
    target = _target_for(tool_name, tool_input)
    return [
        event
        for event in current.get("accounting_refs", [])
        if isinstance(event, Mapping)
        and event.get("kind") == "control_ack"
        and event.get("tool_use_id") == tool_use_id
        and event.get("tool_name") == tool_name
        and event.get("payload_digest") == digest
        and event.get("target") == target
    ]


def _apply_writer_effect_on_ack(
    current: dict[str, Any],
    *,
    control: Mapping[str, Any],
    execution: Mapping[str, Any],
) -> None:
    """Apply the authorized WriterLease effect inside the same ACK transaction."""
    effect = control["writer_effect"]
    if effect == "NONE":
        if execution.get("granted_authority") != "none":
            raise ControlError("writing lifecycle ACK cannot use writer_effect=NONE")
        return

    lease = current.get("writer_lease")
    if not isinstance(lease, dict):
        raise ControlError("writer lifecycle ACK requires WriterLease")
    if (
        lease.get("owner_kind") != "execution"
        or lease.get("owner_id") != execution.get("execution_id")
        or lease.get("unit_id") != execution.get("unit_id")
        or lease.get("lease_epoch") != control.get("expected_lease_epoch")
    ):
        raise ControlError("writer lifecycle ACK uses stale WriterLease identity")

    if effect in {"RESERVE", "RETAIN"}:
        if lease.get("state") not in {"RESERVED", "HELD"}:
            raise ControlError("writer activation ACK requires RESERVED or HELD WriterLease")
        lease["state"] = "HELD"
        return
    if effect == "REVOKE":
        if lease.get("state") != "REVOKING":
            raise ControlError("writer interrupt ACK requires REVOKING WriterLease")
        return
    raise ControlError("writer lifecycle ACK has unsupported writer_effect")


def acknowledge_control(
    thread_id: str,
    *,
    tool_name: str,
    tool_input: Mapping[str, Any],
    tool_response: Any,
    tool_use_id: str,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Acknowledge one Host call, binding the ACK to the exact current control."""
    if not isinstance(tool_use_id, str) or not tool_use_id.strip():
        raise ControlError("tool_use_id must be non-empty")
    acknowledged: dict[str, Any] = {}

    def mutate(current: dict[str, Any]) -> None:
        matches = _matching_controls(
            current,
            tool_name=tool_name,
            tool_input=tool_input,
            control_state="IN_FLIGHT",
            tool_use_id=tool_use_id,
        )
        if not matches:
            historical = _historical_ack_matches(
                current,
                tool_name=tool_name,
                tool_input=tool_input,
                tool_use_id=tool_use_id,
            )
            if historical or state.accounting_filter_contains(
                current,
                kind=state.CONTROL_ACK_FILTER_KIND,
                value=tool_use_id,
            ):
                raise ControlAlreadyAcknowledged("control acknowledgement already persisted")
            raise ControlError("PostToolUse does not match exactly one IN_FLIGHT control")
        if len(matches) != 1:
            raise ControlError("PostToolUse matches multiple IN_FLIGHT controls")
        control = matches[0]
        execution = _execution(current, control["execution_id"])
        _require_current_execution(current, execution, operation=control["operation"])
        ack_ref = _ack_ref(control["control_id"], tool_use_id)
        if any(event.get("ref") == ack_ref for event in current["accounting_refs"]):
            raise ControlAlreadyAcknowledged("control acknowledgement already persisted")
        if tool_name == "spawn_agent" and isinstance(tool_response, Mapping):
            response_task = tool_response.get("task_name")
            if response_task is not None and response_task != control["target"]:
                raise ControlError("spawn response task_name conflicts with PendingControl target")
        if execution["control_epoch"] != control["expected_control_epoch"]:
            raise ControlError("execution control_epoch changed while control was IN_FLIGHT")

        _apply_writer_effect_on_ack(current, control=control, execution=execution)
        execution["control_epoch"] = control["next_control_epoch"]
        if control["operation"] == "FOLLOWUP":
            execution["followup_count"] = 1
        acknowledged.update(copy.deepcopy(control))
        acknowledged["state"] = "ACKED"
        current["pending_controls"].remove(control)
        current["accounting_refs"].append(
            {
                "ref": ack_ref,
                "kind": "control_ack",
                "control_id": control["control_id"],
                "execution_id": execution["execution_id"],
                "control_epoch": execution["control_epoch"],
                "tool_use_id": tool_use_id,
                "tool_name": tool_name,
                "payload_digest": control["payload_digest"],
                "target": control["target"],
            }
        )

    try:
        state.mutate_state(thread_id, mutate, temp_root=temp_root)
    except ControlAlreadyAcknowledged:
        current = state.load_state(thread_id, temp_root=temp_root)
        if current is None:
            raise ControlError("acknowledged control state disappeared") from None
        return {
            "state": "ACKED",
            "tool_use_id": tool_use_id,
            "idempotent": True,
        }
    acknowledged["idempotent"] = False
    return acknowledged


def mark_control_unknown(
    thread_id: str,
    *,
    tool_use_id: str,
    temp_root: str | os.PathLike[str] | None = None,
) -> bool:
    """Quarantine one IN_FLIGHT control when PostToolUse cannot be reconciled."""
    changed = False

    def mutate(current: dict[str, Any]) -> None:
        nonlocal changed
        matches = [
            control
            for control in current["pending_controls"]
            if control.get("state") == "IN_FLIGHT" and control.get("tool_use_id") == tool_use_id
        ]
        if len(matches) != 1:
            raise ControlError("tool_use_id does not resolve to exactly one IN_FLIGHT control")
        matches[0]["state"] = "UNKNOWN"
        changed = True

    state.mutate_state(thread_id, mutate, temp_root=temp_root)
    return changed


def unresolved_control_for_execution(
    payload: Mapping[str, Any], execution_id: str
) -> dict[str, Any] | None:
    matches = [
        control
        for control in payload.get("pending_controls", [])
        if isinstance(control, dict)
        and control.get("execution_id") == execution_id
        and control.get("state") in state.UNRESOLVED_CONTROL_STATES
    ]
    if len(matches) > 1:
        raise ControlError("execution has multiple unresolved controls")
    return copy.deepcopy(matches[0]) if matches else None


def target_is_managed(payload: Mapping[str, Any], target: str) -> bool:
    if not isinstance(target, str) or not target.strip():
        return False
    return any(
        target in {execution.get("native_task_name"), execution.get("agent_id")}
        for execution in payload.get("executions", [])
        if isinstance(execution, Mapping)
    )


def runtime_temp_root() -> Path | None:
    raw = os.environ.get("SUBAGENTS_DISPATCH_TEMP_ROOT")
    if raw is None or not raw.strip():
        return None
    return Path(raw)
