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
PROFILE_AGENT_TYPES = policy_contract.profile_agent_types()


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
    if profile_id not in state.PROFILE_CONTRACT or profile_id not in PROFILE_AGENT_TYPES:
        raise ManagedExecutionContractError("execution has unsupported managed profile")
    model, effort, profile_authority = state.PROFILE_CONTRACT[profile_id]
    if execution.get("model") != model or execution.get("effort") != effort:
        raise ManagedExecutionContractError("execution model/effort drift from fixed profile")
    if state.AUTHORITY_RANK.get(execution.get("granted_authority"), 99) > state.AUTHORITY_RANK.get(
        profile_authority, -1
    ):
        raise ManagedExecutionContractError("execution authority exceeds fixed profile")
    return PROFILE_AGENT_TYPES[profile_id]


def assignment_packet(
    current: Mapping[str, Any], *, execution: Mapping[str, Any]
) -> dict[str, Any]:
    """Build the one canonical five-section responsibility record."""
    unit = _unit(current, str(execution.get("unit_id")))
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
            "decision_boundary": (
                "Do not widen scope, change architecture, or reinterpret acceptance "
                "without the main session."
            ),
        },
        "constraints": {
            "forbidden_scope": list(unit["ownership"]["forbidden"]),
            "evidence_boundary": (
                "Use only supplied or independently inspected evidence for this WorkUnit; "
                "report uncertainty to the main session."
            ),
            "delegation_boundary": "Do not create or control further subagents.",
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
