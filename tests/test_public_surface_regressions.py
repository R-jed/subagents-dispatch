from __future__ import annotations

import json
from pathlib import Path
import re
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / ".codex-plugin" / "plugin.json"
SKILLS = ROOT / "skills"
INSTALL_DOC = ROOT / "docs" / "plugin-installation.md"
PYTHON_RUNTIME_DOC = ROOT / "docs" / "python-runtime.md"
RELEASE = ROOT / "docs" / "release-checklist.md"
README_CN = ROOT / "README.md"
README_EN = ROOT / "README_EN.md"
README_AI = ROOT / "README_AI.md"
EVALS_README = ROOT / "evals" / "README.md"
INTERACTION = ROOT / "contracts" / "interaction.md"
STATUS_SKILL = SKILLS / "status" / "SKILL.md"
CI = ROOT / ".github" / "workflows" / "ci.yml"
SKILL_IDS = ("dispatch", "preview", "status", "steer", "takeover", "doctor")
CANONICAL_MARKETPLACE = "codex plugin marketplace add R-jed/subagents-dispatch"
PLUGIN_ADD = "codex plugin add subagents-dispatch@subagents-dispatch"
UPGRADE = "codex plugin marketplace upgrade subagents-dispatch"
PLUGIN_REMOVE = "codex plugin remove subagents-dispatch@subagents-dispatch"


def durable_active_surface_files() -> list[Path]:
    paths = [README_CN, README_EN, README_AI, ROOT / "PRIVACY.md", PLUGIN]
    paths.extend(sorted((ROOT / "docs").glob("*.md")))
    paths.extend(sorted((ROOT / "contracts").glob("*.md")))
    paths.extend(sorted(SKILLS.glob("**/*.md")))
    paths.extend(sorted(SKILLS.glob("**/*.yaml")))
    paths.extend(sorted((ROOT / "evals").glob("*.json")))
    paths.extend(sorted((ROOT / "scripts").glob("*.py")))
    return paths


def durable_public_contract_files() -> list[Path]:
    paths = [README_CN, README_EN, README_AI, ROOT / "PRIVACY.md", PLUGIN]
    paths.extend(sorted((ROOT / "docs").glob("*.md")))
    paths.extend(sorted((ROOT / "contracts").glob("*.md")))
    paths.extend(sorted(SKILLS.glob("*/SKILL.md")))
    return paths


def test_regression_active_surfaces_keep_full_legacy_entrypoint_scan():
    forbidden_literal = (
        "$dispatch",
        "$doctor",
        "/subagents-dispatch:dispatch",
        "/subagents-dispatch:doctor",
    )
    forbidden_bare = re.compile(r"(?<![A-Za-z0-9_.-])/(?:dispatch|doctor)\b")
    violations: list[str] = []
    for path in durable_active_surface_files():
        text = path.read_text(encoding="utf-8")
        for token in forbidden_literal:
            if token in text:
                violations.append(f"{path.relative_to(ROOT)} contains {token!r}")
        for match in forbidden_bare.finditer(text):
            violations.append(
                f"{path.relative_to(ROOT)} contains unverified bare App entry {match.group(0)!r}"
            )
    assert violations == []


def test_regression_active_surfaces_keep_full_obsolete_contract_scan():
    forbidden = {
        "skills/dispatch/references": "obsolete Skill-owned shared contract path",
        "policy-contract.json": "obsolete root policy path",
        "Zero children is normal": "numeric zero-child framing",
        "max_active_writers_per_workspace": "numeric writer-capacity policy",
        "/dispatch preview": "obsolete payload control grammar",
        "/dispatch status": "obsolete payload control grammar",
        "/dispatch steer": "obsolete payload control grammar",
        "/dispatch takeover": "obsolete payload control grammar",
        "A green branch run does not replace the pull-request merge-result run": "obsolete PR-only governance",
        "Require pull requests": "obsolete PR-only governance",
        "Execution Receipt": "obsolete receipt name",
        "· complete · no retry": "obsolete English receipt state axis",
        "· 完成 · 未重试": "obsolete Chinese receipt state axis",
        "无需最终复核": "obsolete negative review wording",
    }
    defects: list[str] = []
    for path in durable_public_contract_files():
        text = path.read_text(encoding="utf-8")
        for phrase, reason in forbidden.items():
            if phrase in text:
                defects.append(f"{path.relative_to(ROOT)}: {reason}: {phrase}")
        if "/subagents-dispatch:" in text:
            defects.append(f"{path.relative_to(ROOT)}: unverified namespaced slash syntax")
    assert defects == []


