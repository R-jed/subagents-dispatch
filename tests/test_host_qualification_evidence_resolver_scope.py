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
ROLE = "subagents_dispatch_reader"
TASK_PATH = "/root/sd_canary_a1"


def write_rollout(sessions: Path, thread_id: str, records: list[str], day: str) -> None:
    folder = sessions / day
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"rollout-2026-08-26T00-00-00-{thread_id}.jsonl"
    path.write_text("\n".join(records) + "\n", encoding="utf-8")


def test_task_address_resolver_ignores_malformed_non_session_payload_in_unrelated_rollout(
    tmp_path: Path,
):
    sessions = tmp_path / "sessions"
    unrelated_session = {
        "timestamp": "2026-08-25T23:00:00Z",
        "type": "session_meta",
        "payload": {
            "id": OTHER_THREAD,
            "parent_thread_id": ROOT_THREAD,
            "agent_role": ROLE,
            "agent_path": "/root/other",
        },
    }
    write_rollout(
        sessions,
        OTHER_THREAD,
        [json.dumps(unrelated_session), '{"type":"response_item"'],
        "2026/08/25",
    )

    matching_session = {
        "timestamp": "2026-08-26T00:01:00Z",
        "type": "session_meta",
        "payload": {
            "id": CHILD_THREAD,
            "parent_thread_id": ROOT_THREAD,
            "agent_role": ROLE,
            "agent_path": TASK_PATH,
            "cli_version": "0.149.0-alpha.4.3",
        },
    }
    write_rollout(sessions, CHILD_THREAD, [json.dumps(matching_session)], "2026/08/26")

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


import pytest


@pytest.mark.parametrize(
    "task_path",
    ["/root/BadName", "/root/bad-name", "/root/bad.name", "/root/root", "/root/parent/child"],
)
def test_task_address_resolver_rejects_noncanonical_or_nonleaf_managed_path(
    tmp_path: Path, task_path: str
):
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    result = subprocess.run(
        [sys.executable, str(EVIDENCE), "--sessions-dir", str(sessions),
         "resolve-child", "--agent-path", task_path,
         "--since", "2026-08-26T00:00:00Z"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    assert result.returncode != 0
    assert "canonical /root/<task>" in result.stderr
