from __future__ import annotations

import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SPAWN_GUARD = SCRIPTS / "spawn_guard.py"
DISPATCH_STATE = SCRIPTS / "dispatch_state.py"
WINDOWS_HOOK_LAUNCHER = ROOT / "hooks" / "run-python.cmd"


def load_module(name: str, path: Path):
    scripts = str(SCRIPTS)
    sys.path.insert(0, scripts)
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts)


state = load_module("spawn_guard_dispatch_state", DISPATCH_STATE)
guard = load_module("spawn_guard_under_test", SPAWN_GUARD)


def unit(
    *,
    role: str = "worker",
    task_name: str = "sd_u1_a1_execute",
    writer: bool = True,
) -> dict:
    return {
        "unit_id": "U1",
        "task_id": "task-1",
        "attempt": 1,
        "native_task_name": task_name,
        "agent_id": None,
        "role": role,
        "model_lane": "test-lane",
        "responsibility": {
            "outcome": "perform one bounded responsibility",
            "intent": "implement" if writer else "inspect",
            "acceptance": "Main verifies the result",
        },
        "authority": {
            "write_scope": ["owned.py"] if writer else [],
            "mutation_authority": "bounded-source-write" if writer else "none",
            "decision_rights": [],
        },
        "writer": writer,
        "control_state": "SPAWN_PENDING",
        "adopted": False,
        "accepted": False,
        "failure_origin": "none",
        "blocker": "none",
        "quarantine_reason": None,
    }


def prepare(tmp_path: Path, *, role: str = "worker", task_name: str = "sd_u1_a1_execute") -> None:
    payload = state.new_state(thread_id="root-thread")
    state.prepare_spawn(
        payload,
        unit(role=role, task_name=task_name, writer=role in {"worker", "solver"}),
        temp_root=tmp_path,
    )


def hook_input(
    *,
    target_agent_type: str = "subagents_dispatch_worker",
    fork_turns: str | None = "none",
    task_name: str = "sd_u1_a1_execute",
    caller_agent_type: str | None = None,
    session_id: str = "root-thread",
) -> dict:
    tool_input = {
        "task_name": task_name,
        "message": "SECRET_MESSAGE_MUST_NEVER_BE_EMITTED",
        "agent_type": target_agent_type,
    }
    if fork_turns is not None:
        tool_input["fork_turns"] = fork_turns
    payload = {
        "hook_event_name": "PreToolUse",
        "session_id": session_id,
        "turn_id": "turn-1",
        "cwd": "/tmp/project",
        "model": "gpt-5.6-sol",
        "permission_mode": "default",
        "tool_name": "spawn_agent",
        "tool_use_id": "call-1",
        "transcript_path": None,
        "tool_input": tool_input,
    }
    if caller_agent_type is not None:
        payload["agent_id"] = "child-agent"
        payload["agent_type"] = caller_agent_type
    return payload


def reason(result: dict | None) -> str:
    assert result is not None
    assert result["decision"] == "block"
    return str(result["reason"])


def run_guard_cli(raw: bytes) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, str(SPAWN_GUARD)],
        cwd=ROOT,
        input=raw,
        capture_output=True,
        check=False,
    )


def test_valid_prepared_managed_spawn_is_allowed(tmp_path: Path):
    prepare(tmp_path)
    assert guard.evaluate_hook(hook_input(), temp_root=tmp_path) is None


def test_missing_or_non_none_fork_turns_is_blocked(tmp_path: Path):
    prepare(tmp_path)
    missing = guard.evaluate_hook(hook_input(fork_turns=None), temp_root=tmp_path)
    full = guard.evaluate_hook(hook_input(fork_turns="all"), temp_root=tmp_path)
    partial = guard.evaluate_hook(hook_input(fork_turns="3"), temp_root=tmp_path)
    assert "fork_turns" in reason(missing)
    assert "fork_turns" in reason(full)
    assert "fork_turns" in reason(partial)


def test_wrong_managed_role_or_native_task_name_is_blocked(tmp_path: Path):
    prepare(tmp_path)
    wrong_role = guard.evaluate_hook(
        hook_input(target_agent_type="subagents_dispatch_reader"),
        temp_root=tmp_path,
    )
    wrong_task = guard.evaluate_hook(
        hook_input(task_name="sd_other_task"),
        temp_root=tmp_path,
    )
    assert "agent_type" in reason(wrong_role)
    assert "task_name" in reason(wrong_task)


def test_managed_spawn_without_prepared_state_is_blocked(tmp_path: Path):
    result = guard.evaluate_hook(hook_input(), temp_root=tmp_path)
    assert "prepared" in reason(result).lower()


