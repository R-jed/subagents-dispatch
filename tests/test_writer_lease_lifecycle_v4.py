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


def install_graph(state, graph, tmp_path: Path, *, two_writers: bool = False):
    payload = state.new_state(thread_id="thread-p5")
    state.write_state(payload, temp_root=tmp_path)
    units = [
        graph.make_work_unit(
            unit_id="U1",
            intent="implement",
            goal="change owned source",
            output="patch",
            ownership_write=["src/a.py"],
            authority_ceiling="bounded-source-write",
            write_scope_ceiling=["src/a.py"],
            done_when="tests pass",
        )
    ]
    if two_writers:
        units.append(
            graph.make_work_unit(
                unit_id="U2",
                intent="implement",
                goal="change second source",
                output="patch",
                ownership_write=["src/b.py"],
                authority_ceiling="bounded-source-write",
                write_scope_ceiling=["src/b.py"],
                done_when="tests pass",
            )
        )
    graph.install_work_graph(
        "thread-p5",
        team_plan_revision=1,
        units=units,
        temp_root=tmp_path,
    )


def allocate_writer(
    lifecycle,
    tmp_path: Path,
    *,
    unit_id: str = "U1",
    execution_id: str = "exec-1",
    lease_id: str = "lease-1",
):
    scope = ["src/a.py"] if unit_id == "U1" else ["src/b.py"]
    return lifecycle.allocate_execution(
        "thread-p5",
        unit_id=unit_id,
        execution_id=execution_id,
        native_task_name=f"sd-{unit_id.lower()}-a1",
        profile_id="worker",
        granted_authority="bounded-source-write",
        granted_write_scope=scope,
        writer_lease_id=lease_id,
        temp_root=tmp_path,
    )


def activate_writer(state, control, lifecycle, tmp_path: Path, *, execution_id: str = "exec-1"):
    current = state.load_state("thread-p5", temp_root=tmp_path)
    assert current is not None
    execution = next(item for item in current["executions"] if item["execution_id"] == execution_id)
    tool_input = lifecycle.build_managed_spawn_tool_input(
        "thread-p5", execution_id=execution_id, temp_root=tmp_path
    )
    prepared = lifecycle.prepare_spawn(
        "thread-p5",
        execution_id=execution_id,
        control_id=f"spawn:{execution_id}",
        tool_input=tool_input,
        temp_root=tmp_path,
    )
    control.consume_prepared_control(
        "thread-p5",
        tool_name="spawn_agent",
        tool_input=tool_input,
        tool_use_id=f"tool-spawn-{execution_id}",
        temp_root=tmp_path,
    )
    lifecycle.acknowledge_lifecycle_control(
        "thread-p5",
        tool_name="spawn_agent",
        tool_input=tool_input,
        tool_response={"task_name": execution["native_task_name"]},
        tool_use_id=f"tool-spawn-{execution_id}",
        temp_root=tmp_path,
    )
    return prepared


def _host_status(host_state: str):
    if host_state == "completed":
        return {"completed": None}
    if host_state == "errored":
        return {"errored": "test failure"}
    return host_state


def _observation_payloads(state, tmp_path: Path, *, execution_id: str, host_state: str, label: str):
    current = state.load_state("thread-p5", temp_root=tmp_path)
    assert current is not None
    execution = next(item for item in current["executions"] if item["execution_id"] == execution_id)
    tool_use_id = f"observe-{label}-{current['state_revision']}"
    common = {
        "session_id": "thread-p5",
        "turn_id": f"turn-{label}",
        "tool_name": "list_agents",
        "tool_use_id": tool_use_id,
    }
    pre = {**common, "hook_event_name": "PreToolUse", "tool_input": {}}
    post = {
        **common,
        "hook_event_name": "PostToolUse",
        "tool_input": {},
        "tool_response": [
            {
                "agent_name": f"/root/{execution['native_task_name']}",
                "status": _host_status(host_state),
            }
        ],
    }
    return pre, post


