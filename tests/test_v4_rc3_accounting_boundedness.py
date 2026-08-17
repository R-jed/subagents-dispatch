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


def unit() -> dict:
    return {
        "unit_id": "U1",
        "intent": "inspect",
        "goal": "bounded accounting",
        "output": "facts",
        "depends_on": [],
        "state": "EXECUTING",
        "ownership": {"write": [], "forbidden": []},
        "authority_ceiling": "none",
        "write_scope_ceiling": [],
        "done_when": "facts verified",
        "accepted_result_ref": None,
        "accepted_execution_id": None,
        "accepted_control_epoch": None,
    }


def execution() -> dict:
    return {
        "execution_id": "exec-1",
        "unit_id": "U1",
        "team_plan_revision": 1,
        "attempt_no": 1,
        "profile_id": "reader",
        "agent_id": "agent-1",
        "native_task_name": "sd-u1-a1",
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


def install(state, tmp_path: Path) -> None:
    payload = state.new_state(thread_id="thread-bounded")
    payload["team_plan_revision"] = 1
    payload["work_units"] = [unit()]
    payload["executions"] = [execution()]
    state.write_state(payload, temp_root=tmp_path)


def test_lifecycle_invocation_identity_includes_turn_id(tmp_path: Path):
    state = load_module("bounded_state_identity", "dispatch_state_v4.py")
    control = load_module("bounded_control_identity", "dispatch_control_v4.py")
    install(state, tmp_path)
    tool_input = {"target": "sd-u1-a1", "message": "same correction"}

    control.prepare_control(
        "thread-bounded",
        control_id="c1",
        execution_id="exec-1",
        operation="FOLLOWUP",
        tool_input=tool_input,
        temp_root=tmp_path,
    )
    control.consume_prepared_control(
        "thread-bounded",
        tool_name="followup_task",
        tool_input=tool_input,
        turn_id="turn-1",
        tool_use_id="T",
        temp_root=tmp_path,
    )
    first = control.acknowledge_control(
        "thread-bounded",
        tool_name="followup_task",
        tool_input=tool_input,
        tool_response={},
        turn_id="turn-1",
        tool_use_id="T",
        temp_root=tmp_path,
    )
    assert first["idempotent"] is False

    control.prepare_control(
        "thread-bounded",
        control_id="c2",
        execution_id="exec-1",
        operation="FOLLOWUP",
        tool_input=tool_input,
        temp_root=tmp_path,
    )
    control.consume_prepared_control(
        "thread-bounded",
        tool_name="followup_task",
        tool_input=tool_input,
        turn_id="turn-2",
        tool_use_id="T",
        temp_root=tmp_path,
    )

    delayed = control.acknowledge_control(
        "thread-bounded",
        tool_name="followup_task",
        tool_input=tool_input,
        tool_response={},
        turn_id="turn-1",
        tool_use_id="T",
        temp_root=tmp_path,
    )
    assert delayed["idempotent"] is True
    current = state.load_state("thread-bounded", temp_root=tmp_path)
    assert current is not None
    c2 = next(item for item in current["pending_controls"] if item["control_id"] == "c2")
    assert c2["state"] == "IN_FLIGHT"
    assert c2["turn_id"] == "turn-2"


def test_accounting_history_is_compacted_before_state_limit(tmp_path: Path):
    state = load_module("bounded_state_compaction", "dispatch_state_v4.py")
    install(state, tmp_path)

    def add_history(current: dict) -> None:
        for index in range(400):
            current["accounting_refs"].append(
                {
                    "ref": f"control-ack:c{index}:tool-{index}",
                    "kind": "control_ack",
                    "control_id": f"c{index}",
                    "execution_id": "exec-1",
                    "control_epoch": index,
                    "turn_id": f"turn-{index}",
                    "tool_use_id": f"tool-{index}",
                    "tool_name": "followup_task",
                    "payload_digest": "a" * 64,
                    "target": "sd-u1-a1",
                }
            )
            current["accounting_refs"].append(
                {
                    "ref": f"host-observation-receipt:observe-{index}",
                    "kind": "host_observation_receipt",
                    "turn_id": f"observe-turn-{index}",
                    "tool_use_id": f"observe-{index}",
                    "response_digest": "b" * 64,
                }
            )
            current["accounting_refs"].append(
                {
                    "ref": f"host-observation:exec-1:0:none:COMPLETED:observe-{index}",
                    "kind": "host_observation",
                    "source": "post_tool_use:list_agents",
                    "execution_id": "exec-1",
                    "control_epoch": 0,
                    "lease_epoch": None,
                    "lifecycle": "COMPLETED",
                    "turn_id": f"observe-turn-{index}",
                    "tool_use_id": f"observe-{index}",
                    "agent_name": "/root/sd-u1-a1",
                }
            )

    updated = state.mutate_state("thread-bounded", add_history, temp_root=tmp_path)
    assert len(updated["accounting_refs"]) <= 160
    path = state.state_path("thread-bounded", temp_root=tmp_path)
    assert path.stat().st_size < state.DEFAULT_MAX_BYTES
    observations = [
        event
        for event in updated["accounting_refs"]
        if event.get("kind") == "host_observation"
    ]
    assert len(observations) == 1
    assert observations[0]["lifecycle"] == "COMPLETED"
