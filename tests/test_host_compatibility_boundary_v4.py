from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_n1_records_multi_agent_v2_compatibility_boundary():
    contract = json.loads(
        (ROOT / "docs" / "v4" / "host-smoke.json").read_text(encoding="utf-8")
    )
    n1 = next(probe for probe in contract["required_probes"] if probe["id"] == "N1")
    boundary = n1["compatibility_boundary"]

    assert boundary["field"] == "features.multi_agent_v2=false"
    assert boundary["status"] == "retain_until_target_host_evidence"
    assert "target Host" in boundary["reason"]
    assert "N1" in boundary["removal_condition"]
    assert "collaboration tools" in boundary["removal_condition"]
