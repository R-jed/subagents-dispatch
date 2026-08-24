#!/usr/bin/env python3
"""V4 Native Core Orchestrate production facade.

The main session owns decomposition, profile choice, dispatch judgment, integration,
and final acceptance. Deterministic helpers validate fixed profile, lifecycle, and
state constraints without selecting work on the main session's behalf.
"""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any, Mapping

import dispatch_state_v4 as state
import execution_lifecycle_v4 as lifecycle
import policy as policy_contract
import scheduler_v4 as scheduler
import work_graph_v4 as work_graph


_PROFILE_SPECS = policy_contract.profile_contracts()
FIXED_PROFILES = {
    role: {
        "agent_type": spec["agent_type"],
        "model": spec["model"],
        "effort": spec["effort"],
        "authority_ceiling": spec["mutation_authority"],
        "semantic_role": spec["semantic_role"],
    }
    for role, spec in _PROFILE_SPECS.items()
}


class OrchestrateError(RuntimeError):
    """An Orchestrate request violates V4 session or fixed-profile policy."""


def select_profile(*, profile_id: str, intent: str) -> dict[str, Any]:
    """Validate one profile chosen explicitly by the main session."""
    if profile_id not in FIXED_PROFILES:
        raise OrchestrateError("profile_id is outside the fixed managed profiles")
    if not isinstance(intent, str) or not intent.strip():
        raise OrchestrateError("intent must be non-empty")
    profile = copy.deepcopy(FIXED_PROFILES[profile_id])
    profile["profile_id"] = profile_id
    profile["intent"] = intent
    return profile


def plan_only_preview(*, goal: str, responsibilities: list[Mapping[str, Any]]) -> dict[str, Any]:
    if not isinstance(goal, str) or not goal.strip():
        raise OrchestrateError("goal must be non-empty")
    units: list[dict[str, Any]] = []
    canonical_units: list[dict[str, Any]] = []
    for index, responsibility in enumerate(responsibilities, start=1):
        if not isinstance(responsibility, Mapping):
            raise OrchestrateError("responsibility must be an object")
        intent = responsibility.get("intent", "inspect")
        profile_id = responsibility.get("profile_id")
        if not isinstance(profile_id, str) or not profile_id.strip():
            raise OrchestrateError(
                "plan-only responsibility requires explicit profile_id from the main session"
            )
        profile = select_profile(profile_id=profile_id, intent=intent)
        unit_goal = responsibility.get("goal", intent)
        try:
            unit = work_graph.make_work_unit(
                unit_id=f"U{index}",
                intent=intent,
                goal=unit_goal,
                output="plan-only preview",
                depends_on=responsibility.get("depends_on", []),
                done_when="Main accepts this responsibility before execution.",
            )
        except TypeError as exc:
            raise OrchestrateError("plan-only responsibility has invalid field types") from exc
        canonical_units.append(unit)
        units.append(
            {
                "unit_id": unit["unit_id"],
                "intent": unit["intent"],
                "goal": unit["goal"],
                "depends_on": list(unit["depends_on"]),
                "profile": profile,
            }
        )

    validation_state = state.new_state(thread_id="plan-only-preview")
    validation_state["work_units"] = canonical_units
    try:
        state.validate_state_payload(validation_state)
    except state.StatePayloadError as exc:
        raise OrchestrateError(f"invalid plan-only WorkUnit graph: {exc}") from exc

    return {
        "mode": "PLAN_ONLY",
        "goal": goal,
        "state_created": False,
        "writer_lease_acquired": False,
        "host_actions": [],
        "work_units": units,
    }


def _load(thread_id: str, temp_root: str | os.PathLike[str] | None) -> dict[str, Any] | None:
    return state.load_state(thread_id, temp_root=temp_root)


def _unresolved(payload: Mapping[str, Any]) -> bool:
    if any(unit["state"] not in {"ACCEPTED", "CANCELLED"} for unit in payload.get("work_units", [])):
        return True
    if any(
        execution["lifecycle"] in {"SPAWN_PENDING", "RUNNING", "INTERRUPTED", "UNKNOWN"}
        for execution in payload.get("executions", [])
    ):
        return True
    lease = payload.get("writer_lease")
    return isinstance(lease, Mapping) and lease.get("state") in state.WRITER_BLOCKING_STATES


