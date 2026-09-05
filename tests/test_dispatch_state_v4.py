from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
MODULE_PATH = SCRIPTS / "dispatch_state_v4.py"


def load_module(name: str, path: Path):
    scripts = str(SCRIPTS)
    sys.path.insert(0, scripts)
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts)


def work_unit(
    *,
    unit_id: str = "U1",
    state: str = "EXECUTING",
    depends_on: list[str] | None = None,
    authority: str = "bounded-source-write",
) -> dict:
    write_scope = ["src/owned.py"] if authority != "none" else []
    return {
        "unit_id": unit_id,
        "intent": "implement" if authority != "none" else "inspect",
        "goal": "complete one stable responsibility",
        "output": "bounded verified result",
        "depends_on": depends_on or [],
        "state": state,
        "ownership": {"write": write_scope, "forbidden": []},
        "authority_ceiling": authority,
        "write_scope_ceiling": write_scope,
        "done_when": "Main can verify the bounded result",
        "accepted_result_ref": None,
        "accepted_execution_id": None,
        "accepted_control_epoch": None,
    }


def execution(
    *,
    execution_id: str = "exec-1",
    unit_id: str = "U1",
    lifecycle: str = "RUNNING",
    agent_id: str | None = "agent-1",
    control_epoch: int = 0,
    role_id: str = "programmer",
    reasoning_effort: str | None = None,
    granted_authority: str | None = None,
) -> dict:
    routes = {
        "programmer": ("subagents_dispatch_programmer", "gpt-5.6-luna", "max"),
        "product_manager": ("subagents_dispatch_product_manager", "gpt-5.6-sol", "medium"),
        "department_director": ("subagents_dispatch_department_director", "gpt-6-astra", "high"),
    }
    agent_type, model, default_effort = routes[role_id]
    effort = reasoning_effort or default_effort
    authority = granted_authority
    if authority is None:
        authority = "bounded-source-write" if role_id == "programmer" else "none"
    return {
        "execution_id": execution_id,
        "unit_id": unit_id,
        "attempt_no": 1,
        "role_id": role_id,
        "agent_type": agent_type,
        "agent_id": agent_id,
        "native_task_name": f"sd_{unit_id.lower()}_a1",
        "model": model,
        "reasoning_effort": effort,
        "granted_authority": authority,
        "granted_write_scope": ["src/owned.py"] if authority != "none" else [],
        "workspace_id": "canonical",
        "lifecycle": lifecycle,
        "control_epoch": control_epoch,
        "followup_count": 0,
        "failure_origin": "none",
        "blocker": "none",
        "quarantine_reason": None,
    }


def populated_state(module, *, control_epoch: int = 0, writer: bool = False) -> dict:
    state = module.new_state(thread_id="thread-1", locale="en")
    state["work_units"] = [work_unit()]
    state["executions"] = [execution(control_epoch=control_epoch)]
    if writer:
        state["writer_lease"] = {
            "lease_id": "lease-1",
            "lease_epoch": 4,
            "workspace_id": "canonical",
            "unit_id": "U1",
            "owner_kind": "execution",
            "owner_id": "exec-1",
            "state": "HELD",
        }
    module.validate_state_payload(state)
    return state


def test_new_v4_state_has_exact_bounded_top_level_shape():
    module = load_module("dispatch_state_v4_new", MODULE_PATH)
    state = module.new_state(thread_id="thread-1", locale="zh", now="2026-08-17T00:00:00Z")

    assert state == {
        "schema_version": "4.1",
        "root_session_id": "thread-1",
        "state_revision": 0,
        "work_units": [],
        "executions": [],
        "writer_lease": None,
        "accounting_refs": [],
        "created_at": "2026-08-17T00:00:00Z",
        "updated_at": "2026-08-17T00:00:00Z",
        "locale": "zh",
    }
    assert module.validate_state_payload(state) == state


