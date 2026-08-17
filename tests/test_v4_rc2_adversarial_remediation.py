from __future__ import annotations

import importlib.util
import json
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


def work_unit(
    unit_id: str,
    *,
    state_name: str = "READY",
    authority: str = "none",
    path: str | None = None,
) -> dict:
    scope = [] if authority == "none" else [path or f"src/{unit_id.lower()}.py"]
    return {
        "unit_id": unit_id,
        "intent": "inspect" if authority == "none" else "implement",
        "goal": f"complete {unit_id}",
        "output": "verified result",
        "depends_on": [],
        "state": state_name,
        "ownership": {"write": scope, "forbidden": []},
        "authority_ceiling": authority,
        "write_scope_ceiling": scope,
        "done_when": "Main verifies the result",
        "accepted_result_ref": None,
        "accepted_execution_id": None,
        "accepted_control_epoch": None,
    }


def execution(
    unit_id: str,
    *,
    execution_id: str,
    lifecycle: str,
    authority: str = "none",
    task_name: str | None = None,
) -> dict:
    writable = authority != "none"
    return {
        "execution_id": execution_id,
        "unit_id": unit_id,
        "team_plan_revision": 1,
        "attempt_no": 1,
        "profile_id": "worker" if writable else "reader",
        "agent_id": None,
        "native_task_name": task_name or f"sd-{unit_id.lower()}-a1",
        "model": "gpt-5.6-luna",
        "effort": "max",
        "granted_authority": authority,
        "granted_write_scope": [f"src/{unit_id.lower()}.py"] if writable else [],
        "workspace_id": "canonical",
        "lifecycle": lifecycle,
        "control_epoch": 0,
        "followup_count": 0,
        "failure_origin": "none",
        "blocker": "none",
        "quarantine_reason": None,
    }


def host_snapshot(capacity: int) -> dict:
    return {
        "execution_ready": True,
        "missing": [],
        "max_spawned_threads": capacity,
    }


def test_direct_posttool_ack_atomically_promotes_writer_lease(tmp_path: Path):
    state = load_module("rc2_state_ack", "dispatch_state_v4.py")
    control = load_module("rc2_control_ack", "dispatch_control_v4.py")
    payload = state.new_state(thread_id="thread-rc2")
    payload["team_plan_revision"] = 1
    payload["work_units"] = [
        work_unit(
            "U1",
            state_name="EXECUTING",
            authority="bounded-source-write",
            path="src/u1.py",
        )
    ]
    payload["executions"] = [
        execution(
            "U1",
            execution_id="exec-1",
            lifecycle="SPAWN_PENDING",
            authority="bounded-source-write",
        )
    ]
    payload["writer_lease"] = {
        "lease_id": "lease-1",
        "lease_epoch": 1,
        "workspace_id": "canonical",
        "unit_id": "U1",
        "owner_kind": "execution",
        "owner_id": "exec-1",
        "state": "RESERVED",
    }
    state.write_state(payload, temp_root=tmp_path)
    tool_input = {
        "task_name": "sd-u1-a1",
        "message": "bounded write",
        "agent_type": "subagents_dispatch_worker",
        "fork_turns": "none",
    }
    control.prepare_control(
        "thread-rc2",
        control_id="spawn:exec-1",
        execution_id="exec-1",
        operation="SPAWN",
        tool_input=tool_input,
        writer_effect="RESERVE",
        temp_root=tmp_path,
    )
    control.consume_prepared_control(
        "thread-rc2",
        tool_name="spawn_agent",
        tool_input=tool_input,
        tool_use_id="tool-spawn-1",
        temp_root=tmp_path,
    )
    before = state.load_state("thread-rc2", temp_root=tmp_path)
    assert before is not None
    before_revision = before["state_revision"]
    assert before["writer_lease"]["state"] == "RESERVED"

    ack = control.acknowledge_control(
        "thread-rc2",
        tool_name="spawn_agent",
        tool_input=tool_input,
        tool_response={"task_name": "sd-u1-a1"},
        tool_use_id="tool-spawn-1",
        temp_root=tmp_path,
    )
    after = state.load_state("thread-rc2", temp_root=tmp_path)
    assert after is not None
    assert ack["state"] == "ACKED"
    assert after["writer_lease"]["state"] == "HELD"
    assert after["pending_controls"] == []
    assert after["state_revision"] == before_revision + 1


def test_completed_open_thread_still_consumes_host_capacity_until_closed():
    state = load_module("rc2_state_capacity", "dispatch_state_v4.py")
    scheduler = load_module("rc2_scheduler_capacity", "scheduler_v4.py")
    payload = state.new_state(thread_id="thread-capacity")
    payload["team_plan_revision"] = 1
    payload["work_units"] = [
        work_unit("U0", state_name="RESULT_READY"),
        work_unit("U1"),
        work_unit("U2"),
    ]
    payload["executions"] = [
        execution("U0", execution_id="exec-old", lifecycle="COMPLETED")
    ]
    state.validate_state_payload(payload)

    occupied = scheduler.scheduler_decision(
        payload,
        capability_snapshot=host_snapshot(2),
        wakeup_reason="AGENT_COMPLETED",
    )
    assert occupied["occupied_open_threads"] == 1
    assert occupied["launch_budget"] == 1
    assert len(occupied["actions"]) == 1

    payload["executions"][0]["lifecycle"] = "CLOSED"
    state.validate_state_payload(payload)
    released = scheduler.scheduler_decision(
        payload,
        capability_snapshot=host_snapshot(2),
        wakeup_reason="CAPACITY_RELEASED",
    )
    assert released["occupied_open_threads"] == 0
    assert released["launch_budget"] == 2
    assert len(released["actions"]) == 2


