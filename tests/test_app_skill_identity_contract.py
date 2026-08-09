from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Active product surfaces only. Historical changelog text and regression-test source
# are intentionally outside this scan.
ACTIVE_FILES = [
    ROOT / "README.md",
    ROOT / "README_EN.md",
    ROOT / "README_AI.md",
    *sorted((ROOT / "docs").glob("*.md")),
    *sorted((ROOT / "skills").glob("**/*.md")),
    *sorted((ROOT / "skills").glob("**/*.yaml")),
    *sorted((ROOT / "evals").glob("*.json")),
    *sorted((ROOT / "scripts").glob("*.py")),
]

FORBIDDEN_LITERAL_ENTRYPOINTS = (
    "$dispatch",
    "$doctor",
    "/subagents-dispatch:dispatch",
    "/subagents-dispatch:doctor",
)

# Avoid matching repository paths such as skills/dispatch. A command token starts
# at a non-path boundary, while a path slash is preceded by a word/path char.
FORBIDDEN_BARE_SLASH = re.compile(r"(?<![A-Za-z0-9_.-])/(?:dispatch|doctor)\b")


def test_active_surfaces_do_not_publish_unverified_or_legacy_skill_entrypoints():
    violations: list[str] = []
    for path in ACTIVE_FILES:
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_LITERAL_ENTRYPOINTS:
            if token in text:
                violations.append(f"{path.relative_to(ROOT)} contains {token!r}")
        for match in FORBIDDEN_BARE_SLASH.finditer(text):
            violations.append(
                f"{path.relative_to(ROOT)} contains unverified bare App entry {match.group(0)!r}"
            )
    assert not violations, "Active product surfaces publish stale/unverified Skill entrypoints:\n" + "\n".join(violations)


def test_active_surfaces_keep_prefixed_stable_skill_identity_and_human_ui_gate():
    dispatch = (ROOT / "skills" / "dispatch" / "SKILL.md").read_text(encoding="utf-8")
    doctor = (ROOT / "skills" / "doctor" / "SKILL.md").read_text(encoding="utf-8")
    release = (ROOT / "docs" / "release-checklist.md").read_text(encoding="utf-8")
    ai_reference = (ROOT / "README_AI.md").read_text(encoding="utf-8")

    assert "name: subagents-dispatch" in dispatch
    assert "name: subagents-doctor" in doctor
    assert "Subagents Dispatch" in dispatch
    assert "Subagents Doctor" in doctor
    assert "Direct human Codex App observation" in release
    assert "cannot by itself close a Host/UI gate" in release
    assert "record the exact rendered entry labels" in release
    assert "post-selection presentation" in release
    assert "If the App does not render a literal slash-command string after selection" in release
    assert "Do not invent a Codex App slash-command string" in ai_reference
