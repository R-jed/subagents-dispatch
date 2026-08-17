#!/usr/bin/env python3
"""Strict V4 Host evidence ingestion from paired list_agents Hooks.

PreToolUse captures the exact execution/control/lease basis for one observation
request. PostToolUse can only reconcile against that captured basis, so a late or
out-of-order Host response cannot be rebound to a newer execution generation.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

import dispatch_state_v4 as state
import host_capabilities
import writer_lease_v4 as writer


PRE_TOOL_USE = "PreToolUse"
POST_TOOL_USE = "PostToolUse"
OBSERVATION_TOOL = "list_agents"
RESERVED_AGENT_PREFIX = "subagents_dispatch_"
PREPARE_KIND = "host_observation_prepare"
RECEIPT_KIND = "host_observation_receipt"


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


def _hook_identity(payload: Mapping[str, Any], *, expected_event: str) -> tuple[str, str, str]:
    if not isinstance(payload, Mapping):
        raise HostEvidenceError("Hook payload must be an object")
    if payload.get("hook_event_name") != expected_event or payload.get("tool_name") != OBSERVATION_TOOL:
        raise HostEvidenceError(
            f"authoritative Host observation requires list_agents {expected_event}"
        )
    session_id = payload.get("session_id")
    turn_id = payload.get("turn_id")
    tool_use_id = payload.get("tool_use_id")
    if not _nonempty(session_id) or not _nonempty(turn_id) or not _nonempty(tool_use_id):
        raise HostEvidenceError("Host observation requires session_id, turn_id, and tool_use_id")
    caller_agent_type = payload.get("agent_type")
    if isinstance(caller_agent_type, str) and caller_agent_type.startswith(RESERVED_AGENT_PREFIX):
        raise HostEvidenceError("managed child cannot author authoritative root Host evidence")
    if payload.get("subagent") is not None:
        raise HostEvidenceError("subagent Hook context cannot author root Host evidence")
    return str(session_id), str(turn_id), str(tool_use_id)


def _prepare_ref(tool_use_id: str) -> str:
    return f"host-observation-prepare:{tool_use_id}"


def _receipt_ref(tool_use_id: str) -> str:
    return f"host-observation-receipt:{tool_use_id}"


def _response_digest(response: list[Mapping[str, Any]]) -> str:
    encoded = json.dumps(
        response,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def prepare_list_agents_pre_tool_use(
    payload: Mapping[str, Any],
    *,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Bind one list_agents invocation to the current execution observation bases."""
    session_id, turn_id, tool_use_id = _hook_identity(payload, expected_event=PRE_TOOL_USE)
    prepared: dict[str, Any] = {}

    def mutate(current: dict[str, Any]) -> None:
        if current.get("root_session_id") != session_id:
            raise HostEvidenceError("Host observation is bound to another root session")
        if any(
            isinstance(event, Mapping)
            and event.get("kind") in {PREPARE_KIND, RECEIPT_KIND}
            and event.get("tool_use_id") == tool_use_id
            for event in current.get("accounting_refs", [])
        ):
            raise HostEvidenceError("list_agents tool_use_id was already prepared or consumed")
        bases = [
            state.observation_basis(current, execution_id=str(execution["execution_id"]))
            for execution in current.get("executions", [])
            if isinstance(execution, Mapping)
        ]
        event = {
            "ref": _prepare_ref(tool_use_id),
            "kind": PREPARE_KIND,
            "turn_id": turn_id,
            "tool_use_id": tool_use_id,
            "bases": bases,
        }
        current["accounting_refs"].append(event)
        prepared.update(event)

    state.mutate_state(session_id, mutate, temp_root=temp_root)
    return prepared


def _matching_prepare(
    current: Mapping[str, Any], *, turn_id: str, tool_use_id: str
) -> Mapping[str, Any] | None:
    matches = [
        event
        for event in current.get("accounting_refs", [])
        if isinstance(event, Mapping)
        and event.get("kind") == PREPARE_KIND
        and event.get("turn_id") == turn_id
        and event.get("tool_use_id") == tool_use_id
    ]
    if len(matches) > 1:
        raise HostEvidenceError("list_agents observation has multiple preparation records")
    return matches[0] if matches else None


