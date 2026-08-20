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


def test_h08_is_spawn_message_binding_preflight_before_h01():
    current = probes()
    h08 = current["H08"]
    h08_text = requirements(h08)
    h01_text = requirements(current["H01"])

    assert h08["operation"] == "spawn message binding capability preflight"
    assert "before h01" in h08_text
    assert "plaintext or verifiable binding metadata" in h08_text
    assert "before host mutation" in h08_text
    assert "opaque or transformed message content" in h08_text
    assert "h08 fail and stops the campaign" in h08_text
    assert "do not rebind pendingcontrol to observed ciphertext" in h08_text

    assert "h08 spawn-message binding capability has already passed" in h01_text
    assert "without omitting or rebinding opaque message semantics" in h01_text


def test_h02_owns_followup_message_binding():
    text = requirements(probes()["H02"])

    assert "followup_task message representation remains exact-bindable" in text
    assert "before host mutation" in text
    assert "opaque or transformed message content without a verifiable binding fails closed" in text


def test_h08_rejects_transport_continuity_as_semantic_binding():
    text = requirements(probes()["H08"])

    assert "plaintext digest" in text
    assert "authenticated binding token" in text
    assert "use string heuristics" in text
    assert "omit message semantics from authorization" in text