def observe(lifecycle, tmp_path: Path, *, execution_id: str, host_state: str):
    state = lifecycle.state
    guard = load_module(
        f"p5_guard_{execution_id}_{host_state}",
        "orchestration_guard.py",
    )
    pre, post = _observation_payloads(
        state,
        tmp_path,
        execution_id=execution_id,
        host_state=host_state,
        label=f"{execution_id}-{host_state}",
    )
    assert guard.evaluate_pre_tool_use(pre, temp_root=tmp_path) is None
    assert guard.evaluate_post_tool_use(post, temp_root=tmp_path) is None
    current = state.load_state("thread-p5", temp_root=tmp_path)
    assert current is not None
    execution = next(item for item in current["executions"] if item["execution_id"] == execution_id)
    proof = any(
        event.get("kind") == "host_observation"
        and event.get("tool_use_id") == post["tool_use_id"]
        for event in current["accounting_refs"]
    )
    return {
        "reconcile_status": "applied" if proof else "stale",
        "lifecycle": execution["lifecycle"],
        "state": current,
    }


def test_fresh_writer_reserves_atomically_and_second_writer_blocks(tmp_path: Path):
    state = load_module("p5_state_reserve", "dispatch_state_v4.py")
    graph = load_module("p5_graph_reserve", "work_graph_v4.py")
    lifecycle = load_module("p5_lifecycle_reserve", "execution_lifecycle_v4.py")
    install_graph(state, graph, tmp_path, two_writers=True)

    first = allocate_writer(lifecycle, tmp_path)
    assert first["writer_lease"]["state"] == "RESERVED"
    assert first["writer_lease"]["owner_id"] == "exec-1"

    with pytest.raises(lifecycle.ExecutionLifecycleError, match="managed writer"):
        allocate_writer(
            lifecycle,
            tmp_path,
            unit_id="U2",
            execution_id="exec-2",
            lease_id="lease-2",
        )


def test_spawn_ack_promotes_reserved_writer_to_held(tmp_path: Path):
    state = load_module("p5_state_ack", "dispatch_state_v4.py")
    graph = load_module("p5_graph_ack", "work_graph_v4.py")
    control = load_module("p5_control_ack", "dispatch_control_v4.py")
    lifecycle = load_module("p5_lifecycle_ack", "execution_lifecycle_v4.py")
    install_graph(state, graph, tmp_path)
    allocate_writer(lifecycle, tmp_path)
    activate_writer(state, control, lifecycle, tmp_path)

    current = state.load_state("thread-p5", temp_root=tmp_path)
    assert current is not None
    assert current["writer_lease"]["state"] == "HELD"
    assert any(
        event.get("ref") == "control-ack:spawn:exec-1:tool-spawn-exec-1"
        and event.get("control_id") == "spawn:exec-1"
        for event in current["accounting_refs"]
    )


def test_interrupt_ack_alone_never_releases_or_transfers_writer(tmp_path: Path):
    state = load_module("p5_state_interrupt", "dispatch_state_v4.py")
    graph = load_module("p5_graph_interrupt", "work_graph_v4.py")
    control = load_module("p5_control_interrupt", "dispatch_control_v4.py")
    lifecycle = load_module("p5_lifecycle_interrupt", "execution_lifecycle_v4.py")
    writer = lifecycle.writer
    install_graph(state, graph, tmp_path)
    allocate_writer(lifecycle, tmp_path)
    activate_writer(state, control, lifecycle, tmp_path)
    observe(lifecycle, tmp_path, execution_id="exec-1", host_state="running")

    interrupt_input = {"target": "sd-u1-a1"}
    prepared = lifecycle.prepare_interrupt(
        "thread-p5",
        execution_id="exec-1",
        tool_input=interrupt_input,
        temp_root=tmp_path,
    )
    control.consume_prepared_control(
        "thread-p5",
        tool_name="interrupt_agent",
        tool_input=interrupt_input,
        tool_use_id="tool-interrupt-1",
        temp_root=tmp_path,
    )
    lifecycle.acknowledge_lifecycle_control(
        "thread-p5",
        tool_name="interrupt_agent",
        tool_input=interrupt_input,
        tool_response={},
        tool_use_id="tool-interrupt-1",
        temp_root=tmp_path,
    )
    assert prepared["writer_effect"] == "REVOKE"
    current = state.load_state("thread-p5", temp_root=tmp_path)
    assert current is not None
    lease = current["writer_lease"]
    assert lease["state"] == "REVOKING"

    with pytest.raises(writer.WriterLeaseError, match="not settled|observation"):
        lifecycle.takeover_to_main(
            "thread-p5",
            execution_id="exec-1",
            old_lease_id=lease["lease_id"],
            old_lease_epoch=lease["lease_epoch"],
            main_lease_id="lease-main",
            temp_root=tmp_path,
        )


