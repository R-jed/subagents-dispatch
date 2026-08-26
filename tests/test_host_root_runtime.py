from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
ROOT_INSPECTOR = ROOT / "scripts" / "inspect-host-root-runtime.py"
COLLAB_INSPECTOR = ROOT / "scripts" / "inspect-collaboration-runtime.py"
PACKAGE_MANIFEST = ROOT / ".codex-plugin" / "package-integrity.json"
THREAD = "11111111-1111-7111-8111-111111111111"
SESSION = "22222222-2222-7222-8222-222222222222"
CHILD = "33333333-3333-7333-8333-333333333333"
CALL_ID = "call_host_runtime_binding"
TASK_ADDRESS = "/root/sd_h4_n2_reader_a1"


def write_root_rollout(sessions: Path, *, parent: str | None = None, session_id: str | None = SESSION) -> Path:
    folder = sessions / "2026" / "08" / "26"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"rollout-2026-08-26T03-00-00-{THREAD}.jsonl"
    records = [
        {
            "timestamp": "2026-08-26T03:00:00Z",
            "type": "session_meta",
            "payload": {
                "id": THREAD,
                "session_id": session_id,
                "parent_thread_id": parent,
                "cli_version": "0.149.0-alpha.4.3",
                "cwd": "/repo",
                "model_provider": "openai",
            },
        },
        {
            "timestamp": "2026-08-26T03:00:01Z",
            "type": "turn_context",
            "payload": {
                "model": "gpt-5.6-luna",
                "effort": "max",
                "cwd": "/repo",
                "multi_agent_version": "v1",
                "sandbox_policy": {"type": "workspace-write", "private": "SECRET"},
                "permission_profile": {"type": "default", "private": "SECRET"},
            },
        },
        {
            "timestamp": "2026-08-26T03:00:02Z",
            "type": "response_item",
            "payload": {"type": "reasoning", "summary": "SECRET REASONING"},
        },
        {
            "timestamp": "2026-08-26T03:00:03Z",
            "type": "turn_context",
            "payload": {
                "model": "gpt-5.6-sol",
                "effort": "high",
                "model_provider": "openai",
                "cwd": "/repo",
                "multi_agent_version": "v2",
                "sandbox_policy": {"type": "danger-full-access"},
                "permission_profile": {"type": "disabled"},
                "developer_instructions": "SECRET INSTRUCTIONS",
            },
        },
    ]
    path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")
    return path


def run_root_inspector(sessions: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT_INSPECTOR), THREAD, "--sessions-dir", str(sessions)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_root_inspector_binds_session_and_uses_latest_turn_only(tmp_path: Path):
    sessions = tmp_path / "sessions"
    write_root_rollout(sessions)

    result = run_root_inspector(sessions)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {
        "cwd": "/repo",
        "effort": "high",
        "latest_turn_at": "2026-08-26T03:00:03Z",
        "model": "gpt-5.6-sol",
        "model_provider": "openai",
        "multi_agent_version": "v2",
        "parent_thread_id": None,
        "permission_profile_type": "disabled",
        "runtime_version": "0.149.0-alpha.4.3",
        "sandbox_policy_type": "danger-full-access",
        "session_id": SESSION,
        "thread_id": THREAD,
    }
    assert "SECRET" not in result.stdout
    assert "developer_instructions" not in result.stdout
    assert "reasoning" not in result.stdout.lower()


def test_root_inspector_does_not_infer_missing_latest_turn_fields(tmp_path: Path):
    sessions = tmp_path / "sessions"
    path = write_root_rollout(sessions)
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    latest = records[-1]["payload"]
    del latest["model"]
    del latest["effort"]
    del latest["multi_agent_version"]
    path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")

    result = run_root_inspector(sessions)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["model"] is None
    assert payload["effort"] is None
    assert payload["multi_agent_version"] is None


def test_root_inspector_rejects_child_thread(tmp_path: Path):
    sessions = tmp_path / "sessions"
    write_root_rollout(sessions, parent="00000000-0000-7000-8000-000000000000")

    result = run_root_inspector(sessions)

    assert result.returncode != 0
    assert "child thread" in result.stderr


def test_root_inspector_requires_authoritative_session_id(tmp_path: Path):
    sessions = tmp_path / "sessions"
    write_root_rollout(sessions, session_id=None)

    result = run_root_inspector(sessions)

    assert result.returncode != 0
    assert "session_id" in result.stderr


def test_root_inspector_is_maintainer_only_and_not_shipped():
    manifest_text = PACKAGE_MANIFEST.read_text(encoding="utf-8")
    assert "scripts/inspect-host-root-runtime.py" not in manifest_text


def test_existing_collaboration_inspector_binds_spawn_result_to_host_child_activity(tmp_path: Path):
    sessions = tmp_path / "sessions"
    folder = sessions / "2026" / "08" / "26"
    folder.mkdir(parents=True)
    path = folder / f"rollout-2026-08-26T03-10-00-{THREAD}.jsonl"
    records = [
        {
            "timestamp": "2026-08-26T03:10:01Z",
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "namespace": "collaboration",
                "name": "spawn_agent",
                "call_id": CALL_ID,
                "arguments": json.dumps(
                    {
                        "task_name": "sd_h4_n2_reader_a1",
                        "message": "SECRET ASSIGNMENT",
                        "agent_type": "subagents_dispatch_reader",
                        "fork_turns": "none",
                    }
                ),
            },
        },
        {
            "timestamp": "2026-08-26T03:10:02Z",
            "type": "response_item",
            "payload": {
                "type": "function_call_output",
                "call_id": CALL_ID,
                "output": json.dumps({"task_name": TASK_ADDRESS}),
            },
        },
        {
            "timestamp": "2026-08-26T03:10:03Z",
            "type": "event_msg",
            "payload": {
                "type": "sub_agent_activity",
                "event_id": CALL_ID,
                "agent_thread_id": CHILD,
                "agent_path": TASK_ADDRESS,
                "kind": "Started",
            },
        },
    ]
    path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(COLLAB_INSPECTOR),
            THREAD,
            "--sessions-dir",
            str(sessions),
            "--call-id",
            CALL_ID,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["thread_id"] == THREAD
    assert len(payload["calls"]) == 1
    call = payload["calls"][0]
    assert call["result"]["recognized_success"] is True
    assert call["result"]["task_name"] == TASK_ADDRESS
    assert call["activities"] == [
        {
            "agent_path": TASK_ADDRESS,
            "agent_thread_id": CHILD,
            "kind": "Started",
            "timestamp": "2026-08-26T03:10:03Z",
        }
    ]
    assert "SECRET ASSIGNMENT" not in result.stdout
