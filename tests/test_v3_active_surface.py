from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def active_surface_files() -> list[Path]:
    paths = [
        ROOT / "README.md",
        ROOT / "README_EN.md",
        ROOT / "README_AI.md",
        ROOT / "PRIVACY.md",
        ROOT / ".codex-plugin" / "plugin.json",
        ROOT / ".agents" / "plugins" / "marketplace.json",
    ]
    paths.extend(sorted((ROOT / "docs").glob("*.md")))
    paths.extend(sorted((ROOT / "contracts").glob("*.md")))
    paths.extend(sorted((ROOT / "skills").glob("*/SKILL.md")))
    return paths


def test_active_v3_surfaces_have_no_obsolete_paths_control_grammar_or_policy_phrases():
    forbidden = {
        "skills/dispatch/references": "obsolete Skill-owned shared contract path",
        "policy-contract.json": "obsolete root policy path",
        "Zero children is normal": "numeric zero-child framing",
        "max_active_writers_per_workspace": "numeric writer-capacity policy",
        "/dispatch preview": "obsolete payload control grammar",
        "/dispatch status": "obsolete payload control grammar",
        "/dispatch steer": "obsolete payload control grammar",
        "/dispatch takeover": "obsolete payload control grammar",
        "$dispatch": "obsolete command identity",
        "A green branch run does not replace the pull-request merge-result run": "obsolete PR-only governance",
        "Require pull requests": "obsolete PR-only governance",
        "Execution Receipt": "obsolete receipt name",
        "· complete · no retry": "obsolete English receipt state axis",
        "· 完成 · 未重试": "obsolete Chinese receipt state axis",
        "无需最终复核": "obsolete negative review wording",
    }

    defects: list[str] = []
    for path in active_surface_files():
        text = path.read_text(encoding="utf-8")
        for phrase, reason in forbidden.items():
            if phrase in text:
                defects.append(f"{path.relative_to(ROOT)}: {reason}: {phrase}")

    assert defects == []


def test_active_v3_surfaces_do_not_publish_unverified_namespaced_slash_syntax():
    defects: list[str] = []
    for path in active_surface_files():
        text = path.read_text(encoding="utf-8")
        if "/subagents-dispatch:" in text:
            defects.append(str(path.relative_to(ROOT)))
    assert defects == []
