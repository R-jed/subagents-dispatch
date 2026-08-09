from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / ".codex-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".agents" / "plugins" / "marketplace.json"
README_CN = ROOT / "README.md"
README_EN = ROOT / "README_EN.md"
README_AI = ROOT / "README_AI.md"
CHANGELOG = ROOT / "CHANGELOG.md"
RELEASE_CHECKLIST = ROOT / "docs" / "release-checklist.md"

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def current_version() -> str:
    version = json.loads(PLUGIN.read_text(encoding="utf-8"))["version"]
    assert isinstance(version, str) and SEMVER.fullmatch(version)
    return version


def test_public_version_markers_match_plugin_manifest():
    version = current_version()
    badge = f"version-{version}-green.svg"
    assert badge in README_CN.read_text(encoding="utf-8")
    assert badge in README_EN.read_text(encoding="utf-8")
    assert re.search(
        rf"^Current version:\s+{re.escape(version)}$",
        README_AI.read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )


def test_latest_changelog_entry_matches_plugin_manifest():
    version = current_version()
    match = re.search(r"^## \[([^\]]+)\]", CHANGELOG.read_text(encoding="utf-8"), flags=re.MULTILINE)
    assert match, "CHANGELOG.md must contain a version heading"
    assert match.group(1) == version


def test_marketplace_plugin_source_is_bound_to_release_tag():
    version = current_version()
    market = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    plugins = market.get("plugins")
    assert isinstance(plugins, list) and len(plugins) == 1
    source = plugins[0].get("source")
    assert source == {
        "source": "url",
        "url": "https://github.com/R-jed/subagents-dispatch.git",
        "ref": f"v{version}",
    }


def test_release_checklist_keeps_static_host_and_distribution_gates_separate():
    text = RELEASE_CHECKLIST.read_text(encoding="utf-8")
    for marker in [
        "## 2. Repository gates",
        "## 3. Real Codex Host gates",
        "RESTART_REQUIRED",
        "subagents_dispatch_reader",
        "subagents_dispatch_worker",
        "## 4. Hard release blockers",
        "## 5. Repository governance before tagging",
        "## 6. Tag, distribution smoke, and GitHub Release",
        "Marketplace entry at the tag resolves the Plugin source from the same tag",
    ]:
        assert marker in text