def test_fresh_same_epoch_interrupted_observation_allows_atomic_takeover(tmp_path: Path):
    state = load_module("p5_state_takeover", "dispatch_state_v4.py")
    graph = load_module("p5_graph_takeover", "work_graph_v4.py")
    control = load_module("p5_control_takeover", "dispatch_control_v4.py")
    lifecycle = load_module("p5_lifecycle_takeover", "execution_lifecycle_v4.py")
    install_graph(state, graph, tmp_path)
    allocate_writer(lifecycle, tmp_path)
    activate_writer(state, control, lifecycle, tmp_path)
    observe(lifecycle, tmp_path, execution_id="exec-1", host_state="running")

    interrupt_input = {"target": "sd-u1-a1"}
    lifecycle.prepare_interrupt(
        "thread-p5", execution_id="exec-1", tool_input=interrupt_input, temp_root=tmp_path
    )
    control.consume_prepared_control(
        "thread-p5",
        tool_name="interrupt_agent",
        tool_input=interrupt_input,
        tool_use_id="tool-interrupt-1",
        temp_root=tmp_path,
    )
    lifecycle.acknowledge_lifecycle_control(
        "thread-p5",
        tool_name="interrupt_agent",
        tool_input=interrupt_input,
        tool_response={},
        tool_use_id="tool-interrupt-1",
        temp_root=tmp_path,
    )
    interrupted = observe(lifecycle, tmp_path, execution_id="exec-1", host_state="interrupted")
    assert interrupted["lifecycle"] == "INTERRUPTED"

    current = state.load_state("thread-p5", temp_root=tmp_path)
    assert current is not None
    old = current["writer_lease"]
    main = lifecycle.takeover_to_main(
        "thread-p5",
        execution_id="exec-1",
        old_lease_id=old["lease_id"],
        old_lease_epoch=old["lease_epoch"],
        main_lease_id="lease-main",
        temp_root=tmp_path,
    )
    assert main["owner_kind"] == "main"
    assert main["state"] == "HELD"
    assert main["lease_epoch"] == old["lease_epoch"] + 1