def test_v4_state_rejects_extra_fields_and_v3_schema():
    module = load_module("dispatch_state_v4_shape", MODULE_PATH)
    state = module.new_state(thread_id="thread-1")
    state["raw_transcript"] = "forbidden"
    with pytest.raises(module.StatePayloadError, match="unsupported fields"):
        module.validate_state_payload(state)

    state = module.new_state(thread_id="thread-1")
    state["schema_version"] = "1.0"
    with pytest.raises(module.StatePayloadError, match="schema_version"):
        module.validate_state_payload(state)


def test_retired_team_plan_fields_are_rejected():
    module = load_module("dispatch_state_v4_no_team_plan", MODULE_PATH)
    state = module.new_state(thread_id="thread-1")
    state["team_plan_revision"] = 1
    with pytest.raises(module.StatePayloadError, match="unsupported fields: team_plan_revision"):
        module.validate_state_payload(state)

    state = module.new_state(thread_id="thread-1")
    state["work_units"] = [work_unit()]
    record = execution()
    record["team_plan_revision"] = 1
    state["executions"] = [record]
    with pytest.raises(module.StatePayloadError, match="unsupported fields: team_plan_revision"):
        module.validate_state_payload(state)


def test_work_graph_requires_safe_acyclic_dependencies_and_closed_ownership():
    module = load_module("dispatch_state_v4_graph", MODULE_PATH)
    state = module.new_state(thread_id="thread-1")
    state["work_units"] = [
        work_unit(unit_id="U1", depends_on=["U2"]),
        work_unit(unit_id="U2", depends_on=["U1"]),
    ]
    with pytest.raises(module.StatePayloadError, match="acyclic"):
        module.validate_state_payload(state)

    state = module.new_state(thread_id="thread-1")
    bad = work_unit()
    bad["ownership"]["write"] = ["../escape.py"]
    bad["write_scope_ceiling"] = ["../escape.py"]
    state["work_units"] = [bad]
    with pytest.raises(module.StatePayloadError, match="safe relative path"):
        module.validate_state_payload(state)


def test_execution_is_pinned_to_exact_role_route_and_work_unit_authority_ceiling():
    module = load_module("dispatch_state_v4_profiles", MODULE_PATH)
    state = populated_state(module)

    state["executions"][0]["reasoning_effort"] = "high"
    with pytest.raises(module.StatePayloadError, match="managed route"):
        module.validate_state_payload(state)

    state = populated_state(module)
    state["work_units"][0]["authority_ceiling"] = "none"
    state["work_units"][0]["write_scope_ceiling"] = []
    state["work_units"][0]["ownership"]["write"] = []
    with pytest.raises(module.StatePayloadError, match="authority ceiling"):
        module.validate_state_payload(state)


def test_v2_native_task_name_is_sufficient_when_agent_id_is_unavailable():
    module = load_module("dispatch_state_v4_v2_identity", MODULE_PATH)
    state = module.new_state(thread_id="thread-1")
    state["work_units"] = [work_unit()]
    state["executions"] = [execution(agent_id=None, lifecycle="RUNNING")]

    assert module.validate_state_payload(state) == state
    assert state["executions"][0]["native_task_name"] == "sd_u1_a1"


def test_department_director_cannot_claim_write_authority():
    module = load_module("dispatch_state_v4_readonly", MODULE_PATH)
    state = module.new_state(thread_id="thread-1")
    state["work_units"] = [work_unit(authority="bounded-source-write")]
    record = execution(role_id="department_director", granted_authority="bounded-source-write")
    record["granted_authority"] = "bounded-source-write"
    record["granted_write_scope"] = ["src/owned.py"]
    state["executions"] = [record]

    with pytest.raises(module.StatePayloadError, match="Department Director must be read-only"):
        module.validate_state_payload(state)


def test_writer_lease_owner_is_bound_to_main_or_matching_execution():
    module = load_module("dispatch_state_v4_lease", MODULE_PATH)
    state = populated_state(module, writer=True)
    assert module.validate_state_payload(state) == state

    state["writer_lease"]["owner_id"] = "exec-other"
    with pytest.raises(module.StatePayloadError, match="matching ExecutionBinding"):
        module.validate_state_payload(state)

    state = populated_state(module)
    state["writer_lease"] = {
        "lease_id": "lease-main",
        "lease_epoch": 1,
        "workspace_id": "canonical",
        "unit_id": "U1",
        "owner_kind": "main",
        "owner_id": "thread-1",
        "state": "RESERVED",
    }
    assert module.validate_state_payload(state) == state


