from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V4 = ROOT / "docs" / "v4"


def load_json(name: str) -> dict:
    return json.loads((V4 / name).read_text(encoding="utf-8"))


def test_v4_engineering_baseline_is_hardened_main_not_bare_v3_0_0():
    baseline = load_json("engineering-baseline.json")

    assert baseline["family"] == "V3.x Hardened Baseline"
    assert baseline["branch"] == "main"
    assert baseline["commit"] == "1252c366756b1f981c845f7664da14c0f81eac20"
    assert baseline["release_lineage"] == {
        "v3.0.0": "f90105f4a9f0ecdf94c8306095d80a92ab995370",
        "v3.0.1": "bfc4e249ba1acc75876dab1b43cedb9f321ee829",
    }
    assert "state-protocol family" in baseline["migration_note"]
    assert baseline["phase0_guard_evidence"] == {
        "baseline_spawn_guard_failure_exit_code": 78,
        "codex_pre_tool_use_blocking_exit_code": 2,
        "phase0_fix_required": True,
    }


def test_v3_post_release_spawn_guard_evidence_does_not_satisfy_v4_runtime_gate():
    smoke = load_json("host-smoke.json")

    assert smoke["status"] == "PENDING"
    assert smoke["blocks_phase"] == "phase8-supported-release"
    inherited = smoke["inherited_evidence"]
    assert len(inherited) == 1
    assert inherited[0]["source"] == "PR #66"
    assert inherited[0]["satisfies_runtime_gate"] is False
    assert "real Host execution of PreToolUse for spawn_agent" in inherited[0]["does_not_prove"]


def test_real_host_smoke_gate_covers_all_managed_lifecycle_boundaries():
    smoke = load_json("host-smoke.json")
    probes = {probe["id"]: probe for probe in smoke["required_probes"]}

    assert set(probes) == {f"H{number:02d}" for number in range(11)}
    assert probes["H00"]["operation"] == "Hook trust and activation"
    assert probes["H01"]["operation"] == "spawn_agent"
    assert probes["H02"]["operation"] == "followup_task"
    assert probes["H03"]["operation"] == "interrupt_agent"
    assert probes["H04"]["operation"] == "SubagentStop"
    assert probes["H05"]["operation"] == "managed child sibling followup"
    assert probes["H06"]["operation"] == "managed child sibling interrupt"
    assert probes["H07"]["operation"] == "missing or failed PostToolUse"
    assert probes["H08"]["operation"] == "message payload representation compatibility"
    assert probes["H09"]["operation"] == "open spawned-thread capacity and refill"
    assert probes["H10"]["operation"] == "writable lifecycle acknowledgement"

    for probe_id in ("H01", "H02", "H03"):
        requirements = set(probes[probe_id]["requires"])
        assert "PreToolUse observed" in requirements
        assert "PostToolUse observed" in requirements
        assert "same tool_use_id across PreToolUse and PostToolUse" in requirements
    assert "exact active lifecycle Hook definition hash captured" in probes["H00"]["requires"]
    assert any("canonical digests match" in item for item in probes["H08"]["requires"])
    assert "closing the child releases capacity" in probes["H09"]["requires"]
    assert any("WriterLease is HELD" in item for item in probes["H10"]["requires"])


def test_offline_development_can_advance_while_supported_release_stays_blocked():
    status = load_json("phase-status.json")
    smoke = load_json("host-smoke.json")

    assert status["phases"]["phase0"]["status"] == "PASS"
    assert status["phases"]["phase1"]["status"] == "PASS"
    assert status["phases"]["phase2"]["status"] == "PASS"
    assert status["phases"]["phase3"]["repository_implementation"] == "PASS"
    assert status["phases"]["phase3"]["offline_verification"] == "PASS"
    assert status["phases"]["phase3"]["real_host_smoke"] == "PENDING_RELEASE_GATE"
    assert smoke["status"] == "PENDING"
    assert status["phases"]["phase4"]["status"] == "PASS"
    assert smoke["blocks_phase"] == "phase8-supported-release"
    assert "publication remain blocked" in status["release_rule"]
