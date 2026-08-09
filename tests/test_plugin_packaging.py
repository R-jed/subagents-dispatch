from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT
PLUGIN = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".agents" / "plugins" / "marketplace.json"
SKILLS_ROOT = PLUGIN_ROOT / "skills"
MAIN_SKILL = SKILLS_ROOT / "dispatch"
DOCTOR_SKILL = SKILLS_ROOT / "doctor"
INSTALL_DOC = ROOT / "docs" / "plugin-installation.md"
POLICY = PLUGIN_ROOT / "policy-contract.json"
CANONICAL_MARKETPLACE = "codex plugin marketplace add R-jed/subagents-dispatch"
PLUGIN_ADD = "codex plugin add subagents-dispatch@subagents-dispatch"
UPGRADE = "codex plugin marketplace upgrade subagents-dispatch"
PLUGIN_REMOVE = "codex plugin remove subagents-dispatch@subagents-dispatch"
MARKETPLACE_REMOVE = "codex plugin marketplace remove subagents-dispatch"
MAIN_SKILL_ID = "subagents-dispatch"
DOCTOR_SKILL_ID = "subagents-doctor"
MAIN_DISPLAY_NAME = "Subagents Dispatch"
DOCTOR_DISPLAY_NAME = "Subagents Doctor"


def test_plugin_manifest_and_marketplace_use_canonical_identity():
    payload = json.loads(PLUGIN.read_text(encoding="utf-8"))
    version = payload["version"]
    release_ref = f"v{version}"
    assert payload["name"] == "subagents-dispatch"
    assert payload["skills"] == "./skills/"
    assert payload["repository"] == "https://github.com/R-jed/subagents-dispatch"
    assert payload["homepage"] == "https://github.com/R-jed/subagents-dispatch#readme"
    assert payload["interface"]["displayName"] == "subagents-dispatch"
    assert payload["interface"]["websiteURL"] == "https://github.com/R-jed/subagents-dispatch"
    assert {path.name for path in SKILLS_ROOT.iterdir() if path.is_dir()} == {"dispatch", "doctor"}
    assert (MAIN_SKILL / "SKILL.md").is_file()
    assert (DOCTOR_SKILL / "SKILL.md").is_file()

    market = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    assert market == {
        "name": "subagents-dispatch",
        "interface": {"displayName": "subagents-dispatch"},
        "plugins": [
            {
                "name": "subagents-dispatch",
                "source": {
                    "source": "url",
                    "url": "https://github.com/R-jed/subagents-dispatch.git",
                    "ref": release_ref,
                },
                "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                "category": "Productivity",
            }
        ],
    }


