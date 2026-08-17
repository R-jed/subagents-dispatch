from __future__ import annotations

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / ".codex-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".agents" / "plugins" / "marketplace.json"
README_CN = ROOT / "README.md"
README_EN = ROOT / "README_EN.md"
README_AI = ROOT / "README_AI.md"
CHANGELOG = ROOT / "CHANGELOG.md"
CHANGELOG_V3 = ROOT / "CHANGELOG_V3.md"
RELEASE = ROOT / "docs" / "release-checklist.md"
HOST_SMOKE = ROOT / "docs" / "v4" / "host-smoke.json"
STAGED_HOOKS = ROOT / "docs" / "v4" / "hooks.json"
PRODUCTION_HOOKS = ROOT / "hooks" / "hooks.json"
POLICY = ROOT / "contracts" / "policy.json"
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def current_version() -> str:
    version = json.loads(PLUGIN.read_text(encoding="utf-8"))["version"]
    assert isinstance(version, str) and SEMVER.fullmatch(version)
    return version


def test_v4_version_identity_is_consistent_without_premature_tag_claim():
    version = current_version()
    assert version == "4.0.0"
    assert f"version-{version}-green.svg" in README_CN.read_text(encoding="utf-8")
    assert f"version-{version}-green.svg" in README_EN.read_text(encoding="utf-8")
    assert re.search(
        rf"^Current version:\s+{re.escape(version)}$",
        README_AI.read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
    market = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    assert market["plugins"][0]["source"]["ref"] == f"v{version}"
    release = RELEASE.read_text(encoding="utf-8")
    assert "does not claim platform-enforced tag immutability" in release
    assert "Do not create `v4.0.0` until every required release gate" not in release
    assert "versioned semantic-version tag only after all required release gates pass" in release


def test_latest_changelog_matches_v4_and_preserves_v3_history_verbatim():
    text = CHANGELOG.read_text(encoding="utf-8")
    match = re.search(r"^## \[([^\]]+)\]", text, flags=re.MULTILINE)
    assert match and match.group(1) == current_version()
    assert CHANGELOG_V3.is_file()
    old = CHANGELOG_V3.read_text(encoding="utf-8")
    assert "## [3.0.1]" in old
    assert "## [3.0.0]" in old
    assert "CHANGELOG_V3.md" in text


def test_release_evidence_ownership_is_explicit_and_nonfungible():
    text = RELEASE.read_text(encoding="utf-8")
    for phrase in (
        "### Evidence ownership",
        "Repository/API/CI evidence",
        "Raw Host/rollout evidence",
        "Direct human Codex App observation",
        "Model self-report",
        "cannot by itself close a Host/UI gate",
        "must protect one concrete public capability, safety property, distribution property, or release claim",
    ):
        assert phrase in text


def test_release_path_keeps_experiment_plane_conditional_and_host_gate_mandatory():
    text = RELEASE.read_text(encoding="utf-8")
    assert "Experiment Plane research capabilities and are not hard release blockers unless a release claim depends on them" in text
    assert "Runtime attestation and the V4 Host lifecycle smoke remain release-path evidence" in text
    smoke = json.loads(HOST_SMOKE.read_text(encoding="utf-8"))
    assert smoke["status"] != "PASS"
    assert smoke["blocks_release"] == "v4.0.0-production-hook-activation-and-publication"
    assert {probe["id"] for probe in smoke["required_probes"]} == {
        f"H{number:02d}" for number in range(11)
    }


def test_staged_hooks_are_not_promoted_without_real_host_evidence():
    staged = json.loads(STAGED_HOOKS.read_text(encoding="utf-8"))
    production = json.loads(PRODUCTION_HOOKS.read_text(encoding="utf-8"))
    assert {"PreToolUse", "PostToolUse", "SubagentStop"}.issubset(staged["hooks"])
    assert set(production["hooks"]) == {"PreToolUse"}
    assert "Only after H00-H10 pass may the staged `docs/v4/hooks.json` be promoted" in RELEASE.read_text(encoding="utf-8")


def test_release_contract_freezes_two_skills_and_five_profile_identities():
    release = RELEASE.read_text(encoding="utf-8")
    assert "skills/orchestrate" in release and "skills/doctor" in release
    for agent_type in (
        "subagents_dispatch_reader",
        "subagents_dispatch_worker",
        "subagents_dispatch_investigator",
        "subagents_dispatch_solver",
        "subagents_dispatch_advisor",
    ):
        assert agent_type in release
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    assert policy["fixed_execution_profiles"] == {
        "luna": "max",
        "terra": "high",
        "sol": "high",
        "dynamic_effort_routing": False,
    }
    assert "Configured → Requested → Accepted → Observed" in release


def test_release_contract_resolves_python_without_bare_python_assumption():
    release = RELEASE.read_text(encoding="utf-8")
    runtime = (ROOT / "docs" / "python-runtime.md").read_text(encoding="utf-8")
    for phrase in ("<python-3.11+>", "PYTHON_PREREQUISITE_UNMET", "environment adaptation", "sys.executable"):
        assert phrase in release or phrase in runtime
    assert "A resolved `sys.executable` may be reused" in release


def test_distribution_removal_is_semantically_bounded():
    release = RELEASE.read_text(encoding="utf-8")
    assert "allow only the semantic delta required by the supported Plugin and Marketplace registration removal commands" in release
    assert "unrelated configuration semantics and other Codex state must remain unchanged" in release


def test_release_sequence_keeps_host_and_human_gates_after_offline_ci():
    release = RELEASE.read_text(encoding="utf-8")
    order = [
        "repository matrix PASS",
        "real Host H00-H10 PASS",
        "promote staged V4 Hooks",
        "repository matrix PASS again",
        "Doctor --release-check PASS",
        "human two-Skill App observation PASS",
        "create v4.0.0 versioned semantic-version tag",
    ]
    positions = [release.index(item) for item in order]
    assert positions == sorted(positions)
    assert "If any real Host gate remains unavailable, record the candidate as repository-complete and release-blocked" in release


def test_ai_reference_is_v4_owner_map_and_does_not_impersonate_runtime_evidence():
    text = README_AI.read_text(encoding="utf-8")
    for phrase in (
        "Current version:     4.0.0",
        "Orchestrate",
        "Doctor",
        "scripts/orchestrate_v4.py",
        "scripts/dispatch_state_v4.py",
        "scripts/writer_lease_v4.py",
        "docs/v4/host-smoke.json",
        "Offline CI cannot promote `docs/v4/host-smoke.json` to PASS",
    ):
        assert phrase in text
    assert "codex plugin marketplace add" not in text


def test_privacy_keeps_local_attestation_and_temporary_state_boundaries():
    text = (ROOT / "PRIVACY.md").read_text(encoding="utf-8")
    for phrase in (
        "## Local runtime attestation",
        "does not scan transcript records for task facts",
        "does not upload the rollout",
        "operating system's temporary directory",
        "active.json",
        "raw prompts",
        "private reasoning",
    ):
        assert phrase in text


def test_transient_local_review_artifacts_are_not_packaged():
    forbidden = {"deep-review-report", "release-candidate-closure", "local-validation", "handoff-progress", "headoff"}
    offenders: list[str] = []
    for base in (ROOT, ROOT / "docs"):
        for path in base.iterdir():
            if path.is_file() and any(marker in path.name.lower() for marker in forbidden):
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []
