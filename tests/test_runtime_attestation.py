from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
INSPECTOR = ROOT / "scripts" / "inspect-agent-runtime.py"
THREAD = "11111111-1111-7111-8111-111111111111"
PARENT = "00000000-0000-7000-8000-000000000000"
ROLE = "subagents_dispatch_worker"


def write_rollout(
    sessions: Path,
    *,
    thread_id: str = THREAD,
    session_id: str | None = None,
    parent_thread_id: str | None = PARENT,
    agent_role: str | None = ROLE,
    turns: list[dict] | None = None,
    relative_dir: str = "2026/08/10",
    extra_records: list[dict] | None = None,
) -> Path:
    folder = sessions / relative_dir
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"rollout-2026-08-10T23-55-00-{thread_id}.jsonl"
    session = {
        "timestamp": "2026-08-10T23:55:00Z",
        "type": "session_meta",
        "payload": {
            "session_id": thread_id if session_id is None else session_id,
            "id": thread_id,
            "parent_thread_id": parent_thread_id,
            "agent_role": agent_role,
            "cli_version": "0.999.0-test",
            "cwd": "/private/project",
            "model_provider": "openai",
        },
    }
    default_turn = {
        "timestamp": "2026-08-10T23:55:01Z",
        "type": "turn_context",
        "payload": {
            "model": "gpt-5.6-luna",
            "effort": "max",
            "sandbox_policy": {"type": "workspace-write", "writable_roots": ["SECRET"]},
            "permission_profile": {"type": "default", "private": "SECRET"},
            "cwd": "/private/project",
            "developer_instructions": "SECRET INSTRUCTIONS",
        },
    }
    records = [session]
    records.extend(extra_records or [])
    records.extend(turns if turns is not None else [default_turn])
    path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )
    return path


