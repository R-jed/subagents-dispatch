from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT
PLUGIN = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".agents" / "plugins" / "marketplace.json"
SKILLS_ROOT = PLUGIN_ROOT / "skills"
SKILL_IDS = {"dispatch", "preview", "status", "steer", "takeover", "doctor"}
INSTALL_DOC = ROOT / "docs" / "plugin-installation.md"
PYTHON_RUNTIME_DOC = ROOT / "docs" / "python-runtime.md"
POLICY = PLUGIN_ROOT / "contracts" / "policy.json"
CANONICAL_MARKETPLACE = "codex plugin marketplace add R-jed/subagents-dispatch"
PLUGIN_ADD = "codex plugin add subagents-dispatch@subagents-dispatch"
UPGRADE = "codex plugin marketplace upgrade subagents-dispatch"
PLUGIN_REMOVE = "codex plugin remove subagents-dispatch@subagents-dispatch"
MARKETPLACE_REMOVE = "codex plugin marketplace remove subagents-dispatch"


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
    assert {path.name for path in SKILLS_ROOT.iterdir() if path.is_dir()} == SKILL_IDS
    for skill_id in SKILL_IDS:
        assert (SKILLS_ROOT / skill_id / "SKILL.md").is_file()

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


def test_skill_ids_and_ui_names_are_explicit_and_distinct():
    for skill_id in SKILL_IDS:
        root = SKILLS_ROOT / skill_id
        skill = (root / "SKILL.md").read_text(encoding="utf-8")
        ui = (root / "agents" / "openai.yaml").read_text(encoding="utf-8")
        assert f"name: {skill_id}\n" in skill
        assert f'display_name: "Subagents Dispatch: {skill_id.title()}"' in ui
        assert "allow_implicit_invocation: false" in ui


def test_plugin_starter_prompts_do_not_invent_host_command_syntax():
    payload = json.loads(PLUGIN.read_text(encoding="utf-8"))
    prompts = "\n".join(payload["interface"]["defaultPrompt"])
    for skill_id in SKILL_IDS:
        assert skill_id.title() in prompts
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
    assert policy["schema_version"] == 6
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


def test_dispatch_skill_is_a_thin_adapter_to_canonical_contracts():
    text = (SKILLS_ROOT / "dispatch" / "SKILL.md").read_text(encoding="utf-8")
    for name in ["policy.json", "routing.md", "guardrails.md", "state.md", "team-plan.md", "recovery.md", "handoff.md", "final-review.md", "receipt.md"]:
        assert f"../../contracts/{name}" in text
    assert "../../docs/python-runtime.md" in text
    assert "Python 3.11+" in text


def test_doctor_reuses_supported_diagnostics_and_existing_installer():
    text = (SKILLS_ROOT / "doctor" / "SKILL.md").read_text(encoding="utf-8")
    for phrase in [
        "../../contracts/policy.json",
        "../../contracts/state.md",
        "../../contracts/guardrails.md",
        "../../docs/python-runtime.md",
        "../../scripts/doctor.py",
        "../../scripts/install-agents.py",
        "../../scripts/runtime-evidence.py",
    ]:
        assert phrase in text
    assert "Diagnosis is read-only by default" in text
    assert "explicit user intent" in text
    assert "Do not edit Codex config files directly" in text
    assert "<python-3.11+> ../../scripts/inspect-agent-runtime.py" in text
    assert "python ../../scripts/inspect-agent-runtime.py" not in text


def test_install_doc_contains_current_lifecycle_and_app_skill_menu_contract():
    text = INSTALL_DOC.read_text(encoding="utf-8")
    for phrase in [
        CANONICAL_MARKETPLACE,
        PLUGIN_ADD,
        "## Python helper prerequisite",
        "Python 3.11 or newer",
        "python-runtime.md",
        "PYTHON_PREREQUISITE_UNMET",
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
        "six explicit Skill identities",
        "Dispatch",
        "Preview",
        "Status",
        "Steer",
        "Takeover",
        "Doctor",
        "exact slash entry rendered by the App is a Host/UI fact",
    ]:
        assert phrase in text
    assert "asks permission" not in text


def test_python_helper_runtime_declares_portable_resolution_and_ci_boundary():
    assert PYTHON_RUNTIME_DOC.is_file()
    text = PYTHON_RUNTIME_DOC.read_text(encoding="utf-8")
    for phrase in [
        "Python 3.11 or newer",
        "python3",
        "python",
        "py -3.11",
        "sys.executable",
        "environment adaptation",
        "PYTHON_PREREQUISITE_UNMET",
        "actions/setup-python",
        "real Codex App task shell",
    ]:
        assert phrase in text
    assert "A single `command not found`" in text


def test_public_readmes_use_explicit_skill_names_without_inventing_exact_slash_entry():
    version = json.loads(PLUGIN.read_text(encoding="utf-8"))["version"]
    for name in ["README.md", "README_EN.md"]:
        text = (ROOT / name).read_text(encoding="utf-8")
        assert version in text
        for skill_id in SKILL_IDS:
            assert skill_id.title() in text
        assert CANONICAL_MARKETPLACE in text
        assert PLUGIN_ADD in text
        assert UPGRADE in text
        assert PLUGIN_REMOVE in text
        assert MARKETPLACE_REMOVE in text
        assert "$dispatch" not in text
        assert "$doctor" not in text

    ai = (ROOT / "README_AI.md").read_text(encoding="utf-8")
    assert version in ai
    for skill_id in SKILL_IDS:
        assert f"`{skill_id}`" in ai
    assert "docs/plugin-installation.md" in ai
    assert "Do not invent a Codex App slash-command string" in ai
    for command in [CANONICAL_MARKETPLACE, PLUGIN_ADD, UPGRADE, PLUGIN_REMOVE]:
        assert command not in ai