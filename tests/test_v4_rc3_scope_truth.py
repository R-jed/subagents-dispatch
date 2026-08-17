from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load_state(name: str):
    scripts = str(SCRIPTS)
    sys.path.insert(0, scripts)
    try:
        spec = importlib.util.spec_from_file_location(name, SCRIPTS / "dispatch_state_v4.py")
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts)


def unit(*, write: list[str], forbidden: list[str], ceiling: list[str] | None = None) -> dict:
    return {
        "unit_id": "U1",
        "intent": "implement",
        "goal": "bounded write",
        "output": "patch",
        "depends_on": [],
        "state": "READY",
        "ownership": {"write": write, "forbidden": forbidden},
        "authority_ceiling": "bounded-source-write",
        "write_scope_ceiling": list(write if ceiling is None else ceiling),
        "done_when": "tests pass",
        "accepted_result_ref": None,
        "accepted_execution_id": None,
        "accepted_control_epoch": None,
    }


def payload(state, *, write: list[str], forbidden: list[str], ceiling: list[str] | None = None) -> dict:
    value = state.new_state(thread_id="thread-scope")
    value["team_plan_revision"] = 1
    value["work_units"] = [unit(write=write, forbidden=forbidden, ceiling=ceiling)]
    return value


def test_backslash_scope_is_rejected_as_noncanonical():
    state = load_state("rc3_scope_backslash")
    value = payload(state, write=["src\\secret.py"], forbidden=[])
    with pytest.raises(state.StatePayloadError, match="canonical|POSIX"):
        state.validate_state_payload(value)


def test_duplicate_separator_scope_is_rejected_as_noncanonical():
    state = load_state("rc3_scope_separator")
    value = payload(state, write=["src//secret.py"], forbidden=[])
    with pytest.raises(state.StatePayloadError, match="canonical|POSIX"):
        state.validate_state_payload(value)


def test_write_parent_cannot_overlap_forbidden_descendant():
    state = load_state("rc3_scope_parent_write")
    value = payload(state, write=["src"], forbidden=["src/secret.py"])
    with pytest.raises(state.StatePayloadError, match="overlap|ancestry"):
        state.validate_state_payload(value)


def test_forbidden_parent_cannot_overlap_write_descendant():
    state = load_state("rc3_scope_parent_forbidden")
    value = payload(state, write=["src/public.py"], forbidden=["src"])
    with pytest.raises(state.StatePayloadError, match="overlap|ancestry"):
        state.validate_state_payload(value)


def test_disjoint_canonical_scopes_are_valid():
    state = load_state("rc3_scope_disjoint")
    value = payload(
        state,
        write=["src/public.py"],
        forbidden=["secrets/private.py"],
    )
    assert state.validate_state_payload(value) == value


def test_execution_granted_scope_must_also_be_canonical():
    state = load_state("rc3_scope_execution")
    value = payload(state, write=["src/owned.py"], forbidden=[])
    value["work_units"][0]["state"] = "EXECUTING"
    value["executions"] = [
        {
            "execution_id": "exec-1",
            "unit_id": "U1",
            "team_plan_revision": 1,
            "attempt_no": 1,
            "profile_id": "worker",
            "agent_id": None,
            "native_task_name": "sd-u1-a1",
            "model": "gpt-5.6-luna",
            "effort": "max",
            "granted_authority": "bounded-source-write",
            "granted_write_scope": ["src\\owned.py"],
            "workspace_id": "canonical",
            "lifecycle": "SPAWN_PENDING",
            "control_epoch": 0,
            "followup_count": 0,
            "failure_origin": "none",
            "blocker": "none",
            "quarantine_reason": None,
        }
    ]
    with pytest.raises(state.StatePayloadError, match="canonical|POSIX"):
        state.validate_state_payload(value)
