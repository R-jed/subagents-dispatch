from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tomllib

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


def test_responsibility_semantics_survive_work_unit_to_wire_record():
    graph = load_module("pre_host_graph", "work_graph_v4.py")
    managed = load_module("pre_host_managed", "managed_execution_v4.py")

    unit = graph.make_work_unit(
        unit_id="U1",
        intent="inspect",
        goal="trace API compatibility",
        output="bounded evidence",
        done_when="compatibility boundary is evidenced",
        interfaces=["public API users.list"],
        invariants=["existing pagination behavior remains stable"],
        decision_boundary="Escalate any public API behavior change to the main session.",
        accepted_evidence_refs=["src/api/users.py:list_users", "tests/test_users.py::test_pagination"],
        do_not_redo=["baseline pagination call mapping"],
        stop_boundary="Stop for contract, judgment, investigation, stalled, scope, or safety blockers.",
    )
    current = {"work_units": [unit], "executions": []}
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
    assert packet["interfaces"] == {
        "interfaces": ["public API users.list"],
        "invariants": ["existing pagination behavior remains stable"],
        "decision_boundary": "Escalate any public API behavior change to the main session.",
    }
    assert packet["constraints"]["accepted_evidence_refs"] == [
        "src/api/users.py:list_users",
        "tests/test_users.py::test_pagination",
    ]
    assert packet["constraints"]["do_not_redo"] == ["baseline pagination call mapping"]
    assert packet["constraints"]["delegation_boundary"] == "Do not create or control further subagents."
    assert packet["constraints"]["stop_boundary"].startswith("Stop for contract")


def test_managed_assignment_rejects_persisted_work_unit_without_responsibility_context():
    managed = load_module("pre_host_managed_missing", "managed_execution_v4.py")
    current = {
        "work_units": [
            {
                "unit_id": "U1",
                "intent": "inspect",
                "goal": "trace contract",
                "output": "evidence",
                "depends_on": [],
                "state": "EXECUTING",
                "ownership": {"write": [], "forbidden": []},
                "authority_ceiling": "none",
                "write_scope_ceiling": [],
                "done_when": "evidence exists",
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

    with pytest.raises(managed.ManagedExecutionContractError, match="responsibility context"):
        managed.assignment_packet(current, execution=execution)


def test_managed_profiles_request_leaf_collaboration_posture():
    policy = json.loads((ROOT / "contracts" / "policy.json").read_text(encoding="utf-8"))
    for role, spec in policy["roles"].items():
        profile = tomllib.loads(
            (ROOT / "agent-profiles" / spec["profile_file"]).read_text(encoding="utf-8")
        )
        assert profile["agents"]["enabled"] is False, role
        assert profile["features"]["multi_agent_v2"] is False, role
        assert "create further subagents" in profile["developer_instructions"].lower(), role


def test_machine_contracts_keep_profile_intent_separate_from_host_truth():
    architecture = json.loads(
        (ROOT / "docs" / "v4" / "architecture.json").read_text(encoding="utf-8")
    )
    orchestrate = json.loads(
        (ROOT / "docs" / "v4" / "orchestrate.json").read_text(encoding="utf-8")
    )

    assert architecture["host_capability_requirements"] == [
        "spawn",
        "observe",
        "wait_or_wakeup",
        "followup",
        "interrupt",
        "fresh_context_spawn",
    ]
    assert architecture["managed_profile_requirements"] == [
        "fixed_profile_route",
        "behavioral_leaf_boundary",
        "host_evidence_for_managed_no_descendant_behavior",
        "host_evidence_for_effective_read_only_when_required",
    ]
    assert architecture["host_truth"] == {
        "capacity_owner": "codex_host",
        "child_identity_owner": "codex_host",
        "lifecycle_owner": "codex_host",
        "materialization_owner": "codex_host",
        "managed_child_collaboration_surface_owner": "codex_host",
        "effective_permission_owner": "codex_host",
    }
    assert orchestrate["host_execution"] == "native_host_only"
    assert orchestrate["lifecycle_authority"] == "codex_host"
    assert orchestrate["child_collaboration_policy"] == "main_only_managed_dispatch"
    assert orchestrate["managed_child_depth_policy"] == "behavioral_leaf_with_host_observed_no_descendant"


def test_rc3_integrity_closure_is_history_not_active_contract():
    assert not (ROOT / "contracts" / "rc3-integrity-closure.md").exists()
    assert (ROOT / "docs" / "history" / "rc3-integrity-closure.md").is_file()
