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


def setup_read_execution(label: str, tmp_path: Path):
    state = load_module(f"canonical_target_state_{label}", "dispatch_state_v4.py")
    graph = load_module(f"canonical_target_graph_{label}", "work_graph_v4.py")
    lifecycle = load_module(f"canonical_target_lifecycle_{label}", "execution_lifecycle_v4.py")
    thread_id = f"canonical-target-{label}"
    state.write_state(state.new_state(thread_id=thread_id), temp_root=tmp_path)
    graph.install_work_graph(
        thread_id,
        units=[
            graph.make_work_unit(
                unit_id="U1",
                intent="inspect",
                goal="inspect U1",
                output="evidence U1",
                done_when="Main verifies U1",
            )
        ],
        temp_root=tmp_path,
    )
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
    return state, lifecycle, thread_id


def observe(lifecycle, thread_id: str, tmp_path: Path, *, host_state: str, basis=None):
    if basis is None:
        basis = lifecycle.fresh_observation_basis(
            thread_id, execution_id="exec-1", temp_root=tmp_path
        )
    return lifecycle.persist_host_observation(
        thread_id,
        basis=basis,
        host_state=host_state,
        agent_id="agent-1",
        temp_root=tmp_path,
    )


def test_interrupt_accepts_canonical_host_task_address_and_rejects_bare_name(tmp_path: Path):
    state, lifecycle, thread_id = setup_read_execution("interrupt", tmp_path)
    observe(lifecycle, thread_id, tmp_path, host_state="running")

    with pytest.raises(
        lifecycle.ExecutionLifecycleError,
        match="canonical Host task address",
    ):
        lifecycle.prepare_interrupt(
            thread_id,
            execution_id="exec-1",
            tool_input={"target": "sd_u1_a1"},
            temp_root=tmp_path,
        )

    unchanged = state.load_state(thread_id, temp_root=tmp_path)
    assert unchanged is not None
    assert unchanged["executions"][0]["control_epoch"] == 0

    prepared = lifecycle.prepare_interrupt(
        thread_id,
        execution_id="exec-1",
        tool_input={"target": "/root/sd_u1_a1"},
        temp_root=tmp_path,
    )

    assert prepared["operation"] == "INTERRUPT"
    assert prepared["tool_input"] == {"target": "/root/sd_u1_a1"}
    assert prepared["control_epoch"] == 1


def test_continue_preserves_canonical_host_task_address(tmp_path: Path):
    state, lifecycle, thread_id = setup_read_execution("continue", tmp_path)
    observe(lifecycle, thread_id, tmp_path, host_state="running")
    interrupted = lifecycle.prepare_interrupt(
        thread_id,
        execution_id="exec-1",
        tool_input={"target": "/root/sd_u1_a1"},
        temp_root=tmp_path,
    )
    observe(
        lifecycle,
        thread_id,
        tmp_path,
        host_state="interrupted",
        basis=interrupted["observation_basis"],
    )

    prepared = lifecycle.prepare_same_child_continue(
        thread_id,
        execution_id="exec-1",
        tool_input={
            "target": "/root/sd_u1_a1",
            "message": "continue the same bounded responsibility",
        },
        temp_root=tmp_path,
    )

    assert prepared["operation"] == "CONTINUE"
    assert prepared["tool_input"]["target"] == "/root/sd_u1_a1"
    assert prepared["control_epoch"] == 2
    current = state.load_state(thread_id, temp_root=tmp_path)
    assert current is not None
    execution = current["executions"][0]
    assert execution["attempt_no"] == 1
    assert execution["followup_count"] == 0


def test_followup_preserves_canonical_host_task_address_and_changed_basis(tmp_path: Path):
    state, lifecycle, thread_id = setup_read_execution("followup", tmp_path)
    observe(lifecycle, thread_id, tmp_path, host_state="completed")

    prepared = lifecycle.prepare_same_child_followup(
        thread_id,
        execution_id="exec-1",
        tool_input={
            "target": "/root/sd_u1_a1",
            "message": "correct one verified edge case",
        },
        correction_basis_ref="correction:verified-edge-case",
        temp_root=tmp_path,
    )

    assert prepared["operation"] == "FOLLOWUP"
    assert prepared["tool_input"]["target"] == "/root/sd_u1_a1"
    assert prepared["control_epoch"] == 1
    assert prepared["correction_basis_hash"]
    current = state.load_state(thread_id, temp_root=tmp_path)
    assert current is not None
    execution = current["executions"][0]
    assert execution["attempt_no"] == 1
    assert execution["followup_count"] == 1
