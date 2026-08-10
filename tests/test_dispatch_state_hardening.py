import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "dispatch_state.py"


def load_module():
    spec = importlib.util.spec_from_file_location("dispatch_state_hardening", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def unit(module, *, state="UNKNOWN", blocker="investigation"):
    return {
        "unit_id": "U1",
        "task_id": "task-1",
        "attempt": 1,
        "native_task_name": "sd-u1-a1-execute",
        "agent_id": "agent-1",
        "role": "worker",
        "model_lane": "Luna Max",
        "responsibility": {"outcome": "change one file", "acceptance": "focused test passes"},
        "authority": {"write_scope": ["owned.py"]},
        "writer": True,
        "control_state": state,
        "adopted": False,
        "accepted": False,
        "failure_origin": "runtime_ambiguous" if state == "UNKNOWN" else "none",
        "blocker": blocker,
        "quarantine_reason": "native_identity_not_found" if state == "UNKNOWN" else None,
    }


def errored_observation(*, failure_origin: str):
    return {
        "complete": True,
        "children": [
            {
                "native_task_name": "sd-u1-a1-execute",
                "agent_id": "agent-1",
                "state": "errored",
                "failure_origin": failure_origin,
            }
        ],
    }


def test_reconcile_real_failure_clears_quarantine_blocker_and_normalizes_origin(tmp_path: Path):
    module = load_module()
    state = module.new_state(thread_id="thread-1", locale="zh")
    state["units"] = [unit(module)]

    reconciled = module.reconcile_state(
        state,
        errored_observation(failure_origin="runtime_ambiguous"),
    )
    record = reconciled["units"][0]
    assert record["control_state"] == "FAILED"
    assert record["failure_origin"] == "tool_failure"
    assert record["blocker"] == "none"
    assert record["quarantine_reason"] is None


def test_reconcile_real_failure_preserves_supported_failure_origin():
    module = load_module()
    state = module.new_state(thread_id="thread-1", locale="en")
    state["units"] = [unit(module)]

    reconciled = module.reconcile_state(
        state,
        errored_observation(failure_origin="timeout"),
    )
    record = reconciled["units"][0]
    assert record["control_state"] == "FAILED"
    assert record["failure_origin"] == "timeout"
    assert record["blocker"] == "none"
    assert record["quarantine_reason"] is None


def test_remove_missing_state_does_not_create_thread_or_lock(tmp_path: Path):
    module = load_module()
    thread_root = tmp_path / "subagents-dispatch" / "missing-thread"

    assert module.remove_state("missing-thread", temp_root=tmp_path) is False
    assert not thread_root.exists()
