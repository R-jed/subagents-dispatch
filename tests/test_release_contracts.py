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


def test_latest_changelog_matches_release_version_without_legacy_v3_file():
    text = CHANGELOG.read_text(encoding="utf-8")
    match = re.search(r"^## \[([^\]]+)\]", text, flags=re.MULTILINE)
    assert match and match.group(1) == current_version()
    assert not CHANGELOG_V3.exists()


def test_host_release_gate_matches_native_core_architecture_campaign():
    smoke = json.loads(HOST_SMOKE.read_text(encoding="utf-8"))
    architecture = json.loads(ARCHITECTURE.read_text(encoding="utf-8"))

    assert smoke["status"] == "PENDING"
    assert smoke["gate_id"] == "v4-real-host-n0-n8"
    assert smoke["results"] == {}
    assert [probe["id"] for probe in smoke["required_probes"]] == [f"N{number}" for number in range(9)]
    assert architecture["release"]["host_campaign"] == [
        "N0_route_model_effort_fork_turns",
        "N1_child_collaboration_containment",
        "N2_spawn_identity_binding",
        "N3_capacity_rejection_no_materialization",
        "N4_followup_continue_same_child",
        "N5_interrupt_settlement",
        "N6_writer_takeover_settlement",
        "N7_rollout_reconciliation_privacy",
        "N8_final_review_and_effective_sandbox_truth",
    ]
    assert architecture["host_truth"]["lifecycle_owner"] == "codex_host"
    assert architecture["host_truth"]["capacity_owner"] == "codex_host"
    assert architecture["host_truth"]["managed_child_collaboration_surface_owner"] == "codex_host"
    assert architecture["host_truth"]["effective_permission_owner"] == "codex_host"
