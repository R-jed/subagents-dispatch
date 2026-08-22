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
    state = load_module(f"phase2_state_{label}", "dispatch_state_v4.py")
    graph = load_module(f"phase2_graph_{label}", "work_graph_v4.py")
    lifecycle = load_module(f"phase2_lifecycle_{label}", "execution_lifecycle_v4.py")
    return state, graph, lifecycle


def unit(graph, unit_id: str, *, depends_on=(), goal: str | None = None):
    return graph.make_work_unit(
        unit_id=unit_id,
        intent="inspect",
        goal=goal or f"inspect {unit_id}",
        output=f"evidence {unit_id}",
        depends_on=depends_on,
        done_when=f"Main verifies {unit_id}",
    )


def test_install_work_graph_accepts_one_to_four_units_without_teamplan(tmp_path: Path):
    state, graph, _lifecycle = modules("install")
    for count in (1, 4):
        thread_id = f"phase2-install-{count}"
        state.write_state(state.new_state(thread_id=thread_id), temp_root=tmp_path)
        units = [unit(graph, f"U{i}") for i in range(1, count + 1)]
        current = graph.install_work_graph(thread_id, units=units, temp_root=tmp_path)
        assert current["team_plan_revision"] is None
        assert [item["unit_id"] for item in current["work_units"]] == [
            f"U{i}" for i in range(1, count + 1)
        ]


def test_append_work_units_extends_live_graph_without_rewriting_existing_unit(tmp_path: Path):
    state, graph, lifecycle = modules("append")
    thread_id = "phase2-append"
    state.write_state(state.new_state(thread_id=thread_id), temp_root=tmp_path)
    graph.install_work_graph(thread_id, units=[unit(graph, "U1")], temp_root=tmp_path)
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
    before = state.load_state(thread_id, temp_root=tmp_path)
    assert before is not None
    existing = dict(before["work_units"][0])

    current = graph.append_work_units(
        thread_id,
        units=[unit(graph, "U2"), unit(graph, "U3", depends_on=["U1"])],
        temp_root=tmp_path,
    )

    assert current["work_units"][0] == existing
    assert [item["unit_id"] for item in current["work_units"]] == ["U1", "U2", "U3"]
    assert next(item for item in current["work_units"] if item["unit_id"] == "U3")["state"] == "BLOCKED"


def test_update_unstarted_work_unit_can_change_responsibility_before_execution(tmp_path: Path):
    state, graph, _lifecycle = modules("update")
    thread_id = "phase2-update"
    state.write_state(state.new_state(thread_id=thread_id), temp_root=tmp_path)
    graph.install_work_graph(
        thread_id,
        units=[unit(graph, "U1"), unit(graph, "U2", depends_on=["U1"])],
        temp_root=tmp_path,
    )

    replacement = unit(graph, "U2", goal="inspect the narrowed interface")
    current = graph.update_unstarted_work_unit(
        thread_id,
        unit_id="U2",
        unit=replacement,
        temp_root=tmp_path,
    )

    changed = next(item for item in current["work_units"] if item["unit_id"] == "U2")
    assert changed["goal"] == "inspect the narrowed interface"
    assert changed["depends_on"] == []
    assert changed["state"] == "READY"


def test_work_unit_responsibility_freezes_after_first_execution_binding(tmp_path: Path):
    state, graph, lifecycle = modules("freeze")
    thread_id = "phase2-freeze"
    state.write_state(state.new_state(thread_id=thread_id), temp_root=tmp_path)
    graph.install_work_graph(thread_id, units=[unit(graph, "U1")], temp_root=tmp_path)
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

    with pytest.raises(graph.WorkGraphError, match="frozen"):
        graph.update_unstarted_work_unit(
            thread_id,
            unit_id="U1",
            unit=unit(graph, "U1", goal="changed responsibility"),
            temp_root=tmp_path,
        )

    current = state.load_state(thread_id, temp_root=tmp_path)
    assert current is not None
    assert current["work_units"][0]["goal"] == "inspect U1"


def test_appended_dependency_unlocks_only_after_main_acceptance(tmp_path: Path):
    state, graph, lifecycle = modules("acceptance")
    thread_id = "phase2-acceptance"
    state.write_state(state.new_state(thread_id=thread_id), temp_root=tmp_path)
    graph.install_work_graph(thread_id, units=[unit(graph, "U1")], temp_root=tmp_path)
    graph.append_work_units(
        thread_id,
        units=[unit(graph, "U2", depends_on=["U1"])],
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
    completed_basis = lifecycle.fresh_observation_basis(
        thread_id, execution_id="exec-1", temp_root=tmp_path
    )
    completed = lifecycle.persist_host_observation(
        thread_id,
        basis=completed_basis,
        host_state="completed",
        agent_id="agent-1",
        temp_root=tmp_path,
    )
    u2 = next(item for item in completed["state"]["work_units"] if item["unit_id"] == "U2")
    assert u2["state"] == "BLOCKED"

    accepted = graph.accept_work_unit(
        thread_id,
        unit_id="U1",
        execution_id="exec-1",
        result_ref="result:u1",
        control_epoch=0,
        temp_root=tmp_path,
    )
    u2 = next(item for item in accepted["work_units"] if item["unit_id"] == "U2")
    assert u2["state"] == "READY"
