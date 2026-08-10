#!/usr/bin/env python3
from pathlib import Path

STATE = Path("scripts/dispatch_state.py")
RECEIPT = Path("contracts/receipt.md")
TEST = Path("tests/test_receipt_verification_rework.py")

text = STATE.read_text(encoding="utf-8")

old_kinds = '''RECEIPT_EVENT_KINDS = {
    "attempt",
    "followup",
    "retry",
    "semantic_rework",
    "reviewer_attempt",
    "review_round",
    "control",
}
'''
new_kinds = '''RECEIPT_EVENT_KINDS = {
    "attempt",
    "followup",
    "retry",
    "verification_gap",
    "semantic_rework",
    "reviewer_attempt",
    "review_round",
    "control",
}
'''
if text.count(old_kinds) != 1:
    raise SystemExit("expected receipt kind block exactly once")
text = text.replace(old_kinds, new_kinds, 1)

old_gap = '''    gap_review_artifacts = {
        event.get("review_artifact_id")
        for event in unique
        if event["kind"] == "review_round"
        and event.get("verdict") in {"rework_required", "redesign_required"}
    }
'''
new_gap = '''    gap_review_artifacts = {
        event.get("review_artifact_id")
        for event in unique
        if event["kind"] == "review_round"
        and event.get("verdict") in {"rework_required", "redesign_required"}
    }
    verification_gaps = {
        event.get("ref"): {
            "verification_artifact_id": event.get("verification_artifact_id"),
            "oracle_ref": event.get("oracle_ref"),
        }
        for event in unique
        if event["kind"] == "verification_gap"
    }
'''
if text.count(old_gap) != 1:
    raise SystemExit("expected review gap block exactly once")
text = text.replace(old_gap, new_gap, 1)

old_rework = '''        elif kind == "semantic_rework":
            correction_key = (event.get("unit_id"), event.get("attempt"), event.get("agent_id"))
            artifact_id = event.get("review_artifact_id")
            if correction_key not in followup_event_keys or artifact_id not in gap_review_artifacts:
                raise ReceiptAccountingError(
                    f"rework event {event['ref']} requires a materialized correction and bound review gap"
                )
            if correction_key in rework_keys:
                raise ReceiptAccountingError(f"duplicate rework for event {event['ref']}")
            rework_keys.add(correction_key)
            semantic_reworks += 1
'''
new_rework = '''        elif kind == "verification_gap":
            artifact_id = event.get("verification_artifact_id")
            oracle_ref = event.get("oracle_ref")
            if (
                not isinstance(artifact_id, str)
                or REVIEW_ARTIFACT_PATTERN.fullmatch(artifact_id) is None
                or not _nonempty(oracle_ref)
            ):
                raise ReceiptAccountingError(
                    f"verification gap {event['ref']} requires an exact candidate artifact and oracle_ref"
                )
        elif kind == "semantic_rework":
            correction_key = (event.get("unit_id"), event.get("attempt"), event.get("agent_id"))
            review_artifact_id = event.get("review_artifact_id")
            verification_gap_ref = event.get("verification_gap_ref")
            review_bound = (
                isinstance(review_artifact_id, str)
                and review_artifact_id in gap_review_artifacts
            )
            verification_bound = (
                isinstance(verification_gap_ref, str)
                and verification_gap_ref in verification_gaps
            )
            if correction_key not in followup_event_keys or review_bound == verification_bound:
                raise ReceiptAccountingError(
                    f"rework event {event['ref']} requires a materialized correction and exactly one bound review or verification gap"
                )
            if correction_key in rework_keys:
                raise ReceiptAccountingError(f"duplicate rework for event {event['ref']}")
            rework_keys.add(correction_key)
            semantic_reworks += 1
'''
if text.count(old_rework) != 1:
    raise SystemExit("expected semantic rework block exactly once")
text = text.replace(old_rework, new_rework, 1)

