from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATE = ROOT / "skills" / "orchestrate" / "SKILL.md"
CONTRACTS = ROOT / "contracts"
CASES = ROOT / "evals" / "interaction-cases.json"


def cases() -> dict[str, dict]:
    payload = json.loads(CASES.read_text(encoding="utf-8"))
    return {case["id"]: case for case in payload["cases"]}


def test_orchestrate_unifies_preview_status_steer_and_takeover_without_legacy_skills():
    text = ORCHESTRATE.read_text(encoding="utf-8")
    assert "single V4 orchestration entrypoint" in text
    assert "plan-only" in text
    assert "Status, correction, takeover, cancellation, and continuation" in text
    for retired in ("dispatch", "preview", "status", "steer", "takeover"):
        assert not (ROOT / "skills" / retired).exists()


def test_plan_only_is_strictly_non_executing():
    text = ORCHESTRATE.read_text(encoding="utf-8")
    for phrase in ("without creating `active.json`", "acquiring WriterLease", "preparing PendingControl"):
        assert phrase in text
    expected = cases()["preview-never-spawns-or-mutates"]["expected"]
    assert expected["spawn_children"] is False
    assert expected["mutate_source"] is False
    assert expected["external_action"] is False


def test_status_and_target_resolution_preserve_unknown_and_ambiguity():
    interaction = (CONTRACTS / "interaction.md").read_text(encoding="utf-8")
    assert "Do not busy-poll" in interaction
    assert "report `UNKNOWN` exactly" in interaction
    status = cases()["status-is-one-shot-and-preserves-unknown"]["expected"]
    assert status["poll_loop"] is False
    assert status["reported_state"] == "UNKNOWN"
    many = cases()["targetless-control-multiple-eligible-requires-choice"]["expected"]
    assert many["requires_choice"] is True


def test_correction_preserves_scope_and_material_change_requires_reclassification():
    expected = cases()["steer-preserves-responsibility-and-authority"]["expected"]
    assert expected["same_unit"] is True
    assert expected["same_attempt"] is True
    assert expected["same_role"] is True
    assert expected["authority_expands"] is False
    changed = cases()["steer-cannot-hide-material-scope-change"]["expected"]
    assert changed["requires_main_reclassification"] is True


def test_takeover_never_transfers_unknown_writer():
    orchestrate = ORCHESTRATE.read_text(encoding="utf-8")
    assert "Interrupt acknowledgement alone never settles a writer" in orchestrate
    assert "fresh current-generation Host evidence" in orchestrate
    unknown = cases()["takeover-unknown-owner-does-not-force-transfer"]["expected"]
    assert unknown["ownership_transferred"] is False
    assert unknown["main_conflicting_write"] is False
    assert unknown["reported_state"] == "UNKNOWN"


def test_handoff_and_candidate_review_contracts_remain_evidence_bound():
    handoff = (CONTRACTS / "handoff.md").read_text(encoding="utf-8")
    review = (CONTRACTS / "final-review.md").read_text(encoding="utf-8")
    assert "Only facts Main has independently accepted" in handoff
    assert "A capsule cannot grant" in handoff
    assert "review_artifact_id" in review
    assert "Mutation invalidates" in review or "mutation" in review.lower()


def test_teamplan_dependencies_still_require_main_acceptance_after_takeover():
    text = (CONTRACTS / "team-plan.md").read_text(encoding="utf-8")
    assert "A taken-over unit becomes dependency-satisfied only after Main completes and accepts" in text
    assert "python scripts/validate_team_plan.py" in text
