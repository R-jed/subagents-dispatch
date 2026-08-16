#!/usr/bin/env python3
"""Read-only PreToolUse guard for subagents-dispatch managed spawns."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dispatch_state import (  # type: ignore[import-not-found]
    StateCorruptError,
    StateIdentityError,
    StatePathError,
    load_state,
)
from policy import POLICY_CONTRACT_PATH, load_policy_contract  # type: ignore[import-not-found]


EXPECTED_EVENT = "PreToolUse"
EXPECTED_TOOL = "spawn_agent"
RESERVED_AGENT_PREFIX = "subagents_dispatch_"
MAX_STDIN_BYTES = 2 * 1024 * 1024


class GuardContractError(RuntimeError):
    """Bundled guard policy is malformed or incomplete."""


def _block(code: str, message: str) -> dict[str, Any]:
    return {
        "decision": "block",
        "reason": f"subagents-dispatch spawn guard [{code}]: {message}",
    }


def _policy_shape(path: Path) -> tuple[dict[str, str], str, int]:
    try:
        policy = load_policy_contract(path)
    except RuntimeError as exc:
        raise GuardContractError("policy contract is unavailable") from exc
    roles = policy.get("roles")
    delegation = policy.get("delegation")
    if not isinstance(roles, dict) or not isinstance(delegation, dict):
        raise GuardContractError("policy contract is incomplete")
    agent_types: dict[str, str] = {}
    for role, spec in roles.items():
        if not isinstance(role, str) or not isinstance(spec, dict):
            raise GuardContractError("policy roles are invalid")
        agent_type = spec.get("agent_type")
        if not isinstance(agent_type, str) or not agent_type.startswith(RESERVED_AGENT_PREFIX):
            raise GuardContractError("policy Agent identity is invalid")
        agent_types[role] = agent_type
    fork_turns = delegation.get("fork_turns")
    max_depth = delegation.get("max_depth")
    if fork_turns != "none" or max_depth != 1:
        raise GuardContractError("delegation guard invariants are invalid")
    return agent_types, fork_turns, max_depth


def _is_reserved(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(RESERVED_AGENT_PREFIX)


def evaluate_hook(
    payload: Mapping[str, Any],
    *,
    temp_root: str | os.PathLike[str] | None = None,
    policy_path: Path = POLICY_CONTRACT_PATH,
) -> dict[str, Any] | None:
    """Return a blocking Hook response, or None for pass-through."""
    if payload.get("hook_event_name") != EXPECTED_EVENT or payload.get("tool_name") != EXPECTED_TOOL:
        return None

    tool_input = payload.get("tool_input")
    caller_agent_type = payload.get("agent_type")
    target_agent_type = tool_input.get("agent_type") if isinstance(tool_input, Mapping) else None

    if not _is_reserved(caller_agent_type) and not _is_reserved(target_agent_type):
        return None

    try:
        role_agent_types, expected_fork_turns, max_depth = _policy_shape(policy_path)
    except GuardContractError:
        return _block("POLICY_UNAVAILABLE", "managed spawn policy could not be verified")

    managed_agent_types = set(role_agent_types.values())
    if caller_agent_type in managed_agent_types:
        return _block(
            "DELEGATION_DEPTH",
            f"managed project children cannot spawn another agent; max delegation depth is {max_depth}",
        )

    if target_agent_type not in managed_agent_types:
        if _is_reserved(target_agent_type):
            return _block("AGENT_TYPE", "requested reserved agent_type is not a current production role")
        return None

    if not isinstance(tool_input, Mapping):
        return _block("TOOL_INPUT", "managed spawn requires an object tool_input")
    if tool_input.get("fork_turns") != expected_fork_turns:
        return _block(
            "FORK_TURNS",
            f"managed spawn requires explicit fork_turns={expected_fork_turns}",
        )

    task_name = tool_input.get("task_name")
    if not isinstance(task_name, str) or not task_name.strip():
        return _block("TASK_NAME", "managed spawn requires the prepared native task_name")
    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id.strip():
        return _block("STATE_IDENTITY", "managed spawn requires a valid root session identity")

    try:
        state = load_state(session_id, temp_root=temp_root)
    except (StateCorruptError, StateIdentityError, StatePathError):
        return _block("STATE_UNSAFE", "prepared Dispatch state is corrupt, unsafe, or ambiguous")
    if state is None:
        return _block("STATE_MISSING", "no prepared Dispatch state exists for this managed spawn")
    if state.get("pending_takeover") is not None:
        return _block("TAKEOVER_PENDING", "managed spawn is blocked while a takeover transition is unresolved")

    matches = [
        record
        for record in state.get("units", [])
        if isinstance(record, Mapping)
        and record.get("control_state") == "SPAWN_PENDING"
        and record.get("native_task_name") == task_name
    ]
    if len(matches) != 1:
        return _block("TASK_NAME", "task_name does not resolve to exactly one prepared SPAWN_PENDING attempt")

    record = matches[0]
    semantic_role = record.get("role")
    expected_agent_type = role_agent_types.get(semantic_role) if isinstance(semantic_role, str) else None
    if expected_agent_type is None:
        return _block("STATE_ROLE", "prepared state references an unknown production role")
    if target_agent_type != expected_agent_type:
        return _block(
            "AGENT_TYPE",
            "requested agent_type does not match the policy role bound to the prepared attempt",
        )
    return None


def _runtime_temp_root() -> Path | None:
    raw = os.environ.get("SUBAGENTS_DISPATCH_TEMP_ROOT")
    if raw is None or not raw.strip():
        return None
    return Path(raw)


def main() -> None:
    raw = sys.stdin.buffer.read(MAX_STDIN_BYTES + 1)
    if len(raw) > MAX_STDIN_BYTES:
        print("subagents-dispatch spawn guard input exceeded its bounded limit", file=sys.stderr)
        raise SystemExit(78)
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        print("subagents-dispatch spawn guard received invalid Hook JSON", file=sys.stderr)
        raise SystemExit(78)
    if not isinstance(payload, dict):
        print("subagents-dispatch spawn guard requires an object Hook payload", file=sys.stderr)
        raise SystemExit(78)

    try:
        result = evaluate_hook(payload, temp_root=_runtime_temp_root())
    except Exception as exc:
        print(
            f"subagents-dispatch spawn guard unavailable: {type(exc).__name__}",
            file=sys.stderr,
        )
        raise SystemExit(78) from None
    if result is not None:
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
