import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
WORKLOADS = ROOT / "evals" / "behavioral-workloads.json"
RESULT_SCHEMA = ROOT / "evals" / "behavioral-result.schema.json"


def cases() -> dict[str, dict]:
    payload = json.loads(WORKLOADS.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "4.0"
    return {item["id"]: item for item in payload["workloads"]}


def test_behavioral_suite_covers_required_final_review_and_process_history_negative_control():
    by_id = cases()

    public = by_id["public-contract-final-review-required"]["expected"]
    assert public["review_requirement"] == "required"
    assert public["review_reason"] == "public_contract_change"
    assert public["fresh_sol_required"] is True
    assert public["ship_required"] is True

    negative = by_id["process-history-does-not-force-review"]["expected"]
    assert negative["review_requirement"] == "not_required"


def test_behavioral_suite_covers_verification_gap_and_sol_main_independence():
    by_id = cases()
    gap = by_id["verification-gap-final-review-required"]["expected"]
    sol_main = by_id["sol-main-still-needs-independent-review"]["expected"]
    assert gap["review_requirement"] == "required"
    assert gap["review_reason"] == "verification_gap"
    assert gap["fresh_sol_required"] is True
    assert sol_main["main_judgment_coverage"] == "covered"
    assert sol_main["fresh_sol_required"] is True
    assert sol_main["independence_required"] is True


def test_behavioral_suite_covers_verdict_invalidation_lifecycle():
    by_id = cases()
    fix_first = by_id["fix-first-invalidates-old-review"]["expected"]
    mutation = by_id["post-review-mutation-invalidates-ship"]["expected"]

    assert fix_first["old_verdict_valid"] is False
    assert fix_first["fresh_rereview_required"] is True
    assert mutation["old_verdict_valid"] is False
    assert mutation["artifact_verify_must_fail"] is True
    assert mutation["fresh_rereview_required"] is True


def test_behavioral_result_schema_supports_final_review_metrics():
    schema = json.loads(RESULT_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    props = schema["properties"]["runs"]["items"]["properties"]

    for field in [
        "final_review_requirement",
        "final_review_trigger_reasons",
        "final_review_attempts",
        "final_review_verdict",
        "final_review_gate_satisfied",
        "review_artifact_verify_failures",
        "post_review_mutations",
    ]:
        assert field in props

    assert "adaptive_routing_v4_final_review" in props["mode"]["enum"]
    assert props["final_review_requirement"]["enum"] == [None, "not_required", "required"]
    assert props["final_review_verdict"]["enum"] == [
        None,
        "ship",
        "fix-first",
        "rethink",
        "insufficient_evidence",
        "incomplete",
        "declined",
    ]
