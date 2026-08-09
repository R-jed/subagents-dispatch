import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTERACTION = ROOT / "contracts" / "interaction.md"
CASES = ROOT / "evals" / "interaction-cases.json"


def test_missing_current_dispatch_and_missing_target_never_create_fake_control_state():
    text = INTERACTION.read_text(encoding="utf-8")
    assert "there are no current delegated responsibilities" in text
    assert "do not reconstruct an old task from memory" in text
    assert "takeover does not proceed" in text

    payload = json.loads(CASES.read_text(encoding="utf-8"))
    by_id = {case["id"]: case for case in payload["cases"]}

    empty = by_id["status-with-no-current-dispatch-does-not-invent-state"]["expected"]
    assert empty["active_responsibilities"] == 0
    assert empty["reported_unknown_unit"] is False
    assert empty["search_other_sessions"] is False

    missing = by_id["control-target-missing-fails-closed"]["expected"]
    assert missing["target_resolved"] is False
    assert missing["ownership_transferred"] is False
    assert missing["invent_agent_id"] is False
    assert missing["search_other_sessions"] is False
