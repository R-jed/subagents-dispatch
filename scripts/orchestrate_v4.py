#!/usr/bin/env python3
"""V4 Orchestrate production facade.

Orchestration decisions remain deterministic and Host-neutral. Repository and
offline verification may run while real Host smoke is pending, while managed
Host lifecycle execution stays fail-closed behind release_gate_v4.
"""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any, Mapping

import dispatch_state_v4 as state
import execution_lifecycle_v4 as lifecycle
import release_gate_v4 as release_gate
import scheduler_v4 as scheduler


FIXED_PROFILES = {
    "reader": {
        "model": "gpt-5.6-luna",
        "effort": "max",
        "authority_ceiling": "none",
        "semantic_role": "work",
    },
    "worker": {
        "model": "gpt-5.6-luna",
        "effort": "max",
        "authority_ceiling": "bounded-source-write",
        "semantic_role": "work",
    },
    "investigator": {
        "model": "gpt-5.6-terra",
        "effort": "high",
        "authority_ceiling": "none",
        "semantic_role": "work",
    },
    "solver": {
        "model": "gpt-5.6-sol",
        "effort": "high",
        "authority_ceiling": "bounded-source-write",
        "semantic_role": "work",
    },
    "advisor": {
        "model": "gpt-5.6-sol",
        "effort": "high",
        "authority_ceiling": "none",
        "semantic_role": "review",
    },
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
    """Select one fixed V4 profile without changing model or reasoning effort."""
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
    """Compile a plan preview without reading or creating active state or Host work."""
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


def execution_readiness() -> dict[str, Any]:
    """Return the canonical supported-execution release gate without mutation."""
    return release_gate.managed_execution_readiness()


def require_execution_ready() -> dict[str, Any]:
    """Fail closed before any managed Host lifecycle action is prepared."""
    return release_gate.require_managed_execution_ready()


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
    if isinstance(lease, Mapping) and lease.get("state") in state.WRITER_BLOCKING_STATES:
        return True
    return any(
        control["state"] in state.UNRESOLVED_CONTROL_STATES
        for control in payload.get("pending_controls", [])
    )


def admission_decision(
    thread_id: str,
    *,
    orchestration_id: str | None,
    new_task: bool,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Prevent an unrelated request from silently attaching to active orchestration."""
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
    for control_item in current["pending_controls"]:
        if control_item["state"] in state.UNRESOLVED_CONTROL_STATES:
            blockers.append(
                {
                    "kind": "control",
                    "control_id": control_item["control_id"],
                    "state": control_item["state"],
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
            "execution_readiness": execution_readiness(),
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
    decision = scheduler.scheduler_decision(
        current,
        capability_snapshot=capability_snapshot,
        wakeup_reason=wakeup_reason,
    )
    decision["execution_readiness"] = execution_readiness()
    return decision


def prepare_steer(
    thread_id: str,
    *,
    orchestration_id: str,
    execution_id: str,
    tool_input: Mapping[str, Any],
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    require_execution_ready()
    require_control_session(thread_id, orchestration_id=orchestration_id, temp_root=temp_root)
    return lifecycle.prepare_same_child_followup(
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
    require_execution_ready()
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
