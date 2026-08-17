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


def test_one_host_occupancy_observation_authorizes_at_most_one_fresh_spawn():
    state = load_module("rc4_capacity_state", "dispatch_state_v4.py")
    graph = load_module("rc4_capacity_graph", "work_graph_v4.py")
    host = load_module("rc4_capacity_host", "host_capabilities.py")
    scheduler = load_module("rc4_capacity_scheduler", "scheduler_v4.py")

    payload = state.new_state(thread_id="thread-capacity")
    payload["team_plan_revision"] = 1
    payload["work_units"] = [
        graph.make_work_unit(
            unit_id=f"U{index}",
            intent="inspect",
            goal=f"inspect {index}",
            output="facts",
            done_when="Main verifies facts",
        )
        for index in range(1, 4)
    ]
    payload["accounting_refs"] = [
        {
            "ref": "host-capacity-observation:tool-capacity",
            "kind": "host_capacity_observation",
            "source": "post_tool_use:list_agents",
            "turn_id": "turn-capacity",
            "tool_use_id": "tool-capacity",
            "resident_children": 0,
            "settled_children": 0,
            "active_children": 0,
            "managed_resident_children": 0,
            "unmanaged_resident_children": 0,
            "response_digest": "a" * 64,
        }
    ]
    snapshot = host.normalize_host_capabilities(
        {
            "surface": "multi_agent_v2",
            "tools": ["spawn_agent", "followup_task", "interrupt_agent", "list_agents", "wait_agent"],
            "hooks": {
                "PreToolUse": ["spawn_agent", "followup_task", "interrupt_agent", "list_agents"],
                "PostToolUse": ["spawn_agent", "followup_task", "interrupt_agent", "list_agents"],
                "SubagentStop": True,
            },
            "fork_turns_none": True,
            "max_spawned_threads": 3,
        }
    )

    decision = scheduler.scheduler_decision(
        payload,
        capability_snapshot=snapshot,
        wakeup_reason="USER_INPUT",
    )
    assert decision["initial_fanout"] is True
    assert decision["launch_budget"] == 1
    assert len(decision["actions"]) == 1
