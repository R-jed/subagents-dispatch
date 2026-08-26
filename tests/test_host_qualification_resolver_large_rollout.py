from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "scripts" / "host_qualification_evidence.py"
ROOT_THREAD = "11111111-1111-7111-8111-111111111111"
CHILD_THREAD = "22222222-2222-7222-8222-222222222222"
OTHER_THREAD = "33333333-3333-7333-8333-333333333333"
SESSION_ID = "aaaaaaaa-aaaa-7aaa-8aaa-aaaaaaaaaaaa"
ROLE = "subagents_dispatch_reader"
TASK_PATH = "/root/sd_host_canary_a1"
MAX_ROLLOUT_BYTES = 64 * 1024 * 1024


def write_rollout(
    sessions: Path,
    *,
    thread_id: str,
    timestamp: str,
    agent_path: str,
    day: str,
) -> Path:
    folder = sessions / day
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"rollout-2026-08-26T00-00-00-{thread_id}.jsonl"
    records = [
        {
            "timestamp": timestamp,
            "type": "session_meta",
            "payload": {
                "session_id": SESSION_ID,
                "id": thread_id,
                "parent_thread_id": ROOT_THREAD,
                "agent_role": ROLE,
                "agent_path": agent_path,
                "cli_version": "0.150.0-alpha.8",
            },
        },
        {
            "timestamp": "2026-08-26T00:01:01Z",
            "type": "turn_context",
            "payload": {"model": "gpt-5.6-luna", "effort": "max"},
        },
    ]
    path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )
    return path


def test_resolver_ignores_unrelated_rollout_over_exact_inspector_limit(tmp_path: Path):
    sessions = tmp_path / "sessions"
    unrelated = write_rollout(
        sessions,
        thread_id=OTHER_THREAD,
        timestamp="2026-08-26T00:00:30Z",
        agent_path="/root/unrelated",
        day="2026/08/26",
    )
    with unrelated.open("r+b") as handle:
        handle.seek(MAX_ROLLOUT_BYTES + 1)
        handle.write(b"\n")

    write_rollout(
        sessions,
        thread_id=CHILD_THREAD,
        timestamp="2026-08-26T00:01:00Z",
        agent_path=TASK_PATH,
        day="2026/08/27",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(EVIDENCE),
            "--sessions-dir",
            str(sessions),
            "resolve-child",
            "--agent-path",
            TASK_PATH,
            "--since",
            "2026-08-26T00:00:00Z",
            "--expected-parent-thread-id",
            ROOT_THREAD,
            "--expected-agent-role",
            ROLE,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["thread_id"] == CHILD_THREAD
