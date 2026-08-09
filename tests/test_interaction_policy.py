from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "dispatch"
SKILL = SKILL_ROOT / "SKILL.md"
INTERACTION = SKILL_ROOT / "references" / "interaction.md"
HANDOFF = SKILL_ROOT / "references" / "handoff-capsule.md"
RECOVERY = SKILL_ROOT / "references" / "recovery.md"
GUARDRAILS = SKILL_ROOT / "references" / "guardrails.md"
TEAM_PLAN = SKILL_ROOT / "references" / "team-plan.md"
CASES = ROOT / "evals" / "interaction-cases.json"


def cases() -> dict[str, dict]:
    payload = json.loads(CASES.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.0"
    assert payload["suite"] == "subagents-dispatch-interaction-contract"
    result = {case["id"]: case for case in payload["cases"]}
    assert len(result) == len(payload["cases"])
    return result


def test_skill_exposes_control_intents_without_implicit_orchestration():
    text = SKILL.read_text(encoding="utf-8")
    for form in ["$dispatch preview <task>", "$dispatch status", "$dispatch steer <unit_id>: <guidance>", "$dispatch takeover <unit_id>"]:
        assert form in text
    assert "Handle an explicit control intent before ordinary routing" in text
    assert "Preview performs no delegated execution or mutation" in text
    assert "bare `/dispatch` slash command is not part of this Plugin contract" in text


def test_preview_is_strictly_non_executing():
    text = INTERACTION.read_text(encoding="utf-8").lower()
    for phrase in ["child spawn        forbidden", "agent provisioning forbidden", "source mutation    forbidden", "external action    forbidden", "persistent teamplan creation forbidden", "it is provisional"]:
        assert phrase in text
    expected = cases()["preview-never-spawns-or-mutates"]["expected"]
    assert expected == {"mode": "preview", "spawn_children": False, "provision_agents": False, "mutate_source": False, "external_action": False, "plan_is_provisional": True}


def test_first_use_auto_provisions_only_clean_absence_then_requires_fresh_task():
    skill = SKILL.read_text(encoding="utf-8")
    guardrails = GUARDRAILS.read_text(encoding="utf-8")
    assert "readiness outcome: RESTART_REQUIRED" in skill
    assert "do not attempt spawn_agent in this task" in skill
    assert "Routine first-use provisioning is not a separate consent prompt" in guardrails
    assert "`RESTART_REQUIRED` is a pre-dispatch readiness outcome" in guardrails
    assert "Do not overwrite or repair that state under routine first-use authority" in guardrails
    clean = cases()["first-use-clean-absence-auto-provisions-then-restarts"]["expected"]
    assert clean["routine_provisioning"] is True
    assert clean["separate_provisioning_prompt"] is False
    assert clean["readiness_outcome"] == "RESTART_REQUIRED"
    assert clean["spawn_children_current_task"] is False
    exact = cases()["first-use-exact-profiles-but-role-unavailable-restarts-without-spawn"]["expected"]
    assert exact["readiness_outcome"] == "RESTART_REQUIRED"
    conflict = cases()["first-use-conflicting-managed-state-requires-user-action"]["expected"]
    assert conflict["routine_overwrite"] is False
    assert conflict["readiness_outcome"] == "USER_ACTION_REQUIRED"


def test_status_preserves_unknown_and_does_not_busy_poll():
    text = INTERACTION.read_text(encoding="utf-8")
    assert "one-shot state inspection" in text
    assert "Do not busy-poll" in text
    assert "report `UNKNOWN` exactly" in text
    expected = cases()["status-is-one-shot-and-preserves-unknown"]["expected"]
    assert expected["poll_loop"] is False
    assert expected["reported_state"] == "UNKNOWN"
    assert expected["retry"] is False
    assert expected["replacement_work"] is False
    assert cases()["status-page-task-is-not-control-status"]["expected"] == {"mode": "task", "status_control": False}


def test_steering_preserves_responsibility_role_and_authority():
    text = INTERACTION.read_text(encoding="utf-8")
    for phrase in ["same responsibility, role, task attempt, authority, and ownership", "must not silently change", "do not label it steering"]:
        assert phrase in text
    expected = cases()["steer-preserves-responsibility-and-authority"]["expected"]
    assert expected["same_unit"] is True
    assert expected["same_attempt"] is True
    assert expected["same_role"] is True
    assert expected["authority_expands"] is False
    rejected = cases()["steer-cannot-hide-material-scope-change"]["expected"]
    assert rejected["requires_main_reclassification"] is True


def test_takeover_is_main_takeover_and_never_steals_an_unknown_writer():
    interaction = INTERACTION.read_text(encoding="utf-8")
    recovery = RECOVERY.read_text(encoding="utf-8")
    guardrails = GUARDRAILS.read_text(encoding="utf-8")
    assert "existing `main_takeover` recovery action" in interaction
    assert "user explicitly requests takeover" in recovery
    assert "previous writing owner is confirmed stopped/terminal/closed" in recovery
    assert "`UNKNOWN` is not sufficient evidence for ownership transfer" in guardrails
    running = cases()["takeover-running-writer-settles-old-owner-first"]["expected"]
    assert running["main_write_before_stop_confirmation"] is False
    assert running["preserve_one_writer"] is True
    unknown = cases()["takeover-unknown-owner-does-not-force-transfer"]["expected"]
    assert unknown["ownership_transferred"] is False
    assert unknown["reported_state"] == "UNKNOWN"


def test_receipt_is_compact_factual_and_only_after_real_delegation():
    interaction = INTERACTION.read_text(encoding="utf-8")
    guardrails = GUARDRAILS.read_text(encoding="utf-8")
    assert "When at least one child was actually spawned" in interaction
    assert "Do not emit the receipt for a zero-child task, preview, or status-only request" in interaction
    assert "Keep the default receipt to one line" in guardrails
    assert "does not estimate token counts or currency cost" in interaction
    assert cases()["receipt-only-after-real-delegation"]["expected"]["receipt"] is True
    assert cases()["zero-child-completion-has-no-receipt"]["expected"]["receipt"] is False
    telemetry = cases()["receipt-never-guesses-model-or-cost"]["expected"]
    assert telemetry == {"claim_observed_model": False, "estimate_tokens": False, "estimate_currency_cost": False}


def test_handoff_capsule_contains_only_main_accepted_truth_and_cannot_grant_authority():
    handoff = HANDOFF.read_text(encoding="utf-8")
    router = (SKILL_ROOT / "references" / "router-core.md").read_text(encoding="utf-8")
    for phrase in ["Only facts Main has independently accepted", "A child assertion is not an accepted fact", "Do not pass child-to-child claims directly as settled truth", "A capsule cannot grant", "STALE IF"]:
        assert phrase in handoff
    assert "Only after that verification may Main promote supported facts/evidence into a Handoff Capsule" in router
    accepted = cases()["handoff-capsule-promotes-only-accepted-evidence"]["expected"]
    assert accepted["claim_in_accepted_facts"] is False
    assert accepted["verified_fact_may_enter_capsule"] is True
    authority = cases()["handoff-capsule-does-not-grant-write-authority"]["expected"]
    assert authority["capsule_can_expand_authority"] is False


def test_takeover_and_capsules_fit_existing_teamplan_contract():
    text = TEAM_PLAN.read_text(encoding="utf-8")
    assert "TeamPlan does not define a `main` role" in text
    assert "A pure Main takeover also does not invent `role: main` or require a revision" in (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    assert "A taken-over unit becomes dependency-satisfied only after Main completes and accepts" in text
    assert "A Handoff Capsule may carry already-accepted evidence" in text
    assert "python scripts/validate_team_plan.py" in text
