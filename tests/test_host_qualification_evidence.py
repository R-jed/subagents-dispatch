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


def write_rollout(
    sessions: Path,
    *,
    thread_id: str,
    timestamp: str,
    parent_thread_id: str | None,
    agent_role: str | None,
    agent_path: str | None,
    session_id: str = SESSION_ID,
    turns: list[dict] | None = None,
    extra_records: list[dict] | None = None,
    day: str = "2026/08/26",
) -> Path:
    folder = sessions / day
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"rollout-2026-08-26T00-00-00-{thread_id}.jsonl"
    session = {
        "timestamp": timestamp,
        "type": "session_meta",
        "payload": {
            "session_id": session_id,
            "id": thread_id,
            "parent_thread_id": parent_thread_id,
            "agent_role": agent_role,
            "agent_path": agent_path,
            "cli_version": "0.149.0-alpha.4.3",
            "cwd": "/repo",
            "model_provider": "openai",
        },
    }
    default_turn = {
        "timestamp": "2026-08-26T00:00:01Z",
        "type": "turn_context",
        "payload": {
            "model": "gpt-5.6-luna",
            "effort": "max",
            "model_provider": "openai",
            "sandbox_policy": {"type": "read-only", "secret": "DO_NOT_LEAK"},
            "permission_profile": {"type": "disabled", "secret": "DO_NOT_LEAK"},
            "cwd": "/repo",
            "multi_agent_version": "v2",
            "developer_instructions": "DO_NOT_LEAK",
        },
    }
    records = [
        session,
        *(extra_records or []),
        *(turns if turns is not None else [default_turn]),
    ]
    path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )
    return path


