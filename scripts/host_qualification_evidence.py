#!/usr/bin/env python3
"""Collect maintainer-only Host qualification evidence from local Codex rollouts.

This helper is deliberately outside the shipped Plugin manifest. It resolves native
child identity from an exact Host task address, inspects the current root's latest
turn, and emits privacy-safe aggregate rollout facts. It never emits prompts,
assistant output, reasoning, environment values, source contents, or raw tool payloads.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Iterable, NoReturn


ROOT = Path(__file__).resolve().parent
INSPECTOR_PATH = ROOT / "inspect-agent-runtime.py"
AGENT_PATH = re.compile(r"^/root/(?!root$)[a-z0-9_]+$")
SESSION_META_LINE = re.compile(r'"type"\s*:\s*"session_meta"')
AGENT_CONTROL_TOOLS = frozenset(
    {"spawn_agent", "send_message", "followup_task", "interrupt_agent"}
)
AGENT_LAYER_TOOLS = frozenset(
    {*AGENT_CONTROL_TOOLS, "wait_agent", "list_agents"}
)
OBSERVED_EVENT_TYPES = frozenset(
    {"session_meta", "turn_context", "event_msg", "response_item", "context_compacted"}
)


def fail(message: str) -> NoReturn:
    raise SystemExit(f"ERROR: {message}")


def load_inspector():
    spec = importlib.util.spec_from_file_location(
        "subagents_dispatch_runtime_inspector", INSPECTOR_PATH
    )
    if spec is None or spec.loader is None:
        fail("could not load inspect-agent-runtime.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


INSPECTOR = load_inspector()


def parse_rfc3339(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        fail(f"{label} must be a non-empty RFC3339 timestamp")
    raw = value.strip()
    normalized = raw[:-1] + "+00:00" if raw.endswith(("Z", "z")) else raw
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        fail(f"{label} must be a valid RFC3339 timestamp: {exc}")
    if parsed.tzinfo is None:
        fail(f"{label} must include a timezone")
    return parsed.astimezone(timezone.utc)


def utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def resolve_sessions_dir(path: Path) -> Path:
    if not path.is_absolute():
        fail("sessions directory must be absolute")
    if path.is_symlink():
        fail("refusing symlinked sessions directory")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        fail(f"sessions directory is unavailable: {exc}")
    if not resolved.is_dir():
        fail("sessions path is not a directory")
    return resolved


def rollout_files(sessions_dir: Path) -> Iterable[Path]:
    for current, dirnames, filenames in os.walk(sessions_dir, followlinks=False):
        current_path = Path(current)
        dirnames[:] = [
            name for name in dirnames if not (current_path / name).is_symlink()
        ]
        for name in sorted(filenames):
            if not name.startswith("rollout-") or not name.endswith(".jsonl"):
                continue
            candidate = current_path / name
            if candidate.is_symlink():
                fail("refusing symlinked rollout file during Host evidence resolution")
            try:
                resolved = candidate.resolve(strict=True)
                resolved.relative_to(sessions_dir)
            except (OSError, ValueError) as exc:
                fail(f"unsafe rollout path during Host evidence resolution: {exc}")
            if not resolved.is_file():
                fail("rollout candidate is not a regular file")
            yield resolved


def json_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        INSPECTOR.iter_stable_rollout_lines(path), start=1
    ):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            fail(f"invalid rollout JSON in {path.name} at line {line_number}: {exc}")
        if not isinstance(record, dict):
            fail(f"rollout record in {path.name} at line {line_number} is not an object")
        records.append(record)
    return records


def observed_records(path: Path) -> list[dict[str, Any]]:
    return [record for record in json_records(path) if record.get("type") in OBSERVED_EVENT_TYPES]


def session_meta_records(path: Path) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Read only session_meta candidates while scanning unrelated rollouts.

    The task-address resolver may inspect many historical rollout files. Unrelated
    payload corruption must not block identity resolution, while malformed or
    ambiguous session metadata remains a hard stop.
    """

    matches: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for line_number, line in enumerate(
        INSPECTOR.iter_stable_rollout_lines(path), start=1
    ):
        if not SESSION_META_LINE.search(line):
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            fail(
                f"invalid session_meta JSON in {path.name} at line {line_number}: {exc}"
            )
        if not isinstance(record, dict) or record.get("type") != "session_meta":
            continue
        payload = INSPECTOR.payload_object(record, line_number)
        matches.append((record, payload))
    return matches


