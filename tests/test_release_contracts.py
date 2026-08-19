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
REFERENCE_HOOKS = ROOT / "docs" / "v4" / "hooks.json"
ACTIVE_HOOKS = ROOT / "hooks" / "hooks.json"
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


def test_host_release_gate_binds_pending_campaign_to_active_candidate_hook():
    smoke = json.loads(HOST_SMOKE.read_text(encoding="utf-8"))
    assert smoke["status"] == "PENDING"
    assert smoke["gate_id"] == "v4-real-host-h00-h20"
    assert smoke["results"] == {}
    assert smoke["activation_manifest"] == "hooks/hooks.json"
    assert smoke["production_manifest"] == "hooks/hooks.json"
    assert [probe["id"] for probe in smoke["required_probes"]] == [
        f"H{number:02d}" for number in range(21)
    ]

    active = json.loads(ACTIVE_HOOKS.read_text(encoding="utf-8"))
    reference = json.loads(REFERENCE_HOOKS.read_text(encoding="utf-8"))
    assert set(active["hooks"]) == {"PreToolUse", "PostToolUse", "SubagentStop"}
    assert reference["hooks"] == active["hooks"]
