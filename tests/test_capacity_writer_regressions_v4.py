from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load_module(name: str, filename: str):
    scripts = str(SCRIPTS)
    sys.path.insert(0, scripts)
    try:
        spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts)


def work_unit(*, writable: bool) -> dict:
    scope = ["src/u1.py"] if writable else []
    return {
        "unit_id": "U1",
        "intent": "implement" if writable else "inspect",
        "goal": "bounded task",
        "output": "patch" if writable else "facts",
        "depends_on": [],
        "state": "READY",
        "ownership": {"write": scope, "forbidden": []},
        "authority_ceiling": "bounded-source-write" if writable else "none",
        "write_scope_ceiling": scope,
        "done_when": "Main verifies result",
        "responsibility_context": {
            "interfaces": [],
            "invariants": [],
            "decision_boundary": "Escalate material decisions to Main.",
            "accepted_evidence_refs": [],
            "do_not_redo": [],
            "stop_boundary": "Stop and report blockers to Main.",
        },
        "accepted_result_ref": None,
        "accepted_execution_id": None,
        "accepted_control_epoch": None,
    }


def test_explicit_pre_materialization_rejection_rolls_back_attempt_and_reserved_writer(tmp_path: Path):
    state = load_module("native_capacity_state_rollback", "dispatch_state_v4.py")
    lifecycle = load_module("native_capacity_lifecycle_rollback", "execution_lifecycle_v4.py")

    payload = state.new_state(thread_id="root-thread")
    payload["work_units"] = [work_unit(writable=True)]
    state.write_state(payload, temp_root=tmp_path)

    lifecycle.allocate_execution(
        "root-thread",
        unit_id="U1",
        execution_id="exec-rejected",
        native_task_name="sd_u1_a1",
        profile_id="worker",
        granted_authority="bounded-source-write",
        granted_write_scope=["src/u1.py"],
        writer_lease_id="lease-rejected",
        temp_root=tmp_path,
    )
    provisional = state.load_state("root-thread", temp_root=tmp_path)
    assert provisional is not None
    assert provisional["executions"][0]["attempt_no"] == 1
    assert provisional["writer_lease"]["state"] == "RESERVED"

    lifecycle.rollback_pre_materialization_spawn(
        "root-thread", execution_id="exec-rejected", temp_root=tmp_path
    )
    rolled_back = state.load_state("root-thread", temp_root=tmp_path)
    assert rolled_back is not None
    assert rolled_back["executions"] == []
    assert rolled_back["writer_lease"] is None
    assert rolled_back["work_units"][0]["state"] == "READY"

    second = lifecycle.allocate_execution(
        "root-thread",
        unit_id="U1",
        execution_id="exec-real",
        native_task_name="sd_u1_a1",
        profile_id="worker",
        granted_authority="bounded-source-write",
        granted_write_scope=["src/u1.py"],
        writer_lease_id="lease-real",
        temp_root=tmp_path,
    )
    assert second["execution"]["attempt_no"] == 1
    assert second["execution"]["native_task_name"] == "sd_u1_a1"


def test_current_generation_compact_host_observation_is_sufficient_for_writer_settlement(tmp_path: Path):
    state = load_module("native_capacity_state_settlement", "dispatch_state_v4.py")
    writer = load_module("native_capacity_writer_settlement", "writer_lease_v4.py")

    payload = state.new_state(thread_id="root-thread")
    unit = work_unit(writable=True)
    unit["state"] = "RESULT_READY"
    payload["work_units"] = [unit]
    payload["executions"] = [
        {
            "execution_id": "exec-1",
            "unit_id": "U1",
            "team_plan_revision": None,
            "attempt_no": 1,
            "profile_id": "worker",
            "agent_id": "agent-1",
            "native_task_name": "sd_u1_a1",
            "model": "gpt-5.6-luna",
            "effort": "max",
            "granted_authority": "bounded-source-write",
            "granted_write_scope": ["src/u1.py"],
            "workspace_id": "canonical",
            "lifecycle": "COMPLETED",
            "control_epoch": 0,
            "followup_count": 0,
            "failure_origin": "none",
            "blocker": "none",
            "quarantine_reason": None,
        }
    ]
    payload["writer_lease"] = {
        "lease_id": "lease-1",
        "lease_epoch": 1,
        "workspace_id": "canonical",
        "unit_id": "U1",
        "owner_kind": "execution",
        "owner_id": "exec-1",
        "state": "HELD",
    }
    payload["accounting_refs"] = [
        {
            "ref": "host-observation:exec-1:0:1:COMPLETED",
            "kind": "host_observation",
            "execution_id": "exec-1",
            "control_epoch": 0,
            "lease_epoch": 1,
            "lifecycle": "COMPLETED",
        }
    ]
    state.write_state(payload, temp_root=tmp_path)

    released = writer.release_settled_execution_writer(
        "root-thread",
        execution_id="exec-1",
        lease_id="lease-1",
        lease_epoch=1,
        temp_root=tmp_path,
    )
    assert released["state"] == "RELEASED"


def test_stale_lease_epoch_proof_cannot_release_writer(tmp_path: Path):
    state = load_module("native_capacity_state_stale", "dispatch_state_v4.py")
    writer = load_module("native_capacity_writer_stale", "writer_lease_v4.py")

    payload = state.new_state(thread_id="root-thread")
    unit = work_unit(writable=True)
    unit["state"] = "RESULT_READY"
    payload["work_units"] = [unit]
    payload["executions"] = [
        {
            "execution_id": "exec-1",
            "unit_id": "U1",
            "team_plan_revision": None,
            "attempt_no": 1,
            "profile_id": "worker",
            "agent_id": "agent-1",
            "native_task_name": "sd_u1_a1",
            "model": "gpt-5.6-luna",
            "effort": "max",
            "granted_authority": "bounded-source-write",
            "granted_write_scope": ["src/u1.py"],
            "workspace_id": "canonical",
            "lifecycle": "COMPLETED",
            "control_epoch": 0,
            "followup_count": 0,
            "failure_origin": "none",
            "blocker": "none",
            "quarantine_reason": None,
        }
    ]
    payload["writer_lease"] = {
        "lease_id": "lease-2",
        "lease_epoch": 2,
        "workspace_id": "canonical",
        "unit_id": "U1",
        "owner_kind": "execution",
        "owner_id": "exec-1",
        "state": "HELD",
    }
    payload["accounting_refs"] = [
        {
            "ref": "host-observation:exec-1:0:1:COMPLETED",
            "kind": "host_observation",
            "execution_id": "exec-1",
            "control_epoch": 0,
            "lease_epoch": 1,
            "lifecycle": "COMPLETED",
        }
    ]
    state.write_state(payload, temp_root=tmp_path)

    try:
        writer.release_settled_execution_writer(
            "root-thread",
            execution_id="exec-1",
            lease_id="lease-2",
            lease_epoch=2,
            temp_root=tmp_path,
        )
    except writer.WriterLeaseError as exc:
        assert "fresh current-epoch Host observation proof" in str(exc)
    else:
        raise AssertionError("stale proof unexpectedly released WriterLease")