def test_takeover_stays_blocked_when_observation_post_lacks_pre_basis(tmp_path: Path):
    state = load_module("p5_state_guard", "dispatch_state_v4.py")
    graph = load_module("p5_graph_guard", "work_graph_v4.py")
    control = load_module("p5_control_guard", "dispatch_control_v4.py")
    lifecycle = load_module("p5_lifecycle_guard", "execution_lifecycle_v4.py")
    guard = load_module("p5_guard_unbound", "orchestration_guard.py")
    writer = lifecycle.writer
    install_graph(state, graph, tmp_path)
    allocate_writer(lifecycle, tmp_path)
    activate_writer(state, control, lifecycle, tmp_path)
    observe(lifecycle, tmp_path, execution_id="exec-1", host_state="running")
    interrupt_input = {"target": "sd-u1-a1"}
    lifecycle.prepare_interrupt(
        "thread-p5", execution_id="exec-1", tool_input=interrupt_input, temp_root=tmp_path
    )
    control.consume_prepared_control(
        "thread-p5",
        tool_name="interrupt_agent",
        tool_input=interrupt_input,
        tool_use_id="tool-interrupt-1",
        temp_root=tmp_path,
    )
    lifecycle.acknowledge_lifecycle_control(
        "thread-p5",
        tool_name="interrupt_agent",
        tool_input=interrupt_input,
        tool_response={},
        tool_use_id="tool-interrupt-1",
        temp_root=tmp_path,
    )
    current = state.load_state("thread-p5", temp_root=tmp_path)
    assert current is not None
    execution = current["executions"][0]
    post = {
        "session_id": "thread-p5",
        "turn_id": "turn-unbound",
        "hook_event_name": "PostToolUse",
        "tool_name": "list_agents",
        "tool_input": {},
        "tool_use_id": "observe-unbound",
        "tool_response": [
            {"agent_name": f"/root/{execution['native_task_name']}", "status": "interrupted"}
        ],
    }
    stopped = guard.evaluate_post_tool_use(post, temp_root=tmp_path)
    assert stopped is not None and stopped["continue"] is False
    current = state.load_state("thread-p5", temp_root=tmp_path)
    assert current is not None
    assert current["executions"][0]["lifecycle"] == "RUNNING"
    lease = current["writer_lease"]
    with pytest.raises(writer.WriterLeaseError, match="not settled|observation"):
        lifecycle.takeover_to_main(
            "thread-p5",
            execution_id="exec-1",
            old_lease_id=lease["lease_id"],
            old_lease_epoch=lease["lease_epoch"],
            main_lease_id="lease-main",
            temp_root=tmp_path,
        )


def test_naked_guard_boolean_is_not_settlement_api(tmp_path: Path):
    state = load_module("p5_state_guard_bool", "dispatch_state_v4.py")
    graph = load_module("p5_graph_guard_bool", "work_graph_v4.py")
    control = load_module("p5_control_guard_bool", "dispatch_control_v4.py")
    lifecycle = load_module("p5_lifecycle_guard_bool", "execution_lifecycle_v4.py")
    writer = lifecycle.writer
    install_graph(state, graph, tmp_path)
    allocate_writer(lifecycle, tmp_path)
    activate_writer(state, control, lifecycle, tmp_path)
    observe(lifecycle, tmp_path, execution_id="exec-1", host_state="completed")
    current = state.load_state("thread-p5", temp_root=tmp_path)
    assert current is not None
    lease = current["writer_lease"]

    with pytest.raises(TypeError, match="guard_coverage"):
        writer.release_settled_execution_writer(
            "thread-p5",
            execution_id="exec-1",
            lease_id=lease["lease_id"],
            lease_epoch=lease["lease_epoch"],
            guard_coverage=True,
            temp_root=tmp_path,
        )


def test_pre_captured_observation_cannot_settle_new_control_epoch(tmp_path: Path):
    state = load_module("p5_state_stale", "dispatch_state_v4.py")
    graph = load_module("p5_graph_stale", "work_graph_v4.py")
    control = load_module("p5_control_stale", "dispatch_control_v4.py")
    lifecycle = load_module("p5_lifecycle_stale", "execution_lifecycle_v4.py")
    guard = load_module("p5_guard_stale", "orchestration_guard.py")
    install_graph(state, graph, tmp_path)
    allocate_writer(lifecycle, tmp_path)
    activate_writer(state, control, lifecycle, tmp_path)
    observe(lifecycle, tmp_path, execution_id="exec-1", host_state="completed")

    pre, delayed_post = _observation_payloads(
        state,
        tmp_path,
        execution_id="exec-1",
        host_state="completed",
        label="stale-before-followup",
    )
    assert guard.evaluate_pre_tool_use(pre, temp_root=tmp_path) is None

    followup_input = {"target": "sd-u1-a1", "message": "focused correction"}
    lifecycle.prepare_same_child_followup(
        "thread-p5",
        execution_id="exec-1",
        tool_input=followup_input,
        temp_root=tmp_path,
    )
    control.consume_prepared_control(
        "thread-p5",
        tool_name="followup_task",
        tool_input=followup_input,
        tool_use_id="tool-followup-1",
        temp_root=tmp_path,
    )
    lifecycle.acknowledge_lifecycle_control(
        "thread-p5",
        tool_name="followup_task",
        tool_input=followup_input,
        tool_response={},
        tool_use_id="tool-followup-1",
        temp_root=tmp_path,
    )
    assert guard.evaluate_post_tool_use(delayed_post, temp_root=tmp_path) is None

    current = state.load_state("thread-p5", temp_root=tmp_path)
    assert current is not None
    current_execution = current["executions"][0]
    assert current_execution["control_epoch"] == 1
    assert current_execution["followup_count"] == 1
    assert not any(
        event.get("kind") == "host_observation"
        and event.get("tool_use_id") == delayed_post["tool_use_id"]
        and event.get("control_epoch") == 1
        for event in current["accounting_refs"]
    )


