from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load_module(name: str, filename: str):
    scripts = str(SCRIPTS)
    sys.path.insert(0, scripts)
    try:
        spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts)


def host_snapshot(capacity: int | None = 4) -> dict:
    host = load_module(f"host_adapter_caps_{capacity}", "host_capabilities.py")
    return host.normalize_host_capabilities(
        {
            "surface": "multi_agent_v2",
            "tools": [
                "spawn_agent",
                "followup_task",
                "interrupt_agent",
                "list_agents",
                "wait_agent",
            ],
            "fork_turns_none": True,
            "max_concurrent_threads_per_session": capacity,
        }
    )


def payload_with_ready_units(count: int = 2) -> dict:
    state = load_module(f"host_adapter_state_{count}", "dispatch_state_v4.py")
    graph = load_module(f"host_adapter_graph_{count}", "work_graph_v4.py")
    payload = state.new_state(thread_id=f"host-adapter-{count}")
    payload["work_units"] = [
        graph.make_work_unit(
            unit_id=f"U{index}",
            intent="inspect",
            goal=f"inspect {index}",
            output="evidence",
            done_when="verified",
        )
        for index in range(1, count + 1)
    ]
    state.validate_state_payload(payload)
    return payload


def test_normalized_capacity_keeps_codex_v2_session_semantics():
    snapshot = host_snapshot(4)
    assert snapshot["max_concurrent_threads_per_session"] == 4
    assert snapshot["capacity_includes_primary"] is True
    assert "max_spawned_threads" not in snapshot
    assert "capacity_excludes_primary" not in snapshot


def test_missing_host_snapshot_fails_closed_in_constraint_projection():
    scheduler = load_module("host_adapter_scheduler_missing", "scheduler_v4.py")
    decision = scheduler.constraint_snapshot(
        payload_with_ready_units(),
        capability_snapshot=None,
        wakeup_reason="USER_INPUT",
    )
    assert decision["host_ready"] is False
    assert decision["host_missing"] == ["capability_snapshot"]
    assert decision["available_launch_slots"] == 0
    assert decision["stop_reason"] == "host_not_execution_ready"


def test_session_capacity_counts_primary_before_managed_children():
    scheduler = load_module("host_adapter_scheduler_capacity", "scheduler_v4.py")
    decision = scheduler.constraint_snapshot(
        payload_with_ready_units(4),
        capability_snapshot=host_snapshot(4),
        wakeup_reason="USER_INPUT",
    )
    assert decision["host_session_capacity"] == 4
    assert decision["available_launch_slots"] == 3


def test_unknown_numeric_capacity_does_not_invent_a_limit_after_capabilities_are_proven():
    scheduler = load_module("host_adapter_scheduler_unknown", "scheduler_v4.py")
    decision = scheduler.constraint_snapshot(
        payload_with_ready_units(4),
        capability_snapshot=host_snapshot(None),
        wakeup_reason="USER_INPUT",
    )
    assert decision["host_ready"] is True
    assert decision["host_session_capacity"] is None
    assert decision["available_launch_slots"] == 4
