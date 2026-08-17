from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_installer_guidance_uses_orchestrate_only():
    text = (ROOT / "scripts" / "install-agents.py").read_text(encoding="utf-8")
    assert "explicit Dispatch task" not in text
    assert "through Dispatch" not in text
    assert "current Dispatch task" not in text
    assert "explicit Orchestrate task" in text
    assert "through Orchestrate" in text


def test_runtime_module_docs_reflect_v4_cutover():
    orchestrate = (ROOT / "scripts" / "orchestrate_v4.py").read_text(encoding="utf-8")
    state = (ROOT / "scripts" / "dispatch_state_v4.py").read_text(encoding="utf-8")
    assert "coexistence facade" not in orchestrate
    assert "Production Skills remain on V3" not in state
    assert "V4 Orchestrate production facade" in orchestrate
    assert "This module owns the V4 schema" in state


def test_deferred_structural_debt_is_explicit():
    payload = json.loads((ROOT / "docs" / "v4" / "technical-debt.json").read_text(encoding="utf-8"))
    items = {item["id"]: item for item in payload["items"]}
    assert set(items) == {
        "TD-V4-STATE-STORAGE-DECOUPLE",
        "TD-V4-DOCTOR-COMPAT-DECOUPLE",
    }
    assert {item["status"] for item in items.values()} == {"DEFERRED_POST_HOST_VALIDATION"}
    assert "H01-H07" in payload["release_policy"]
