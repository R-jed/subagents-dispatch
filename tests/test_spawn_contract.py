import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "dispatch" / "SKILL.md"
GUARDRAILS = ROOT / "contracts" / "guardrails.md"
RECOVERY = ROOT / "contracts" / "recovery.md"
INTERACTION = ROOT / "contracts" / "interaction.md"
RECEIPT = ROOT / "contracts" / "receipt.md"
CASES = ROOT / "evals" / "interaction-cases.json"
WORKLOADS = ROOT / "evals" / "behavioral-workloads.json"


def by_id(path: Path, key: str) -> dict[str, dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {item["id"]: item for item in payload[key]}


def test_project_child_spawn_requires_explicit_fresh_context_before_tool_call():
    skill = SKILL.read_text(encoding="utf-8")
    guardrails = GUARDRAILS.read_text(encoding="utf-8")

    assert "../../contracts/guardrails.md" in skill

    for phrase in [
        "new project child + exact project agent_type -> fork_turns: none",
        "Full-history (`all`) and omitted `fork_turns` are forbidden for project children",
        "correct it before invoking the Host",
    ]:
        assert phrase in guardrails

    expected = by_id(CASES, "cases")["custom-role-spawn-requires-fork-turns-none"]["expected"]
    assert expected == {
        "spawn_call_valid": False,
        "required_fork_turns": "none",
        "full_history_allowed": False,
        "omitted_fork_turns_allowed": False,
    }


def test_pre_child_spawn_rejection_does_not_create_attempt_or_receipt_retry():
    recovery = RECOVERY.read_text(encoding="utf-8")
    receipt = RECEIPT.read_text(encoding="utf-8")
    guardrails = GUARDRAILS.read_text(encoding="utf-8")

    for phrase in [
        "an Agent attempt begins only after the Host accepts the spawn and returns an inspectable child identity",
        "no attempt-budget consumption",
        "no receipt retry increment",
        "A pre-attempt spawn rejection is not `same_role_retry`",
    ]:
        assert phrase in recovery

    assert "pre-attempt spawn rejection" in guardrails
    assert "does not consume the two-attempt recovery budget" in guardrails
    assert "Recovery retry increments only when a confirmed materialized Agent attempt is replaced" in receipt
    assert "A pre-child spawn rejection is never a retry" in receipt

    expected = by_id(CASES, "cases")["pre-child-spawn-rejection-does-not-count-as-retry"]["expected"]
    assert expected == {
        "materialized_agent_attempts": 1,
        "retry_count": 0,
        "receipt_retry": "no_retry",
        "consume_attempt_budget_on_rejection": False,
    }


def test_live_host_workload_freezes_the_real_spawn_regression():
    workload = by_id(WORKLOADS, "workloads")["dispatch-custom-role-fresh-context-spawn"]
    expected = workload["expected"]

    assert workload["category"] == "interaction_spawn_context"
    assert expected["first_spawn_agent_type"] == "subagents_dispatch_reader"
    assert expected["first_spawn_fork_turns"] == "none"
    assert expected["full_history_spawn_calls"] == 0
    assert expected["omitted_fork_turns_calls"] == 0
    assert expected["pre_child_rejections_count_as_agent_attempt"] is False
    assert expected["pre_child_rejections_increment_receipt_retry"] is False
