from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


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


def evidence() -> dict:
    lifecycle = ["spawn_agent", "followup_task", "interrupt_agent"]
    guarded = [*lifecycle, "list_agents"]
    return {
        "surface": "multi_agent_v2",
        "tools": lifecycle + ["list_agents", "wait_agent"],
        "hooks": {
            "PreToolUse": guarded,
            "PostToolUse": guarded,
            "SubagentStop": True,
        },
        "fork_turns_none": True,
        "max_spawned_threads": 3,
    }


def trust(**overrides) -> dict:
    value = {
        "manifest_sha256": "b" * 64,
        "trusted_current_definition": True,
        "evidence_ref": "host-smoke:H00",
    }
    value.update(overrides)
    return value


def test_guard_summary_requires_execution_ready_host_and_current_trust():
    module = load_module("rc2_guard_proof", "host_capabilities.py")
    snapshot = module.normalize_host_capabilities(evidence())
    proof = module.build_guard_coverage_proof(
        snapshot,
        session_id="thread-proof",
        trust_evidence=trust(),
    )
    assert proof == {
        "schema_version": "4.0",
        "authority": "diagnostic_only",
        "session_id": "thread-proof",
        "manifest_sha256": "b" * 64,
        "trusted_current_definition": True,
        "pre_tool_use": True,
        "post_tool_use": True,
        "host_observation_guard": True,
        "subagent_stop_veto": True,
        "evidence_ref": "host-smoke:H00",
    }

    with pytest.raises(module.HostCapabilityError, match="not proven trusted"):
        module.build_guard_coverage_proof(
            snapshot,
            session_id="thread-proof",
            trust_evidence=trust(trusted_current_definition=False),
        )


def test_guard_summary_rejects_incomplete_lifecycle_hook_snapshot():
    module = load_module("rc2_guard_proof_missing", "host_capabilities.py")
    raw = evidence()
    raw["hooks"]["PostToolUse"] = ["spawn_agent", "followup_task", "list_agents"]
    snapshot = module.normalize_host_capabilities(raw)
    assert snapshot["execution_ready"] is False
    with pytest.raises(module.HostCapabilityError, match="execution-ready"):
        module.build_guard_coverage_proof(
            snapshot,
            session_id="thread-proof",
            trust_evidence=trust(),
        )
