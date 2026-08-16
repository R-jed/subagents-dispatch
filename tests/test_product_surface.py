from __future__ import annotations

import json
from pathlib import Path
import re
import tomllib
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / ".codex-plugin" / "plugin.json"
HOOKS = ROOT / "hooks" / "hooks.json"
MARKETPLACE = ROOT / ".agents" / "plugins" / "marketplace.json"
POLICY = ROOT / "contracts" / "policy.json"
SKILLS = ROOT / "skills"
CI = ROOT / ".github" / "workflows" / "ci.yml"
INSTALL_DOC = ROOT / "docs" / "plugin-installation.md"
ARCHITECTURE = ROOT / "docs" / "architecture.md"
REPO_ARCH = ROOT / "docs" / "repository-architecture.md"
RELEASE = ROOT / "docs" / "release-checklist.md"
PRIVACY = ROOT / "PRIVACY.md"
README_CN = ROOT / "README.md"
README_EN = ROOT / "README_EN.md"
README_AI = ROOT / "README_AI.md"
DOCTOR_SKILL = SKILLS / "doctor" / "SKILL.md"
DISPATCH_SKILL = SKILLS / "dispatch" / "SKILL.md"
UNINSTALLER = ROOT / "scripts" / "uninstall-agents.py"
SKILL_IDS = {"dispatch", "preview", "status", "steer", "takeover", "doctor"}
DOCTOR_LAYERS = [
    "Plugin",
    "Skills",
    "Spawn guard package",
    "Managed Agent profiles",
    "Dispatch state",
    "Codex Host",
    "Spawn guard runtime",
    "Runtime route",
    "Effective permission state",
    "Permission-source provenance",
]
CANONICAL_MARKETPLACE = "codex plugin marketplace add R-jed/subagents-dispatch"
PLUGIN_ADD = "codex plugin add subagents-dispatch@subagents-dispatch"
UPGRADE = "codex plugin marketplace upgrade subagents-dispatch"
PLUGIN_REMOVE = "codex plugin remove subagents-dispatch@subagents-dispatch"
MARKETPLACE_REMOVE = "codex plugin marketplace remove subagents-dispatch"


def active_surface_files() -> list[Path]:
    paths = [README_CN, README_EN, README_AI, PRIVACY, PLUGIN, MARKETPLACE]
    paths.extend(sorted((ROOT / "docs").glob("*.md")))
    paths.extend(sorted((ROOT / "contracts").glob("*.md")))
    paths.extend(sorted(SKILLS.glob("*/SKILL.md")))
    return paths


def test_active_surfaces_do_not_publish_unverified_or_legacy_skill_entrypoints():
    forbidden_literal = (
        "$dispatch",
        "$doctor",
        "/subagents-dispatch:dispatch",
        "/subagents-dispatch:doctor",
    )
    bare = re.compile(r"(?<![A-Za-z0-9_.-])/(?:dispatch|doctor)\b")
    violations: list[str] = []
    for path in active_surface_files():
        text = path.read_text(encoding="utf-8")
        for token in forbidden_literal:
            if token in text:
                violations.append(f"{path.relative_to(ROOT)} contains {token!r}")
        if bare.search(text):
            violations.append(f"{path.relative_to(ROOT)} contains an unverified bare App entry")
    assert not violations, "\n".join(violations)


def test_six_explicit_skills_keep_distinct_identity_and_human_ui_gate():
    assert {path.name for path in SKILLS.iterdir() if path.is_dir()} == SKILL_IDS
    for skill_id in SKILL_IDS:
        skill = (SKILLS / skill_id / "SKILL.md").read_text(encoding="utf-8")
        metadata = yaml.safe_load(
            (SKILLS / skill_id / "agents" / "openai.yaml").read_text(encoding="utf-8")
        )
        assert f"name: {skill_id}\n" in skill
        assert metadata["interface"]["display_name"] == f"Subagents Dispatch: {skill_id.title()}"
        assert metadata["policy"]["allow_implicit_invocation"] is False
    release = RELEASE.read_text(encoding="utf-8")
    assert "Direct human Codex App observation" in release
    assert "cannot by itself close a Host/UI gate" in release
    assert "record the exact rendered entry labels" in release
    assert "Do not invent literal slash-command syntax" in release


