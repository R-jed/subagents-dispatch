"""Crash-safe semantic ownership for one calibration Marketplace table."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import tomllib
from typing import Any, Callable, NoReturn


STATES = {"PREPARED", "APPLIED", "COMMITTED", "CLEANUP_PENDING", "CLEANED"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _crash_at(boundary: str) -> None:
    if os.environ.get("SUBAGENTS_DISPATCH_CALIBRATION_CRASH_AT") == boundary:
        os._exit(86)


def _fail(message: str) -> NoReturn:
    raise SystemExit(f"ERROR: {message}")


def _semantic_value(data: dict[str, Any], semantic_path: list[str]) -> Any:
    return data.get(semantic_path[0], {}).get(semantic_path[1])


def _read_config(path: Path) -> tuple[bytes, dict[str, Any], tuple[int, int]]:
    if path.is_symlink():
        _fail(f"refusing symlinked shared config: {path}")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        _fail(f"could not open shared config {path}: {exc}")
    try:
        opened = os.fstat(fd)
        linked = os.stat(path, follow_symlinks=False)
        if not os.path.isfile(path) or (opened.st_dev, opened.st_ino) != (linked.st_dev, linked.st_ino):
            _fail(f"shared config path identity changed: {path}")
        chunks: list[bytes] = []
        while chunk := os.read(fd, 65536):
            chunks.append(chunk)
    finally:
        os.close(fd)
    raw = b"".join(chunks)
    try:
        parsed = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeError, tomllib.TOMLDecodeError) as exc:
        _fail(f"malformed shared config {path}: {exc}")
    return raw, parsed, (opened.st_dev, opened.st_ino)


def _atomic_replace(
    path: Path, raw: bytes, expected_identity: tuple[int, int], expected_raw: bytes
) -> tuple[int, int]:
    if path.is_symlink():
        _fail(f"refusing symlinked shared config: {path}")
    current = os.stat(path, follow_symlinks=False)
    if (current.st_dev, current.st_ino) != expected_identity:
        _fail(f"shared config path identity changed before write: {path}")
    current_raw, _, current_identity = _read_config(path)
    if current_identity != expected_identity or current_raw != expected_raw:
        _fail(f"shared config changed before write: {path}")
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    staged = Path(name)
    try:
        with os.fdopen(fd, "wb") as handle:
            os.fchmod(handle.fileno(), current.st_mode & 0o777)
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        current = os.stat(path, follow_symlinks=False)
        if (current.st_dev, current.st_ino) != expected_identity:
            _fail(f"shared config path identity changed before replace: {path}")
        final_raw, _, final_identity = _read_config(path)
        if final_identity != expected_identity or final_raw != expected_raw:
            _fail(f"shared config changed immediately before replace: {path}")
        os.replace(staged, path)
        parent_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    finally:
        staged.unlink(missing_ok=True)
    linked = os.stat(path, follow_symlinks=False)
    return linked.st_dev, linked.st_ino


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _add_table(raw: bytes, semantic_path: list[str], expected: dict[str, Any]) -> bytes:
    text = raw.decode("utf-8")
    suffix = "" if text.endswith("\n") else "\n"
    return (
        text
        + suffix
        + f"\n[{semantic_path[0]}.{_toml_string(semantic_path[1])}]\n"
        + "".join(f"{key} = {str(value).lower() if isinstance(value, bool) else _toml_string(value)}\n" for key, value in expected.items())
    ).encode("utf-8")


def _remove_table(raw: bytes, semantic_path: list[str]) -> bytes:
    text = raw.decode("utf-8")
    key = re.escape(semantic_path[1])
    header = re.compile(
        rf'(?m)^\[{re.escape(semantic_path[0])}\.(?:{key}|"{key}")\][ \t]*(?:\n|$)'
    )
    matches = list(header.finditer(text))
    if len(matches) != 1:
        _fail("owned Marketplace table is not uniquely removable")
    start = matches[0].start()
    following = re.search(r"(?m)^\s*\[", text[matches[0].end() :])
    end = matches[0].end() + following.start() if following else len(text)
    return (text[:start] + text[end:]).encode("utf-8")


def new_record(
    target: Path,
    semantic_path: list[str],
    expected_state: dict[str, Any] | Path,
    campaign_id: str,
    candidate_sha: str,
) -> dict[str, Any]:
    raw, parsed, identity = _read_config(target)
    if _semantic_value(parsed, semantic_path) is not None:
        _fail(f"pre-existing shared config object: {'.'.join(semantic_path)}")
    expected = {"source": str(expected_state)} if isinstance(expected_state, Path) else expected_state
    now = _now()
    return {
        "target_path": str(target),
        "canonical_target_path": str(target.resolve()),
        "target_identity": {"device": identity[0], "inode": identity[1]},
        "config_format": "toml",
        "semantic_path": semantic_path,
        "operation": "create_table",
        "pre_state": {"exists": False},
        "expected_applied_state": expected,
        "rollback_operation": "remove_exact_semantic_table",
        "transaction_id": hashlib.sha256(
            f"{campaign_id}\0{candidate_sha}\0{target}\0{'.'.join(semantic_path)}".encode()
        ).hexdigest(),
        "campaign_id": campaign_id,
        "candidate_sha": candidate_sha,
        "status": "PREPARED",
        "created_at": now,
        "updated_at": now,
        "config_sha256_before": hashlib.sha256(raw).hexdigest(),
    }


def validate_record(record: dict[str, Any], campaign_id: str, candidate_sha: str) -> None:
    required = {
        "target_path", "canonical_target_path", "target_identity", "config_format",
        "semantic_path", "operation", "pre_state", "expected_applied_state",
        "transaction_id", "campaign_id", "candidate_sha", "status", "created_at", "updated_at",
        "rollback_operation",
    }
    if set(record) - (required | {"config_sha256_before", "cleanup_result"}) or not required <= set(record):
        _fail("shared config transaction journal is incomplete or contains unknown fields")
    if record["campaign_id"] != campaign_id or record["candidate_sha"] != candidate_sha:
        _fail("shared config transaction campaign/candidate mismatch")
    if (
        record["status"] not in STATES
        or record["config_format"] != "toml"
        or record["operation"] != "create_table"
        or record["rollback_operation"] != "remove_exact_semantic_table"
    ):
        _fail("shared config transaction journal is invalid")
    path = record["semantic_path"]
    if not isinstance(path, list) or len(path) != 2 or path[0] not in {"marketplaces", "plugins"}:
        _fail("shared config transaction semantic path is invalid")
    target = Path(record["target_path"])
    if str(target.resolve()) != record["canonical_target_path"]:
        _fail("shared config transaction target path drifted")
    expected_id = hashlib.sha256(
        f"{campaign_id}\0{candidate_sha}\0{target}\0{'.'.join(path)}".encode()
    ).hexdigest()
    if record["transaction_id"] != expected_id:
        _fail("shared config transaction identity drifted")
    if record["pre_state"] != {"exists": False} or not isinstance(record["expected_applied_state"], dict):
        _fail("shared config transaction semantic authority is invalid")
    identity = record["target_identity"]
    if set(identity) != {"device", "inode"} or not all(
        isinstance(identity[key], int) and identity[key] >= 0 for key in identity
    ):
        _fail("shared config transaction target identity is invalid")


def _state(record: dict[str, Any]) -> tuple[Path, bytes, Any, tuple[int, int]]:
    target = Path(record["target_path"])
    raw, parsed, identity = _read_config(target)
    return target, raw, _semantic_value(parsed, record["semantic_path"]), identity


def apply(record: dict[str, Any], persist: Callable[[], None]) -> None:
    target, raw, current, identity = _state(record)
    expected_identity = record["target_identity"]
    if identity != (expected_identity["device"], expected_identity["inode"]):
        _fail("shared config target identity changed after PREPARED; conflict")
    if current is not None:
        _fail("shared config object appeared after PREPARED; conflict")
    before = record.get("config_sha256_before")
    if before != hashlib.sha256(raw).hexdigest():
        _fail("shared config changed after PREPARED; conflict")
    new_identity = _atomic_replace(
        target,
        _add_table(raw, record["semantic_path"], record["expected_applied_state"]),
        identity,
        raw,
    )
    record["target_identity"] = {"device": new_identity[0], "inode": new_identity[1]}
    _crash_at("after_config_mutation")
    if os.environ.get("SUBAGENTS_DISPATCH_CALIBRATION_FAIL_AT") == "after_config_mutation":
        _fail("injected failure after config mutation")
    _, _, current, _ = _state(record)
    if current != record["expected_applied_state"]:
        _fail("shared config mutation verification failed")
    record["status"] = "APPLIED"
    record["updated_at"] = _now()
    persist()
    _crash_at("after_applied")


def commit(record: dict[str, Any], persist: Callable[[], None]) -> None:
    _, _, current, _ = _state(record)
    if current != record["expected_applied_state"]:
        _fail("shared config mutation changed before COMMITTED; conflict")
    record["status"] = "COMMITTED"
    record["updated_at"] = _now()
    persist()
    _crash_at("after_committed")


def cleanup(record: dict[str, Any], persist: Callable[[], None]) -> None:
    target, raw, current, identity = _state(record)
    expected = record["expected_applied_state"]
    if record["status"] == "CLEANED":
        if current is not None:
            _fail("CLEANED shared config mutation reappeared; conflict")
        return
    if current is None:
        record["status"] = "CLEANED"
        record["cleanup_result"] = "already_absent"
        record["updated_at"] = _now()
        persist()
        return
    if current != expected:
        _fail("owned shared config object was externally modified; conflict")
    record["status"] = "CLEANUP_PENDING"
    record["updated_at"] = _now()
    persist()
    _crash_at("after_cleanup_pending")
    new_identity = _atomic_replace(
        target, _remove_table(raw, record["semantic_path"]), identity, raw
    )
    record["target_identity"] = {"device": new_identity[0], "inode": new_identity[1]}
    _crash_at("after_cleanup_mutation")
    _, _, current, _ = _state(record)
    if current is not None:
        _fail("shared config cleanup verification failed")
    record["status"] = "CLEANED"
    record["cleanup_result"] = "removed"
    record["updated_at"] = _now()
    persist()
