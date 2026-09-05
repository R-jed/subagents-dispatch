from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import sys

import pytest


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


def responsibility_context() -> dict:
    return {
        "interfaces": [],
        "invariants": [],
        "decision_boundary": "Return material decisions to Main.",
        "accepted_evidence_refs": [],
        "do_not_redo": [],
        "stop_boundary": "Stop and report blockers to Main.",
    }


def work_unit(*, writable: bool) -> dict:
    scope = ["src/a.py"] if writable else []
    return {
        "unit_id": "U1",
        "intent": "implement" if writable else "inspect",
        "goal": "bounded responsibility",
        "output": "patch" if writable else "evidence",
        "depends_on": [],
        "state": "READY",
        "ownership": {"write": scope, "forbidden": []},
        "authority_ceiling": "bounded-source-write" if writable else "none",
        "write_scope_ceiling": scope,
        "done_when": "Main verifies the result",
        "responsibility_context": responsibility_context(),
        "accepted_result_ref": None,
        "accepted_execution_id": None,
        "accepted_control_epoch": None,
    }


def install_unit(state, tmp_path: Path, *, writable: bool = False) -> None:
    payload = state.new_state(thread_id="root-thread")
    payload["work_units"] = [work_unit(writable=writable)]
    state.write_state(payload, temp_root=tmp_path)


def test_execution_binding_records_role_and_exact_route_and_spawn_sends_it(tmp_path: Path):
    state = load_module("gpt6_binding_state", "dispatch_state_v4.py")
    lifecycle = load_module("gpt6_binding_lifecycle", "execution_lifecycle_v4.py")
    install_unit(state, tmp_path)

    allocated = lifecycle.allocate_execution(
        "root-thread",
        unit_id="U1",
        execution_id="exec-1",
        native_task_name="sd_u1_a1",
        role_id="product_manager",
        reasoning_effort="medium",
        granted_authority="none",
        temp_root=tmp_path,
    )["execution"]

    assert allocated["role_id"] == "product_manager"
    assert allocated["agent_type"] == "subagents_dispatch_product_manager"
    assert allocated["model"] == "gpt-5.6-sol"
    assert allocated["reasoning_effort"] == "medium"
    assert "profile_id" not in allocated
    assert "effort" not in allocated

    spawn = lifecycle.build_managed_spawn_tool_input(
        "root-thread", execution_id="exec-1", temp_root=tmp_path
    )
    assert spawn["agent_type"] == "subagents_dispatch_product_manager"
    assert spawn["model"] == "gpt-5.6-sol"
    assert spawn["reasoning_effort"] == "medium"
    assert spawn["fork_turns"] == "none"


def test_product_manager_effort_is_explicit_and_out_of_policy_effort_is_rejected(tmp_path: Path):
    state = load_module("gpt6_binding_state_effort", "dispatch_state_v4.py")
    lifecycle = load_module("gpt6_binding_lifecycle_effort", "execution_lifecycle_v4.py")
    install_unit(state, tmp_path)

    with pytest.raises(lifecycle.ExecutionLifecycleError, match="explicit reasoning_effort"):
        lifecycle.allocate_execution(
            "root-thread",
            unit_id="U1",
            execution_id="exec-1",
            native_task_name="sd_u1_a1",
            role_id="product_manager",
            reasoning_effort=None,
            granted_authority="none",
            temp_root=tmp_path,
        )

    with pytest.raises(lifecycle.ExecutionLifecycleError, match="outside the policy route"):
        lifecycle.allocate_execution(
            "root-thread",
            unit_id="U1",
            execution_id="exec-2",
            native_task_name="sd_u1_a1",
            role_id="product_manager",
            reasoning_effort="xhigh",
            granted_authority="none",
            temp_root=tmp_path,
        )


def test_department_director_can_never_receive_mutation_authority(tmp_path: Path):
    state = load_module("gpt6_binding_state_director", "dispatch_state_v4.py")
    lifecycle = load_module("gpt6_binding_lifecycle_director", "execution_lifecycle_v4.py")
    install_unit(state, tmp_path, writable=True)

    with pytest.raises(lifecycle.ExecutionLifecycleError, match="Department Director.*read-only"):
        lifecycle.allocate_execution(
            "root-thread",
            unit_id="U1",
            execution_id="exec-1",
            native_task_name="sd_u1_a1",
            role_id="department_director",
            reasoning_effort="high",
            granted_authority="bounded-source-write",
            granted_write_scope=["src/a.py"],
            writer_lease_id="lease-1",
            temp_root=tmp_path,
        )


def test_old_profile_id_state_is_rejected_as_unsupported_schema(tmp_path: Path):
    state = load_module("gpt6_binding_state_old", "dispatch_state_v4.py")
    payload = state.new_state(thread_id="root-thread")
    payload["work_units"] = [work_unit(writable=False)]
    payload["work_units"][0]["state"] = "EXECUTING"
    payload["executions"] = [
        {
            "execution_id": "exec-1",
            "unit_id": "U1",
            "attempt_no": 1,
            "profile_id": "reader",
            "agent_id": None,
            "native_task_name": "sd_u1_a1",
            "model": "gpt-5.6-luna",
            "effort": "max",
            "granted_authority": "none",
            "granted_write_scope": [],
            "workspace_id": "canonical",
            "lifecycle": "SPAWN_PENDING",
            "control_epoch": 0,
            "followup_count": 0,
            "failure_origin": "none",
            "blocker": "none",
            "quarantine_reason": None,
            "execution_basis_ref": "initial:exec-1",
        }
    ]
    old = copy.deepcopy(payload)
    old["schema_version"] = "4.0"
    with pytest.raises(state.StatePayloadError, match="unsupported.*schema_version"):
        state.validate_state_payload(old, thread_id="root-thread")
