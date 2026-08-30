from __future__ import annotations

import importlib.util
import json
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


def raw_host_evidence(*, capacity: int | None = 4) -> dict:
    return {
        "surface": "multi_agent_v2",
        "tools": ["spawn_agent", "followup_task", "interrupt_agent", "list_agents", "wait_agent"],
        "fork_turns_none": True,
        "managed_child_containment": "verified",
        "max_concurrent_threads_per_session": capacity,
    }


def work_unit(unit_id: str, *, state_name: str = "READY", writable: bool = False) -> dict:
    scope = [f"src/{unit_id.lower()}.py"] if writable else []
    return {
        "unit_id": unit_id,
        "intent": "implement" if writable else "inspect",
        "goal": f"work {unit_id}",
        "output": "verified result",
        "depends_on": [],
        "state": state_name,
        "ownership": {"write": scope, "forbidden": []},
        "authority_ceiling": "bounded-source-write" if writable else "none",
        "write_scope_ceiling": scope,
        "done_when": "Main verifies result",
        "accepted_result_ref": None,
        "accepted_execution_id": None,
        "accepted_control_epoch": None,
    }


def test_execution_binding_rejects_host_invalid_native_task_name():
    state = load_module("native_name_state", "dispatch_state_v4.py")
    payload = state.new_state(thread_id="thread-native-name")
    payload["work_units"] = [work_unit("U1", state_name="EXECUTING")]
    payload["executions"] = [
        {
            "execution_id": "exec_1",
            "unit_id": "U1",
            "attempt_no": 1,
            "profile_id": "reader",
            "agent_id": "agent-exec-1",
            "native_task_name": "sd-u1-a1",
            "model": "gpt-5.6-luna",
            "effort": "max",
            "granted_authority": "none",
            "granted_write_scope": [],
            "workspace_id": "canonical",
            "lifecycle": "RUNNING",
            "control_epoch": 0,
            "followup_count": 0,
            "failure_origin": "none",
            "blocker": "none",
            "quarantine_reason": None,
        }
    ]
    with pytest.raises(state.StatePayloadError, match="native_task_name|agent name|Host"):
        state.validate_state_payload(payload)


@pytest.mark.parametrize("bad_name", ["sd-u1-a1", "BadName", "root", "a/b", " a "])
def test_allocate_execution_rejects_host_invalid_task_names(tmp_path: Path, bad_name: str):
    state = load_module(f"native_allocate_state_{bad_name!r}", "dispatch_state_v4.py")
    lifecycle = load_module(f"native_allocate_lifecycle_{bad_name!r}", "execution_lifecycle_v4.py")
    payload = state.new_state(thread_id="thread-native-allocate")
    payload["work_units"] = [work_unit("U1")]
    state.write_state(payload, temp_root=tmp_path)

    with pytest.raises(Exception, match="native_task_name|agent name|Host"):
        lifecycle.allocate_execution(
            "thread-native-allocate",
            unit_id="U1",
            execution_id="exec_1",
            native_task_name=bad_name,
            profile_id="reader",
            granted_authority="none",
            temp_root=tmp_path,
        )


def test_known_host_session_capacity_is_advisory_scheduler_ceiling():
    state = load_module("native_capacity_state", "dispatch_state_v4.py")
    host = load_module("native_capacity_host", "host_capabilities.py")
    scheduler = load_module("native_capacity_scheduler", "scheduler_v4.py")

    payload = state.new_state(thread_id="thread-native-capacity")
    payload["work_units"] = [work_unit("U1"), work_unit("U2"), work_unit("U3")]
    snapshot = host.normalize_host_capabilities(raw_host_evidence(capacity=2))

    decision = scheduler.constraint_snapshot(payload, capability_snapshot=snapshot, wakeup_reason="USER_INPUT")

    assert decision["selection_owner"] == "main"
    assert decision["host_session_capacity"] == 2
    assert decision["product_child_limit"] == 4
    assert decision["available_launch_slots"] == 1
    assert decision["launch_budget"] == 1
    assert decision["actions"] == []


