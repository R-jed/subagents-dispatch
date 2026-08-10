from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVAL_DOC = ROOT / "docs" / "behavioral-evals.md"


def test_behavioral_eval_protocol_uses_current_dispatch_receipt_semantics():
    text = EVAL_DOC.read_text(encoding="utf-8")
    for phrase in [
        "Dispatch Receipt, and Handoff Capsule boundaries",
        "## Experiment I: Dispatch Receipt clarity",
        "explicit Dispatch with zero materialized children",
        "minimal zero-child Dispatch + Review receipt",
        "Preview-only request",
        "no terminal Dispatch Receipt",
    ]:
        assert phrase in text
    for obsolete in [
        "Execution Receipt",
        "one-line 2.1 receipt",
        "When the workload exercises 2.1 controls",
        "preview <same task used for a later real run>",
        "These should not add a receipt.",
    ]:
        assert obsolete not in text


def test_behavioral_eval_protocol_keeps_ui_syntax_observation_gated():
    text = EVAL_DOC.read_text(encoding="utf-8")
    assert "Do not assume or record a literal slash string unless the App directly renders one" in text
    assert "contracts/receipt.md" in text
    assert "contracts/state.md" in text