def run_tool(sessions: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(EVIDENCE), "--sessions-dir", str(sessions), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_resolve_child_binds_task_address_to_unique_post_cutoff_thread(tmp_path: Path):
    sessions = tmp_path / "sessions"
    write_rollout(
        sessions,
        thread_id=OTHER_THREAD,
        timestamp="2026-08-25T23:59:00Z",
        parent_thread_id=ROOT_THREAD,
        agent_role=ROLE,
        agent_path=TASK_PATH,
        day="2026/08/25",
    )
    write_rollout(
        sessions,
        thread_id=CHILD_THREAD,
        timestamp="2026-08-26T00:01:00Z",
        parent_thread_id=ROOT_THREAD,
        agent_role=ROLE,
        agent_path=TASK_PATH,
    )

    result = run_tool(
        sessions,
        "resolve-child",
        "--agent-path",
        TASK_PATH,
        "--since",
        "2026-08-26T00:00:00Z",
        "--expected-parent-thread-id",
        ROOT_THREAD,
        "--expected-agent-role",
        ROLE,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "agent_path": TASK_PATH,
        "agent_role": ROLE,
        "parent_thread_id": ROOT_THREAD,
        "runtime_version": "0.149.0-alpha.4.3",
        "session_observed_at": "2026-08-26T00:01:00Z",
        "thread_id": CHILD_THREAD,
    }


def test_resolve_child_fails_closed_on_two_post_cutoff_matches(tmp_path: Path):
    sessions = tmp_path / "sessions"
    for thread_id, day, timestamp in (
        (CHILD_THREAD, "2026/08/26", "2026-08-26T00:01:00Z"),
        (OTHER_THREAD, "2026/08/27", "2026-08-26T00:02:00Z"),
    ):
        write_rollout(
            sessions,
            thread_id=thread_id,
            timestamp=timestamp,
            parent_thread_id=ROOT_THREAD,
            agent_role=ROLE,
            agent_path=TASK_PATH,
            day=day,
        )

    result = run_tool(
        sessions,
        "resolve-child",
        "--agent-path",
        TASK_PATH,
        "--since",
        "2026-08-26T00:00:00Z",
    )

    assert result.returncode != 0
    assert "multiple rollouts matched" in result.stderr


def test_resolve_child_ignores_task_path_text_outside_session_meta(tmp_path: Path):
    sessions = tmp_path / "sessions"
    write_rollout(
        sessions,
        thread_id=OTHER_THREAD,
        timestamp="2026-08-26T00:01:00Z",
        parent_thread_id=ROOT_THREAD,
        agent_role=ROLE,
        agent_path="/root/other",
        extra_records=[
            {
                "timestamp": "2026-08-26T00:01:01Z",
                "type": "response_item",
                "payload": {"type": "reasoning", "summary": TASK_PATH},
            }
        ],
    )

    result = run_tool(
        sessions,
        "resolve-child",
        "--agent-path",
        TASK_PATH,
        "--since",
        "2026-08-26T00:00:00Z",
    )

    assert result.returncode != 0
    assert "no rollout matched" in result.stderr


def test_primary_uses_latest_turn_and_binds_root_session_identity(tmp_path: Path):
    sessions = tmp_path / "sessions"
    turns = [
        {
            "timestamp": "2026-08-26T00:00:01Z",
            "type": "turn_context",
            "payload": {
                "model": "gpt-5.6-luna",
                "effort": "max",
                "cwd": "/repo",
                "model_provider": "openai",
                "multi_agent_version": "v1",
            },
        },
        {
            "timestamp": "2026-08-26T00:00:03Z",
            "type": "turn_context",
            "payload": {
                "model": "gpt-5.6-sol",
                "effort": "high",
                "cwd": "/repo",
                "model_provider": "openai",
                "multi_agent_version": "v2",
                "developer_instructions": "DO_NOT_LEAK",
            },
        },
    ]
    write_rollout(
        sessions,
        thread_id=ROOT_THREAD,
        timestamp="2026-08-26T00:00:00Z",
        parent_thread_id=None,
        agent_role=None,
        agent_path=None,
        turns=turns,
    )

    result = run_tool(sessions, "primary", ROOT_THREAD)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {
        "cwd": "/repo",
        "effort": "high",
        "latest_turn_at": "2026-08-26T00:00:03Z",
        "model": "gpt-5.6-sol",
        "model_provider": "openai",
        "multi_agent_version": "v2",
        "parent_thread_id": None,
        "runtime_version": "0.149.0-alpha.4.3",
        "session_id": SESSION_ID,
        "thread_id": ROOT_THREAD,
    }
    assert "DO_NOT_LEAK" not in result.stdout


def test_primary_rejects_child_thread(tmp_path: Path):
    sessions = tmp_path / "sessions"
    write_rollout(
        sessions,
        thread_id=CHILD_THREAD,
        timestamp="2026-08-26T00:00:00Z",
        parent_thread_id=ROOT_THREAD,
        agent_role=ROLE,
        agent_path=TASK_PATH,
    )

    result = run_tool(sessions, "primary", CHILD_THREAD)

    assert result.returncode != 0
    assert "requires a root thread" in result.stderr


def test_aggregate_reports_privacy_safe_counts(tmp_path: Path):
    sessions = tmp_path / "sessions"
    extra = [
        {
            "timestamp": "2026-08-26T00:00:02Z",
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "name": "collaboration.spawn_agent",
                "arguments": "DO_NOT_LEAK",
            },
        },
        {
            "timestamp": "2026-08-26T00:00:03Z",
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "name": "shell.exec",
                "arguments": "DO_NOT_LEAK",
            },
        },
        {
            "timestamp": "2026-08-26T00:00:04Z",
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {"total_token_usage": {"total_tokens": 1234}},
            },
        },
        {
            "timestamp": "2026-08-26T00:00:05Z",
            "type": "event_msg",
            "payload": {"type": "context_compacted", "secret": "DO_NOT_LEAK"},
        },
    ]
    write_rollout(
        sessions,
        thread_id=CHILD_THREAD,
        timestamp="2026-08-26T00:00:00Z",
        parent_thread_id=ROOT_THREAD,
        agent_role=ROLE,
        agent_path=TASK_PATH,
        extra_records=extra,
    )

    result = run_tool(
        sessions,
        "aggregate",
        CHILD_THREAD,
        "--expected-parent-thread-id",
        ROOT_THREAD,
        "--expected-agent-role",
        ROLE,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["tool_call_count"] == 2
    assert payload["agent_control_call_count"] == 1
    assert payload["agent_control_tools_seen"] == ["spawn_agent"]
    assert payload["compaction_count"] == 1
    assert payload["raw_tokens"] == 1234
    assert payload["latest_event_at"] == "2026-08-26T00:00:05Z"
    assert payload["timestamp_observation_complete"] is True
    assert payload["tool_name_observation_complete"] is True
    assert payload["token_usage_observation_complete"] is True
    assert "DO_NOT_LEAK" not in result.stdout



def test_aggregate_distinguishes_control_from_full_v2_agent_layer(tmp_path: Path):
    sessions = tmp_path / "sessions"
    names = [
        "spawn_agent",
        "send_message",
        "followup_task",
        "wait_agent",
        "interrupt_agent",
        "list_agents",
    ]
    extra = [
        {
            "timestamp": f"2026-08-26T00:00:{index + 2:02d}Z",
            "type": "response_item",
            "payload": {"type": "function_call", "name": name, "arguments": "DO_NOT_LEAK"},
        }
        for index, name in enumerate(names)
    ]
    write_rollout(
        sessions,
        thread_id=CHILD_THREAD,
        timestamp="2026-08-26T00:00:00Z",
        parent_thread_id=ROOT_THREAD,
        agent_role=ROLE,
        agent_path=TASK_PATH,
        extra_records=extra,
    )

    result = run_tool(sessions, "aggregate", CHILD_THREAD)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["agent_control_call_count"] == 4
    assert payload["agent_control_tools_seen"] == [
        "followup_task",
        "interrupt_agent",
        "send_message",
        "spawn_agent",
    ]
    assert payload["agent_layer_call_count"] == 6
    assert payload["agent_layer_tools_seen"] == sorted(names)

def test_aggregate_does_not_turn_missing_usage_or_tool_name_into_zero(tmp_path: Path):
    sessions = tmp_path / "sessions"
    extra = [
        {
            "timestamp": "2026-08-26T00:00:02Z",
            "type": "response_item",
            "payload": {"type": "function_call", "arguments": "DO_NOT_LEAK"},
        },
        {
            "timestamp": "2026-08-26T00:00:03Z",
            "type": "event_msg",
            "payload": {"type": "token_count", "info": {}},
        },
    ]
    write_rollout(
        sessions,
        thread_id=CHILD_THREAD,
        timestamp="2026-08-26T00:00:00Z",
        parent_thread_id=ROOT_THREAD,
        agent_role=ROLE,
        agent_path=TASK_PATH,
        extra_records=extra,
    )

    result = run_tool(sessions, "aggregate", CHILD_THREAD)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["tool_call_count"] == 1
    assert payload["agent_control_call_count"] is None
    assert payload["agent_control_tools_seen"] is None
    assert payload["tool_name_observation_complete"] is False
    assert payload["raw_tokens"] is None
    assert payload["token_usage_observation_complete"] is False


def test_aggregate_preserves_unobservable_sandbox_as_unknown(tmp_path: Path):
    sessions = tmp_path / "sessions"
    turns = [
        {
            "timestamp": "2026-08-26T00:00:01Z",
            "type": "turn_context",
            "payload": {
                "model": "gpt-5.6-luna",
                "effort": "max",
                "permission_profile": {"type": "disabled"},
                "cwd": "/repo",
            },
        }
    ]
    write_rollout(
        sessions,
        thread_id=CHILD_THREAD,
        timestamp="2026-08-26T00:00:00Z",
        parent_thread_id=ROOT_THREAD,
        agent_role=ROLE,
        agent_path=TASK_PATH,
        turns=turns,
    )

    result = run_tool(sessions, "aggregate", CHILD_THREAD)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["sandbox_policy_type"] is None
    assert payload["permission_profile_type"] == "disabled"


def test_maintainer_evidence_helper_is_not_shipped():
    manifest = json.loads((ROOT / ".codex-plugin" / "package-integrity.json").read_text())
    assert "scripts/host_qualification_evidence.py" not in manifest["files"]