def resolve_child_by_agent_path(
    sessions_dir: Path,
    *,
    agent_path: str,
    since: datetime,
    expected_parent_thread_id: str | None,
    expected_agent_role: str | None,
) -> dict[str, Any]:
    path_value = agent_path.strip()
    if not AGENT_PATH.fullmatch(path_value):
        fail("agent path must be a canonical /root/<task> Host task address")

    matches: list[dict[str, Any]] = []
    for rollout in rollout_files(sessions_dir):
        sessions = session_meta_records(rollout)
        if not sessions:
            continue
        relevant = [
            (record, payload)
            for record, payload in sessions
            if INSPECTOR.optional_text(payload.get("agent_path")) == path_value
        ]
        if not relevant:
            continue
        if len(sessions) != 1 or len(relevant) != 1:
            fail("matching agent path appears in ambiguous session metadata")
        record, payload = relevant[0]
        observed_at = parse_rfc3339(
            record.get("timestamp"), "matching session_meta timestamp"
        )
        if observed_at < since:
            continue

        thread = INSPECTOR.optional_text(payload.get("id"))
        if thread is None:
            fail("matching session_meta does not expose child thread id")
        thread = INSPECTOR.canonical_uuid(thread, "matching session_meta.id")

        parent = INSPECTOR.optional_text(payload.get("parent_thread_id"))
        if parent is not None:
            parent = INSPECTOR.canonical_uuid(
                parent, "matching session_meta.parent_thread_id"
            )
        role = INSPECTOR.optional_text(payload.get("agent_role"))

        if expected_parent_thread_id is not None and parent != expected_parent_thread_id:
            fail("matching agent path has the wrong parent_thread_id")
        if expected_agent_role is not None and role != expected_agent_role:
            fail("matching agent path has the wrong agent_role")

        matches.append(
            {
                "thread_id": thread,
                "parent_thread_id": parent,
                "agent_role": role,
                "agent_path": path_value,
                "session_observed_at": utc_text(observed_at),
                "runtime_version": INSPECTOR.optional_text(payload.get("cli_version")),
            }
        )

    if not matches:
        fail("no rollout matched the requested agent path at or after the cutoff")
    if len(matches) != 1:
        fail("multiple rollouts matched the requested agent path at or after the cutoff")
    return matches[0]