def test_plugin_manifest_remains_official_validator_compatible_and_hooks_use_default_discovery():
    payload = json.loads(PLUGIN.read_text(encoding="utf-8"))
    assert payload["name"] == "subagents-dispatch"
    assert payload["skills"] == "./skills/"
    for unsupported in ("hooks", "mcpServers", "apps", "agents"):
        assert unsupported not in payload
    hooks = json.loads(HOOKS.read_text(encoding="utf-8"))
    assert set(hooks) == {"description", "hooks"}
    assert set(hooks["hooks"]) == {"PreToolUse"}
    groups = hooks["hooks"]["PreToolUse"]
    assert len(groups) == 1
    assert groups[0]["matcher"] == "spawn_agent"
    handlers = groups[0]["hooks"]
    assert len(handlers) == 1
    handler = handlers[0]
    assert handler["type"] == "command"
    assert handler["async"] is False
    assert handler["timeout"] == 5
    assert "run-python.sh" in handler["command"]
    assert "run-python.cmd" in handler["commandWindows"]
    assert not (ROOT / ".codex-plugin" / "hooks.json").exists()


def test_plugin_manifest_has_public_identity_brand_legal_links_and_starter_prompts():
    payload = json.loads(PLUGIN.read_text(encoding="utf-8"))
    interface = payload["interface"]
    assert payload["repository"] == "https://github.com/R-jed/subagents-dispatch"
    assert payload["homepage"] == "https://github.com/R-jed/subagents-dispatch#readme"
    assert interface["displayName"] == "subagents-dispatch"
    assert interface["brandColor"] == "#2563EB"
    for field in ("privacyPolicyURL", "termsOfServiceURL"):
        parsed = urlparse(interface[field])
        assert parsed.scheme == "https" and parsed.netloc
    for field in ("composerIcon", "logo"):
        asset = ROOT / interface[field].removeprefix("./")
        assert asset.is_file() and "<svg" in asset.read_text(encoding="utf-8")
    prompts = interface["defaultPrompt"]
    assert len(prompts) == len(SKILL_IDS)
    for skill_id in SKILL_IDS:
        assert any(skill_id.title() in prompt for prompt in prompts)
    assert all(len(prompt) <= 128 for prompt in prompts)
    for stale in ("$dispatch", "$doctor", "/dispatch", "/doctor", "/subagents-dispatch:"):
        assert all(stale not in prompt for prompt in prompts)


def test_policy_contract_owns_routes_fresh_context_and_single_writer():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    assert policy["schema_version"] == 8
    assert policy["delegation"] == {"max_depth": 1, "fork_turns": "none"}
    assert policy["write_coordination"] == {
        "mode": "single_writer",
        "scope": "canonical_workspace",
    }
    assert set(policy["roles"]) == {"reader", "worker", "solver", "investigator", "advisor"}
    profile_dir = ROOT / "agent-profiles"
    expected_files = {spec["profile_file"] for spec in policy["roles"].values()}
    assert {path.name for path in profile_dir.glob("*.toml")} == expected_files
    for spec in policy["roles"].values():
        profile = tomllib.loads((profile_dir / spec["profile_file"]).read_text(encoding="utf-8"))
        assert profile["name"] == spec["agent_type"]
        assert profile["model"] == spec["model"]
        assert profile["model_reasoning_effort"] == spec["effort"]
        assert profile["description"].strip()
        assert profile["developer_instructions"].strip()
        assert "sandbox_mode" not in profile


