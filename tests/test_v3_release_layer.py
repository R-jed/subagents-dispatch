from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_privacy_discloses_thread_scoped_temporary_capsule_and_retention_boundary():
    text = (ROOT / "PRIVACY.md").read_text(encoding="utf-8")
    for phrase in [
        "operating system's temporary directory",
        "root-thread-id",
        "active.json",
        "raw prompts",
        "private reasoning",
        "credentials",
        "full source files",
        "Normal terminal completion removes",
        "seven days",
        "unresolved active writers are retained",
        "not sent to the project maintainer",
    ]:
        assert phrase in text


def test_chinese_public_examples_use_receipt_activity_vocabulary():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert all(word not in text for word in ["Reader", "Worker", "Solver", "Investigator", "Advisor"])
    for word in ["Luna", "Sol", "Terra", "Max", "High", "XHigh", "Status", "Steer", "Takeover", "读取", "调研", "执行", "决策", "验收"]:
        assert word in text


def test_public_receipt_examples_use_independent_axes_without_task_completion_state():
    chinese = (ROOT / "README.md").read_text(encoding="utf-8")
    english = (ROOT / "README_EN.md").read_text(encoding="utf-8")

    assert "编排: Luna Max 读取 · Luna Max 执行 · Sol High 验收" in chinese
    assert "验收: 1轮 · 通过" in chinese
    for obsolete in [
        "Dispatch: Luna Max 读取 → Luna Max 执行 · 完成 · 未重试 · 无需最终复核",
        "· 完成 · 未重试",
        "无需最终复核",
    ]:
        assert obsolete not in chinese

    assert "Dispatch: Luna Max Read · Luna Max Execute · Sol High Review" in english
    assert "Review: 1 round · passed" in english
    for obsolete in [
        "Dispatch: Luna Max Read → Luna Max Execute · complete · no retry · not required",
        "· complete · no retry",
    ]:
        assert obsolete not in english


def test_work_section_63_adversarial_cases_are_registered_once():
    payload = json.loads((ROOT / "evals" / "interaction-cases.json").read_text(encoding="utf-8"))
    ids = [case["id"] for case in payload["cases"]]
    expected = {
        "missing-thread-id",
        "spawn-pending-no-match",
        "spawn-pending-single-match",
        "spawn-pending-multiple-match",
        "corrupt-capsule-active-writer",
        "multi-targetless-steer",
        "single-targetless-steer",
        "interrupted-takeover",
        "fix-first-without-correction",
        "retry-then-rework",
        "locale-persistence",
        "unrelated-dispatch-with-unresolved-writer",
        "repeated-status-dedupe",
        "same-child-resume",
        "route-mismatch",
    }
    assert expected <= set(ids)
    assert len(ids) == len(set(ids))


def test_ci_and_release_docs_keep_host_app_evidence_external_and_local_gates_deterministic():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    release = (ROOT / "docs" / "release-checklist.md").read_text(encoding="utf-8")
    assert "OPENAI_CODEX_PLUGIN_VALIDATOR_REF" in workflow
    for phrase in ["python -m ruff check", "python -m pytest -q", "install-agents.py --codex-home", "doctor.py --codex-home"]:
        assert phrase in workflow or phrase in release
    for phrase in [
        "short-lived feature branch",
        "adversarial/deep review",
        "direct merge to main",
        "GitHub Actions cross-platform confirmation",
        "A pull request is optional",
        "all six Plugin Skills",
    ]:
        assert phrase in release
    assert "A green branch run does not replace the pull-request merge-result run" not in release
    ai_reference = (ROOT / "README_AI.md").read_text(encoding="utf-8")
    assert "App labels require direct human observation" in ai_reference
    assert "Host route/control claims require raw Host/rollout evidence from the exact candidate under validation" in ai_reference
    assert "Evidence status belongs to the release validation record, not this reference file" in ai_reference
    assert "never treat repository text or model self-report as proof that a Host/UI gate passed" in ai_reference
    assert "short-lived feature branch" in ai_reference


def test_release_checklist_requires_all_five_live_routes_without_promoting_accepted_to_observed():
    release = (ROOT / "docs" / "release-checklist.md").read_text(encoding="utf-8")
    for agent_type in [
        "subagents_dispatch_reader",
        "subagents_dispatch_worker",
        "subagents_dispatch_solver",
        "subagents_dispatch_investigator",
        "subagents_dispatch_advisor",
    ]:
        assert agent_type in release
    assert "accepted exact `agent_type` proves role acceptance only" in release
    assert "Missing source provenance makes only that dimension `UNKNOWN`" in release
    assert "Observed mismatches and public/local conflicts fail closed" in release


def test_formal_validation_resolves_python_311_without_bare_python_assumption():
    release = (ROOT / "docs" / "release-checklist.md").read_text(encoding="utf-8")
    runtime = (ROOT / "docs" / "runtime-attestation.md").read_text(encoding="utf-8")
    helper_runtime = (ROOT / "docs" / "python-runtime.md").read_text(encoding="utf-8")

    for text in [release, runtime, helper_runtime]:
        assert "Python 3.11" in text
    for phrase in [
        "PYTHON_PREREQUISITE_UNMET",
        "environment adaptation",
        "sys.executable",
    ]:
        assert phrase in helper_runtime
        assert phrase in release or phrase in runtime

    assert "<python-3.11+>" in release
    assert "<python-3.11+>" in runtime
    assert "python scripts/inspect-agent-runtime.py" not in release
    assert "python scripts/inspect-agent-runtime.py" not in runtime
    assert "A missing command named `python` is not a failed prerequisite" in release
    assert "downstream Host acceptance, runtime route, inspector, and behavioral gates are `NOT TESTED` or `INVALIDATED`" in release