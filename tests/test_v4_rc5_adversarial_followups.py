from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
STATE = SCRIPTS / "dispatch_state_v4.py"
CONTROL = SCRIPTS / "dispatch_control_v4.py"
GUARD = SCRIPTS / "orchestration_guard.py"
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


def _work_unit(unit_id: str, *, writable: bool = False) -> dict:
    path = f"src/{unit_id.lower()}.py"
    return {
        "unit_id": unit_id,
        "intent": "implement" if writable else "inspect",
        "goal": "bounded write" if writable else "bounded read",
        "output": "patch" if writable else "facts",
        "depends_on": [],
        "state": "RESULT_READY" if writable else "EXECUTING",
        "ownership": {"write": [path] if writable else [], "forbidden": []},
        "authority_ceiling": "bounded-source-write" if writable else "none",
        "write_scope_ceiling": [path] if writable else [],
        "done_when": "tests pass" if writable else "Main verifies facts",
        "accepted_result_ref": None,
        "accepted_execution_id": None,
        "accepted_control_epoch": None,
    }


def _execution(unit_id: str, execution_id: str, task_name: str, *, writable: bool = False) -> dict:
    path = f"src/{unit_id.lower()}.py"
    return {
        "execution_id": execution_id,
        "unit_id": unit_id,
        "team_plan_revision": None,
        "attempt_no": 1,
        "profile_id": "worker" if writable else "reader",
        "agent_id": "agent-1" if writable else None,
        "native_task_name": task_name,
        "model": "gpt-5.6-luna",
        "effort": "max",
        "granted_authority": "bounded-source-write" if writable else "none",
        "granted_write_scope": [path] if writable else [],
        "workspace_id": "canonical",
        "lifecycle": "COMPLETED" if writable else "SPAWN_PENDING",
        "control_epoch": 0,
        "followup_count": 0,
        "failure_origin": "none",
        "blocker": "none",
        "quarantine_reason": None,
    }


def _capacity_event(state_module) -> dict:
    return {
        "ref": "host-capacity-observation:observe-capacity",
        "kind": state_module.HOST_CAPACITY_OBSERVATION_KIND,
        "source": "post_tool_use:list_agents",
        "turn_id": "turn-capacity",
        "tool_use_id": "observe-capacity",
        "resident_children": 0,
        "settled_children": 0,
        "active_children": 0,
        "managed_resident_children": 0,
        "unmanaged_resident_children": 0,
        "response_digest": "a" * 64,
    }


def test_one_capacity_observation_cannot_authorize_second_fresh_spawn(tmp_path: Path):
    state = load_module("rc5_followup_state_capacity", STATE)
    control = load_module("rc5_followup_control_capacity", CONTROL)
    guard = load_module("rc5_followup_guard_capacity", GUARD)
    managed = load_module("rc5_followup_managed_capacity", MANAGED)

    payload = state.new_state(thread_id="root-thread")
    payload["work_units"] = [_work_unit("U1"), _work_unit("U2")]
    payload["executions"] = [
        _execution("U1", "exec-1", "sd_u1_a1"),
        _execution("U2", "exec-2", "sd_u2_a1"),
    ]
    payload["accounting_refs"].append(_capacity_event(state))
    state.write_state(payload, temp_root=tmp_path)

    current = state.load_state("root-thread", temp_root=tmp_path)
    assert current is not None
    first_input = managed.expected_spawn_input_for_execution(current, execution_id="exec-1")
    second_input = managed.expected_spawn_input_for_execution(current, execution_id="exec-2")
    control.prepare_control(
        "root-thread",
        control_id="spawn:exec-1",
        execution_id="exec-1",
        operation="SPAWN",
        tool_input=first_input,
        temp_root=tmp_path,
    )
    control.prepare_control(
        "root-thread",
        control_id="spawn:exec-2",
        execution_id="exec-2",
        operation="SPAWN",
        tool_input=second_input,
        temp_root=tmp_path,
    )

    first_pre = {
        "hook_event_name": "PreToolUse",
        "session_id": "root-thread",
        "turn_id": "turn-spawn-1",
        "tool_name": "spawn_agent",
        "tool_use_id": "tool-spawn-1",
        "tool_input": first_input,
    }
    second_pre = {
        "hook_event_name": "PreToolUse",
        "session_id": "root-thread",
        "turn_id": "turn-spawn-2",
        "tool_name": "spawn_agent",
        "tool_use_id": "tool-spawn-2",
        "tool_input": second_input,
    }

    assert guard.evaluate_pre_tool_use(first_pre, temp_root=tmp_path) is None
    blocked = guard.evaluate_pre_tool_use(second_pre, temp_root=tmp_path)
    assert blocked is not None
    assert blocked["decision"] == "block"
    assert "capacity" in blocked["reason"].lower()

    latest = state.load_state("root-thread", temp_root=tmp_path)
    assert latest is not None
    second_control = next(item for item in latest["pending_controls"] if item["control_id"] == "spawn:exec-2")
    assert second_control["state"] == "PREPARED"
    assert second_control["tool_use_id"] is None


def test_v4_contracts_state_scheduler_two_three_ceiling_without_unbounded_override():
    required = "V4 execution remains bounded by the scheduler's initial two-child and product three-child ceilings"
    for relative in ("contracts/guardrails.md", "contracts/routing.md"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert required in text, relative
    guardrails = (ROOT / "contracts" / "guardrails.md").read_text(encoding="utf-8")
    assert "use as many simultaneously useful children as the task genuinely supports and the native runtime allows" not in guardrails


def test_active_writer_exact_settlement_receipt_survives_history_compaction(tmp_path: Path):
    state = load_module("rc5_followup_state_receipt", STATE)
    writer = load_module("rc5_followup_writer_receipt", WRITER)

    payload = state.new_state(thread_id="root-thread")
    payload["work_units"] = [_work_unit("U1", writable=True)]
    payload["executions"] = [_execution("U1", "exec-1", "sd_u1_a1", writable=True)]
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
            "turn_id": "turn-observe-1",
            "tool_use_id": "observe-1",
            "agent_name": "/root/sd_u1_a1",
        }
    )
    state.write_state(payload, temp_root=tmp_path)

    def add_exact_receipt(current: dict) -> None:
        current["accounting_refs"].append(
            {
                "ref": "host-observation-receipt:observe-1",
                "kind": "host_observation_receipt",
                "turn_id": "turn-observe-1",
                "tool_use_id": "observe-1",
                "response_digest": "b" * 64,
            }
        )

    state.mutate_state("root-thread", add_exact_receipt, temp_root=tmp_path)

    def add_newer_receipts(current: dict) -> None:
        for index in range(2, 67):
            current["accounting_refs"].append(
                {
                    "ref": f"host-observation-receipt:observe-{index}",
                    "kind": "host_observation_receipt",
                    "turn_id": f"turn-observe-{index}",
                    "tool_use_id": f"observe-{index}",
                    "response_digest": f"{index:064x}",
                }
            )

    state.mutate_state("root-thread", add_newer_receipts, temp_root=tmp_path)
    compacted = state.load_state("root-thread", temp_root=tmp_path)
    assert compacted is not None
    assert any(
        event.get("kind") == "host_observation_receipt" and event.get("tool_use_id") == "observe-1"
        for event in compacted["accounting_refs"]
    )

    released = writer.release_settled_execution_writer(
        "root-thread",
        execution_id="exec-1",
        lease_id="lease-1",
        lease_epoch=1,
        temp_root=tmp_path,
    )
    assert released["state"] == "RELEASED"
