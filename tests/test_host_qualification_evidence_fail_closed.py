from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "scripts" / "host_qualification_evidence.py"
ROOT_THREAD = "11111111-1111-7111-8111-111111111111"
CHILD_THREAD = "22222222-2222-7222-8222-222222222222"
ROLE = "subagents_dispatch_reader"


def run_tool(sessions: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(EVIDENCE), "--sessions-dir", str(sessions), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def write_lines(sessions: Path, thread_id: str, lines: list[str]) -> Path:
    folder = sessions / "2026/08/26"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"rollout-2026-08-26T00-00-00-{thread_id}.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_aggregate_rejects_malformed_rollout_record_instead_of_undercounting(tmp_path: Path):
    sessions = tmp_path / "sessions"
    session = {
        "timestamp": "2026-08-26T00:00:00Z",
        "type": "session_meta",
        "payload": {
            "id": CHILD_THREAD,
            "session_id": "session-tree-opaque",
            "parent_thread_id": ROOT_THREAD,
            "agent_role": ROLE,
            "agent_path": "/root/sd_canary_a1",
            "cli_version": "0.149.0-alpha.4.3",
            "cwd": "/repo",
        },
    }
    turn = {
        "timestamp": "2026-08-26T00:00:01Z",
        "type": "turn_context",
        "payload": {
            "model": "gpt-5.6-luna",
            "effort": "max",
            "sandbox_policy": {"type": "read-only"},
            "permission_profile": {"type": "disabled"},
            "cwd": "/repo",
        },
    }
    write_lines(
        sessions,
        CHILD_THREAD,
        [json.dumps(session), json.dumps(turn), '{"type":"response_item"'],
    )

    result = run_tool(sessions, "aggregate", CHILD_THREAD)

    assert result.returncode != 0
    assert "invalid rollout JSON" in result.stderr


def test_primary_accepts_opaque_host_session_identity(tmp_path: Path):
    sessions = tmp_path / "sessions"
    session = {
        "timestamp": "2026-08-26T00:00:00Z",
        "type": "session_meta",
        "payload": {
            "id": ROOT_THREAD,
            "session_id": "host-session-tree-opaque-7119",
            "parent_thread_id": None,
            "agent_role": None,
            "cli_version": "0.149.0-alpha.4.3",
            "cwd": "/repo",
            "model_provider": "openai",
        },
    }
    turn = {
        "timestamp": "2026-08-26T00:00:01Z",
        "type": "turn_context",
        "payload": {
            "model": "gpt-5.6-sol",
            "effort": "high",
            "cwd": "/repo",
            "multi_agent_version": "v2",
        },
    }
    write_lines(sessions, ROOT_THREAD, [json.dumps(session), json.dumps(turn)])

    result = run_tool(sessions, "primary", ROOT_THREAD)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["session_id"] == "host-session-tree-opaque-7119"
    assert payload["thread_id"] == ROOT_THREAD


def test_resolve_child_rejects_noncanonical_host_task_address(tmp_path: Path):
    sessions = tmp_path / "sessions"
    sessions.mkdir()

    result = run_tool(
        sessions,
        "resolve-child",
        "--agent-path",
        "/root/a/b",
        "--since",
        "2026-08-26T00:00:00Z",
    )

    assert result.returncode != 0
    assert "canonical /root/<task>" in result.stderr


def test_primary_rejects_missing_turn_timestamp_instead_of_guessing_latest(tmp_path: Path):
    sessions = tmp_path / "sessions"
    session = {
        "timestamp": "2026-08-26T00:00:00Z",
        "type": "session_meta",
        "payload": {
            "id": ROOT_THREAD,
            "session_id": "host-session-tree-opaque-7119",
            "parent_thread_id": None,
            "agent_role": None,
            "cwd": "/repo",
        },
    }
    turn = {
        "type": "turn_context",
        "payload": {"model": "gpt-5.6-sol", "effort": "high", "cwd": "/repo"},
    }
    write_lines(sessions, ROOT_THREAD, [json.dumps(session), json.dumps(turn)])

    result = run_tool(sessions, "primary", ROOT_THREAD)

    assert result.returncode != 0
    assert "turn_context[1] timestamp" in result.stderr
