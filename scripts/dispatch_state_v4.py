#!/usr/bin/env python3
"""Public V4 orchestration-state boundary.

Schema validation and reconciliation live in ``dispatch_state_v4_core``. This
module exposes only the supported runtime surface and owns safe active-state
creation/removal. Existing active state is never overwritten through this
facade.
"""

from __future__ import annotations

import os as _os
import re as _re
from pathlib import Path as _Path
from typing import Any as _Any, Mapping as _Mapping

import dispatch_state_v4_core as _core
import state_storage as _storage


SCHEMA_VERSION = _core.SCHEMA_VERSION
DEFAULT_MAX_BYTES = _core.DEFAULT_MAX_BYTES
CANONICAL_WORKSPACE_ID = _core.CANONICAL_WORKSPACE_ID
WORK_UNIT_STATES = _core.WORK_UNIT_STATES
EXECUTION_STATES = _core.EXECUTION_STATES
WRITER_LEASE_STATES = _core.WRITER_LEASE_STATES
WRITER_BLOCKING_STATES = _core.WRITER_BLOCKING_STATES
WRITER_OWNER_KINDS = _core.WRITER_OWNER_KINDS
WORK_INTENTS = _core.WORK_INTENTS
MUTATION_AUTHORITIES = _core.MUTATION_AUTHORITIES
AUTHORITY_RANK = _core.AUTHORITY_RANK
FAILURE_ORIGINS = _core.FAILURE_ORIGINS
TASK_BLOCKERS = _core.TASK_BLOCKERS
PROFILE_CONTRACT = _core.PROFILE_CONTRACT
HOST_STATE_MAP = _core.HOST_STATE_MAP
HOST_UNCERTAIN_STATES = _core.HOST_UNCERTAIN_STATES

StateError = _core.StateError
StateIdentityError = _core.StateIdentityError
StatePathError = _core.StatePathError
StatePayloadError = _core.StatePayloadError
StateCorruptError = _core.StateCorruptError
StateLockError = _core.StateLockError

validate_native_task_name = _core.validate_native_task_name
scopes_within = _core.scopes_within
current_execution_for_unit = _core.current_execution_for_unit
new_state = _core.new_state
state_path = _core.state_path
mutate_state = _core.mutate_state
observation_basis = _core.observation_basis
reconcile_execution_observation = _core.reconcile_execution_observation

_TERMINAL_WORK_UNIT_STATES = {"ACCEPTED", "CANCELLED"}
_UNSETTLED_EXECUTION_STATES = {"SPAWN_PENDING", "RUNNING", "INTERRUPTED", "UNKNOWN"}
_TASK_UNIT_PATTERN = _re.compile(r"[A-Za-z0-9_]+\Z")


def native_task_name_for(
    payload: _Mapping[str, _Any], *, unit_id: str, attempt_no: int
) -> str:
    """Derive the canonical Host task name from one WorkUnit attempt generation."""
    if not isinstance(unit_id, str) or _TASK_UNIT_PATTERN.fullmatch(unit_id) is None:
        raise StatePayloadError(
            "managed WorkUnit unit_id must use letters, digits, or underscores for Host task naming"
        )
    if not isinstance(attempt_no, int) or isinstance(attempt_no, bool) or attempt_no < 1:
        raise StatePayloadError("managed execution attempt_no must be a positive integer")
    folded = unit_id.lower()
    collisions = [
        item.get("unit_id")
        for item in payload.get("work_units", [])
        if isinstance(item, _Mapping)
        and isinstance(item.get("unit_id"), str)
        and item["unit_id"].lower() == folded
    ]
    if collisions != [unit_id]:
        raise StatePayloadError(
            "managed WorkUnit unit_id must be unique under case-folded Host task naming"
        )
    return validate_native_task_name(f"sd_{folded}_a{attempt_no}")


def _validate_execution_task_bindings(payload: _Mapping[str, _Any]) -> None:
    for execution in payload.get("executions", []):
        if not isinstance(execution, _Mapping):
            continue
        unit_id = execution.get("unit_id")
        attempt_no = execution.get("attempt_no")
        expected = native_task_name_for(
            payload,
            unit_id=str(unit_id) if isinstance(unit_id, str) else "",
            attempt_no=attempt_no,
        )
        if execution.get("native_task_name") != expected:
            raise StatePayloadError(
                "native_task_name must match the WorkUnit and attempt generation"
            )