old_format = '''    if rounds == 0:
        lines.append("验收: 未触发" if locale == "zh" else "Review: not triggered")
    elif locale == "zh":
'''
new_format = '''    if rounds == 0:
        if review["reworks"]:
            lines.append(
                f"验收: 未触发独立复核 · 返工{review['reworks']}次"
                if locale == "zh"
                else f"Review: independent review not triggered · rework×{review['reworks']}"
            )
        else:
            lines.append("验收: 未触发" if locale == "zh" else "Review: not triggered")
    elif locale == "zh":
'''
if text.count(old_format) != 1:
    raise SystemExit("expected zero-round format block exactly once")
text = text.replace(old_format, new_format, 1)
STATE.write_text(text, encoding="utf-8")

receipt = RECEIPT.read_text(encoding="utf-8")
receipt = receipt.replace(
    "The Review axis reports the independent Final Review loop only. It does not claim that the overall user task is complete.",
    "The Review axis reports the quality loop: independent Final Review rounds plus evidence-bound semantic rework. A rework count does not imply that independent Final Review ran, and this axis does not claim that the overall user task is complete.",
)
receipt = receipt.replace(
    '''A reviewer attempt that crashes before producing a verdict contributes to Dispatch as a materialized Agent pass but does not increment the Review round count.\n\n## Rework versus retry\n''',
    '''A reviewer attempt that crashes before producing a verdict contributes to Dispatch as a materialized Agent pass but does not increment the Review round count.\n\nWhen Main deterministic verification finds the gap and no independent Final Review ran, keep that distinction visible:\n\n```text\n验收: 未触发独立复核 · 返工1次\nReview: independent review not triggered · rework×1\n```\n\n## Rework versus retry\n''',
)
receipt = receipt.replace(
    '''The rework event binds that materialized focused follow-up and the `review_artifact_id` of the review round that reported the concrete gap. An unbound claim is not a rework.\n''',
    '''A review-driven rework binds that materialized focused follow-up and the `review_artifact_id` of the review round that reported the concrete gap.\n\nA Main-verification-driven rework first records a typed `verification_gap` event with a stable ref, the exact candidate `verification_artifact_id` (`sha256:<64 hex>`), and a non-empty deterministic `oracle_ref` identifying the acceptance check that exposed the gap. The `semantic_rework` event then binds the same materialized focused follow-up to that `verification_gap_ref`. Raw test output is not persisted in the receipt event.\n\nA semantic rework must bind exactly one gap source: independent Review or Main verification. A caller-supplied rework count, free-form `rebind` label, or correction with no evidence-bound gap is not a rework.\n''',
)
receipt = receipt.replace(
    '''semantic rework         -> Review rework only when a correction pass actually begins\nreviewer attempt        -> Dispatch pass, even if no verdict is produced\n''',
    '''verification gap        -> Main acceptance evidence; no Dispatch pass or Review round by itself\nsemantic rework         -> Review-axis rework only when a correction pass actually begins from one bound gap\nreviewer attempt        -> Dispatch pass, even if no verdict is produced\n''',
)
RECEIPT.write_text(receipt, encoding="utf-8")

