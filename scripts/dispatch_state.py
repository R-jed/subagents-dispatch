#!/usr/bin/env python3
"""Bounded thread-local continuity helpers for Codex Native Subagents."""

from __future__ import annotations

import copy
import errno
import json
import os
import re
import stat
import tempfile
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence


SCHEMA_VERSION = "1.0"
STATE_DIRECTORY = "subagents-dispatch"
STATE_FILE = "active.json"
LOCK_FILE = "active.lock"
DEFAULT_MAX_BYTES = 64 * 1024
DEFAULT_STALE_AFTER = timedelta(days=7)
THREAD_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
FORBIDDEN_PERSISTED_KEYS = {
    "prompt",
    "raw_prompt",
    "transcript",
    "raw_transcript",
    "reasoning",
    "chain_of_thought",
    "credential",
    "credentials",
    "secret",
    "secrets",
    "password",
    "access_token",
    "source_content",
    "source_contents",
    "tool_output",
    "full_tool_output",
    "web_page",
}
TOP_LEVEL_FIELDS = {
    "schema_version",
    "root_thread_id",
    "locale",
    "created_at",
    "updated_at",
    "team_plan_revision",
    "units",
    "accounting_refs",
    "controls",
    "pending_takeover",
}
UNIT_FIELDS = {
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
    "PLANNED",
    "SPAWN_PENDING",
    "RUNNING",
    "INTERRUPTED",
    "COMPLETED",
    "FAILED",
    "UNKNOWN",
    "CLOSED",
}
ACTIVE_STATES = {"SPAWN_PENDING", "RUNNING", "INTERRUPTED", "UNKNOWN"}
NON_ACTIVE_STATES = {"COMPLETED", "FAILED", "CLOSED"}
FAILURE_ORIGINS = {
    "none",
    "runtime_unavailable",
    "permission_failure",
    "tool_failure",
    "timeout",
    "quality_failure",
    "runtime_ambiguous",
}
TASK_BLOCKERS = {"none", "contract", "judgment", "investigation", "stalled"}
HOST_STATE_MAP = {
    "pending": "SPAWN_PENDING",
    "running": "RUNNING",
    "interrupted": "INTERRUPTED",
    "completed": "COMPLETED",
    "failed": "FAILED",
    "errored": "FAILED",
    "stopped": "CLOSED",
    "closed": "CLOSED",
}


class StateError(RuntimeError):
    """Base error for bounded dispatch state."""


class StateIdentityError(StateError):
    """The Host did not provide a safe root-thread identity."""


class StatePathError(StateError):
    """The state path is outside the safe temporary boundary."""


class StatePayloadError(StateError):
    """The state payload is invalid or too large."""


class StateCorruptError(StateError):
    """Existing state cannot be trusted."""


class StateLockError(StateError):
    """The state lock cannot be acquired safely."""


class TargetResolutionError(StateError):
    """A requested unit does not resolve exactly."""


class ReceiptAccountingError(StateError):
    """Receipt events are invalid or reuse a stable ref inconsistently."""


def _utc_text(now: datetime | str | None = None) -> str:
    if isinstance(now, str):
        return now
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return current.astimezone(UTC).isoformat().replace("+00:00", "Z")


def resolve_thread_id(
    thread_id: str | None = None, *, environ: Mapping[str, str] | None = None
) -> str:
    value = thread_id
    if value is None:
        value = (environ or os.environ).get("CODEX_THREAD_ID")
    if not isinstance(value, str) or not THREAD_ID_PATTERN.fullmatch(value) or value in {".", ".."}:
        raise StateIdentityError("a valid CODEX_THREAD_ID is required")
    return value


def _temporary_root(temp_root: str | os.PathLike[str] | None) -> Path:
    candidate = Path(temp_root) if temp_root is not None else Path(tempfile.gettempdir())
    if not candidate.is_absolute():
        raise StatePathError("temporary state root must be absolute")
    if candidate.is_symlink():
        raise StatePathError("temporary state root must not be a symlink")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise StatePathError(f"temporary state root is unavailable: {exc}") from exc
    if not resolved.is_dir():
        raise StatePathError("temporary state root must be a directory")
    system_temp = Path(tempfile.gettempdir()).resolve(strict=True)
    if resolved != system_temp and system_temp not in resolved.parents:
        raise StatePathError("temporary state root must remain inside the OS temporary directory")
    return resolved


def _reject_symlink(path: Path, label: str) -> None:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return
    if stat.S_ISLNK(mode):
        raise StatePathError(f"{label} must not be a symlink")


def _ensure_private_directory(path: Path, label: str) -> None:
    _reject_symlink(path, label)
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        pass
    if not path.is_dir():
        raise StatePathError(f"{label} must be a directory")
    os.chmod(path, 0o700)


