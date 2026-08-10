import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "dispatch_state.py"


def load_module():
    spec = importlib.util.spec_from_file_location("dispatch_state_compact_schema", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def unit():
    return {
        "unit_id": "U1",
        "task_id": "task-1",
        "attempt": 1,
        "native_task_name": "sd-u1-a1-execute",
        "agent_id": None,
        "role": "worker",
        "model_lane": "Luna Max",
        "responsibility": {
            "outcome": "change one owned file",
            "intent": "implement",
            "acceptance": "focused test passes",
        },
        "authority": {
            "write_scope": ["owned.py"],
            "mutation_authority": "bounded-source-write",
            "decision_rights": ["local implementation mechanics"],
        },
        "writer": True,
        "control_state": "SPAWN_PENDING",
        "adopted": False,
        "accepted": False,
        "failure_origin": "none",
        "blocker": "none",
        "quarantine_reason": None,
    }


def state_with_unit(module):
    state = module.new_state(thread_id="thread-1", locale="en")
    state["units"] = [unit()]
    return state


def test_compact_snapshot_accepts_only_existing_router_and_authority_shape():
    module = load_module()
    state = state_with_unit(module)
    state["team_plan_revision"] = 2
    state["pending_takeover"] = {"unit_id": "U1", "status": "pending"}
    assert module.validate_state_payload(state) == state


@pytest.mark.parametrize(
    "field,value,message",
    [
        ("team_plan_revision", 0, "positive integer"),
        ("team_plan_revision", True, "positive integer"),
        ("controls", [{"action": "Status"}], "must remain empty"),
        ("pending_takeover", {"unit_id": "U9", "status": "pending"}, "existing unit"),
        ("pending_takeover", {"unit_id": "U1", "status": "done"}, "status=pending"),
        (
            "pending_takeover",
            {"unit_id": "U1", "status": "pending", "note": "free-form"},
            "exactly unit_id and status",
        ),
    ],
)
def test_top_level_compact_metadata_rejects_unowned_or_malformed_state(field, value, message):
    module = load_module()
    state = state_with_unit(module)
    state[field] = value
    with pytest.raises(module.StatePayloadError, match=message):
        module.validate_state_payload(state)


def test_responsibility_rejects_free_form_or_invalid_intent():
    module = load_module()
    state = state_with_unit(module)
    state["units"][0]["responsibility"]["task_description"] = "copy arbitrary task text"
    with pytest.raises(module.StatePayloadError, match="responsibility has unsupported fields"):
        module.validate_state_payload(state)

    state = state_with_unit(module)
    state["units"][0]["responsibility"]["intent"] = "deploy"
    with pytest.raises(module.StatePayloadError, match="invalid intent"):
        module.validate_state_payload(state)


def test_authority_rejects_free_form_fields_and_invalid_values():
    module = load_module()
    state = state_with_unit(module)
    state["units"][0]["authority"]["notes"] = "arbitrary authority prose"
    with pytest.raises(module.StatePayloadError, match="authority has unsupported fields"):
        module.validate_state_payload(state)

    state = state_with_unit(module)
    state["units"][0]["authority"]["mutation_authority"] = "unbounded"
    with pytest.raises(module.StatePayloadError, match="invalid mutation_authority"):
        module.validate_state_payload(state)

    state = state_with_unit(module)
    state["units"][0]["authority"]["write_scope"] = [""]
    with pytest.raises(module.StatePayloadError, match="array of non-empty strings"):
        module.validate_state_payload(state)


def test_receipt_summary_has_no_unreachable_generic_recovery_channel():
    module = load_module()
    summary = module.account_receipt([])
    assert "recoveries" not in summary
    forged = {
        **summary,
        "zero_child": False,
        "dispatch": [{"model_lane": None, "activity": "read", "count": 1}],
        "recoveries": 3,
    }
    rendered = module.format_receipt(forged, locale="en")
    assert "recovery×" not in rendered