def test_managed_child_cannot_spawn_further_agents(tmp_path: Path):
    result = guard.evaluate_hook(
        hook_input(
            target_agent_type="default",
            caller_agent_type="subagents_dispatch_worker",
            session_id="child-thread",
        ),
        temp_root=tmp_path,
    )
    assert "delegation depth" in reason(result).lower()


def test_pending_takeover_blocks_new_managed_spawn(tmp_path: Path):
    prepare(tmp_path)
    payload = state.load_state("root-thread", temp_root=tmp_path)
    assert payload is not None
    payload["pending_takeover"] = {"unit_id": "U1", "status": "pending"}
    state.write_state(payload, thread_id="root-thread", temp_root=tmp_path)

    result = guard.evaluate_hook(hook_input(), temp_root=tmp_path)
    assert "takeover" in reason(result).lower()


def test_corrupt_managed_state_fails_closed_without_leaking_tool_message(tmp_path: Path):
    state_dir = tmp_path / "subagents-dispatch" / "root-thread"
    state_dir.mkdir(parents=True)
    state_file = state_dir / "active.json"
    state_file.write_text("{broken", encoding="utf-8")
    if sys.platform != "win32":
        state_file.chmod(0o600)

    result = guard.evaluate_hook(hook_input(), temp_root=tmp_path)
    rendered = json.dumps(result, ensure_ascii=False)
    assert "state" in reason(result).lower()
    assert "SECRET_MESSAGE_MUST_NEVER_BE_EMITTED" not in rendered


def test_unrelated_spawn_passes_through_without_dispatch_state(tmp_path: Path):
    payload = hook_input(target_agent_type="unrelated_custom_agent", fork_turns="all")
    assert guard.evaluate_hook(payload, temp_root=tmp_path) is None


def test_non_spawn_tool_passes_through(tmp_path: Path):
    payload = hook_input()
    payload["tool_name"] = "apply_patch"
    assert guard.evaluate_hook(payload, temp_root=tmp_path) is None


def test_cli_invalid_json_uses_codex_blocking_exit_code():
    result = run_guard_cli(b"{broken")

    assert result.returncode == guard.BLOCKING_EXIT_CODE == 2
    assert result.stdout == b""
    assert b"invalid Hook JSON" in result.stderr


def test_cli_oversized_input_uses_codex_blocking_exit_code():
    result = run_guard_cli(b"x" * (guard.MAX_STDIN_BYTES + 1))

    assert result.returncode == guard.BLOCKING_EXIT_CODE == 2
    assert result.stdout == b""
    assert b"exceeded its bounded limit" in result.stderr


def test_internal_guard_error_uses_codex_blocking_exit_code_without_leaking_exception(
    monkeypatch,
    capsys,
):
    payload = json.dumps(hook_input()).encode("utf-8")
    fake_stdin = io.TextIOWrapper(io.BytesIO(payload), encoding="utf-8")
    monkeypatch.setattr(guard.sys, "stdin", fake_stdin)

    def crash() -> None:
        raise RuntimeError("SECRET_INTERNAL_EXCEPTION")

    monkeypatch.setattr(guard, "_runtime_temp_root", crash)

    with pytest.raises(SystemExit) as exc_info:
        guard.main()

    assert exc_info.value.code == guard.BLOCKING_EXIT_CODE == 2
    captured = capsys.readouterr()
    assert "managed spawn blocked" in captured.err
    assert "SECRET_INTERNAL_EXCEPTION" not in captured.err


def test_windows_launcher_falls_back_to_latest_python3_from_py_launcher(tmp_path: Path):
    if sys.platform != "win32":
        return

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_py = fake_bin / "py.cmd"
    fake_py.write_text(
        "@echo off\r\n"
        "if \"%~1\"==\"-3.11\" exit /b 1\r\n"
        "if not \"%~1\"==\"-3\" exit /b 1\r\n"
        "if \"%~2\"==\"-c\" exit /b 0\r\n"
        f'\"{sys.executable}\" \"%~2\"\r\n'
        "exit /b %errorlevel%\r\n",
        encoding="utf-8",
    )
    marker = tmp_path / "hook-ran.txt"
    probe = tmp_path / "probe.py"
    probe.write_text(
        "from pathlib import Path\n"
        "import os\n"
        "Path(os.environ['HOOK_MARKER']).write_text('ok', encoding='utf-8')\n",
        encoding="utf-8",
    )
    system_root = Path(os.environ["SystemRoot"])
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join([str(fake_bin), str(system_root / "System32")])
    env["PATHEXT"] = ".COM;.EXE;.BAT;.CMD"
    env["HOOK_MARKER"] = str(marker)

    result = subprocess.run(
        ["cmd.exe", "/d", "/c", str(WINDOWS_HOOK_LAUNCHER), str(probe)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert marker.read_text(encoding="utf-8") == "ok"
