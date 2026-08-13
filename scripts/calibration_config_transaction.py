"""Crash-safe semantic ownership for one calibration Marketplace table."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import ctypes
import json
import os
from pathlib import Path
import re
import sys
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


def atomic_exchange_supported() -> bool:
    if sys.platform == "win32":
        return False
    libc = ctypes.CDLL(None, use_errno=True)
    return (sys.platform == "darwin" and hasattr(libc, "renamex_np")) or hasattr(
        libc, "renameat2"
    )


def _require_atomic_exchange() -> None:
    if not atomic_exchange_supported():
        _fail("platform lacks atomic path exchange required for safe shared-config mutation")


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


def _read_raw(path: Path) -> tuple[bytes, tuple[int, int]]:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        opened = os.fstat(fd)
        chunks: list[bytes] = []
        while chunk := os.read(fd, 65536):
            chunks.append(chunk)
    finally:
        os.close(fd)
    return b"".join(chunks), (opened.st_dev, opened.st_ino)


def _atomic_replace(
    path: Path,
    raw: bytes,
    expected_identity: tuple[int, int],
    expected_raw: bytes,
    exchange_path: Path,
    exchange_identity: tuple[int, int] | None,
    persist_exchange_identity: Callable[[tuple[int, int]], None],
    validate_external_evidence: Callable[[], None] | None = None,
) -> tuple[int, int]:
    _require_atomic_exchange()
    if path.is_symlink():
        _fail(f"refusing symlinked shared config: {path}")
    current = os.stat(path, follow_symlinks=False)
    if (current.st_dev, current.st_ino) != expected_identity:
        _fail(f"shared config path identity changed before write: {path}")
    current_raw, _, current_identity = _read_config(path)
    if current_identity != expected_identity or current_raw != expected_raw:
        _fail(f"shared config changed before write: {path}")
    if exchange_path.is_symlink():
        _fail(f"shared-config exchange path is unsafe: {exchange_path}")
    if exchange_path.exists():
        if exchange_identity is None:
            _fail(f"shared-config exchange path already exists: {exchange_path}")
        fd = os.open(exchange_path, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
        staged = os.fstat(fd)
        staged_identity = (staged.st_dev, staged.st_ino)
        if staged_identity != exchange_identity:
            os.close(fd)
            _fail("shared-config staged mutation changed; conflict")
    else:
        fd = os.open(
            exchange_path,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        staged = os.fstat(fd)
        staged_identity = (staged.st_dev, staged.st_ino)
        persist_exchange_identity(staged_identity)
    original_fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        opened_original = os.fstat(original_fd)
        if (opened_original.st_dev, opened_original.st_ino) != expected_identity:
            _fail(f"shared config path identity changed before staging: {path}")
        os.fchmod(fd, current.st_mode & 0o777)
        os.lseek(fd, 0, os.SEEK_SET)
        view = memoryview(raw)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                _fail("shared-config staged mutation write failed")
            view = view[written:]
        os.ftruncate(fd, len(raw))
        os.fsync(fd)
        os.lseek(fd, 0, os.SEEK_SET)
        staged_raw = b""
        while chunk := os.read(fd, 65536):
            staged_raw += chunk
        if staged_raw != raw:
            _fail("shared-config staged mutation verification failed")
        current = os.stat(path, follow_symlinks=False)
        if (current.st_dev, current.st_ino) != expected_identity:
            _fail(f"shared config path identity changed before replace: {path}")
        final_raw, _, final_identity = _read_config(path)
        if final_identity != expected_identity or final_raw != expected_raw:
            _fail(f"shared config changed immediately before replace: {path}")
        if validate_external_evidence is not None:
            validate_external_evidence()
        _atomic_exchange(exchange_path, path)
        linked = os.stat(path, follow_symlinks=False)
        os.lseek(original_fd, 0, os.SEEK_SET)
        previous_raw = b""
        while chunk := os.read(original_fd, 65536):
            previous_raw += chunk
        exchanged = os.stat(exchange_path, follow_symlinks=False)
        if (
            (linked.st_dev, linked.st_ino) != staged_identity
            or (exchanged.st_dev, exchanged.st_ino) != expected_identity
            or previous_raw != expected_raw
        ):
            _fail(f"shared config changed during atomic write: {path}")
        if validate_external_evidence is not None:
            validate_external_evidence()
        parent_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    finally:
        os.close(original_fd)
        os.close(fd)
    return staged_identity


def _atomic_exchange(first: Path, second: Path) -> None:
    _require_atomic_exchange()
    libc = ctypes.CDLL(None, use_errno=True)
    first_bytes, second_bytes = os.fsencode(first), os.fsencode(second)
    if sys.platform == "darwin" and hasattr(libc, "renamex_np"):
        result = libc.renamex_np(first_bytes, second_bytes, 0x00000002)
    elif hasattr(libc, "renameat2"):
        result = libc.renameat2(-2, first_bytes, -2, second_bytes, 0x00000002)
    else:  # pragma: no cover - guarded by _require_atomic_exchange
        raise AssertionError("atomic exchange capability changed during mutation")
    if result != 0:
        error = ctypes.get_errno()
        _fail(f"atomic shared-config exchange failed: {os.strerror(error)}")


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
    transaction_id = hashlib.sha256(
        f"{campaign_id}\0{candidate_sha}\0{target}\0{'.'.join(semantic_path)}".encode()
    ).hexdigest()
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
        "transaction_id": transaction_id,
        "campaign_id": campaign_id,
        "candidate_sha": candidate_sha,
        "status": "PREPARED",
        "created_at": now,
        "updated_at": now,
        "config_sha256_before": hashlib.sha256(raw).hexdigest(),
        "exchange_candidate_sha256": hashlib.sha256(
            _add_table(raw, semantic_path, expected)
        ).hexdigest(),
        "exchange_path": str(target.parent / f".{target.name}.{transaction_id}.apply.exchange"),
        "cleanup_exchange_path": str(
            target.parent / f".{target.name}.{transaction_id}.cleanup.exchange"
        ),
    }


def validate_record(record: dict[str, Any], campaign_id: str, candidate_sha: str) -> None:
    required = {
        "target_path", "canonical_target_path", "target_identity", "config_format",
        "semantic_path", "operation", "pre_state", "expected_applied_state",
        "transaction_id", "campaign_id", "candidate_sha", "status", "created_at", "updated_at",
        "rollback_operation",
    }
    if set(record) - (required | {
        "config_sha256_before", "cleanup_result", "cleanup_expected_sha256",
        "cleanup_displaced_sha256",
        "exchange_path", "exchange_candidate_sha256", "exchange_identity",
        "cleanup_exchange_path", "cleanup_exchange_identity",
    }) or not required <= set(record):
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
    expected_exchange = target.parent / f".{target.name}.{expected_id}.apply.exchange"
    if record.get("exchange_path") != str(expected_exchange):
        _fail("shared config transaction exchange path drifted")
    expected_cleanup_exchange = target.parent / f".{target.name}.{expected_id}.cleanup.exchange"
    if record.get("cleanup_exchange_path") != str(expected_cleanup_exchange):
        _fail("shared config transaction cleanup exchange path drifted")
    if record["status"] == "PREPARED" and "exchange_identity" not in record:
        expected_candidate = hashlib.sha256(
            _add_table(_read_config(target)[0], path, record["expected_applied_state"])
        ).hexdigest()
        if record.get("exchange_candidate_sha256") != expected_candidate:
            _fail("shared config transaction exchange candidate drifted")
    if record["pre_state"] != {"exists": False} or not isinstance(record["expected_applied_state"], dict):
        _fail("shared config transaction semantic authority is invalid")
    identity = record["target_identity"]
    if set(identity) != {"device", "inode"} or not all(
        isinstance(identity[key], int) and identity[key] >= 0 for key in identity
    ):
        _fail("shared config transaction target identity is invalid")
    for field in ("exchange_identity", "cleanup_exchange_identity"):
        exchange_identity = record.get(field)
        if exchange_identity is not None and (
            set(exchange_identity) != {"device", "inode"}
            or not all(
                isinstance(exchange_identity[key], int) and exchange_identity[key] >= 0
                for key in exchange_identity
            )
        ):
            _fail(f"shared config transaction {field} is invalid")


def _state(record: dict[str, Any]) -> tuple[Path, bytes, Any, tuple[int, int]]:
    target = Path(record["target_path"])
    raw, parsed, identity = _read_config(target)
    return target, raw, _semantic_value(parsed, record["semantic_path"]), identity


def _require_owned_identity(record: dict[str, Any], identity: tuple[int, int]) -> None:
    expected = record["target_identity"]
    if identity != (expected["device"], expected["inode"]):
        _fail("shared config target identity changed; conflict")


def _validate_exchange_evidence(
    record: dict[str, Any], path_field: str, identity_field: str, hash_field: str | None
) -> tuple[int, int] | None:
    exchange = Path(record[path_field])
    if not exchange.exists() and not exchange.is_symlink():
        if identity_field in record:
            _fail("shared-config exchange evidence is missing; conflict")
        return None
    if exchange.is_symlink() or not exchange.is_file():
        _fail("shared-config exchange recovery path is unsafe")
    raw, identity = _read_raw(exchange)
    expected = record.get(identity_field)
    if expected == {"device": identity[0], "inode": identity[1]}:
        if hash_field is not None and hashlib.sha256(raw).hexdigest() != record[hash_field]:
            _fail("shared-config exchange evidence content changed; conflict")
        return identity
    _fail("shared-config exchange evidence changed; conflict")


def apply(record: dict[str, Any], persist: Callable[[], None]) -> None:
    _require_atomic_exchange()
    target, raw, current, identity = _state(record)
    expected_identity = record["target_identity"]
    staged = record.get("exchange_identity")
    exchange = Path(record["exchange_path"])
    if staged is not None and exchange.exists() and not exchange.is_symlink():
        exchange_raw, exchange_identity = _read_raw(exchange)
        staged_identity = (staged["device"], staged["inode"])
        original_identity = (expected_identity["device"], expected_identity["inode"])
        if identity == staged_identity and exchange_identity == original_identity:
            if (
                current != record["expected_applied_state"]
                or hashlib.sha256(raw).hexdigest()
                != record["exchange_candidate_sha256"]
                or hashlib.sha256(exchange_raw).hexdigest()
                != record["config_sha256_before"]
            ):
                _fail("shared config apply write attribution is unresolved; conflict")
            record["target_identity"] = staged
            record["exchange_identity"] = expected_identity
            record["status"] = "APPLIED"
            record["updated_at"] = _now()
            persist()
            return
    _validate_exchange_evidence(
        record, "exchange_path", "exchange_identity", None
    )
    if identity != (expected_identity["device"], expected_identity["inode"]):
        _fail("shared config target identity changed after PREPARED; conflict")
    if current is not None:
        _fail("shared config object appeared after PREPARED; conflict")
    before = record.get("config_sha256_before")
    if before != hashlib.sha256(raw).hexdigest():
        _fail("shared config changed after PREPARED; conflict")
    def persist_exchange_identity(identity: tuple[int, int]) -> None:
        record["exchange_identity"] = {"device": identity[0], "inode": identity[1]}
        record["updated_at"] = _now()
        persist()

    new_identity = _atomic_replace(
        target,
        _add_table(raw, record["semantic_path"], record["expected_applied_state"]),
        identity,
        raw,
        Path(record["exchange_path"]),
        (
            (record["exchange_identity"]["device"], record["exchange_identity"]["inode"])
            if "exchange_identity" in record
            else None
        ),
        persist_exchange_identity,
    )
    record["target_identity"] = {"device": new_identity[0], "inode": new_identity[1]}
    record["exchange_identity"] = {"device": identity[0], "inode": identity[1]}
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
    _, _, current, identity = _state(record)
    _require_owned_identity(record, identity)
    if current != record["expected_applied_state"]:
        _fail("shared config mutation changed before COMMITTED; conflict")
    record["status"] = "COMMITTED"
    record["updated_at"] = _now()
    persist()
    _crash_at("after_committed")


def cleanup(record: dict[str, Any], persist: Callable[[], None]) -> None:
    _require_atomic_exchange()
    _validate_exchange_evidence(
        record, "exchange_path", "exchange_identity", "config_sha256_before"
    )
    target, raw, current, identity = _state(record)
    expected = record["expected_applied_state"]
    expected_identity = record["target_identity"]
    owned_identity = identity == (expected_identity["device"], expected_identity["inode"])
    if (
        not owned_identity
        and record["status"] == "CLEANUP_PENDING"
        and current is None
        and record.get("cleanup_expected_sha256") == hashlib.sha256(raw).hexdigest()
    ):
        staged = record.get("cleanup_exchange_identity")
        if staged != {"device": identity[0], "inode": identity[1]}:
            _fail("shared config cleanup write attribution is unresolved; conflict")
        exchange = Path(record["cleanup_exchange_path"])
        if exchange.is_symlink() or not exchange.is_file():
            _fail("shared-config exchange recovery path is unsafe")
        _, displaced_identity = _read_raw(exchange)
        if displaced_identity != (expected_identity["device"], expected_identity["inode"]):
            _fail("shared config cleanup write attribution is unresolved; conflict")
        _, verified_raw, verified_current, verified_identity = _state(record)
        if (
            verified_identity != identity
            or verified_current is not None
            or hashlib.sha256(verified_raw).hexdigest()
            != record["cleanup_expected_sha256"]
        ):
            _fail("shared config changed during cleanup recovery; conflict")
        _validate_exchange_evidence(
            record,
            "cleanup_exchange_path",
            "target_identity",
            "cleanup_displaced_sha256",
        )
        record["target_identity"] = {
            "device": verified_identity[0], "inode": verified_identity[1]
        }
        record["cleanup_exchange_identity"] = {
            "device": displaced_identity[0], "inode": displaced_identity[1]
        }
        record["status"] = "CLEANED"
        record["cleanup_result"] = "removed"
        record["updated_at"] = _now()
        persist()
        return
    _validate_exchange_evidence(
        record,
        "cleanup_exchange_path",
        "cleanup_exchange_identity",
        (
            "cleanup_displaced_sha256"
            if record["status"] == "CLEANED"
            else None
        ),
    )
    _require_owned_identity(record, identity)
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
    cleaned_raw = _remove_table(raw, record["semantic_path"])
    record["cleanup_expected_sha256"] = hashlib.sha256(cleaned_raw).hexdigest()
    record["cleanup_displaced_sha256"] = hashlib.sha256(raw).hexdigest()
    record["status"] = "CLEANUP_PENDING"
    record["updated_at"] = _now()
    persist()
    _crash_at("after_cleanup_pending")
    def persist_cleanup_exchange_identity(identity: tuple[int, int]) -> None:
        record["cleanup_exchange_identity"] = {
            "device": identity[0], "inode": identity[1]
        }
        record["updated_at"] = _now()
        persist()

    new_identity = _atomic_replace(
        target,
        cleaned_raw,
        identity,
        raw,
        Path(record["cleanup_exchange_path"]),
        (
            (
                record["cleanup_exchange_identity"]["device"],
                record["cleanup_exchange_identity"]["inode"],
            )
            if "cleanup_exchange_identity" in record
            else None
        ),
        persist_cleanup_exchange_identity,
        lambda: _validate_exchange_evidence(
            record, "exchange_path", "exchange_identity", "config_sha256_before"
        ),
    )
    record["target_identity"] = {"device": new_identity[0], "inode": new_identity[1]}
    record["cleanup_exchange_identity"] = {"device": identity[0], "inode": identity[1]}
    _crash_at("after_cleanup_mutation")
    _, _, current, _ = _state(record)
    if current is not None:
        _fail("shared config cleanup verification failed")
    record["status"] = "CLEANED"
    record["cleanup_result"] = "removed"
    record["updated_at"] = _now()
    persist()