def test_regression_third_party_mit_notice_remains_packaged_without_repository_pointer():
    notice = ROOT / "THIRD_PARTY_NOTICES.md"
    assert notice.is_file()
    text = notice.read_text(encoding="utf-8")
    for phrase in (
        "MIT-licensed third-party material",
        "Copyright (c) 2026 Zhijian AI / Dapeng",
        "Permission is hereby granted",
        'THE SOFTWARE IS PROVIDED "AS IS"',
    ):
        assert phrase in text
    assert "github.com/" not in text


def test_regression_plugin_legal_links_still_target_packaged_policy_files():
    interface = json.loads(PLUGIN.read_text(encoding="utf-8"))["interface"]
    for field, suffix in (
        ("privacyPolicyURL", "/PRIVACY.md"),
        ("termsOfServiceURL", "/TERMS.md"),
    ):
        parsed = urlparse(interface[field])
        assert parsed.scheme == "https" and parsed.netloc
        assert parsed.path.endswith(suffix)
    assert (ROOT / "PRIVACY.md").is_file()
    assert (ROOT / "TERMS.md").is_file()


def test_regression_openai_skill_metadata_keeps_description_and_prompt_contract():
    for skill_id in SKILL_IDS:
        payload = yaml.safe_load(
            (SKILLS / skill_id / "agents" / "openai.yaml").read_text(encoding="utf-8")
        )
        action_name = skill_id.title()
        interface = payload["interface"]
        assert interface["display_name"] == f"Subagents Dispatch: {action_name}"
        assert 25 <= len(interface["short_description"]) <= 64
        assert action_name in interface["default_prompt"]
        assert payload["policy"]["allow_implicit_invocation"] is False
        for stale in ("$dispatch", "$doctor", "/dispatch", "/doctor", "/subagents-dispatch:"):
            assert stale not in interface["default_prompt"]


def test_regression_root_plugin_layout_and_ci_do_not_reintroduce_removed_subdirectory():
    assert PLUGIN.is_file()
    assert (SKILLS / "dispatch" / "SKILL.md").is_file()
    stale = "plugins/subagents-dispatch"
    text = CI.read_text(encoding="utf-8")
    assert stale not in text
    assert ".codex-plugin/plugin.json" in text
    assert "scripts/install-agents.py" in text


def test_regression_python_helper_runtime_keeps_portable_resolution_boundary():
    assert PYTHON_RUNTIME_DOC.is_file()
    text = PYTHON_RUNTIME_DOC.read_text(encoding="utf-8")
    for phrase in (
        "Python 3.11 or newer",
        "python3",
        "python",
        "py -3.11",
        "sys.executable",
        "environment adaptation",
        "PYTHON_PREREQUISITE_UNMET",
        "actions/setup-python",
        "real Codex App task shell",
        "A single `command not found`",
    ):
        assert phrase in text


def test_regression_public_readmes_keep_deeper_docs_and_full_repository_layout():
    for path, heading in ((README_CN, "## 项目结构"), (README_EN, "## Repository layout")):
        text = path.read_text(encoding="utf-8")
        assert heading in text
        for entry in (
            ".agents/plugins/",
            ".codex-plugin/",
            "agent-profiles/",
            "contracts/",
            "skills/",
            "dispatch/",
            "preview/",
            "status/",
            "steer/",
            "takeover/",
            "doctor/",
            "docs/",
            "evals/",
            "scripts/",
            "tests/",
        ):
            assert entry in text
        for link in (
            "README_AI.md",
            "docs/plugin-installation.md",
            "docs/architecture.md",
            "docs/native-subagent-runtime.md",
            "docs/runtime-attestation.md",
            "docs/experiment-protocol.md",
            "contracts/composition.md",
        ):
            assert link in text


def test_regression_public_readme_visual_surface_uses_canonical_assets_only():
    banner = ROOT / "assets" / "subagents-dispatch-banner.png"
    assert banner.is_file()
    assert not (ROOT / "docs" / "logo-light.svg").exists()
    assert not (ROOT / "docs" / "logo-dark.svg").exists()
    for path in (README_CN, README_EN):
        text = path.read_text(encoding="utf-8")
        assert "<picture" not in text
        assert "assets/subagents-dispatch-banner.png" in text
        assert "#gh-light-mode-only" not in text
        assert "#gh-dark-mode-only" not in text
        assert "docs/logo-" not in text
        for line in text.splitlines():
            if "<img" in line and "subagents-dispatch-banner" not in line and "shields.io" not in line:
                raise AssertionError(f"Unexpected README image: {line}")


