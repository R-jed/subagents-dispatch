#!/usr/bin/env python3
from pathlib import Path

STATE = Path("scripts/dispatch_state.py")
TEST = Path("tests/test_dispatch_state_hardening.py")

text = STATE.read_text(encoding="utf-8")

old_failure = '''            record["failure_origin"] = (
                child.get("failure_origin", "tool_failure") if mapped == "FAILED" else "none"
            )
            if mapped != "FAILED":
                record["blocker"] = "none"
'''
new_failure = '''            if mapped == "FAILED":
                failure_origin = child.get("failure_origin", "tool_failure")
                record["failure_origin"] = (
                    failure_origin
                    if failure_origin in FAILURE_ORIGINS - {"none", "runtime_ambiguous"}
                    else "tool_failure"
                )
                record["blocker"] = "none"
            else:
                record["failure_origin"] = "none"
                record["blocker"] = "none"
'''
if text.count(old_failure) != 1:
    raise SystemExit("expected reconcile failure-origin block exactly once")
text = text.replace(old_failure, new_failure, 1)

old_remove = '''    identity = resolve_thread_id(thread_id)
    with state_lock(identity, temp_root=temp_root):
        _, _, path, _ = _paths(identity, temp_root, create=True)
        if not path.exists():
            return False
'''
new_remove = '''    identity = resolve_thread_id(thread_id)
    _, _, existing_path, _ = _paths(identity, temp_root, create=False)
    if not existing_path.exists():
        return False
    with state_lock(identity, temp_root=temp_root):
        _, _, path, _ = _paths(identity, temp_root, create=False)
        if not path.exists():
            return False
'''
if text.count(old_remove) != 1:
    raise SystemExit("expected remove_state preflight block exactly once")
text = text.replace(old_remove, new_remove, 1)
STATE.write_text(text, encoding="utf-8")

TEST.write_text(
    '''import importlib.util
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


def test_reconcile_real_failure_clears_quarantine_blocker_and_normalizes_origin(tmp_path: Path):
    module = load_module()
    state = module.new_state(thread_id="thread-1", locale="zh")
    state["units"] = [unit(module)]
    observation = {
        "complete": True,
        "children": [
            {
                "native_task_name": "sd-u1-a1-execute",
                "agent_id": "agent-1",
                "state": "errored",
                "failure_origin": "runtime_ambiguous",
            }
        ],
    }

    reconciled = module.reconcile_state(state, observation)
    record = reconciled["units"][0]
    assert record["control_state"] == "FAILED"
    assert record["failure_origin"] == "tool_failure"
    assert record["blocker"] == "none"
    assert record["quarantine_reason"] is None


def test_remove_missing_state_does_not_create_thread_or_lock(tmp_path: Path):
    module = load_module()
    thread_root = tmp_path / "subagents-dispatch" / "missing-thread"

    assert module.remove_state("missing-thread", temp_root=tmp_path) is False
    assert not thread_root.exists()
''',
    encoding="utf-8",
)