def test_delayed_running_observation_cannot_reopen_completed_same_epoch(tmp_path: Path):
    state = load_module("p5_state_monotonic", "dispatch_state_v4.py")
    graph = load_module("p5_graph_monotonic", "work_graph_v4.py")
    control = load_module("p5_control_monotonic", "dispatch_control_v4.py")
    lifecycle = load_module("p5_lifecycle_monotonic", "execution_lifecycle_v4.py")
    install_graph(state, graph, tmp_path)
    allocate_writer(lifecycle, tmp_path)
    activate_writer(state, control, lifecycle, tmp_path)
    completed = observe(lifecycle, tmp_path, execution_id="exec-1", host_state="completed")
    assert completed["lifecycle"] == "COMPLETED"

    delayed = observe(lifecycle, tmp_path, execution_id="exec-1", host_state="running")
    assert delayed["reconcile_status"] == "stale"
    current = state.load_state("thread-p5", temp_root=tmp_path)
    assert current is not None
    assert current["executions"][0]["lifecycle"] == "COMPLETED"
    assert current["work_units"][0]["state"] == "RESULT_READY"


def test_new_epoch_followup_can_reactivate_completed_execution(tmp_path: Path):
    state = load_module("p5_state_new_epoch", "dispatch_state_v4.py")
    graph = load_module("p5_graph_new_epoch", "work_graph_v4.py")
    control = load_module("p5_control_new_epoch", "dispatch_control_v4.py")
    lifecycle = load_module("p5_lifecycle_new_epoch", "execution_lifecycle_v4.py")
    install_graph(state, graph, tmp_path)
    allocate_writer(lifecycle, tmp_path)
    activate_writer(state, control, lifecycle, tmp_path)
    observe(lifecycle, tmp_path, execution_id="exec-1", host_state="completed")

    followup_input = {"target": "sd-u1-a1", "message": "focused correction"}
    lifecycle.prepare_same_child_followup(
        "thread-p5", execution_id="exec-1", tool_input=followup_input, temp_root=tmp_path
    )
    control.consume_prepared_control(
        "thread-p5",
        tool_name="followup_task",
        tool_input=followup_input,
        tool_use_id="tool-followup-reactivate",
        temp_root=tmp_path,
    )
    lifecycle.acknowledge_lifecycle_control(
        "thread-p5",
        tool_name="followup_task",
        tool_input=followup_input,
        tool_response={},
        tool_use_id="tool-followup-reactivate",
        temp_root=tmp_path,
    )
    running = observe(lifecycle, tmp_path, execution_id="exec-1", host_state="running")
    assert running["lifecycle"] == "RUNNING"
    assert running["state"]["executions"][0]["control_epoch"] == 1
    assert running["state"]["work_units"][0]["state"] == "EXECUTING"


