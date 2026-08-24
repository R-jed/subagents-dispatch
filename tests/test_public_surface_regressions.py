from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / ".codex-plugin" / "plugin.json"
SKILLS = ROOT / "skills"
INSTALL_DOC = ROOT / "docs" / "plugin-installation.md"
README_FILES = (
    ROOT / "README.md",
    ROOT / "README_EN.md",
    ROOT / "README_AI.md",
    ROOT / "evals" / "README.md",
)
PUBLIC_SKILLS = ("orchestrate", "doctor")


def test_v4_public_surface_never_reintroduces_retired_skill_directories():
    assert {path.name for path in SKILLS.iterdir() if path.is_dir()} == set(PUBLIC_SKILLS)
    for retired in ("dispatch", "preview", "status", "steer", "takeover"):
        assert not (SKILLS / retired).exists()


def test_v4_skill_metadata_keeps_explicit_human_invocation_boundary():
    for skill_id in PUBLIC_SKILLS:
        payload = yaml.safe_load(
            (SKILLS / skill_id / "agents" / "openai.yaml").read_text(encoding="utf-8")
        )
        interface = payload["interface"]
        assert interface["display_name"] == f"Subagents Dispatch: {skill_id.title()}"
        assert 25 <= len(interface["short_description"]) <= 64
        assert skill_id.title() in interface["default_prompt"]
        assert payload["policy"]["allow_implicit_invocation"] is False


def test_third_party_mit_notice_remains_in_license_without_dead_source_dependency():
    assert not (ROOT / "THIRD_PARTY_NOTICES.md").exists()
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    for phrase in (
        "Copyright (c) 2026 Zhijian AI / Dapeng",
        "Permission is hereby granted",
        'THE SOFTWARE IS PROVIDED "AS IS"',
        "8b9abec4b353c70f04e8409302169309544bae95",
    ):
        assert phrase in license_text
    assert not (ROOT / "scripts" / "validate_team_plan.py").exists()


def test_plugin_no_longer_tracks_repository_privacy_or_terms_files():
    interface = json.loads(PLUGIN.read_text(encoding="utf-8"))["interface"]
    for field in ("privacyPolicyURL", "termsOfServiceURL"):
        assert field not in interface
    assert not (ROOT / "PRIVACY.md").exists()
    assert not (ROOT / "TERMS.md").exists()


def test_readme_files_are_valid_basic_text_files():
    for path in README_FILES:
        assert path.is_file()
        raw = path.read_bytes()
        assert raw
        assert b"\x00" not in raw
        text = raw.decode("utf-8")
        assert text.strip()
        assert text.endswith("\n")


def test_public_uninstall_docs_forbid_manual_managed_profile_removal():
    forbidden = (
        "rm ~/.codex/agents/subagents-dispatch-reader.toml",
        "rm ~/.codex/agents/subagents-dispatch-worker.toml",
        "rm ~/.codex/agents/subagents-dispatch-solver.toml",
        "rm ~/.codex/agents/subagents-dispatch-investigator.toml",
        "rm ~/.codex/agents/subagents-dispatch-advisor.toml",
        "rm ~/.codex/.subagents-dispatch-agents.json",
    )
    for path in (INSTALL_DOC, SKILLS / "doctor" / "SKILL.md"):
        text = path.read_text(encoding="utf-8")
        assert all(command not in text for command in forbidden)
