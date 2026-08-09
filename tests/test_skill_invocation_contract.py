from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DISPATCH = "$dispatch"
DOCTOR = "$doctor"
PICKER = "/skills"
LEGACY_NAMESPACED = ("/subagents-dispatch:dispatch", "/subagents-dispatch:doctor")
BARE_DISPATCH = re.compile(r"(?<![\w$])/dispatch(?=\s|`|$)")
BARE_DOCTOR = re.compile(r"(?<![\w$])/doctor(?=\s|`|$)")

ACTIVE_SURFACES = [
    ROOT / "README.md",
    ROOT / "README_EN.md",
    ROOT / "README_AI.md",
    ROOT / ".codex-plugin" / "plugin.json",
    ROOT / "skills" / "dispatch" / "SKILL.md",
    ROOT / "skills" / "dispatch" / "agents" / "openai.yaml",
    ROOT / "skills" / "doctor" / "SKILL.md",
    ROOT / "skills" / "doctor" / "agents" / "openai.yaml",
    ROOT / "skills" / "dispatch" / "references" / "interaction.md",
    ROOT / "skills" / "dispatch" / "references" / "guardrails.md",
    ROOT / "docs" / "plugin-installation.md",
    ROOT / "docs" / "architecture.md",
    ROOT / "docs" / "native-subagent-runtime.md",
    ROOT / "docs" / "behavioral-evals.md",
    ROOT / "docs" / "release-checklist.md",
    ROOT / "evals" / "interaction-cases.json",
    ROOT / "evals" / "behavioral-workloads.json",
]


def test_plugin_and_skill_ui_metadata_use_native_skill_mentions():
    plugin = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    prompts = plugin["interface"]["defaultPrompt"]
    assert any(DISPATCH in prompt for prompt in prompts)
    assert any(DOCTOR in prompt for prompt in prompts)

    dispatch_ui = yaml.safe_load((ROOT / "skills" / "dispatch" / "agents" / "openai.yaml").read_text(encoding="utf-8"))
    doctor_ui = yaml.safe_load((ROOT / "skills" / "doctor" / "agents" / "openai.yaml").read_text(encoding="utf-8"))
    assert DISPATCH in dispatch_ui["interface"]["default_prompt"]
    assert DOCTOR in doctor_ui["interface"]["default_prompt"]
    assert dispatch_ui["policy"]["allow_implicit_invocation"] is False
    assert doctor_ui["policy"]["allow_implicit_invocation"] is False


def test_active_surfaces_do_not_advertise_stale_slash_entrypoints():
    failures: list[str] = []
    for path in ACTIVE_SURFACES:
        text = path.read_text(encoding="utf-8")
        if any(value in text for value in LEGACY_NAMESPACED):
            failures.append(f"{path}: legacy namespaced slash identity")
        if BARE_DISPATCH.search(text):
            failures.append(f"{path}: bare /dispatch entrypoint")
        if BARE_DOCTOR.search(text):
            failures.append(f"{path}: bare /doctor entrypoint")
    assert not failures, "\n".join(failures)


def test_public_surfaces_explain_skill_picker_and_explicit_mentions():
    for path in [ROOT / "README.md", ROOT / "README_EN.md", ROOT / "docs" / "plugin-installation.md"]:
        text = path.read_text(encoding="utf-8")
        assert DISPATCH in text
        assert DOCTOR in text
        assert PICKER in text


def test_release_gate_uses_registry_discovery_not_bare_slash_discovery():
    text = (ROOT / "docs" / "release-checklist.md").read_text(encoding="utf-8")
    assert "Skill registry" in text
    assert "explicit invocation $dispatch" in text
    assert "explicit invocation $doctor" in text
    assert "Bare `/dispatch` and `/doctor` slash commands are not a Skill-discovery requirement" in text