def test_retired_pending_control_field_is_rejected():
    module = load_module("dispatch_state_v4_no_controls", MODULE_PATH)
    state = populated_state(module)
    state["pending_controls"] = []

    with pytest.raises(module.StatePayloadError, match="unsupported fields: pending_controls"):
        module.validate_state_payload(state)


def test_invalid_failed_failure_origin_is_rejected_without_coercion():
    module = load_module("dispatch_state_v4_failure_origin", MODULE_PATH)
    state = populated_state(module)
    basis = module.observation_basis(state, execution_id="exec-1")

    with pytest.raises(module.StatePayloadError, match="valid failure_origin"):
        module.reconcile_execution_observation(
            state,
            basis=basis,
            host_state="errored",
            failure_origin="made_up_failure",
        )
    assert state["executions"][0]["lifecycle"] == "RUNNING"
    assert state["executions"][0]["failure_origin"] == "none"


def test_managed_child_ceiling_is_rejected_inside_atomic_mutation(tmp_path: Path):
    module = load_module("dispatch_state_v4_child_ceiling", MODULE_PATH)
    state = module.new_state(thread_id="thread-1", now="2026-08-17T00:00:00Z")
    state["work_units"] = [
        work_unit(unit_id=f"U{index}", authority="none") for index in range(1, 5)
    ]
    state["executions"] = [
        execution(
            execution_id=f"exec-{index}",
            unit_id=f"U{index}",
            role_id="programmer", reasoning_effort="max",
            granted_authority="none",
            agent_id=f"agent-{index}",
        )
        for index in range(1, 5)
    ]
    module.write_state(state, temp_root=tmp_path)
    before = module.load_state("thread-1", temp_root=tmp_path)
    assert before is not None

    def add_fifth(current: dict) -> None:
        current["work_units"].append(work_unit(unit_id="U5", authority="none"))
        current["executions"].append(
            execution(
                execution_id="exec-5",
                unit_id="U5",
                role_id="programmer", reasoning_effort="max",
                granted_authority="none",
                agent_id="agent-5",
            )
        )

    with pytest.raises(module.StatePayloadError, match="managed child limit"):
        module.mutate_state("thread-1", add_fifth, temp_root=tmp_path)

    assert module.load_state("thread-1", temp_root=tmp_path) == before


def test_state_revision_cas_and_atomic_persistence(tmp_path: Path):
    module = load_module("dispatch_state_v4_mutation", MODULE_PATH)
    state = module.new_state(thread_id="thread-1", now="2026-08-17T00:00:00Z")
    path = module.write_state(state, temp_root=tmp_path)
    assert module.load_state("thread-1", temp_root=tmp_path) == state

    updated = module.mutate_state(
        "thread-1",
        lambda current: current["work_units"].append(work_unit(authority="none")),
        expected_state_revision=0,
        temp_root=tmp_path,
        now="2026-08-17T00:01:00Z",
    )
    assert updated["state_revision"] == 1
    assert path == module.state_path("thread-1", temp_root=tmp_path)
    assert module.load_state("thread-1", temp_root=tmp_path) == updated

    with pytest.raises(module.StatePayloadError, match="compare-and-swap"):
        module.mutate_state(
            "thread-1",
            lambda current: None,
            expected_state_revision=0,
            temp_root=tmp_path,
        )


def test_v4_loader_fails_closed_on_pre_current_live_state(tmp_path: Path):
    v4 = load_module("dispatch_state_v4_pre_current", MODULE_PATH)
    legacy_path = v4.state_path("thread-1", temp_root=tmp_path)
    legacy_path.parent.mkdir(parents=True, mode=0o700)
    legacy_path.write_text(
        '{"schema_version":"1.0","root_thread_id":"thread-1","units":[]}',
        encoding="utf-8",
    )
    legacy_path.chmod(0o600)

    with pytest.raises(v4.StateCorruptError, match="unsupported fields|schema_version"):
        v4.load_state("thread-1", temp_root=tmp_path)


