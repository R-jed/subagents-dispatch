#!/usr/bin/env python3
"""Strict V4 Host evidence ingestion from list_agents PostToolUse.

Only the production Hook envelope can create authoritative lifecycle observations.
Absence from a list_agents response is not interpreted as not_found.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

import dispatch_state_v4 as state
import host_capabilities
import writer_lease_v4 as writer


POST_TOOL_USE = "PostToolUse"
OBSERVATION_TOOL = "list_agents"
RESERVED_AGENT_PREFIX = "subagents_dispatch_"


class HostEvidenceError(RuntimeError):
    """A Hook payload cannot be trusted as authoritative V4 Host evidence."""


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _strict_response(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        raise HostEvidenceError("list_agents tool_response must be an array")
    result: list[Mapping[str, Any]] = []
    names: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, Mapping) or set(item) != {"agent_name", "status"}:
            raise HostEvidenceError(
                f"list_agents tool_response[{index}] must contain exactly agent_name and status"
            )
        name = item.get("agent_name")
        if not _nonempty(name) or name in names:
            raise HostEvidenceError("list_agents response has invalid or duplicate agent_name")
        try:
            host_capabilities.normalize_agent_status(item.get("status"))
        except host_capabilities.HostCapabilityError as exc:
            raise HostEvidenceError(str(exc)) from exc
        names.add(name)
        result.append(item)
    return result


def ingest_list_agents_post_tool_use(
    payload: Mapping[str, Any],
    *,
    temp_root: str | os.PathLike[str] | None = None,
) -> list[dict[str, Any]]:
    """Reconcile managed executions present in one genuine list_agents response."""
    if not isinstance(payload, Mapping):
        raise HostEvidenceError("Hook payload must be an object")
    if payload.get("hook_event_name") != POST_TOOL_USE or payload.get("tool_name") != OBSERVATION_TOOL:
        raise HostEvidenceError("authoritative Host observation requires list_agents PostToolUse")
    session_id = payload.get("session_id")
    turn_id = payload.get("turn_id")
    tool_use_id = payload.get("tool_use_id")
    if not _nonempty(session_id) or not _nonempty(turn_id) or not _nonempty(tool_use_id):
        raise HostEvidenceError("Host observation requires session_id, turn_id, and tool_use_id")
    caller_agent_type = payload.get("agent_type")
    if isinstance(caller_agent_type, str) and caller_agent_type.startswith(RESERVED_AGENT_PREFIX):
        raise HostEvidenceError("managed child cannot author authoritative root Host evidence")
    subagent = payload.get("subagent")
    if subagent is not None:
        raise HostEvidenceError("subagent Hook context cannot author root Host evidence")

    current = state.load_state(session_id, temp_root=temp_root)
    if current is None:
        raise HostEvidenceError("active V4 state is unavailable for Host observation")
    if current.get("root_session_id") != session_id:
        raise HostEvidenceError("Host observation is bound to another root session")

    response = _strict_response(payload.get("tool_response"))
    by_name = {str(item["agent_name"]): item for item in response}
    outcomes: list[dict[str, Any]] = []
    for execution in current.get("executions", []):
        if not isinstance(execution, Mapping):
            continue
        expected_name = f"/root/{execution['native_task_name']}"
        item = by_name.get(expected_name)
        if item is None:
            continue
        normalized = host_capabilities.normalize_agent_status(item["status"])
        basis = state.observation_basis(current, execution_id=execution["execution_id"])
        outcome = writer.persist_authoritative_host_observation(
            session_id,
            basis=basis,
            host_state=normalized["state"],
            turn_id=turn_id,
            tool_use_id=tool_use_id,
            agent_name=expected_name,
            temp_root=temp_root,
        )
        outcomes.append(
            {
                "execution_id": execution["execution_id"],
                "agent_name": expected_name,
                "host_state": normalized["state"],
                "reconcile_status": outcome["reconcile_status"],
                "idempotent": outcome.get("idempotent", False),
            }
        )
        refreshed = state.load_state(session_id, temp_root=temp_root)
        if refreshed is None:
            raise HostEvidenceError("V4 state disappeared during Host observation")
        current = refreshed
    return outcomes


def runtime_temp_root() -> Path | None:
    raw = os.environ.get("SUBAGENTS_DISPATCH_TEMP_ROOT")
    if raw is None or not raw.strip():
        return None
    return Path(raw)
