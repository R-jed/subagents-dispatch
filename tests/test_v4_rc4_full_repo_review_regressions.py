from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
V4 = ROOT / "docs" / "v4"


def load_module(name: str, filename: str):
    scripts = str(SCRIPTS)
    sys.path.insert(0, scripts)
    try:
        spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts)


def test_post_tool_use_failure_uses_host_blocking_semantics(monkeypatch):
    guard = load_module("full_review_guard", "orchestration_guard.py")

    def fail(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(guard.host_evidence, "invalidate_host_capacity_observation", fail)
    result = guard._invalidate_capacity("root-session", temp_root=None)
    assert result == {
        "decision": "block",
        "reason": "subagents-dispatch orchestration guard: Host capacity truth could not be invalidated safely; lifecycle result rejected",
    }


def test_subagent_stop_keeps_real_stop_semantics():
    guard = load_module("full_review_stop_guard", "orchestration_guard.py")
    result = guard.evaluate_subagent_stop(
        {
            "hook_event_name": "SubagentStop",
            "agent_type": "subagents_dispatch_reader",
        }
    )
    assert result is not None
    assert result["continue"] is False
    assert "decision" not in result


def test_h07_requires_real_post_tool_use_blocking_semantics():
    smoke = json.loads((V4 / "host-smoke.json").read_text(encoding="utf-8"))
    probes = {probe["id"]: probe for probe in smoke["required_probes"]}
    h07 = " ".join(probes["H07"]["requires"])
    assert "decision:block" in h07
    assert "rejects the lifecycle result" in h07


def test_active_v4_public_contracts_use_only_orchestrate_and_doctor():
    guardrails = (ROOT / "contracts" / "guardrails.md").read_text(encoding="utf-8")
    interaction = (ROOT / "contracts" / "interaction.md").read_text(encoding="utf-8")
    installation = (ROOT / "docs" / "plugin-installation.md").read_text(encoding="utf-8")
    ai_reference = (ROOT / "README_AI.md").read_text(encoding="utf-8")
    doctor_skill = (ROOT / "skills" / "doctor" / "SKILL.md").read_text(encoding="utf-8")

    retired_claims = (
        "stable `dispatch`, `preview`, `status`, `steer`, `takeover`, and `doctor` Skills",
        "stable interaction Skill ids are `preview`, `status`, `steer`, and `takeover`",
        "packages six explicit Skill identities",
        "H01-H07",
    )
    combined = "\n".join((guardrails, interaction, installation, ai_reference, doctor_skill))
    for claim in retired_claims:
        assert claim not in combined
    assert "Orchestrate" in guardrails
    assert "Orchestrate" in interaction
    assert "Orchestrate" in installation


def test_writer_settlement_contract_matches_runtime_proof_boundary():
    lifecycle = json.loads((V4 / "writer-lifecycle.json").read_text(encoding="utf-8"))
    requires = lifecycle["settlement_theorem"]["requires"]
    assert "proven managed lifecycle Guard coverage" not in requires
    assert "authoritative current-epoch list_agents Hook observation" in requires

    orchestrate = (ROOT / "skills" / "orchestrate" / "SKILL.md").read_text(encoding="utf-8")
    assert "current managed lifecycle Guard coverage evidence" not in orchestrate
    assert "authoritative current-epoch list_agents Hook observation" in orchestrate
