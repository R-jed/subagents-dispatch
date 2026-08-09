import builtins
import importlib.util
import json
import os
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "dispatch_state.py"


def load_module():
    spec = importlib.util.spec_from_file_location("dispatch_state", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_module_import_does_not_require_posix_fcntl(monkeypatch):
    original_import = builtins.__import__

    def import_without_fcntl(name, *args, **kwargs):
        if name == "fcntl":
            raise ImportError("fcntl is unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_fcntl)
    load_module()


def capsule(module, thread_id: str, *, updated_at: str = "2026-08-10T00:00:00Z") -> dict:
    return module.new_state(thread_id=thread_id, locale="zh", now=updated_at)


def unit(
    *,
    unit_id: str = "U1",
    task_id: str = "task-1",
    attempt: int = 1,
    state: str = "SPAWN_PENDING",
    agent_id: str | None = None,
    native_task_name: str = "sd-u1-a1-execute",
    writer: bool = True,
) -> dict:
    return {
        "unit_id": unit_id,
        "task_id": task_id,
        "attempt": attempt,
        "native_task_name": native_task_name,
        "agent_id": agent_id,
        "role": "worker",
        "model_lane": "Luna Max",
        "responsibility": {"outcome": "change one file", "acceptance": "focused test passes"},
        "authority": {"write_scope": ["owned.py"]},
        "writer": writer,
        "control_state": state,
        "adopted": False,
        "accepted": False,
        "failure_origin": "runtime_ambiguous" if state == "UNKNOWN" else "none",
        "blocker": "none",
        "quarantine_reason": None,
    }


def receipt_event(
    ref: str,
    kind: str,
    unit_id: str,
    attempt: int,
    agent_id: str,
    **evidence,
) -> dict:
    return {
        "ref": ref,
        "kind": kind,
        "unit_id": unit_id,
        "attempt": attempt,
        "agent_id": agent_id,
        **evidence,
    }


def test_state_path_is_thread_scoped_and_requires_reliable_identity(tmp_path: Path, monkeypatch):
    module = load_module()

    first = module.state_path("thread-1", temp_root=tmp_path)
    second = module.state_path("thread-2", temp_root=tmp_path)
    assert first == tmp_path / "subagents-dispatch" / "thread-1" / "active.json"
    assert first != second

    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    with pytest.raises(module.StateIdentityError, match="CODEX_THREAD_ID"):
        module.state_path(temp_root=tmp_path)

    for invalid in ["", ".", "..", "a/b", "a\\b", " space", "x" * 129]:
        with pytest.raises(module.StateIdentityError):
            module.state_path(invalid, temp_root=tmp_path)


def test_atomic_state_write_is_compact_private_and_bounded(tmp_path: Path):
    module = load_module()
    state = capsule(module, "thread-1")

    path = module.write_state(state, temp_root=tmp_path)
    assert path == module.state_path("thread-1", temp_root=tmp_path)
    assert module.load_state("thread-1", temp_root=tmp_path) == state
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700
    assert path.parent.parent.stat().st_mode & 0o777 == 0o700
    assert not list(path.parent.glob(".active.*.tmp"))

    too_large = capsule(module, "thread-1")
    too_large["units"] = [{"unit_id": "U1", "responsibility": {"acceptance": "x" * 70_000}}]
    with pytest.raises(module.StatePayloadError, match="bytes"):
        module.write_state(too_large, temp_root=tmp_path)


def test_state_lock_is_exclusive_and_private(tmp_path: Path):
    module = load_module()
    with module.state_lock("thread-1", temp_root=tmp_path):
        lock_path = tmp_path / "subagents-dispatch" / "thread-1" / "active.lock"
        assert lock_path.stat().st_mode & 0o777 == 0o600
        with pytest.raises(module.StateLockError, match="locked"):
            with module.state_lock("thread-1", temp_root=tmp_path, blocking=False):
                pass


def test_unsafe_roots_symlinks_and_corrupt_state_fail_closed(tmp_path: Path):
    module = load_module()
    outside = tmp_path / "outside"
    outside.mkdir()
    unsafe_root = tmp_path / "unsafe"
    unsafe_root.symlink_to(outside, target_is_directory=True)
    with pytest.raises(module.StatePathError, match="symlink"):
        module.write_state(capsule(module, "thread-1"), temp_root=unsafe_root)

    safe_root = tmp_path / "safe"
    safe_root.mkdir()
    dispatch_root = safe_root / "subagents-dispatch"
    dispatch_root.symlink_to(outside, target_is_directory=True)
    with pytest.raises(module.StatePathError, match="symlink"):
        module.write_state(capsule(module, "thread-1"), temp_root=safe_root)

    dispatch_root.unlink()
    thread_dir = dispatch_root / "thread-1"
    dispatch_root.mkdir(mode=0o700)
    thread_dir.mkdir(mode=0o700)
    state_path = thread_dir / "active.json"
    state_path.write_text("{not-json", encoding="utf-8")
    os.chmod(state_path, 0o600)
    with pytest.raises(module.StateCorruptError, match="invalid JSON"):
        module.load_state("thread-1", temp_root=safe_root)
    assert state_path.exists()


def test_payload_rejects_identity_mismatch_and_unbounded_top_level_data(tmp_path: Path):
    module = load_module()
    state = capsule(module, "thread-1")
    state["root_thread_id"] = "thread-2"
    with pytest.raises(module.StatePayloadError, match="root_thread_id"):
        module.write_state(state, thread_id="thread-1", temp_root=tmp_path)

    state = capsule(module, "thread-1")
    state["raw_transcript"] = "secret"
    with pytest.raises(module.StatePayloadError, match="unsupported fields"):
        module.write_state(state, temp_root=tmp_path)

    state = capsule(module, "thread-1")
    unsafe = unit()
    unsafe["responsibility"]["raw_transcript"] = "private child output"
    state["units"] = [unsafe]
    with pytest.raises(module.StatePayloadError, match="forbidden persisted field"):
        module.write_state(state, temp_root=tmp_path)

    path = tmp_path / "subagents-dispatch" / "thread-1" / "active.json"
    path.parent.mkdir(parents=True, mode=0o700)
    path.write_text(json.dumps({"schema_version": "1.0"}), encoding="utf-8")
    os.chmod(path, 0o600)
    with pytest.raises(module.StateCorruptError, match="root_thread_id"):
        module.load_state("thread-1", temp_root=tmp_path)


def test_prepare_spawn_is_persisted_before_host_identity_exists(tmp_path: Path):
    module = load_module()
    state = capsule(module, "thread-1")

    prepared = module.prepare_spawn(state, unit(), temp_root=tmp_path)

    assert prepared["units"][0]["control_state"] == "SPAWN_PENDING"
    assert prepared["units"][0]["agent_id"] is None
    assert module.load_state("thread-1", temp_root=tmp_path) == prepared
    with pytest.raises(module.StatePayloadError, match="unresolved unit"):
        module.prepare_spawn(prepared, unit(task_id="task-2"), temp_root=tmp_path)


def test_prepare_spawn_rejects_a_second_active_writer(tmp_path: Path):
    module = load_module()
    stale = capsule(module, "thread-1")
    first = module.prepare_spawn(stale, unit(), temp_root=tmp_path)
    assert first["units"][0]["unit_id"] == "U1"

    with pytest.raises(module.StatePayloadError, match="active writer"):
        module.prepare_spawn(
            stale,
            unit(unit_id="U2", task_id="task-2", native_task_name="sd-u2-a1-execute"),
            temp_root=tmp_path,
        )
    assert module.load_state("thread-1", temp_root=tmp_path) == first


def test_reconcile_unambiguously_binds_spawn_and_host_truth_wins():
    module = load_module()
    state = capsule(module, "thread-1")
    state["units"] = [unit()]
    observation = {
        "complete": True,
        "children": [
            {
                "native_task_name": "sd-u1-a1-execute",
                "agent_id": "agent-1",
                "state": "running",
            }
        ],
    }

    running = module.reconcile_state(state, observation)
    assert running["units"][0]["agent_id"] == "agent-1"
    assert running["units"][0]["control_state"] == "RUNNING"

    interrupted = module.reconcile_state(
        running,
        {
            "complete": True,
            "children": [{**observation["children"][0], "state": "interrupted"}],
        },
    )
    assert interrupted["units"][0]["control_state"] == "INTERRUPTED"

    resumed = module.reconcile_state(interrupted, observation)
    assert resumed["units"][0]["control_state"] == "RUNNING"
    assert resumed["units"][0]["task_id"] == "task-1"
    assert resumed["units"][0]["attempt"] == 1
    assert resumed["units"][0]["agent_id"] == "agent-1"
    assert module.reconcile_state(resumed, observation) == resumed


def test_reconcile_ambiguity_conflict_and_absence_quarantine_without_replacement():
    module = load_module()
    state = capsule(module, "thread-1")
    state["units"] = [unit()]
    duplicate_name = {
        "complete": True,
        "children": [
            {"native_task_name": "sd-u1-a1-execute", "agent_id": "agent-1", "state": "running"},
            {"native_task_name": "sd-u1-a1-execute", "agent_id": "agent-2", "state": "running"},
        ],
    }
    ambiguous = module.reconcile_state(state, duplicate_name)
    record = ambiguous["units"][0]
    assert record["control_state"] == "UNKNOWN"
    assert record["failure_origin"] == "runtime_ambiguous"
    assert record["quarantine_reason"] == "ambiguous_native_identity"
    assert len(ambiguous["units"]) == 1

    stale = capsule(module, "thread-1")
    stale["units"] = [unit(state="RUNNING", agent_id="agent-1")]
    absent = module.reconcile_state(stale, {"complete": True, "children": []})
    assert absent["units"][0]["control_state"] == "UNKNOWN"
    assert absent["units"][0]["quarantine_reason"] == "native_identity_absent"
    assert len(absent["units"]) == 1


def test_status_is_one_low_resolution_snapshot_with_optional_unit_zoom():
    module = load_module()
    state = capsule(module, "thread-1")
    state["units"] = [
        unit(),
        unit(
            unit_id="U2",
            task_id="task-2",
            native_task_name="sd-u2-a1-read",
            writer=False,
        ),
    ]
    observation = {
        "complete": True,
        "children": [
            {"native_task_name": "sd-u1-a1-execute", "agent_id": "agent-1", "state": "running"},
            {"native_task_name": "sd-u2-a1-read", "agent_id": "agent-2", "state": "completed"},
        ],
    }

    snapshot = module.status_snapshot(state, observation)
    assert [item["unit_id"] for item in snapshot["units"]] == ["U1", "U2"]
    assert set(snapshot["units"][0]) == {"unit_id", "role", "control_state", "writer", "blocker"}
    assert state["units"][0]["control_state"] == "SPAWN_PENDING"
    assert state["accounting_refs"] == []

    zoom = module.status_snapshot(state, observation, unit_id="U2")
    assert zoom["units"] == [snapshot["units"][1]]
    with pytest.raises(module.TargetResolutionError, match="not found"):
        module.status_snapshot(state, observation, unit_id="U9")


def test_target_resolution_never_guesses_and_controls_preserve_identity():
    module = load_module()
    state = capsule(module, "thread-1")
    assert module.resolve_control_target(state, action="steer")["status"] == "none"

    first = unit(state="RUNNING", agent_id="agent-1")
    state["units"] = [first]
    resolved = module.resolve_control_target(state, action="steer")
    assert resolved["status"] == "resolved"
    assert resolved["unit"] == first

    state["units"].append(
        unit(
            unit_id="U2",
            task_id="task-2",
            state="RUNNING",
            agent_id="agent-2",
            native_task_name="sd-u2-a1-execute",
        )
    )
    ambiguous = module.resolve_control_target(state, action="steer")
    assert ambiguous == {"status": "ambiguous", "candidates": ["U1", "U2"]}
    exact = module.resolve_control_target(state, unit_id="U2", action="steer")
    assert exact["status"] == "resolved"
    assert exact["unit"]["agent_id"] == "agent-2"

    state["units"][1]["control_state"] = "INTERRUPTED"
    ineligible = module.resolve_control_target(state, unit_id="U2", action="steer")
    assert ineligible["status"] == "ineligible"
    assert "not Resume" in ineligible["reason"]


def test_takeover_and_dispatch_resume_fail_closed_without_new_work():
    module = load_module()
    immutable = unit(state="INTERRUPTED", agent_id="agent-1")
    state = capsule(module, "thread-1")
    state["units"] = [immutable]

    takeover = module.takeover_target(state)
    assert takeover["status"] == "resolved"
    assert takeover["conflicting_write_allowed"] is False
    assert takeover["reason"] == "previous writer is not definitively non-active"

    resumed = module.resume_dispatch(state)
    assert resumed["operation"] == "resume_existing_child"
    assert resumed["binding"] == {
        key: immutable[key]
        for key in [
            "unit_id",
            "task_id",
            "attempt",
            "agent_id",
            "role",
            "responsibility",
            "authority",
        ]
    }
    assert resumed["accounting_delta"] == {
        "child": 0,
        "retry": 0,
        "followup": 0,
        "pass": 0,
        "rework": 0,
    }
    assert state["units"] == [immutable]

    state["units"][0]["control_state"] = "UNKNOWN"
    state["units"][0]["failure_origin"] = "runtime_ambiguous"
    blocked = module.resume_dispatch(state)
    assert blocked["status"] == "blocked"
    assert blocked["operation"] is None

    state["units"][0].update(
        {"control_state": "CLOSED", "failure_origin": "none", "adopted": False, "accepted": False}
    )
    closed = module.takeover_target(state)
    assert closed["status"] == "resolved"
    assert closed["conflicting_write_allowed"] is True


def test_normal_cleanup_and_stale_cleanup_preserve_uncertain_active_state(tmp_path: Path):
    module = load_module()
    old = "2026-07-01T00:00:00Z"
    terminal = capsule(module, "terminal", updated_at=old)
    terminal["units"] = [unit(state="CLOSED", agent_id="agent-1")]
    module.write_state(terminal, temp_root=tmp_path)

    uncertain = capsule(module, "uncertain", updated_at=old)
    uncertain["units"] = [unit(state="UNKNOWN", agent_id="agent-2")]
    module.write_state(uncertain, temp_root=tmp_path)

    current = capsule(module, "current", updated_at=old)
    current["units"] = [unit(state="CLOSED", agent_id="agent-3")]
    module.write_state(current, temp_root=tmp_path)

    report = module.cleanup_stale_states(
        temp_root=tmp_path,
        active_thread_id="current",
        now="2026-08-10T00:00:00Z",
    )
    assert report["removed"] == ["terminal"]
    assert report["retained_active"] == ["uncertain"]
    assert report["current"] == ["current"]
    assert module.load_state("terminal", temp_root=tmp_path) is None
    assert module.load_state("uncertain", temp_root=tmp_path) is not None

    assert module.remove_state("current", temp_root=tmp_path) is True
    assert module.load_state("current", temp_root=tmp_path) is None


def test_remove_state_rejects_active_or_uncertain_work(tmp_path: Path):
    module = load_module()
    state = capsule(module, "thread-1")
    state["units"] = [unit(state="UNKNOWN", agent_id="agent-1")]
    module.write_state(state, temp_root=tmp_path)

    with pytest.raises(module.StatePayloadError, match="unresolved"):
        module.remove_state("thread-1", temp_root=tmp_path)
    assert module.load_state("thread-1", temp_root=tmp_path) is not None


@pytest.mark.parametrize("unresolved", ["PLANNED", "pending_takeover"])
def test_cleanup_and_remove_preserve_all_unresolved_work(tmp_path: Path, unresolved: str):
    module = load_module()
    state = capsule(module, "thread-1", updated_at="2026-07-01T00:00:00Z")
    if unresolved == "PLANNED":
        state["units"] = [unit(state="PLANNED")]
    else:
        state["pending_takeover"] = {"unit_id": "U1", "status": "pending"}
    module.write_state(state, temp_root=tmp_path)

    with pytest.raises(module.StatePayloadError, match="unresolved"):
        module.remove_state("thread-1", temp_root=tmp_path)
    report = module.cleanup_stale_states(
        temp_root=tmp_path,
        now="2026-08-10T00:00:00Z",
    )
    assert report["retained_active"] == ["thread-1"]
    assert module.load_state("thread-1", temp_root=tmp_path) is not None


def test_state_rejects_unknown_recovery_axes_and_explicit_empty_identity(tmp_path: Path):
    module = load_module()
    state = capsule(module, "thread-1")
    state["units"] = [unit(state="RUNNING", agent_id="agent-1")]
    state["units"][0]["failure_origin"] = "invented"
    with pytest.raises(module.StatePayloadError, match="failure_origin"):
        module.write_state(state, temp_root=tmp_path)

    state["units"][0]["failure_origin"] = "none"
    state["units"][0]["blocker"] = "invented"
    with pytest.raises(module.StatePayloadError, match="blocker"):
        module.write_state(state, temp_root=tmp_path)

    with pytest.raises(module.StateIdentityError):
        module.write_state(capsule(module, "thread-1"), thread_id="", temp_root=tmp_path)


@pytest.mark.parametrize(
    ("state_name", "failure_origin", "blocker", "accepted", "message"),
    [
        ("FAILED", "none", "none", False, "requires a failure_origin"),
        ("RUNNING", "timeout", "none", False, "non-failure state"),
        ("RUNNING", "none", "judgment", False, "blocker belongs only"),
        ("RUNNING", "none", "none", True, "accepted evidence"),
        ("PLANNED", "none", "contract", False, "blocker belongs only"),
    ],
)
def test_state_rejects_cross_axis_invalid_recovery_truth(
    tmp_path: Path,
    state_name: str,
    failure_origin: str,
    blocker: str,
    accepted: bool,
    message: str,
):
    module = load_module()
    agent_id = None if state_name == "PLANNED" else "agent-1"
    state = capsule(module, "thread-1")
    state["units"] = [unit(state=state_name, agent_id=agent_id)]
    state["units"][0].update(
        failure_origin=failure_origin,
        blocker=blocker,
        accepted=accepted,
    )
    with pytest.raises(module.StatePayloadError, match=message):
        module.write_state(state, temp_root=tmp_path)


def test_stale_cleanup_rechecks_state_before_deleting(tmp_path: Path, monkeypatch):
    module = load_module()
    stale = capsule(module, "thread-1", updated_at="2026-07-01T00:00:00Z")
    stale["units"] = [unit(state="CLOSED", agent_id="agent-1")]
    module.write_state(stale, temp_root=tmp_path)
    original_is_stale = module.is_stale
    refreshed = False

    def refresh_during_cleanup(payload, **kwargs):
        nonlocal refreshed
        if not refreshed:
            refreshed = True
            fresh = dict(payload)
            fresh["updated_at"] = "2026-08-10T00:00:00Z"
            module.write_state(fresh, temp_root=tmp_path)
        return original_is_stale(payload, **kwargs)

    monkeypatch.setattr(module, "is_stale", refresh_during_cleanup)
    report = module.cleanup_stale_states(
        temp_root=tmp_path,
        now="2026-08-10T00:00:01Z",
    )

    assert report["removed"] == []
    assert report["fresh"] == ["thread-1"]
    assert module.load_state("thread-1", temp_root=tmp_path)["updated_at"] == "2026-08-10T00:00:00Z"


def test_receipt_accounting_uses_unique_stable_refs_and_separate_axes():
    module = load_module()
    first_artifact = "sha256:" + "a" * 64
    second_artifact = "sha256:" + "b" * 64
    materialized = [
        {"unit_id": "U1", "attempt": 1, "agent_id": "agent-1"},
        {"unit_id": "U2", "attempt": 1, "agent_id": "agent-2a", "control_state": "FAILED"},
        {"unit_id": "U2", "attempt": 2, "agent_id": "agent-2b", "control_state": "RUNNING"},
        {"unit_id": "U3", "attempt": 1, "agent_id": "agent-3"},
        {"unit_id": "U3", "attempt": 2, "agent_id": "agent-4"},
    ]
    events = [
        receipt_event("attempt:U1:A1", "attempt", "U1", 1, "agent-1", model_lane="Luna Max", model_evidence_source="native", activity="read"),
        receipt_event("attempt:U1:A1", "attempt", "U1", 1, "agent-1", model_lane="Luna Max", model_evidence_source="native", activity="read"),
        receipt_event("followup:U1:A1:F1", "followup", "U1", 1, "agent-1", model_lane="Luna Max", model_evidence_source="native", activity="execute"),
        receipt_event("retry:U2:A2", "retry", "U2", 2, "agent-2b"),
        receipt_event("review-attempt:U3:A1", "reviewer_attempt", "U3", 1, "agent-3", model_lane="Sol High", model_evidence_source="native", activity="review"),
        receipt_event("review-round:U3:R1", "review_round", "U3", 1, "agent-3", verdict="rework_required", review_artifact_id=first_artifact),
        receipt_event("rework:U1:R1", "semantic_rework", "U1", 1, "agent-1", review_artifact_id=first_artifact),
        receipt_event("review-attempt:U3:A2", "reviewer_attempt", "U3", 2, "agent-4", model_lane="Sol High", model_evidence_source="native", activity="review"),
        receipt_event("review-round:U3:R2", "review_round", "U3", 2, "agent-4", verdict="passed", review_artifact_id=second_artifact),
        receipt_event("recovery:U1:REBIND", "recovery", "U1", 1, "agent-1", action="rebind"),
        {"ref": "control:status:1", "kind": "control", "action": "Status"},
        {"ref": "control:status:1", "kind": "control", "action": "Status"},
    ]

    summary = module.account_receipt(events, materialized_units=materialized)
    assert summary["dispatch"] == [
        {"model_lane": "Luna Max", "activity": "read", "count": 1},
        {"model_lane": "Luna Max", "activity": "execute", "count": 1},
        {"model_lane": "Sol High", "activity": "review", "count": 2},
    ]
    assert summary["focused_followups"] == 1
    assert summary["retries"] == 1
    assert summary["semantic_reworks"] == 1
    assert summary["reviewer_attempts"] == 2
    assert summary["review"] == {"rounds": 2, "reworks": 1, "verdict": "passed"}
    assert summary["recoveries"] == 1
    assert summary["controls"] == [{"action": "Status", "count": 1}]

    with pytest.raises(module.ReceiptAccountingError, match="conflicting event ref"):
        module.account_receipt(
            [
                receipt_event("attempt:U1:A1", "attempt", "U1", 1, "agent-1", model_lane="Luna Max", model_evidence_source="native", activity="read"),
                receipt_event("attempt:U1:A1", "attempt", "U1", 1, "agent-1", model_lane="Sol High", model_evidence_source="native", activity="decide"),
            ],
            materialized_units=materialized,
        )


def test_receipt_formatter_localizes_public_activity_without_internal_roles():
    module = load_module()
    materialized = [
        {"unit_id": f"U{index}", "attempt": 1, "agent_id": f"agent-{index}"}
        for index in range(1, 6)
    ]
    summary = module.account_receipt(
        [
            receipt_event("a1", "attempt", "U1", 1, "agent-1", model_lane="Luna Max", model_evidence_source="native", activity="read"),
            receipt_event("a2", "attempt", "U2", 1, "agent-2", model_lane="Terra XHigh", model_evidence_source="native", activity="investigate"),
            receipt_event("a3", "attempt", "U3", 1, "agent-3", model_lane="Luna Max", model_evidence_source="native", activity="execute"),
            receipt_event("a4", "attempt", "U4", 1, "agent-4", model_lane="Sol High", model_evidence_source="native", activity="decide"),
            receipt_event("a5", "reviewer_attempt", "U5", 1, "agent-5", model_lane="Sol High", model_evidence_source="native", activity="review"),
            receipt_event("r1", "review_round", "U5", 1, "agent-5", verdict="passed", review_artifact_id="sha256:" + "c" * 64),
        ],
        materialized_units=materialized,
    )
    chinese = module.format_receipt(summary, locale="zh")
    assert "编排: Luna Max 读取 · Terra XHigh 调研 · Luna Max 执行 · Sol High 决策 · Sol High 验收" in chinese
    assert "验收: 1轮 · 通过" in chinese
    assert not {"Reader", "Worker", "Solver", "Investigator", "Advisor"} & set(chinese.split())

    english = module.format_receipt(summary, locale="en")
    assert "Dispatch: Luna Max Read · Terra XHigh Investigate · Luna Max Execute · Sol High Decide · Sol High Review" in english
    assert "Review: 1 round · passed" in english


def test_receipt_persists_unique_events_and_requires_observed_model_evidence(tmp_path: Path):
    module = load_module()
    state = capsule(module, "thread-1")
    state["units"] = [unit(state="COMPLETED", agent_id="agent-1")]
    module.write_state(state, temp_root=tmp_path)
    event = {
        "ref": "attempt:U1:A1",
        "kind": "attempt",
        "unit_id": "U1",
        "attempt": 1,
        "agent_id": "agent-1",
        "model_lane": "Luna Max",
        "model_evidence_source": "native",
        "activity": "execute",
    }

    module.persist_receipt_events("thread-1", [event], temp_root=tmp_path)
    module.persist_receipt_events("thread-1", [event], temp_root=tmp_path)
    persisted = module.load_state("thread-1", temp_root=tmp_path)

    assert persisted["accounting_refs"] == [event]
    assert module.account_receipt(
        persisted["accounting_refs"], materialized_units=persisted["units"]
    )["dispatch"] == [
        {"model_lane": "Luna Max", "activity": "execute", "count": 1}
    ]
    with pytest.raises(module.ReceiptAccountingError, match="materialized child"):
        module.persist_receipt_events(
            "thread-1",
            [
                {
                    **event,
                    "ref": "attempt:U999:A1",
                    "unit_id": "U999",
                    "agent_id": "agent-999",
                }
            ],
            temp_root=tmp_path,
        )
    with pytest.raises(module.ReceiptAccountingError, match="duplicate materialized attempt"):
        module.persist_receipt_events(
            "thread-1",
            [{**event, "ref": "attempt:duplicate-ref"}],
            temp_root=tmp_path,
        )
    with pytest.raises(module.ReceiptAccountingError, match="materialized replacement"):
        module.persist_receipt_events(
            "thread-1",
            [receipt_event("retry:U999:A2", "retry", "U999", 2, "agent-999")],
            temp_root=tmp_path,
        )
    with pytest.raises(module.ReceiptAccountingError, match="observed model evidence"):
        module.account_receipt(
            [receipt_event("attempt:U2:A1", "attempt", "U2", 1, "agent-2", model_lane="Sol High", activity="decide")],
            materialized_units=[{"unit_id": "U2", "attempt": 1, "agent_id": "agent-2"}],
        )

    unobserved = module.account_receipt(
        [receipt_event("attempt:U3:A1", "attempt", "U3", 1, "agent-3", activity="read")],
        materialized_units=[{"unit_id": "U3", "attempt": 1, "agent_id": "agent-3"}],
    )
    assert module.format_receipt(unobserved, locale="en").startswith("Dispatch: Read")


def test_zero_child_receipt_is_minimal_and_status_reconciliation_is_idempotent():
    module = load_module()
    empty = module.account_receipt([])
    assert module.format_receipt(empty, locale="zh") == "编排: 未调度子代理\n验收: 未触发"
    assert module.format_receipt(empty, locale="en") == "Dispatch: no Subagents dispatched\nReview: not triggered"

    events = [{"ref": "control:status:snapshot-1", "kind": "control", "action": "Status"}] * 3
    assert module.account_receipt(events)["controls"] == [{"action": "Status", "count": 1}]


def test_receipt_rejects_unbound_review_rework_and_recovery_claims():
    module = load_module()
    materialized = [{"unit_id": "U1", "attempt": 1, "agent_id": "agent-1"}]
    for event, message in [
        ({"ref": "review:fake", "kind": "review_round", "verdict": "passed"}, "reviewer"),
        ({"ref": "rework:fake", "kind": "semantic_rework"}, "correction"),
        ({"ref": "recovery:fake", "kind": "recovery", "action": "rebind"}, "rebind"),
    ]:
        with pytest.raises(module.ReceiptAccountingError, match=message):
            module.account_receipt([event], materialized_units=materialized)