def inspect_primary(sessions_dir: Path, thread_id: str) -> dict[str, Any]:
    thread = INSPECTOR.canonical_uuid(thread_id, "thread_id")
    rollout = INSPECTOR.find_exact_rollout(sessions_dir, thread)
    records = observed_records(rollout)
    sessions = [record for record in records if record.get("type") == "session_meta"]
    turns = [record for record in records if record.get("type") == "turn_context"]
    if len(sessions) != 1:
        fail("primary rollout must contain exactly one session_meta record")
    if not turns:
        fail("primary rollout contains no turn_context records")

    session = INSPECTOR.payload_object(sessions[0], 1)
    observed_thread = INSPECTOR.optional_text(session.get("id"))
    if observed_thread is None:
        fail("primary session_meta does not expose thread id")
    observed_thread = INSPECTOR.canonical_uuid(
        observed_thread, "primary session_meta.id"
    )
    if observed_thread != thread:
        fail("primary session_meta does not identify the requested thread")

    parent = INSPECTOR.optional_text(session.get("parent_thread_id"))
    if parent is not None:
        fail("primary inspection requires a root thread with no parent_thread_id")
    role = INSPECTOR.optional_text(session.get("agent_role"))
    if role is not None:
        fail("primary inspection requires a root thread without an agent_role")

    session_id = INSPECTOR.optional_text(session.get("session_id"))
    if session_id is None:
        fail("primary session_meta does not expose session_id")

    ordered_turns: list[tuple[datetime, dict[str, Any]]] = []
    for index, record in enumerate(turns, start=1):
        timestamp = parse_rfc3339(
            record.get("timestamp"), f"turn_context[{index}] timestamp"
        )
        ordered_turns.append(
            (timestamp, INSPECTOR.payload_object(record, index))
        )
    latest_at, latest = max(ordered_turns, key=lambda item: item[0])

    return {
        "session_id": session_id,
        "thread_id": thread,
        "parent_thread_id": None,
        "model": INSPECTOR.optional_text(latest.get("model")),
        "effort": INSPECTOR.optional_text(latest.get("effort")),
        "model_provider": INSPECTOR.optional_text(latest.get("model_provider"))
        or INSPECTOR.optional_text(session.get("model_provider")),
        "cwd": INSPECTOR.optional_text(latest.get("cwd"))
        or INSPECTOR.optional_text(session.get("cwd")),
        "runtime_version": INSPECTOR.optional_text(session.get("cli_version")),
        "multi_agent_version": INSPECTOR.optional_text(
            latest.get("multi_agent_version")
        ),
        "latest_turn_at": utc_text(latest_at),
    }


def call_name(payload: dict[str, Any]) -> str | None:
    for field in ("name", "tool_name", "recipient"):
        value = INSPECTOR.optional_text(payload.get(field))
        if value is not None:
            return value.rsplit(".", 1)[-1]
    return None


