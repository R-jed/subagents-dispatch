from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
MODULE_PATH = SCRIPTS / "host_capabilities.py"


def load_module():
    scripts = str(SCRIPTS)
    sys.path.insert(0, scripts)
    try:
        spec = importlib.util.spec_from_file_location("host_capabilities_under_test", MODULE_PATH)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules["host_capabilities_under_test"] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts)


def evidence(*, post: bool = True, stop: bool = True, capacity: int | None = 4) -> dict:
    lifecycle = ["spawn_agent", "followup_task", "interrupt_agent"]
    pre_guarded = [*lifecycle, "list_agents", "send_message"]
    post_guarded = [*lifecycle, "list_agents"]
    return {
        "surface": "multi_agent_v2",
        "tools": [
            "spawn_agent",
            "send_message",
            "followup_task",
            "wait_agent",
            "list_agents",
            "interrupt_agent",
        ],
        "hooks": {
            "PreToolUse": pre_guarded,
            "PostToolUse": post_guarded
            if post
            else ["spawn_agent", "interrupt_agent", "list_agents"],
            "SubagentStop": stop,
        },
        "fork_turns_none": True,
        "max_spawned_threads": capacity,
    }


def trust(**overrides) -> dict:
    value = {
        "manifest_sha256": "b" * 64,
        "trusted_current_definition": True,
        "evidence_ref": "host-smoke:H00",
    }
    value.update(overrides)
    return value


def test_complete_evidence_normalizes_to_execution_ready_snapshot():
    module = load_module()
    snapshot = module.normalize_host_capabilities(evidence())

    assert snapshot["execution_ready"] is True
    assert snapshot["missing"] == []
    assert all(snapshot["capabilities"].values())
    assert snapshot["capacity_excludes_primary"] is True
    assert snapshot["max_spawned_threads"] == 4
    assert module.effective_managed_child_limit(snapshot, product_limit=3) == 3


def test_public_v2_agent_status_union_is_normalized_without_assuming_agent_id():
    module = load_module()

    assert module.normalize_agent_status("pending_init") == {
        "state": "pending_init",
        "detail": None,
    }
    assert module.normalize_agent_status("running") == {"state": "running", "detail": None}
    assert module.normalize_agent_status({"completed": None}) == {
        "state": "completed",
        "detail": None,
    }
    assert module.normalize_agent_status({"completed": "done"}) == {
        "state": "completed",
        "detail": "done",
    }
    assert module.normalize_agent_status({"errored": "boom"}) == {
        "state": "errored",
        "detail": "boom",
    }


def test_malformed_agent_status_fails_closed():
    module = load_module()

    for status in ["completed", {"completed": 1}, {"errored": None}, {"other": "x"}]:
        with pytest.raises(module.HostCapabilityError, match="status"):
            module.normalize_agent_status(status)


def test_missing_lifecycle_post_hook_fails_closed():
    module = load_module()
    snapshot = module.normalize_host_capabilities(evidence(post=False))

    assert snapshot["execution_ready"] is False
    assert snapshot["capabilities"]["post_tool_use_guard"] is False
    assert "post_tool_use_guard" in snapshot["missing"]


def test_host_observation_requires_paired_pre_and_post_hooks():
    module = load_module()
    payload = evidence()
    payload["hooks"]["PreToolUse"] = [
        "spawn_agent",
        "followup_task",
        "interrupt_agent",
        "send_message",
    ]
    snapshot = module.normalize_host_capabilities(payload)

    assert snapshot["execution_ready"] is False
    assert snapshot["capabilities"]["host_observation_guard"] is False
    assert "host_observation_guard" in snapshot["missing"]


def test_missing_peer_message_guard_fails_closed_when_tool_is_exposed():
    module = load_module()
    payload = evidence()
    payload["hooks"]["PreToolUse"].remove("send_message")
    snapshot = module.normalize_host_capabilities(payload)

    assert snapshot["execution_ready"] is False
    assert snapshot["capabilities"]["peer_message_guard"] is False
    assert "peer_message_guard" in snapshot["missing"]


def test_missing_subagent_stop_veto_fails_closed():
    module = load_module()
    snapshot = module.normalize_host_capabilities(evidence(stop=False))

    assert snapshot["execution_ready"] is False
    assert "subagent_stop_veto" in snapshot["missing"]


def test_fresh_context_capability_is_required_for_execution():
    module = load_module()
    payload = evidence()
    payload["fork_turns_none"] = False
    snapshot = module.normalize_host_capabilities(payload)

    assert snapshot["execution_ready"] is False
    assert "fresh_context_spawn" in snapshot["missing"]