def _paths(
    thread_id: str | None,
    temp_root: str | os.PathLike[str] | None,
    *,
    create: bool,
) -> tuple[str, Path, Path, Path]:
    identity = resolve_thread_id(thread_id)
    root = _temporary_root(temp_root)
    dispatch_root = root / STATE_DIRECTORY
    thread_root = dispatch_root / identity
    if create:
        _ensure_private_directory(dispatch_root, "dispatch state root")
        _ensure_private_directory(thread_root, "thread state directory")
    else:
        _reject_symlink(dispatch_root, "dispatch state root")
        _reject_symlink(thread_root, "thread state directory")
    state = thread_root / STATE_FILE
    lock = thread_root / LOCK_FILE
    _reject_symlink(state, "state file")
    _reject_symlink(lock, "state lock")
    return identity, thread_root, state, lock


def state_path(
    thread_id: str | None = None,
    *,
    temp_root: str | os.PathLike[str] | None = None,
) -> Path:
    return _paths(thread_id, temp_root, create=False)[2]


def new_state(
    *,
    thread_id: str | None = None,
    locale: str = "en",
    now: datetime | str | None = None,
) -> dict[str, Any]:
    identity = resolve_thread_id(thread_id)
    if locale not in {"zh", "en"}:
        raise StatePayloadError("locale must be zh or en")
    timestamp = _utc_text(now)
    return {
        "schema_version": SCHEMA_VERSION,
        "root_thread_id": identity,
        "locale": locale,
        "created_at": timestamp,
        "updated_at": timestamp,
        "team_plan_revision": None,
        "units": [],
        "accounting_refs": [],
        "controls": [],
        "pending_takeover": None,
    }


