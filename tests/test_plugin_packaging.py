from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / ".codex-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".agents" / "plugins" / "marketplace.json"
SKILLS_ROOT = ROOT / "skills"
MAIN_SKILL = SKILLS_ROOT / "dispatch"
DOCTOR_SKILL = SKILLS_ROOT / "doctor"
INSTALL_DOC = ROOT / "docs" / "plugin-installation.md"
POLICY = ROOT / "policy-contract.json"
CANONICAL_MARKETPLACE = "codex plugin marketplace add R-jed/subagents-dispatch"
PLUGIN_ADD = "codex plugin add subagents-dispatch@subagents-dispatch"
UPGRADE = "codex plugin marketplace upgrade subagents-dispatch"
PLUGIN_REMOVE = "codex plugin remove subagents-dispatch@subagents-dispatch"
MARKETPLACE_REMOVE = "codex plugin marketplace remove subagents-dispatch"
USER_COMMAND_DISPATCH = "$dispatch"
USER_COMMAND_DOCTOR = "$doctor"


def test_plugin_manifest_and_marketplace_use_canonical_identity():
    payload = json.loads(PLUGIN.read_text(encoding="utf-8"))
    version = payload["version"]
    assert payload["name"] == "subagents-dispatch"
    assert payload["skills"] == "./skills/"
    assert payload["repository"] == "https://github.com/R-jed/subagents-dispatch"
    assert payload["homepage"] == "https://github.com/R-jed/subagents-dispatch#readme"
    assert payload["interface"]["displayName"] == "subagents-dispatch"
    assert {path.name for path in SKILLS_ROOT.iterdir() if path.is_dir()} == {"dispatch", "doctor"}
    assert (MAIN_SKILL / "SKILL.md").is_file()
    assert (DOCTOR_SKILL / "SKILL.md").is_file()

    market = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    assert market["name"] == "subagents-dispatch"
    assert market["plugins"][0]["name"] == "subagents-dispatch"
    assert market["plugins"][0]["source"] == {
        "source": "url",
        "url": "https://github.com/R-jed/subagents-dispatch.git",
        "ref": f"v{version}",
    }


def test_root_plugin_layout_and_canonical_ci_verifier_do_not_use_removed_subdirectory():
    assert PLUGIN.is_file()
    assert (ROOT / "skills" / "dispatch" / "SKILL.md").is_file()
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "plugins/subagents-dispatch" not in text
    assert ".codex-plugin/plugin.json" in text
    assert "scripts/install-agents.py" in text


def test_plugin_brand_assets_and_supported_components():
    payload = json.loads(PLUGIN.read_text(encoding="utf-8"))
    interface = payload["interface"]
    assert interface["brandColor"] == "#2563EB"
    for field in ["composerIcon", "logo"]:
        asset = ROOT / interface[field].removeprefix("./")
        assert asset.is_file() and "<svg" in asset.read_text(encoding="utf-8")
    for unsupported in ["agents", "hooks", "mcpServers", "apps"]:
        assert unsupported not in payload
    for field in ["homepage", "repository"]:
        parsed = urlparse(payload[field])
        assert parsed.scheme == "https" and parsed.netloc
    prompts = interface["defaultPrompt"]
    assert any(USER_COMMAND_DISPATCH in prompt for prompt in prompts)
    assert any(USER_COMMAND_DOCTOR in prompt for prompt in prompts)
    assert all("/subagents-dispatch:" not in prompt for prompt in prompts)


def test_policy_contract_owns_the_five_packaged_profiles():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    expected = {spec["profile_file"] for spec in policy["roles"].values()}
    assert len(expected) == 5
    assert {p.name for p in (ROOT / "agent-profiles").glob("*.toml")} == expected
    assert all(name.startswith("subagents-dispatch-") for name in expected)
    assert all(spec["agent_type"].startswith("subagents_dispatch_") for spec in policy["roles"].values())


def test_third_party_mit_notice_is_packaged_without_repository_pointer():
    notice = ROOT / "THIRD_PARTY_NOTICES.md"
    text = notice.read_text(encoding="utf-8")
    for phrase in ["MIT-licensed third-party material", "Copyright (c) 2026 Zhijian AI / Dapeng", "Permission is hereby granted", 'THE SOFTWARE IS PROVIDED "AS IS"']:
        assert phrase in text
    assert "github.com/" not in text


def test_main_skill_owns_profile_readiness_before_delegated_execution():
    text = (MAIN_SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "../../scripts/install-agents.py" in text
    assert 'python "$installer" --check' in text
    assert "RESTART_REQUIRED" in text
    assert "do not attempt spawn_agent in this task" in text
    assert "USER_ACTION_REQUIRED" in text
    assert "On the fresh task, inspect exact role availability again" in text
    assert "do not substitute another role" in text


def test_doctor_reuses_supported_diagnostics_and_existing_installer():
    text = (DOCTOR_SKILL / "SKILL.md").read_text(encoding="utf-8")
    for phrase in ["codex --version", "codex doctor --json", "codex plugin marketplace list --json", "codex plugin list --available --json", "../../scripts/install-agents.py", 'python "$installer" --check', CANONICAL_MARKETPLACE, PLUGIN_ADD, UPGRADE, "$doctor"]:
        assert phrase in text
    assert "Diagnosis is read-only by default" in text
    assert "explicitly asks" in text
    assert "Never edit Codex config files directly" in text
    assert "Do not use `marketplace remove` as a generic reset" in text
    assert "start a fresh Codex session" in text


def test_install_doc_contains_current_install_update_uninstall_and_skill_contract():
    text = INSTALL_DOC.read_text(encoding="utf-8")
    for phrase in [CANONICAL_MARKETPLACE, PLUGIN_ADD, "## First delegated run", "five managed custom-Agent profiles", "automatically provisions", "RESTART_REQUIRED", "does not attempt to spawn", "fresh Codex task/session", "fails closed", "## Update", UPGRADE, "## Uninstall", PLUGIN_REMOVE, MARKETPLACE_REMOVE, USER_COMMAND_DISPATCH, USER_COMMAND_DOCTOR, "/skills"]:
        assert phrase in text
    assert "asks permission" not in text


def test_public_readmes_and_ai_reference_use_skill_mentions():
    version = json.loads(PLUGIN.read_text(encoding="utf-8"))["version"]
    for name in ["README.md", "README_EN.md"]:
        text = (ROOT / name).read_text(encoding="utf-8")
        assert version in text
        assert USER_COMMAND_DISPATCH in text
        assert USER_COMMAND_DOCTOR in text
        assert "/skills" in text
        assert CANONICAL_MARKETPLACE in text
        assert PLUGIN_ADD in text
        assert UPGRADE in text
        assert PLUGIN_REMOVE in text
        assert MARKETPLACE_REMOVE in text

    ai = (ROOT / "README_AI.md").read_text(encoding="utf-8")
    assert version in ai
    assert USER_COMMAND_DISPATCH in ai
    assert USER_COMMAND_DOCTOR in ai
    assert "docs/plugin-installation.md" in ai
    assert "RESTART_REQUIRED" in ai
