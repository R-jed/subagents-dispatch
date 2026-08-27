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


def test_interrupt_accepts_canonical_host_task_address(tmp_path: Path):
    state = load_module("canonical_target_state_interrupt", "dispatch_state_v4.py")
    graph = load_module("canonical_target_graph_interrupt", "work_graph_v4.py")
    lifecycle = load_module("canonical_target_lifecycle_interrupt", "execution_lifecycle_v4.py")
    thread_id = "canonical-target-interrupt"
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
    running_basis = lifecycle.fresh_observation_basis(
        thread_id, execution_id="exec-1", temp_root=tmp_path
    )
    lifecycle.persist_host_observation(
        thread_id,
        basis=running_basis,
        host_state="running",
        agent_id="agent-1",
        temp_root=tmp_path,
    )

    prepared = lifecycle.prepare_interrupt(
        thread_id,
        execution_id="exec-1",
        tool_input={"target": "/root/sd_u1_a1"},
        temp_root=tmp_path,
    )

    assert prepared["operation"] == "INTERRUPT"
    assert prepared["tool_input"] == {"target": "/root/sd_u1_a1"}
    assert prepared["control_epoch"] == 1
