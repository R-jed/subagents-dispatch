from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / ".codex-plugin" / "plugin.json"
SKILLS = ROOT / "skills"
INSTALL_DOC = ROOT / "docs" / "plugin-installation.md"
PYTHON_RUNTIME_DOC = ROOT / "docs" / "python-runtime.md"
RELEASE = ROOT / "docs" / "release-checklist.md"
README_FILES = (
    ROOT / "README.md",
    ROOT / "README_EN.md",
    ROOT / "README_AI.md",
)
EVALS_README = ROOT / "evals" / "README.md"
CI = ROOT / ".github" / "workflows" / "ci.yml"
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


def test_third_party_mit_notice_remains_packaged_without_repository_pointer():
    notice = ROOT / "THIRD_PARTY_NOTICES.md"
    text = notice.read_text(encoding="utf-8")
    for phrase in (
        "MIT-licensed third-party material",
        "Copyright (c) 2026 Zhijian AI / Dapeng",
        "Permission is hereby granted",
        'THE SOFTWARE IS PROVIDED "AS IS"',
    ):
        assert phrase in text
    assert "github.com/" not in text


def test_plugin_legal_links_still_target_packaged_policy_files():
    interface = json.loads(PLUGIN.read_text(encoding="utf-8"))["interface"]
    for field, suffix in (("privacyPolicyURL", "/PRIVACY.md"), ("termsOfServiceURL", "/TERMS.md")):
        parsed = urlparse(interface[field])
        assert parsed.scheme == "https" and parsed.netloc
        assert parsed.path.endswith(suffix)
        assert (ROOT / suffix.removeprefix("/")).is_file()


def test_python_helper_runtime_keeps_portable_resolution_boundary():
    text = PYTHON_RUNTIME_DOC.read_text(encoding="utf-8")
    for phrase in (
        "Python 3.11 or newer",
        "python3",
        "python",
        "py -3.11",
        "sys.executable",
        "environment adaptation",
        "PYTHON_PREREQUISITE_UNMET",
        "actions/setup-python",
        "real Codex App task shell",
        "A single `command not found`",
    ):
        assert phrase in text


def test_readme_files_are_valid_basic_text_files():
    for path in README_FILES:
        assert path.is_file()
        raw = path.read_bytes()
        assert raw
        assert b"\x00" not in raw
        text = raw.decode("utf-8")
        assert text.strip()
        assert text.endswith("\n")


def test_evals_readme_keeps_measurement_plane_separate_from_runtime_policy():
    text = EVALS_README.read_text(encoding="utf-8")
    for phrase in (
        "not part of the normal user setup",
        "behavioral-workloads.json",
        "routing-cases.json",
        "runtime-assurance-cases.json",
        "do not control how the plugin routes or coordinates work",
    ):
        assert phrase in text


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


def test_release_docs_keep_real_host_validation_as_a_distinct_gate():
    text = RELEASE.read_text(encoding="utf-8")
    assert "Host" in text
    assert "Hook" in text
    assert "offline" in text.lower()
    assert "docs/v4/host-smoke.json" in text


def test_ci_keeps_root_plugin_layout_and_full_validation_gates():
    text = CI.read_text(encoding="utf-8")
    assert ".codex-plugin/plugin.json" in text
    assert "scripts/install-agents.py" in text
    assert "python scripts/package_integrity.py --check-generated" in text
    assert "python -m pytest -q" in text
    assert "python -m ruff check scripts tests --ignore E402" in text
