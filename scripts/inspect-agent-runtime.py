#!/usr/bin/env python3
"""Extract allowlisted routing metadata from one exact Codex rollout.

This helper is for explicit runtime attestation only. It never scans transcript content
for task facts and never emits prompts, assistant output, tool payloads, reasoning, or
source contents. The returned object is suitable for the `local` observation layer of
`scripts/runtime-evidence.py`.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any, Iterator, NoReturn
from uuid import UUID


TARGET_LINE = re.compile(r'"type"\s*:\s*"(?:session_meta|turn_context)"')
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
        description="Extract allowlisted routing metadata from one exact Codex child rollout."
    )
    parser.add_argument("thread_id", help="Exact Codex child thread/session UUID.")
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--sessions-dir",
        type=Path,
        help="Explicit Codex sessions directory. Overrides CODEX_HOME discovery.",
    )
    source.add_argument(
        "--codex-home",
        type=Path,
        help="Codex home containing sessions/ (default: $CODEX_HOME or ~/.codex).",
    )
    parser.add_argument(
        "--expected-parent-thread-id",
        help="Optional exact parent/root thread UUID to bind the observation.",
    )
    parser.add_argument(
        "--expected-agent-role",
        help="Optional exact managed agent_type to bind the observation.",
    )
    return parser.parse_args()


def resolve_sessions_dir(args: argparse.Namespace) -> Path:
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
        dirnames[:] = [
            name for name in dirnames if not (current_path / name).is_symlink()
        ]
        for name in filenames:
            if not name.startswith("rollout-") or not name.endswith(suffix):
                continue
            candidate = current_path / name
            if candidate.is_symlink():
                fail("refusing symlinked rollout file")
            try:
                resolved = candidate.resolve(strict=True)
            except OSError as exc:
                fail(f"matched rollout is unavailable: {exc}")
            try:
                resolved.relative_to(sessions_dir)
            except ValueError:
                fail("matched rollout escapes the sessions directory")
            if not resolved.is_file():
                fail("matched rollout is not a regular file")
            matches.append(resolved)
    if not matches:
        fail("no rollout filename matched the requested thread id")
    if len(matches) != 1:
        fail("multiple rollout filenames matched the requested thread id")
    return matches[0]


def _decode_rollout_line(raw_line: bytes) -> str:
    try:
        return raw_line.decode("utf-8")
    except UnicodeDecodeError as exc:
        fail(f"could not decode matched rollout as UTF-8: {exc}")


def _drain_complete_lines(pending: bytearray, *, eof: bool) -> Iterator[str]:
    start = 0
    while True:
        match = NEWLINE_BOUNDARY.search(pending, start)
        if match is None:
            break
        if not eof and match.group() == b"\r" and match.end() == len(pending):
            break
        end = match.end()
        if end - start > MAX_ROLLOUT_LINE_BYTES:
            fail(
                "matched rollout line exceeds maximum rollout line size of "
                f"{MAX_ROLLOUT_LINE_BYTES} bytes"
            )
        yield _decode_rollout_line(bytes(pending[start:end]))
        start = end

    if start:
        del pending[:start]
    if len(pending) > MAX_ROLLOUT_LINE_BYTES:
        fail(
            "matched rollout line exceeds maximum rollout line size of "
            f"{MAX_ROLLOUT_LINE_BYTES} bytes"
        )


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
        fail(f"could not open matched rollout without following links: {exc}")

    try:
        opened = os.fstat(fd)
        if (
            not stat.S_ISREG(opened.st_mode)
            or (opened.st_dev, opened.st_ino) != (expected.st_dev, expected.st_ino)
        ):
            fail("matched rollout identity drifted while opening")
        if opened.st_size > MAX_ROLLOUT_BYTES:
            fail(
                f"matched rollout exceeds maximum rollout size of {MAX_ROLLOUT_BYTES} bytes"
            )

        total_bytes = 0
        pending = bytearray()
        read_size = max(
            1,
            min(
                READ_CHUNK_BYTES,
                MAX_ROLLOUT_BYTES + 1,
                MAX_ROLLOUT_LINE_BYTES + 1,
            ),
        )

        while True:
            chunk = os.read(fd, read_size)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > MAX_ROLLOUT_BYTES:
                fail(
                    f"matched rollout exceeds maximum rollout size of {MAX_ROLLOUT_BYTES} bytes"
                )
            pending.extend(chunk)
            yield from _drain_complete_lines(pending, eof=False)

        yield from _drain_complete_lines(pending, eof=True)
        if pending:
            yield _decode_rollout_line(bytes(pending))
            pending.clear()

        closed = os.fstat(fd)
        try:
            current = os.lstat(path)
        except OSError as exc:
            fail(f"matched rollout changed while being read: {exc}")
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


def payload_object(record: dict[str, Any], line_number: int) -> dict[str, Any]:
    payload = record.get("payload")
    if not isinstance(payload, dict):
        fail(f"target rollout record at line {line_number} has no object payload")
    return payload


def optional_text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def nested_type(value: Any) -> str | None:
    if isinstance(value, dict):
        return optional_text(value.get("type"))
    if isinstance(value, str):
        return optional_text(value)
    return None


def observe_stable_field(
    state: dict[str, tuple[str | None, bool, bool]],
    key: str,
    value: str | None,
) -> None:
    current, complete, conflict = state[key]
    if value is None:
        complete = False
    elif current is None:
        current = value
    elif current != value:
        conflict = True
    state[key] = (current, complete, conflict)


def resolved_stable_field(
    state: dict[str, tuple[str | None, bool, bool]],
    key: str,
    label: str,
) -> str | None:
    value, complete, conflict = state[key]
    if conflict:
        fail(f"conflicting {label} values across turn_context records")
    return value if complete else None


def inspect_rollout(
    path: Path,
    *,
    thread_id: str,
    expected_parent_thread_id: str | None,
    expected_agent_role: str | None,
) -> dict[str, str | None]:
    session_meta_count = 0
    session: dict[str, Any] | None = None
    turn_count = 0
    stable: dict[str, tuple[str | None, bool, bool]] = {
        "model": (None, True, False),
        "effort": (None, True, False),
        "cwd": (None, True, False),
        "sandbox": (None, True, False),
        "permission": (None, True, False),
    }

    for line_number, line in enumerate(iter_stable_rollout_lines(path), start=1):
        if not TARGET_LINE.search(line):
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            fail(f"invalid target rollout JSON at line {line_number}: {exc}")
        if not isinstance(record, dict):
            fail(f"target rollout record at line {line_number} is not an object")
        record_type = record.get("type")
        if record_type == "session_meta":
            payload = payload_object(record, line_number)
            session_meta_count += 1
            if session is None:
                session = payload
        elif record_type == "turn_context":
            payload = payload_object(record, line_number)
            turn_count += 1
            observe_stable_field(stable, "model", optional_text(payload.get("model")))
            observe_stable_field(stable, "effort", optional_text(payload.get("effort")))
            observe_stable_field(stable, "cwd", optional_text(payload.get("cwd")))
            observe_stable_field(stable, "sandbox", nested_type(payload.get("sandbox_policy")))
            observe_stable_field(
                stable,
                "permission",
                nested_type(payload.get("permission_profile")),
            )

    if session_meta_count != 1 or session is None:
        fail("rollout must contain exactly one session_meta record")
    if turn_count == 0:
        fail("rollout contains no turn_context records")

    observed_thread = optional_text(session.get("id"))
    if observed_thread is None:
        fail("session_meta does not expose thread id")
    try:
        observed_thread = canonical_uuid(observed_thread, "session_meta.id")
    except SystemExit:
        raise
    if observed_thread != thread_id:
        fail("session_meta does not identify the requested thread")

    session_id = optional_text(session.get("session_id"))
    if session_id is not None:
        canonical_uuid(session_id, "session_meta.session_id")

    parent = optional_text(session.get("parent_thread_id"))
    if parent is not None:
        parent = canonical_uuid(parent, "session_meta.parent_thread_id")
    if expected_parent_thread_id is not None and parent != expected_parent_thread_id:
        fail("session_meta parent_thread_id does not match the expected parent")

    agent_role = optional_text(session.get("agent_role"))
    if expected_agent_role is not None and agent_role != expected_agent_role:
        fail("session_meta agent_role does not match the expected managed role")

    result: dict[str, str | None] = {
        "thread_id": thread_id,
        "parent_thread_id": parent,
        "agent_role": agent_role,
        "agent_path": optional_text(session.get("agent_path")),
        "model_provider": optional_text(session.get("model_provider")),
        "model": resolved_stable_field(stable, "model", "model"),
        "effort": resolved_stable_field(stable, "effort", "effort"),
        "sandbox_policy_type": resolved_stable_field(stable, "sandbox", "sandbox policy"),
        "permission_profile_type": resolved_stable_field(
            stable, "permission", "permission profile"
        ),
        "cwd": resolved_stable_field(stable, "cwd", "cwd"),
        "runtime_version": optional_text(session.get("cli_version")),
    }
    return result


def main() -> None:
    args = parse_args()
    thread_id = canonical_uuid(args.thread_id, "thread_id")
    expected_parent = (
        canonical_uuid(args.expected_parent_thread_id, "expected parent thread id")
        if args.expected_parent_thread_id
        else None
    )
    expected_role = optional_text(args.expected_agent_role)
    if args.expected_agent_role is not None and expected_role is None:
        fail("expected agent role must be a non-empty string")

    sessions_dir = resolve_sessions_dir(args)
    rollout = find_exact_rollout(sessions_dir, thread_id)
    result = inspect_rollout(
        rollout,
        thread_id=thread_id,
        expected_parent_thread_id=expected_parent,
        expected_agent_role=expected_role,
    )
    json.dump(result, sys.stdout, sort_keys=True, separators=(",", ":"))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