def _matching_receipt(
    current: Mapping[str, Any], *, turn_id: str, tool_use_id: str
) -> Mapping[str, Any] | None:
    matches = [
        event
        for event in current.get("accounting_refs", [])
        if isinstance(event, Mapping)
        and event.get("kind") == RECEIPT_KIND
        and event.get("turn_id") == turn_id
        and event.get("tool_use_id") == tool_use_id
    ]
    if len(matches) > 1:
        raise HostEvidenceError("list_agents observation has multiple consumption receipts")
    return matches[0] if matches else None


def ingest_list_agents_post_tool_use(
    payload: Mapping[str, Any],
    *,
    temp_root: str | os.PathLike[str] | None = None,
) -> list[dict[str, Any]]:
    """Reconcile one genuine list_agents result against its PreToolUse-captured basis."""
    session_id, turn_id, tool_use_id = _hook_identity(payload, expected_event=POST_TOOL_USE)
    response = _strict_response(payload.get("tool_response"))
    response_digest = _response_digest(response)
    current = state.load_state(session_id, temp_root=temp_root)
    if current is None:
        raise HostEvidenceError("active V4 state is unavailable for Host observation")
    if current.get("root_session_id") != session_id:
        raise HostEvidenceError("Host observation is bound to another root session")

    prepared = _matching_prepare(current, turn_id=turn_id, tool_use_id=tool_use_id)
    if prepared is None:
        receipt = _matching_receipt(current, turn_id=turn_id, tool_use_id=tool_use_id)
        if receipt is not None and receipt.get("response_digest") == response_digest:
            return []
        raise HostEvidenceError("list_agents PostToolUse has no matching PreToolUse basis")

    bases = prepared.get("bases")
    if not isinstance(bases, list) or not all(isinstance(item, Mapping) for item in bases):
        raise HostEvidenceError("list_agents preparation has invalid observation bases")
    by_name = {str(item["agent_name"]): item for item in response}
    outcomes: list[dict[str, Any]] = []
    for basis in bases:
        execution_id = basis.get("execution_id")
        if not _nonempty(execution_id):
            raise HostEvidenceError("list_agents preparation has invalid execution identity")
        refreshed = state.load_state(session_id, temp_root=temp_root)
        if refreshed is None:
            raise HostEvidenceError("V4 state disappeared during Host observation")
        matches = [
            execution
            for execution in refreshed.get("executions", [])
            if isinstance(execution, Mapping) and execution.get("execution_id") == execution_id
        ]
        if len(matches) != 1:
            raise HostEvidenceError("prepared Host observation execution no longer resolves exactly")
        expected_name = f"/root/{matches[0]['native_task_name']}"
        item = by_name.get(expected_name)
        if item is None:
            continue
        normalized = host_capabilities.normalize_agent_status(item["status"])
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
                "execution_id": execution_id,
                "agent_name": expected_name,
                "host_state": normalized["state"],
                "reconcile_status": outcome["reconcile_status"],
                "idempotent": outcome.get("idempotent", False),
            }
        )

    def finalize(latest: dict[str, Any]) -> None:
        prep = _matching_prepare(latest, turn_id=turn_id, tool_use_id=tool_use_id)
        if prep is None:
            receipt = _matching_receipt(latest, turn_id=turn_id, tool_use_id=tool_use_id)
            if receipt is not None and receipt.get("response_digest") == response_digest:
                return
            raise HostEvidenceError("list_agents observation preparation disappeared before receipt")
        latest["accounting_refs"].remove(prep)
        latest["accounting_refs"].append(
            {
                "ref": _receipt_ref(tool_use_id),
                "kind": RECEIPT_KIND,
                "turn_id": turn_id,
                "tool_use_id": tool_use_id,
                "response_digest": response_digest,
            }
        )

    state.mutate_state(session_id, finalize, temp_root=temp_root)
    return outcomes


def runtime_temp_root() -> Path | None:
    raw = os.environ.get("SUBAGENTS_DISPATCH_TEMP_ROOT")
    if raw is None or not raw.strip():
        return None
    return Path(raw)
