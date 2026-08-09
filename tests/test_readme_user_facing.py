import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZH = (ROOT / "README.md").read_text(encoding="utf-8")
EN = (ROOT / "README_EN.md").read_text(encoding="utf-8")
AI = (ROOT / "README_AI.md").read_text(encoding="utf-8")
EVALS = (ROOT / "evals" / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
VERSION = MANIFEST["version"]
CANONICAL_MARKETPLACE = "codex plugin marketplace add R-jed/subagents-dispatch"
PLUGIN_ADD = "codex plugin add subagents-dispatch@subagents-dispatch"
UPGRADE = "codex plugin marketplace upgrade subagents-dispatch"
SKILL_IDS = ["dispatch", "preview", "status", "steer", "takeover", "doctor"]
README_LOGO = "assets/subagents-dispatch-banner.png"


def test_public_readmes_explain_the_current_repository_layout():
    assert "## 项目结构" in ZH
    assert "## Repository layout" in EN
    for text in [ZH, EN]:
        for path in [
            ".agents/plugins/",
            ".codex-plugin/",
            "agent-profiles/",
            "contracts/",
            "skills/",
            "dispatch/",
            "preview/",
            "status/",
            "steer/",
            "takeover/",
            "doctor/",
            "docs/",
            "evals/",
            "scripts/",
            "tests/",
        ]:
            assert path in text
        assert "├── dispatch/" in text
        assert "└── doctor/" in text


def test_public_readmes_link_deeper_docs():
    for text in [ZH, EN]:
        for link in [
            "README_AI.md",
            "docs/plugin-installation.md",
            "docs/architecture.md",
            "docs/native-subagent-runtime.md",
        ]:
            assert link in text


def test_public_readme_visual_surface_uses_canonical_plugin_assets():
    plugin_assets = ROOT / "assets"
    assert (plugin_assets / "subagents-dispatch-banner.png").is_file()
    assert not (ROOT / "docs" / "logo-light.svg").exists()
    assert not (ROOT / "docs" / "logo-dark.svg").exists()

    for text in [ZH, EN]:
        assert "<picture" not in text
        assert README_LOGO in text
        assert "#gh-light-mode-only" not in text
        assert "#gh-dark-mode-only" not in text
        assert "docs/logo-" not in text
        for line in text.splitlines():
            if "<img" in line and "subagents-dispatch-banner" not in line and "shields.io" not in line:
                raise AssertionError(f"Unexpected README image: {line}")


def test_ai_reference_is_an_index_to_canonical_policy_owners():
    for phrase in [
        "R-jed/subagents-dispatch",
        "Repo marketplace id: subagents-dispatch",
        f"Current version:     {VERSION}",
        "Distribution:        Codex Plugin",
        "contracts/interaction.md",
        "contracts/routing.md",
        "contracts/handoff.md",
        "contracts/team-plan.md",
        "contracts/recovery.md",
        "contracts/guardrails.md",
        "contracts/final-review.md",
        "contracts/policy.json",
        "skills/<id>/SKILL.md",
        "docs/plugin-installation.md",
        "scripts/policy.py",
        "Do not invent a Codex App slash-command string",
    ]:
        assert phrase in AI
    for skill_id in SKILL_IDS:
        assert f"`{skill_id}`" in AI
    assert "not a second copy of runtime policy" in AI
    for command in [CANONICAL_MARKETPLACE, PLUGIN_ADD, UPGRADE, "/subagents-dispatch:dispatch", "$dispatch"]:
        assert command not in AI


def test_evals_readme_identifies_measurement_boundary_and_canonical_owners():
    for phrase in [
        "not part of the normal user setup",
        "behavioral-workloads.json",
        "behavioral-result.schema.json",
        "routing-cases.json",
        "coordination-cases.json",
        "interaction-cases.json",
        "runtime-assurance-cases.json",
        "do not control how the plugin routes or coordinates work",
        "`interaction.md`",
        "`routing.md`",
        "`handoff.md`",
        "`team-plan.md`",
        "`recovery.md`",
        "`guardrails.md`",
        "`final-review.md`",
        "`policy.json`",
    ]:
        assert phrase in EVALS
