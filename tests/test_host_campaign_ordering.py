from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOST_SMOKE = ROOT / "docs" / "v4" / "host-smoke.json"
QUALIFICATION_PLAN = ROOT / "tasks" / "real-host-qualification-plan.md"


def payload() -> dict:
    return json.loads(HOST_SMOKE.read_text(encoding="utf-8"))


def probes() -> dict[str, dict]:
    return {item["id"]: item for item in payload()["required_probes"]}


def requirements(probe: dict) -> str:
    return " ".join(probe["requires"]).lower()


def test_native_campaign_is_exactly_n0_through_n7_and_stays_pending_in_repo():
    current = payload()

    assert current["schema_version"] == "4.0.0-native-host-smoke-2"
    assert current["gate_id"] == "v4-real-host-n0-n7"
    assert current["status"] == "PENDING"
    assert current["results"] == {}
    assert [item["id"] for item in current["required_probes"]] == [f"N{index}" for index in range(8)]


def test_environment_binding_uses_native_session_and_thread_identity():
    current = payload()

    assert current["required_environment_fields"] == [
        "architecture",
        "codex_version",
        "host_build",
        "platform",
        "session_id",
        "thread_id",
    ]
    assert "run_id" not in current["required_environment_fields"]

    identity = current["environment_identity_semantics"]
    assert "session-tree identity" in identity["session_id"]["meaning"]
    assert "session_meta.session_id" in identity["session_id"]["authoritative_sources"][-1]
    assert "current root thread" in identity["thread_id"]["meaning"]
    assert any("CODEX_THREAD_ID" in source for source in identity["thread_id"]["authoritative_sources"])
    assert "session_meta.id" in identity["thread_id"]["authoritative_sources"][-1]
    assert "UNKNOWN" in identity["unknown_policy"]
    assert "repository commit" in identity["unknown_policy"]


def test_spawn_and_capacity_gates_separate_success_rejection_and_ambiguity():
    current = probes()
    n2 = requirements(current["N2"])
    n3 = requirements(current["N3"])

    assert "native child identity" in n2
    assert "executionbinding" in n2
    assert "no child identity or resident child materializes" in n3
    assert "rolls back provisional execution" in n3
    assert "unknown" in n3


def test_same_child_interrupt_and_writer_settlement_are_explicitly_sequenced():
    current = probes()

    assert "same executionbinding identity" in requirements(current["N4"])
    assert "interrupt result alone does not release writerlease" in requirements(current["N5"])
    assert "stale control or lease generation evidence cannot settle" in requirements(current["N5"])
    assert "unknown or unsettled writer ownership blocks replacement" in requirements(current["N6"])
    assert "single-writer invariant" in requirements(current["N6"])


def test_managed_depth_and_rollout_privacy_have_separate_gates():
    current = probes()
    n1 = requirements(current["N1"])

    assert current["N1"]["operation"] == "managed delegation depth"
    assert "canonical managed spawn route" in n1
    assert "adversarial untrusted-input" in n1
    assert "does not issue spawn_agent" in n1
    assert "no descendant identity" in n1
    assert "is fail" in n1
    assert "generic v2 recursive-capability probes" in n1
    assert "allowlisted inspection omits assignment text and reasoning content" in requirements(current["N7"])
    assert "N8" not in current


def test_h1_h2_require_single_probe_guard_without_issue_comment_runtime_dependency():
    plan = QUALIFICATION_PLAN.read_text(encoding="utf-8")

    assert "scripts/host_qualification_guard.py" in plan
    assert "allocate_single_probe_execution" in plan
    assert "prepare_single_probe_spawn" in plan
    assert "qualification_run_ref" in plan
    assert "qualification:<campaign>:<h1|h2>:<profile>" in plan
    assert "preflight:issue-91-comment-" not in plan
    assert "Do not reject a completed qualification result and allocate a fresh attempt" in plan


def test_host_lifecycle_is_operator_owned_and_self_restart_is_fail_closed():
    plan = QUALIFICATION_PLAN.read_text(encoding="utf-8")

    assert "OPERATOR_ACTION_REQUIRED_STOP" in plan
    assert "Codex MUST NOT quit, restart, relaunch, or update the Desktop Host" in plan
    assert "Codex must never perform steps 1 through 3" in plan
    assert "Never attempt to bridge a Host restart" in plan


def test_issue_91_is_evidence_journal_not_per_action_preflight_protocol():
    plan = QUALIFICATION_PLAN.read_text(encoding="utf-8")

    assert "Issue #91 is the append-only Host evidence journal" in plan
    assert "No Issue #91 comment is required before every Host action" in plan
    assert "Prefer one consolidated entry per phase" in plan
    assert "routine preflight, review, and amendment comments should not be created" in plan
