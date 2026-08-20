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


def test_h08_is_native_encrypted_message_preflight_on_h01_specimen():
    current = probes()
    h08 = current["H08"]
    h08_text = requirements(h08)
    h01_text = requirements(current["H01"])

    assert h08["operation"] == "native encrypted-message compatibility preflight"
    assert "same authorized spawn specimen used by h01" in h08_text
    assert "before host child mutation" in h08_text
    assert "opaque or transformed transport data" in h08_text
    assert "does not decrypt, rebind, hash-compare, or infer its content" in h08_text
    assert "task_name agent_type fork_turns" in h08_text
    assert "authorization-envelope mutation is rejected" in h08_text
    assert "h15 owns behavior-level delivery" in h08_text

    assert "h08 native encrypted-message compatibility has passed" in h01_text
    assert "codex owns message transport" in h01_text
    assert "task_name agent_type fork_turns control epoch and writer effect" in h01_text


def test_h02_binds_followup_control_while_host_owns_message_transport():
    text = requirements(probes()["H02"])

    assert "same-child target preserved" in text
    assert "target lifecycle generation and writer effect" in text
    assert "opaque or transformed message transport representation" in text
    assert "target drift or lifecycle-generation drift fails closed" in text


def test_h15_owns_semantic_delivery_evidence_without_decrypting_transport():
    text = requirements(probes()["H15"])

    assert "observable child behavior" in text
    assert "distinct non-sensitive markers" in text
    assert "without inspecting encrypted transport content" in text
    assert "parallel siblings isolated" in text