def test_dispatch_and_doctor_delegate_to_canonical_deterministic_owners():
    dispatch = DISPATCH_SKILL.read_text(encoding="utf-8")
    for name in (
        "policy.json",
        "routing.md",
        "composition.md",
        "guardrails.md",
        "state.md",
        "team-plan.md",
        "recovery.md",
        "handoff.md",
        "final-review.md",
        "receipt.md",
    ):
        assert f"../../contracts/{name}" in dispatch
    assert "PreToolUse(spawn_agent)" in dispatch
    assert "SPAWN_PENDING" in dispatch
    assert "does not create state" in dispatch

    doctor = DOCTOR_SKILL.read_text(encoding="utf-8")
    for phrase in (
        "../../scripts/doctor.py",
        "../../scripts/doctor_core.py",
        "../../scripts/spawn_guard.py",
        "../../scripts/install-agents.py",
        "../../scripts/uninstall-agents.py",
        "../../scripts/runtime-evidence.py",
        "../../scripts/inspect-agent-runtime.py",
        "show its user-facing output verbatim",
    ):
        assert phrase in doctor
    for layer in DOCTOR_LAYERS:
        assert layer in doctor


def test_doctor_public_docs_match_the_ten_layer_contract_and_experiment_plane_stays_separate():
    for path in (INSTALL_DOC, ARCHITECTURE, REPO_ARCH):
        text = path.read_text(encoding="utf-8")
        assert "exactly ten" in text
        assert "exactly eight" not in text
        for layer in DOCTOR_LAYERS:
            assert layer in text
    doctor = DOCTOR_SKILL.read_text(encoding="utf-8")
    assert "Experiment Plane remains separate" in doctor
    assert "development checks" in doctor


def test_privacy_and_release_contract_cover_hook_boundary_without_claiming_new_control_plane():
    privacy = PRIVACY.read_text(encoding="utf-8")
    for phrase in (
        "spawn guard",
        "PreToolUse",
        "locally",
        "does not persist",
        "no telemetry",
    ):
        assert phrase in privacy
    release = RELEASE.read_text(encoding="utf-8")
    for phrase in (
        "spawn guard",
        "hooks/hooks.json",
        "Hook trust",
        "fork_turns",
        "official OpenAI Plugin validator",
    ):
        assert phrase in release
    composition = (ROOT / "contracts" / "composition.md").read_text(encoding="utf-8")
    assert "second MCP control plane" in composition


def test_ci_runs_validator_full_suite_and_managed_profile_lifecycle():
    text = CI.read_text(encoding="utf-8")
    assert "python -m json.tool hooks/hooks.json" in text
    assert "OPENAI_CODEX_PLUGIN_VALIDATOR_REF" in text
    assert "Validate Plugin with pinned official OpenAI validator" in text
    assert "python -m pytest -q" in text
    assert 'python scripts/uninstall-agents.py --codex-home "$target"' in text
    assert "managed Agent check unexpectedly passed after uninstall" in text
    assert text.count('python scripts/install-agents.py --codex-home "$target" --check') >= 3
    assert "startsWith(github.ref, 'refs/tags/')" in text
    assert 'test "$GITHUB_REF_NAME" = "v$version"' in text


def test_public_install_uninstall_update_flow_preserves_ownership_order():
    install = INSTALL_DOC.read_text(encoding="utf-8")
    for phrase in (
        CANONICAL_MARKETPLACE,
        PLUGIN_ADD,
        "Python 3.11 or newer",
        "PYTHON_PREREQUISITE_UNMET",
        "five managed custom-Agent profiles",
        "RESTART_REQUIRED",
        UPGRADE,
        "scripts/uninstall-agents.py",
        PLUGIN_REMOVE,
        MARKETPLACE_REMOVE,
    ):
        assert phrase in install
    cleanup_index = install.index("scripts/uninstall-agents.py")
    assert cleanup_index < install.index(PLUGIN_REMOVE)
    assert UNINSTALLER.is_file()
    forbidden = [
        "rm ~/.codex/agents/subagents-dispatch-reader.toml",
        "rm ~/.codex/.subagents-dispatch-agents.json",
    ]
    for path in (INSTALL_DOC, README_CN, README_EN, DOCTOR_SKILL):
        text = path.read_text(encoding="utf-8")
        assert all(command not in text for command in forbidden)


