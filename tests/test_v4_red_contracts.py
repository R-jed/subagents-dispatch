from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tomllib

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

V4_RED = pytest.mark.xfail(
    strict=True,
    reason="V4 implementation is intentionally absent during architecture-freeze phase",
)


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


@V4_RED
def test_red_public_surface_is_orchestrate_and_doctor_only():
    skills = sorted(path.name for path in (ROOT / "skills").iterdir() if path.is_dir())
    assert skills == ["doctor", "orchestrate"]


@V4_RED
def test_red_dispatch_state_uses_v4_schema():
    state = load_module("v4_red_dispatch_state_schema", SCRIPTS / "dispatch_state.py")
    assert state.SCHEMA_VERSION == "4.0"


@V4_RED
def test_red_state_capsule_has_v4_runtime_entities():
    state = load_module("v4_red_dispatch_state_entities", SCRIPTS / "dispatch_state.py")
    capsule = state.new_state(thread_id="v4-red-thread")
    assert {
        "state_revision",
        "work_units",
        "executions",
        "writer_lease",
        "pending_controls",
    }.issubset(capsule)


@V4_RED
def test_red_work_unit_state_machine_exists():
    state = load_module("v4_red_dispatch_state_work_unit", SCRIPTS / "dispatch_state.py")
    assert set(state.WORK_UNIT_STATES) == {
        "BLOCKED",
        "READY",
        "EXECUTING",
        "RESULT_READY",
        "VERIFYING",
        "ACCEPTED",
        "REJECTED",
        "CANCELLED",
    }


@V4_RED
def test_red_writer_lease_state_machine_exists():
    state = load_module("v4_red_dispatch_state_writer", SCRIPTS / "dispatch_state.py")
    assert set(state.WRITER_LEASE_STATES) == {
        "RESERVED",
        "HELD",
        "REVOKING",
        "UNKNOWN",
        "RELEASED",
    }


@V4_RED
def test_red_pending_control_state_machine_and_prepare_api_exist():
    state = load_module("v4_red_dispatch_state_control", SCRIPTS / "dispatch_state.py")
    assert set(state.PENDING_CONTROL_STATES) == {
        "PREPARED",
        "IN_FLIGHT",
        "ACKED",
        "UNKNOWN",
        "CANCELLED",
    }
    assert callable(state.prepare_control)


def test_host_capability_adapter_exists():
    assert (SCRIPTS / "host_capabilities.py").is_file()


@V4_RED
def test_red_managed_guard_covers_lifecycle_and_stop_events():
    payload = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    hooks = payload["hooks"]

    assert {"PreToolUse", "PostToolUse", "SubagentStop"}.issubset(hooks)

    pre_matchers = {group.get("matcher") for group in hooks["PreToolUse"]}
    post_matchers = {group.get("matcher") for group in hooks["PostToolUse"]}

    assert "spawn_agent|followup_task|interrupt_agent" in pre_matchers
    assert "spawn_agent|followup_task|interrupt_agent" in post_matchers


@V4_RED
def test_red_investigator_profile_is_terra_high():
    profile = tomllib.loads(
        (ROOT / "agent-profiles" / "subagents-dispatch-investigator.toml").read_text(encoding="utf-8")
    )
    assert profile["model"] == "gpt-5.6-terra"
    assert profile["model_reasoning_effort"] == "high"
