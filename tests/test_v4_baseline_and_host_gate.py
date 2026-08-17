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


def test_tracked_host_contract_cannot_self_attest_runtime_pass():
    smoke = load_json("host-smoke.json")

    assert smoke["schema_version"] == "4.0.0-host-smoke-7"
    assert smoke["gate_id"] == "v4-real-host-h00-h20"
    assert smoke["status"] == "PENDING"
    assert smoke["results"] == {}
    assert "external exact-candidate campaign" in smoke["pass_policy"]


def test_real_host_smoke_gate_covers_all_managed_lifecycle_boundaries():
    smoke = load_json("host-smoke.json")
    probes = {probe["id"]: probe for probe in smoke["required_probes"]}

    assert set(probes) == {f"H{number:02d}" for number in range(21)}
    assert probes["H00"]["operation"] == "Hook trust and activation"
    assert probes["H01"]["operation"] == "spawn_agent Pre/Post"
    assert probes["H02"]["operation"] == "followup_task Pre/Post"
    assert probes["H03"]["operation"] == "interrupt_agent Pre/Post"
    assert probes["H04"]["operation"] == "SubagentStop veto"
    assert probes["H09"]["operation"] == "V2 residency capacity and refill"
    assert probes["H18"]["operation"] == "mixed managed unmanaged Host occupancy"
    assert probes["H19"]["operation"] == "candidate-bound Host evidence"
    assert probes["H20"]["operation"] == "Windows effective path aliases"
    assert probes["H20"]["platform"] == "windows"
    assert smoke["required_environment_fields"] == [
        "architecture",
        "codex_version",
        "host_build",
        "platform",
        "run_id",
    ]
    assert smoke["required_result_fields"] == ["environment_id", "evidence_ref", "status"]


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
    assert smoke["results"] == {}
    assert status["phases"]["phase4"]["status"] == "PASS"
    assert status["phases"]["phase8"]["publication"] == "BLOCKED"
    assert status["phases"]["phase8"]["external_host_campaign"] == "REQUIRED_H00_H20"
    assert "external candidate-bound H00-H20 Host campaign PASS" in status["release_rule"]
    assert "tracked docs/v4/host-smoke.json remains a PENDING static contract" in status["release_rule"]
