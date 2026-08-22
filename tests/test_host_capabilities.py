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


def evidence(*, capacity: int | None = 4, fork_turns_none: bool = True) -> dict:
    return {
        "surface": "multi_agent_v2",
        "tools": [
            "spawn_agent",
            "followup_task",
            "wait_agent",
            "list_agents",
            "interrupt_agent",
        ],
        "fork_turns_none": fork_turns_none,
        "max_spawned_threads": capacity,
    }


def test_complete_native_evidence_normalizes_to_execution_ready_snapshot():
    module = load_module()
    snapshot = module.normalize_host_capabilities(evidence())

    assert snapshot["execution_ready"] is True
    assert snapshot["missing"] == []
    assert snapshot["capabilities"] == {
        "spawn": True,
        "observe": True,
        "wait_or_wakeup": True,
        "followup": True,
        "interrupt": True,
    }
    assert snapshot["capacity_excludes_primary"] is True
    assert snapshot["max_spawned_threads"] == 4


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


def test_missing_native_primitive_marks_snapshot_not_execution_ready():
    module = load_module()
    payload = evidence()
    payload["tools"].remove("interrupt_agent")

    snapshot = module.normalize_host_capabilities(payload)

    assert snapshot["execution_ready"] is False
    assert snapshot["capabilities"]["interrupt"] is False
    assert snapshot["missing"] == ["interrupt"]


def test_fresh_context_capability_is_required_for_execution():
    module = load_module()
    snapshot = module.normalize_host_capabilities(evidence(fork_turns_none=False))

    assert snapshot["execution_ready"] is False
    assert snapshot["missing"] == ["fresh_context_spawn"]


def test_unknown_host_capacity_stays_unknown_instead_of_inventing_default():
    module = load_module()
    snapshot = module.normalize_host_capabilities(evidence(capacity=None))

    assert snapshot["execution_ready"] is True
    assert snapshot["max_spawned_threads"] is None


def test_malformed_or_partial_evidence_is_rejected():
    module = load_module()
    payload = evidence()
    del payload["tools"]
    with pytest.raises(module.HostCapabilityError, match="missing fields"):
        module.normalize_host_capabilities(payload)

    payload = evidence()
    payload["max_spawned_threads"] = 0
    with pytest.raises(module.HostCapabilityError, match="positive integer"):
        module.normalize_host_capabilities(payload)

    payload = evidence()
    payload["unexpected"] = {}
    with pytest.raises(module.HostCapabilityError, match="unsupported fields"):
        module.normalize_host_capabilities(payload)


def test_unclassified_collaboration_identity_is_rejected_for_host_adaptation():
    module = load_module()
    payload = evidence()
    payload["tools"].append("multi_agent_spawn")

    with pytest.raises(module.HostCapabilityError, match="unclassified collaboration"):
        module.normalize_host_capabilities(payload)


def test_namespaced_native_identities_map_to_same_semantics():
    module = load_module()
    payload = evidence()
    payload["tools"] = [
        "collaboration.spawn_agent",
        "collaboration.followup_task",
        "collaboration.wait_agent",
        "collaboration.list_agents",
        "collaboration.interrupt_agent",
    ]

    snapshot = module.normalize_host_capabilities(payload)

    assert snapshot["execution_ready"] is True
    assert snapshot["missing"] == []
    assert all(snapshot["capabilities"].values())


def test_send_message_is_classified_but_not_required_for_main_led_correctness():
    module = load_module()
    payload = evidence()
    payload["tools"].append("send_message")

    snapshot = module.normalize_host_capabilities(payload)

    assert snapshot["execution_ready"] is True
    assert set(snapshot["capabilities"]) == set(module.REQUIRED_CAPABILITIES)


def test_normalized_snapshot_validation_rejects_shape_drift():
    module = load_module()
    snapshot = module.normalize_host_capabilities(evidence())
    drifted = dict(snapshot)
    drifted["capabilities"] = {**snapshot["capabilities"], "unknown_capability": True}

    with pytest.raises(module.HostCapabilityError, match="capability set"):
        module.validate_normalized_snapshot(drifted)


def test_capability_snapshot_copy_is_validated_and_detached():
    module = load_module()
    snapshot = module.normalize_host_capabilities(evidence())
    copied = module.capability_snapshot_copy(snapshot)

    assert copied == snapshot
    assert copied is not snapshot
    assert copied["capabilities"] is not snapshot["capabilities"]
