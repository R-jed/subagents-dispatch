#!/usr/bin/env python3
from pathlib import Path

DOCTOR = Path("tests/test_doctor.py")
RUNTIME = Path("tests/test_v3_runtime_hardening.py")

doctor = DOCTOR.read_text(encoding="utf-8")
old_pending = '''        "team_plan_revision": None,
        "units": [],
        "accounting_refs": [],
        "controls": [],
        "pending_takeover": {"unit_id": "U1", "status": "pending"},
'''
new_pending = '''        "team_plan_revision": None,
        "units": [
            {
                "unit_id": "U1",
                "task_id": "task-1",
                "attempt": 1,
                "native_task_name": "sd-u1-a1-execute",
                "agent_id": "agent-1",
                "role": "worker",
                "model_lane": "Luna Max",
                "responsibility": {"outcome": "finish bounded work", "acceptance": "Main accepts result"},
                "authority": {"write_scope": ["owned.py"]},
                "writer": True,
                "control_state": "RUNNING",
                "adopted": False,
                "accepted": False,
                "failure_origin": "none",
                "blocker": "none",
                "quarantine_reason": None,
            }
        ],
        "accounting_refs": [],
        "controls": [],
        "pending_takeover": {"unit_id": "U1", "status": "pending"},
'''
if doctor.count(old_pending) != 1:
    raise SystemExit("expected Doctor pending-takeover fixture exactly once")
doctor = doctor.replace(old_pending, new_pending, 1)
DOCTOR.write_text(doctor, encoding="utf-8")

runtime = RUNTIME.read_text(encoding="utf-8")
old_concurrent = '''    concurrent["controls"] = [{"ref": "concurrent-metadata"}]
    module.write_state(concurrent, temp_root=tmp_path)
'''
new_concurrent = '''    concurrent["accounting_refs"] = [
        {"ref": "control:status:concurrent", "kind": "control", "action": "Status"}
    ]
    module.write_state(concurrent, temp_root=tmp_path)
'''
if runtime.count(old_concurrent) != 1:
    raise SystemExit("expected concurrent controls fixture exactly once")
runtime = runtime.replace(old_concurrent, new_concurrent, 1)
old_concurrent_assert = '''    assert bound["controls"] == [{"ref": "concurrent-metadata"}]
'''
new_concurrent_assert = '''    assert bound["accounting_refs"] == [
        {"ref": "control:status:concurrent", "kind": "control", "action": "Status"}
    ]
'''
if runtime.count(old_concurrent_assert) != 1:
    raise SystemExit("expected concurrent controls assertion exactly once")
runtime = runtime.replace(old_concurrent_assert, new_concurrent_assert, 1)

old_status = '''    current["controls"] = [{"ref": "status-metadata"}]
    module.write_state(current, temp_root=tmp_path)
'''
new_status = '''    current["accounting_refs"] = [
        {"ref": "control:status:metadata", "kind": "control", "action": "Status"}
    ]
    module.write_state(current, temp_root=tmp_path)
'''
if runtime.count(old_status) != 1:
    raise SystemExit("expected status controls fixture exactly once")
runtime = runtime.replace(old_status, new_status, 1)
old_status_assert = '''    assert persisted["controls"] == [{"ref": "status-metadata"}]
'''
new_status_assert = '''    assert persisted["accounting_refs"] == [
        {"ref": "control:status:metadata", "kind": "control", "action": "Status"}
    ]
'''
if runtime.count(old_status_assert) != 1:
    raise SystemExit("expected status controls assertion exactly once")
runtime = runtime.replace(old_status_assert, new_status_assert, 1)
RUNTIME.write_text(runtime, encoding="utf-8")
