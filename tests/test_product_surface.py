from __future__ import annotations

import json
from pathlib import Path
import tomllib
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / ".codex-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".agents" / "plugins" / "marketplace.json"
POLICY = ROOT / "contracts" / "policy.json"
SKILLS = ROOT / "skills"
HOST_SMOKE = ROOT / "docs" / "v4" / "host-smoke.json"
PUBLIC_SKILLS = {"orchestrate", "doctor"}
CANONICAL_MARKETPLACE = "codex plugin marketplace add R-jed/subagents-dispatch"
PLUGIN_ADD = "codex plugin add subagents-dispatch@subagents-dispatch"
PLUGIN_REMOVE = "codex plugin remove subagents-dispatch@subagents-dispatch"
MARKETPLACE_REMOVE = "codex plugin marketplace remove subagents-dispatch"


def test_public_surface_is_exactly_two_explicit_skills():
    assert {path.name for path in SKILLS.iterdir() if path.is_dir()} == PUBLIC_SKILLS
    for skill_id in PUBLIC_SKILLS:
        skill = (SKILLS / skill_id / "SKILL.md").read_text(encoding="utf-8")
        metadata = yaml.safe_load(
            (SKILLS / skill_id / "agents" / "openai.yaml").read_text(encoding="utf-8")
        )
        assert f"name: {skill_id}\n" in skill
        assert metadata["interface"]["display_name"] == f"Subagents Dispatch: {skill_id.title()}"
        assert metadata["policy"]["allow_implicit_invocation"] is False


def test_plugin_manifest_is_v4_two_skill_identity_and_validator_compatible():
    payload = json.loads(PLUGIN.read_text(encoding="utf-8"))
    assert payload["name"] == "subagents-dispatch"
    assert payload["version"] == "4.0.0"
    assert payload["skills"] == "./skills/"
    for unsupported in ("mcpServers", "apps", "agents"):
        assert unsupported not in payload
    interface = payload["interface"]
    assert len(interface["defaultPrompt"]) == 2
    assert any("Orchestrate" in prompt for prompt in interface["defaultPrompt"])
    assert any("Doctor" in prompt for prompt in interface["defaultPrompt"])
    assert "two explicit Skills" in interface["longDescription"]
    for field in ("privacyPolicyURL", "termsOfServiceURL"):
        parsed = urlparse(interface[field])
        assert parsed.scheme == "https" and parsed.netloc
    for field in ("composerIcon", "logo"):
        path = ROOT / interface[field].removeprefix("./")
        assert path.is_file()


def test_marketplace_plugin_source_is_exact_checkout_root():
    market = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    assert market["plugins"][0]["source"] == {"source": "local", "path": "./"}


def test_fixed_profiles_follow_policy_and_child_collaboration_is_disabled():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    assert policy["schema_version"] == 9
    assert policy["delegation"] == {"max_depth": 1, "fork_turns": "none"}
    assert policy["write_coordination"] == {"mode": "single_writer", "scope": "canonical_workspace"}
    assert set(policy["roles"]) == {"reader", "worker", "investigator", "solver", "advisor"}

    for role, spec in policy["roles"].items():
        profile = tomllib.loads(
            (ROOT / "agent-profiles" / spec["profile_file"]).read_text(encoding="utf-8")
        )
        assert profile["model"] == spec["model"], role
        assert profile["model_reasoning_effort"] == spec["effort"], role
        assert profile["agents"]["enabled"] is False, role
        assert profile["features"]["multi_agent_v2"] is False, role


def test_native_core_release_is_blocked_until_external_n0_n8_campaign_passes():
    smoke = json.loads(HOST_SMOKE.read_text(encoding="utf-8"))
    assert smoke["status"] == "PENDING"
    assert smoke["results"] == {}
    assert smoke["gate_id"] == "v4-real-host-n0-n8"
    assert [probe["id"] for probe in smoke["required_probes"]] == [f"N{index}" for index in range(9)]


def test_installation_document_keeps_supported_commands():
    text = (ROOT / "docs" / "plugin-installation.md").read_text(encoding="utf-8")
    assert CANONICAL_MARKETPLACE in text
    assert PLUGIN_ADD in text
    assert PLUGIN_REMOVE in text
    assert MARKETPLACE_REMOVE in text