def test_marketplace_release_identity_is_version_pinned():
    plugin = json.loads(PLUGIN.read_text(encoding="utf-8"))
    market = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    assert market == {
        "name": "subagents-dispatch",
        "interface": {"displayName": "subagents-dispatch"},
        "plugins": [
            {
                "name": "subagents-dispatch",
                "source": {
                    "source": "url",
                    "url": "https://github.com/R-jed/subagents-dispatch.git",
                    "ref": f"v{plugin['version']}",
                },
                "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                "category": "Productivity",
            }
        ],
    }


def test_public_readmes_cover_current_surface_without_unmeasured_performance_claims():
    version = json.loads(PLUGIN.read_text(encoding="utf-8"))["version"]
    zh = README_CN.read_text(encoding="utf-8")
    en = README_EN.read_text(encoding="utf-8")
    for text in (zh, en):
        assert version in text
        for skill_id in SKILL_IDS:
            assert skill_id.title() in text
        for command in (CANONICAL_MARKETPLACE, PLUGIN_ADD, UPGRADE, PLUGIN_REMOVE, MARKETPLACE_REMOVE):
            assert command in text
        for path in (
            ".agents/plugins/",
            ".codex-plugin/",
            "agent-profiles/",
            "contracts/",
            "skills/",
            "hooks/",
            "docs/",
            "evals/",
            "scripts/",
            "tests/",
        ):
            assert path in text
        for phrase in ("Configured", "Requested", "Accepted", "Observed", "0 child", "Runtime Attestation"):
            assert phrase in text
    assert "本 README 不声称 subagents-dispatch 已经被证明更快、更省总 Token" in zh
    assert "this README does not claim that subagents-dispatch is proven faster" in en


def test_ai_reference_is_an_index_to_canonical_policy_owners():
    text = README_AI.read_text(encoding="utf-8")
    for phrase in (
        "R-jed/subagents-dispatch",
        "contracts/interaction.md",
        "contracts/routing.md",
        "contracts/state.md",
        "contracts/guardrails.md",
        "contracts/policy.json",
        "docs/plugin-installation.md",
        "scripts/policy.py",
        "Do not invent a Codex App slash-command string",
    ):
        assert phrase in text
    assert "not a second copy of runtime policy" in text


def test_structural_contract_and_status_vocabulary_remain_intact():
    contracts = ROOT / "contracts"
    assert {path.name for path in contracts.iterdir() if path.is_file()} == {
        "policy.json",
        "routing.md",
        "composition.md",
        "interaction.md",
        "state.md",
        "receipt.md",
        "team-plan.md",
        "recovery.md",
        "guardrails.md",
        "handoff.md",
        "evidence-artifact.md",
        "final-review.md",
    }
    interaction = (contracts / "interaction.md").read_text(encoding="utf-8")
    for phrase in (
        "Running / 运行中",
        "Waiting / 等待",
        "Needs attention / 需处理",
        "Completed / 已完成",
        "Do not dump the full active-state JSON by default",
    ):
        assert phrase in interaction
    assert "## Dispatch Receipt" in interaction


def test_doctor_live_route_workflow_still_requires_exact_five_roles_and_runtime_evidence():
    text = DOCTOR_SKILL.read_text(encoding="utf-8")
    for role in (
        "subagents_dispatch_reader",
        "subagents_dispatch_worker",
        "subagents_dispatch_solver",
        "subagents_dispatch_investigator",
        "subagents_dispatch_advisor",
    ):
        assert role in text
    assert "fork_turns = none" in text
    assert "scripts/runtime-evidence.py" in text
    assert "UNKNOWN" in text
