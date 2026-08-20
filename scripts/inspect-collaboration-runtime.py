#!/usr/bin/env python3
"""Emit allowlisted collaboration metadata from one exact Codex root rollout."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
from typing import Any, Iterator, NoReturn
from uuid import UUID

COLLAB_NAMESPACE = "collaboration"
COLLAB_TOOLS = {
    "spawn_agent",
    "followup_task",
    "interrupt_agent",
    "list_agents",
    "send_message",
    "wait_agent",
}
TARGET_LINE = re.compile(
    rb'"(?:namespace|name|call_id|sub_agent_activity|subagent_activity|SubAgentActivity)"'
)
NEWLINE_BOUNDARY = re.compile(br"\r\n|\r|\n")
READ_CHUNK_BYTES = 1024 * 1024
MAX_ROLLOUT_BYTES = 64 * 1024 * 1024
MAX_ROLLOUT_LINE_BYTES = 4 * 1024 * 1024


def fail(message: str) -> NoReturn:
    raise SystemExit(f"ERROR: {message}")


def canonical_uuid(value: str, label: str) -> str:
    raw = value.strip()
    try:
        parsed = UUID(raw)
    except (ValueError, AttributeError) as exc:
        fail(f"{label} must be a canonical UUID: {exc}")
    canonical = str(parsed)
    if raw != canonical:
        fail(f"{label} must use canonical lowercase UUID form")
    return canonical


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract allowlisted collaboration call/result/activity metadata from one root rollout."
    )
    parser.add_argument("thread_id", help="Exact root Codex thread/session UUID.")
    parser.add_argument("--sessions-dir", type=Path)
    parser.add_argument("--codex-home", type=Path)
    parser.add_argument("--call-id", help="Optional exact collaboration call id.")
    return parser.parse_args()


def resolve_sessions_dir(args: argparse.Namespace) -> Path:
    if args.sessions_dir is not None and args.codex_home is not None:
        fail("use only one of --sessions-dir or --codex-home")
    if args.sessions_dir is not None:
        root = args.sessions_dir.expanduser()
    else:
        codex_home = args.codex_home
        if codex_home is None:
            codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
        root = codex_home.expanduser() / "sessions"
    if not root.is_absolute():
        fail("sessions directory must be absolute")
    if root.is_symlink():
        fail("refusing symlinked sessions directory")
    try:
        resolved = root.resolve(strict=True)
    except OSError as exc:
        fail(f"sessions directory is unavailable: {exc}")
    if not resolved.is_dir():
        fail("sessions path is not a directory")
    return resolved


def find_exact_rollout(sessions_dir: Path, thread_id: str) -> Path:
    suffix = f"-{thread_id}.jsonl"
    matches: list[Path] = []
    for current, dirnames, filenames in os.walk(sessions_dir, followlinks=False):
        current_path = Path(current)
        dirnames[:] = [name for name in dirnames if not (current_path / name).is_symlink()]
        for name in filenames:
            if not name.startswith("rollout-") or not name.endswith(suffix):
                continue
            candidate = current_path / name
            if candidate.is_symlink():
                fail("refusing symlinked rollout file")
            try:
                resolved = candidate.resolve(strict=True)
                resolved.relative_to(sessions_dir)
            except (OSError, ValueError) as exc:
                fail(f"matched rollout is unsafe or unavailable: {exc}")
            if not resolved.is_file():
                fail("matched rollout is not a regular file")
            matches.append(resolved)
    if not matches:
        fail("no rollout filename matched the requested thread id")
    if len(matches) != 1:
        fail("multiple rollout filenames matched the requested thread id")
    return matches[0]


def _decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        fail(f"could not decode matched rollout as UTF-8: {exc}")


def _drain_lines(pending: bytearray, *, eof: bool) -> Iterator[str]:
    start = 0
    while True:
        match = NEWLINE_BOUNDARY.search(pending, start)
        if match is None:
            break
        if not eof and match.group() == b"\r" and match.end() == len(pending):
            break
        end = match.end()
        if end - start > MAX_ROLLOUT_LINE_BYTES:
            fail("matched rollout line exceeds maximum size")
        yield _decode(bytes(pending[start:end]))
        start = end
    if start:
        del pending[:start]
    if len(pending) > MAX_ROLLOUT_LINE_BYTES:
        fail("matched rollout line exceeds maximum size")


def iter_stable_rollout_lines(path: Path) -> Iterator[str]:
    try:
        expected = os.lstat(path)
    except OSError as exc:
        fail(f"matched rollout is unavailable before opening: {exc}")
    if not stat.S_ISREG(expected.st_mode):
        fail("matched rollout is not a regular file before opening")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        fail(f"could not open matched rollout safely: {exc}")
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (
            expected.st_dev,
            expected.st_ino,
        ):
            fail("matched rollout identity drifted while opening")
        if opened.st_size > MAX_ROLLOUT_BYTES:
            fail("matched rollout exceeds maximum size")
        total = 0
        pending = bytearray()
        while True:
            chunk = os.read(fd, READ_CHUNK_BYTES)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_ROLLOUT_BYTES:
                fail("matched rollout exceeds maximum size")
            pending.extend(chunk)
            yield from _drain_lines(pending, eof=False)
        yield from _drain_lines(pending, eof=True)
        if pending:
            yield _decode(bytes(pending))
        closed = os.fstat(fd)
        current = os.lstat(path)
        if (
            not stat.S_ISREG(current.st_mode)
            or (closed.st_dev, closed.st_ino) != (opened.st_dev, opened.st_ino)
            or (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino)
            or closed.st_size != opened.st_size
            or closed.st_mtime_ns != opened.st_mtime_ns
            or current.st_size != closed.st_size
            or current.st_mtime_ns != closed.st_mtime_ns
        ):
            fail("matched rollout changed while being read")
    finally:
        os.close(fd)


def nonempty(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def parse_arguments(raw: Any, call_id: str) -> dict[str, Any]:
    if not isinstance(raw, str):
        fail(f"collaboration call {call_id} arguments must be JSON text")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        fail(f"collaboration call {call_id} arguments are invalid JSON: {exc}")
    if not isinstance(value, dict):
        fail(f"collaboration call {call_id} arguments must decode to an object")
    return value


def authorization_projection(name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "spawn_agent":
        return {
            "task_name": nonempty(args.get("task_name")),
            "agent_type": nonempty(args.get("agent_type")),
            "fork_turns": nonempty(args.get("fork_turns")),
        }
    if name in {"followup_task", "interrupt_agent", "send_message"}:
        return {"target": nonempty(args.get("target"))}
    return {}


def output_summary(output: Any, tool_name: str) -> dict[str, Any]:
    summary: dict[str, Any] = {"observed": True, "recognized_success": False}
    if tool_name == "spawn_agent" and isinstance(output, str):
        try:
            decoded = json.loads(output)
        except json.JSONDecodeError:
            return summary
        if isinstance(decoded, dict):
            task_name = nonempty(decoded.get("task_name"))
            if task_name is not None:
                summary["recognized_success"] = True
                summary["task_name"] = task_name
    elif tool_name in {"followup_task", "send_message"} and output == "":
        summary["recognized_success"] = True
    elif tool_name == "interrupt_agent" and isinstance(output, str):
        try:
            decoded = json.loads(output)
        except json.JSONDecodeError:
            return summary
        if isinstance(decoded, dict) and "previous_status" in decoded:
            summary["recognized_success"] = True
            previous = decoded.get("previous_status")
            if isinstance(previous, str):
                summary["previous_status"] = previous
    return summary


def event_activity(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    candidates = [payload]
    for key in ("item", "turn_item"):
        value = payload.get(key)
        if isinstance(value, dict):
            candidates.append(value)
    for item in candidates:
        item_type = item.get("type")
        if item_type not in {"sub_agent_activity", "subagent_activity", "SubAgentActivity"}:
            continue
        legacy_id = nonempty(item.get("id"))
        event_id = nonempty(item.get("event_id"))
        if legacy_id is not None and event_id is not None and legacy_id != event_id:
            fail("sub-agent activity id/event_id conflict")
        item_id = event_id or legacy_id
        agent_thread_id = nonempty(item.get("agent_thread_id"))
        agent_path = nonempty(item.get("agent_path"))
        kind = nonempty(item.get("kind"))
        if item_id and agent_thread_id and agent_path and kind:
            return {
                "call_id": item_id,
                "kind": kind,
                "agent_thread_id": agent_thread_id,
                "agent_path": agent_path,
            }
    return None


def inspect(path: Path, *, thread_id: str, call_filter: str | None) -> dict[str, Any]:
    calls: dict[str, dict[str, Any]] = {}
    outputs: dict[str, list[tuple[str | None, Any]]] = {}
    activities: dict[str, list[dict[str, Any]]] = {}
    for line_number, line in enumerate(iter_stable_rollout_lines(path), start=1):
        encoded = line.encode("utf-8", errors="ignore")
        if not TARGET_LINE.search(encoded):
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            fail(f"invalid target rollout JSON at line {line_number}: {exc}")
        if not isinstance(record, dict):
            continue
        timestamp = nonempty(record.get("timestamp"))
        record_type = record.get("type")
        payload = record.get("payload")
        if record_type == "response_item" and isinstance(payload, dict):
            payload_type = payload.get("type")
            if payload_type == "function_call":
                namespace = nonempty(payload.get("namespace"))
                name = nonempty(payload.get("name"))
                call_id = nonempty(payload.get("call_id"))
                if namespace != COLLAB_NAMESPACE or name not in COLLAB_TOOLS or call_id is None:
                    continue
                if call_filter is not None and call_id != call_filter:
                    continue
                if call_id in calls:
                    fail(f"duplicate collaboration function_call for call_id {call_id}")
                args = parse_arguments(payload.get("arguments"), call_id)
                calls[call_id] = {
                    "call_id": call_id,
                    "timestamp": timestamp,
                    "namespace": namespace,
                    "name": name,
                    "authorization": authorization_projection(name, args),
                    "message_present": "message" in args,
                    "message_nonempty": isinstance(args.get("message"), str)
                    and bool(args["message"].strip()),
                }
            elif payload_type == "function_call_output":
                call_id = nonempty(payload.get("call_id"))
                if call_id is None:
                    continue
                if call_filter is not None and call_id != call_filter:
                    continue
                outputs.setdefault(call_id, []).append((timestamp, payload.get("output")))
        elif record_type == "event_msg":
            activity = event_activity(payload)
            if activity is not None:
                call_id = activity.pop("call_id")
                if call_filter is None or call_id == call_filter:
                    activity["timestamp"] = timestamp
                    activities.setdefault(call_id, []).append(activity)

    if call_filter is not None and call_filter not in calls:
        fail("requested collaboration call_id was not found")
    result_calls: list[dict[str, Any]] = []
    for call_id, call in calls.items():
        matching_outputs = outputs.get(call_id, [])
        if len(matching_outputs) > 1:
            fail(f"multiple function_call_output records for call_id {call_id}")
        if matching_outputs:
            out_timestamp, output = matching_outputs[0]
            call["result"] = output_summary(output, call["name"])
            call["result"]["timestamp"] = out_timestamp
        else:
            call["result"] = {"observed": False, "recognized_success": False, "timestamp": None}
        call["activities"] = activities.get(call_id, [])
        result_calls.append(call)
    result_calls.sort(key=lambda item: ((item.get("timestamp") or ""), item["call_id"]))
    return {"thread_id": thread_id, "calls": result_calls}


def main() -> None:
    args = parse_args()
    thread_id = canonical_uuid(args.thread_id, "THREAD_ID")
    sessions_dir = resolve_sessions_dir(args)
    rollout = find_exact_rollout(sessions_dir, thread_id)
    result = inspect(rollout, thread_id=thread_id, call_filter=args.call_id)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
