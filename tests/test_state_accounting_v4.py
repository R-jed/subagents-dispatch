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


def populated_state(state) -> dict:
    payload = state.new_state(thread_id="thread-bounded")
    payload["work_units"] = [
        {
            "unit_id": "U1",
            "intent": "inspect",
            "goal": "bounded accounting",
            "output": "facts",
            "depends_on": [],
            "state": "RESULT_READY",
            "ownership": {"write": [], "forbidden": []},
            "authority_ceiling": "none",
            "write_scope_ceiling": [],
            "done_when": "facts verified",
            "accepted_result_ref": None,
            "accepted_execution_id": None,
            "accepted_control_epoch": None,
        }
    ]
    payload["executions"] = [
        {
            "execution_id": "exec-1",
            "unit_id": "U1",
            "attempt_no": 1,
            "profile_id": "reader",
            "agent_id": "agent-1",
            "native_task_name": "sd_u1_a1",
            "model": "gpt-5.6-luna",
            "effort": "max",
            "granted_authority": "none",
            "granted_write_scope": [],
            "workspace_id": "canonical",
            "lifecycle": "COMPLETED",
            "control_epoch": 0,
            "followup_count": 0,
            "failure_origin": "none",
            "blocker": "none",
            "quarantine_reason": None,
        }
    ]
    return payload


def compact_observation() -> dict:
    return {
        "ref": "host-observation:exec-1:0:none:COMPLETED",
        "kind": "host_observation",
        "execution_id": "exec-1",
        "control_epoch": 0,
        "lease_epoch": None,
        "lifecycle": "COMPLETED",
    }


def test_accounting_accepts_only_compact_native_host_observation_shape():
    state = load_module("bounded_state_shape", "dispatch_state_v4.py")
    payload = populated_state(state)
    payload["accounting_refs"] = [compact_observation()]
    assert state.validate_state_payload(payload) == payload

    payload["accounting_refs"][0]["tool_use_id"] = "retired-hook-id"
    with pytest.raises(state.StatePayloadError, match="host_observation accounting ref has invalid fields"):
        state.validate_state_payload(payload)


def test_accounting_refs_require_unique_stable_identity():
    state = load_module("bounded_state_unique", "dispatch_state_v4.py")
    payload = populated_state(state)
    event = compact_observation()
    payload["accounting_refs"] = [event, dict(event)]

    with pytest.raises(state.StatePayloadError, match="unique stable refs"):
        state.validate_state_payload(payload)


def test_state_fails_closed_before_unbounded_accounting_growth():
    state = load_module("bounded_state_limit", "dispatch_state_v4.py")
    payload = populated_state(state)
    payload["accounting_refs"] = [
        {
            "ref": f"evidence:{index}:{'x' * 1000}",
            "kind": "external_evidence",
        }
        for index in range(100)
    ]

    with pytest.raises(state.StatePayloadError, match="state exceeds"):
        state.validate_state_payload(payload)
