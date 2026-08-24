from __future__ import annotations

import importlib.util
import json
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


def test_single_reader_execution_does_not_carry_team_plan_compatibility(tmp_path: Path):
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

    assert "team_plan_revision" not in result["execution"]
    assert result["writer_lease"] is None


def test_single_writer_execution_reserves_lease_without_compatibility_marker(tmp_path: Path):
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

    assert "team_plan_revision" not in result["execution"]
    assert result["writer_lease"]["state"] == "RESERVED"


def test_single_unit_uses_the_same_authoritative_work_graph_api(tmp_path: Path):
    state = load_module("closure_state_install", "dispatch_state_v4.py")
    graph = load_module("closure_graph_install", "work_graph_v4.py")
    state.write_state(state.new_state(thread_id="thread-complexity"), temp_root=tmp_path)

    unit = graph.make_work_unit(
        unit_id="U1",
        intent="inspect",
        goal="inspect one thing",
        output="evidence",
        done_when="evidence exists",
    )
    installed = graph.install_work_graph(
        "thread-complexity", units=[unit], temp_root=tmp_path
    )
    assert "team_plan_revision" not in installed
    assert installed["work_units"][0]["state"] == "READY"
    assert not hasattr(graph, "install_single_work_unit")

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
    with pytest.raises(state.StatePayloadError, match="unknown unit"):
        graph.install_work_graph(
            "thread-complexity-2", units=[dependent], temp_root=second_root
        )


def test_managed_assignment_has_one_canonical_five_section_record():
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
                    "decision_boundary": "Escalate material decisions to Main.",
                    "accepted_evidence_refs": [],
                    "do_not_redo": [],
                    "stop_boundary": "Stop and report blockers to Main.",
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
        "attempt_no": 1,
        "granted_authority": "none",
        "granted_write_scope": [],
    }

    packet = managed.assignment_packet(current, execution=execution)
    assert list(packet) == ["objective", "ownership", "interfaces", "constraints", "verification"]
    assert packet["ownership"]["execution_id"] == "exec-1"
    assert "team_plan_revision" not in packet["ownership"]


def test_profile_machine_truth_has_one_policy_projection():
    policy = load_module("closure_policy", "policy.py")
    state = load_module("closure_state_policy", "dispatch_state_v4.py")
    orchestrate = load_module("closure_orchestrate_policy", "orchestrate_v4.py")
    managed = load_module("closure_managed_policy", "managed_execution_v4.py")

    profiles = policy.profile_contracts()
    assert set(profiles) == {"reader", "worker", "investigator", "solver", "advisor"}
    for role, spec in profiles.items():
        assert state.PROFILE_CONTRACT[role] == (
            spec["model"], spec["effort"], spec["mutation_authority"]
        )
        assert orchestrate.FIXED_PROFILES[role]["model"] == spec["model"]
        assert managed.PROFILE_AGENT_TYPES[role] == spec["agent_type"]


def test_runtime_integrity_keeps_product_runtime_and_excludes_maintainer_tools():
    integrity = load_module("closure_integrity", "package_integrity.py")
    files = {path.as_posix() for path in integrity.runtime_files(ROOT)}
    maintainer_only = {
        "scripts/calibration_profile_contract.py",
        "scripts/calibration_profiles.py",
        "scripts/calibration_profiles_core.py",
        "scripts/release_evidence_v4.py",
        "scripts/score-behavioral-evals.py",
        "scripts/validate-experiment-campaign.py",
        "scripts/validate-experiment-run.py",
        "scripts/validate_experiment_campaign_core.py",
    }
    assert not (files & maintainer_only)
    for required in (
        "scripts/doctor.py",
        "scripts/install-agents.py",
        "scripts/host_capabilities.py",
        "scripts/execution_lifecycle_v4.py",
        "scripts/writer_lease_v4.py",
        "scripts/review-artifact.py",
        "scripts/runtime-evidence.py",
    ):
        assert required in files


def test_active_contracts_assign_current_two_skill_and_native_host_ownership():
    architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    orchestrate_skill = (ROOT / "skills" / "orchestrate" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    final_review = (ROOT / "contracts" / "final-review.md").read_text(encoding="utf-8")
    machine = json.loads(
        (ROOT / "docs" / "v4" / "architecture.json").read_text(encoding="utf-8")
    )
    expected_runtime_owners = {
        "orchestration": "scripts/orchestrate_v4.py",
        "state": "scripts/dispatch_state_v4.py",
        "storage": "scripts/state_storage.py",
        "work_graph": "scripts/work_graph_v4.py",
        "scheduler": "scripts/scheduler_v4.py",
        "execution_lifecycle": "scripts/execution_lifecycle_v4.py",
        "writer_lease": "scripts/writer_lease_v4.py",
        "managed_execution": "scripts/managed_execution_v4.py",
        "host_capabilities": "scripts/host_capabilities.py",
        "runtime_evidence": "scripts/inspect-collaboration-runtime.py",
    }

    for expected in (
        "docs/v4/architecture.json",
        "Codex Native Subagents",
        "Orchestrate",
        "Doctor",
    ):
        assert expected in architecture
    assert machine["runtime_owners"] == expected_runtime_owners
    assert not (ROOT / "docs" / "v4" / "phase-status.json").exists()
    assert not (ROOT / "docs" / "repository-architecture.md").exists()
    assert "../../docs/v4/architecture.json#runtime_owners" in orchestrate_skill
    assert "selection/invocation of Orchestrate" in final_review
    assert machine["public_skills"] == ["orchestrate", "doctor"]
    assert machine["host_truth"]["lifecycle_owner"] == "codex_host"


def test_recovery_contract_uses_execution_identity_and_native_lifecycle():
    recovery = (ROOT / "contracts" / "recovery.md").read_text(encoding="utf-8")
    assert "execution_id" in recovery
    assert "attempt_no" in recovery
    assert "Codex Host owns native lifecycle truth" in recovery
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
