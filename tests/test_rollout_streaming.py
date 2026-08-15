from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
INSPECTOR = ROOT / "scripts" / "inspect-agent-runtime.py"
THREAD = "11111111-1111-7111-8111-111111111111"
PARENT = "00000000-0000-7000-8000-000000000000"
ROLE = "subagents_dispatch_worker"


def load_inspector():
    spec = importlib.util.spec_from_file_location("rollout_streaming_inspector", INSPECTOR)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rollout_records() -> list[dict]:
    return [
        {
            "type": "session_meta",
            "payload": {
                "id": THREAD,
                "parent_thread_id": PARENT,
                "agent_role": ROLE,
                "model_provider": "openai",
            },
        },
        {
            "type": "turn_context",
            "payload": {
                "model": "gpt-5.6-luna",
                "effort": "max",
                "sandbox_policy": {"type": "workspace-write"},
                "permission_profile": {"type": "default"},
                "cwd": "/project",
            },
        },
    ]


def write_rollout(path: Path, *, trailing_lines: list[str] | None = None) -> None:
    lines = [json.dumps(record) for record in rollout_records()]
    lines.extend(trailing_lines or [])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def inspect(module, path: Path):
    return module.inspect_rollout(
        path,
        thread_id=THREAD,
        expected_parent_thread_id=PARENT,
        expected_agent_role=ROLE,
    )


def test_rollout_records_are_parsed_before_end_of_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    module = load_inspector()
    rollout = tmp_path / f"rollout-test-{THREAD}.jsonl"
    write_rollout(rollout, trailing_lines=["x" * 1024 for _ in range(256)])

    original_read = module.os.read
    original_loads = module.json.loads
    eof_seen = False
    parsed_before_eof = False

    def tracking_read(fd: int, size: int) -> bytes:
        nonlocal eof_seen
        chunk = original_read(fd, size)
        if not chunk:
            eof_seen = True
        return chunk

    def tracking_loads(value: str):
        nonlocal parsed_before_eof
        if not eof_seen:
            parsed_before_eof = True
        return original_loads(value)

    monkeypatch.setattr(module.os, "read", tracking_read)
    monkeypatch.setattr(module.json, "loads", tracking_loads)

    result = inspect(module, rollout)

    assert result["model"] == "gpt-5.6-luna"
    assert parsed_before_eof is True


def test_rollout_total_scan_limit_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    module = load_inspector()
    rollout = tmp_path / f"rollout-test-{THREAD}.jsonl"
    write_rollout(rollout, trailing_lines=["padding" * 64])
    monkeypatch.setattr(module, "MAX_ROLLOUT_BYTES", rollout.stat().st_size - 1, raising=False)

    with pytest.raises(SystemExit, match="rollout exceeds maximum scan size"):
        inspect(module, rollout)


def test_rollout_line_limit_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    module = load_inspector()
    rollout = tmp_path / f"rollout-test-{THREAD}.jsonl"
    target_lines = [json.dumps(record) for record in rollout_records()]
    target_max = max(len(line.encode("utf-8")) for line in target_lines)
    limit = target_max + 32
    write_rollout(rollout, trailing_lines=["z" * (limit + 1)])
    monkeypatch.setattr(module, "MAX_LINE_BYTES", limit, raising=False)

    with pytest.raises(SystemExit, match="rollout line exceeds maximum size"):
        inspect(module, rollout)
