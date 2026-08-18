from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
GUARD = SCRIPTS / "orchestration_guard.py"
STATE = SCRIPTS / "dispatch_state_v4.py"
CONTROL = SCRIPTS / "dispatch_control_v4.py"
MANAGED = SCRIPTS / "managed_execution_v4.py"
WRITER = SCRIPTS / "writer_lease_v4.py"


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


def _v4_state(state_module, tmp_path: Path) -> None:
    payload = state_module.new_state(thread_id="root-thread")
    payload["work_units"] = [
        {
            "unit_id": "U1",
            "intent": "inspect",
            "goal": "bounded read",
            "output": "facts",
            "depends_on": [],
            "state": "EXECUTING",
            "ownership": {"write": [], "forbidden": []},
            "authority_ceiling": "none",
            "write_scope_ceiling": [],
            "done_when": "Main verifies facts",
            "accepted_result_ref": None,
            "accepted_execution_id": None,
            "accepted_control_epoch": None,
        }
    ]
    payload["executions"] = [
        {
            "execution_id": "exec-1",
            "unit_id": "U1",
            "team_plan_revision": None,
            "attempt_no": 1,
            "profile_id": "reader",
            "agent_id": None,
            "native_task_name": "sd_u1_a1",
            "model": "gpt-5.6-luna",
            "effort": "max",
            "granted_authority": "none",
            "granted_write_scope": [],
            "workspace_id": "canonical",
            "lifecycle": "SPAWN_PENDING",
            "control_epoch": 0,
            "followup_count": 0,
            "failure_origin": "none",
            "blocker": "none",
            "quarantine_reason": None,
        }
    ]
    payload["accounting_refs"].append(
        {
            "ref": "host-capacity-observation:old",
            "kind": state_module.HOST_CAPACITY_OBSERVATION_KIND,
            "source": "post_tool_use:list_agents",
            "turn_id": "turn-observe",
            "tool_use_id": "tool-observe",
            "resident_children": 0,
            "settled_children": 0,
            "active_children": 0,
            "managed_resident_children": 0,
            "unmanaged_resident_children": 0,
            "response_digest": "a" * 64,
        }
    )
    state_module.write_state(payload, temp_root=tmp_path)


def _settled_writer_state(state_module, tmp_path: Path) -> None:
    payload = state_module.new_state(thread_id="root-thread")
    payload["work_units"] = [
        {
            "unit_id": "U1",
            "intent": "implement",
            "goal": "bounded write",
            "output": "patch",
            "depends_on": [],
            "state": "RESULT_READY",
            "ownership": {"write": ["src/a.py"], "forbidden": []},
            "authority_ceiling": "bounded-source-write",
            "write_scope_ceiling": ["src/a.py"],
            "done_when": "tests pass",
            "accepted_result_ref": None,
            "accepted_execution_id": None,
            "accepted_control_epoch": None,
        }
    ]
    payload["executions"] = [
        {
            "execution_id": "exec-1",
            "unit_id": "U1",
            "team_plan_revision": None,
            "attempt_no": 1,
            "profile_id": "worker",
            "agent_id": "agent-1",
            "native_task_name": "sd_u1_a1",
            "model": "gpt-5.6-luna",
            "effort": "max",
            "granted_authority": "bounded-source-write",
            "granted_write_scope": ["src/a.py"],
            "workspace_id": "canonical",
            "lifecycle": "COMPLETED",
            "control_epoch": 0,
            "followup_count": 0,
            "failure_origin": "none",
            "blocker": "none",
            "quarantine_reason": None,
        }
    ]
    payload["writer_lease"] = {
        "lease_id": "lease-1",
        "lease_epoch": 1,
        "workspace_id": "canonical",
        "unit_id": "U1",
        "owner_kind": "execution",
        "owner_id": "exec-1",
        "state": "HELD",
    }
    payload["accounting_refs"].append(
        {
            "ref": "host-observation:exec-1:0:1:COMPLETED:observe-1",
            "kind": "host_observation",
            "source": "post_tool_use:list_agents",
            "execution_id": "exec-1",
            "control_epoch": 0,
            "lease_epoch": 1,
            "lifecycle": "COMPLETED",
            "turn_id": "turn-observe",
            "tool_use_id": "observe-1",
            "agent_name": "/root/sd_u1_a1",
        }
    )
    state_module.write_state(payload, temp_root=tmp_path)


