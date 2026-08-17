from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tomllib

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

HOOK_ACTIVATION_RED = pytest.mark.xfail(
    strict=True,
    reason="V4 lifecycle Hooks remain staged until the real Host smoke gate passes",
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


def test_public_surface_is_orchestrate_and_doctor_only():
    skills = sorted(path.name for path in (ROOT / "skills").iterdir() if path.is_dir())
    assert skills == ["doctor", "orchestrate"]


def test_orchestrate_owns_v4_state_without_silent_legacy_migration():
    text = (SCRIPTS / "orchestrate_v4.py").read_text(encoding="utf-8")
    assert "import dispatch_state_v4 as state" in text
    assert "dispatch_state.py" not in text
    state = load_module("v4_cutover_state", SCRIPTS / "dispatch_state_v4.py")
    assert state.SCHEMA_VERSION == "4.0"
    capsule = state.new_state(thread_id="v4-red-thread")
    assert {
        "state_revision",
        "work_units",
        "executions",
        "writer_lease",
        "pending_controls",
    }.issubset(capsule)


def test_v4_runtime_state_machines_are_active_contracts():
    state = load_module("v4_cutover_state_machines", SCRIPTS / "dispatch_state_v4.py")
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
    assert set(state.WRITER_LEASE_STATES) == {
        "RESERVED",
        "HELD",
        "REVOKING",
        "UNKNOWN",
        "RELEASED",
    }
    assert set(state.PENDING_CONTROL_STATES) == {
        "PREPARED",
        "IN_FLIGHT",
        "ACKED",
        "UNKNOWN",
        "CANCELLED",
    }
    control = load_module("v4_cutover_control", SCRIPTS / "dispatch_control_v4.py")
    assert callable(control.prepare_control)


def test_host_capability_adapter_exists():
    assert (SCRIPTS / "host_capabilities.py").is_file()


@HOOK_ACTIVATION_RED
def test_red_managed_guard_covers_lifecycle_and_stop_events():
    payload = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    hooks = payload["hooks"]
    assert {"PreToolUse", "PostToolUse", "SubagentStop"}.issubset(hooks)
    pre_matchers = {group.get("matcher") for group in hooks["PreToolUse"]}
    post_matchers = {group.get("matcher") for group in hooks["PostToolUse"]}
    assert "spawn_agent|followup_task|interrupt_agent" in pre_matchers
    assert "spawn_agent|followup_task|interrupt_agent" in post_matchers


def test_investigator_profile_is_terra_high():
    profile = tomllib.loads(
        (ROOT / "agent-profiles" / "subagents-dispatch-investigator.toml").read_text(encoding="utf-8")
    )
    assert profile["model"] == "gpt-5.6-terra"
    assert profile["model_reasoning_effort"] == "high"
