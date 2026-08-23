from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_contract() -> dict:
    return json.loads((ROOT / "docs" / "v4" / "host-smoke.json").read_text(encoding="utf-8"))


def test_probe_turn_capability_is_bound_to_exact_turn_and_v2_surface():
    contract = load_contract()
    capability = contract["probe_turn_capability_semantics"]

    assert capability["turn_binding_field"] == "turn_id"
    assert capability["required_multi_agent_version"] == "v2"
    assert capability["historical_turn_reuse"] is False
    assert capability["unavailable_or_conflicting_verdict"] == "NOT_RUN"
    assert capability["unavailable_or_conflicting_action"] == "do not invoke Agent-control tools"

    assert capability["required_v2_spawn_schema"] == {
        "required": ["task_name", "message"],
        "present": ["fork_turns"],
        "absent": ["fork_context"],
    }

    sources = capability["authoritative_sources"]
    assert any("turn_context.multi_agent_version" in source and "probe turn_id" in source for source in sources)
    assert any("same probe turn" in source and "tool schema" in source for source in sources)


def test_probe_turn_capability_precondition_covers_native_agent_control_probes():
    contract = load_contract()
    capability = contract["probe_turn_capability_semantics"]

    assert capability["applies_to_host_agent_control_steps_in_probes"] == [
        "N0",
        "N1",
        "N2",
        "N3",
        "N4",
        "N5",
        "N6",
        "N8",
    ]

    probes = {probe["id"]: probe for probe in contract["required_probes"]}
    assert any("probe-turn capability precondition" in item for item in probes["N0"]["requires"])
    assert any("probe-turn capability precondition" in item for item in probes["N1"]["requires"])
