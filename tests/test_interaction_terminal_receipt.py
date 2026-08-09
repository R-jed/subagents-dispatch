import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTERACTION = ROOT / "contracts" / "interaction.md"
RECEIPT = ROOT / "contracts" / "receipt.md"
SKILL = ROOT / "skills" / "dispatch" / "SKILL.md"
CASES = ROOT / "evals" / "interaction-cases.json"


def test_blocked_delegated_terminal_response_keeps_compact_receipt():
    interaction = INTERACTION.read_text(encoding="utf-8")
    receipt = RECEIPT.read_text(encoding="utf-8")
    assert "whether the requested work completed successfully or ended blocked/partial" in interaction
    assert "Main owns the task-facing final response" in receipt
    assert "../../contracts/receipt.md" in SKILL.read_text(encoding="utf-8")

    payload = json.loads(CASES.read_text(encoding="utf-8"))
    by_id = {case["id"]: case for case in payload["cases"]}
    expected = by_id["blocked-delegated-outcome-still-has-receipt"]["expected"]
    assert expected["receipt"] is True
    assert expected["axes"] == ["Dispatch", "Review"]
    assert expected["may_report_blocker"] is True
    assert expected["must_preserve_unknown"] is True