def test_intermediate_writer_states_are_recoverable_without_widening_authority(tmp_path: Path):
    state = load_module("rc2_state_crash", "dispatch_state_v4.py")
    graph = load_module("rc2_graph_crash", "work_graph_v4.py")
    control = load_module("rc2_control_crash", "dispatch_control_v4.py")
    lifecycle = load_module("rc2_lifecycle_crash", "execution_lifecycle_v4.py")
    writer = load_module("rc2_writer_crash", "writer_lease_v4.py")

    payload = state.new_state(thread_id="thread-crash")
    state.write_state(payload, temp_root=tmp_path)
    unit = graph.make_work_unit(
        unit_id="U1",
        intent="implement",
        goal="bounded write",
        output="patch",
        ownership_write=["src/u1.py"],
        authority_ceiling="bounded-source-write",
        write_scope_ceiling=["src/u1.py"],
        done_when="tests pass",
    )
    graph.install_work_graph(
        "thread-crash", team_plan_revision=1, units=[unit], temp_root=tmp_path
    )
    lifecycle.allocate_execution(
        "thread-crash",
        unit_id="U1",
        execution_id="exec-1",
        native_task_name="sd-u1-a1",
        profile_id="worker",
        granted_authority="bounded-source-write",
        granted_write_scope=["src/u1.py"],
        writer_lease_id="lease-1",
        temp_root=tmp_path,
    )

    spawn = {
        "task_name": "sd-u1-a1",
        "message": "bounded write",
        "agent_type": "subagents_dispatch_worker",
        "fork_turns": "none",
    }
    lifecycle.prepare_spawn(
        "thread-crash",
        execution_id="exec-1",
        control_id="spawn:exec-1",
        tool_input=spawn,
        temp_root=tmp_path,
    )
    control.consume_prepared_control(
        "thread-crash",
        tool_name="spawn_agent",
        tool_input=spawn,
        tool_use_id="tool-spawn",
        temp_root=tmp_path,
    )
    lifecycle.acknowledge_lifecycle_control(
        "thread-crash",
        tool_name="spawn_agent",
        tool_input=spawn,
        tool_response={"task_name": "sd-u1-a1"},
        tool_use_id="tool-spawn",
        temp_root=tmp_path,
    )
    basis = lifecycle.fresh_observation_basis(
        "thread-crash", execution_id="exec-1", temp_root=tmp_path
    )
    lifecycle.persist_host_observation(
        "thread-crash",
        basis=basis,
        host_state="running",
        agent_id="agent-1",
        temp_root=tmp_path,
    )

    current = state.load_state("thread-crash", temp_root=tmp_path)
    assert current is not None
    lease = current["writer_lease"]
    writer.begin_revoke_execution_writer(
        "thread-crash",
        execution_id="exec-1",
        lease_id=lease["lease_id"],
        lease_epoch=lease["lease_epoch"],
        temp_root=tmp_path,
    )
    intermediate = state.load_state("thread-crash", temp_root=tmp_path)
    assert intermediate is not None
    assert intermediate["writer_lease"]["state"] == "REVOKING"
    assert intermediate["pending_controls"] == []

    interrupt = {"target": "sd-u1-a1"}
    recovered = lifecycle.prepare_interrupt(
        "thread-crash",
        execution_id="exec-1",
        tool_input=interrupt,
        temp_root=tmp_path,
    )
    assert recovered["operation"] == "INTERRUPT"
    assert recovered["writer_effect"] == "REVOKE"
    current = state.load_state("thread-crash", temp_root=tmp_path)
    assert current is not None
    assert current["writer_lease"]["state"] == "REVOKING"
    assert len(current["pending_controls"]) == 1


def test_public_architecture_and_orchestrate_bind_current_v4_contracts():
    architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    skill = (ROOT / "skills" / "orchestrate" / "SKILL.md").read_text(encoding="utf-8")
    assert "Orchestrate\nDoctor" in architecture
    assert "initial managed children <= 2" in architecture
    assert "normal managed children <= 3" in architecture
    assert "six explicit Skills" not in architecture.lower()
    assert "../../contracts/final-review.md" in skill
    assert "../../scripts/review-artifact.py" in skill
    assert "valid `ship` verdict" in skill
    assert "Any deliverable mutation after review invalidates" in skill


def test_host_smoke_requires_trust_payload_capacity_and_writer_ack_probes():
    smoke = json.loads((ROOT / "docs" / "v4" / "host-smoke.json").read_text(encoding="utf-8"))
    probes = {item["id"]: item for item in smoke["required_probes"]}
    assert set(probes) == {f"H{number:02d}" for number in range(11)}
    assert "exact active lifecycle Hook definition hash captured" in probes["H00"]["requires"]
    assert any("canonical digests match" in item for item in probes["H08"]["requires"])
    assert any("closing the child releases capacity" in item for item in probes["H09"]["requires"])
    assert any("WriterLease is HELD" in item for item in probes["H10"]["requires"])