def test_skill_ids_are_product_prefixed_and_ui_names_are_distinct():
    main = (MAIN_SKILL / "SKILL.md").read_text(encoding="utf-8")
    doctor = (DOCTOR_SKILL / "SKILL.md").read_text(encoding="utf-8")
    main_ui = (MAIN_SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8")
    doctor_ui = (DOCTOR_SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8")

    assert f"name: {MAIN_SKILL_ID}" in main
    assert f"name: {DOCTOR_SKILL_ID}" in doctor
    assert "name: dispatch\n" not in main
    assert "name: doctor\n" not in doctor
    assert f'display_name: "{MAIN_DISPLAY_NAME}"' in main_ui
    assert f'display_name: "{DOCTOR_DISPLAY_NAME}"' in doctor_ui
    assert "allow_implicit_invocation: false" in main_ui
    assert "allow_implicit_invocation: false" in doctor_ui


def test_plugin_starter_prompts_do_not_invent_host_command_syntax():
    payload = json.loads(PLUGIN.read_text(encoding="utf-8"))
    prompts = "\n".join(payload["interface"]["defaultPrompt"])
    assert MAIN_DISPLAY_NAME in prompts
    assert DOCTOR_DISPLAY_NAME in prompts
    for stale in ["$dispatch", "$doctor", "/dispatch", "/doctor", "/subagents-dispatch:dispatch", "/subagents-dispatch:doctor"]:
        assert stale not in prompts


def test_root_plugin_layout_and_canonical_ci_verifier_do_not_use_removed_subdirectory():
    assert PLUGIN.is_file()
    assert (ROOT / "skills" / "dispatch" / "SKILL.md").is_file()
    stale = "plugins/subagents-dispatch"
    path = ROOT / ".github" / "workflows" / "ci.yml"
    text = path.read_text(encoding="utf-8")
    assert stale not in text, f"{path} still targets the removed plugin subdirectory"
    assert ".codex-plugin/plugin.json" in text
    assert "scripts/install-agents.py" in text


def test_plugin_brand_assets_and_supported_components():
    payload = json.loads(PLUGIN.read_text(encoding="utf-8"))
    interface = payload["interface"]
    assert interface["brandColor"] == "#2563EB"
    for field in ["composerIcon", "logo"]:
        asset = PLUGIN_ROOT / interface[field].removeprefix("./")
        assert asset.is_file() and "<svg" in asset.read_text(encoding="utf-8")
    for unsupported in ["agents", "hooks", "mcpServers", "apps"]:
        assert unsupported not in payload
    for field in ["homepage", "repository"]:
        parsed = urlparse(payload[field])
        assert parsed.scheme == "https" and parsed.netloc


def test_policy_contract_owns_the_five_packaged_profiles():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    assert policy["schema_version"] == 5
    assert set(policy["roles"]) == {"reader", "worker", "solver", "investigator", "advisor"}
    expected = {spec["profile_file"] for spec in policy["roles"].values()}
    assert len(expected) == 5
    assert {p.name for p in (PLUGIN_ROOT / "agent-profiles").glob("*.toml")} == expected
    assert all(name.startswith("subagents-dispatch-") for name in expected)
    assert all(spec["agent_type"].startswith("subagents_dispatch_") for spec in policy["roles"].values())


def test_third_party_mit_notice_is_packaged_without_repository_pointer():
    notice = PLUGIN_ROOT / "THIRD_PARTY_NOTICES.md"
    assert notice.is_file()
    text = notice.read_text(encoding="utf-8")
    for phrase in [
        "MIT-licensed third-party material",
        "Copyright (c) 2026 Zhijian AI / Dapeng",
        "Permission is hereby granted",
        'THE SOFTWARE IS PROVIDED "AS IS"',
    ]:
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
    for phrase in [
        "codex --version",
        "codex doctor --json",
        "codex plugin marketplace list --json",
        "codex plugin list --available --json",
        "../../scripts/install-agents.py",
        'python "$installer" --check',
        CANONICAL_MARKETPLACE,
        PLUGIN_ADD,
        UPGRADE,
        DOCTOR_SKILL_ID,
    ]:
        assert phrase in text
    assert "Diagnosis is read-only by default" in text
    assert "explicitly asks" in text
    assert "Never edit Codex config files directly" in text
    assert "Do not use `marketplace remove` as a generic reset" in text
    assert "start a fresh Codex session" in text


def test_install_doc_contains_current_lifecycle_and_app_skill_menu_contract():
    text = INSTALL_DOC.read_text(encoding="utf-8")
    for phrase in [
        CANONICAL_MARKETPLACE,
        PLUGIN_ADD,
        "## First delegated run",
        "five managed custom-Agent profiles",
        "automatically provisions",
        "RESTART_REQUIRED",
        "does not attempt to spawn",
        "fresh Codex task/session",
        "fails closed",
        "## Update",
        UPGRADE,
        "## Uninstall",
        PLUGIN_REMOVE,
        MARKETPLACE_REMOVE,
        "type `/` to open the Skill menu",
        MAIN_DISPLAY_NAME,
        DOCTOR_DISPLAY_NAME,
        "exact slash entry rendered by the App is a Host/UI fact",
    ]:
        assert phrase in text
    assert "asks permission" not in text


def test_public_readmes_use_prefixed_app_skill_names_without_inventing_exact_slash_entry():
    version = json.loads(PLUGIN.read_text(encoding="utf-8"))["version"]
    for name in ["README.md", "README_EN.md"]:
        text = (ROOT / name).read_text(encoding="utf-8")
        assert version in text
        assert MAIN_DISPLAY_NAME in text
        assert DOCTOR_DISPLAY_NAME in text
        assert CANONICAL_MARKETPLACE in text
        assert PLUGIN_ADD in text
        assert UPGRADE in text
        assert PLUGIN_REMOVE in text
        assert MARKETPLACE_REMOVE in text
        assert "$dispatch" not in text
        assert "$doctor" not in text

    ai = (ROOT / "README_AI.md").read_text(encoding="utf-8")
    assert version in ai
    assert MAIN_SKILL_ID in ai
    assert DOCTOR_SKILL_ID in ai
    assert MAIN_DISPLAY_NAME in ai
    assert DOCTOR_DISPLAY_NAME in ai
    assert "docs/plugin-installation.md" in ai
    assert "RESTART_REQUIRED" in ai
    assert "Do not invent a Codex App slash-command string" in ai
    for command in [CANONICAL_MARKETPLACE, PLUGIN_ADD, UPGRADE, PLUGIN_REMOVE]:
        assert command not in ai