def test_unknown_host_capacity_allows_bounded_product_admission():
    state = load_module("native_unknown_capacity_state", "dispatch_state_v4.py")
    host = load_module("native_unknown_capacity_host", "host_capabilities.py")
    scheduler = load_module("native_unknown_capacity_scheduler", "scheduler_v4.py")

    payload = state.new_state(thread_id="thread-native-unknown-capacity")
    payload["work_units"] = [work_unit("U1"), work_unit("U2"), work_unit("U3")]
    snapshot = host.normalize_host_capabilities(raw_host_evidence(capacity=None))

    decision = scheduler.constraint_snapshot(payload, capability_snapshot=snapshot, wakeup_reason="USER_INPUT")

    assert decision["selection_owner"] == "main"
    assert decision["host_session_capacity"] is None
    assert decision["host_ready"] is True
    assert decision["product_child_limit"] == 4
    assert decision["available_launch_slots"] == 4
    assert decision["launch_budget"] == 4
    assert decision["actions"] == []


def test_scheduler_rejects_caller_shaped_inconsistent_normalized_snapshot():
    state = load_module("native_snapshot_state", "dispatch_state_v4.py")
    scheduler = load_module("native_snapshot_scheduler", "scheduler_v4.py")
    payload = state.new_state(thread_id="thread-native-snapshot")
    payload["work_units"] = [work_unit("U1")]
    forged = {
        "surface": "multi_agent_v2",
        "capabilities": {
            "spawn": True,
            "observe": True,
            "wait_or_wakeup": True,
            "followup": True,
            "interrupt": True,
            "unknown_capability": True,
        },
        "fork_turns_none": True,
        "max_concurrent_threads_per_session": 4,
        "capacity_includes_primary": True,
        "execution_ready": True,
        "missing": [],
    }
    with pytest.raises(scheduler.SchedulerError, match="normalized|capability set"):
        scheduler.constraint_snapshot(payload, capability_snapshot=forged, wakeup_reason="USER_INPUT")


def test_release_identity_binds_native_host_contract_digest():
    release = load_module("native_release_contract", "release_evidence_v4.py")
    identity = release.current_candidate_identity(ROOT)

    assert release.HOST_CAMPAIGN_CONTRACT_VERSION == "4.0.0-native-host-smoke-2"
    assert release.REQUIRED_HOST_PROBES == tuple(f"N{index}" for index in range(8))
    assert "host_contract_sha256" in identity
    assert len(identity["host_contract_sha256"]) == 64


def test_machine_host_contract_is_native_core_n0_n7():
    contract = json.loads((ROOT / "docs" / "v4" / "host-smoke.json").read_text(encoding="utf-8"))

    assert contract["gate_id"] == "v4-real-host-n0-n7"
    assert [probe["id"] for probe in contract["required_probes"]] == [f"N{index}" for index in range(8)]
    assert "activation_manifest" not in contract
    assert "production_manifest" not in contract


def test_n1_oracle_targets_actual_managed_delegation_depth():
    contract = json.loads((ROOT / "docs" / "v4" / "host-smoke.json").read_text(encoding="utf-8"))
    n1 = next(probe for probe in contract["required_probes"] if probe["id"] == "N1")

    assert n1["operation"] == "managed delegation depth"
    assert "accepted_grandchild_outcomes" not in n1
    assert any("canonical managed spawn route" in item for item in n1["requires"])
    assert any("every fixed managed profile" in item for item in n1["requires"])
    assert any("adversarial untrusted-input" in item for item in n1["requires"])
    assert any("does not issue spawn_agent" in item for item in n1["requires"])
    assert any("no descendant identity" in item and "spawn-edge" in item for item in n1["requires"])
    assert any("is FAIL" in item and "descendant materialization" in item for item in n1["requires"])
    assert any("is UNKNOWN" in item for item in n1["requires"])
    assert any("generic V2 recursive-capability probes" in item for item in n1["requires"])
    assert any("do not prove Host-hard descendant isolation" in item for item in n1["requires"])


