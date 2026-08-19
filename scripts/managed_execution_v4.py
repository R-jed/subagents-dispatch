#!/usr/bin/env python3
"""Pure V4 managed-execution contract derivation.

This module derives the only valid Host spawn payload for a persisted
ExecutionBinding. It performs no state mutation and no Host calls so both the
lifecycle layer and the production Guard can verify the same contract
independently.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

import dispatch_state_v4 as state
import policy as policy_contract


MANAGED_FORK_TURNS = "none"
_PROFILE_SPECS = policy_contract.profile_contracts()
PROFILE_AGENT_TYPES = {role: spec["agent_type"] for role, spec in _PROFILE_SPECS.items()}
RESPONSIBILITY_CONTEXT_FIELDS = {
    "interfaces",
    "invariants",
    "decision_boundary",
    "accepted_evidence_refs",
    "do_not_redo",
    "stop_boundary",
}


class ManagedExecutionContractError(RuntimeError):
    """Persisted V4 execution state cannot produce one safe managed Host call."""


def _execution_by_id(current: Mapping[str, Any], execution_id: str) -> Mapping[str, Any]:
    matches = [
        item
        for item in current.get("executions", [])
        if isinstance(item, Mapping) and item.get("execution_id") == execution_id
    ]
    if len(matches) != 1:
        raise ManagedExecutionContractError("execution_id does not resolve exactly once")
    return matches[0]


def _execution_by_task_name(current: Mapping[str, Any], task_name: str) -> Mapping[str, Any]:
    matches = [
        item
        for item in current.get("executions", [])
        if isinstance(item, Mapping) and item.get("native_task_name") == task_name
    ]
    if len(matches) != 1:
        raise ManagedExecutionContractError("task_name does not resolve exactly once")
    return matches[0]


def _unit(current: Mapping[str, Any], unit_id: str) -> Mapping[str, Any]:
    matches = [
        item
        for item in current.get("work_units", [])
        if isinstance(item, Mapping) and item.get("unit_id") == unit_id
    ]
    if len(matches) != 1:
        raise ManagedExecutionContractError("unit_id does not resolve exactly once")
    return matches[0]


def _profile_agent_type(execution: Mapping[str, Any]) -> str:
    profile_id = execution.get("profile_id")
    if profile_id not in _PROFILE_SPECS:
        raise ManagedExecutionContractError("execution has unsupported managed profile")
    spec = _PROFILE_SPECS[str(profile_id)]
    if execution.get("model") != spec["model"] or execution.get("effort") != spec["effort"]:
        raise ManagedExecutionContractError("execution model/effort drift from fixed profile")
    if state.AUTHORITY_RANK.get(execution.get("granted_authority"), 99) > state.AUTHORITY_RANK.get(
        spec["mutation_authority"], -1
    ):
        raise ManagedExecutionContractError("execution authority exceeds fixed profile")
    return spec["agent_type"]


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: Any, *, label: str) -> list[str]:
    if not isinstance(value, list) or not all(_nonempty(item) for item in value):
        raise ManagedExecutionContractError(f"responsibility context {label} must be strings")
    if len(value) != len(set(value)):
        raise ManagedExecutionContractError(f"responsibility context {label} must be unique")
    return list(value)


def _responsibility_context(unit: Mapping[str, Any]) -> dict[str, Any]:
    raw = unit.get("responsibility_context")
    if not isinstance(raw, Mapping) or set(raw) != RESPONSIBILITY_CONTEXT_FIELDS:
        raise ManagedExecutionContractError("managed WorkUnit requires complete responsibility context")
    interfaces = _string_list(raw.get("interfaces"), label="interfaces")
    invariants = _string_list(raw.get("invariants"), label="invariants")
    accepted_evidence_refs = _string_list(
        raw.get("accepted_evidence_refs"), label="accepted_evidence_refs"
    )
    do_not_redo = _string_list(raw.get("do_not_redo"), label="do_not_redo")
    decision_boundary = raw.get("decision_boundary")
    stop_boundary = raw.get("stop_boundary")
    if not _nonempty(decision_boundary) or not _nonempty(stop_boundary):
        raise ManagedExecutionContractError(
            "responsibility context requires decision_boundary and stop_boundary"
        )
    return {
        "interfaces": interfaces,
        "invariants": invariants,
        "decision_boundary": str(decision_boundary),
        "accepted_evidence_refs": accepted_evidence_refs,
        "do_not_redo": do_not_redo,
        "stop_boundary": str(stop_boundary),
    }


def assignment_packet(
    current: Mapping[str, Any], *, execution: Mapping[str, Any]
) -> dict[str, Any]:
    """Build the one canonical five-section responsibility record."""
    unit = _unit(current, str(execution.get("unit_id")))
    context = _responsibility_context(unit)
    return {
        "objective": {
            "intent": unit["intent"],
            "goal": unit["goal"],
            "output": unit["output"],
        },
        "ownership": {
            "unit_id": unit["unit_id"],
            "execution_id": execution["execution_id"],
            "attempt_no": execution["attempt_no"],
            "team_plan_revision": execution.get("team_plan_revision"),
            "mutation_authority": execution["granted_authority"],
            "write_scope": list(execution["granted_write_scope"]),
        },
        "interfaces": {
            "interfaces": context["interfaces"],
            "invariants": context["invariants"],
            "decision_boundary": context["decision_boundary"],
        },
        "constraints": {
            "forbidden_scope": list(unit["ownership"]["forbidden"]),
            "accepted_evidence_refs": context["accepted_evidence_refs"],
            "do_not_redo": context["do_not_redo"],
            "evidence_boundary": (
                "Use only supplied or independently inspected evidence for this WorkUnit; "
                "report uncertainty to the main session."
            ),
            "delegation_boundary": "Do not create or control further subagents.",
            "stop_boundary": context["stop_boundary"],
        },
        "verification": {
            "acceptance": unit["done_when"],
        },
    }


def render_assignment_message(packet: Mapping[str, Any]) -> str:
    return json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def expected_spawn_input_for_execution(
    current: Mapping[str, Any], *, execution_id: str
) -> dict[str, Any]:
    execution = _execution_by_id(current, execution_id)
    agent_type = _profile_agent_type(execution)
    packet = assignment_packet(current, execution=execution)
    return {
        "task_name": execution["native_task_name"],
        "message": render_assignment_message(packet),
        "agent_type": agent_type,
        "fork_turns": MANAGED_FORK_TURNS,
    }


def expected_spawn_input_for_task(
    current: Mapping[str, Any], *, task_name: str
) -> dict[str, Any]:
    execution = _execution_by_task_name(current, task_name)
    return expected_spawn_input_for_execution(
        current, execution_id=str(execution["execution_id"])
    )


def validate_actual_spawn_input(
    current: Mapping[str, Any], *, tool_input: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(tool_input, Mapping):
        raise ManagedExecutionContractError("managed spawn tool_input must be an object")
    task_name = tool_input.get("task_name")
    if not isinstance(task_name, str) or not task_name.strip():
        raise ManagedExecutionContractError("managed spawn requires native task_name")
    expected = expected_spawn_input_for_task(current, task_name=task_name)
    actual = dict(tool_input)
    if actual != expected:
        raise ManagedExecutionContractError(
            "managed spawn input does not match profile, fresh-context, or assignment contract"
        )
    return expected
