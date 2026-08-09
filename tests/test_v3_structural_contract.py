from __future__ import annotations

import json
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
SKILLS = ROOT / "skills"

SKILL_IDS = {"dispatch", "preview", "status", "steer", "takeover", "doctor"}
CONTRACT_FILES = {
    "policy.json",
    "routing.md",
    "interaction.md",
    "state.md",
    "receipt.md",
    "team-plan.md",
    "recovery.md",
    "guardrails.md",
    "handoff.md",
    "final-review.md",
}


def test_root_contracts_are_the_only_active_canonical_owners():
    assert {path.name for path in CONTRACTS.iterdir() if path.is_file()} == CONTRACT_FILES
    assert not (ROOT / "policy-contract.json").exists()
    assert not (SKILLS / "dispatch" / "references").exists()


def test_six_explicit_thin_skills_have_exact_ids_and_metadata():
    assert {path.name for path in SKILLS.iterdir() if path.is_dir()} == SKILL_IDS
    for skill_id in SKILL_IDS:
        skill = SKILLS / skill_id
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        assert match
        assert yaml.safe_load(match.group(1))["name"] == skill_id

        metadata = yaml.safe_load((skill / "agents" / "openai.yaml").read_text(encoding="utf-8"))
        assert metadata["policy"]["allow_implicit_invocation"] is False


def test_machine_policy_uses_semantic_writer_coordination():
    policy = json.loads((CONTRACTS / "policy.json").read_text(encoding="utf-8"))
    assert policy["delegation"] == {"max_depth": 1}
    assert policy["write_coordination"] == {
        "mode": "single_writer",
        "scope": "canonical_workspace",
    }
    assert "max_active_writers_per_workspace" not in json.dumps(policy)
    assert set(policy["roles"]) == {"reader", "worker", "solver", "investigator", "advisor"}


def test_plugin_starter_prompts_cover_all_skills_without_guessed_slash_syntax():
    manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    prompts = "\n".join(manifest["interface"]["defaultPrompt"])
    for label in ["Dispatch", "Preview", "Status", "Steer", "Takeover", "Doctor"]:
        assert label in prompts
    assert not re.search(r"(?<![A-Za-z0-9_.-])/(?:dispatch|preview|status|steer|takeover|doctor)\b", prompts, re.I)
