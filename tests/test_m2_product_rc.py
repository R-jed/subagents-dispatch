from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALL_DOC = ROOT / "docs" / "plugin-installation.md"
DOCTOR_SKILL = ROOT / "skills" / "doctor" / "SKILL.md"
README_CN = ROOT / "README.md"
README_EN = ROOT / "README_EN.md"
README_AI = ROOT / "README_AI.md"
REPO_ARCH = ROOT / "docs" / "repository-architecture.md"
CI = ROOT / ".github" / "workflows" / "ci.yml"
UNINSTALLER = ROOT / "scripts" / "uninstall-agents.py"

PLUGIN_REMOVE = "codex plugin remove subagents-dispatch@subagents-dispatch"
MARKETPLACE_REMOVE = "codex plugin marketplace remove subagents-dispatch"


def test_product_rc_has_one_ownership_aware_managed_profile_uninstaller():
    assert UNINSTALLER.is_file()
    install = INSTALL_DOC.read_text(encoding="utf-8")
    doctor = DOCTOR_SKILL.read_text(encoding="utf-8")
    ai = README_AI.read_text(encoding="utf-8")
    architecture = REPO_ARCH.read_text(encoding="utf-8")

    for text in (install, doctor, ai, architecture):
        assert "scripts/uninstall-agents.py" in text or "../../scripts/uninstall-agents.py" in text
    assert "ownership-aware" in install
    assert "ownership-aware" in doctor
    assert "managed Agent profile removal" in ai
    assert "managed Agent profile removal" in architecture


def test_public_uninstall_flow_removes_managed_profiles_before_plugin_registration():
    for path in (INSTALL_DOC, README_CN, README_EN):
        text = path.read_text(encoding="utf-8")
        plugin_index = text.index(PLUGIN_REMOVE)
        if path == INSTALL_DOC:
            cleanup_index = text.index("scripts/uninstall-agents.py")
        elif path == README_CN:
            cleanup_index = text.index("明确要求卸载 subagents-dispatch 的 managed profiles")
        else:
            cleanup_index = text.index("explicitly ask it to uninstall the subagents-dispatch managed profiles")
        assert cleanup_index < plugin_index
        assert MARKETPLACE_REMOVE in text


def test_public_uninstall_flow_does_not_publish_manual_managed_profile_rm():
    forbidden = [
        "rm ~/.codex/agents/subagents-dispatch-reader.toml",
        "rm ~/.codex/agents/subagents-dispatch-worker.toml",
        "rm ~/.codex/agents/subagents-dispatch-solver.toml",
        "rm ~/.codex/agents/subagents-dispatch-investigator.toml",
        "rm ~/.codex/agents/subagents-dispatch-advisor.toml",
        "rm ~/.codex/.subagents-dispatch-agents.json",
    ]
    for path in (INSTALL_DOC, README_CN, README_EN, DOCTOR_SKILL):
        text = path.read_text(encoding="utf-8")
        for command in forbidden:
            assert command not in text


def test_ci_runs_uninstall_reinstall_lifecycle_and_tag_parity_gate():
    text = CI.read_text(encoding="utf-8")
    assert "python scripts/uninstall-agents.py --codex-home \"$target\"" in text
    assert "managed Agent check unexpectedly passed after uninstall" in text
    assert text.count("python scripts/install-agents.py --codex-home \"$target\" --check") >= 3
    assert "startsWith(github.ref, 'refs/tags/')" in text
    assert 'test "$GITHUB_REF_NAME" = "v$version"' in text
