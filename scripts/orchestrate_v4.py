#!/usr/bin/env python3
"""V4 Native Core Orchestrate production facade.

Orchestrate owns deterministic routing and project decisions. Main invokes native
Host lifecycle tools and feeds observed lifecycle truth into the lifecycle layer.
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


_PROFILE_SPECS = policy_contract.profile_contracts()
FIXED_PROFILES = {
    role: {
        "model": spec["model"],
        "effort": spec["effort"],
        "authority_ceiling": spec["mutation_authority"],
        "semantic_role": spec["semantic_role"],
    }
    for role, spec in _PROFILE_SPECS.items()
}


class OrchestrateError(RuntimeError):
    """An Orchestrate request violates V4 session or routing policy."""


def route_profile(
    *,
    intent: str,
    requires_write: bool = False,
    broad_investigation: bool = False,
    stalled_or_high_judgment: bool = False,
    review: bool = False,
) -> dict[str, Any]:
    if review:
        profile_id = "advisor"
    elif stalled_or_high_judgment:
        profile_id = "solver"
    elif requires_write:
        profile_id = "worker"
    elif broad_investigation:
        profile_id = "investigator"
    else:
        profile_id = "reader"
    profile = copy.deepcopy(FIXED_PROFILES[profile_id])
    profile["profile_id"] = profile_id
    profile["intent"] = intent
    profile["granted_authority"] = (
        "bounded-source-write" if requires_write and profile_id in {"worker", "solver"} else "none"
    )
    return profile


def plan_only_preview(*, goal: str, responsibilities: list[Mapping[str, Any]]) -> dict[str, Any]:
    if not isinstance(goal, str) or not goal.strip():
        raise OrchestrateError("goal must be non-empty")
    units: list[dict[str, Any]] = []
    for index, responsibility in enumerate(responsibilities, start=1):
        if not isinstance(responsibility, Mapping):
            raise OrchestrateError("responsibility must be an object")
        intent = str(responsibility.get("intent", "inspect"))
        route = route_profile(
            intent=intent,
            requires_write=responsibility.get("requires_write") is True,
            broad_investigation=responsibility.get("broad_investigation") is True,
            stalled_or_high_judgment=responsibility.get("stalled_or_high_judgment") is True,
            review=responsibility.get("review") is True,
        )
        units.append(
            {
                "unit_id": f"U{index}",
                "intent": intent,
                "goal": str(responsibility.get("goal", intent)),
                "depends_on": list(responsibility.get("depends_on", [])),
                "route": route,
            }
        )
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
    current = require_control_session(
        thread_id, orchestration_id=orchestration_id, temp_root=temp_root
    )
    return scheduler.scheduler_decision(
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
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Prepare the one bounded post-completion same-child correction."""
    require_control_session(thread_id, orchestration_id=orchestration_id, temp_root=temp_root)
    return lifecycle.prepare_same_child_followup(
        thread_id,
        execution_id=execution_id,
        tool_input=tool_input,
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
    """Prepare continuation of the same interrupted child without spending correction budget."""
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
