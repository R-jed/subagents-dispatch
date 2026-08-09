from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "skills" / "dispatch" / "references"


def test_explicit_skill_selection_can_cover_first_required_final_review():
    final_review = (REFERENCES / "final-review.md").read_text(encoding="utf-8").lower()
    guardrails = (REFERENCES / "guardrails.md").read_text(encoding="utf-8").lower()
    assert "fresh review after explicit user selection/invocation of subagents dispatch" in final_review
    assert "normal bounded orchestration envelope" in final_review
    assert "child count by itself is not a consent trigger" in guardrails
    assert "material compute expansion" in guardrails


def test_implicit_invocation_is_disabled_while_explicit_skill_selection_is_the_entrypoint():
    openai = (
        ROOT
        / "skills"
        / "dispatch"
        / "agents"
        / "openai.yaml"
    ).read_text(encoding="utf-8")
    guardrails = (REFERENCES / "guardrails.md").read_text(encoding="utf-8")
    assert "allow_implicit_invocation: false" in openai
    assert "supported entrypoint is explicit user selection/invocation" in guardrails
    assert "displayed as **Subagents Dispatch**" in guardrails
    assert "Exact task and control payloads are owned by `interaction.md`" in guardrails
    assert "Explicit invocation only" in guardrails


def test_declined_required_review_remains_incomplete():
    final_review = (REFERENCES / "final-review.md").read_text(encoding="utf-8").lower()
    assert "user declines" in final_review
    assert "independent assurance remains incomplete" in final_review
    assert "do not silently downgrade" in final_review


def test_repeated_final_review_cycles_remain_compute_consent_bounded():
    final_review = (REFERENCES / "final-review.md").read_text(encoding="utf-8").lower()
    guardrails = (REFERENCES / "guardrails.md").read_text(encoding="utf-8").lower()
    assert "repeated correction/re-review loops" in final_review
    assert "material compute expansion" in final_review
    assert "repeated expensive solver, advisor, investigator" in guardrails
