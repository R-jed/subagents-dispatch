#!/usr/bin/env python3
from pathlib import Path

STATE = Path("scripts/dispatch_state.py")
STATE_DOC = Path("contracts/state.md")
STATE_TEST = Path("tests/test_dispatch_state.py")
COMPACT_TEST = Path("tests/test_dispatch_state_compact_schema.py")

text = STATE.read_text(encoding="utf-8")

old_constants = '''UNIT_FIELDS = {
    "unit_id",
    "task_id",
    "attempt",
    "native_task_name",
    "agent_id",
    "role",
    "model_lane",
    "responsibility",
    "authority",
    "writer",
    "control_state",
    "adopted",
    "accepted",
    "failure_origin",
    "blocker",
    "quarantine_reason",
}
CONTROL_STATES = {
'''
new_constants = '''UNIT_FIELDS = {
    "unit_id",
    "task_id",
    "attempt",
    "native_task_name",
    "agent_id",
    "role",
    "model_lane",
    "responsibility",
    "authority",
    "writer",
    "control_state",
    "adopted",
    "accepted",
    "failure_origin",
    "blocker",
    "quarantine_reason",
}
RESPONSIBILITY_FIELDS = {"outcome", "intent", "acceptance"}
RESPONSIBILITY_REQUIRED_FIELDS = {"outcome", "acceptance"}
AUTHORITY_FIELDS = {"write_scope", "mutation_authority", "decision_rights"}
AUTHORITY_REQUIRED_FIELDS = {"write_scope"}
RESPONSIBILITY_INTENTS = {"inspect", "implement", "verify", "review"}
MUTATION_AUTHORITIES = {"none", "declared-output-only", "bounded-source-write"}
PENDING_TAKEOVER_FIELDS = {"unit_id", "status"}
CONTROL_STATES = {
'''
if text.count(old_constants) != 1:
    raise SystemExit("expected unit constants block exactly once")
text = text.replace(old_constants, new_constants, 1)

old_validation = '''    if not isinstance(payload.get("controls"), list):
        raise StatePayloadError("controls must be an array")
    _validate_units(payload["units"])
    try:
'''
new_validation = '''    if not isinstance(payload.get("controls"), list):
        raise StatePayloadError("controls must be an array")
    _validate_units(payload["units"])
    _validate_compact_top_level(payload)
    try:
'''
if text.count(old_validation) != 1:
    raise SystemExit("expected top-level validation block exactly once")
text = text.replace(old_validation, new_validation, 1)

