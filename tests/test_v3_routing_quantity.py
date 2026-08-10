from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROUTING = ROOT / "contracts" / "routing.md"


def test_delegation_quantity_is_value_driven_not_zero_child_numeric_policy():
    text = ROUTING.read_text(encoding="utf-8")
    assert "Delegation is optional and value-driven" in text
    assert "There is no minimum Subagent count" in text
    assert "zero children is a valid derived outcome" in text
    assert "Zero children is normal" not in text
    assert "Native Codex capacity is the upper bound on concurrency, not a target" in text
    assert "Do not keep Agents busy merely because the host has spare capacity" in text