def admission_decision(
    thread_id: str,
    *,
    orchestration_id: str | None,
    new_task: bool,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    current = _load(thread_id, temp_root)
    if current is None:
        return {"decision": "NEW_ALLOWED", "orchestration_id": None}
    active_id = current["root_session_id"]
    if orchestration_id == active_id:
        return {"decision": "RESUME_ALLOWED", "orchestration_id": active_id}
    if _unresolved(current):
        return {
            "decision": "BLOCK_ACTIVE_ORCHESTRATION",
            "orchestration_id": active_id,
            "requires_explicit_target": True,
        }
    if new_task:
        return {"decision": "NEW_ALLOWED_AFTER_TERMINAL", "orchestration_id": active_id}
    return {
        "decision": "TARGET_REQUIRED",
        "orchestration_id": active_id,
        "requires_explicit_target": True,
    }


def require_control_session(
    thread_id: str,
    *,
    orchestration_id: str,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    current = _load(thread_id, temp_root)
    if current is None:
        raise OrchestrateError("no active V4 orchestration")
    if orchestration_id != current["root_session_id"]:
        raise OrchestrateError("control request does not target the active orchestration")
    return current


def _current_control_execution(
    current: Mapping[str, Any], *, execution_id: str
) -> Mapping[str, Any]:
    matches = [
        item
        for item in current.get("executions", [])
        if isinstance(item, Mapping) and item.get("execution_id") == execution_id
    ]
    if len(matches) != 1:
        raise OrchestrateError("execution_id does not resolve exactly once")
    execution = matches[0]
    current_execution = state.current_execution_for_unit(
        current, unit_id=str(execution["unit_id"])
    )
    if current_execution is None or current_execution.get("execution_id") != execution_id:
        raise OrchestrateError("control request targets a superseded execution")
    return execution


def _validate_message_control_input(
    tool_input: Mapping[str, Any], *, target: str
) -> dict[str, Any]:
    if not isinstance(tool_input, Mapping):
        raise OrchestrateError("native control tool_input must be an object")
    if set(tool_input) != {"target", "message"} or tool_input.get("target") != target:
        raise OrchestrateError("native control tool_input does not match ExecutionBinding")
    message = tool_input.get("message")
    if not isinstance(message, str) or not message.strip():
        raise OrchestrateError("native control message must be non-empty")
    return copy.deepcopy(dict(tool_input))


def prepare_managed_spawn(
    thread_id: str,
    *,
    orchestration_id: str,
    execution_id: str,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Return the only Host spawn payload allowed for the current managed execution."""
    current = require_control_session(
        thread_id, orchestration_id=orchestration_id, temp_root=temp_root
    )
    _current_control_execution(current, execution_id=execution_id)
    tool_input = lifecycle.build_managed_spawn_tool_input(
        thread_id,
        execution_id=execution_id,
        temp_root=temp_root,
    )
    return lifecycle.prepare_spawn(
        thread_id,
        execution_id=execution_id,
        tool_input=tool_input,
        temp_root=temp_root,
    )


def status_view(
    thread_id: str,
    *,
    orchestration_id: str,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    current = require_control_session(
        thread_id, orchestration_id=orchestration_id, temp_root=temp_root
    )
    view = scheduler.scheduler_status(current)
    blockers: list[dict[str, Any]] = []
    for unit in current["work_units"]:
        if unit["state"] == "BLOCKED":
            blockers.append(
                {
                    "kind": "dependency",
                    "unit_id": unit["unit_id"],
                    "depends_on": list(unit["depends_on"]),
                }
            )
    for execution in current["executions"]:
        if execution["blocker"] != "none" or execution["lifecycle"] == "UNKNOWN":
            blockers.append(
                {
                    "kind": "execution",
                    "execution_id": execution["execution_id"],
                    "state": execution["lifecycle"],
                    "blocker": execution["blocker"],
                }
            )
    view.update(
        {
            "orchestration_id": current["root_session_id"],
            "blockers": blockers,
            "acceptance": [
                {
                    "unit_id": unit["unit_id"],
                    "state": unit["state"],
                    "accepted_result_ref": unit["accepted_result_ref"],
                }
                for unit in current["work_units"]
            ],
        }
    )
    return view


def reconcile_once(
    thread_id: str,
    *,
    orchestration_id: str,
    capability_snapshot: Mapping[str, Any] | None,
    wakeup_reason: str,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Return machine constraints; the main session still chooses any next dispatch."""
    current = require_control_session(
        thread_id, orchestration_id=orchestration_id, temp_root=temp_root
    )
    return scheduler.constraint_snapshot(
        current,
        capability_snapshot=capability_snapshot,
        wakeup_reason=wakeup_reason,
    )


def prepare_steer(
    thread_id: str,
    *,
    orchestration_id: str,
    execution_id: str,
    tool_input: Mapping[str, Any],
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Validate focused guidance for one currently running child without mutating project state."""
    current = require_control_session(
        thread_id, orchestration_id=orchestration_id, temp_root=temp_root
    )
    execution = _current_control_execution(current, execution_id=execution_id)
    if execution["lifecycle"] != "RUNNING":
        raise OrchestrateError("Steer requires a RUNNING execution")
    validated_input = _validate_message_control_input(
        tool_input, target=str(execution["native_task_name"])
    )
    return {
        "operation": "STEER",
        "execution_id": execution_id,
        "tool_input": validated_input,
        "control_epoch": execution["control_epoch"],
        "observation_basis": state.observation_basis(current, execution_id=execution_id),
    }


def prepare_correction(
    thread_id: str,
    *,
    orchestration_id: str,
    execution_id: str,
    tool_input: Mapping[str, Any],
    correction_basis_ref: str,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    require_control_session(thread_id, orchestration_id=orchestration_id, temp_root=temp_root)
    return lifecycle.prepare_same_child_followup(
        thread_id,
        execution_id=execution_id,
        tool_input=tool_input,
        correction_basis_ref=correction_basis_ref,
        temp_root=temp_root,
    )


def prepare_continue(
    thread_id: str,
    *,
    orchestration_id: str,
    execution_id: str,
    tool_input: Mapping[str, Any],
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    require_control_session(thread_id, orchestration_id=orchestration_id, temp_root=temp_root)
    return lifecycle.prepare_same_child_continue(
        thread_id,
        execution_id=execution_id,
        tool_input=tool_input,
        temp_root=temp_root,
    )


def prepare_takeover_interrupt(
    thread_id: str,
    *,
    orchestration_id: str,
    execution_id: str,
    tool_input: Mapping[str, Any],
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    require_control_session(thread_id, orchestration_id=orchestration_id, temp_root=temp_root)
    return lifecycle.prepare_interrupt(
        thread_id,
        execution_id=execution_id,
        tool_input=tool_input,
        temp_root=temp_root,
    )


def runtime_temp_root() -> Path | None:
    raw = os.environ.get("SUBAGENTS_DISPATCH_TEMP_ROOT")
    if raw is None or not raw.strip():
        return None
    return Path(raw)
