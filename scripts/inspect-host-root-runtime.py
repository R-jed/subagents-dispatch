#!/usr/bin/env python3
"""Emit allowlisted runtime identity for one exact Codex root rollout.

This maintainer-only helper is for real-Host qualification. It reads the exact root
rollout identified by thread UUID, requires authoritative root/session identity, and
uses only the latest turn_context for turn-scoped runtime fields. It never emits
prompts, messages, reasoning, tool payloads, environment values, or source contents.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, NoReturn


HERE = Path(__file__).resolve().parent
AGENT_INSPECTOR = HERE / "inspect-agent-runtime.py"


def fail(message: str) -> NoReturn:
    raise SystemExit(f"ERROR: {message}")


def load_agent_inspector():
    spec = importlib.util.spec_from_file_location("subagents_dispatch_agent_runtime", AGENT_INSPECTOR)
    if spec is None or spec.loader is None:
        fail("could not load the exact rollout reader")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect one exact Codex root rollout using latest-turn runtime evidence."
    )
    parser.add_argument("thread_id", help="Exact current root thread UUID.")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--sessions-dir", type=Path)
    source.add_argument("--codex-home", type=Path)
    return parser.parse_args()


def nonempty(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def nested_type(value: Any) -> str | None:
    if isinstance(value, dict):
        return nonempty(value.get("type"))
    if isinstance(value, str):
        return nonempty(value)
    return None


def resolve_sessions_dir(runtime, args: argparse.Namespace) -> Path:
    runtime_args = argparse.Namespace(
        sessions_dir=args.sessions_dir,
        codex_home=args.codex_home,
    )
    return runtime.resolve_sessions_dir(runtime_args)


def inspect_root(runtime, path: Path, *, thread_id: str) -> dict[str, str | None]:
    session_count = 0
    session: dict[str, Any] | None = None
    latest_turn: dict[str, Any] | None = None
    latest_turn_at: str | None = None

    for line_number, line in enumerate(runtime.iter_stable_rollout_lines(path), start=1):
        if not runtime.TARGET_LINE.search(line):
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            fail(f"invalid target rollout JSON at line {line_number}: {exc}")
        if not isinstance(record, dict):
            fail(f"target rollout record at line {line_number} is not an object")
        record_type = record.get("type")
        if record_type == "session_meta":
            payload = runtime.payload_object(record, line_number)
            session_count += 1
            if session is None:
                session = payload
        elif record_type == "turn_context":
            latest_turn = runtime.payload_object(record, line_number)
            latest_turn_at = nonempty(record.get("timestamp"))

    if session_count != 1 or session is None:
        fail("root rollout must contain exactly one session_meta record")
    if latest_turn is None:
        fail("root rollout contains no turn_context records")

    observed_thread = nonempty(session.get("id"))
    if observed_thread is None:
        fail("session_meta does not expose root thread id")
    observed_thread = runtime.canonical_uuid(observed_thread, "session_meta.id")
    if observed_thread != thread_id:
        fail("session_meta does not identify the requested root thread")

    parent = nonempty(session.get("parent_thread_id"))
    if parent is not None:
        fail("requested rollout is a child thread, not a root thread")

    session_id = nonempty(session.get("session_id"))
    if session_id is None:
        fail("session_meta does not expose required root session_id")
    session_id = runtime.canonical_uuid(session_id, "session_meta.session_id")

    return {
        "thread_id": thread_id,
        "session_id": session_id,
        "parent_thread_id": None,
        "model": nonempty(latest_turn.get("model")),
        "effort": nonempty(latest_turn.get("effort")),
        "model_provider": nonempty(latest_turn.get("model_provider"))
        or nonempty(session.get("model_provider")),
        "cwd": nonempty(latest_turn.get("cwd")) or nonempty(session.get("cwd")),
        "sandbox_policy_type": nested_type(latest_turn.get("sandbox_policy")),
        "permission_profile_type": nested_type(latest_turn.get("permission_profile")),
        "multi_agent_version": nonempty(latest_turn.get("multi_agent_version")),
        "runtime_version": nonempty(session.get("cli_version")),
        "latest_turn_at": latest_turn_at,
    }


def main() -> None:
    args = parse_args()
    runtime = load_agent_inspector()
    thread_id = runtime.canonical_uuid(args.thread_id, "thread_id")
    sessions_dir = resolve_sessions_dir(runtime, args)
    rollout = runtime.find_exact_rollout(sessions_dir, thread_id)
    result = inspect_root(runtime, rollout, thread_id=thread_id)
    json.dump(result, sys.stdout, sort_keys=True, separators=(",", ":"))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