def test_stale_observation_is_discarded_without_state_or_lease_change():
    module = load_module("dispatch_state_v4_stale", MODULE_PATH)
    state = populated_state(module, control_epoch=2, writer=True)
    basis = module.observation_basis(state, execution_id="exec-1")

    newer = copy.deepcopy(state)
    newer["executions"][0]["control_epoch"] = 3
    result = module.reconcile_execution_observation(
        newer,
        basis=basis,
        host_state="completed",
        agent_id="agent-1",
    )

    assert result["reconcile_status"] == "stale"
    assert result["state"] == newer
    assert result["state"]["writer_lease"]["state"] == "HELD"


def test_host_completed_produces_result_ready_without_acceptance_or_writer_release():
    module = load_module("dispatch_state_v4_completed", MODULE_PATH)
    state = populated_state(module, writer=True)
    basis = module.observation_basis(state, execution_id="exec-1")

    result = module.reconcile_execution_observation(
        state,
        basis=basis,
        host_state="completed",
        agent_id="agent-1",
        now="2026-08-17T00:01:00Z",
    )
    reconciled = result["state"]

    assert result["reconcile_status"] == "applied"
    assert reconciled["executions"][0]["lifecycle"] == "COMPLETED"
    assert reconciled["work_units"][0]["state"] == "RESULT_READY"
    assert reconciled["work_units"][0]["accepted_result_ref"] is None
    assert reconciled["writer_lease"]["state"] == "HELD"
    assert reconciled["state_revision"] == state["state_revision"] + 1


def test_duplicate_host_observation_is_idempotent_and_does_not_advance_revision():
    module = load_module("dispatch_state_v4_duplicate", MODULE_PATH)
    state = populated_state(module, writer=True)
    basis = module.observation_basis(state, execution_id="exec-1")

    first = module.reconcile_execution_observation(
        state,
        basis=basis,
        host_state="completed",
        agent_id="agent-1",
        now="2026-08-17T00:01:00Z",
    )
    second = module.reconcile_execution_observation(
        first["state"],
        basis=basis,
        host_state="completed",
        agent_id="agent-1",
        now="2026-08-17T00:02:00Z",
    )

    assert first["reconcile_status"] == "applied"
    assert second["reconcile_status"] == "noop"
    assert second["state"] == first["state"]


def test_completed_observation_does_not_regress_work_unit_verification_or_rejection():
    module = load_module("dispatch_state_v4_nonregression", MODULE_PATH)

    for state_name in ("VERIFYING", "REJECTED"):
        state = populated_state(module)
        state["work_units"][0]["state"] = state_name
        basis = module.observation_basis(state, execution_id="exec-1")
        result = module.reconcile_execution_observation(
            state,
            basis=basis,
            host_state="completed",
            agent_id="agent-1",
        )
        assert result["state"]["work_units"][0]["state"] == state_name


def test_interrupt_observation_never_releases_writer_lease():
    module = load_module("dispatch_state_v4_interrupted", MODULE_PATH)
    state = populated_state(module, writer=True)
    basis = module.observation_basis(state, execution_id="exec-1")

    result = module.reconcile_execution_observation(
        state,
        basis=basis,
        host_state="interrupted",
        agent_id="agent-1",
    )

    assert result["state"]["executions"][0]["lifecycle"] == "INTERRUPTED"
    assert result["state"]["writer_lease"]["state"] == "HELD"


def test_unknown_host_identity_quarantines_execution_and_preserves_writer_block():
    module = load_module("dispatch_state_v4_unknown", MODULE_PATH)
    state = populated_state(module, writer=True)
    basis = module.observation_basis(state, execution_id="exec-1")

    result = module.reconcile_execution_observation(
        state,
        basis=basis,
        host_state="not_found",
    )

    execution_record = result["state"]["executions"][0]
    assert execution_record["lifecycle"] == "UNKNOWN"
    assert execution_record["failure_origin"] == "runtime_ambiguous"
    assert result["state"]["writer_lease"]["state"] == "HELD"
