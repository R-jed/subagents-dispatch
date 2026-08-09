from __future__ import annotations

import json
import tomllib
from pathlib import Path
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT
MANIFEST = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
SKILLS_ROOT = PLUGIN_ROOT / "skills"
SKILL_IDS = ["dispatch", "preview", "status", "steer", "takeover", "doctor"]
POLICY = PLUGIN_ROOT / "contracts" / "policy.json"


def test_plugin_manifest_has_public_legal_links_and_stays_skills_only():
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    interface = payload["interface"]
    assert payload["name"] == "subagents-dispatch"
    assert payload["skills"] == "./skills/"
    for unsupported_component in ["mcpServers", "apps", "hooks"]:
        assert unsupported_component not in payload
    for field, suffix in [
        ("privacyPolicyURL", "/PRIVACY.md"),
        ("termsOfServiceURL", "/TERMS.md"),
    ]:
        parsed = urlparse(interface[field])
        assert parsed.scheme == "https" and parsed.netloc
        assert parsed.path.endswith(suffix)
    assert (ROOT / "PRIVACY.md").is_file()
    assert (ROOT / "TERMS.md").is_file()


def test_plugin_starter_prompts_cover_all_skills_without_inventing_app_command_syntax():
    prompts = json.loads(MANIFEST.read_text(encoding="utf-8"))["interface"]["defaultPrompt"]
    assert len(prompts) == len(SKILL_IDS)
    for skill_id in SKILL_IDS:
        assert any(skill_id.title() in prompt for prompt in prompts)
    assert all(len(prompt) <= 128 for prompt in prompts)
    for stale in ["$dispatch", "$doctor", "/dispatch", "/doctor", "/subagents-dispatch:"]:
        assert all(stale not in prompt for prompt in prompts)


def test_openai_skill_metadata_uses_explicit_display_identity_and_explicit_only_policy():
    for skill_id in SKILL_IDS:
        payload = yaml.safe_load((SKILLS_ROOT / skill_id / "agents" / "openai.yaml").read_text(encoding="utf-8"))
        action_name = skill_id.title()
        interface = payload["interface"]
        assert interface["display_name"] == f"Subagents Dispatch: {action_name}"
        assert 25 <= len(interface["short_description"]) <= 64
        assert action_name in interface["default_prompt"]
        assert payload["policy"]["allow_implicit_invocation"] is False
        for stale in ["$dispatch", "$doctor", "/dispatch", "/doctor", "/subagents-dispatch:"]:
            assert stale not in interface["default_prompt"]


def test_managed_agent_profiles_follow_policy_owned_native_shape():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    profile_dir = PLUGIN_ROOT / "agent-profiles"
    for role in policy["roles"].values():
        payload = tomllib.loads((profile_dir / role["profile_file"]).read_text(encoding="utf-8"))
        assert payload["name"] == role["agent_type"]
        assert isinstance(payload["description"], str) and payload["description"].strip()
        assert isinstance(payload["developer_instructions"], str) and payload["developer_instructions"].strip()
        assert payload["model"] == role["model"]
        assert payload["model_reasoning_effort"] == role["effort"]
        assert payload["sandbox_mode"] == role["sandbox_intent"]
