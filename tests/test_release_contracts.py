from __future__ import annotations

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / ".codex-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".agents" / "plugins" / "marketplace.json"
CHANGELOG = ROOT / "CHANGELOG.md"
CHANGELOG_V3 = ROOT / "CHANGELOG_V3.md"
HOST_SMOKE = ROOT / "docs" / "v4" / "host-smoke.json"
ARCHITECTURE = ROOT / "docs" / "v4" / "architecture.json"
BEHAVIOR_COMPARISON = ROOT / "docs" / "v4" / "rc4-native-core-behavior-comparison.json"
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def current_version() -> str:
    version = json.loads(PLUGIN.read_text(encoding="utf-8"))["version"]
    assert isinstance(version, str) and SEMVER.fullmatch(version)
    return version


def test_release_version_identity_uses_exact_marketplace_checkout_as_plugin_source():
    assert current_version() == "4.0.0"
    market = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    source = market["plugins"][0]["source"]
    assert source == {"source": "local", "path": "./"}


def test_latest_changelog_matches_release_version_and_keeps_v3_history():
    text = CHANGELOG.read_text(encoding="utf-8")
    match = re.search(r"^## \[([^\]]+)\]", text, flags=re.MULTILINE)
    assert match and match.group(1) == current_version()
    assert CHANGELOG_V3.is_file()


def test_host_release_gate_matches_native_core_architecture_campaign():
    smoke = json.loads(HOST_SMOKE.read_text(encoding="utf-8"))
    architecture = json.loads(ARCHITECTURE.read_text(encoding="utf-8"))

    assert smoke["status"] == "PENDING"
    assert smoke["gate_id"] == "v4-real-host-n0-n8"
    assert smoke["results"] == {}
    assert [probe["id"] for probe in smoke["required_probes"]] == [f"N{number}" for number in range(9)]
    assert architecture["release"]["host_campaign"] == [
        "N0_route_model_effort_fork_turns",
        "N1_child_collaboration_absent",
        "N2_spawn_identity_binding",
        "N3_capacity_rejection_no_materialization",
        "N4_followup_continue_same_child",
        "N5_interrupt_settlement",
        "N6_writer_takeover_settlement",
        "N7_rollout_reconciliation_privacy",
        "N8_final_review_and_sandbox_truth",
    ]
    assert "activation_manifest" not in smoke
    assert "production_manifest" not in smoke
    assert architecture["host_truth"]["plugin_hook_required"] is False


def test_rc4_native_core_behavior_comparison_records_only_reviewed_deltas():
    comparison = json.loads(BEHAVIOR_COMPARISON.read_text(encoding="utf-8"))

    assert comparison["baseline"] == {
        "name": "RC4 Host contract closure",
        "commit": "c6c788bf1d5ba4a061b6252fc307fafec7ef07a3",
        "source_pr": 73,
    }
    assert comparison["comparison_result"]["blocking_unapproved_behavior_regressions"] == 0
    assert comparison["comparison_result"]["release_ready"] is False
    assert comparison["comparison_result"]["status"] == "READY_FOR_EXACT_CANDIDATE_HOST_VALIDATION"

    assert {item["id"] for item in comparison["corrected_regressions"]} == {
        "terra-effort-drift",
        "steer-correction-conflation",
    }
    assert all(item["status"] == "CORRECTED" for item in comparison["corrected_regressions"])

    assert {item["id"] for item in comparison["intentional_changes"]} == {
        "remove-hook-correctness-authority",
        "remove-pending-control",
        "capacity-policy",
        "broad-reader-fanout",
        "public-skill-surface",
        "receipt-surface",
    }
    assert all(item["status"] == "APPROVED_DELTA" for item in comparison["intentional_changes"])

    pending_host = {item["id"]: item["status"] for item in comparison["host_evidence_required"]}
    assert pending_host == {
        "N0-N8": "PENDING",
        "same-child-rejection-edge": "PENDING_N4",
        "interrupt-rejection-edge": "PENDING_N5",
        "sandbox-truth": "PENDING_N8",
    }
