#!/usr/bin/env python3
"""Legacy migration contract for codex-delegate → subagents-dispatch."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import NamedTuple

LEGACY_MANAGED_BY = "codex-delegate"
LEGACY_MANIFEST_NAME = ".codex-delegate-agents.json"
LEGACY_LOCK_NAME = ".codex-delegate-agents.lock"
CURRENT_MANAGED_BY = "subagents-dispatch"
CURRENT_MANIFEST_NAME = ".subagents-dispatch-agents.json"
LEGACY_PROFILE_FILES = (
    "codex-delegate-reader.toml",
    "codex-delegate-worker.toml",
    "codex-delegate-solver.toml",
    "codex-delegate-investigator.toml",
    "codex-delegate-advisor.toml",
)


class LegacyManifest(NamedTuple):
    schema_version: int
    managed_by: str
    profile_hashes: dict[str, str]


class MigrationState(NamedTuple):
    legacy_only: bool
    current_only: bool
    mixed: bool
    legacy_modified: bool
    migration_complete: bool
    ownership_unknown: bool
    preserved_legacy: bool


class LegacyBackup(NamedTuple):
    files: dict[str, bytes]
    removal_map: dict[str, bool]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def legacy_manifest_status(path: Path) -> tuple[str, LegacyManifest | None]:
    """Return (status, manifest): missing, valid, invalid, or unsafe."""
    if path.is_symlink():
        return "unsafe", None
    if not path.exists():
        return "missing", None
    if not path.is_file():
        return "unsafe", None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return "invalid", None
    if not isinstance(payload, dict):
        return "invalid", None
    if payload.get("schema_version") != 1 or payload.get("managed_by") != LEGACY_MANAGED_BY:
        return "invalid", None
    hashes = payload.get("profile_hashes")
    if not isinstance(hashes, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in hashes.items()
    ):
        return "invalid", None
    if set(hashes) - set(LEGACY_PROFILE_FILES):
        # Automatic cleanup understands only the fixed legacy profile set. An
        # unknown ownership entry may describe a managed file this generation
        # cannot safely snapshot/remove/restore, so preserve the manifest and
        # require explicit review instead of discarding ownership evidence.
        return "invalid", None
    return "valid", LegacyManifest(1, LEGACY_MANAGED_BY, dict(hashes))


def load_legacy_manifest(path: Path) -> LegacyManifest | None:
    status, manifest = legacy_manifest_status(path)
    return manifest if status == "valid" else None


def _legacy_profile_state(codex_home: Path) -> tuple[list[str], bool]:
    agents_dir = codex_home / "agents"
    regular: list[str] = []
    unsafe = False
    if not agents_dir.exists():
        return regular, unsafe
    if agents_dir.is_symlink() or not agents_dir.is_dir():
        return regular, True
    for filename in LEGACY_PROFILE_FILES:
        path = agents_dir / filename
        if path.is_symlink():
            unsafe = True
        elif path.exists():
            if path.is_file():
                regular.append(filename)
            else:
                unsafe = True
    return regular, unsafe


def _current_manifest_valid(codex_home: Path) -> bool:
    path = codex_home / CURRENT_MANIFEST_NAME
    if path.is_symlink() or not path.is_file():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    return (
        isinstance(payload, dict)
        and payload.get("managed_by") == CURRENT_MANAGED_BY
        and payload.get("schema_version") == 1
        and isinstance(payload.get("profile_hashes"), dict)
    )


def detect_legacy_state(codex_home: Path) -> MigrationState:
    agents_dir = codex_home / "agents"
    manifest_status, legacy_manifest = legacy_manifest_status(
        codex_home / LEGACY_MANIFEST_NAME
    )
    legacy_profiles, unsafe_profiles = _legacy_profile_state(codex_home)
    has_current = _current_manifest_valid(codex_home)
    has_legacy = manifest_status != "missing" or bool(legacy_profiles) or unsafe_profiles
    ownership_unknown = (
        manifest_status in {"invalid", "unsafe"}
        or unsafe_profiles
        or (manifest_status == "missing" and bool(legacy_profiles))
    )

    legacy_modified = False
    unowned_profiles = False
    if legacy_manifest and agents_dir.is_dir() and not agents_dir.is_symlink():
        for filename in legacy_profiles:
            expected_hash = legacy_manifest.profile_hashes.get(filename)
            if expected_hash is None:
                unowned_profiles = True
                continue
            try:
                actual_hash = sha256_bytes((agents_dir / filename).read_bytes())
            except OSError:
                ownership_unknown = True
                continue
            if actual_hash != expected_hash:
                legacy_modified = True

    legacy_only = has_legacy and not has_current
    mixed = has_legacy and has_current
    current_only = has_current and not has_legacy
    preserved_legacy = mixed and (
        legacy_modified or unowned_profiles or ownership_unknown
    )
    return MigrationState(
        legacy_only=legacy_only,
        current_only=current_only,
        mixed=mixed,
        legacy_modified=legacy_modified,
        migration_complete=current_only,
        ownership_unknown=ownership_unknown,
        preserved_legacy=preserved_legacy,
    )


def collect_legacy_files(codex_home: Path) -> dict[str, bytes]:
    """Snapshot migration payload. Lock files are coordination primitives, not payload."""
    agents_dir = codex_home / "agents"
    files: dict[str, bytes] = {}
    manifest_path = codex_home / LEGACY_MANIFEST_NAME
    if manifest_path.is_file() and not manifest_path.is_symlink():
        files[LEGACY_MANIFEST_NAME] = manifest_path.read_bytes()
    if agents_dir.is_dir() and not agents_dir.is_symlink():
        for filename in LEGACY_PROFILE_FILES:
            path = agents_dir / filename
            if path.is_file() and not path.is_symlink():
                files[f"agents/{filename}"] = path.read_bytes()
    return files


def can_safely_remove_legacy(
    codex_home: Path,
    legacy_manifest: LegacyManifest | None,
) -> dict[str, bool]:
    agents_dir = codex_home / "agents"
    result: dict[str, bool] = {LEGACY_LOCK_NAME: False}
    all_profiles_removable = legacy_manifest is not None

    for filename in LEGACY_PROFILE_FILES:
        path = agents_dir / filename
        relative = f"agents/{filename}"
        if path.is_symlink():
            result[relative] = False
            all_profiles_removable = False
            continue
        if not path.exists():
            continue
        if not path.is_file():
            result[relative] = False
            all_profiles_removable = False
            continue
        expected = legacy_manifest.profile_hashes.get(filename) if legacy_manifest else None
        if expected is None:
            result[relative] = False
            all_profiles_removable = False
            continue
        try:
            removable = sha256_bytes(path.read_bytes()) == expected
        except OSError:
            removable = False
        result[relative] = removable
        if not removable:
            all_profiles_removable = False

    manifest_status, _ = legacy_manifest_status(codex_home / LEGACY_MANIFEST_NAME)
    result[LEGACY_MANIFEST_NAME] = manifest_status == "valid" and all_profiles_removable
    return result


def backup_legacy_files(codex_home: Path) -> tuple[LegacyBackup, list[str]]:
    manifest = load_legacy_manifest(codex_home / LEGACY_MANIFEST_NAME)
    removal_map = can_safely_remove_legacy(codex_home, manifest)
    files = collect_legacy_files(codex_home)
    warnings: list[str] = []
    for relative_path, can_remove in removal_map.items():
        target = codex_home / relative_path
        if (
            not can_remove
            and relative_path != LEGACY_LOCK_NAME
            and (target.exists() or target.is_symlink())
        ):
            warnings.append(
                f"Preserving legacy file without proven ownership: {relative_path}"
            )
    return LegacyBackup(files, removal_map), warnings


def _restore_removed_paths(
    codex_home: Path,
    backup: LegacyBackup,
    paths: list[str],
) -> list[str]:
    errors: list[str] = []
    for relative_path in reversed(paths):
        target = codex_home / relative_path
        try:
            if target.exists() or target.is_symlink():
                errors.append(
                    f"refusing to overwrite changed path while restoring {relative_path}"
                )
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(backup.files[relative_path])
        except OSError as exc:
            errors.append(f"could not restore {relative_path}: {exc}")
    return errors


def remove_legacy_target(path: Path) -> None:
    """Indirection used by transaction fault-injection tests."""
    path.unlink()


def commit_legacy_cleanup(
    codex_home: Path,
    backup: LegacyBackup,
) -> tuple[list[str], list[str]]:
    """Transactionally remove snapshotted, unchanged, proven-owned legacy files."""
    removable = [
        path
        for path, can_remove in backup.removal_map.items()
        if can_remove and path in backup.files
    ]
    warnings = [
        f"Preserved legacy file: {path}"
        for path, can_remove in backup.removal_map.items()
        if not can_remove and path != LEGACY_LOCK_NAME and path in backup.files
    ]

    for relative_path in removable:
        target = codex_home / relative_path
        if target.is_symlink() or not target.is_file():
            raise RuntimeError(
                f"Legacy migration drift detected before cleanup: {relative_path}"
            )
        if target.read_bytes() != backup.files[relative_path]:
            raise RuntimeError(
                f"Legacy migration drift detected before cleanup: {relative_path}"
            )

    removed: list[str] = []
    messages: list[str] = []
    try:
        for relative_path in removable:
            target = codex_home / relative_path
            if target.is_symlink() or not target.is_file():
                raise RuntimeError(
                    f"Legacy migration drift detected during cleanup: {relative_path}"
                )
            if target.read_bytes() != backup.files[relative_path]:
                raise RuntimeError(
                    f"Legacy migration drift detected during cleanup: {relative_path}"
                )
            remove_legacy_target(target)
            removed.append(relative_path)
            messages.append(f"Removed legacy file: {relative_path}")
    except BaseException as exc:
        rollback_errors = _restore_removed_paths(codex_home, backup, removed)
        if rollback_errors:
            raise RuntimeError(
                f"Legacy cleanup failed: {exc}; rollback incomplete: "
                + "; ".join(rollback_errors)
            ) from exc
        raise
    return messages, warnings


def rollback_legacy_cleanup(codex_home: Path, backup: LegacyBackup) -> list[str]:
    removed_paths = [
        path
        for path, can_remove in backup.removal_map.items()
        if can_remove
        and path in backup.files
        and not (codex_home / path).exists()
        and not (codex_home / path).is_symlink()
    ]
    return _restore_removed_paths(codex_home, backup, removed_paths)


def format_migration_state(state: MigrationState) -> str:
    if state.preserved_legacy:
        if state.ownership_unknown:
            return "current_with_preserved_legacy_ownership_unknown"
        if state.legacy_modified:
            return "current_with_preserved_legacy_modified"
        return "current_with_preserved_legacy"
    if state.ownership_unknown:
        return "legacy_ownership_unknown"
    if state.migration_complete:
        return "migration_complete"
    if state.mixed:
        if state.legacy_modified:
            return "mixed_legacy_modified"
        return "mixed"
    if state.legacy_only:
        if state.legacy_modified:
            return "legacy_only_modified"
        return "legacy_only"
    if state.current_only:
        return "current_only"
    return "unknown"