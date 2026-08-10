import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "dispatch_state.py"


def load_module():
    spec = importlib.util.spec_from_file_location("dispatch_state_verification_rework", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def materialized_worker():
    return {
        "unit_id": "U1",
        "attempt": 1,
        "agent_id": "agent-1",
        "role": "worker",
        "model_lane": "Luna Max",
    }


def followup_event():
    return {
        "ref": "followup:U1:A1:F1",
        "kind": "followup",
        "unit_id": "U1",
        "attempt": 1,
        "agent_id": "agent-1",
        "activity": "execute",
    }


def test_main_verification_gap_can_bind_real_semantic_rework_without_review_round():
    module = load_module()
    artifact_id = "sha256:" + "a" * 64
    events = [
        followup_event(),
        {
            "ref": "verification-gap:pagination-test",
            "kind": "verification_gap",
            "verification_artifact_id": artifact_id,
            "oracle_ref": "pytest:tests/test_api.py::test_pagination",
        },
        {
            "ref": "rework:U1:verification-1",
            "kind": "semantic_rework",
            "unit_id": "U1",
            "attempt": 1,
            "agent_id": "agent-1",
            "verification_gap_ref": "verification-gap:pagination-test",
        },
    ]

    summary = module.account_receipt(events, materialized_units=[materialized_worker()])
    assert summary["semantic_reworks"] == 1
    assert summary["review"] == {"rounds": 0, "reworks": 1, "verdict": None}
    assert "验收: 未触发独立复核 · 返工1次" in module.format_receipt(summary, locale="zh")
    assert "Review: independent review not triggered · rework×1" in module.format_receipt(summary, locale="en")


def test_verification_gap_requires_exact_artifact_and_oracle():
    module = load_module()
    for event in [
        {"ref": "gap:missing-artifact", "kind": "verification_gap", "oracle_ref": "pytest:test"},
        {
            "ref": "gap:bad-artifact",
            "kind": "verification_gap",
            "verification_artifact_id": "candidate",
            "oracle_ref": "pytest:test",
        },
        {
            "ref": "gap:missing-oracle",
            "kind": "verification_gap",
            "verification_artifact_id": "sha256:" + "b" * 64,
        },
    ]:
        with pytest.raises(module.ReceiptAccountingError, match="exact candidate artifact and oracle_ref"):
            module.account_receipt([event], materialized_units=[materialized_worker()])


def test_semantic_rework_rejects_missing_or_multiple_gap_sources():
    module = load_module()
    artifact_id = "sha256:" + "c" * 64
    gap = {
        "ref": "verification-gap:one",
        "kind": "verification_gap",
        "verification_artifact_id": artifact_id,
        "oracle_ref": "pytest:test_one",
    }
    unbound = {
        "ref": "rework:unbound",
        "kind": "semantic_rework",
        "unit_id": "U1",
        "attempt": 1,
        "agent_id": "agent-1",
    }
    with pytest.raises(module.ReceiptAccountingError, match="exactly one bound review or verification gap"):
        module.account_receipt([followup_event(), gap, unbound], materialized_units=[materialized_worker()])

    advisor = {
        "unit_id": "U2",
        "attempt": 1,
        "agent_id": "advisor-1",
        "role": "advisor",
        "model_lane": "Sol High",
    }
    both = [
        followup_event(),
        gap,
        {
            "ref": "reviewer:U2:A1",
            "kind": "reviewer_attempt",
            "unit_id": "U2",
            "attempt": 1,
            "agent_id": "advisor-1",
            "activity": "review",
            "review_artifact_id": artifact_id,
        },
        {
            "ref": "review:U2:R1",
            "kind": "review_round",
            "unit_id": "U2",
            "attempt": 1,
            "agent_id": "advisor-1",
            "verdict": "rework_required",
            "review_artifact_id": artifact_id,
        },
        {
            "ref": "rework:both",
            "kind": "semantic_rework",
            "unit_id": "U1",
            "attempt": 1,
            "agent_id": "agent-1",
            "review_artifact_id": artifact_id,
            "verification_gap_ref": "verification-gap:one",
        },
    ]
    with pytest.raises(module.ReceiptAccountingError, match="exactly one bound review or verification gap"):
        module.account_receipt(both, materialized_units=[materialized_worker(), advisor])
