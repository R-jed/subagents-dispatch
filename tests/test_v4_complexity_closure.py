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


def install_unplanned_unit(state, graph, tmp_path: Path, *, writable: bool = False):
    payload = state.new_state(thread_id="thread-complexity")
    unit = graph.make_work_unit(
        unit_id="U1",
        intent="implement" if writable else "inspect",
        goal="complete one bounded responsibility",
        output="verified result",
        ownership_write=["src/a.py"] if writable else [],
        authority_ceiling="bounded-source-write" if writable else "none",
        write_scope_ceiling=["src/a.py"] if writable else [],
        done_when="acceptance evidence exists",
    )
    payload["work_units"] = [unit]
    state.write_state(payload, temp_root=tmp_path)
    return unit


def test_single_reader_execution_does_not_require_team_plan(tmp_path: Path):
    state = load_module("closure_state_reader", "dispatch_state_v4.py")
    graph = load_module("closure_graph_reader", "work_graph_v4.py")
    lifecycle = load_module("closure_lifecycle_reader", "execution_lifecycle_v4.py")
    install_unplanned_unit(state, graph, tmp_path)

    result = lifecycle.allocate_execution(
        "thread-complexity",
        unit_id="U1",
        execution_id="exec-reader",
        native_task_name="sd_u1_a1",
        profile_id="reader",
        granted_authority="none",
        temp_root=tmp_path,
    )

    assert result["execution"]["team_plan_revision"] is None
    persisted = state.load_state("thread-complexity", temp_root=tmp_path)
    assert persisted is not None
    assert persisted["team_plan_revision"] is None
    assert persisted["executions"][0]["team_plan_revision"] is None


def test_single_writer_execution_reserves_lease_without_team_plan(tmp_path: Path):
    state = load_module("closure_state_writer", "dispatch_state_v4.py")
    graph = load_module("closure_graph_writer", "work_graph_v4.py")
    lifecycle = load_module("closure_lifecycle_writer", "execution_lifecycle_v4.py")
    install_unplanned_unit(state, graph, tmp_path, writable=True)

    result = lifecycle.allocate_execution(
        "thread-complexity",
        unit_id="U1",
        execution_id="exec-writer",
        native_task_name="sd_u1_a1",
        profile_id="worker",
        granted_authority="bounded-source-write",
        granted_write_scope=["src/a.py"],
        writer_lease_id="lease-single",
        temp_root=tmp_path,
    )

    assert result["execution"]["team_plan_revision"] is None
    assert result["writer_lease"]["state"] == "RESERVED"
    assert result["writer_lease"]["owner_id"] == "exec-writer"


def test_single_work_unit_installer_keeps_null_revision_and_rejects_dependencies(tmp_path: Path):
    state = load_module("closure_state_install", "dispatch_state_v4.py")
    graph = load_module("closure_graph_install", "work_graph_v4.py")
    payload = state.new_state(thread_id="thread-complexity")
    state.write_state(payload, temp_root=tmp_path)

    assert hasattr(graph, "install_single_work_unit")
    unit = graph.make_work_unit(
        unit_id="U1",
        intent="inspect",
        goal="inspect one thing",
        output="evidence",
        done_when="evidence exists",
    )
    installed = graph.install_single_work_unit(
        "thread-complexity", unit=unit, temp_root=tmp_path
    )
    assert installed["team_plan_revision"] is None
    assert len(installed["work_units"]) == 1
    assert installed["work_units"][0]["state"] == "READY"

    second_root = tmp_path / "second"
    second_root.mkdir()
    state.write_state(state.new_state(thread_id="thread-complexity-2"), temp_root=second_root)
    dependent = graph.make_work_unit(
        unit_id="U2",
        intent="inspect",
        goal="invalid dependent single work",
        output="evidence",
        depends_on=["U0"],
        done_when="never",
    )
    with pytest.raises(graph.WorkGraphError, match="dependency|single"):
        graph.install_single_work_unit(
            "thread-complexity-2", unit=dependent, temp_root=second_root
        )


