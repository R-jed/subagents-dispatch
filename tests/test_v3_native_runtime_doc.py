from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "docs" / "native-subagent-runtime.md"


def test_native_runtime_document_keeps_selected_and_observed_route_truth_separate():
    text = RUNTIME.read_text(encoding="utf-8")
    for phrase in [
        "Configured or selected values never become observed values by assumption",
        "ordinary Dispatch Receipt may display the selected project lane",
        "not an independent live telemetry measurement",
        "Contradictory native evidence is a route-integrity failure",
        "The current Plugin does not add a private App Server client",
    ]:
        assert phrase in text
    assert "Execution Receipts follow this same rule" not in text
    assert "subagents-dispatch 2.1 does not add" not in text


def test_native_runtime_document_uses_explicit_skill_semantics_not_guessed_slash_grammar():
    text = RUNTIME.read_text(encoding="utf-8")
    assert "The Plugin packages six explicit Skill ids" in text
    assert "These are semantic inputs after selection, not guessed literal App slash strings" in text
    for obsolete in [
        "preview <task>",
        "steer <unit_id>: <guidance>",
        "takeover <unit_id>",
    ]:
        assert obsolete not in text
    assert "pendingInit  -> RUNNING" in text
    assert "notFound     -> UNKNOWN" in text
    assert "no minimum Subagent count" in text
