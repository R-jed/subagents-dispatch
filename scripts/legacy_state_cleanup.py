#!/usr/bin/env python3
"""Ownership-safe cleanup for terminal V3 orchestration capsules.

This compatibility helper understands only the minimum V3 state needed to decide
whether a stale capsule is terminal. It never participates in V4 routing,
lifecycle, acceptance, or receipt accounting.
"""

from __future__ import annotations

import json
import os
import stat
from datetime import datetime, timedelta
from typing import Any, Mapping

import state_storage as storage


LEGACY_SCHEMA_VERSION = "1.0"
DEFAULT_MAX_BYTES = 64 * 1024
DEFAULT_STALE_AFTER = timedelta(days=7)
LEGACY_NON_ACTIVE_STATES = {"COMPLETED", "FAILED", "CLOSED"}

StateError = storage.StateError
StateIdentityError = storage.StateIdentityError
StatePathError = storage.StatePathError
StateLockError = storage.StateLockError


class LegacyStateCorruptError(StateError):
    """A V3 capsule cannot be classified safely."""


def resolve_thread_id(thread_id: str | None = None) -> str:
    return storage.resolve_thread_id(thread_id)


def _read_payload(
    thread_id: str,
    *,
    temp_root: str | os.PathLike[str] | None,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> dict[str, Any] | None:
    identity, _, path, _ = storage._paths(thread_id, temp_root, create=False)
    if not path.exists():
        return None
    mode = path.lstat().st_mode
    if not stat.S_ISREG(mode):
        raise LegacyStateCorruptError("legacy state file must be a regular file")
    if os.name != "nt" and mode & 0o077:
        raise LegacyStateCorruptError("legacy state file must be private")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise LegacyStateCorruptError(f"cannot read legacy state: {exc}") from exc
    if len(raw) > max_bytes:
        raise LegacyStateCorruptError(f"legacy state exceeds {max_bytes} bytes")
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LegacyStateCorruptError(f"legacy state contains invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise LegacyStateCorruptError("legacy state must be an object")
    if payload.get("schema_version") != LEGACY_SCHEMA_VERSION:
        return payload
    storage._reject_forbidden_persisted_fields(payload)
    if payload.get("root_thread_id") != identity:
        raise LegacyStateCorruptError("legacy root_thread_id does not match state directory")
    try:
        storage._parse_timestamp(payload.get("updated_at"))
    except (TypeError, ValueError) as exc:
        raise LegacyStateCorruptError("legacy updated_at is invalid") from exc
    units = payload.get("units")
    if not isinstance(units, list):
        raise LegacyStateCorruptError("legacy units must be an array")
    for index, unit in enumerate(units):
        if not isinstance(unit, Mapping):
            raise LegacyStateCorruptError(f"legacy unit {index} must be an object")
        if not isinstance(unit.get("unit_id"), str) or not unit["unit_id"]:
            raise LegacyStateCorruptError(f"legacy unit {index} has invalid unit_id")
        attempt = unit.get("attempt")
        if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt < 1:
            raise LegacyStateCorruptError(f"legacy unit {index} has invalid attempt")
        if not isinstance(unit.get("control_state"), str):
            raise LegacyStateCorruptError(f"legacy unit {index} has invalid control_state")
    pending = payload.get("pending_takeover")
    if pending is not None and not isinstance(pending, Mapping):
        raise LegacyStateCorruptError("legacy pending_takeover is malformed")
    return payload


def _is_legacy(payload: Mapping[str, Any]) -> bool:
    return payload.get("schema_version") == LEGACY_SCHEMA_VERSION


def _latest_units(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    latest: dict[str, Mapping[str, Any]] = {}
    for record in payload.get("units", []):
        unit_id = str(record["unit_id"])
        current = latest.get(unit_id)
        if current is None or int(record["attempt"]) > int(current["attempt"]):
            latest[unit_id] = record
    return list(latest.values())


def _has_unresolved_work(payload: Mapping[str, Any]) -> bool:
    return payload.get("pending_takeover") is not None or any(
        record.get("control_state") not in LEGACY_NON_ACTIVE_STATES
        for record in _latest_units(payload)
    )


def _is_stale(
    payload: Mapping[str, Any],
    *,
    now: datetime | str | None,
    stale_after: timedelta,
) -> bool:
    current = storage._parse_timestamp(storage._utc_text(now))
    updated = storage._parse_timestamp(payload.get("updated_at"))
    return current - updated > stale_after


def cleanup_stale_states(
    *,
    temp_root: str | os.PathLike[str] | None = None,
    active_thread_id: str | None = None,
    now: datetime | str | None = None,
    stale_after: timedelta = DEFAULT_STALE_AFTER,
) -> dict[str, list[str]]:
    root = storage._temporary_root(temp_root) / storage.STATE_DIRECTORY
    report = {
        "removed": [],
        "retained_active": [],
        "current": [],
        "fresh": [],
        "corrupt": [],
        "unsafe": [],
        "nonlegacy": [],
    }
    storage._reject_symlink(root, "dispatch state root")
    if not root.exists():
        return report
    active_identity = (
        storage.resolve_thread_id(active_thread_id) if active_thread_id is not None else None
    )
    for entry in sorted(root.iterdir(), key=lambda item: item.name):
        try:
            identity = storage.resolve_thread_id(entry.name)
            storage._reject_symlink(entry, "thread state directory")
            if not entry.is_dir():
                raise storage.StatePathError("thread state entry must be a directory")
        except (storage.StateIdentityError, storage.StatePathError):
            report["unsafe"].append(entry.name)
            continue
        if active_identity is not None and identity == active_identity:
            report["current"].append(identity)
            continue
        try:
            payload = _read_payload(identity, temp_root=temp_root)
        except (LegacyStateCorruptError, storage.StateError):
            report["corrupt"].append(identity)
            continue
        if payload is None:
            report["fresh"].append(identity)
            continue
        if not _is_legacy(payload):
            report["nonlegacy"].append(identity)
            continue
        if not _is_stale(payload, now=now, stale_after=stale_after):
            report["fresh"].append(identity)
            continue
        if _has_unresolved_work(payload):
            report["retained_active"].append(identity)
            continue
        with storage.state_lock(identity, temp_root=temp_root):
            try:
                current = _read_payload(identity, temp_root=temp_root)
            except (LegacyStateCorruptError, storage.StateError):
                report["corrupt"].append(identity)
                continue
            if current is None:
                continue
            if not _is_legacy(current):
                report["nonlegacy"].append(identity)
                continue
            if current != payload or not _is_stale(
                current, now=now, stale_after=stale_after
            ):
                report["fresh"].append(identity)
                continue
            if _has_unresolved_work(current):
                report["retained_active"].append(identity)
                continue
            _, _, path, _ = storage._paths(identity, temp_root, create=False)
            storage._reject_symlink(path, "state file")
            path.unlink()
            report["removed"].append(identity)
    return report
