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


def modules(label: str):
    state = load_module(f"phase3_state_{label}", "dispatch_state_v4.py")
    graph = load_module(f"phase3_graph_{label}", "work_graph_v4.py")
    lifecycle = load_module(f"phase3_lifecycle_{label}", "execution_lifecycle_v4.py")
    return state, graph, lifecycle


def read_unit(graph, unit_id: str, *, depends_on=()):
    return graph.make_work_unit(
        unit_id=unit_id,
        intent="inspect",
        goal=f"inspect {unit_id}",
        output=f"evidence {unit_id}",
        depends_on=depends_on,
        done_when=f"Main verifies {unit_id}",
    )


def write_unit(graph, unit_id: str):
    path = f"src/{unit_id.lower()}.py"
    return graph.make_work_unit(
        unit_id=unit_id,
        intent="implement",
        goal=f"implement {unit_id}",
        output=f"verified patch {unit_id}",
        ownership_write=[path],
        authority_ceiling="bounded-source-write",
        write_scope_ceiling=[path],
        done_when=f"Main verifies {unit_id}",
    )


def persist_status(lifecycle, thread_id: str, execution_id: str, tmp_path: Path, host_state: str):
    basis = lifecycle.fresh_observation_basis(
        thread_id, execution_id=execution_id, temp_root=tmp_path
    )
    return lifecycle.persist_host_observation(
        thread_id,
        basis=basis,
        host_state=host_state,
        agent_id=f"agent-{execution_id}",
        failure_origin="tool_failure",
        temp_root=tmp_path,
    )


def test_multi_unit_dependency_executes_without_teamplan_runtime_gate(tmp_path: Path):
    state, graph, lifecycle = modules("teamplan-free")
    thread_id = "phase3-teamplan-free"
    state.write_state(state.new_state(thread_id=thread_id), temp_root=tmp_path)
    installed = graph.install_work_graph(
        thread_id,
        team_plan_revision=1,
        units=[read_unit(graph, "U1"), read_unit(graph, "U2", depends_on=["U1"])],
        temp_root=tmp_path,
    )
    assert installed["team_plan_revision"] is None
    assert graph.ready_frontier(installed) == ["U1"]

    lifecycle.allocate_execution(
        thread_id,
        unit_id="U1",
        execution_id="exec-u1",
        native_task_name="sd_u1_a1",
        profile_id="reader",
        granted_authority="none",
        execution_basis_ref="initial:u1",
        temp_root=tmp_path,
    )
    persist_status(lifecycle, thread_id, "exec-u1", tmp_path, "completed")
    graph.accept_work_unit(
        thread_id,
        unit_id="U1",
        execution_id="exec-u1",
        result_ref="result:u1",
        control_epoch=0,
        temp_root=tmp_path,
    )

    current = state.load_state(thread_id, temp_root=tmp_path)
    assert current is not None
    assert current["team_plan_revision"] is None
    assert graph.ready_frontier(current) == ["U2"]

    allocated = lifecycle.allocate_execution(
        thread_id,
        unit_id="U2",
        execution_id="exec-u2",
        native_task_name="sd_u2_a1",
        profile_id="reader",
        granted_authority="none",
        execution_basis_ref="initial:u2",
        temp_root=tmp_path,
    )
    assert allocated["execution"]["attempt_no"] == 1