def test_unknown_host_capacity_stays_unknown_instead_of_inventing_default():
    module = load_module()
    snapshot = module.normalize_host_capabilities(evidence(capacity=None))

    assert snapshot["execution_ready"] is True
    assert snapshot["max_spawned_threads"] is None
    assert module.effective_managed_child_limit(snapshot) is None


def test_product_limit_is_capped_by_spawned_thread_capacity_excluding_primary():
    module = load_module()
    snapshot = module.normalize_host_capabilities(evidence(capacity=2))

    assert snapshot["capacity_excludes_primary"] is True
    assert module.effective_managed_child_limit(snapshot, product_limit=3) == 2


def test_malformed_or_partial_evidence_is_rejected():
    module = load_module()
    payload = evidence()
    del payload["hooks"]
    with pytest.raises(module.HostCapabilityError, match="missing fields"):
        module.normalize_host_capabilities(payload)

    payload = evidence()
    payload["max_spawned_threads"] = 0
    with pytest.raises(module.HostCapabilityError, match="positive integer"):
        module.normalize_host_capabilities(payload)


def test_unclassified_flattened_collaboration_identity_is_rejected():
    module = load_module()
    payload = evidence()
    payload["tools"].append("multi_agent_spawn")

    with pytest.raises(module.HostCapabilityError, match="unclassified collaboration"):
        module.normalize_host_capabilities(payload)


def test_namespaced_model_identity_requires_flattened_hook_coverage():
    module = load_module()
    payload = evidence()
    payload["tools"].append("collaboration.spawn_agent")

    snapshot = module.normalize_host_capabilities(payload)

    assert snapshot["execution_ready"] is False
    assert snapshot["capabilities"]["pre_tool_use_guard"] is False
    assert snapshot["capabilities"]["post_tool_use_guard"] is False


def test_namespaced_model_identity_can_pass_with_exact_flattened_hook_coverage():
    module = load_module()
    payload = evidence()
    payload["tools"].append("collaboration.spawn_agent")
    payload["hooks"]["PreToolUse"].append("collaborationspawn_agent")
    payload["hooks"]["PostToolUse"].append("collaborationspawn_agent")

    snapshot = module.normalize_host_capabilities(payload)

    assert snapshot["execution_ready"] is True
    assert snapshot["missing"] == []


def test_dotted_model_identity_does_not_count_as_hook_identity():
    module = load_module()
    payload = evidence()
    payload["tools"].append("collaboration.spawn_agent")
    payload["hooks"]["PreToolUse"].append("collaboration.spawn_agent")
    payload["hooks"]["PostToolUse"].append("collaboration.spawn_agent")

    snapshot = module.normalize_host_capabilities(payload)

    assert snapshot["execution_ready"] is False
    assert module.canonical_hook_tool_name("collaboration.spawn_agent") is None
    assert module.canonical_hook_tool_name("collaborationspawn_agent") == "spawn_agent"


def test_required_hook_tool_set_is_exact_lifecycle_surface():
    module = load_module()
    assert module.required_lifecycle_hook_tools() == (
        "spawn_agent",
        "followup_task",
        "interrupt_agent",
    )


def test_guard_coverage_proof_requires_execution_ready_host_and_current_trust():
    module = load_module()
    snapshot = module.normalize_host_capabilities(evidence(capacity=3))
    proof = module.build_guard_coverage_proof(
        snapshot,
        session_id="thread-proof",
        trust_evidence=trust(),
    )
    assert proof == {
        "schema_version": "4.0",
        "authority": "diagnostic_only",
        "session_id": "thread-proof",
        "manifest_sha256": "b" * 64,
        "trusted_current_definition": True,
        "pre_tool_use": True,
        "post_tool_use": True,
        "host_observation_guard": True,
        "peer_message_guard": True,
        "subagent_stop_veto": True,
        "evidence_ref": "host-smoke:H00",
    }

    with pytest.raises(module.HostCapabilityError, match="not proven trusted"):
        module.build_guard_coverage_proof(
            snapshot,
            session_id="thread-proof",
            trust_evidence=trust(trusted_current_definition=False),
        )


def test_guard_coverage_proof_rejects_incomplete_lifecycle_hook_snapshot():
    module = load_module()
    payload = evidence(capacity=3)
    payload["hooks"]["PostToolUse"] = ["spawn_agent", "followup_task", "list_agents"]
    snapshot = module.normalize_host_capabilities(payload)
    assert snapshot["execution_ready"] is False
    with pytest.raises(module.HostCapabilityError, match="execution-ready"):
        module.build_guard_coverage_proof(
            snapshot,
            session_id="thread-proof",
            trust_evidence=trust(),
        )
