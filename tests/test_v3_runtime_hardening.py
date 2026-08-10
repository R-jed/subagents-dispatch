import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "dispatch_state.py"


def load_module():
    spec = importlib.util.spec_from_file_location("dispatch_state_hardening", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def unit(*, state="SPAWN_PENDING", agent_id=None):
    return {
        "unit_id": "U1",
        "task_id": "task-1",
        "attempt": 1,
        "native_task_name": "sd-u1-a1-execute",
        "agent_id": agent_id,
        "role": "worker",
        "model_lane": "Luna Max",
        "responsibility": {"outcome": "change one file", "acceptance": "focused test passes"},
        "authority": {"write_scope": ["owned.py"]},
        "writer": True,
        "control_state": state,
        "adopted": False,
        "accepted": False,
        "failure_origin": "none",
        "blocker": "none",
        "quarantine_reason": None,
    }


def observation(state):
    return {
        "complete": True,
        "children": [
            {
                "native_task_name": "sd-u1-a1-execute",
                "agent_id": "agent-1",
                "state": state,
            }
        ],
    }


def test_current_codex_native_statuses_normalize_without_inventing_new_lifecycle_states():
    module = load_module()
    capsule = module.new_state(thread_id="thread-1", locale="en")
    capsule["units"] = [unit()]

    pending = module.reconcile_state(capsule, observation("pendingInit"))
    assert pending["units"][0]["control_state"] == "RUNNING"
    assert pending["units"][0]["agent_id"] == "agent-1"

    completed = module.reconcile_state(pending, observation("completed"))
    assert completed["units"][0]["control_state"] == "COMPLETED"

    shutdown_source = module.new_state(thread_id="thread-1", locale="en")
    shutdown_source["units"] = [unit(state="RUNNING", agent_id="agent-1")]
    shutdown = module.reconcile_state(shutdown_source, observation("shutdown"))
    assert shutdown["units"][0]["control_state"] == "CLOSED"
    assert shutdown["units"][0]["adopted"] is False

    error_source = module.new_state(thread_id="thread-1", locale="en")
    error_source["units"] = [unit(state="RUNNING", agent_id="agent-1")]
    errored = module.reconcile_state(error_source, observation("errored"))
    assert errored["units"][0]["control_state"] == "FAILED"
    assert errored["units"][0]["failure_origin"] == "tool_failure"


def test_codex_not_found_is_uncertain_and_never_releases_writer_ownership():
    module = load_module()
    capsule = module.new_state(thread_id="thread-1", locale="en")
    capsule["units"] = [unit(state="RUNNING", agent_id="agent-1")]

    reconciled = module.reconcile_state(capsule, observation("notFound"))
    record = reconciled["units"][0]
    assert record["control_state"] == "UNKNOWN"
    assert record["failure_origin"] == "runtime_ambiguous"
    assert record["quarantine_reason"] == "native_identity_not_found"

    takeover = module.takeover_target(reconciled)
    assert takeover["status"] == "resolved"
    assert takeover["conflicting_write_allowed"] is False


def test_spawn_binding_reloads_canonical_state_and_preserves_concurrent_metadata(tmp_path: Path):
    module = load_module()
    initial = module.new_state(thread_id="thread-1", locale="en")
    prepared = module.prepare_spawn(initial, unit(), temp_root=tmp_path)

    concurrent = module.load_state("thread-1", temp_root=tmp_path)
    assert concurrent is not None
    concurrent["accounting_refs"] = [
        {"ref": "control:status:concurrent", "kind": "control", "action": "Status"}
    ]
    module.write_state(concurrent, temp_root=tmp_path)

    bound = module.bind_spawn_identity(
        "thread-1",
        unit_id="U1",
        task_id="task-1",
        attempt=1,
        native_task_name="sd-u1-a1-execute",
        agent_id="agent-1",
        temp_root=tmp_path,
        now="2026-08-10T00:00:01Z",
    )
    record = bound["units"][0]
    assert record["control_state"] == "RUNNING"
    assert record["agent_id"] == "agent-1"
    assert bound["accounting_refs"] == [
        {"ref": "control:status:concurrent", "kind": "control", "action": "Status"}
    ]
    assert module.load_state("thread-1", temp_root=tmp_path) == bound
    assert prepared["units"][0]["agent_id"] is None

    with pytest.raises(module.StatePayloadError, match="no longer eligible"):
        module.bind_spawn_identity(
            "thread-1",
            unit_id="U1",
            task_id="task-1",
            attempt=1,
            native_task_name="sd-u1-a1-execute",
            agent_id="agent-2",
            temp_root=tmp_path,
        )


def test_persisted_reconciliation_updates_same_capsule_without_losing_metadata(tmp_path: Path):
    module = load_module()
    initial = module.new_state(thread_id="thread-1", locale="zh")
    module.prepare_spawn(initial, unit(), temp_root=tmp_path)
    module.bind_spawn_identity(
        "thread-1",
        unit_id="U1",
        task_id="task-1",
        attempt=1,
        native_task_name="sd-u1-a1-execute",
        agent_id="agent-1",
        temp_root=tmp_path,
    )
    current = module.load_state("thread-1", temp_root=tmp_path)
    assert current is not None
    current["accounting_refs"] = [
        {"ref": "control:status:metadata", "kind": "control", "action": "Status"}
    ]
    module.write_state(current, temp_root=tmp_path)

    snapshot = module.persisted_status_snapshot(
        "thread-1",
        observation("completed"),
        temp_root=tmp_path,
        now="2026-08-10T00:00:02Z",
    )
    assert snapshot["units"][0]["control_state"] == "COMPLETED"
    persisted = module.load_state("thread-1", temp_root=tmp_path)
    assert persisted is not None
    assert persisted["units"][0]["control_state"] == "COMPLETED"
    assert persisted["accounting_refs"] == [
        {"ref": "control:status:metadata", "kind": "control", "action": "Status"}
    ]
    assert snapshot["reconciled_state"] == persisted


def test_receipt_uses_materialized_selected_lane_without_claiming_live_telemetry():
    module = load_module()
    materialized = [
        {
            "unit_id": "U1",
            "attempt": 1,
            "agent_id": "agent-1",
            "role": "worker",
            "model_lane": "Luna Max",
        }
    ]
    event = {
        "ref": "attempt:U1:A1",
        "kind": "attempt",
        "unit_id": "U1",
        "attempt": 1,
        "agent_id": "agent-1",
        "activity": "execute",
    }

    summary = module.account_receipt([event], materialized_units=materialized)
    assert summary["dispatch"] == [
        {"model_lane": "Luna Max", "activity": "execute", "count": 1}
    ]
    assert module.format_receipt(summary, locale="en").startswith("Dispatch: Luna Max Execute")

    configured = {**event, "model_lane": "Luna Max", "model_evidence_source": "configured"}
    assert module.account_receipt([configured], materialized_units=materialized)["dispatch"] == [
        {"model_lane": "Luna Max", "activity": "execute", "count": 1}
    ]

    with pytest.raises(module.ReceiptAccountingError, match="conflicts with selected model lane"):
        module.account_receipt(
            [{**event, "model_lane": "Sol High", "model_evidence_source": "native"}],
            materialized_units=materialized,
        )