old_nonempty = '''def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_units(units: list[Any]) -> None:
'''
new_nonempty = '''def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_string_list(value: Any, *, label: str) -> None:
    if not isinstance(value, list) or not all(_nonempty(item) for item in value):
        raise StatePayloadError(f"{label} must be an array of non-empty strings")


def _validate_compact_responsibility(value: Any, *, prefix: str) -> None:
    if not isinstance(value, dict):
        raise StatePayloadError(f"{prefix} responsibility must be an object")
    extra = set(value) - RESPONSIBILITY_FIELDS
    missing = RESPONSIBILITY_REQUIRED_FIELDS - set(value)
    if extra:
        raise StatePayloadError(
            f"{prefix} responsibility has unsupported fields: {', '.join(sorted(extra))}"
        )
    if missing:
        raise StatePayloadError(
            f"{prefix} responsibility is missing fields: {', '.join(sorted(missing))}"
        )
    if not _nonempty(value.get("outcome")) or not _nonempty(value.get("acceptance")):
        raise StatePayloadError(f"{prefix} responsibility requires outcome and acceptance")
    intent = value.get("intent")
    if intent is not None and intent not in RESPONSIBILITY_INTENTS:
        raise StatePayloadError(f"{prefix} responsibility has invalid intent")


def _validate_compact_authority(value: Any, *, prefix: str) -> None:
    if not isinstance(value, dict):
        raise StatePayloadError(f"{prefix} authority must be an object")
    extra = set(value) - AUTHORITY_FIELDS
    missing = AUTHORITY_REQUIRED_FIELDS - set(value)
    if extra:
        raise StatePayloadError(
            f"{prefix} authority has unsupported fields: {', '.join(sorted(extra))}"
        )
    if missing:
        raise StatePayloadError(
            f"{prefix} authority is missing fields: {', '.join(sorted(missing))}"
        )
    _validate_string_list(value.get("write_scope"), label=f"{prefix} authority.write_scope")
    mutation_authority = value.get("mutation_authority")
    if mutation_authority is not None and mutation_authority not in MUTATION_AUTHORITIES:
        raise StatePayloadError(f"{prefix} authority has invalid mutation_authority")
    if "decision_rights" in value:
        _validate_string_list(
            value.get("decision_rights"), label=f"{prefix} authority.decision_rights"
        )


def _validate_compact_top_level(payload: Mapping[str, Any]) -> None:
    revision = payload.get("team_plan_revision")
    if revision is not None and (
        not isinstance(revision, int) or isinstance(revision, bool) or revision < 1
    ):
        raise StatePayloadError("team_plan_revision must be null or a positive integer")
    if payload.get("controls") != []:
        raise StatePayloadError(
            "controls is reserved and must remain empty; control accounting belongs in accounting_refs"
        )
    pending = payload.get("pending_takeover")
    if pending is None:
        return
    if not isinstance(pending, dict) or set(pending) != PENDING_TAKEOVER_FIELDS:
        raise StatePayloadError("pending_takeover must contain exactly unit_id and status")
    if not _nonempty(pending.get("unit_id")) or pending.get("status") != "pending":
        raise StatePayloadError("pending_takeover requires a unit_id and status=pending")
    unit_ids = {record.get("unit_id") for record in payload.get("units", [])}
    if pending["unit_id"] not in unit_ids:
        raise StatePayloadError("pending_takeover must reference an existing unit")


def _validate_units(units: list[Any]) -> None:
'''
if text.count(old_nonempty) != 1:
    raise SystemExit("expected _nonempty block exactly once")
text = text.replace(old_nonempty, new_nonempty, 1)

old_unit_objects = '''        if not isinstance(record["responsibility"], dict) or not isinstance(record["authority"], dict):
            raise StatePayloadError(f"{prefix} requires compact responsibility and authority objects")
        for field in ("writer", "adopted", "accepted"):
'''
new_unit_objects = '''        _validate_compact_responsibility(record["responsibility"], prefix=prefix)
        _validate_compact_authority(record["authority"], prefix=prefix)
        for field in ("writer", "adopted", "accepted"):
'''
if text.count(old_unit_objects) != 1:
    raise SystemExit("expected unit responsibility/authority block exactly once")
text = text.replace(old_unit_objects, new_unit_objects, 1)

old_recoveries = '''    review_rounds = 0
    review_verdict: str | None = None
    recoveries = 0

    materialized_keys = (
'''
new_recoveries = '''    review_rounds = 0
    review_verdict: str | None = None

    materialized_keys = (
'''
if text.count(old_recoveries) != 1:
    raise SystemExit("expected dead recoveries variable exactly once")
text = text.replace(old_recoveries, new_recoveries, 1)

old_return = '''        "review": {
            "rounds": review_rounds,
            "reworks": semantic_reworks,
            "verdict": review_verdict,
        },
        "recoveries": recoveries,
        "zero_child": not dispatch,
'''
new_return = '''        "review": {
            "rounds": review_rounds,
            "reworks": semantic_reworks,
            "verdict": review_verdict,
        },
        "zero_child": not dispatch,
'''
if text.count(old_return) != 1:
    raise SystemExit("expected dead recoveries return exactly once")
text = text.replace(old_return, new_return, 1)

old_formatter = '''    recovery_parts = []
    if summary.get("retries"):
        recovery_parts.append(
            f"重试{summary['retries']}次" if locale == "zh" else f"retry×{summary['retries']}"
        )
    if summary.get("recoveries"):
        recovery_parts.append(
            f"恢复{summary['recoveries']}次"
            if locale == "zh"
            else f"recovery×{summary['recoveries']}"
        )
    if recovery_parts:
        lines.append(("恢复: " if locale == "zh" else "Recovery: ") + " · ".join(recovery_parts))
'''
new_formatter = '''    if summary.get("retries"):
        retry_text = (
            f"重试{summary['retries']}次"
            if locale == "zh"
            else f"retry×{summary['retries']}"
        )
        lines.append(("恢复: " if locale == "zh" else "Recovery: ") + retry_text)
'''
if text.count(old_formatter) != 1:
    raise SystemExit("expected dead generic recovery formatter exactly once")
