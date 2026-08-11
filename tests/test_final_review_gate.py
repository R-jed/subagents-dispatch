from pathlib import Path
import json
import tomllib

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT
SKILL = PLUGIN / "skills" / "dispatch"
CONTRACTS = PLUGIN / "contracts"
PROFILES = PLUGIN / "agent-profiles"
POLICY = CONTRACTS / "policy.json"


def contract():
    return json.loads(POLICY.read_text(encoding="utf-8"))


def test_final_review_is_linked_and_semantically_triggered():
    skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    review = (CONTRACTS / "final-review.md").read_text(encoding="utf-8")
    assert "../../contracts/final-review.md" in skill
    assert "Candidate Ready" in review
    assert "requested deliverable is complete enough for acceptance" in review
    assert "semantic coverage closure" in review
    assert "For Git-backed deliverables" in review
    assert "For a non-Git deliverable" in review
    assert "deterministic SHA-256 digest" in review
    assert "Do not hash a summary" in review
    assert "Process history" in review
    for trigger in contract()["final_review"]["trigger_codes"]:
        assert trigger in review


def test_current_advisor_route_matches_policy_and_is_fresh():
    spec = contract()["roles"]["advisor"]
    advisor = tomllib.loads((PROFILES / spec["profile_file"]).read_text(encoding="utf-8"))
    review = (CONTRACTS / "final-review.md").read_text(encoding="utf-8")
    assert "agent_type: subagents_dispatch_advisor" in review
    assert "fork_turns: none" in review
    assert advisor["name"] == spec["agent_type"]
    assert advisor["model"] == spec["model"]
    assert advisor["model_reasoning_effort"] == spec["effort"]
    assert "sandbox_mode" not in advisor
    assert spec["mutation_authority"] == "none"


def test_review_lifecycle_remains_fail_closed_and_artifact_bound():
    review = (CONTRACTS / "final-review.md").read_text(encoding="utf-8")
    for phrase in [
        "review_artifact_id",
        "review-artifact.py",
        "ship",
        "fix-first",
        "rethink",
        "INSUFFICIENT_EVIDENCE",
        "Any deliverable mutation after review invalidates the old verdict",
    ]:
        assert phrase in review
    final_review = contract()["final_review"]
    assert final_review["ship_verdict"] == "ship"
    assert final_review["correction_verdicts"] == ["fix-first", "rethink"]
    assert final_review["unresolved_verdict"] == "insufficient_evidence"


def test_sol_review_is_selective_outside_required_assurance():
    router = (CONTRACTS / "routing.md").read_text(encoding="utf-8").lower()
    review = (CONTRACTS / "final-review.md").read_text(encoding="utf-8").lower()
    assert "final review" in router
    assert "candidate" in router and "independent second judgment" in router
    assert "process history" in review
    assert "not a trigger by itself" in review
