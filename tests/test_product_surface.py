from __future__ import annotations

import json
from pathlib import Path
import tomllib

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


def test_plugin_manifest_is_v1_two_skill_identity_and_validator_compatible():
    payload = json.loads(PLUGIN.read_text(encoding="utf-8"))
    assert payload["name"] == "subagents-dispatch"
    assert payload["version"] == "1.0.0"
    assert payload["skills"] == "./skills/"
    for unsupported in ("mcpServers", "apps", "agents"):
        assert unsupported not in payload
    interface = payload["interface"]
    assert len(interface["defaultPrompt"]) == 2
    assert "Orchestrate" in interface["longDescription"]
    assert "Doctor" in interface["longDescription"]
    product_copy = " ".join(
        [
            payload["description"],
            interface["shortDescription"],
            interface["longDescription"],
            *interface["defaultPrompt"],
        ]
    )
    for internal in (
        "WorkUnit",
        "TeamPlan",
        "ExecutionBinding",
        "WriterLease",
        "lifecycle reconciliation",
        "two-Skill surface",
        "Native Core",
    ):
        assert internal not in product_copy
    for field in ("privacyPolicyURL", "termsOfServiceURL"):
        assert field not in interface
    for field in ("composerIcon", "logo"):
        path = ROOT / interface[field].removeprefix("./")
        assert path.is_file()


def test_orchestrate_keeps_engineering_narration_out_of_user_deliverables():
    text = (SKILLS / "orchestrate" / "SKILL.md").read_text(encoding="utf-8")
    for surface in ("UI", "PDFs", "presentations", "reports", "screenshots", "exported files"):
        assert surface in text
    assert "Unless the user explicitly requests" in text
    for internal_process in (
        "agent planning",
        "implementation rationale",
        "debugging chronology",
        "verification mechanics",
        "future-work planning",
    ):
        assert internal_process in text


def test_compaction_uses_generation_safe_task_identity_without_permanent_tombstones():
    skill = (SKILLS / "orchestrate" / "SKILL.md").read_text(encoding="utf-8")
    recovery = (ROOT / "contracts" / "recovery.md").read_text(encoding="utf-8")
    state = (ROOT / "contracts" / "state.md").read_text(encoding="utf-8")
    assert "runtime-derived Host task name" in skill
    assert "attempt_no` remains monotonic across bounded history compaction" in skill
    assert "derives `native_task_name` deterministically" in recovery
    assert "unbounded orchestration-lifetime tombstone set" in recovery
    assert "canonical Host control address" in state
    assert "monotonic `max_attempt_no`" in state
    assert "WorkUnit, attempt, control, and lease generation basis" in state


def test_marketplace_plugin_source_is_exact_checkout_root():
    market = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    assert market["plugins"][0]["source"] == {"source": "local", "path": "./"}


def test_fixed_profiles_follow_policy_and_request_leaf_containment():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    assert policy["schema_version"] == 9
    assert policy["delegation"] == {
        "max_depth": 1,
        "fork_turns": "none",
        "max_managed_children": 4,
    }
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


def test_native_core_release_is_blocked_until_external_n0_n7_campaign_passes():
    smoke = json.loads(HOST_SMOKE.read_text(encoding="utf-8"))
    assert smoke["status"] == "PENDING"
    assert smoke["results"] == {}
    assert smoke["gate_id"] == "v4-real-host-n0-n7"
    assert [probe["id"] for probe in smoke["required_probes"]] == [f"N{index}" for index in range(8)]


def test_installation_document_keeps_supported_commands():
    text = (ROOT / "docs" / "plugin-installation.md").read_text(encoding="utf-8")
    assert CANONICAL_MARKETPLACE in text
    assert PLUGIN_ADD in text
    assert PLUGIN_REMOVE in text
    assert MARKETPLACE_REMOVE in text
