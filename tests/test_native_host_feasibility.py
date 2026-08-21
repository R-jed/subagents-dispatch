from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tomllib


ROOT = Path(__file__).resolve().parents[1]
INSPECTOR = ROOT / "scripts" / "inspect-collaboration-runtime.py"
THREAD = "11111111-1111-7111-8111-111111111111"
CHILD = "22222222-2222-7222-8222-222222222222"
PROFILES = {
    "subagents-dispatch-reader.toml": ("gpt-5.6-luna", "max", "read-only"),
    "subagents-dispatch-worker.toml": ("gpt-5.6-luna", "max", None),
    "subagents-dispatch-investigator.toml": ("gpt-5.6-terra", "xhigh", "read-only"),
    "subagents-dispatch-solver.toml": ("gpt-5.6-sol", "high", None),
    "subagents-dispatch-advisor.toml": ("gpt-5.6-sol", "high", "read-only"),
}


def test_all_managed_profiles_disable_child_multi_agent_without_route_drift():
    for filename, (model, effort, sandbox) in PROFILES.items():
        payload = tomllib.loads((ROOT / "agent-profiles" / filename).read_text(encoding="utf-8"))
        assert payload["model"] == model
        assert payload["model_reasoning_effort"] == effort
        assert payload.get("sandbox_mode") == sandbox
        assert payload["agents"]["enabled"] is False
        assert payload["features"]["multi_agent_v2"] is False
        assert "create further subagents" in payload["developer_instructions"]


def write_rollout(sessions: Path, records: list[dict], *, relative: str = "2026/08/20") -> Path:
    folder = sessions / relative
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"rollout-2026-08-20T23-00-00-{THREAD}.jsonl"
    path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")
    return path


def base_records() -> list[dict]:
    return [
        {
            "timestamp": "2026-08-20T14:00:00Z",
            "type": "session_meta",
            "payload": {"id": THREAD, "cwd": "/SECRET/project"},
        },
        {
            "timestamp": "2026-08-20T14:00:01Z",
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "namespace": "collaboration",
                "name": "spawn_agent",
                "arguments": json.dumps(
                    {
                        "task_name": "sd-u1-a1",
                        "message": "SECRET ASSIGNMENT BODY",
                        "agent_type": "subagents_dispatch_reader",
                        "fork_turns": "none",
                    }
                ),
                "call_id": "call_spawn",
            },
        },
        {
            "timestamp": "2026-08-20T14:00:02Z",
            "type": "event_msg",
            "payload": {
                "type": "sub_agent_activity",
                "event_id": "call_spawn",
                "occurred_at_ms": 1_777_777_777_777,
                "kind": "started",
                "agent_thread_id": CHILD,
                "agent_path": "/root/sd-u1-a1",
            },
        },
        {
            "timestamp": "2026-08-20T14:00:03Z",
            "type": "response_item",
            "payload": {
                "type": "function_call_output",
                "call_id": "call_spawn",
                "output": json.dumps(
                    {"task_name": "/root/sd-u1-a1", "nickname": "SECRET NICKNAME"}
                ),
            },
        },
        {
            "timestamp": "2026-08-20T14:00:04Z",
            "type": "response_item",
            "payload": {"type": "reasoning", "summary": "SECRET REASONING"},
        },
    ]


def run_inspector(sessions: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(INSPECTOR), THREAD, "--sessions-dir", str(sessions), *extra],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_collaboration_inspector_binds_call_result_and_activity_without_message_leak(tmp_path: Path):
    sessions = tmp_path / "sessions"
    write_rollout(sessions, base_records())

    result = run_inspector(sessions, "--call-id", "call_spawn")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {
        "thread_id": THREAD,
        "calls": [
            {
                "call_id": "call_spawn",
                "timestamp": "2026-08-20T14:00:01Z",
                "namespace": "collaboration",
                "name": "spawn_agent",
                "authorization": {
                    "task_name": "sd-u1-a1",
                    "agent_type": "subagents_dispatch_reader",
                    "fork_turns": "none",
                },
                "message_present": True,
                "message_nonempty": True,
                "result": {
                    "observed": True,
                    "recognized_success": True,
                    "task_name": "/root/sd-u1-a1",
                    "timestamp": "2026-08-20T14:00:03Z",
                },
                "activities": [
                    {
                        "kind": "started",
                        "agent_thread_id": CHILD,
                        "agent_path": "/root/sd-u1-a1",
                        "timestamp": "2026-08-20T14:00:02Z",
                    }
                ],
            }
        ],
    }
    assert "SECRET" not in result.stdout
    assert "message" not in result.stdout.lower() or '"message_present"' in result.stdout
    assert "reasoning" not in result.stdout.lower()
    assert "nickname" not in result.stdout.lower()


def test_collaboration_inspector_rejects_conflicting_activity_ids(tmp_path: Path):
    sessions = tmp_path / "sessions"
    records = base_records()
    records[2]["payload"]["id"] = "call_other"
    write_rollout(sessions, records)

    result = run_inspector(sessions)

    assert result.returncode != 0
    assert "sub-agent activity id/event_id conflict" in result.stderr


def test_collaboration_inspector_does_not_relabel_unknown_output_as_success(tmp_path: Path):
    sessions = tmp_path / "sessions"
    records = base_records()
    records[3]["payload"]["output"] = "capacity limit reached: SECRET DETAIL"
    write_rollout(sessions, records)

    result = run_inspector(sessions, "--call-id", "call_spawn")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    summary = payload["calls"][0]["result"]
    assert summary["observed"] is True
    assert summary["recognized_success"] is False
    assert "SECRET" not in result.stdout
    assert "capacity limit" not in result.stdout


def test_collaboration_inspector_rejects_duplicate_call_id(tmp_path: Path):
    sessions = tmp_path / "sessions"
    records = base_records()
    records.insert(2, dict(records[1]))
    write_rollout(sessions, records)

    result = run_inspector(sessions)

    assert result.returncode != 0
    assert "duplicate collaboration function_call" in result.stderr


def test_collaboration_inspector_rejects_multiple_exact_rollouts(tmp_path: Path):
    sessions = tmp_path / "sessions"
    write_rollout(sessions, base_records(), relative="2026/08/20")
    write_rollout(sessions, base_records(), relative="2026/08/21")

    result = run_inspector(sessions)

    assert result.returncode != 0
    assert "multiple rollout filenames matched" in result.stderr
