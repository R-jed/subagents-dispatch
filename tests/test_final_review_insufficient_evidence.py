from pathlib import Path
import json
import tomllib

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT
ADVISOR = PLUGIN / "agent-profiles" / "subagents-dispatch-advisor.toml"
REVIEW = PLUGIN / "contracts" / "final-review.md"
SCHEMA = ROOT / "evals" / "behavioral-result.schema.json"


def test_advisor_can_fail_closed_on_missing_evidence():
    instructions = tomllib.loads(ADVISOR.read_text())["developer_instructions"]
    assert "INSUFFICIENT_EVIDENCE" in instructions
    assert "missing dependency" in instructions


def test_review_keeps_insufficient_evidence_unresolved():
    review = REVIEW.read_text()
    assert "INSUFFICIENT_EVIDENCE" in review
    assert "Keep the candidate at review-pending" in review
    assert "This is not completion" in review
    assert "fresh review" in review


def test_behavioral_schema_records_insufficient_evidence():
    schema = json.loads(SCHEMA.read_text())
    verdicts = schema["properties"]["runs"]["items"]["properties"]["final_review_verdict"]["enum"]
    assert "insufficient_evidence" in verdicts