def run_inspector(sessions: Path, *extra: str, thread_id: str = THREAD) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(INSPECTOR),
            thread_id,
            "--sessions-dir",
            str(sessions),
            *extra,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_exact_rollout_returns_only_allowlisted_runtime_metadata(tmp_path: Path):
    sessions = tmp_path / "sessions"
    write_rollout(
        sessions,
        extra_records=[
            {
                "timestamp": "2026-08-10T23:55:00Z",
                "type": "event_msg",
                "payload": {
                    "type": "user_message",
                    "message": 'SECRET prompt says {"type":"turn_context"}',
                },
            },
            {
                "timestamp": "2026-08-10T23:55:00Z",
                "type": "response_item",
                "payload": {
                    "type": "reasoning",
                    "summary": "SECRET REASONING",
                },
            },
        ],
    )

    result = run_inspector(
        sessions,
        "--expected-parent-thread-id",
        PARENT,
        "--expected-agent-role",
        ROLE,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {
        "agent_role": ROLE,
        "effort": "max",
        "model": "gpt-5.6-luna",
        "parent_thread_id": PARENT,
        "permission_profile_type": "default",
        "runtime_version": "0.999.0-test",
        "sandbox_policy_type": "workspace-write",
        "thread_id": THREAD,
    }
    serialized = result.stdout
    assert "SECRET" not in serialized
    assert "developer_instructions" not in serialized
    assert "/private/project" not in serialized
    assert "rollout-" not in serialized


def test_distinct_live_session_id_does_not_change_child_binding(tmp_path: Path):
    sessions = tmp_path / "sessions"
    session_id = "22222222-2222-7222-8222-222222222222"
    write_rollout(sessions, session_id=session_id)

    result = run_inspector(
        sessions,
        "--expected-parent-thread-id",
        PARENT,
        "--expected-agent-role",
        ROLE,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["thread_id"] == THREAD
    assert payload["parent_thread_id"] == PARENT
    assert payload["agent_role"] == ROLE
    assert payload["model"] == "gpt-5.6-luna"
    assert payload["effort"] == "max"
    assert payload["sandbox_policy_type"] == "workspace-write"
    assert payload["permission_profile_type"] == "default"
    assert "session_id" not in payload


def test_missing_exact_rollout_is_rejected(tmp_path: Path):
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    result = run_inspector(sessions)
    assert result.returncode != 0
    assert "no rollout filename matched" in result.stderr


def test_duplicate_exact_rollout_is_rejected(tmp_path: Path):
    sessions = tmp_path / "sessions"
    write_rollout(sessions, relative_dir="2026/08/10")
    write_rollout(sessions, relative_dir="2026/08/11")
    result = run_inspector(sessions)
    assert result.returncode != 0
    assert "multiple rollout filenames matched" in result.stderr


def test_symlinked_rollout_is_rejected_when_supported(tmp_path: Path):
    sessions = tmp_path / "sessions"
    real_root = tmp_path / "real"
    real = write_rollout(real_root)
    target_dir = sessions / "2026/08/10"
    target_dir.mkdir(parents=True)
    link = target_dir / real.name
    try:
        link.symlink_to(real)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable in this test environment")

    result = run_inspector(sessions)
    assert result.returncode != 0
    assert "symlinked rollout" in result.stderr


def test_session_identity_mismatch_is_rejected(tmp_path: Path):
    sessions = tmp_path / "sessions"
    path = write_rollout(sessions)
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    records[0]["payload"]["id"] = "22222222-2222-7222-8222-222222222222"
    path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")

    result = run_inspector(sessions)
    assert result.returncode != 0
    assert "does not identify the requested thread" in result.stderr


def test_expected_parent_and_role_bind_the_observation(tmp_path: Path):
    sessions = tmp_path / "sessions"
    write_rollout(sessions)

    wrong_parent = run_inspector(
        sessions,
        "--expected-parent-thread-id",
        "22222222-2222-7222-8222-222222222222",
    )
    assert wrong_parent.returncode != 0
    assert "parent_thread_id does not match" in wrong_parent.stderr

    wrong_role = run_inspector(
        sessions,
        "--expected-agent-role",
        "subagents_dispatch_reader",
    )
    assert wrong_role.returncode != 0
    assert "agent_role does not match" in wrong_role.stderr


def test_model_drift_across_turns_is_rejected(tmp_path: Path):
    sessions = tmp_path / "sessions"
    turns = [
        {
            "type": "turn_context",
            "payload": {
                "model": "gpt-5.6-luna",
                "effort": "max",
                "sandbox_policy": {"type": "workspace-write"},
                "permission_profile": {"type": "default"},
            },
        },
        {
            "type": "turn_context",
            "payload": {
                "model": "gpt-5.6-terra",
                "effort": "max",
                "sandbox_policy": {"type": "workspace-write"},
                "permission_profile": {"type": "default"},
            },
        },
    ]
    write_rollout(sessions, turns=turns)

    result = run_inspector(sessions)
    assert result.returncode != 0
    assert "conflicting model values" in result.stderr


def test_effort_drift_across_turns_is_rejected(tmp_path: Path):
    sessions = tmp_path / "sessions"
    turns = [
        {
            "type": "turn_context",
            "payload": {
                "model": "gpt-5.6-luna",
                "effort": "high",
                "sandbox_policy": {"type": "workspace-write"},
                "permission_profile": {"type": "default"},
            },
        },
        {
            "type": "turn_context",
            "payload": {
                "model": "gpt-5.6-luna",
                "effort": "max",
                "sandbox_policy": {"type": "workspace-write"},
                "permission_profile": {"type": "default"},
            },
        },
    ]
    write_rollout(sessions, turns=turns)

    result = run_inspector(sessions)
    assert result.returncode != 0
    assert "conflicting effort values" in result.stderr


def test_missing_field_in_any_turn_stays_unobserved_instead_of_being_inferred(tmp_path: Path):
    sessions = tmp_path / "sessions"
    turns = [
        {
            "type": "turn_context",
            "payload": {
                "model": "gpt-5.6-luna",
                "effort": "max",
                "sandbox_policy": {"type": "workspace-write"},
                "permission_profile": {"type": "default"},
            },
        },
        {
            "type": "turn_context",
            "payload": {
                "model": "gpt-5.6-luna",
                "sandbox_policy": {"type": "workspace-write"},
                "permission_profile": {"type": "default"},
            },
        },
    ]
    write_rollout(sessions, turns=turns)

    result = run_inspector(sessions)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["model"] == "gpt-5.6-luna"
    assert payload["effort"] is None


@pytest.mark.parametrize(
    ("field", "first", "second", "message"),
    [
        ("sandbox_policy", {"type": "workspace-write"}, {"type": "read-only"}, "sandbox policy"),
        ("permission_profile", {"type": "default"}, {"type": "elevated"}, "permission profile"),
    ],
)
def test_permission_metadata_drift_is_rejected(
    tmp_path: Path,
    field: str,
    first: dict,
    second: dict,
    message: str,
):
    sessions = tmp_path / "sessions"
    base = {
        "model": "gpt-5.6-luna",
        "effort": "max",
        "sandbox_policy": {"type": "workspace-write"},
        "permission_profile": {"type": "default"},
    }
    first_payload = {**base, field: first}
    second_payload = {**base, field: second}
    write_rollout(
        sessions,
        turns=[
            {"type": "turn_context", "payload": first_payload},
            {"type": "turn_context", "payload": second_payload},
        ],
    )

    result = run_inspector(sessions)
    assert result.returncode != 0
    assert f"conflicting {message} values" in result.stderr