def _serialized_payload(payload: Mapping[str, Any], *, max_bytes: int) -> bytes:
    try:
        encoded = json.dumps(
            payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise StatePayloadError(f"state must be JSON serializable: {exc}") from exc
    if len(encoded) > max_bytes:
        raise StatePayloadError(f"state exceeds {max_bytes} bytes")
    return encoded


def validate_state_payload(
    payload: Any,
    *,
    thread_id: str | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise StatePayloadError("state must be a JSON object")
    _serialized_payload(payload, max_bytes=max_bytes)
    extra = set(payload) - TOP_LEVEL_FIELDS
    missing = TOP_LEVEL_FIELDS - set(payload)
    if extra:
        raise StatePayloadError("state has unsupported fields: " + ", ".join(sorted(extra)))
    if missing:
        raise StatePayloadError("state is missing fields: " + ", ".join(sorted(missing)))
    _reject_forbidden_persisted_fields(payload)
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise StatePayloadError("unsupported state schema_version")
    identity = resolve_thread_id(
        thread_id if thread_id is not None else payload.get("root_thread_id")
    )
    if payload.get("root_thread_id") != identity:
        raise StatePayloadError("root_thread_id does not match CODEX_THREAD_ID")
    if payload.get("locale") not in {"zh", "en"}:
        raise StatePayloadError("locale must be zh or en")
    if not isinstance(payload.get("units"), list):
        raise StatePayloadError("units must be an array")
    if not isinstance(payload.get("accounting_refs"), list):
        raise StatePayloadError("accounting_refs must be an array")
    if not isinstance(payload.get("controls"), list):
        raise StatePayloadError("controls must be an array")
    _validate_units(payload["units"])
    try:
        unique_accounting = _unique_receipt_events(payload["accounting_refs"])
        account_receipt(unique_accounting, materialized_units=payload["units"])
    except ReceiptAccountingError as exc:
        raise StatePayloadError(f"invalid accounting_refs: {exc}") from exc
    if len(unique_accounting) != len(payload["accounting_refs"]):
        raise StatePayloadError("accounting_refs must contain unique stable refs")
    for field in ("created_at", "updated_at"):
        try:
            _parse_timestamp(payload.get(field))
        except (TypeError, ValueError) as exc:
            raise StatePayloadError(f"{field} must be an ISO-8601 timestamp") from exc
    return payload


def _reject_forbidden_persisted_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(key, str) and key.lower() in FORBIDDEN_PERSISTED_KEYS:
                raise StatePayloadError(f"forbidden persisted field: {key}")
            _reject_forbidden_persisted_fields(child)
    elif isinstance(value, list):
        for child in value:
            _reject_forbidden_persisted_fields(child)


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_units(units: list[Any]) -> None:
    task_ids: set[str] = set()
    native_names: set[str] = set()
    agent_ids: set[str] = set()
    by_unit: dict[str, list[dict[str, Any]]] = {}
    for index, record in enumerate(units):
        prefix = f"unit record {index}"
        if not isinstance(record, dict):
            raise StatePayloadError(f"{prefix} must be an object")
        extra = set(record) - UNIT_FIELDS
        missing = UNIT_FIELDS - set(record)
        if extra or missing:
            detail = sorted(extra or missing)
            kind = "unsupported" if extra else "missing"
            raise StatePayloadError(f"{prefix} has {kind} fields: {', '.join(detail)}")
        for field in ("unit_id", "task_id", "native_task_name", "role", "model_lane"):
            if not _nonempty(record[field]):
                raise StatePayloadError(f"{prefix} has invalid {field}")
        if not isinstance(record["attempt"], int) or isinstance(record["attempt"], bool):
            raise StatePayloadError(f"{prefix} has invalid attempt")
        if record["attempt"] not in {1, 2}:
            raise StatePayloadError(f"{prefix} attempt must be 1 or 2")
        if record["task_id"] in task_ids or record["native_task_name"] in native_names:
            raise StatePayloadError(f"{prefix} duplicates task or native task identity")
        task_ids.add(record["task_id"])
        native_names.add(record["native_task_name"])
        agent_id = record["agent_id"]
        if agent_id is not None and not _nonempty(agent_id):
            raise StatePayloadError(f"{prefix} has invalid agent_id")
        if isinstance(agent_id, str):
            if agent_id in agent_ids:
                raise StatePayloadError(f"{prefix} duplicates agent_id")
            agent_ids.add(agent_id)
        state = record["control_state"]
        if state not in CONTROL_STATES:
            raise StatePayloadError(f"{prefix} has invalid control_state")
        if state in {"PLANNED", "SPAWN_PENDING"} and agent_id is not None:
            raise StatePayloadError(f"{prefix} must not bind agent_id before RUNNING")
        if state in {"RUNNING", "INTERRUPTED", "COMPLETED", "FAILED", "CLOSED"} and agent_id is None:
            raise StatePayloadError(f"{prefix} requires agent_id in {state}")
        if not isinstance(record["responsibility"], dict) or not isinstance(record["authority"], dict):
            raise StatePayloadError(f"{prefix} requires compact responsibility and authority objects")
        for field in ("writer", "adopted", "accepted"):
            if not isinstance(record[field], bool):
                raise StatePayloadError(f"{prefix} {field} must be boolean")
        if record["adopted"] and not record["accepted"]:
            raise StatePayloadError(f"{prefix} adopted=true requires accepted evidence")
        if record["adopted"] and state not in {"COMPLETED", "CLOSED"}:
            raise StatePayloadError(f"{prefix} cannot be adopted before completion")
        if record["accepted"] and state not in {"COMPLETED", "CLOSED"}:
            raise StatePayloadError(f"{prefix} accepted evidence requires completion")
        if state == "UNKNOWN":
            if record["failure_origin"] != "runtime_ambiguous":
                raise StatePayloadError(f"{prefix} UNKNOWN requires runtime_ambiguous")
        elif record["failure_origin"] == "runtime_ambiguous":
            raise StatePayloadError(f"{prefix} runtime_ambiguous requires UNKNOWN")
        if record["failure_origin"] not in FAILURE_ORIGINS:
            raise StatePayloadError(f"{prefix} has invalid failure_origin")
        if record["blocker"] not in TASK_BLOCKERS:
            raise StatePayloadError(f"{prefix} has invalid blocker")
        if state == "FAILED" and record["failure_origin"] == "none":
            raise StatePayloadError(f"{prefix} FAILED requires a failure_origin")
        if state not in {"FAILED", "UNKNOWN"} and record["failure_origin"] != "none":
            raise StatePayloadError(f"{prefix} non-failure state requires failure_origin=none")
        if state not in {"FAILED", "UNKNOWN"} and record["blocker"] != "none":
            raise StatePayloadError(f"{prefix} blocker belongs only on FAILED or UNKNOWN")
        by_unit.setdefault(record["unit_id"], []).append(record)
    for unit_id, records in by_unit.items():
        ordered = sorted(records, key=lambda item: item["attempt"])
        if [item["attempt"] for item in ordered] != list(range(1, len(ordered) + 1)):
            raise StatePayloadError(f"{unit_id} attempts must be contiguous from 1")
        if len(ordered) == 2 and ordered[0]["control_state"] != "FAILED":
            raise StatePayloadError(f"{unit_id} retry requires the first attempt to be FAILED")


def _parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise TypeError(value)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(value)
    return parsed.astimezone(UTC)


@contextmanager
def state_lock(
    thread_id: str | None = None,
    *,
    temp_root: str | os.PathLike[str] | None = None,
    blocking: bool = True,
) -> Iterator[None]:
    _, _, _, lock_path = _paths(thread_id, temp_root, create=True)
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(lock_path, flags, 0o600)
    except OSError as exc:
        raise StateLockError(f"cannot open state lock: {exc}") from exc
    locked = False
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(descriptor, 0o600)
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise StateLockError("state lock must be a regular file")
        try:
            if os.name == "nt":
                import msvcrt

                os.lseek(descriptor, 0, os.SEEK_SET)
                operation = msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK
                msvcrt.locking(descriptor, operation, 1)
            else:
                import fcntl

                operation = fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB)
                fcntl.flock(descriptor, operation)
            locked = True
        except OSError as exc:
            if exc.errno in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                raise StateLockError("state is already locked") from exc
            raise StateLockError(f"cannot acquire state lock: {exc}") from exc
        yield
    finally:
        try:
            if locked:
                if os.name == "nt":
                    import msvcrt

                    os.lseek(descriptor, 0, os.SEEK_SET)
                    msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def _write_unlocked(path: Path, encoded: bytes) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=".active.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
        if os.name != "nt":
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


def write_state(
    payload: Mapping[str, Any],
    *,
    thread_id: str | None = None,
    temp_root: str | os.PathLike[str] | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> Path:
    identity = resolve_thread_id(
        thread_id if thread_id is not None else payload.get("root_thread_id")
    )
    validate_state_payload(payload, thread_id=identity, max_bytes=max_bytes)
    encoded = _serialized_payload(payload, max_bytes=max_bytes)
    with state_lock(identity, temp_root=temp_root):
        _, _, path, _ = _paths(identity, temp_root, create=True)
        _write_unlocked(path, encoded)
    return path


def load_state(
    thread_id: str | None = None,
    *,
    temp_root: str | os.PathLike[str] | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> dict[str, Any] | None:
    identity, _, path, _ = _paths(thread_id, temp_root, create=False)
    if not path.exists():
        return None
    mode = path.lstat().st_mode
    if not stat.S_ISREG(mode) or mode & 0o077:
        raise StateCorruptError("state file must be a private regular file")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise StateCorruptError(f"cannot read state: {exc}") from exc
    if len(raw) > max_bytes:
        raise StateCorruptError(f"state exceeds {max_bytes} bytes")
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StateCorruptError(f"state contains invalid JSON: {exc}") from exc
    try:
        validate_state_payload(payload, thread_id=identity, max_bytes=max_bytes)
    except (StateIdentityError, StatePayloadError) as exc:
        raise StateCorruptError(str(exc)) from exc
    return payload


def _touch(payload: dict[str, Any], now: datetime | str | None = None) -> None:
    payload["updated_at"] = _utc_text(now)


def prepare_spawn(
    payload: Mapping[str, Any],
    unit: Mapping[str, Any],
    *,
    temp_root: str | os.PathLike[str] | None = None,
    now: datetime | str | None = None,
) -> dict[str, Any]:
    """Persist SPAWN_PENDING before the caller invokes the native Host."""
    supplied = copy.deepcopy(dict(payload))
    validate_state_payload(supplied)
    identity = resolve_thread_id(supplied["root_thread_id"])
    record = copy.deepcopy(dict(unit))
    if record.get("control_state") != "SPAWN_PENDING" or record.get("agent_id") is not None:
        raise StatePayloadError("a prepared spawn must be SPAWN_PENDING without agent_id")
    with state_lock(identity, temp_root=temp_root):
        current_state = load_state(identity, temp_root=temp_root)
        prepared = copy.deepcopy(current_state if current_state is not None else supplied)
        same_unit = [
            item for item in prepared["units"] if item["unit_id"] == record.get("unit_id")
        ]
        if same_unit:
            current = max(same_unit, key=lambda item: item["attempt"])
            if current["control_state"] != "FAILED" or record.get("attempt") != current["attempt"] + 1:
                raise StatePayloadError("cannot spawn a replacement for an unresolved unit")
        if record.get("writer") is True and any(
            item["writer"] is True and item["control_state"] in ACTIVE_STATES
            for item in _latest_units(prepared)
        ):
            raise StatePayloadError("cannot prepare a second active writer")
        prepared["units"].append(record)
        _touch(prepared, now)
        validate_state_payload(prepared)
        encoded = _serialized_payload(prepared, max_bytes=DEFAULT_MAX_BYTES)
        _, _, path, _ = _paths(identity, temp_root, create=True)
        _write_unlocked(path, encoded)
        return prepared


def _quarantine(record: dict[str, Any], reason: str) -> None:
    record["control_state"] = "UNKNOWN"
    record["failure_origin"] = "runtime_ambiguous"
    record["blocker"] = "investigation"
    record["adopted"] = False
    record["accepted"] = False
    record["quarantine_reason"] = reason


def _matching_children(record: Mapping[str, Any], children: Sequence[Mapping[str, Any]]) -> tuple[list[Mapping[str, Any]], bool]:
    by_name = [child for child in children if child.get("native_task_name") == record["native_task_name"]]
    agent_id = record.get("agent_id")
    by_agent = [child for child in children if agent_id is not None and child.get("agent_id") == agent_id]
    identity_conflict = False
    if by_name and agent_id is not None and any(child.get("agent_id") != agent_id for child in by_name):
        identity_conflict = True
    if by_agent and any(child.get("native_task_name") != record["native_task_name"] for child in by_agent):
        identity_conflict = True
    matches: list[Mapping[str, Any]] = []
    for child in [*by_name, *by_agent]:
        if child not in matches:
            matches.append(child)
    return matches, identity_conflict


def reconcile_state(
    payload: Mapping[str, Any],
    host_observation: Mapping[str, Any],
    *,
    now: datetime | str | None = None,
) -> dict[str, Any]:
    """Reconcile once against one supplied, already-observed Host snapshot."""
    state = copy.deepcopy(dict(payload))
    validate_state_payload(state)
    if not isinstance(host_observation, Mapping):
        raise StatePayloadError("host observation must be an object")
    complete = host_observation.get("complete")
    children = host_observation.get("children")
    if not isinstance(complete, bool) or not isinstance(children, list):
        raise StatePayloadError("host observation requires complete boolean and children array")
    if not all(isinstance(child, Mapping) for child in children):
        raise StatePayloadError("host observation children must be objects")

    changed = False
    for record in state["units"]:
        if record["control_state"] in {"PLANNED", "FAILED", "CLOSED"}:
            continue
        before = copy.deepcopy(record)
        matches, conflict = _matching_children(record, children)
        if conflict or len(matches) > 1:
            _quarantine(record, "native_identity_conflict" if conflict else "ambiguous_native_identity")
            changed = changed or record != before
            continue
        if not matches:
            if complete and record["control_state"] in ACTIVE_STATES:
                _quarantine(record, "native_identity_absent")
                changed = changed or record != before
            continue
        child = matches[0]
        for field in ("unit_id", "task_id", "attempt"):
            if field in child and child[field] != record[field]:
                _quarantine(record, "native_identity_conflict")
                changed = changed or record != before
                break
        else:
            agent_id = child.get("agent_id")
            host_state = child.get("state")
            if not _nonempty(agent_id) or host_state not in HOST_STATE_MAP:
                _quarantine(record, "invalid_native_observation")
                changed = changed or record != before
                continue
            mapped = HOST_STATE_MAP[host_state]
            if mapped == "SPAWN_PENDING":
                mapped = "RUNNING"
            record["agent_id"] = agent_id
            record["control_state"] = mapped
            record["quarantine_reason"] = None
            record["failure_origin"] = (
                child.get("failure_origin", "tool_failure") if mapped == "FAILED" else "none"
            )
            if mapped != "FAILED":
                record["blocker"] = "none"
            changed = changed or record != before
    if changed:
        _touch(state, now)
    validate_state_payload(state)
    return state


def _latest_units(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for record in payload["units"]:
        unit_id = record["unit_id"]
        if unit_id not in latest:
            order.append(unit_id)
        if unit_id not in latest or record["attempt"] > latest[unit_id]["attempt"]:
            latest[unit_id] = record
    return [latest[unit_id] for unit_id in order]


def status_snapshot(
    payload: Mapping[str, Any],
    host_observation: Mapping[str, Any],
    *,
    unit_id: str | None = None,
) -> dict[str, Any]:
    reconciled = reconcile_state(payload, host_observation)
    records = _latest_units(reconciled)
    if unit_id is not None:
        records = [record for record in records if record["unit_id"] == unit_id]
        if not records:
            raise TargetResolutionError(f"unit {unit_id!r} not found")
    return {
        "units": [
            {
                "unit_id": record["unit_id"],
                "role": record["role"],
                "control_state": record["control_state"],
                "writer": record["writer"],
                "blocker": record["blocker"],
            }
            for record in records
        ],
        "reconciled_state": reconciled,
    }


def _eligible_for(action: str, record: Mapping[str, Any]) -> bool:
    state = record["control_state"]
    if action == "steer":
        return state == "RUNNING"
    if action == "takeover":
        return not record["adopted"]
    if action == "dispatch_resume":
        return state in ACTIVE_STATES or (state == "COMPLETED" and not record["adopted"])
    raise StatePayloadError(f"unsupported control action: {action}")


def resolve_control_target(
    payload: Mapping[str, Any],
    *,
    unit_id: str | None = None,
    action: str,
) -> dict[str, Any]:
    validate_state_payload(dict(payload))
    records = _latest_units(payload)
    if unit_id is not None:
        exact = [record for record in records if record["unit_id"] == unit_id]
        if not exact:
            return {"status": "none", "candidates": []}
        record = exact[0]
        if not _eligible_for(action, record):
            reason = (
                "INTERRUPTED is not Resume"
                if action == "steer" and record["control_state"] == "INTERRUPTED"
                else f"{record['control_state']} is not eligible for {action}"
            )
            return {"status": "ineligible", "unit": record, "reason": reason}
        return {"status": "resolved", "unit": record}
    eligible = [record for record in records if _eligible_for(action, record)]
    if not eligible:
        return {"status": "none", "candidates": []}
    if len(eligible) > 1:
        return {"status": "ambiguous", "candidates": sorted(record["unit_id"] for record in eligible)}
    return {"status": "resolved", "unit": eligible[0]}


def takeover_target(
    payload: Mapping[str, Any], *, unit_id: str | None = None
) -> dict[str, Any]:
    resolution = resolve_control_target(payload, unit_id=unit_id, action="takeover")
    if resolution["status"] != "resolved":
        return resolution
    record = resolution["unit"]
    allowed = not record["writer"] or record["control_state"] in NON_ACTIVE_STATES
    return {
        **resolution,
        "conflicting_write_allowed": allowed,
        "reason": None if allowed else "previous writer is not definitively non-active",
    }


def resume_dispatch(
    payload: Mapping[str, Any], *, unit_id: str | None = None
) -> dict[str, Any]:
    resolution = resolve_control_target(payload, unit_id=unit_id, action="dispatch_resume")
    if resolution["status"] != "resolved":
        return {**resolution, "operation": None}
    record = resolution["unit"]
    if record["control_state"] == "UNKNOWN":
        return {"status": "blocked", "operation": None, "reason": "native identity is UNKNOWN"}
    operations = {
        "INTERRUPTED": "resume_existing_child",
        "RUNNING": "observe_existing_child",
        "SPAWN_PENDING": "reconcile_pending_spawn",
        "COMPLETED": "adopt_existing_result",
    }
    binding_fields = (
        "unit_id",
        "task_id",
        "attempt",
        "agent_id",
        "role",
        "responsibility",
        "authority",
    )
    return {
        "status": "resolved",
        "operation": operations[record["control_state"]],
        "binding": {field: copy.deepcopy(record[field]) for field in binding_fields},
        "accounting_delta": {"child": 0, "retry": 0, "followup": 0, "pass": 0, "rework": 0},
    }


def remove_state(
    thread_id: str | None = None,
    *,
    temp_root: str | os.PathLike[str] | None = None,
) -> bool:
    identity = resolve_thread_id(thread_id)
    with state_lock(identity, temp_root=temp_root):
        _, _, path, _ = _paths(identity, temp_root, create=True)
        if not path.exists():
            return False
        payload = load_state(identity, temp_root=temp_root)
        assert payload is not None
        if _has_unresolved_work(payload):
            raise StatePayloadError("cannot remove state with unresolved work")
        _reject_symlink(path, "state file")
        path.unlink()
        return True


def is_stale(
    payload: Mapping[str, Any],
    *,
    now: datetime | str | None = None,
    stale_after: timedelta = DEFAULT_STALE_AFTER,
) -> bool:
    current = _parse_timestamp(_utc_text(now))
    return current - _parse_timestamp(payload.get("updated_at")) > stale_after


def _has_unresolved_work(payload: Mapping[str, Any]) -> bool:
    return payload.get("pending_takeover") is not None or any(
        record["control_state"] not in NON_ACTIVE_STATES for record in _latest_units(payload)
    )


def cleanup_stale_states(
    *,
    temp_root: str | os.PathLike[str] | None = None,
    active_thread_id: str | None = None,
    now: datetime | str | None = None,
    stale_after: timedelta = DEFAULT_STALE_AFTER,
    can_discard_active: Callable[[Mapping[str, Any]], bool] | None = None,
) -> dict[str, list[str]]:
    root = _temporary_root(temp_root) / STATE_DIRECTORY
    report = {
        "removed": [],
        "retained_active": [],
        "current": [],
        "fresh": [],
        "corrupt": [],
        "unsafe": [],
    }
    _reject_symlink(root, "dispatch state root")
    if not root.exists():
        return report
    for entry in sorted(root.iterdir(), key=lambda item: item.name):
        try:
            identity = resolve_thread_id(entry.name)
            _reject_symlink(entry, "thread state directory")
            if not entry.is_dir():
                raise StatePathError("thread state entry must be a directory")
        except (StateIdentityError, StatePathError):
            report["unsafe"].append(entry.name)
            continue
        if active_thread_id is not None and identity == resolve_thread_id(active_thread_id):
            report["current"].append(identity)
            continue
        try:
            payload = load_state(identity, temp_root=temp_root)
        except StateCorruptError:
            report["corrupt"].append(identity)
            continue
        if payload is None or not is_stale(payload, now=now, stale_after=stale_after):
            report["fresh"].append(identity)
            continue
        active = _has_unresolved_work(payload)
        active_discard_approved = bool(
            active and can_discard_active is not None and can_discard_active(payload)
        )
        if active and not active_discard_approved:
            report["retained_active"].append(identity)
            continue
        with state_lock(identity, temp_root=temp_root):
            current = load_state(identity, temp_root=temp_root)
            if current is None:
                continue
            if not is_stale(current, now=now, stale_after=stale_after):
                report["fresh"].append(identity)
                continue
            current_active = _has_unresolved_work(current)
            if current_active and (not active_discard_approved or current != payload):
                report["retained_active"].append(identity)
                continue
            _, _, path, _ = _paths(identity, temp_root, create=True)
            _reject_symlink(path, "state file")
            path.unlink()
            report["removed"].append(identity)
    return report


RECEIPT_EVENT_KINDS = {
    "attempt",
    "followup",
    "retry",
    "semantic_rework",
    "reviewer_attempt",
    "review_round",
    "recovery",
    "control",
}
PUBLIC_ACTIVITIES = {"read", "investigate", "execute", "decide", "review"}
MATERIALIZED_EVENT_KINDS = {"attempt", "followup", "reviewer_attempt"}
REVIEW_VERDICTS = {
    "passed",
    "rework_required",
    "redesign_required",
    "insufficient_evidence",
}


def _unique_receipt_events(events: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    by_ref: dict[str, dict[str, Any]] = {}
    for index, event in enumerate(events):
        if not isinstance(event, Mapping):
            raise ReceiptAccountingError(f"event {index} must be an object")
        item = dict(event)
        ref = item.get("ref")
        kind = item.get("kind")
        if not _nonempty(ref):
            raise ReceiptAccountingError(f"event {index} requires a stable ref")
        if kind not in RECEIPT_EVENT_KINDS:
            raise ReceiptAccountingError(f"event {ref} has unsupported kind")
        prior = by_ref.get(ref)
        if prior is not None:
            if prior != item:
                raise ReceiptAccountingError(f"conflicting event ref: {ref}")
            continue
        by_ref[ref] = item
        unique.append(item)
    return unique


def _materialized_unit_keys(units: Sequence[Mapping[str, Any]]) -> set[tuple[str, int, str]]:
    return {
        (record["unit_id"], record["attempt"], record["agent_id"])
        for record in units
        if _nonempty(record.get("agent_id"))
    }


def account_receipt(
    events: Sequence[Mapping[str, Any]],
    *,
    materialized_units: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Derive receipt axes from stable materialization refs, never mutable counters."""
    unique = _unique_receipt_events(events)
    dispatch: list[dict[str, Any]] = []
    dispatch_by_key: dict[tuple[str | None, str], dict[str, Any]] = {}
    controls: list[dict[str, Any]] = []
    controls_by_action: dict[str, dict[str, Any]] = {}
    focused_followups = 0
    retries = 0
    semantic_reworks = 0
    reviewer_attempts = 0
    review_rounds = 0
    review_verdict: str | None = None
    recoveries = 0

    materialized_keys = (
        _materialized_unit_keys(materialized_units) if materialized_units is not None else None
    )
    unit_attempts = {
        (record.get("unit_id"), record.get("attempt")): record
        for record in materialized_units or []
    }
    attempt_keys: set[tuple[str, int, str]] = set()
    followup_keys: set[tuple[str, int, str]] = set()
    retry_keys: set[tuple[str, int, str]] = set()
    for event in unique:
        kind = event["kind"]
        if kind in MATERIALIZED_EVENT_KINDS:
            unit_id = event.get("unit_id")
            attempt = event.get("attempt")
            agent_id = event.get("agent_id")
            if (
                not _nonempty(unit_id)
                or not isinstance(attempt, int)
                or isinstance(attempt, bool)
                or not _nonempty(agent_id)
            ):
                raise ReceiptAccountingError(
                    f"materialized event {event['ref']} requires unit, attempt, and child identity"
                )
            if materialized_keys is None or (unit_id, attempt, agent_id) not in materialized_keys:
                raise ReceiptAccountingError(
                    f"materialized child for event {event['ref']} is unavailable"
                )
            identity_key = (unit_id, attempt, agent_id)
            seen = followup_keys if kind == "followup" else attempt_keys
            if identity_key in seen:
                raise ReceiptAccountingError(
                    f"duplicate materialized {kind} for event {event['ref']}"
                )
            seen.add(identity_key)
            model_lane = event.get("model_lane")
            activity = event.get("activity")
            if activity not in PUBLIC_ACTIVITIES:
                raise ReceiptAccountingError(f"materialized event {event['ref']} lacks public activity")
            if model_lane is not None:
                if not _nonempty(model_lane) or event.get("model_evidence_source") not in {"native", "both"}:
                    raise ReceiptAccountingError(
                        f"materialized event {event['ref']} lacks observed model evidence"
                    )
            key = (model_lane, activity)
            aggregate = dispatch_by_key.get(key)
            if aggregate is None:
                aggregate = {"model_lane": model_lane, "activity": activity, "count": 0}
                dispatch_by_key[key] = aggregate
                dispatch.append(aggregate)
            aggregate["count"] += 1
            if kind == "followup":
                focused_followups += 1
            if kind == "reviewer_attempt":
                reviewer_attempts += 1
        elif kind == "retry":
            unit_id = event.get("unit_id")
            attempt = event.get("attempt")
            agent_id = event.get("agent_id")
            retry_key = (unit_id, attempt, agent_id)
            prior = unit_attempts.get((unit_id, 1))
            if (
                attempt != 2
                or not _nonempty(unit_id)
                or not _nonempty(agent_id)
                or materialized_keys is None
                or retry_key not in materialized_keys
                or prior is None
                or prior.get("control_state") != "FAILED"
            ):
                raise ReceiptAccountingError(
                    f"retry event {event['ref']} requires a failed first attempt and materialized replacement"
                )
            if retry_key in retry_keys:
                raise ReceiptAccountingError(f"duplicate retry for event {event['ref']}")
            retry_keys.add(retry_key)
            retries += 1
        elif kind == "semantic_rework":
            semantic_reworks += 1
        elif kind == "review_round":
            verdict = event.get("verdict")
            if verdict not in REVIEW_VERDICTS:
                raise ReceiptAccountingError(f"review event {event['ref']} has invalid verdict")
            review_rounds += 1
            review_verdict = verdict
        elif kind == "recovery":
            if not _nonempty(event.get("action")):
                raise ReceiptAccountingError(f"recovery event {event['ref']} requires action")
            recoveries += 1
        elif kind == "control":
            action = event.get("action")
            if action not in {"Status", "Steer", "Takeover"}:
                raise ReceiptAccountingError(f"control event {event['ref']} has invalid action")
            aggregate = controls_by_action.get(action)
            if aggregate is None:
                aggregate = {"action": action, "count": 0}
                controls_by_action[action] = aggregate
                controls.append(aggregate)
            aggregate["count"] += 1

    return {
        "dispatch": dispatch,
        "controls": controls,
        "focused_followups": focused_followups,
        "retries": retries,
        "semantic_reworks": semantic_reworks,
        "reviewer_attempts": reviewer_attempts,
        "review": {
            "rounds": review_rounds,
            "reworks": semantic_reworks,
            "verdict": review_verdict,
        },
        "recoveries": recoveries,
        "zero_child": not dispatch,
    }


def persist_receipt_events(
    thread_id: str | None,
    events: Sequence[Mapping[str, Any]],
    *,
    temp_root: str | os.PathLike[str] | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
    now: datetime | str | None = None,
) -> dict[str, Any]:
    """Atomically persist unique receipt events in the active root-thread capsule."""
    incoming = _unique_receipt_events(events)
    identity = resolve_thread_id(thread_id)
    with state_lock(identity, temp_root=temp_root):
        payload = load_state(identity, temp_root=temp_root, max_bytes=max_bytes)
        if payload is None:
            raise ReceiptAccountingError("active dispatch state is unavailable")
        merged = _unique_receipt_events([*payload["accounting_refs"], *incoming])
        account_receipt(merged, materialized_units=payload["units"])
        payload["accounting_refs"] = merged
        _touch(payload, now)
        validate_state_payload(payload, thread_id=identity, max_bytes=max_bytes)
        encoded = _serialized_payload(payload, max_bytes=max_bytes)
        _, _, path, _ = _paths(identity, temp_root, create=True)
        _write_unlocked(path, encoded)
        return payload


ACTIVITY_LABELS = {
    "zh": {
        "read": "读取",
        "investigate": "调研",
        "execute": "执行",
        "decide": "决策",
        "review": "验收",
    },
    "en": {
        "read": "Read",
        "investigate": "Investigate",
        "execute": "Execute",
        "decide": "Decide",
        "review": "Review",
    },
}
VERDICT_LABELS = {
    "zh": {
        "passed": "通过",
        "rework_required": "需返工",
        "redesign_required": "需重新设计",
        "insufficient_evidence": "证据不足",
    },
    "en": {
        "passed": "passed",
        "rework_required": "rework required",
        "redesign_required": "redesign required",
        "insufficient_evidence": "insufficient evidence",
    },
}


def format_receipt(summary: Mapping[str, Any], *, locale: str) -> str:
    if locale not in {"zh", "en"}:
        raise ReceiptAccountingError("receipt locale must be zh or en")
    if summary.get("zero_child"):
        return (
            "编排: 未调度子代理\n验收: 未触发"
            if locale == "zh"
            else "Dispatch: no Subagents dispatched\nReview: not triggered"
        )

    activity_labels = ACTIVITY_LABELS[locale]
    dispatch_parts = []
    for item in summary["dispatch"]:
        count = item["count"]
        suffix = f"×{count}" if count > 1 else ""
        model = f"{item['model_lane']} " if item["model_lane"] is not None else ""
        dispatch_parts.append(f"{model}{activity_labels[item['activity']]}{suffix}")
    lines = [("编排: " if locale == "zh" else "Dispatch: ") + " · ".join(dispatch_parts)]

    controls = summary.get("controls", [])
    if controls:
        parts = [f"{item['action']}×{item['count']}" for item in controls]
        lines.append(("控制: " if locale == "zh" else "Control: ") + " · ".join(parts))

    review = summary["review"]
    rounds = review["rounds"]
    if rounds == 0:
        lines.append("验收: 未触发" if locale == "zh" else "Review: not triggered")
    elif locale == "zh":
        parts = [f"{rounds}轮"]
        if review["reworks"]:
            parts.append(f"返工{review['reworks']}次")
        parts.append(VERDICT_LABELS[locale][review["verdict"]])
        lines.append("验收: " + " · ".join(parts))
    else:
        parts = [f"{rounds} {'round' if rounds == 1 else 'rounds'}"]
        if review["reworks"]:
            parts.append(f"rework×{review['reworks']}")
        parts.append(VERDICT_LABELS[locale][review["verdict"]])
        lines.append("Review: " + " · ".join(parts))

    recovery_parts = []
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
    return "\n".join(lines)
