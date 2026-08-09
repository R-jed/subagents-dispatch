from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "skills" / "dispatch" / "references"


def test_explicit_invocation_can_cover_first_required_final_review():
    final_review = (REFERENCES / "final-review.md").read_text().lower()
    guardrails = (REFERENCES / "guardrails.md").read_text().lower()
    assert "fresh review after explicit `/dispatch`" in final_review
    assert "normal bounded orchestration envelope" in final_review
    assert "child count by itself is not a consent trigger" in guardrails
    assert "material compute expansion" in guardrails


def test_implicit_invocation_is_disabled_instead_of_needing_extra_consent_policy():
    openai = (
        ROOT
        / "skills"
        / "dispatch"
        / "agents"
        / "openai.yaml"
    ).read_text()
    guardrails = (REFERENCES / "guardrails.md").read_text()
    assert "allow_implicit_invocation: false" in openai
    assert "supported user entrypoint is explicit `/dispatch`" in guardrails
    assert "Exact task and control forms are owned by `interaction.md`" in guardrails
    assert "Explicit invocation only" in guardrails


def test_declined_required_review_remains_incomplete():
    final_review = (REFERENCES / "final-review.md").read_text().lower()
    assert "user declines" in final_review
    assert "independent assurance remains incomplete" in final_review
    assert "do not silently downgrade" in final_review


def test_repeated_final_review_cycles_remain_compute_consent_bounded():
    final_review = (REFERENCES / "final-review.md").read_text().lower()
    guardrails = (REFERENCES / "guardrails.md").read_text().lower()
    assert "repeated correction/re-review loops" in final_review
    assert "material compute expansion" in final_review
    assert "repeated expensive solver, advisor, investigator" in guardrails