def validate_state_payload(
    payload: _Mapping[str, _Any],
    *,
    thread_id: str | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> None:
    _core.validate_state_payload(dict(payload), thread_id=thread_id, max_bytes=max_bytes)
    _validate_execution_task_bindings(payload)


def load_state(
    thread_id: str | None = None,
    *,
    temp_root: str | _os.PathLike[str] | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> dict[str, _Any] | None:
    current = _core.load_state(thread_id, temp_root=temp_root, max_bytes=max_bytes)
    if current is not None:
        _validate_execution_task_bindings(current)
    return current


def create_state_if_absent(
    payload: _Mapping[str, _Any],
    *,
    thread_id: str | None = None,
    temp_root: str | _os.PathLike[str] | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> _Path:
    """Create the active V4 capsule exactly once for one root thread."""
    identity = _storage.resolve_thread_id(
        thread_id if thread_id is not None else payload.get("root_session_id")
    )
    validate_state_payload(dict(payload), thread_id=identity, max_bytes=max_bytes)
    encoded = _core._serialized_payload(payload, max_bytes=max_bytes)
    with _storage.state_lock(identity, temp_root=temp_root):
        _, _, path, _ = _storage._paths(identity, temp_root, create=True)
        if path.exists():
            raise StatePayloadError("active V4 state already exists")
        _storage._write_unlocked(path, encoded)
        return path


def _require_terminal_state(current: _Mapping[str, _Any]) -> None:
    if any(unit.get("state") not in _TERMINAL_WORK_UNIT_STATES for unit in current["work_units"]):
        raise StatePayloadError("active V4 state has unresolved WorkUnit responsibility")
    if any(
        execution.get("lifecycle") in _UNSETTLED_EXECUTION_STATES
        for execution in current["executions"]
    ):
        raise StatePayloadError("active V4 state has unsettled or ambiguous execution")
    lease = current.get("writer_lease")
    if isinstance(lease, _Mapping) and lease.get("state") in WRITER_BLOCKING_STATES:
        raise StatePayloadError("active V4 state has blocking WriterLease")


def remove_terminal_state(
    thread_id: str | None = None,
    *,
    expected_state_revision: int | None = None,
    temp_root: str | _os.PathLike[str] | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> bool:
    """Remove active state only after all project responsibility is settled."""
    identity = _storage.resolve_thread_id(thread_id)
    with _storage.state_lock(identity, temp_root=temp_root):
        current = load_state(identity, temp_root=temp_root, max_bytes=max_bytes)
        if current is None:
            return False
        if (
            expected_state_revision is not None
            and current["state_revision"] != expected_state_revision
        ):
            raise StatePayloadError("state_revision compare-and-swap failed")
        _require_terminal_state(current)
        _, _, path, _ = _storage._paths(identity, temp_root, create=False)
        path.unlink()
        if _os.name != "nt":
            directory_fd = _os.open(path.parent, _os.O_RDONLY)
            try:
                _os.fsync(directory_fd)
            finally:
                _os.close(directory_fd)
        return True


def write_state(
    payload: _Mapping[str, _Any],
    *,
    thread_id: str | None = None,
    temp_root: str | _os.PathLike[str] | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> _Path:
    """Compatibility create-only entry point; existing active state is never replaced."""
    return create_state_if_absent(
        payload,
        thread_id=thread_id,
        temp_root=temp_root,
        max_bytes=max_bytes,
    )


__all__ = [
    "AUTHORITY_RANK",
    "CANONICAL_WORKSPACE_ID",
    "DEFAULT_MAX_BYTES",
    "EXECUTION_STATES",
    "FAILURE_ORIGINS",
    "HOST_STATE_MAP",
    "HOST_UNCERTAIN_STATES",
    "MUTATION_AUTHORITIES",
    "PROFILE_CONTRACT",
    "SCHEMA_VERSION",
    "StateCorruptError",
    "StateError",
    "StateIdentityError",
    "StateLockError",
    "StatePathError",
    "StatePayloadError",
    "TASK_BLOCKERS",
    "WORK_INTENTS",
    "WORK_UNIT_STATES",
    "WRITER_BLOCKING_STATES",
    "WRITER_LEASE_STATES",
    "WRITER_OWNER_KINDS",
    "create_state_if_absent",
    "current_execution_for_unit",
    "load_state",
    "mutate_state",
    "native_task_name_for",
    "new_state",
    "observation_basis",
    "reconcile_execution_observation",
    "remove_terminal_state",
    "scopes_within",
    "state_path",
    "validate_native_task_name",
    "validate_state_payload",
]
