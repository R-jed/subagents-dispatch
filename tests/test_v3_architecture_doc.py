from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHITECTURE = ROOT / "docs" / "architecture.md"


def test_architecture_document_matches_v3_control_and_receipt_contracts():
    text = ARCHITECTURE.read_text(encoding="utf-8")

    for phrase in [
        "six thin explicit entry points",
        "There is no minimum Subagent count",
        "INTERRUPTED",
        "## Dispatch Receipt",
        "scripts/dispatch_state.py",
        "Doctor has exactly six diagnostic layers",
        "selected project lane bound to materialized work",
        "Explicit Dispatch that routes everything to Main still returns the minimal zero-child Receipt",
    ]:
        assert phrase in text

    for obsolete in [
        "Version 2.1 adds",
        "## Execution Receipt",
        "Dispatch: Reader → Worker",
        "· complete · no retry",
        "Zero children is normal",
        "preview <task>",
        "steer <unit_id>: <guidance>",
        "Zero-child tasks, Preview, Status-only requests, and `RESTART_REQUIRED` first-use setup do not add a receipt",
    ]:
        assert obsolete not in text


def test_architecture_keeps_codex_native_subagents_as_the_only_runtime():
    text = ARCHITECTURE.read_text(encoding="utf-8")
    assert "Codex remains the only Agent runtime" in text
    for forbidden in [
        "background scheduler is introduced",
        "persistent task database",
        "private Agent runtime",
    ]:
        assert forbidden not in text