def inspect_aggregate(
    sessions_dir: Path,
    thread_id: str,
    *,
    expected_parent_thread_id: str | None,
    expected_agent_role: str | None,
) -> dict[str, Any]:
    thread = INSPECTOR.canonical_uuid(thread_id, "thread_id")
    rollout = INSPECTOR.find_exact_rollout(sessions_dir, thread)
    route = INSPECTOR.inspect_rollout(
        rollout,
        thread_id=thread,
        expected_parent_thread_id=expected_parent_thread_id,
        expected_agent_role=expected_agent_role,
    )
    records = observed_records(rollout)

    turn_count = 0
    tool_call_count = 0
    tool_names_complete = True
    control_tools: list[str] = []
    agent_layer_tools: list[str] = []
    compaction_count = 0
    observed_timestamps: list[datetime] = []
    timestamps_complete = True
    token_event_count = 0
    token_values: list[int] = []
    token_usage_complete = True

    for record in records:
        record_type = record.get("type")
        timestamp_value = record.get("timestamp")
        if timestamp_value is None:
            timestamps_complete = False
        else:
            try:
                observed_timestamps.append(
                    parse_rfc3339(timestamp_value, "rollout event timestamp")
                )
            except SystemExit:
                timestamps_complete = False

        if record_type == "turn_context":
            turn_count += 1
            continue

        payload = record.get("payload")
        if record_type == "response_item":
            if not isinstance(payload, dict):
                fail("response_item payload must be an object")
            payload_type = INSPECTOR.optional_text(payload.get("type"))
            if payload_type and payload_type.endswith("_call"):
                tool_call_count += 1
                name = call_name(payload)
                if name is None:
                    tool_names_complete = False
                elif name in AGENT_LAYER_TOOLS:
                    agent_layer_tools.append(name)
                    if name in AGENT_CONTROL_TOOLS:
                        control_tools.append(name)
            continue

        if record_type == "context_compacted":
            compaction_count += 1
            continue

        if record_type != "event_msg":
            continue
        if not isinstance(payload, dict):
            fail("event_msg payload must be an object")
        event_type = INSPECTOR.optional_text(payload.get("type"))
        if event_type == "context_compacted":
            compaction_count += 1
        elif event_type == "token_count":
            token_event_count += 1
            info = payload.get("info")
            total = (
                info.get("total_token_usage", {}).get("total_tokens")
                if isinstance(info, dict)
                and isinstance(info.get("total_token_usage"), dict)
                else None
            )
            if isinstance(total, bool) or not isinstance(total, int) or total < 0:
                token_usage_complete = False
            else:
                token_values.append(total)

    latest_event_at = (
        utc_text(max(observed_timestamps))
        if timestamps_complete and observed_timestamps
        else None
    )
    raw_tokens = (
        max(token_values)
        if token_event_count > 0
        and token_usage_complete
        and len(token_values) == token_event_count
        else None
    )
    agent_control_call_count = len(control_tools) if tool_names_complete else None
    agent_layer_call_count = len(agent_layer_tools) if tool_names_complete else None

    return {
        "thread_id": route["thread_id"],
        "parent_thread_id": route["parent_thread_id"],
        "agent_role": route["agent_role"],
        "model": route["model"],
        "effort": route["effort"],
        "sandbox_policy_type": route["sandbox_policy_type"],
        "permission_profile_type": route["permission_profile_type"],
        "turn_count": turn_count,
        "tool_call_count": tool_call_count,
        "agent_control_call_count": agent_control_call_count,
        "agent_control_tools_seen": sorted(set(control_tools))
        if tool_names_complete
        else None,
        "agent_layer_call_count": agent_layer_call_count,
        "agent_layer_tools_seen": sorted(set(agent_layer_tools))
        if tool_names_complete
        else None,
        "compaction_count": compaction_count,
        "raw_tokens": raw_tokens,
        "latest_event_at": latest_event_at,
        "timestamp_observation_complete": timestamps_complete,
        "tool_name_observation_complete": tool_names_complete,
        "token_usage_observation_complete": token_event_count > 0
        and token_usage_complete
        and len(token_values) == token_event_count,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect maintainer-only Host qualification evidence."
    )
    parser.add_argument(
        "--sessions-dir",
        type=Path,
        required=True,
        help="Absolute Codex sessions directory.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    resolve = subparsers.add_parser("resolve-child")
    resolve.add_argument("--agent-path", required=True)
    resolve.add_argument("--since", required=True)
    resolve.add_argument("--expected-parent-thread-id")
    resolve.add_argument("--expected-agent-role")

    primary = subparsers.add_parser("primary")
    primary.add_argument("thread_id")

    aggregate = subparsers.add_parser("aggregate")
    aggregate.add_argument("thread_id")
    aggregate.add_argument("--expected-parent-thread-id")
    aggregate.add_argument("--expected-agent-role")

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sessions = resolve_sessions_dir(args.sessions_dir)

    if args.command == "resolve-child":
        expected_parent = (
            INSPECTOR.canonical_uuid(
                args.expected_parent_thread_id, "expected parent thread id"
            )
            if args.expected_parent_thread_id
            else None
        )
        expected_role = INSPECTOR.optional_text(args.expected_agent_role)
        if args.expected_agent_role is not None and expected_role is None:
            fail("expected agent role must be a non-empty string")
        result = resolve_child_by_agent_path(
            sessions,
            agent_path=args.agent_path,
            since=parse_rfc3339(args.since, "since"),
            expected_parent_thread_id=expected_parent,
            expected_agent_role=expected_role,
        )
    elif args.command == "primary":
        result = inspect_primary(sessions, args.thread_id)
    else:
        expected_parent = (
            INSPECTOR.canonical_uuid(
                args.expected_parent_thread_id, "expected parent thread id"
            )
            if args.expected_parent_thread_id
            else None
        )
        expected_role = INSPECTOR.optional_text(args.expected_agent_role)
        if args.expected_agent_role is not None and expected_role is None:
            fail("expected agent role must be a non-empty string")
        result = inspect_aggregate(
            sessions,
            args.thread_id,
            expected_parent_thread_id=expected_parent,
            expected_agent_role=expected_role,
        )

    json.dump(result, sys.stdout, sort_keys=True, separators=(",", ":"))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