def test_architecture_hardens_current_v2_identity_capacity_and_steer_contract():
    architecture = json.loads((ROOT / "docs" / "v4" / "architecture.json").read_text(encoding="utf-8"))

    identity = architecture["identity_binding"]
    assert identity["canonical_native_task_address_field"] == "native_task_name"
    assert identity["host_thread_identity_field"] == "agent_id"
    assert identity["spawn_result_binds_canonical_task_address"] is True
    assert identity["host_activity_binds_thread_identity"] is True
    assert identity["task_address_is_not_thread_identity"] is True
    assert identity["durable_child_identity_owner"] == "codex_host"
    assert identity["resident_runtime_owner"] == "codex_host"
    assert identity["release_campaign_requires_thread_identity_binding"] is True
    assert identity["runtime_agent_id_persistence_required"] is False
    assert identity["runtime_control_address_when_agent_id_unavailable"] == "native_task_name"

    steer = architecture["control_semantics"]["STEER"]
    assert steer["v2_host_tool"] == "followup_task"
    assert steer["requires_running_execution"] is True
    assert steer["preserves_execution_binding"] is True
    assert steer["replacement_child_forbidden"] is True
    assert steer["requires_post_guidance_same_child_evidence"] is True

    scheduler = architecture["scheduler"]
    assert scheduler["host_capacity_public_config_key"] == "agents.max_concurrent_threads_per_session"
    assert scheduler["host_capacity_public_config_includes_primary"] is False
    assert scheduler["host_capacity_normalization"] == "public_spawned_agent_limit_plus_primary"
    assert scheduler["host_capacity_semantics"] == "session_concurrency_includes_primary"
    assert scheduler["host_capacity_internal_v2_semantics"] == "root_inclusive_internal_v2_session_limit"
    assert scheduler["host_capacity_requires_runtime_binding"] is True
    assert scheduler["host_rejection_cause_may_be_ambiguous"] is True

    assert architecture["delegation"]["max_depth"] == 1
    assert architecture["delegation"]["max_depth_scope"] == "project_policy"
    assert architecture["delegation"]["max_depth_is_v2_host_containment_proof"] is False
    assert "host_evidence_for_managed_no_descendant_behavior" in architecture["managed_profile_requirements"]
    assert "host_evidence_for_effective_child_containment" not in architecture["managed_profile_requirements"]
    assert "managed children must not create or control descendants" in architecture["invariants"]["I08"]


def test_host_campaign_hardens_n2_n3_n4_oracles():
    contract = json.loads((ROOT / "docs" / "v4" / "host-smoke.json").read_text(encoding="utf-8"))
    probes = {probe["id"]: probe for probe in contract["required_probes"]}

    n2 = probes["N2"]
    assert "task-address and Host-thread identity evidence" in n2["operation"]
    assert any("canonical native task address" in item for item in n2["requires"])
    assert any("underlying child thread identity" in item for item in n2["requires"])
    assert any("external release evidence" in item for item in n2["requires"])
    assert any("ordinary runtime reconciliation" in item and "omits agent_id" in item for item in n2["requires"])

    n3 = probes["N3"]
    assert n3["operation"] == "Host admission rejection materialization safety"
    assert any("root-inclusive internal V2 session limit" in item for item in n3["requires"])
    assert any("residency pressure" in item for item in n3["requires"])
    assert any("Started activity" in item and "durable child identity" in item for item in n3["requires"])
    assert any("UNKNOWN" in item for item in n3["requires"])

    n4 = probes["N4"]
    assert n4["operation"] == "same-child steering, correction, and continuation"
    assert n4["v2_running_steer_tool"] == "followup_task"
    assert any("RUNNING Steer" in item and "followup_task" in item for item in n4["requires"])
    assert any("same child" in item and "consumed" in item for item in n4["requires"])
    assert any("tool-call acceptance alone is insufficient" in item for item in n4["requires"])
    assert any("attempt_no, control_epoch, and followup_count" in item for item in n4["requires"])