def test_same_child_followup_does_not_create_fresh_attempt_and_is_bounded(tmp_path: Path):
    state = load_module("p5_state_followup", "dispatch_state_v4.py")
    graph = load_module("p5_graph_followup", "work_graph_v4.py")
    control = load_module("p5_control_followup", "dispatch_control_v4.py")
    lifecycle = load_module("p5_lifecycle_followup", "execution_lifecycle_v4.py")
    install_graph(state, graph, tmp_path)
    allocate_writer(lifecycle, tmp_path)
    activate_writer(state, control, lifecycle, tmp_path)
    observe(lifecycle, tmp_path, execution_id="exec-1", host_state="completed")

    followup_input = {"target": "sd-u1-a1", "message": "fix only the failing assertion"}
    lifecycle.prepare_same_child_followup(
        "thread-p5",
        execution_id="exec-1",
        tool_input=followup_input,
        temp_root=tmp_path,
    )
    current = state.load_state("thread-p5", temp_root=tmp_path)
    assert current is not None
    assert len(current["executions"]) == 1
    assert current["executions"][0]["attempt_no"] == 1
    assert current["executions"][0]["followup_count"] == 1

    with pytest.raises(lifecycle.ExecutionLifecycleError, match="budget"):
        lifecycle.prepare_same_child_followup(
            "thread-p5",
            execution_id="exec-1",
            tool_input=followup_input,
            temp_root=tmp_path,
        )


def test_unknown_writer_never_auto_releases(tmp_path: Path):
    state = load_module("p5_state_unknown", "dispatch_state_v4.py")
    graph = load_module("p5_graph_unknown", "work_graph_v4.py")
    lifecycle = load_module("p5_lifecycle_unknown", "execution_lifecycle_v4.py")
    writer = load_module("p5_writer_unknown", "writer_lease_v4.py")
    install_graph(state, graph, tmp_path)
    allocate_writer(lifecycle, tmp_path)
    current = state.load_state("thread-p5", temp_root=tmp_path)
    assert current is not None
    lease = current["writer_lease"]
    writer.mark_execution_writer_unknown(
        "thread-p5",
        execution_id="exec-1",
        lease_id=lease["lease_id"],
        lease_epoch=lease["lease_epoch"],
        temp_root=tmp_path,
    )
    with pytest.raises(writer.WriterLeaseError, match="UNKNOWN"):
        writer.release_settled_execution_writer(
            "thread-p5",
            execution_id="exec-1",
            lease_id=lease["lease_id"],
            lease_epoch=lease["lease_epoch"],
            temp_root=tmp_path,
        )


def test_stale_old_lease_release_cannot_clear_new_main_lease(tmp_path: Path):
    state = load_module("p5_state_epoch", "dispatch_state_v4.py")
    graph = load_module("p5_graph_epoch", "work_graph_v4.py")
    control = load_module("p5_control_epoch", "dispatch_control_v4.py")
    lifecycle = load_module("p5_lifecycle_epoch", "execution_lifecycle_v4.py")
    writer = load_module("p5_writer_epoch", "writer_lease_v4.py")
    install_graph(state, graph, tmp_path)
    allocate_writer(lifecycle, tmp_path)
    activate_writer(state, control, lifecycle, tmp_path)
    observe(lifecycle, tmp_path, execution_id="exec-1", host_state="completed")
    current = state.load_state("thread-p5", temp_root=tmp_path)
    assert current is not None
    old = dict(current["writer_lease"])
    writer.release_settled_execution_writer(
        "thread-p5",
        execution_id="exec-1",
        lease_id=old["lease_id"],
        lease_epoch=old["lease_epoch"],
        temp_root=tmp_path,
    )
    main = writer.acquire_main_writer(
        "thread-p5",
        unit_id="U1",
        lease_id="lease-main",
        temp_root=tmp_path,
    )
    assert main["lease_epoch"] == old["lease_epoch"] + 1

    with pytest.raises(writer.WriterLeaseError, match="stale lease identity"):
        writer.release_settled_execution_writer(
            "thread-p5",
            execution_id="exec-1",
            lease_id=old["lease_id"],
            lease_epoch=old["lease_epoch"],
            temp_root=tmp_path,
        )
    current = state.load_state("thread-p5", temp_root=tmp_path)
    assert current is not None
    assert current["writer_lease"]["lease_id"] == "lease-main"
    assert current["writer_lease"]["state"] == "HELD"
