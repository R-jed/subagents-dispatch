from __future__ import annotations

import gc
import importlib.util
import json
from pathlib import Path
import weakref

import pytest


ROOT = Path(__file__).resolve().parents[1]
INSPECTOR = ROOT / "scripts" / "inspect-agent-runtime.py"
THREAD = "11111111-1111-7111-8111-111111111111"
PARENT = "00000000-0000-7000-8000-000000000000"
ROLE = "subagents_dispatch_worker"


def load_inspector():
    spec = importlib.util.spec_from_file_location("rollout_streaming_followup", INSPECTOR)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def session_meta() -> dict:
    return {
        "type": "session_meta",
        "payload": {
            "id": THREAD,
            "parent_thread_id": PARENT,
            "agent_role": ROLE,
            "model_provider": "openai",
        },
    }


def turn_context() -> dict:
    return {
        "type": "turn_context",
        "payload": {
            "model": "gpt-5.6-luna",
            "effort": "max",
            "sandbox_policy": {"type": "workspace-write"},
            "permission_profile": {"type": "default"},
            "cwd": "/project",
        },
    }


def inspect(module, rollout: Path):
    return module.inspect_rollout(
        rollout,
        thread_id=THREAD,
        expected_parent_thread_id=PARENT,
        expected_agent_role=ROLE,
    )


def test_cr_only_rollout_preserves_text_iterator_newline_compatibility(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    module = load_inspector()
    rollout = tmp_path / f"rollout-test-{THREAD}.jsonl"
    lines = [json.dumps(session_meta()), json.dumps(turn_context())]
    rollout.write_bytes("\r".join(lines).encode("utf-8") + b"\r")
    monkeypatch.setattr(module, "READ_CHUNK_BYTES", 19)

    result = inspect(module, rollout)

    assert result["thread_id"] == THREAD
    assert result["model"] == "gpt-5.6-luna"
    assert result["effort"] == "max"


def test_turn_context_payloads_are_aggregated_without_accumulating_all_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    module = load_inspector()
    rollout = tmp_path / f"rollout-test-{THREAD}.jsonl"
    records = [session_meta(), *[turn_context() for _ in range(32)]]
    rollout.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )

    class TrackedPayload(dict):
        pass

    original_loads = module.json.loads
    payload_refs: list[weakref.ReferenceType[TrackedPayload]] = []
    max_live_payloads = 0

    def tracking_loads(value: str):
        nonlocal max_live_payloads
        record = original_loads(value)
        if isinstance(record, dict) and record.get("type") == "turn_context":
            payload = TrackedPayload(record["payload"])
            record["payload"] = payload
            payload_refs.append(weakref.ref(payload))
            gc.collect()
            max_live_payloads = max(
                max_live_payloads,
                sum(ref() is not None for ref in payload_refs),
            )
        return record

    monkeypatch.setattr(module.json, "loads", tracking_loads)

    result = inspect(module, rollout)

    assert result["model"] == "gpt-5.6-luna"
    assert result["effort"] == "max"
    assert max_live_payloads <= 2
