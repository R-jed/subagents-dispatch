#!/usr/bin/env python3
"""Schema-neutral private state storage primitives.

This module owns only thread identity, temporary-path safety, bounded persisted
content checks, private locking, timestamps, and atomic file replacement. It
contains no orchestration schema, lifecycle, routing, receipt, or control logic.
"""

from __future__ import annotations

import errno
import os
import re
import stat
import tempfile
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator, Mapping


STATE_DIRECTORY = "subagents-dispatch"
STATE_FILE = "active.json"
LOCK_FILE = "active.lock"
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


class StateError(RuntimeError):
    """Base error for bounded local state storage."""


class StateIdentityError(StateError):
    """The Host did not provide a safe root-thread identity."""


class StatePathError(StateError):
    """The state path is outside the safe temporary boundary."""


class StatePayloadError(StateError):
    """Persisted state content is invalid or unsafe."""


class StateCorruptError(StateError):
    """Existing state cannot be trusted."""


class StateLockError(StateError):
    """The state lock cannot be acquired safely."""


def _utc_text(now: datetime | str | None = None) -> str:
    if isinstance(now, str):
        return now
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return current.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise TypeError(value)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(value)
    return parsed.astimezone(UTC)


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
    if os.name != "nt":
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


def _reject_forbidden_persisted_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(key, str) and key.lower() in FORBIDDEN_PERSISTED_KEYS:
                raise StatePayloadError(f"forbidden persisted field: {key}")
            _reject_forbidden_persisted_fields(child)
    elif isinstance(value, list):
        for child in value:
            _reject_forbidden_persisted_fields(child)


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
        if os.name != "nt" and hasattr(os, "fchmod"):
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
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".active.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        if os.name != "nt" and hasattr(os, "fchmod"):
            os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if os.name != "nt":
            os.chmod(path, 0o600)
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)
