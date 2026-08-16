from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "contracts" / "v4-architecture.json"


def load_spec() -> dict:
    return json.loads(SPEC.read_text(encoding="utf-8"))


def test_v4_architecture_freeze_is_internally_consistent():
    spec = load_spec()

    assert spec["schema_version"] == "4.0.0-freeze-1"
    assert spec["public_skills"] == ["orchestrate", "doctor"]
    assert spec["semantic_roles"] == ["main", "work", "review"]

    profiles = spec["profiles"]
    assert profiles["reader"]["model"] == "gpt-5.6-luna"
    assert profiles["reader"]["effort"] == "max"
    assert profiles["worker"]["model"] == "gpt-5.6-luna"
    assert profiles["worker"]["effort"] == "max"
    assert profiles["investigator"]["model"] == "gpt-5.6-terra"
    assert profiles["investigator"]["effort"] == "high"
    assert profiles["solver"]["model"] == "gpt-5.6-sol"
    assert profiles["solver"]["effort"] == "high"
    assert profiles["advisor"]["model"] == "gpt-5.6-sol"
    assert profiles["advisor"]["effort"] == "high"

    assert spec["routing"]["dynamic_reasoning_effort"] is False
    assert spec["routing"]["peer_messaging_on_correctness_path"] is False

    delegation = spec["delegation"]
    assert delegation["max_depth"] == 1
    assert delegation["fork_turns"] == "none"
    assert delegation["initial_managed_children_max"] == 2
    assert delegation["product_managed_children_max"] == 3
    assert delegation["host_capacity_excludes_primary"] is True

    assert spec["work_unit"]["dependency_unlock_state"] == "ACCEPTED"
    assert spec["work_unit"]["host_completed_unlocks_dependency"] is False
    assert spec["reconciliation"]["host_completed_maps_to_work_unit"] == "RESULT_READY"
    assert spec["reconciliation"]["stale_observation_action"] == "discard"

    writer = spec["writer_lease"]
    assert writer["parallel_isolated_writers_v4"] is False
    assert writer["main_requires_lease_for_managed_write"] is True
    assert set(writer["blocking_states"]) == {"RESERVED", "HELD", "REVOKING", "UNKNOWN"}

    control = spec["pending_control"]
    assert control["single_use_binding"] == "tool_use_id"
    assert control["serial_per_execution"] is True

    guard = spec["guard"]
    assert guard["managed_lifecycle_authority_owner"] == "main"
    assert guard["host_hook_coverage_is_release_gate"] is True
    assert guard["subagent_stop_forces_no_auto_continue"] is True

    migration = spec["migration"]
    assert migration["source_family"] == "V3.x"
    assert migration["silent_live_state_migration"] is False
    assert migration["unresolved_live_state"] == "fail_closed"


def test_v4_architecture_freeze_has_no_hidden_dynamic_effort_or_parallel_writer_path():
    spec = load_spec()

    excluded = set(spec["excluded_from_v4_0_0"])
    assert "dynamic_reasoning_effort" in excluded
    assert "parallel_isolated_writers" in excluded
    assert "automatic_worktree_manager" in excluded
    assert spec["state"]["database"] is False
    assert spec["state"]["temporary_thread_scoped"] is True