TEST.write_text(
    '''import importlib.util\nfrom pathlib import Path\n\nimport pytest\n\n\nROOT = Path(__file__).resolve().parents[1]\nMODULE_PATH = ROOT / "scripts" / "dispatch_state.py"\n\n\ndef load_module():\n    spec = importlib.util.spec_from_file_location("dispatch_state_verification_rework", MODULE_PATH)\n    assert spec and spec.loader\n    module = importlib.util.module_from_spec(spec)\n    spec.loader.exec_module(module)\n    return module\n\n\ndef materialized_worker():\n    return {\n        "unit_id": "U1",\n        "attempt": 1,\n        "agent_id": "agent-1",\n        "role": "worker",\n        "model_lane": "Luna Max",\n    }\n\n\ndef followup_event():\n    return {\n        "ref": "followup:U1:A1:F1",\n        "kind": "followup",\n        "unit_id": "U1",\n        "attempt": 1,\n        "agent_id": "agent-1",\n        "activity": "execute",\n    }\n\n\ndef test_main_verification_gap_can_bind_real_semantic_rework_without_review_round():\n    module = load_module()\n    artifact_id = "sha256:" + "a" * 64\n    events = [\n        followup_event(),\n        {\n            "ref": "verification-gap:pagination-test",\n            "kind": "verification_gap",\n            "verification_artifact_id": artifact_id,\n            "oracle_ref": "pytest:tests/test_api.py::test_pagination",\n        },\n        {\n            "ref": "rework:U1:verification-1",\n            "kind": "semantic_rework",\n            "unit_id": "U1",\n            "attempt": 1,\n            "agent_id": "agent-1",\n            "verification_gap_ref": "verification-gap:pagination-test",\n        },\n    ]\n\n    summary = module.account_receipt(events, materialized_units=[materialized_worker()])\n    assert summary["semantic_reworks"] == 1\n    assert summary["review"] == {"rounds": 0, "reworks": 1, "verdict": None}\n    assert "验收: 未触发独立复核 · 返工1次" in module.format_receipt(summary, locale="zh")\n    assert "Review: independent review not triggered · rework×1" in module.format_receipt(summary, locale="en")\n\n\ndef test_verification_gap_requires_exact_artifact_and_oracle():\n    module = load_module()\n    for event in [\n        {"ref": "gap:missing-artifact", "kind": "verification_gap", "oracle_ref": "pytest:test"},\n        {\n            "ref": "gap:bad-artifact",\n            "kind": "verification_gap",\n            "verification_artifact_id": "candidate",\n            "oracle_ref": "pytest:test",\n        },\n        {\n            "ref": "gap:missing-oracle",\n            "kind": "verification_gap",\n            "verification_artifact_id": "sha256:" + "b" * 64,\n        },\n    ]:\n        with pytest.raises(module.ReceiptAccountingError, match="exact candidate artifact and oracle_ref"):\n            module.account_receipt([event], materialized_units=[materialized_worker()])\n\n\ndef test_semantic_rework_rejects_missing_or_multiple_gap_sources():\n    module = load_module()\n    artifact_id = "sha256:" + "c" * 64\n    gap = {\n        "ref": "verification-gap:one",\n        "kind": "verification_gap",\n        "verification_artifact_id": artifact_id,\n        "oracle_ref": "pytest:test_one",\n    }\n    unbound = {\n        "ref": "rework:unbound",\n        "kind": "semantic_rework",\n        "unit_id": "U1",\n        "attempt": 1,\n        "agent_id": "agent-1",\n    }\n    with pytest.raises(module.ReceiptAccountingError, match="exactly one bound review or verification gap"):\n        module.account_receipt([followup_event(), gap, unbound], materialized_units=[materialized_worker()])\n\n    advisor = {\n        "unit_id": "U2",\n        "attempt": 1,\n        "agent_id": "advisor-1",\n        "role": "advisor",\n        "model_lane": "Sol High",\n    }\n    both = [\n        followup_event(),\n        gap,\n        {\n            "ref": "reviewer:U2:A1",\n            "kind": "reviewer_attempt",\n            "unit_id": "U2",\n            "attempt": 1,\n            "agent_id": "advisor-1",\n            "activity": "review",\n            "review_artifact_id": artifact_id,\n        },\n        {\n            "ref": "review:U2:R1",\n            "kind": "review_round",\n            "unit_id": "U2",\n            "attempt": 1,\n            "agent_id": "advisor-1",\n            "verdict": "rework_required",\n            "review_artifact_id": artifact_id,\n        },\n        {\n            "ref": "rework:both",\n            "kind": "semantic_rework",\n            "unit_id": "U1",\n            "attempt": 1,\n            "agent_id": "agent-1",\n            "review_artifact_id": artifact_id,\n            "verification_gap_ref": "verification-gap:one",\n        },\n    ]\n    with pytest.raises(module.ReceiptAccountingError, match="exactly one bound review or verification gap"):\n        module.account_receipt(both, materialized_units=[materialized_worker(), advisor])\n''',
    encoding="utf-8",
)
