#!/usr/bin/env python3
"""Provision subagents-dispatch custom-Agent profiles safely."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import stat
import tempfile
import tomllib
from typing import NoReturn
import uuid

from legacy_migration import (
    LEGACY_LOCK_NAME,
    LEGACY_MANIFEST_NAME,
    backup_legacy_files,
    commit_legacy_cleanup,
    detect_legacy_state,
    format_migration_state,
    load_legacy_manifest,
    rollback_legacy_cleanup,
    sha256_bytes,
)
from policy import load_policy_contract

ROOT = Path(__file__).resolve().parents[1]
PROFILE_SOURCE = ROOT / "agent-profiles"
MANIFEST_NAME = ".subagents-dispatch-agents.json"
LOCK_NAME = ".subagents-dispatch-agents.lock"
MANIFEST_SCHEMA = 1
MANAGED_BY = "subagents-dispatch"
ROLE_KEYS = {"reader", "worker", "solver", "investigator", "advisor"}


def fail(message: str) -> NoReturn:
    raise SystemExit(message)


def lock_file(fd: int) -> None:
    if os.name == "nt":
        import msvcrt

        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
        return
    import fcntl

    fcntl.flock(fd, fcntl.LOCK_EX)


def unlock_file(fd: int) -> None:
    if os.name == "nt":
        import msvcrt

        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        return
    import fcntl

    fcntl.flock(fd, fcntl.LOCK_UN)


@contextmanager
def managed_lock(
    codex_home: Path,
    lock_name: str,
    *,
    check_only: bool,
    label: str,
):
    lock_path = codex_home / lock_name
    if check_only and not codex_home.is_dir():
        fail(f"Required Codex home is missing: {codex_home}")
    if not check_only:
        codex_home.mkdir(parents=True, exist_ok=True)
    if lock_path.is_symlink():
        fail(f"Refusing symlinked {label} lock: {lock_path}")
    if check_only and not lock_path.exists():
        # Read-only check on a never-provisioned install: no lock has been created yet.
        yield
        return

    flags = os.O_RDWR | (0 if check_only else os.O_CREAT)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(lock_path, flags, 0o600)
    except OSError as exc:
        fail(f"Could not open {label} lock {lock_path}: {exc}")

    locked = False
    try:
        metadata = os.fstat(fd)
        if not stat.S_ISREG(metadata.st_mode):
            fail(f"{label.capitalize()} lock is not a regular file: {lock_path}")
        if metadata.st_size == 0:
            if check_only:
                fail(f"{label.capitalize()} lock is missing initialization state: {lock_path}")
            os.write(fd, b"\0")
            os.fsync(fd)
        lock_file(fd)
        locked = True
        yield
    finally:
        if locked:
            unlock_file(fd)
        os.close(fd)


@contextmanager
def installation_locks(
    codex_home: Path,
    *,
    check_only: bool,
    migrate_legacy: bool,
):
    """Acquire locks in one global order: legacy first, current second.

    Legacy codex-delegate installers only know the legacy lock. Taking it before
    the current lock gives migration mutual exclusion with both generations.
    Ordinary current installs only need the current lock.
    """

    if migrate_legacy and not check_only:
        with managed_lock(
            codex_home,
            LEGACY_LOCK_NAME,
            check_only=False,
            label="legacy migration",
        ):
            state = detect_legacy_state(codex_home)
            if state.ownership_unknown:
                fail(
                    "Refusing automatic legacy migration because ownership metadata is missing, invalid, or unsafe. "
                    "Run --legacy-status or /doctor and resolve the preserved legacy files explicitly."
                )
            with managed_lock(
                codex_home,
                LOCK_NAME,
                check_only=False,
                label="installer",
            ):
                yield
        return

    with managed_lock(
        codex_home,
        LOCK_NAME,
        check_only=check_only,
        label="installer",
    ):
        yield


def file_hash(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_installer_policy() -> dict:
    try:
        payload = load_policy_contract()
    except RuntimeError as exc:
        fail(f"Invalid subagents-dispatch policy contract: {exc}")
    roles = payload.get("roles")
    if not isinstance(roles, dict) or set(roles) != ROLE_KEYS:
        fail("Policy contract must define reader, worker, solver, investigator, and advisor roles")
    required = {"profile_file", "agent_type", "model", "effort", "sandbox_intent"}
    seen_files: set[str] = set()
    seen_names: set[str] = set()
    for role, spec in roles.items():
        if not isinstance(spec, dict) or not required <= set(spec):
            fail(f"Policy contract role {role!r} is incomplete")
        values = [spec.get(key) for key in required]
        if not all(isinstance(value, str) and value.strip() for value in values):
            fail(f"Policy contract role {role!r} contains an empty/non-string constant")
        if spec["profile_file"] in seen_files or spec["agent_type"] in seen_names:
            fail(f"Duplicate profile or Agent role in policy contract: {role}")
        seen_files.add(spec["profile_file"])
        seen_names.add(spec["agent_type"])
    return payload


POLICY_CONTRACT = load_installer_policy()
ROLE_SPECS = POLICY_CONTRACT["roles"]
PROFILE_FILES = tuple(spec["profile_file"] for spec in ROLE_SPECS.values())
EXPECTED_PROFILES = {
    spec["profile_file"]: (
        spec["agent_type"],
        spec["model"],
        spec["effort"],
        spec["sandbox_intent"],
    )
    for spec in ROLE_SPECS.values()
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Provision subagents-dispatch managed custom-Agent profiles."
    )
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")),
        help="Codex home directory (default: $CODEX_HOME or ~/.codex).",
    )
    parser.add_argument("--check", action="store_true", help="Verify current managed state without mutation.")
    parser.add_argument(
        "--migrate-legacy",
        action="store_true",
        help="Migrate from legacy codex-delegate installation before installing.",
    )
    parser.add_argument(
        "--legacy-status",
        action="store_true",
        help="Show legacy migration status without mutation.",
    )
    return parser.parse_args()


def load_manifest(path: Path) -> dict | None:
    if path.is_symlink():
        fail(f"Refusing symlinked install manifest: {path}")
    if not path.exists():
        return None
    if not path.is_file():
        fail(f"Install manifest is not a regular file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(f"Invalid install manifest {path}: {exc}")
    if not isinstance(payload, dict) or not isinstance(payload.get("profile_hashes", {}), dict):
        fail(f"Invalid install manifest object: {path}")
    if payload.get("schema_version") != MANIFEST_SCHEMA or payload.get("managed_by") != MANAGED_BY:
        fail(f"Unsupported subagents-dispatch managed-profile manifest: {path}")
    return payload


def manifest_hashes(manifest: dict | None) -> dict[str, str]:
    if manifest is None:
        return {}
    return {
        str(key): str(value)
        for key, value in manifest.get("profile_hashes", {}).items()
        if isinstance(key, str) and isinstance(value, str)
    }


def desired_manifest() -> dict:
    return {
        "schema_version": MANIFEST_SCHEMA,
        "managed_by": MANAGED_BY,
        "profile_hashes": {
            filename: file_hash(PROFILE_SOURCE / filename) for filename in PROFILE_FILES
        },
    }


def validate_sources() -> None:
    seen_names: set[str] = set()
    for filename, expected in EXPECTED_PROFILES.items():
        path = PROFILE_SOURCE / filename
        if path.is_symlink() or not path.is_file():
            fail(f"Agent profile must be a regular non-symlink file: {path}")
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
            fail(f"Invalid Agent profile {path}: {exc}")
        actual = (
            str(data.get("name", "")).strip(),
            str(data.get("model", "")).strip(),
            str(data.get("model_reasoning_effort", "")).strip(),
            str(data.get("sandbox_mode", "")).strip(),
        )
        if actual != expected:
            fail(f"Agent profile {filename} pins {actual!r}; expected {expected!r}")
        if not str(data.get("description", "")).strip() or not str(data.get("developer_instructions", "")).strip():
            fail(f"Agent profile is incomplete: {filename}")
        if expected[0] in seen_names:
            fail(f"Duplicate shipped Agent role name: {expected[0]}")
        seen_names.add(expected[0])


def preflight_agents_dir(path: Path, *, check_only: bool) -> None:
    if path.is_symlink():
        fail(f"Refusing symlinked agents directory: {path}")
    if path.exists() and not path.is_dir():
        fail(f"Agents destination is not a directory: {path}")
    if check_only and not path.is_dir():
        fail(
            f"Not installed: managed Agent profiles have not been provisioned yet "
            f"(agents directory missing: {path}). "
            "An explicit /dispatch task that needs delegation can provision these plugin-owned profiles automatically; "
            "newly provisioned roles require a fresh Codex task/session before spawn."
        )


def parse_profile_name(path: Path) -> str | None:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError):
        return None
    return str(data.get("name", "")).strip() or None


def preflight_profiles(
    agents_dir: Path,
    *,
    check_only: bool,
    managed_hashes: dict[str, str],
    pending_cleanup: set[str] | None = None,
) -> set[str]:
    upgrades: set[str] = set()
    skip_names = pending_cleanup or set()

    for filename in PROFILE_FILES:
        source = PROFILE_SOURCE / filename
        target = agents_dir / filename
        if target.is_symlink():
            fail(f"Refusing symlinked Agent profile destination: {target}")
        if not target.exists():
            if check_only:
                fail(
                    f"Not installed: managed Agent profile is missing ({target}). "
                    "An explicit /dispatch task that needs delegation can provision this plugin-owned profile automatically; "
                    "newly provisioned roles require a fresh Codex task/session before spawn."
                )
            continue
        if not target.is_file():
            fail(f"Agent profile destination is not a regular file: {target}")
        if target.read_bytes() == source.read_bytes():
            continue
        if not check_only and managed_hashes.get(filename) == file_hash(target):
            upgrades.add(filename)
            continue
        fail(
            "Refusing to overwrite an Agent profile that differs from the current package "
            f"and is not proven unchanged from a previous subagents-dispatch install: {target}"
        )

    current_roles = {values[0] for values in EXPECTED_PROFILES.values()}
    if agents_dir.exists():
        for existing in agents_dir.glob("*.toml"):
            if existing.name in PROFILE_FILES or existing.is_symlink() or not existing.is_file():
                continue
            if existing.name in skip_names:
                continue
            existing_name = parse_profile_name(existing)
            if existing_name in current_roles:
                fail(
                    "Refusing to install because another Agent file uses the reserved current role name "
                    f"{existing_name!r}: {existing}"
                )
    return upgrades


def verify_profiles(agents_dir: Path) -> None:
    for filename in PROFILE_FILES:
        source = PROFILE_SOURCE / filename
        target = agents_dir / filename
        if target.is_symlink() or not target.is_file() or target.read_bytes() != source.read_bytes():
            fail(f"Installed Agent profile is missing, unsafe, or differs from shipped template: {target}")


def stage_file(directory: Path, data: bytes) -> Path:
    fd, name = tempfile.mkstemp(prefix=".subagents-dispatch-agent-", dir=directory)
    staged = Path(name)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    return staged


def write_manifest(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = stage_file(
        path.parent,
        (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode(),
    )
    try:
        os.replace(staged, path)
    finally:
        staged.unlink(missing_ok=True)


def backup_target(target: Path) -> Path:
    backup = target.parent / f".{target.name}.backup-{uuid.uuid4().hex}"
    target.rename(backup)
    return backup


def apply_profile_changes(
    agents_dir: Path,
    upgrades: set[str],
    created: list[Path],
    backups: dict[Path, Path],
) -> None:
    for filename in PROFILE_FILES:
        source = PROFILE_SOURCE / filename
        target = agents_dir / filename
        if target.exists() and filename not in upgrades:
            continue
        staged = stage_file(agents_dir, source.read_bytes())
        try:
            if target.exists():
                backups[target] = backup_target(target)
            staged.rename(target)
            if target not in backups:
                created.append(target)
        except BaseException:
            staged.unlink(missing_ok=True)
            raise


def rollback(
    created: list[Path],
    backups: dict[Path, Path],
    manifest_path: Path,
    previous_manifest: bytes | None,
) -> list[str]:
    errors: list[str] = []
    for path in reversed(created):
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            errors.append(f"could not remove created profile {path}: {exc}")
    for target, backup in reversed(list(backups.items())):
        try:
            target.unlink(missing_ok=True)
            backup.rename(target)
        except OSError as exc:
            errors.append(f"could not restore {target}: {exc}")
    try:
        if previous_manifest is None:
            manifest_path.unlink(missing_ok=True)
        else:
            staged = stage_file(manifest_path.parent, previous_manifest)
            try:
                os.replace(staged, manifest_path)
            finally:
                staged.unlink(missing_ok=True)
    except OSError as exc:
        errors.append(f"could not restore managed-profile manifest {manifest_path}: {exc}")
    return errors


def install_locked(codex_home: Path, check_only: bool, migrate_legacy: bool = False) -> None:
    agents_dir = codex_home / "agents"
    manifest_path = codex_home / MANIFEST_NAME
    legacy_backup = None

    if migrate_legacy and not check_only:
        legacy_state = detect_legacy_state(codex_home)
        if legacy_state.ownership_unknown:
            fail(
                "Refusing automatic legacy migration because ownership metadata is missing, invalid, or unsafe. "
                "Run --legacy-status or /doctor and resolve the preserved legacy files explicitly."
            )
        if legacy_state.legacy_only or legacy_state.mixed:
            print(f"Legacy state detected: {format_migration_state(legacy_state)}")
            legacy_backup, legacy_warnings = backup_legacy_files(codex_home)
            for warning in legacy_warnings:
                print(f"  WARNING: {warning}")
        elif legacy_state.migration_complete:
            print("Legacy migration already complete; no legacy files found.")
        else:
            print("No legacy installation detected.")

    validate_sources()
    preflight_agents_dir(agents_dir, check_only=check_only)
    manifest = load_manifest(manifest_path)
    pending_cleanup = None
    if legacy_backup is not None:
        pending_cleanup = {
            Path(relative).name
            for relative, can_remove in legacy_backup.removal_map.items()
            if can_remove and relative.startswith("agents/")
        }
    upgrades = preflight_profiles(
        agents_dir,
        check_only=check_only,
        managed_hashes=manifest_hashes(manifest),
        pending_cleanup=pending_cleanup,
    )

    if check_only:
        verify_profiles(agents_dir)
        if manifest != desired_manifest():
            fail(f"Current managed-profile manifest is missing or stale: {manifest_path}")
        print("CHECK PASSED: subagents-dispatch managed Agent profiles and ownership state are exact.")
        return

    previous_manifest = manifest_path.read_bytes() if manifest_path.is_file() else None
    legacy_cleanup_committed = False

    if legacy_backup is not None:
        cleanup_messages, cleanup_warnings = commit_legacy_cleanup(codex_home, legacy_backup)
        legacy_cleanup_committed = True
        for message in cleanup_messages:
            print(f"  {message}")
        for warning in cleanup_warnings:
            print(f"  WARNING: {warning}")

    profiles_exact = agents_dir.is_dir() and all(
        (agents_dir / filename).is_file()
        and not (agents_dir / filename).is_symlink()
        and (agents_dir / filename).read_bytes() == (PROFILE_SOURCE / filename).read_bytes()
        for filename in PROFILE_FILES
    )
    if profiles_exact and manifest == desired_manifest():
        print("Managed Agent profiles already installed exactly; no changes made.")
        return

    codex_home.mkdir(parents=True, exist_ok=True)
    agents_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    backups: dict[Path, Path] = {}

    try:
        apply_profile_changes(agents_dir, upgrades, created, backups)
        # Pre-commit consistency check: publish ownership only for exact profiles.
        verify_profiles(agents_dir)
        write_manifest(manifest_path, desired_manifest())
        # Post-commit consistency check: fail and roll back if profiles drift during manifest publication.
        verify_profiles(agents_dir)
    except BaseException as exc:
        rollback_errors = rollback(created, backups, manifest_path, previous_manifest)
        if legacy_backup is not None and legacy_cleanup_committed:
            rollback_errors.extend(rollback_legacy_cleanup(codex_home, legacy_backup))
        if rollback_errors:
            fail(
                f"INSTALL FAILED: {exc}\nROLLBACK INCOMPLETE:\n- "
                + "\n- ".join(rollback_errors)
            )
        raise
    else:
        for backup in backups.values():
            backup.unlink(missing_ok=True)

    role_names = ", ".join(spec["agent_type"] for spec in ROLE_SPECS.values())
    print(f"Managed Agent profiles installed under: {agents_dir}")
    print(f"Managed profile manifest: {manifest_path}")
    print(f"Verified roles: {role_names}")
    post_state = detect_legacy_state(codex_home)
    if post_state.preserved_legacy:
        print(
            f"WARNING: {format_migration_state(post_state)}. User-owned legacy state was preserved; "
            "review it explicitly instead of repeating automatic migration."
        )
    print(
        "Profile files are ready. If the current /dispatch task could not see the required role before this install, "
        "its readiness outcome is RESTART_REQUIRED: do not attempt spawn_agent in that task; "
        "start a fresh Codex task/session and rerun the request."
    )


def install(codex_home: Path, check_only: bool, migrate_legacy: bool = False) -> None:
    codex_home = codex_home.expanduser()
    if codex_home.is_symlink():
        fail(f"Refusing symlinked Codex home: {codex_home}")
    codex_home = codex_home.resolve()
    with installation_locks(
        codex_home,
        check_only=check_only,
        migrate_legacy=migrate_legacy,
    ):
        install_locked(codex_home, check_only, migrate_legacy)


def show_legacy_status(codex_home: Path) -> None:
    codex_home = codex_home.expanduser()
    if codex_home.is_symlink():
        fail(f"Refusing symlinked Codex home: {codex_home}")
    codex_home = codex_home.resolve()
    state = detect_legacy_state(codex_home)
    print(f"Legacy migration status: {format_migration_state(state)}")
    print(f"  Legacy only: {state.legacy_only}")
    print(f"  Current only: {state.current_only}")
    print(f"  Mixed: {state.mixed}")
    print(f"  Legacy modified: {state.legacy_modified}")
    print(f"  Ownership unknown: {state.ownership_unknown}")
    print(f"  Preserved legacy: {state.preserved_legacy}")
    print(f"  Migration complete: {state.migration_complete}")

    if state.legacy_only or state.mixed:
        path = codex_home / LEGACY_MANIFEST_NAME
        manifest = load_legacy_manifest(path)
        if manifest:
            print(f"  Legacy manifest: {path}")
            print(f"  Legacy schema version: {manifest.schema_version}")
            print(f"  Legacy managed by: {manifest.managed_by}")
            print(f"  Legacy profiles: {', '.join(manifest.profile_hashes.keys())}")


def main() -> None:
    args = parse_args()
    if args.legacy_status:
        show_legacy_status(args.codex_home)
    else:
        install(args.codex_home, args.check, args.migrate_legacy)


if __name__ == "__main__":
    main()
