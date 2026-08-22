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
    state = load_module(f"remediation_state_{label}", "dispatch_state_v4.py")
    graph = load_module(f"remediation_graph_{label}", "work_graph_v4.py")
    lifecycle = load_module(f"remediation_lifecycle_{label}", "execution_lifecycle_v4.py")
    return state, graph, lifecycle


def read_unit(graph, unit_id: str):
    return graph.make_work_unit(
        unit_id=unit_id,
        intent="inspect",
        goal=f"inspect {unit_id}",
        output=f"evidence {unit_id}",
        done_when=f"Main verifies {unit_id}",
    )


def persist(lifecycle, thread_id: str, execution_id: str, tmp_path: Path, host_state: str):
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


def test_scope_model_rejects_windows_drive_and_allows_descendant_scopes(tmp_path: Path):
    state, graph, lifecycle = modules("scope")

    unsafe = state.new_state(thread_id="scope-unsafe")
    unsafe["work_units"] = [
        graph.make_work_unit(
            unit_id="U1",
            intent="implement",
            goal="unsafe",
            output="patch",
            ownership_write=["C:/outside"],
            authority_ceiling="bounded-source-write",
            write_scope_ceiling=["C:/outside"],
            done_when="verified",
        )
    ]
    with pytest.raises(state.StatePayloadError, match="relative path"):
        state.validate_state_payload(unsafe)

    thread_id = "scope-descendant"
    state.write_state(state.new_state(thread_id=thread_id), temp_root=tmp_path)
    graph.install_work_graph(
        thread_id,
        units=[
            graph.make_work_unit(
                unit_id="U1",
                intent="implement",
                goal="bounded change",
                output="patch",
                ownership_write=["src"],
                ownership_forbidden=["src/generated"],
                authority_ceiling="bounded-source-write",
                write_scope_ceiling=["src/feature"],
                done_when="verified",
            )
        ],
        temp_root=tmp_path,
    )
    allocated = lifecycle.allocate_execution(
        thread_id,
        unit_id="U1",
        execution_id="exec-u1",
        native_task_name="sd_u1_a1",
        profile_id="worker",
        granted_authority="bounded-source-write",
        granted_write_scope=["src/feature/handler.py"],
        execution_basis_ref="initial:u1",
        writer_lease_id="lease-u1",
        temp_root=tmp_path,
    )
    assert allocated["execution"]["granted_write_scope"] == ["src/feature/handler.py"]


def test_duplicate_host_observation_is_true_state_noop(tmp_path: Path):
    state, graph, lifecycle = modules("observation-noop")
    thread_id = "observation-noop"
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
    basis = lifecycle.fresh_observation_basis(
        thread_id, execution_id="exec-1", temp_root=tmp_path
    )
    first = lifecycle.persist_host_observation(
        thread_id,
        basis=basis,
        host_state="running",
        agent_id="agent-1",
        temp_root=tmp_path,
    )
    before = first["state"]
    second = lifecycle.persist_host_observation(
        thread_id,
        basis=basis,
        host_state="running",
        agent_id="agent-1",
        temp_root=tmp_path,
    )
    assert second["reconcile_status"] == "noop"
    assert second["idempotent"] is True
    assert second["state"]["state_revision"] == before["state_revision"]
    assert second["state"]["updated_at"] == before["updated_at"]


def test_observation_basis_stays_stale_after_compaction_and_execution_id_reuse(tmp_path: Path):
    state, graph, lifecycle = modules("generation-basis")
    thread_id = "generation-basis"
    state.write_state(state.new_state(thread_id=thread_id), temp_root=tmp_path)
    graph.install_work_graph(
        thread_id,
        units=[read_unit(graph, "U1"), read_unit(graph, "U2")],
        temp_root=tmp_path,
    )

    lifecycle.allocate_execution(
        thread_id,
        unit_id="U1",
        execution_id="shared-exec",
        native_task_name="sd_u1_a1",
        profile_id="reader",
        granted_authority="none",
        execution_basis_ref="basis:u1:1",
        temp_root=tmp_path,
    )
    stale_basis = lifecycle.fresh_observation_basis(
        thread_id, execution_id="shared-exec", temp_root=tmp_path
    )
    persist(lifecycle, thread_id, "shared-exec", tmp_path, "errored")

    lifecycle.allocate_execution(
        thread_id,
        unit_id="U1",
        execution_id="exec-u1-2",
        native_task_name="sd_u1_a2",
        profile_id="reader",
        granted_authority="none",
        execution_basis_ref="basis:u1:2",
        temp_root=tmp_path,
    )
    persist(lifecycle, thread_id, "exec-u1-2", tmp_path, "errored")
    lifecycle.allocate_execution(
        thread_id,
        unit_id="U1",
        execution_id="exec-u1-3",
        native_task_name="sd_u1_a3",
        profile_id="reader",
        granted_authority="none",
        execution_basis_ref="basis:u1:3",
        temp_root=tmp_path,
    )

    current = state.load_state(thread_id, temp_root=tmp_path)
    assert current is not None
    assert all(item["execution_id"] != "shared-exec" for item in current["executions"])

    lifecycle.allocate_execution(
        thread_id,
        unit_id="U2",
        execution_id="shared-exec",
        native_task_name="sd_u2_a1",
        profile_id="reader",
        granted_authority="none",
        execution_basis_ref="basis:u2:1",
        temp_root=tmp_path,
    )
    result = lifecycle.persist_host_observation(
        thread_id,
        basis=stale_basis,
        host_state="completed",
        agent_id="agent-shared-exec",
        temp_root=tmp_path,
    )
    assert result["reconcile_status"] == "stale"
    latest = state.load_state(thread_id, temp_root=tmp_path)
    assert latest is not None
    u2 = next(item for item in latest["executions"] if item["execution_id"] == "shared-exec")
    assert u2["unit_id"] == "U2"
    assert u2["lifecycle"] == "SPAWN_PENDING"


def test_many_same_child_followups_keep_generation_evidence_bounded(tmp_path: Path):
    state, graph, lifecycle = modules("bounded-followup")
    thread_id = "bounded-followup"
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
    persist(lifecycle, thread_id, "exec-1", tmp_path, "completed")

    for index in range(1, 151):
        prepared = lifecycle.prepare_same_child_followup(
            thread_id,
            execution_id="exec-1",
            tool_input={"target": "sd_u1_a1", "message": f"correction {index}"},
            correction_basis_ref=f"correction:{index}",
            temp_root=tmp_path,
        )
        lifecycle.persist_host_observation(
            thread_id,
            basis=prepared["observation_basis"],
            host_state="completed",
            agent_id="agent-exec-1",
            temp_root=tmp_path,
        )

    current = state.load_state(thread_id, temp_root=tmp_path)
    assert current is not None
    execution = next(item for item in current["executions"] if item["execution_id"] == "exec-1")
    assert execution["followup_count"] == 150
    current_epoch = execution["control_epoch"]
    recovery = [
        event
        for event in current["accounting_refs"]
        if event.get("kind") == "recovery_basis" and event.get("execution_id") == "exec-1"
    ]
    observations = [
        event
        for event in current["accounting_refs"]
        if event.get("kind") == "host_observation" and event.get("execution_id") == "exec-1"
    ]
    assert len(recovery) == 1
    assert recovery[0]["control_epoch"] == current_epoch
    assert observations
    assert all(event["control_epoch"] == current_epoch for event in observations)
    assert len(current["accounting_refs"]) <= 8