def test_fresh_retry_has_no_fixed_attempt_ceiling_and_compacts_old_settled_history(tmp_path: Path):
    state, graph, lifecycle = modules("fresh-retry")
    thread_id = "phase3-fresh-retry"
    state.write_state(state.new_state(thread_id=thread_id), temp_root=tmp_path)
    graph.install_work_graph(thread_id, units=[read_unit(graph, "U1")], temp_root=tmp_path)

    old_basis = None
    for attempt in range(1, 5):
        execution_id = f"exec-{attempt}"
        allocated = lifecycle.allocate_execution(
            thread_id,
            unit_id="U1",
            execution_id=execution_id,
            native_task_name=f"sd_u1_a{attempt}",
            profile_id="reader",
            granted_authority="none",
            execution_basis_ref=f"evidence:attempt-{attempt}",
            temp_root=tmp_path,
        )
        assert allocated["execution"]["attempt_no"] == attempt
        if attempt == 1:
            old_basis = lifecycle.fresh_observation_basis(
                thread_id, execution_id=execution_id, temp_root=tmp_path
            )
        if attempt < 4:
            persist_status(lifecycle, thread_id, execution_id, tmp_path, "errored")

    current = state.load_state(thread_id, temp_root=tmp_path)
    assert current is not None
    retained = [item for item in current["executions"] if item["unit_id"] == "U1"]
    assert [item["attempt_no"] for item in retained] == [3, 4]
    history = next(
        event
        for event in current["accounting_refs"]
        if event.get("kind") == "execution_history" and event.get("unit_id") == "U1"
    )
    assert history["compacted_attempts"] == 2
    assert history["max_attempt_no"] == 2
    assert history["last_execution_id"] == "exec-2"
    assert history["last_basis_ref"] == "evidence:attempt-2"

    assert old_basis is not None
    stale = lifecycle.persist_host_observation(
        thread_id,
        basis=old_basis,
        host_state="completed",
        agent_id="agent-exec-1",
        temp_root=tmp_path,
    )
    assert stale["reconcile_status"] == "stale"


def test_fresh_retry_rejects_reused_retained_basis(tmp_path: Path):
    state, graph, lifecycle = modules("retry-replay")
    thread_id = "phase3-retry-replay"
    state.write_state(state.new_state(thread_id=thread_id), temp_root=tmp_path)
    graph.install_work_graph(thread_id, units=[read_unit(graph, "U1")], temp_root=tmp_path)
    lifecycle.allocate_execution(
        thread_id,
        unit_id="U1",
        execution_id="exec-1",
        native_task_name="sd_u1_a1",
        profile_id="reader",
        granted_authority="none",
        execution_basis_ref="basis:one",
        temp_root=tmp_path,
    )
    persist_status(lifecycle, thread_id, "exec-1", tmp_path, "errored")

    with pytest.raises(lifecycle.ExecutionLifecycleError, match="execution_basis_ref"):
        lifecycle.allocate_execution(
            thread_id,
            unit_id="U1",
            execution_id="exec-2",
            native_task_name="sd_u1_a2",
            profile_id="reader",
            granted_authority="none",
            execution_basis_ref="basis:one",
            temp_root=tmp_path,
        )


def test_same_child_followup_requires_new_basis_without_fixed_count_ceiling(tmp_path: Path):
    state, graph, lifecycle = modules("followup")
    thread_id = "phase3-followup"
    state.write_state(state.new_state(thread_id=thread_id), temp_root=tmp_path)
    graph.install_work_graph(thread_id, units=[read_unit(graph, "U1")], temp_root=tmp_path)
    lifecycle.allocate_execution(
        thread_id,
        unit_id="U1",
        execution_id="exec-1",
        native_task_name="sd_u1_a1",
        profile_id="reader",
        granted_authority="none",
        execution_basis_ref="initial:u1",
        temp_root=tmp_path,
    )
    persist_status(lifecycle, thread_id, "exec-1", tmp_path, "completed")

    first = lifecycle.prepare_same_child_followup(
        thread_id,
        execution_id="exec-1",
        tool_input={"target": "sd_u1_a1", "message": "correct the missing edge case"},
        correction_basis_ref="correction:edge-case",
        temp_root=tmp_path,
    )
    lifecycle.persist_host_observation(
        thread_id,
        basis=first["observation_basis"],
        host_state="completed",
        agent_id="agent-exec-1",
        temp_root=tmp_path,
    )

    with pytest.raises(lifecycle.ExecutionLifecycleError, match="already used"):
        lifecycle.prepare_same_child_followup(
            thread_id,
            execution_id="exec-1",
            tool_input={"target": "sd_u1_a1", "message": "repeat the same correction"},
            correction_basis_ref="correction:edge-case",
            temp_root=tmp_path,
        )

    second = lifecycle.prepare_same_child_followup(
        thread_id,
        execution_id="exec-1",
        tool_input={"target": "sd_u1_a1", "message": "apply the newly verified constraint"},
        correction_basis_ref="correction:new-constraint",
        temp_root=tmp_path,
    )
    assert second["control_epoch"] == 2
    current = state.load_state(thread_id, temp_root=tmp_path)
    assert current is not None
    execution = next(item for item in current["executions"] if item["execution_id"] == "exec-1")
    assert execution["followup_count"] == 2
    followup_basis = [
        event
        for event in current["accounting_refs"]
        if event.get("kind") == "recovery_basis" and event.get("execution_id") == "exec-1"
    ]
    assert len(followup_basis) == 1
    assert followup_basis[0]["control_epoch"] == 2
    assert followup_basis[0]["basis_hash"] == second["correction_basis_hash"]


