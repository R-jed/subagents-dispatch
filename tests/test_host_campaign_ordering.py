from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOST_SMOKE = ROOT / "docs" / "v4" / "host-smoke.json"


def probes() -> dict[str, dict]:
    payload = json.loads(HOST_SMOKE.read_text(encoding="utf-8"))
    return {item["id"]: item for item in payload["required_probes"]}


def requirements(probe: dict) -> str:
    return " ".join(probe["requires"]).lower()


def test_h00_does_not_require_unobservable_stdin_before_behavior_probes():
    payload = json.loads(HOST_SMOKE.read_text(encoding="utf-8"))
    h00 = probes()["H00"]
    text = requirements(h00)

    assert payload["schema_version"] == "4.0.0-host-smoke-7"
    assert payload["status"] == "PENDING"
    assert payload["results"] == {}
    assert "safe non-mutating collaboration observation" in text
    assert "executes both pretooluse and posttooluse" in text
    assert "lack of external raw stdin visibility alone does not block h00" in text
    assert "raw hook-serialized tool_name is recorded when the host exposes it" in text


def test_each_guarded_semantic_owns_its_runtime_interception_evidence():
    current = probes()

    for probe_id in ("H01", "H02", "H03", "H14"):
        assert "intercept" in requirements(current[probe_id])

    assert "raw hook-serialized identity is recorded when the host exposes it" in requirements(
        current["H01"]
    )
    assert "blocked before managed child peer delivery" in requirements(current["H14"])


def test_h08_uses_exact_binding_behavior_when_raw_payload_is_unavailable():
    text = requirements(probes()["H08"])

    assert "exact-binding acceptance and mismatch-rejection behavior" in text
    assert "raw sanitized shapes are recorded when the host exposes them" in text
    assert "does not weaken exact pendingcontrol binding" in text