def test_regression_public_performance_disclaimer_keeps_both_claim_boundaries():
    zh = README_CN.read_text(encoding="utf-8")
    en = README_EN.read_text(encoding="utf-8")
    assert "本 README 不声称 subagents-dispatch 已经被证明更快、更省总 Token" in zh
    assert "当前五个 model / effort 是最优配置" in zh
    assert "this README does not claim that subagents-dispatch is proven faster" in en
    assert "the current five model/effort routes are optimal" in en


def test_regression_ai_reference_keeps_full_owner_map_and_excludes_install_commands():
    text = README_AI.read_text(encoding="utf-8")
    version = json.loads(PLUGIN.read_text(encoding="utf-8"))["version"]
    for phrase in (
        "R-jed/subagents-dispatch",
        "Repo marketplace id: subagents-dispatch",
        f"Current version:     {version}",
        "Distribution:        Codex Plugin",
        "contracts/interaction.md",
        "contracts/routing.md",
        "contracts/handoff.md",
        "contracts/team-plan.md",
        "contracts/recovery.md",
        "contracts/guardrails.md",
        "contracts/final-review.md",
        "contracts/policy.json",
        "skills/<id>/SKILL.md",
        "docs/plugin-installation.md",
        "scripts/policy.py",
        "Do not invent a Codex App slash-command string",
        "not a second copy of runtime policy",
    ):
        assert phrase in text
    for skill_id in SKILL_IDS:
        assert f"`{skill_id}`" in text
    for command in (CANONICAL_MARKETPLACE, PLUGIN_ADD, UPGRADE, "/subagents-dispatch:dispatch", "$dispatch"):
        assert command not in text


def test_regression_evals_readme_keeps_measurement_boundary_and_owner_map():
    text = EVALS_README.read_text(encoding="utf-8")
    for phrase in (
        "not part of the normal user setup",
        "behavioral-workloads.json",
        "behavioral-result.schema.json",
        "routing-cases.json",
        "coordination-cases.json",
        "interaction-cases.json",
        "runtime-assurance-cases.json",
        "do not control how the plugin routes or coordinates work",
        "`interaction.md`",
        "`routing.md`",
        "`handoff.md`",
        "`team-plan.md`",
        "`recovery.md`",
        "`guardrails.md`",
        "`final-review.md`",
        "`policy.json`",
    ):
        assert phrase in text


def test_regression_status_contract_keeps_low_resolution_examples_and_locale_boundary():
    text = INTERACTION.read_text(encoding="utf-8")
    for phrase in (
        "Running / 运行中",
        "Waiting / 等待",
        "Needs attention / 需处理",
        "Completed / 已完成",
        "U1 · Luna Max 读取",
        "U2 · Luna Max 执行 · 等待 U1",
        "U1 · Luna Max Read",
        "waiting for U1",
        "Do not dump the full active-state JSON by default",
        "Use the orchestration locale stored in active state",
        "## Dispatch Receipt",
    ):
        assert phrase in text
    assert "## Execution Receipt" not in text


def test_regression_status_dependency_explanation_remains_evidence_bound():
    interaction = INTERACTION.read_text(encoding="utf-8")
    skill = STATUS_SKILL.read_text(encoding="utf-8")
    assert "only when that dependency is part of current accepted structural truth" in interaction
    assert "omit the dependency explanation rather than reconstructing or guessing it" in interaction
    assert "../../contracts/receipt.md" in skill


def test_regression_public_uninstall_docs_forbid_all_manual_managed_profile_removal_commands():
    forbidden = (
        "rm ~/.codex/agents/subagents-dispatch-reader.toml",
        "rm ~/.codex/agents/subagents-dispatch-worker.toml",
        "rm ~/.codex/agents/subagents-dispatch-solver.toml",
        "rm ~/.codex/agents/subagents-dispatch-investigator.toml",
        "rm ~/.codex/agents/subagents-dispatch-advisor.toml",
        "rm ~/.codex/.subagents-dispatch-agents.json",
    )
    for path in (INSTALL_DOC, README_CN, README_EN, SKILLS / "doctor" / "SKILL.md"):
        text = path.read_text(encoding="utf-8")
        for command in forbidden:
            assert command not in text


def test_regression_release_documents_nonblocking_hook_command_failure_truthfully():
    text = RELEASE.read_text(encoding="utf-8")
    assert "generic non-blocking Hook command failure" in text
    assert "actual native spawn result determines whether a child materializes" in text
    assert "Existing Skill/contract checks remain the correctness fallback" in text
    assert "does not consume a child attempt" not in text
