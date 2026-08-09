from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT
SCRIPTS = PLUGIN / "scripts"
POLICY = PLUGIN / "contracts" / "policy.json"
RECOVERY = PLUGIN / "contracts" / "recovery.md"
LEDGER_SCRIPT = SCRIPTS / "validate_team_ledger.py"


def load_ledger_validator():
    sys.path.insert(0, str(SCRIPTS))
    try:
        spec = importlib.util.spec_from_file_location("subagents_dispatch_team_ledger", LEDGER_SCRIPT)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPTS))


VALIDATOR = load_ledger_validator()


def attempt(
    *,
    unit_id="U1",
    revision=None,
    task_id="task-1",
    attempt_no=1,
    agent_type="subagents_dispatch_reader",
    agent_id="agent-1",
    state="COMPLETED",
    followups=0,
    adopted=True,
    accepted=None,
    failure_origin="none",
    task_blocker="none",
):
    return {
        "unit_id": unit_id,
        "team_plan_revision": revision,
        "task_id": task_id,
        "attempt": attempt_no,
        "agent_type": agent_type,
        "agent_id": agent_id,
        "control_state": state,
        "followup_count": followups,
        "adopted": adopted,
        "accepted": adopted if accepted is None else accepted,
        "failure_origin": failure_origin,
        "task_blocker": task_blocker,
    }


def plan():
    return {
        "schema_version": "1.0",
        "revision": 1,
        "supersedes_revision": None,
        "planning_source": "ad_hoc",
        "source_refs": [],
        "root_goal": "deliver result",
        "units": [
            {
                "unit_id": "U1",
                "role": "reader",
                "goal": "read",
                "output": "evidence",
                "depends_on": [],
                "ownership": {"write": [], "forbidden": []},
                "done_when": "evidence complete",
            },
            {
                "unit_id": "U2",
                "role": "worker",
                "goal": "write",
                "output": "change",
                "depends_on": ["U1"],
                "ownership": {"write": ["src/example.py"], "forbidden": []},
                "done_when": "verified",
            },
        ],
        "integration_owner": "main",
        "integration_order": ["U1", "U2"],
        "final_verification": "Main verifies combined artifact",
        "revision_reason": "initial",
    }


def validate(payload):
    return VALIDATOR.validate_team_ledger_payload(payload)


def single_ledger(record=None):
    return {
        "schema_version": "1.0",
        "team_plans": [],
        "active_team_plan_revision": None,
        "attempts": [record or attempt()],
    }


def test_ledger_derives_role_agent_bindings_from_policy_contract():
    roles = json.loads(POLICY.read_text())["roles"]
    assert VALIDATOR.ROLE_AGENT_TYPES == {role: spec["agent_type"] for role, spec in roles.items()}


def test_recovery_contract_owns_lifecycle_blockers_and_bounds():
    text = RECOVERY.read_text(encoding="utf-8")
    assert VALIDATOR.FAILURE_ORIGINS == {
        "none",
        "runtime_unavailable",
        "permission_failure",
        "tool_failure",
        "timeout",
        "quality_failure",
        "runtime_ambiguous",
    }
    assert VALIDATOR.TASK_BLOCKERS == {"none", "contract", "judgment", "investigation", "stalled"}
    for phrase in [
        "UNKNOWN is not failure",
        "2 Agent attempts",
        "1 focused follow-up",
        "same_agent_followup",
        "same_role_retry",
        "semantic_reroute",
        "main_takeover",
        "Failure itself never means Luna -> Terra -> Sol",
    ]:
        assert phrase in text
    for state in VALIDATOR.CONTROL_STATES:
        assert state in text


def test_single_child_ledger_does_not_require_team_plan():
    result = validate(single_ledger())
    assert result["ledger_valid"] is True
    assert result["unit_count"] == 1


def test_ledger_shape_and_identity_fail_closed():
    payload = single_ledger()
    payload["unexpected"] = True
    assert any("unsupported fields" in error for error in validate(payload)["errors"])

    payload = single_ledger()
    payload["attempts"][0]["unexpected"] = True
    assert any("unsupported fields" in error for error in validate(payload)["errors"])

    payload = single_ledger()
    payload["attempts"].append(
        attempt(task_id="task-1", attempt_no=2, agent_id="agent-1", state="RUNNING", adopted=False)
    )
    errors = validate(payload)["errors"]
    assert any("duplicates task_id" in error for error in errors)
    assert any("duplicates agent_id" in error for error in errors)


def test_malformed_enum_and_attempt_values_fail_closed_instead_of_crashing():
    payload = single_ledger(attempt(state=["COMPLETED"], adopted=False))
    assert any("invalid control_state" in error for error in validate(payload)["errors"])

    payload = single_ledger(attempt(failure_origin=["none"]))
    assert any("invalid failure_origin" in error for error in validate(payload)["errors"])

    payload = single_ledger(attempt(task_blocker=["none"]))
    assert any("invalid task_blocker" in error for error in validate(payload)["errors"])

    payload = single_ledger(attempt(attempt_no="1"))
    payload["attempts"].append(
        attempt(task_id="task-2", attempt_no=2, agent_id="agent-2", state="RUNNING", adopted=False)
    )
    assert any("attempt must be 1 or 2" in error for error in validate(payload)["errors"])


