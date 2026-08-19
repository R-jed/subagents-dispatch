#!/usr/bin/env python3
"""Managed lifecycle and Host-evidence Hook guard for V4 orchestration."""

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
import host_evidence_v4 as host_evidence
import managed_execution_v4 as managed_execution
import spawn_guard


PRE_TOOL_USE = "PreToolUse"
POST_TOOL_USE = "PostToolUse"
SUBAGENT_STOP = "SubagentStop"
LIFECYCLE_TOOLS = {"spawn_agent", "followup_task", "interrupt_agent"}
OBSERVATION_TOOL = "list_agents"
PEER_MESSAGE_TOOL = "send_message"
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


def _tool_leaf_name(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.rsplit(".", 1)[-1]


def _canonical_tool_payload(payload: Mapping[str, Any], tool_name: str) -> dict[str, Any]:
    normalized = dict(payload)
    normalized["tool_name"] = tool_name
    return normalized


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


def _prepare_host_observation(
    payload: Mapping[str, Any],
    *,
    temp_root: str | os.PathLike[str] | None,
) -> dict[str, Any] | None:
    try:
        host_evidence.prepare_list_agents_pre_tool_use(
            _canonical_tool_payload(payload, OBSERVATION_TOOL), temp_root=temp_root
        )
    except host_evidence.HostEvidenceError as exc:
        return _block(str(exc))
    except Exception:
        return _block("Host lifecycle observation could not be prepared safely")
    return None


def _consume_capacity_before_fresh_spawn(
    session_id: str,
    *,
    temp_root: str | os.PathLike[str] | None,
) -> dict[str, Any] | None:
    """Atomically consume one current occupancy truth before a managed fresh spawn."""
    consumed = False

    def mutate(current: dict[str, Any]) -> None:
        nonlocal consumed
        matches = [
            event
            for event in current.get("accounting_refs", [])
            if isinstance(event, Mapping)
            and event.get("kind") == state_v4.HOST_CAPACITY_OBSERVATION_KIND
        ]
        if len(matches) > 1:
            raise GuardStateError("multiple current Host capacity observations are unsafe")
        if not matches:
            return
        current["accounting_refs"].remove(matches[0])
        consumed = True

    try:
        state_v4.mutate_state(session_id, mutate, temp_root=temp_root)
    except Exception:
        return _block("Host capacity truth could not be consumed safely before lifecycle mutation")
    if not consumed:
        return _block("fresh managed spawn requires current authoritative Host capacity truth")
    return None


def _invalidate_capacity_before_lifecycle(
    session_id: str,
    *,
    temp_root: str | os.PathLike[str] | None,
) -> dict[str, Any] | None:
    """Invalidate prior occupancy truth before a non-fresh lifecycle mutation."""
    try:
        host_evidence.invalidate_host_capacity_observation(session_id, temp_root=temp_root)
    except Exception:
        return _block("Host capacity truth could not be consumed safely before lifecycle mutation")
    return None


def evaluate_pre_tool_use(
    payload: Mapping[str, Any],
    *,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any] | None:
    if payload.get("hook_event_name") != PRE_TOOL_USE:
        return None
    tool_name = _tool_leaf_name(payload.get("tool_name"))

    if tool_name == PEER_MESSAGE_TOOL:
        if _is_managed_agent_type(payload.get("agent_type")):
            return _block("managed child Agents cannot send peer messages to other Agents")
        return None

    if tool_name == OBSERVATION_TOOL:
        session_id = _session_id(payload)
        family, _ = _load_family(session_id, temp_root=temp_root)
        if family != "v4":
            return None
        return _prepare_host_observation(payload, temp_root=temp_root)

    if tool_name not in LIFECYCLE_TOOLS:
        return None
    if _is_managed_agent_type(payload.get("agent_type")):
        return _block("managed child Agents cannot invoke lifecycle-control tools")

    tool_input = _tool_input(payload)
    session_id = _session_id(payload)
    family, current = _load_family(session_id, temp_root=temp_root)

    if family == "v4":
        managed_fresh_spawn = tool_name == "spawn_agent" and _is_managed_agent_type(
            tool_input.get("agent_type")
        )
        if managed_fresh_spawn:
            capacity_block = _consume_capacity_before_fresh_spawn(
                session_id, temp_root=temp_root
            )
        else:
            capacity_block = _invalidate_capacity_before_lifecycle(
                session_id, temp_root=temp_root
            )
        if capacity_block is not None:
            return capacity_block

    if tool_name == "spawn_agent" and _is_managed_agent_type(tool_input.get("agent_type")):
        if family == "v3" or family == "none":
            return spawn_guard.evaluate_hook(
                _canonical_tool_payload(payload, tool_name), temp_root=temp_root
            )
        assert current is not None
        try:
            managed_execution.validate_actual_spawn_input(current, tool_input=tool_input)
        except managed_execution.ManagedExecutionContractError as exc:
            return _block(str(exc))
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


def _evaluate_host_observation(
    payload: Mapping[str, Any],
    *,
    temp_root: str | os.PathLike[str] | None,
) -> dict[str, Any] | None:
    try:
        host_evidence.ingest_list_agents_post_tool_use(
            _canonical_tool_payload(payload, OBSERVATION_TOOL), temp_root=temp_root
        )
    except host_evidence.HostEvidenceError:
        return _block("Host lifecycle observation is invalid or unbound; tool result rejected")
    except Exception:
        return _block("Host lifecycle observation could not be persisted safely; tool result rejected")
    return None


def _invalidate_capacity(
    session_id: str,
    *,
    temp_root: str | os.PathLike[str] | None,
) -> dict[str, Any] | None:
    try:
        host_evidence.invalidate_host_capacity_observation(session_id, temp_root=temp_root)
    except Exception:
        return _block("Host capacity truth could not be invalidated safely; tool result rejected")
    return None


def evaluate_post_tool_use(
    payload: Mapping[str, Any],
    *,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any] | None:
    if payload.get("hook_event_name") != POST_TOOL_USE:
        return None
    tool_name = _tool_leaf_name(payload.get("tool_name"))
    if tool_name == PEER_MESSAGE_TOOL:
        return None
    if tool_name == OBSERVATION_TOOL:
        session_id = _session_id(payload)
        family, _ = _load_family(session_id, temp_root=temp_root)
        if family != "v4":
            return None
        return _evaluate_host_observation(payload, temp_root=temp_root)
    if tool_name not in LIFECYCLE_TOOLS:
        return None
    if _is_managed_agent_type(payload.get("agent_type")):
        return _block("managed child lifecycle call reached PostToolUse unexpectedly")

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
    managed_target = _managed_target_in_v4(current, tool_name, tool_input)
    if not inflight and not managed_target:
        return _invalidate_capacity(session_id, temp_root=temp_root)
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
        if inflight:
            try:
                control.mark_control_unknown(
                    session_id,
                    tool_use_id=tool_use_id,
                    temp_root=temp_root,
                )
            except Exception:
                pass
        return _block(
            "managed lifecycle acknowledgement is ambiguous; control quarantined and tool result rejected"
        )
    return _invalidate_capacity(session_id, temp_root=temp_root)


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


def _post_fail_closed(message: str) -> None:
    _emit_and_exit(_block(message))


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
        if event == POST_TOOL_USE:
            _post_fail_closed(
                "subagents-dispatch orchestration guard unavailable; tool result rejected"
            )
            return
        if event == SUBAGENT_STOP:
            _stop_fail_closed("subagents-dispatch orchestration guard unavailable; child stopped")
            return
        _pre_fail_closed("subagents-dispatch orchestration guard unavailable; lifecycle call blocked")
        return
    if result is not None:
        _emit_and_exit(result)


if __name__ == "__main__":
    main()
