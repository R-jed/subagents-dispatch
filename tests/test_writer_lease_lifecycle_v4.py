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


def install_graph(state, graph, tmp_path: Path, *, two_writers: bool = False) -> None:
    state.write_state(state.new_state(thread_id="thread-p5"), temp_root=tmp_path)
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
        "thread-p5", team_plan_revision=1, units=units, temp_root=tmp_path
    )


def allocate_writer(lifecycle, tmp_path: Path, *, unit_id: str = "U1", execution_id: str = "exec-1", lease_id: str = "lease-1"):
    scope = ["src/a.py"] if unit_id == "U1" else ["src/b.py"]
    return lifecycle.allocate_execution(
        "thread-p5",
        unit_id=unit_id,
        execution_id=execution_id,
        native_task_name=f"sd_{unit_id.lower()}_a1",
        profile_id="worker",
        granted_authority="bounded-source-write",
        granted_write_scope=scope,
        writer_lease_id=lease_id,
        temp_root=tmp_path,
    )


def observe(lifecycle, tmp_path: Path, *, execution_id: str, host_state: str, agent_id: str = "agent-1"):
    basis = lifecycle.fresh_observation_basis(
        "thread-p5", execution_id=execution_id, temp_root=tmp_path
    )
    return lifecycle.persist_host_observation(
        "thread-p5",
        basis=basis,
        host_state=host_state,
        agent_id=agent_id,
        temp_root=tmp_path,
    )


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


def test_current_host_running_observation_promotes_reserved_writer_to_held(tmp_path: Path):
    state = load_module("p5_state_running", "dispatch_state_v4.py")
    graph = load_module("p5_graph_running", "work_graph_v4.py")
    lifecycle = load_module("p5_lifecycle_running", "execution_lifecycle_v4.py")
    install_graph(state, graph, tmp_path)
    allocate_writer(lifecycle, tmp_path)

    result = observe(lifecycle, tmp_path, execution_id="exec-1", host_state="running")

    assert result["lifecycle"] == "RUNNING"
    assert result["state"]["writer_lease"]["state"] == "HELD"
    assert result["state"]["executions"][0]["agent_id"] == "agent-1"


def test_interrupt_preparation_revokes_writer_and_tool_return_cannot_transfer_it(tmp_path: Path):
    state = load_module("p5_state_interrupt", "dispatch_state_v4.py")
    graph = load_module("p5_graph_interrupt", "work_graph_v4.py")
    lifecycle = load_module("p5_lifecycle_interrupt", "execution_lifecycle_v4.py")
    install_graph(state, graph, tmp_path)
    allocate_writer(lifecycle, tmp_path)
    observe(lifecycle, tmp_path, execution_id="exec-1", host_state="running")

    prepared = lifecycle.prepare_interrupt(
        "thread-p5",
        execution_id="exec-1",
        tool_input={"target": "sd_u1_a1"},
        temp_root=tmp_path,
    )
    current = state.load_state("thread-p5", temp_root=tmp_path)
    assert current is not None
    lease = current["writer_lease"]
    assert lease["state"] == "REVOKING"

    with pytest.raises(Exception, match="settled|observation"):
        lifecycle.takeover_to_main(
            "thread-p5",
            execution_id="exec-1",
            old_lease_id=lease["lease_id"],
            old_lease_epoch=lease["lease_epoch"],
            main_lease_id="lease-main",
            temp_root=tmp_path,
        )

    interrupted = lifecycle.persist_host_observation(
        "thread-p5",
        basis=prepared["observation_basis"],
        host_state="interrupted",
        agent_id="agent-1",
        temp_root=tmp_path,
    )
    assert interrupted["lifecycle"] == "INTERRUPTED"


def test_fresh_current_generation_interrupted_observation_allows_atomic_takeover(tmp_path: Path):
    state = load_module("p5_state_takeover", "dispatch_state_v4.py")
    graph = load_module("p5_graph_takeover", "work_graph_v4.py")
    lifecycle = load_module("p5_lifecycle_takeover", "execution_lifecycle_v4.py")
    install_graph(state, graph, tmp_path)
    allocate_writer(lifecycle, tmp_path)
    observe(lifecycle, tmp_path, execution_id="exec-1", host_state="running")
    prepared = lifecycle.prepare_interrupt(
        "thread-p5",
        execution_id="exec-1",
        tool_input={"target": "sd_u1_a1"},
        temp_root=tmp_path,
    )
    settled = lifecycle.persist_host_observation(
        "thread-p5",
        basis=prepared["observation_basis"],
        host_state="interrupted",
        agent_id="agent-1",
        temp_root=tmp_path,
    )
    old = settled["state"]["writer_lease"]

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


def test_unknown_writer_never_transfers_or_releases(tmp_path: Path):
    state = load_module("p5_state_unknown", "dispatch_state_v4.py")
    graph = load_module("p5_graph_unknown", "work_graph_v4.py")
    lifecycle = load_module("p5_lifecycle_unknown", "execution_lifecycle_v4.py")
    install_graph(state, graph, tmp_path)
    allocate_writer(lifecycle, tmp_path)
    lifecycle.mark_execution_unknown(
        "thread-p5", execution_id="exec-1", temp_root=tmp_path
    )
    current = state.load_state("thread-p5", temp_root=tmp_path)
    assert current is not None
    lease = current["writer_lease"]
    assert lease["state"] == "UNKNOWN"

    with pytest.raises(Exception, match="UNKNOWN"):
        lifecycle.takeover_to_main(
            "thread-p5",
            execution_id="exec-1",
            old_lease_id=lease["lease_id"],
            old_lease_epoch=lease["lease_epoch"],
            main_lease_id="lease-main",
            temp_root=tmp_path,
        )