text = text.replace(old_formatter, new_formatter, 1)
STATE.write_text(text, encoding="utf-8")

state_doc = STATE_DOC.read_text(encoding="utf-8")
old_doc = '''For a single delegated responsibility without TeamPlan, the compact responsibility snapshot may contain only the semantic fields required to identify the work safely, such as unit id, outcome, intent, delegated role, bounded write scope, and acceptance. For a multi-unit orchestration, TeamPlan remains the canonical structural truth; the capsule stores only the revision binding and the compact active-unit index needed for runtime continuity. It does not duplicate the full plan or recovery ledger by default.

Do not persist raw user prompts, child transcripts, private reasoning, source-file contents, web pages, full tool output, credentials, secrets, or a duplicate evidence corpus.
'''
new_doc = '''For a single delegated responsibility without TeamPlan, the compact responsibility snapshot is deliberately closed rather than free-form:

```text
responsibility
-> outcome        required non-empty text
-> acceptance     required non-empty text
-> intent          optional: inspect | implement | verify | review

authority
-> write_scope         required array of non-empty path/scope strings
-> mutation_authority  optional: none | declared-output-only | bounded-source-write
-> decision_rights     optional array of non-empty bounded-right strings
```

These values reuse the existing Router and Guardrails vocabulary; they do not create a second task taxonomy. Unit identity, delegated role, model lane, lifecycle, and attempt identity remain separate typed fields in the capsule.

For a multi-unit orchestration, TeamPlan remains the canonical structural truth; `team_plan_revision` is either null or a positive integer binding the compact active-unit index to the accepted plan revision. The capsule does not duplicate the full plan or recovery ledger by default.

`controls` is a reserved compatibility field and must remain an empty array. Status/Steer/Takeover accounting has one canonical owner in typed `accounting_refs`; do not create a second control ledger. `pending_takeover`, when present, is exactly `{unit_id, status}` with `status: pending` and must reference an existing unit.

Do not persist raw user prompts, child transcripts, private reasoning, source-file contents, web pages, full tool output, credentials, secrets, or a duplicate evidence corpus. The closed compact field schema and the existing 64 KiB capsule bound are both safety boundaries; callers still must not disguise prohibited content inside an allowed semantic field.
'''
if state_doc.count(old_doc) != 1:
    raise SystemExit("expected compact snapshot documentation block exactly once")
state_doc = state_doc.replace(old_doc, new_doc, 1)
STATE_DOC.write_text(state_doc, encoding="utf-8")

test = STATE_TEST.read_text(encoding="utf-8")
old_pending = '''    if unresolved == "PLANNED":
        state["units"] = [unit(state="PLANNED")]
    else:
        state["pending_takeover"] = {"unit_id": "U1", "status": "pending"}
    module.write_state(state, temp_root=tmp_path)
'''
new_pending = '''    if unresolved == "PLANNED":
        state["units"] = [unit(state="PLANNED")]
    else:
        state["units"] = [unit(state="PLANNED")]
        state["pending_takeover"] = {"unit_id": "U1", "status": "pending"}
    module.write_state(state, temp_root=tmp_path)
'''
if test.count(old_pending) != 1:
    raise SystemExit("expected pending takeover fixture exactly once")
test = test.replace(old_pending, new_pending, 1)
old_recovery_assert = '''    assert summary["recoveries"] == 0
'''
if test.count(old_recovery_assert) != 1:
    raise SystemExit("expected recoveries assertion exactly once")
test = test.replace(old_recovery_assert, "", 1)
STATE_TEST.write_text(test, encoding="utf-8")

