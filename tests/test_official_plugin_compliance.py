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
MAIN_SKILL_ROOT = SKILLS_ROOT / "dispatch"
DOCTOR_SKILL_ROOT = SKILLS_ROOT / "doctor"
MAIN_OPENAI_YAML = MAIN_SKILL_ROOT / "agents" / "openai.yaml"
DOCTOR_OPENAI_YAML = DOCTOR_SKILL_ROOT / "agents" / "openai.yaml"
POLICY = PLUGIN_ROOT / "policy-contract.json"
MAIN_INVOCATION = "/subagents-dispatch:dispatch"
DOCTOR_INVOCATION = "/subagents-dispatch:doctor"


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


def test_plugin_starter_prompts_cover_main_and_doctor_within_supported_limit():
    prompts = json.loads(MANIFEST.read_text(encoding="utf-8"))["interface"]["defaultPrompt"]
    assert 1 <= len(prompts) <= 3
    assert any(MAIN_INVOCATION in prompt for prompt in prompts)
    assert any(DOCTOR_INVOCATION in prompt for prompt in prompts)
    assert all(MAIN_INVOCATION in prompt or DOCTOR_INVOCATION in prompt for prompt in prompts)
    assert all(len(prompt) <= 128 for prompt in prompts)


def test_openai_skill_metadata_uses_each_explicit_invocation():
    main = yaml.safe_load(MAIN_OPENAI_YAML.read_text(encoding="utf-8"))
    doctor = yaml.safe_load(DOCTOR_OPENAI_YAML.read_text(encoding="utf-8"))

    for payload, invocation in [(main, MAIN_INVOCATION), (doctor, DOCTOR_INVOCATION)]:
        interface = payload["interface"]
        assert 25 <= len(interface["short_description"]) <= 64
        assert invocation in interface["default_prompt"]
        assert payload["policy"]["allow_implicit_invocation"] is False


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
