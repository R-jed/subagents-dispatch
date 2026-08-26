from __future__ import annotations

import importlib
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def modules():
    scripts = str(SCRIPTS)
    sys.path.insert(0, scripts)
    try:
        names = [
            "dispatch_state_v4",
            "work_graph_v4",
            "execution_lifecycle_v4",
            "host_qualification_guard",
            "package_integrity",
        ]
        loaded = {}
        for name in names:
            sys.modules.pop(name, None)
            loaded[name] = importlib.import_module(name)
        return (
            loaded["dispatch_state_v4"],
            loaded["work_graph_v4"],
            loaded["execution_lifecycle_v4"],
            loaded["host_qualification_guard"],
            loaded["package_integrity"],
        )
    finally:
        sys.path.remove(scripts)


def investigator_unit(graph):
    return graph.make_work_unit(
        unit_id="H2_N0_INVESTIGATOR",
        intent="inspect",
        goal="verify Investigator fixed configuration",
        output="qualification evidence",
        done_when="Main independently accepts the N0 Investigator evidence.",
    )


def install_unit(state, graph, thread_id: str, tmp_path: Path) -> None:
    state.write_state(state.new_state(thread_id=thread_id), temp_root=tmp_path)
    graph.install_work_graph(
        thread_id,
        units=[investigator_unit(graph)],
        temp_root=tmp_path,
    )


def valid_preflight(comment_id: int = 5418088990) -> str:
    return (
        f"preflight:issue-91-comment-{comment_id}:"
        "H2-N0-INVESTIGATOR-PREFLIGHT-POST-CLEAN-BREAK-001:RERUN"
    )


def test_first_probe_allocation_binds_issue_preflight_instead_of_default_initial_basis(tmp_path: Path):
    state, graph, _, guard, _ = modules()
    thread_id = "qualification-first-probe"
    install_unit(state, graph, thread_id, tmp_path)

    allocated = guard.allocate_single_probe_execution(
        thread_id,
        unit_id="H2_N0_INVESTIGATOR",
        execution_id="exec-1",
        native_task_name="sd_h2_n0_investigator_a1",
        profile_id="investigator",
        granted_authority="none",
        preflight_ref=valid_preflight(),
        temp_root=tmp_path,
    )

    execution = allocated["execution"]
    assert execution["attempt_no"] == 1
    assert execution["execution_basis_ref"] == valid_preflight()
    assert execution["execution_basis_ref"] != "initial:exec-1"
    assert execution["lifecycle"] == "SPAWN_PENDING"


def test_prepare_probe_spawn_rejects_first_attempt_with_default_initial_basis(tmp_path: Path):
    state, graph, lifecycle, guard, _ = modules()
    thread_id = "qualification-default-basis"
    install_unit(state, graph, thread_id, tmp_path)

    lifecycle.allocate_execution(
        thread_id,
        unit_id="H2_N0_INVESTIGATOR",
        execution_id="exec-1",
        native_task_name="sd_h2_n0_investigator_a1",
        profile_id="investigator",
        granted_authority="none",
        temp_root=tmp_path,
    )

    with pytest.raises(guard.QualificationGuardError, match="execution basis"):
        guard.prepare_single_probe_spawn(
            thread_id,
            orchestration_id=thread_id,
            unit_id="H2_N0_INVESTIGATOR",
            execution_id="exec-1",
            preflight_ref=valid_preflight(),
            temp_root=tmp_path,
        )


def test_completed_probe_cannot_be_rejected_and_reallocated_to_repair_provenance(tmp_path: Path):
    state, graph, lifecycle, guard, _ = modules()
    thread_id = "qualification-no-provenance-retry"
    install_unit(state, graph, thread_id, tmp_path)

    allocated = guard.allocate_single_probe_execution(
        thread_id,
        unit_id="H2_N0_INVESTIGATOR",
        execution_id="exec-1",
        native_task_name="sd_h2_n0_investigator_a1",
        profile_id="investigator",
        granted_authority="none",
        preflight_ref=valid_preflight(),
        temp_root=tmp_path,
    )
    execution = allocated["execution"]
    basis = lifecycle.fresh_observation_basis(
        thread_id,
        execution_id=execution["execution_id"],
        temp_root=tmp_path,
    )
    lifecycle.persist_host_observation(
        thread_id,
        basis=basis,
        host_state="completed",
        agent_id="investigator-child-1",
        temp_root=tmp_path,
    )
    graph.reject_work_unit(
        thread_id,
        unit_id="H2_N0_INVESTIGATOR",
        execution_id="exec-1",
        temp_root=tmp_path,
    )

    with pytest.raises(guard.QualificationGuardError):
        guard.allocate_single_probe_execution(
            thread_id,
            unit_id="H2_N0_INVESTIGATOR",
            execution_id="exec-2",
            native_task_name="sd_h2_n0_investigator_a2",
            profile_id="investigator",
            granted_authority="none",
            preflight_ref=valid_preflight(5419999999),
            temp_root=tmp_path,
        )

    current = state.load_state(thread_id, temp_root=tmp_path)
    assert current is not None
    matching = [
        item
        for item in current["executions"]
        if item["unit_id"] == "H2_N0_INVESTIGATOR"
    ]
    assert [(item["attempt_no"], item["execution_id"]) for item in matching] == [(1, "exec-1")]
    unit = next(item for item in current["work_units"] if item["unit_id"] == "H2_N0_INVESTIGATOR")
    assert unit["state"] == "REJECTED"


def test_preflight_ref_must_be_issue_91_rerun_authorization(tmp_path: Path):
    state, graph, _, guard, _ = modules()
    thread_id = "qualification-preflight-shape"
    install_unit(state, graph, thread_id, tmp_path)

    for invalid in (
        "initial:exec-1",
        "preflight:issue-91-comment-5418088990:gate:REUSE",
        "preflight:other-ledger-comment-5418088990:gate:RERUN",
    ):
        with pytest.raises(guard.QualificationGuardError, match="Issue #91 RERUN"):
            guard.allocate_single_probe_execution(
                thread_id,
                unit_id="H2_N0_INVESTIGATOR",
                execution_id="exec-1",
                native_task_name="sd_h2_n0_investigator_a1",
                profile_id="investigator",
                granted_authority="none",
                preflight_ref=invalid,
                temp_root=tmp_path,
            )


def test_qualification_guard_is_maintainer_only_and_not_shipped_in_plugin_runtime():
    _, _, _, _, package_integrity = modules()

    runtime_paths = {path.as_posix() for path in package_integrity.runtime_files(ROOT)}
    assert "scripts/host_qualification_guard.py" not in runtime_paths
    assert "scripts/host_qualification_guard.py" not in package_integrity.load_manifest(ROOT)["files"]