def test_multiple_units_require_team_plan_and_policy_role_binding():
    payload = {
        "schema_version": "1.0",
        "team_plans": [],
        "active_team_plan_revision": None,
        "attempts": [attempt(), attempt(unit_id="U2", task_id="task-2", agent_id="agent-2")],
    }
    assert "multiple delegated units require TeamPlan binding" in validate(payload)["errors"]

    payload = {
        "schema_version": "1.0",
        "team_plans": [plan()],
        "active_team_plan_revision": 1,
        "attempts": [
            attempt(revision=1),
            attempt(unit_id="U2", revision=1, task_id="task-2", agent_type="subagents_dispatch_worker", agent_id="agent-2"),
        ],
    }
    assert validate(payload)["ledger_valid"] is True
    payload["attempts"][1]["agent_type"] = "subagents_dispatch_reader"
    assert any("does not match TeamPlan role" in error for error in validate(payload)["errors"])


def test_unknown_is_not_failure_and_blocks_replacement():
    unknown = attempt(
        agent_id=None,
        state="UNKNOWN",
        adopted=False,
        failure_origin="runtime_ambiguous",
    )
    payload = single_ledger(unknown)
    assert validate(payload)["ledger_valid"] is True

    payload["attempts"].append(
        attempt(task_id="task-2", attempt_no=2, agent_id="agent-2", state="RUNNING", adopted=False)
    )
    assert any("UNKNOWN attempt forbids a replacement attempt" in error for error in validate(payload)["errors"])

    payload = single_ledger(unknown)
    payload["attempts"][0]["failure_origin"] = "timeout"
    assert any("UNKNOWN requires failure_origin=runtime_ambiguous" in error for error in validate(payload)["errors"])


def test_second_attempt_requires_confirmed_failure_and_bounds_remain_two():
    first = attempt(state="FAILED", adopted=False, failure_origin="quality_failure", task_blocker="stalled")
    second = attempt(task_id="task-2", attempt_no=2, agent_id="agent-2", state="RUNNING", adopted=False)
    payload = single_ledger(first)
    payload["attempts"].append(second)
    assert validate(payload)["ledger_valid"] is True

    payload = single_ledger(attempt(state="COMPLETED", adopted=False))
    payload["attempts"].append(second)
    assert any("second attempt requires the first attempt to be FAILED" in error for error in validate(payload)["errors"])

    payload = single_ledger(attempt(attempt_no=3))
    assert any("attempt must be 1 or 2" in error for error in validate(payload)["errors"])
    payload = single_ledger(attempt(followups=2))
    assert any("followup_count must be 0 or 1" in error for error in validate(payload)["errors"])


def test_failure_state_and_adoption_consistency_fail_closed():
    payload = single_ledger(attempt(state="FAILED", adopted=False, failure_origin="none"))
    assert any("FAILED requires a failure_origin" in error for error in validate(payload)["errors"])

    payload = single_ledger(attempt(state="CLOSED", adopted=False, accepted=False))
    assert validate(payload)["ledger_valid"] is True

    payload = single_ledger(attempt(state="COMPLETED", adopted=True, accepted=False))
    assert any("adopted=true requires accepted evidence" in error for error in validate(payload)["errors"])


def test_interrupted_is_nonfinal_and_keeps_the_same_materialized_attempt():
    payload = single_ledger(attempt(state="INTERRUPTED", adopted=False, accepted=False))
    assert validate(payload)["ledger_valid"] is True

    payload["attempts"].append(
        attempt(task_id="task-2", attempt_no=2, agent_id="agent-2", state="RUNNING", adopted=False)
    )
    errors = validate(payload)["errors"]
    assert any("second attempt requires the first attempt to be FAILED" in error for error in errors)


def test_role_can_change_across_plan_revision_without_resetting_unit_identity():
    first_plan = plan()
    second_plan = plan()
    second_plan["revision"] = 2
    second_plan["supersedes_revision"] = 1
    second_plan["revision_reason"] = "judgment blocker changed assigned role"
    second_plan["units"][1]["role"] = "solver"

    payload = {
        "schema_version": "1.0",
        "team_plans": [first_plan, second_plan],
        "active_team_plan_revision": 2,
        "attempts": [
            attempt(
                unit_id="U2",
                revision=1,
                agent_type="subagents_dispatch_worker",
                state="FAILED",
                adopted=False,
                failure_origin="quality_failure",
                task_blocker="judgment",
            ),
            attempt(
                unit_id="U2",
                revision=2,
                task_id="task-2",
                attempt_no=2,
                agent_type="subagents_dispatch_solver",
                agent_id="agent-2",
                state="RUNNING",
                adopted=False,
            ),
        ],
    }
    assert validate(payload)["ledger_valid"] is True


def test_same_unit_id_cannot_hide_a_changed_responsibility_across_revisions():
    first_plan = plan()
    second_plan = plan()
    second_plan["revision"] = 2
    second_plan["supersedes_revision"] = 1
    second_plan["revision_reason"] = "redefined work"
    second_plan["units"][1]["goal"] = "a different responsibility"

    payload = {
        "schema_version": "1.0",
        "team_plans": [first_plan, second_plan],
        "active_team_plan_revision": 2,
        "attempts": [],
    }
    assert any("changes goal/output across TeamPlan revisions" in error for error in validate(payload)["errors"])