def test_post_failure_rejects_result_with_host_supported_block(monkeypatch, capsys):
    guard = load_module("runtime_safety_guard_cli", GUARD)
    payload = {
        "hook_event_name": "PostToolUse",
        "session_id": "root-thread",
        "tool_name": "spawn_agent",
        "tool_use_id": "tool-1",
        "tool_input": {},
        "tool_response": {},
    }
    fake_stdin = io.TextIOWrapper(io.BytesIO(json.dumps(payload).encode()), encoding="utf-8")
    monkeypatch.setattr(guard.sys, "stdin", fake_stdin)
    monkeypatch.setattr(
        guard,
        "evaluate_hook",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    guard.main()
    rendered = json.loads(capsys.readouterr().out)
    assert rendered["decision"] == "block"
    assert "continue" not in rendered
    assert "boom" not in json.dumps(rendered)


def test_managed_lifecycle_pre_consumes_authoritative_capacity_truth(tmp_path: Path):
    state = load_module("runtime_safety_state_capacity", STATE)
    control = load_module("runtime_safety_control_capacity", CONTROL)
    guard = load_module("runtime_safety_guard_capacity", GUARD)
    managed = load_module("runtime_safety_managed_capacity", MANAGED)
    _v4_state(state, tmp_path)
    current = state.load_state("root-thread", temp_root=tmp_path)
    assert current is not None
    tool_input = managed.expected_spawn_input_for_execution(current, execution_id="exec-1")
    control.prepare_control(
        "root-thread",
        control_id="spawn:exec-1",
        execution_id="exec-1",
        operation="SPAWN",
        tool_input=tool_input,
        temp_root=tmp_path,
    )
    payload = {
        "hook_event_name": "PreToolUse",
        "session_id": "root-thread",
        "turn_id": "turn-spawn",
        "tool_name": "spawn_agent",
        "tool_use_id": "tool-spawn",
        "tool_input": tool_input,
    }
    assert guard.evaluate_pre_tool_use(payload, temp_root=tmp_path) is None
    latest = state.load_state("root-thread", temp_root=tmp_path)
    assert latest is not None
    assert not any(
        event.get("kind") == state.HOST_CAPACITY_OBSERVATION_KIND
        for event in latest["accounting_refs"]
    )


def test_writer_settlement_rejects_partial_observation_until_receipt_exists(tmp_path: Path):
    state = load_module("runtime_safety_state_receipt", STATE)
    writer = load_module("runtime_safety_writer_receipt", WRITER)
    _settled_writer_state(state, tmp_path)

    with pytest.raises(writer.WriterLeaseError, match="observation receipt"):
        writer.release_settled_execution_writer(
            "root-thread",
            execution_id="exec-1",
            lease_id="lease-1",
            lease_epoch=1,
            temp_root=tmp_path,
        )

    def add_receipt(current: dict) -> None:
        current["accounting_refs"].append(
            {
                "ref": "host-observation-receipt:observe-1",
                "kind": "host_observation_receipt",
                "source": "post_tool_use:list_agents",
                "turn_id": "turn-observe",
                "tool_use_id": "observe-1",
                "response_digest": "b" * 64,
            }
        )

    state.mutate_state("root-thread", add_receipt, temp_root=tmp_path)
    released = writer.release_settled_execution_writer(
        "root-thread",
        execution_id="exec-1",
        lease_id="lease-1",
        lease_epoch=1,
        temp_root=tmp_path,
    )
    assert released["state"] == "RELEASED"


def test_writer_settlement_rejects_probabilistic_receipt_filter_match(tmp_path: Path):
    state = load_module("runtime_safety_state_filter", STATE)
    writer = load_module("runtime_safety_writer_filter", WRITER)
    _settled_writer_state(state, tmp_path)

    def add_filter_only(current: dict) -> None:
        bits = state._filter_add(0, "observe-1")
        current["accounting_refs"].append(
            state._filter_event(
                kind=state.OBSERVATION_RECEIPT_FILTER_KIND,
                ref=state.OBSERVATION_RECEIPT_FILTER_REF,
                bits=bits,
                count=1,
            )
        )

    state.mutate_state("root-thread", add_filter_only, temp_root=tmp_path)
    current = state.load_state("root-thread", temp_root=tmp_path)
    assert current is not None
    assert state.accounting_filter_contains(
        current,
        kind=state.OBSERVATION_RECEIPT_FILTER_KIND,
        value="observe-1",
    )

    with pytest.raises(writer.WriterLeaseError, match="observation receipt"):
        writer.release_settled_execution_writer(
            "root-thread",
            execution_id="exec-1",
            lease_id="lease-1",
            lease_epoch=1,
            temp_root=tmp_path,
        )