def test_blocking_writer_lease_blocks_new_read_execution_until_settlement(tmp_path: Path):
    state, graph, lifecycle = modules("writer-block")
    thread_id = "phase3-writer-block"
    state.write_state(state.new_state(thread_id=thread_id), temp_root=tmp_path)
    graph.install_work_graph(
        thread_id,
        units=[write_unit(graph, "U1"), read_unit(graph, "U2")],
        temp_root=tmp_path,
    )
    lifecycle.allocate_execution(
        thread_id,
        unit_id="U1",
        execution_id="exec-write",
        native_task_name="sd_u1_write",
        profile_id="worker",
        granted_authority="bounded-source-write",
        granted_write_scope=["src/u1.py"],
        execution_basis_ref="initial:writer",
        writer_lease_id="lease-write",
        temp_root=tmp_path,
    )

    with pytest.raises(lifecycle.ExecutionLifecycleError, match="WriterLease"):
        lifecycle.allocate_execution(
            thread_id,
            unit_id="U2",
            execution_id="exec-read",
            native_task_name="sd_u2_read",
            profile_id="reader",
            granted_authority="none",
            execution_basis_ref="initial:reader",
            temp_root=tmp_path,
        )

    current = state.load_state(thread_id, temp_root=tmp_path)
    assert current is not None
    assert [item["execution_id"] for item in current["executions"]] == ["exec-write"]
    assert current["writer_lease"]["state"] == "RESERVED"


def test_released_writer_owner_survives_mixed_authority_history_compaction(tmp_path: Path):
    state, graph, lifecycle = modules("released-writer-history")
    writer = load_module("phase3_writer_released_history", "writer_lease_v4.py")
    thread_id = "phase3-released-writer-history"
    state.write_state(state.new_state(thread_id=thread_id), temp_root=tmp_path)
    graph.install_work_graph(thread_id, units=[write_unit(graph, "U1")], temp_root=tmp_path)

    allocated = lifecycle.allocate_execution(
        thread_id,
        unit_id="U1",
        execution_id="exec-1",
        native_task_name="sd_u1_a1",
        profile_id="worker",
        granted_authority="bounded-source-write",
        granted_write_scope=["src/u1.py"],
        execution_basis_ref="basis:writer",
        writer_lease_id="lease-1",
        temp_root=tmp_path,
    )
    lease_epoch = allocated["writer_lease"]["lease_epoch"]
    persist_status(lifecycle, thread_id, "exec-1", tmp_path, "errored")
    writer.release_settled_execution_writer(
        thread_id,
        execution_id="exec-1",
        lease_id="lease-1",
        lease_epoch=lease_epoch,
        temp_root=tmp_path,
    )

    for attempt in range(2, 5):
        execution_id = f"exec-{attempt}"
        lifecycle.allocate_execution(
            thread_id,
            unit_id="U1",
            execution_id=execution_id,
            native_task_name=f"sd_u1_a{attempt}",
            profile_id="reader",
            granted_authority="none",
            execution_basis_ref=f"basis:reader-{attempt}",
            temp_root=tmp_path,
        )
        if attempt < 4:
            persist_status(lifecycle, thread_id, execution_id, tmp_path, "errored")

    current = state.load_state(thread_id, temp_root=tmp_path)
    assert current is not None
    assert current["writer_lease"] == {
        "lease_id": "lease-1",
        "lease_epoch": lease_epoch,
        "workspace_id": "canonical",
        "unit_id": "U1",
        "owner_kind": "execution",
        "owner_id": "exec-1",
        "state": "RELEASED",
    }
    retained = [item for item in current["executions"] if item["unit_id"] == "U1"]
    assert [item["attempt_no"] for item in retained] == [1, 3, 4]
    history = next(
        event
        for event in current["accounting_refs"]
        if event.get("kind") == "execution_history" and event.get("unit_id") == "U1"
    )
    assert history["compacted_attempts"] == 1
    assert history["max_attempt_no"] == 2
    assert history["last_execution_id"] == "exec-2"
