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


def test_ci_and_release_docs_keep_host_app_evidence_pending_and_local_gates_deterministic():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    release = (ROOT / "docs" / "release-checklist.md").read_text(encoding="utf-8")
    assert "OPENAI_CODEX_PLUGIN_VALIDATOR_REF" in workflow
    for phrase in ["python -m ruff check", "python -m pytest -q", "install-agents.py --codex-home", "doctor.py --codex-home"]:
        assert phrase in workflow or phrase in release
    assert "directly on `main`" in release
    assert "App labels require direct human observation" in (ROOT / "README_AI.md").read_text(encoding="utf-8")
    assert "Host route/control evidence remains pending" in (ROOT / "README_AI.md").read_text(encoding="utf-8")
