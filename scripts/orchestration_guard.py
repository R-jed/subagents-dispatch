#!/usr/bin/env python3
"""Managed lifecycle Hook guard for V4 PendingControl.

During V4 development this guard preserves V3 spawn compatibility while enforcing
V4 single-use controls. Managed children never receive lifecycle authority.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import dispatch_control_v4 as control
import dispatch_state as state_v3
import dispatch_state_v4 as state_v4
import spawn_guard


PRE_TOOL_USE = "PreToolUse"
POST_TOOL_USE = "PostToolUse"
SUBAGENT_STOP = "SubagentStop"
LIFECYCLE_TOOLS = {"spawn_agent", "followup_task", "interrupt_agent"}
RESERVED_AGENT_PREFIX = "subagents_dispatch_"
MAX_STDIN_BYTES = 2 * 1024 * 1024
BLOCKING_EXIT_CODE = 2


class GuardStateError(RuntimeError):
    """Current Dispatch state cannot be classified safely."""


def _block(reason: str) -> dict[str, Any]:
    return {
        "decision": "block",
        "reason": f"subagents-dispatch orchestration guard: {reason}",
    }


def _stop(reason: str) -> dict[str, Any]:
    return {
        "continue": False,
        "stopReason": reason,
        "reason": reason,
    }


def _is_managed_agent_type(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(RESERVED_AGENT_PREFIX)


def _runtime_temp_root() -> Path | None:
    raw = os.environ.get("SUBAGENTS_DISPATCH_TEMP_ROOT")
    if raw is None or not raw.strip():
        return None
    return Path(raw)


def _load_family(
    session_id: str,
    *,
    temp_root: str | os.PathLike[str] | None,
) -> tuple[str, dict[str, Any] | None]:
    v4_error: Exception | None = None
    try:
        current_v4 = state_v4.load_state(session_id, temp_root=temp_root)
    except (state_v4.StateCorruptError, state_v4.StateIdentityError, state_v4.StatePathError) as exc:
        current_v4 = None
        v4_error = exc
    if current_v4 is not None:
        return "v4", current_v4

    v3_error: Exception | None = None
    try:
        current_v3 = state_v3.load_state(session_id, temp_root=temp_root)
    except (state_v3.StateCorruptError, state_v3.StateIdentityError, state_v3.StatePathError) as exc:
        current_v3 = None
        v3_error = exc
    if current_v3 is not None:
        return "v3", current_v3

    if v4_error is not None and v3_error is not None:
        raise GuardStateError("Dispatch state is corrupt, unsafe, or unclassifiable")
    return "none", None


def _session_id(payload: Mapping[str, Any]) -> str:
    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id.strip():
        raise GuardStateError("valid root session identity is required")
    return session_id


def _tool_input(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    value = payload.get("tool_input")
    if not isinstance(value, Mapping):
        raise control.ControlError("managed lifecycle tool_input must be an object")
    return value


def _tool_use_id(payload: Mapping[str, Any]) -> str:
    value = payload.get("tool_use_id")
    if not isinstance(value, str) or not value.strip():
        raise control.ControlError("managed lifecycle Hook requires tool_use_id")
    return value


def _managed_target_in_v4(
    current: Mapping[str, Any], tool_name: str, tool_input: Mapping[str, Any]
) -> bool:
    if tool_name == "spawn_agent":
        return _is_managed_agent_type(tool_input.get("agent_type"))
    target = tool_input.get("target")
    return isinstance(target, str) and control.target_is_managed(current, target)


def evaluate_pre_tool_use(
    payload: Mapping[str, Any],
    *,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any] | None:
    if payload.get("hook_event_name") != PRE_TOOL_USE:
        return None
    tool_name = payload.get("tool_name")
    if tool_name not in LIFECYCLE_TOOLS:
        return None

    if _is_managed_agent_type(payload.get("agent_type")):
        return _block("managed child Agents cannot invoke lifecycle-control tools")

    tool_input = _tool_input(payload)
    session_id = _session_id(payload)
    family, current = _load_family(session_id, temp_root=temp_root)

    if tool_name == "spawn_agent" and _is_managed_agent_type(tool_input.get("agent_type")):
        if family == "v3" or family == "none":
            return spawn_guard.evaluate_hook(payload, temp_root=temp_root)
        assert current is not None
        control.consume_prepared_control(
            session_id,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_use_id=_tool_use_id(payload),
            temp_root=temp_root,
        )
        return None

    if family == "v4":
        assert current is not None
        if not _managed_target_in_v4(current, tool_name, tool_input):
            return None
        control.consume_prepared_control(
            session_id,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_use_id=_tool_use_id(payload),
            temp_root=temp_root,
        )
    return None


def evaluate_post_tool_use(
    payload: Mapping[str, Any],
    *,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any] | None:
    if payload.get("hook_event_name") != POST_TOOL_USE:
        return None
    tool_name = payload.get("tool_name")
    if tool_name not in LIFECYCLE_TOOLS:
        return None
    if _is_managed_agent_type(payload.get("agent_type")):
        return _stop("managed child lifecycle call reached PostToolUse unexpectedly")

    session_id = _session_id(payload)
    family, current = _load_family(session_id, temp_root=temp_root)
    if family != "v4":
        return None
    assert current is not None
    tool_input = _tool_input(payload)
    tool_use_id = _tool_use_id(payload)

    inflight = [
        item
        for item in current["pending_controls"]
        if item.get("state") == "IN_FLIGHT" and item.get("tool_use_id") == tool_use_id
    ]
    if not inflight:
        if _managed_target_in_v4(current, tool_name, tool_input):
            return _stop("managed lifecycle PostToolUse has no matching IN_FLIGHT control")
        return None
    try:
        control.acknowledge_control(
            session_id,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_response=payload.get("tool_response"),
            tool_use_id=tool_use_id,
            temp_root=temp_root,
        )
    except control.ControlAlreadyAcknowledged:
        return None
    except control.ControlError:
        try:
            control.mark_control_unknown(
                session_id,
                tool_use_id=tool_use_id,
                temp_root=temp_root,
            )
        except Exception:
            pass
        return _stop("managed lifecycle acknowledgement is ambiguous; control quarantined")
    return None


def evaluate_subagent_stop(payload: Mapping[str, Any]) -> dict[str, Any] | None:
    if payload.get("hook_event_name") != SUBAGENT_STOP:
        return None
    if not _is_managed_agent_type(payload.get("agent_type")):
        return None
    return _stop(
        "managed subagent stops after its assigned turn; continuation requires Main PendingControl"
    )


def evaluate_hook(
    payload: Mapping[str, Any],
    *,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any] | None:
    event = payload.get("hook_event_name")
    if event == PRE_TOOL_USE:
        return evaluate_pre_tool_use(payload, temp_root=temp_root)
    if event == POST_TOOL_USE:
        return evaluate_post_tool_use(payload, temp_root=temp_root)
    if event == SUBAGENT_STOP:
        return evaluate_subagent_stop(payload)
    return None


def _emit_and_exit(result: Mapping[str, Any]) -> None:
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))


def _pre_fail_closed(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(BLOCKING_EXIT_CODE)


def _stop_fail_closed(message: str) -> None:
    _emit_and_exit(_stop(message))


def main() -> None:
    raw = sys.stdin.buffer.read(MAX_STDIN_BYTES + 1)
    if len(raw) > MAX_STDIN_BYTES:
        _pre_fail_closed("subagents-dispatch orchestration guard blocked oversized Hook input")
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        _pre_fail_closed("subagents-dispatch orchestration guard blocked invalid Hook JSON")
    if not isinstance(payload, dict):
        _pre_fail_closed("subagents-dispatch orchestration guard requires object Hook payload")

    event = payload.get("hook_event_name")
    try:
        result = evaluate_hook(payload, temp_root=_runtime_temp_root())
    except Exception:
        if event in {POST_TOOL_USE, SUBAGENT_STOP}:
            _stop_fail_closed("subagents-dispatch orchestration guard unavailable; execution stopped")
            return
        _pre_fail_closed("subagents-dispatch orchestration guard unavailable; lifecycle call blocked")
        return
    if result is not None:
        _emit_and_exit(result)


if __name__ == "__main__":
    main()