def test_managed_assignment_uses_five_section_canonical_record():
    managed = load_module("closure_managed", "managed_execution_v4.py")
    current = {
        "work_units": [
            {
                "unit_id": "U1",
                "intent": "inspect",
                "goal": "trace contract",
                "output": "bounded evidence",
                "depends_on": [],
                "state": "EXECUTING",
                "ownership": {"write": [], "forbidden": ["secrets/"]},
                "authority_ceiling": "none",
                "write_scope_ceiling": [],
                "done_when": "contract is evidenced",
                "responsibility_context": {
                    "interfaces": [],
                    "invariants": [],
                    "decision_boundary": "Escalate material decisions to the main session.",
                    "accepted_evidence_refs": [],
                    "do_not_redo": [],
                    "stop_boundary": "Stop and report blockers to the main session.",
                },
                "accepted_result_ref": None,
                "accepted_execution_id": None,
                "accepted_control_epoch": None,
            }
        ],
        "executions": [],
    }
    execution = {
        "execution_id": "exec-1",
        "unit_id": "U1",
        "team_plan_revision": None,
        "attempt_no": 1,
        "granted_authority": "none",
        "granted_write_scope": [],
    }

    packet = managed.assignment_packet(current, execution=execution)
    assert list(packet) == [
        "objective",
        "ownership",
        "interfaces",
        "constraints",
        "verification",
    ]
    assert packet["ownership"]["unit_id"] == "U1"
    assert packet["ownership"]["execution_id"] == "exec-1"
    assert packet["ownership"]["mutation_authority"] == "none"
    assert packet["verification"]["acceptance"] == "contract is evidenced"


def test_routing_has_no_second_responsibility_packet_template():
    text = (ROOT / "contracts" / "routing.md").read_text(encoding="utf-8")
    assert "responsibility-packet.md" in text
    for retired_field in (
        "TEAM PLAN REVISION, when applicable",
        "TASK ID",
        "READ / WRITE SCOPE",
        "HANDOFF CAPSULE, when useful",
    ):
        assert retired_field not in text


def test_profile_machine_truth_comes_from_policy_projection():
    policy = load_module("closure_policy", "policy.py")
    state = load_module("closure_state_policy", "dispatch_state_v4.py")
    orchestrate = load_module("closure_orchestrate_policy", "orchestrate_v4.py")
    managed = load_module("closure_managed_policy", "managed_execution_v4.py")

    profiles = policy.profile_contracts()
    assert set(profiles) == {"reader", "worker", "investigator", "solver", "advisor"}
    for role, spec in profiles.items():
        assert state.PROFILE_CONTRACT[role] == (
            spec["model"],
            spec["effort"],
            spec["mutation_authority"],
        )
        assert orchestrate.FIXED_PROFILES[role]["model"] == spec["model"]
        assert orchestrate.FIXED_PROFILES[role]["effort"] == spec["effort"]
        assert managed.PROFILE_AGENT_TYPES[role] == spec["agent_type"]


def test_runtime_integrity_excludes_maintainer_only_tools_and_keeps_product_scripts():
    integrity = load_module("closure_integrity", "package_integrity.py")
    files = {path.as_posix() for path in integrity.runtime_files(ROOT)}
    excluded = {
        "scripts/calibration_profile_contract.py",
        "scripts/calibration_profiles.py",
        "scripts/calibration_profiles_core.py",
        "scripts/release_evidence_v4.py",
        "scripts/score-behavioral-evals.py",
        "scripts/validate-experiment-campaign.py",
        "scripts/validate-experiment-run.py",
        "scripts/validate_experiment_campaign_core.py",
    }
    assert not (files & excluded)
    for required in (
        "scripts/doctor.py",
        "scripts/install-agents.py",
        "scripts/orchestration_guard.py",
        "scripts/host_evidence_v4.py",
        "scripts/review-artifact.py",
        "scripts/runtime-evidence.py",
        "scripts/spawn_guard.py",
    ):
        assert required in files


def test_active_contracts_use_current_two_skill_and_doctor_ownership():
    architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    final_review = (ROOT / "contracts" / "final-review.md").read_text(encoding="utf-8")
    assert "other root `contracts/` documents are hardened v3.x" not in architecture.lower()
    assert "release readiness" not in architecture
    assert "selection/invocation of Dispatch" not in final_review
    assert "selection/invocation of Orchestrate" in final_review


def test_recovery_contract_uses_v4_execution_identity_and_lifecycle():
    recovery = (ROOT / "contracts" / "recovery.md").read_text(encoding="utf-8")
    assert "execution_id" in recovery
    assert "attempt_no" in recovery
    assert "task_id" not in recovery
    assert "PLANNED" not in recovery
    assert "compact thread-scoped state" not in recovery
    for state_name in (
        "SPAWN_PENDING",
        "RUNNING",
        "INTERRUPTED",
        "COMPLETED",
        "FAILED",
        "UNKNOWN",
        "CLOSED",
    ):
        assert state_name in recovery
