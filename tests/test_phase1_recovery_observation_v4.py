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


def install_units(tmp_path: Path, thread_id: str, *, writable_second: bool = False):
    state = load_module(f"phase1_state_{thread_id}", "dispatch_state_v4.py")
    graph = load_module(f"phase1_graph_{thread_id}", "work_graph_v4.py")
    lifecycle = load_module(f"phase1_lifecycle_{thread_id}", "execution_lifecycle_v4.py")

    state.write_state(state.new_state(thread_id=thread_id), temp_root=tmp_path)
    units = [
        graph.make_work_unit(
            unit_id="U1",
            intent="inspect",
            goal="collect bounded evidence",
            output="evidence",
            done_when="Main verifies the evidence",
        )
    ]
    if writable_second:
        units.append(
            graph.make_work_unit(
                unit_id="U2",
                intent="implement",
                goal="apply one bounded change",
                output="verified patch",
                ownership_write=["src/u2.py"],
                authority_ceiling="bounded-source-write",
                write_scope_ceiling=["src/u2.py"],
                done_when="Main verifies the change",
            )
        )
    graph.install_work_graph(thread_id, units=units, temp_root=tmp_path)
    return state, lifecycle


def fail_first_read_attempt(tmp_path: Path, thread_id: str):
    state, lifecycle = install_units(tmp_path, thread_id)
    lifecycle.allocate_execution(
        thread_id,
        unit_id="U1",
        execution_id="exec-1",
        native_task_name="sd_u1_a1",
        profile_id="reader",
        granted_authority="none",
        execution_basis_ref="initial:user-goal",
        temp_root=tmp_path,
    )
    basis = lifecycle.fresh_observation_basis(
        thread_id, execution_id="exec-1", temp_root=tmp_path
    )
    lifecycle.persist_host_observation(
        thread_id,
        basis=basis,
        host_state="running",
        agent_id="agent-1",
        temp_root=tmp_path,
    )
    basis = lifecycle.fresh_observation_basis(
        thread_id, execution_id="exec-1", temp_root=tmp_path
    )
    lifecycle.persist_host_observation(
        thread_id,
        basis=basis,
        host_state="errored",
        agent_id="agent-1",
        failure_origin="tool_failure",
        temp_root=tmp_path,
    )
    return state, lifecycle


def test_failed_execution_can_allocate_fresh_retry_with_new_basis(tmp_path: Path):
    thread_id = "phase1-failed-retry"
    state, lifecycle = fail_first_read_attempt(tmp_path, thread_id)

    failed = state.load_state(thread_id, temp_root=tmp_path)
    assert failed is not None
    assert failed["work_units"][0]["state"] == "EXECUTING"
    assert failed["executions"][0]["lifecycle"] == "FAILED"

    retry = lifecycle.allocate_execution(
        thread_id,
        unit_id="U1",
        execution_id="exec-2",
        native_task_name="sd_u1_a2",
        profile_id="reader",
        granted_authority="none",
        execution_basis_ref="failure:exec-1:new-evidence",
        temp_root=tmp_path,
    )

    assert retry["execution"]["attempt_no"] == 2
    assert retry["execution"]["execution_basis_ref"] == "failure:exec-1:new-evidence"
    current = state.load_state(thread_id, temp_root=tmp_path)
    assert current is not None
    assert current["work_units"][0]["state"] == "EXECUTING"
    assert [item["execution_id"] for item in current["executions"]] == ["exec-1", "exec-2"]


def test_failed_execution_rejects_reused_recovery_basis(tmp_path: Path):
    thread_id = "phase1-reused-basis"
    _state, lifecycle = fail_first_read_attempt(tmp_path, thread_id)

    with pytest.raises(lifecycle.ExecutionLifecycleError, match="execution_basis_ref"):
        lifecycle.allocate_execution(
            thread_id,
            unit_id="U1",
            execution_id="exec-2",
            native_task_name="sd_u1_a2",
            profile_id="reader",
            granted_authority="none",
            execution_basis_ref="initial:user-goal",
            temp_root=tmp_path,
        )


def test_unknown_execution_still_blocks_fresh_retry(tmp_path: Path):
    thread_id = "phase1-unknown-block"
    state, lifecycle = install_units(tmp_path, thread_id)
    lifecycle.allocate_execution(
        thread_id,
        unit_id="U1",
        execution_id="exec-1",
        native_task_name="sd_u1_a1",
        profile_id="reader",
        granted_authority="none",
        execution_basis_ref="initial:user-goal",
        temp_root=tmp_path,
    )
    lifecycle.mark_execution_unknown(
        thread_id,
        execution_id="exec-1",
        temp_root=tmp_path,
    )

    with pytest.raises(lifecycle.ExecutionLifecycleError):
        lifecycle.allocate_execution(
            thread_id,
            unit_id="U1",
            execution_id="exec-2",
            native_task_name="sd_u1_a2",
            profile_id="reader",
            granted_authority="none",
            execution_basis_ref="new-evidence:after-unknown",
            temp_root=tmp_path,
        )

    current = state.load_state(thread_id, temp_root=tmp_path)
    assert current is not None
    assert [item["execution_id"] for item in current["executions"]] == ["exec-1"]
    assert current["executions"][0]["lifecycle"] == "UNKNOWN"


def test_read_observation_basis_ignores_unrelated_writer_lease_generation(tmp_path: Path):
    thread_id = "phase1-read-writer-basis"
    state, lifecycle = install_units(tmp_path, thread_id, writable_second=True)
    lifecycle.allocate_execution(
        thread_id,
        unit_id="U1",
        execution_id="exec-read",
        native_task_name="sd_u1_a1",
        profile_id="reader",
        granted_authority="none",
        execution_basis_ref="initial:read",
        temp_root=tmp_path,
    )
    read_basis = lifecycle.fresh_observation_basis(
        thread_id, execution_id="exec-read", temp_root=tmp_path
    )
    assert read_basis["lease_epoch"] is None

    lifecycle.allocate_execution(
        thread_id,
        unit_id="U2",
        execution_id="exec-write",
        native_task_name="sd_u2_a1",
        profile_id="worker",
        granted_authority="bounded-source-write",
        granted_write_scope=["src/u2.py"],
        execution_basis_ref="initial:write",
        writer_lease_id="lease-write",
        temp_root=tmp_path,
    )
    writer_basis = lifecycle.fresh_observation_basis(
        thread_id, execution_id="exec-write", temp_root=tmp_path
    )
    assert writer_basis["lease_epoch"] == 1

    result = lifecycle.persist_host_observation(
        thread_id,
        basis=read_basis,
        host_state="completed",
        agent_id="agent-read",
        temp_root=tmp_path,
    )
    assert result["reconcile_status"] == "applied"
    assert result["lifecycle"] == "COMPLETED"

    current = state.load_state(thread_id, temp_root=tmp_path)
    assert current is not None
    read_execution = next(item for item in current["executions"] if item["execution_id"] == "exec-read")
    assert read_execution["lifecycle"] == "COMPLETED"
    assert current["writer_lease"]["owner_id"] == "exec-write"
    assert current["writer_lease"]["state"] == "RESERVED"
