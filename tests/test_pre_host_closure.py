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


def host_evidence() -> dict:
    lifecycle = ["spawn_agent", "followup_task", "interrupt_agent"]
    return {
        "surface": "multi_agent_v2",
        "tools": [
            "spawn_agent",
            "send_message",
            "followup_task",
            "wait_agent",
            "list_agents",
            "interrupt_agent",
        ],
        "hooks": {
            "PreToolUse": [*lifecycle, "list_agents"],
            "PostToolUse": [*lifecycle, "list_agents"],
            "SubagentStop": True,
        },
        "fork_turns_none": True,
        "max_spawned_threads": 4,
    }


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


def test_uncovered_namespaced_lifecycle_identity_blocks_host_readiness():
    host = load_module("pre_host_caps_alias", "host_capabilities.py")
    evidence = host_evidence()
    evidence["tools"].append("collaboration.spawn_agent")

    snapshot = host.normalize_host_capabilities(evidence)

    assert snapshot["execution_ready"] is False
    assert snapshot["capabilities"]["pre_tool_use_guard"] is False
    assert snapshot["capabilities"]["post_tool_use_guard"] is False


def test_exposed_send_message_requires_exact_pre_tool_guard():
    host = load_module("pre_host_caps_peer", "host_capabilities.py")
    snapshot = host.normalize_host_capabilities(host_evidence())

    assert snapshot["execution_ready"] is False
    assert snapshot["capabilities"]["peer_message_guard"] is False
    assert "peer_message_guard" in snapshot["missing"]


def test_exact_namespaced_and_peer_coverage_can_be_execution_ready():
    host = load_module("pre_host_caps_complete", "host_capabilities.py")
    evidence = host_evidence()
    evidence["tools"].extend(
        [
            "collaboration.spawn_agent",
            "collaboration.followup_task",
            "collaboration.interrupt_agent",
            "collaboration.list_agents",
            "collaboration.send_message",
        ]
    )
    evidence["hooks"]["PreToolUse"].extend(
        [
            "send_message",
            "collaboration.spawn_agent",
            "collaboration.followup_task",
            "collaboration.interrupt_agent",
            "collaboration.list_agents",
            "collaboration.send_message",
        ]
    )
    evidence["hooks"]["PostToolUse"].extend(
        [
            "collaboration.spawn_agent",
            "collaboration.followup_task",
            "collaboration.interrupt_agent",
            "collaboration.list_agents",
        ]
    )

    snapshot = host.normalize_host_capabilities(evidence)

    assert snapshot["execution_ready"] is True
    assert snapshot["missing"] == []


def test_managed_child_peer_message_and_namespaced_lifecycle_are_blocked():
    guard = load_module("pre_host_guard", "orchestration_guard.py")
    caller = "subagents_dispatch_reader"

    peer = guard.evaluate_pre_tool_use(
        {
            "hook_event_name": "PreToolUse",
            "session_id": "root-thread",
            "tool_name": "send_message",
            "tool_use_id": "tool-peer",
            "tool_input": {"target": "/root/sibling", "message": "change direction"},
            "agent_type": caller,
        }
    )
    assert peer is not None
    assert peer["decision"] == "block"

    namespaced = guard.evaluate_pre_tool_use(
        {
            "hook_event_name": "PreToolUse",
            "session_id": "root-thread",
            "tool_name": "collaboration.spawn_agent",
            "tool_use_id": "tool-alias",
            "tool_input": {"task_name": "nested", "message": "x", "agent_type": "default"},
            "agent_type": caller,
        }
    )
    assert namespaced is not None
    assert namespaced["decision"] == "block"


def test_staged_manifest_covers_peer_message_and_known_collaboration_aliases():
    payload = json.loads((ROOT / "docs" / "v4" / "hooks.json").read_text(encoding="utf-8"))
    pre_matchers = "|".join(item["matcher"] for item in payload["hooks"]["PreToolUse"])
    post_matchers = "|".join(item["matcher"] for item in payload["hooks"]["PostToolUse"])

    for identity in (
        "spawn_agent",
        "followup_task",
        "interrupt_agent",
        "list_agents",
        "send_message",
        "collaboration.spawn_agent",
        "collaboration.followup_task",
        "collaboration.interrupt_agent",
        "collaboration.list_agents",
        "collaboration.send_message",
    ):
        assert identity.replace(".", "\\.") in pre_matchers or identity in pre_matchers

    for identity in (
        "spawn_agent",
        "followup_task",
        "interrupt_agent",
        "list_agents",
        "collaboration.spawn_agent",
        "collaboration.followup_task",
        "collaboration.interrupt_agent",
        "collaboration.list_agents",
    ):
        assert identity.replace(".", "\\.") in post_matchers or identity in post_matchers


def test_host_contract_requires_exact_identity_peer_and_assignment_semantics():
    payload = json.loads((ROOT / "docs" / "v4" / "host-smoke.json").read_text(encoding="utf-8"))
    probes = {item["id"]: item for item in payload["required_probes"]}

    assert any("identity" in value.lower() or "alias" in value.lower() for value in probes["H01"]["requires"])
    assert any("send_message" in value for value in probes["H14"]["requires"])
    assert any("interfaces" in value.lower() or "invariants" in value.lower() for value in probes["H15"]["requires"])


def test_current_docs_have_no_retired_dispatch_or_doctor_release_owner_drift():
    privacy = (ROOT / "PRIVACY.md").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    ai_index = (ROOT / "README_AI.md").read_text(encoding="utf-8")

    assert "explicit **Dispatch** Skill" not in privacy
    assert "Normal Dispatch, Preview, Status, Steer, Takeover" not in privacy
    assert "release-readiness diagnostic owner" not in changelog
    assert "Doctor --release-check" not in changelog
    for supporting_owner in (
        "contracts/guardrails.md",
        "contracts/handoff.md",
        "contracts/evidence-artifact.md",
    ):
        assert supporting_owner in ai_index


def test_rc3_integrity_closure_is_history_not_active_contract():
    assert not (ROOT / "contracts" / "rc3-integrity-closure.md").exists()
    assert (ROOT / "docs" / "history" / "rc3-integrity-closure.md").is_file()