COMPACT_TEST.write_text(
    '''import importlib.util\nfrom pathlib import Path\n\nimport pytest\n\n\nROOT = Path(__file__).resolve().parents[1]\nMODULE_PATH = ROOT / "scripts" / "dispatch_state.py"\n\n\ndef load_module():\n    spec = importlib.util.spec_from_file_location("dispatch_state_compact_schema", MODULE_PATH)\n    assert spec and spec.loader\n    module = importlib.util.module_from_spec(spec)\n    spec.loader.exec_module(module)\n    return module\n\n\ndef unit():\n    return {\n        "unit_id": "U1",\n        "task_id": "task-1",\n        "attempt": 1,\n        "native_task_name": "sd-u1-a1-execute",\n        "agent_id": None,\n        "role": "worker",\n        "model_lane": "Luna Max",\n        "responsibility": {\n            "outcome": "change one owned file",\n            "intent": "implement",\n            "acceptance": "focused test passes",\n        },\n        "authority": {\n            "write_scope": ["owned.py"],\n            "mutation_authority": "bounded-source-write",\n            "decision_rights": ["local implementation mechanics"],\n        },\n        "writer": True,\n        "control_state": "SPAWN_PENDING",\n        "adopted": False,\n        "accepted": False,\n        "failure_origin": "none",\n        "blocker": "none",\n        "quarantine_reason": None,\n    }\n\n\ndef state_with_unit(module):\n    state = module.new_state(thread_id="thread-1", locale="en")\n    state["units"] = [unit()]\n    return state\n\n\ndef test_compact_snapshot_accepts_only_existing_router_and_authority_shape():\n    module = load_module()\n    state = state_with_unit(module)\n    state["team_plan_revision"] = 2\n    state["pending_takeover"] = {"unit_id": "U1", "status": "pending"}\n    assert module.validate_state_payload(state) == state\n\n\n@pytest.mark.parametrize(\n    "field,value,message",\n    [\n        ("team_plan_revision", 0, "positive integer"),\n        ("team_plan_revision", True, "positive integer"),\n        ("controls", [{"action": "Status"}], "must remain empty"),\n        ("pending_takeover", {"unit_id": "U9", "status": "pending"}, "existing unit"),\n        ("pending_takeover", {"unit_id": "U1", "status": "done"}, "status=pending"),\n    ],\n)\ndef test_top_level_compact_metadata_rejects_unowned_or_malformed_state(field, value, message):\n    module = load_module()\n    state = state_with_unit(module)\n    state[field] = value\n    with pytest.raises(module.StatePayloadError, match=message):\n        module.validate_state_payload(state)\n\n\ndef test_responsibility_rejects_free_form_or_invalid_intent():\n    module = load_module()\n    state = state_with_unit(module)\n    state["units"][0]["responsibility"]["task_description"] = "copy arbitrary task text"\n    with pytest.raises(module.StatePayloadError, match="responsibility has unsupported fields"):\n        module.validate_state_payload(state)\n\n    state = state_with_unit(module)\n    state["units"][0]["responsibility"]["intent"] = "deploy"\n    with pytest.raises(module.StatePayloadError, match="invalid intent"):\n        module.validate_state_payload(state)\n\n\ndef test_authority_rejects_free_form_fields_and_invalid_values():\n    module = load_module()\n    state = state_with_unit(module)\n    state["units"][0]["authority"]["notes"] = "arbitrary authority prose"\n    with pytest.raises(module.StatePayloadError, match="authority has unsupported fields"):\n        module.validate_state_payload(state)\n\n    state = state_with_unit(module)\n    state["units"][0]["authority"]["mutation_authority"] = "unbounded"\n    with pytest.raises(module.StatePayloadError, match="invalid mutation_authority"):\n        module.validate_state_payload(state)\n\n    state = state_with_unit(module)\n    state["units"][0]["authority"]["write_scope"] = [""]\n    with pytest.raises(module.StatePayloadError, match="array of non-empty strings"):\n        module.validate_state_payload(state)\n\n\ndef test_receipt_summary_has_no_unreachable_generic_recovery_channel():\n    module = load_module()\n    summary = module.account_receipt([])\n    assert "recoveries" not in summary\n    forged = {**summary, "zero_child": False, "dispatch": [{"model_lane": None, "activity": "read", "count": 1}], "recoveries": 3}\n    rendered = module.format_receipt(forged, locale="en")\n    assert "recovery×" not in rendered\n''',
    encoding="utf-8",
)
