from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "dispatch"
SKILL = SKILL_ROOT / "SKILL.md"
CONTRACTS = ROOT / "contracts"
INTERACTION = CONTRACTS / "interaction.md"
HANDOFF = CONTRACTS / "handoff.md"
RECOVERY = CONTRACTS / "recovery.md"
GUARDRAILS = CONTRACTS / "guardrails.md"
TEAM_PLAN = CONTRACTS / "team-plan.md"
CASES = ROOT / "evals" / "interaction-cases.json"


def cases() -> dict[str, dict]:
    payload = json.loads(CASES.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.0"
    assert payload["suite"] == "subagents-dispatch-interaction-contract"
    result = {case["id"]: case for case in payload["cases"]}
    assert len(result) == len(payload["cases"])
    return result


def test_explicit_control_skills_reference_the_shared_interaction_contract():
    for skill_id in ["preview", "status", "steer", "takeover"]:
        text = (ROOT / "skills" / skill_id / "SKILL.md").read_text(encoding="utf-8")
        assert f"name: {skill_id}\n" in text
        assert "../../contracts/interaction.md" in text
    assert "without creating another Agent runtime" in INTERACTION.read_text(encoding="utf-8")


def test_preview_is_strictly_non_executing_and_preserves_visible_obligations():
    text = INTERACTION.read_text(encoding="utf-8").lower()
    for phrase in [
        "child spawn        forbidden",
        "agent provisioning forbidden",
        "source mutation    forbidden",
        "external action    forbidden",
        "persistent teamplan creation forbidden",
        "it is provisional",
        "preserve the material obligations already visible",
        "main-owned integration/verification seam",
        "do not create a requirement ledger",
    ]:
        assert phrase in text

    expected = cases()["preview-never-spawns-or-mutates"]["expected"]
    assert expected == {
        "mode": "preview",
        "spawn_children": False,
        "provision_agents": False,
        "mutate_source": False,
        "external_action": False,
        "plan_is_provisional": True,
    }

    coverage = cases()["preview-preserves-visible-material-obligations"]["expected"]
    assert coverage == {
        "mode": "preview",
        "material_obligation_preserved": True,
        "visible_seam_owned": True,
        "main_owned_seam_allowed": True,
        "create_requirement_ledger": False,
        "spawn_decorative_child": False,
        "plan_is_provisional": True,
    }


def test_first_use_auto_provisions_only_clean_absence_then_requires_fresh_task():
    skill = SKILL.read_text(encoding="utf-8")
    guardrails = GUARDRAILS.read_text(encoding="utf-8")
    assert "../../contracts/guardrails.md" in skill
    assert "enter `RESTART_REQUIRED` without attempting `spawn_agent`" in guardrails
    assert "Routine first-use provisioning is not a separate consent prompt" in guardrails
    assert "`RESTART_REQUIRED` is a pre-dispatch readiness outcome" in guardrails
    assert "Do not overwrite or repair that state under routine first-use authority" in guardrails

    clean = cases()["first-use-clean-absence-auto-provisions-then-restarts"]["expected"]
    assert clean == {
        "routine_provisioning": True,
        "separate_provisioning_prompt": False,
        "run_installer": True,
        "run_installer_check": True,
        "readiness_outcome": "RESTART_REQUIRED",
        "spawn_children_current_task": False,
        "fresh_task_required": True,
    }

    exact = cases()["first-use-exact-profiles-but-role-unavailable-restarts-without-spawn"]["expected"]
    assert exact["routine_provisioning"] is False
    assert exact["readiness_outcome"] == "RESTART_REQUIRED"
    assert exact["spawn_children_current_task"] is False

    conflict = cases()["first-use-conflicting-managed-state-requires-user-action"]["expected"]
    assert conflict == {
        "routine_overwrite": False,
        "readiness_outcome": "USER_ACTION_REQUIRED",
        "spawn_children_current_task": False,
        "doctor_guidance": True,
    }


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

    task_case = cases()["status-page-task-is-not-control-status"]["expected"]
    assert task_case == {"mode": "task", "status_control": False}


def test_targetless_control_resolves_only_one_eligible_unit():
    text = INTERACTION.read_text(encoding="utf-8")
    assert "exactly one eligible unit" in text
    assert "return the eligible unit ids as candidates" in text

    one = cases()["targetless-control-one-eligible-auto-resolves"]["expected"]
    assert one == {"target_resolved": True, "resolved_unit": "U2", "requires_choice": False}
    many = cases()["targetless-control-multiple-eligible-requires-choice"]["expected"]
    assert many == {"target_resolved": False, "candidates": ["U1", "U2"], "requires_choice": True}
    interrupted = cases()["steer-interrupted-is-not-resume"]["expected"]
    assert interrupted["resume_claimed"] is False
    assert interrupted["replacement_children"] == 0


def test_steering_preserves_responsibility_role_and_authority():
    text = INTERACTION.read_text(encoding="utf-8")
    for phrase in [
        "same responsibility, role, task attempt, authority, and ownership",
        "must not silently change",
        "do not label it steering",
    ]:
        assert phrase in text

    expected = cases()["steer-preserves-responsibility-and-authority"]["expected"]
    assert expected["same_unit"] is True
    assert expected["same_attempt"] is True
    assert expected["same_role"] is True
    assert expected["authority_expands"] is False

    rejected = cases()["steer-cannot-hide-material-scope-change"]["expected"]
    assert rejected["requires_main_reclassification"] is True
    assert rejected["silent_authority_expansion"] is False


def test_takeover_is_main_takeover_and_never_steals_an_unknown_writer():
    interaction = INTERACTION.read_text(encoding="utf-8")
    recovery = RECOVERY.read_text(encoding="utf-8")
    guardrails = GUARDRAILS.read_text(encoding="utf-8")

    assert "existing `main_takeover` recovery action" in interaction
    assert "user explicitly requests takeover" in recovery
    assert "previous writing owner is confirmed stopped/terminal/closed" in recovery
    assert "`UNKNOWN` is not sufficient evidence for ownership transfer" in guardrails

    running = cases()["takeover-running-writer-settles-old-owner-first"]["expected"]
    assert running["request_native_stop"] is True
    assert running["main_write_before_stop_confirmation"] is False
    assert running["preserve_one_writer"] is True

    unknown = cases()["takeover-unknown-owner-does-not-force-transfer"]["expected"]
    assert unknown["ownership_transferred"] is False
    assert unknown["main_conflicting_write"] is False
    assert unknown["reported_state"] == "UNKNOWN"


def test_receipt_is_compact_factual_and_only_after_real_delegation():
    interaction = INTERACTION.read_text(encoding="utf-8")
    assert "unique stable event references" in interaction
    assert "Explicit Dispatch with zero materialized children emits the minimal receipt" in interaction
    assert "does not estimate token counts or currency cost" in interaction

    delegated = cases()["receipt-after-materialized-delegation"]["expected"]
    assert delegated["receipt"] is True
    assert delegated["axes"] == ["Dispatch", "Review"]

    zero = cases()["zero-child-dispatch-has-minimal-receipt"]["expected"]
    assert zero == {"receipt": True, "minimal_lines": 2, "persistent_state": False}

    telemetry = cases()["receipt-never-guesses-model-or-cost"]["expected"]
    assert telemetry == {
        "claim_observed_model": False,
        "estimate_tokens": False,
        "estimate_currency_cost": False,
    }


def test_handoff_capsule_contains_only_main_accepted_truth_and_cannot_grant_authority():
    handoff = HANDOFF.read_text(encoding="utf-8")
    router = (CONTRACTS / "routing.md").read_text(encoding="utf-8")
    for phrase in [
        "Only facts Main has independently accepted",
        "A child assertion is not an accepted fact",
        "Do not pass child-to-child claims directly as settled truth",
        "A capsule cannot grant",
        "STALE IF",
    ]:
        assert phrase in handoff
    assert "Only after that verification may Main promote supported facts/evidence into a Handoff Capsule" in router

    accepted = cases()["handoff-capsule-promotes-only-accepted-evidence"]["expected"]
    assert accepted["claim_in_accepted_facts"] is False
    assert accepted["verified_fact_may_enter_capsule"] is True
    assert accepted["raw_child_transcript_forwarded"] is False

    stale = cases()["handoff-capsule-invalidates-on-relevant-drift"]["expected"]
    assert stale["capsule_still_authoritative"] is False
    assert stale["narrow_reverification_required"] is True

    authority = cases()["handoff-capsule-does-not-grant-write-authority"]["expected"]
    assert authority["source_write_allowed"] is False
    assert authority["capsule_can_expand_authority"] is False


def test_takeover_and_capsules_fit_existing_teamplan_contract():
    text = TEAM_PLAN.read_text(encoding="utf-8")
    assert "TeamPlan does not define a `main` role" in text
    assert "A pure Main takeover also does not invent `role: main` or require a revision" in (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    assert "A taken-over unit becomes dependency-satisfied only after Main completes and accepts" in text
    assert "A Handoff Capsule may carry already-accepted evidence" in text
    assert "python scripts/validate_team_plan.py" in text
    assert "plugins/subagents-dispatch" not in text
