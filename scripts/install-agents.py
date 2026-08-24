#!/usr/bin/env python3
"""Provision subagents-dispatch custom-Agent profiles safely."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import tomllib
from typing import NoReturn
import uuid

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


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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
def managed_lock(codex_home: Path, *, check_only: bool):
    lock_path = codex_home / LOCK_NAME
    if check_only and not codex_home.is_dir():
        fail(f"Required Codex home is missing: {codex_home}")
    if not check_only:
        codex_home.mkdir(parents=True, exist_ok=True)
    if lock_path.is_symlink():
        fail(f"Refusing symlinked installer lock: {lock_path}")
    if check_only and not lock_path.exists():
        yield
        return

    flags = os.O_RDWR | (0 if check_only else os.O_CREAT)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(lock_path, flags, 0o600)
    except OSError as exc:
        fail(f"Could not open installer lock {lock_path}: {exc}")

    locked = False
    try:
        metadata = os.fstat(fd)
        if not stat.S_ISREG(metadata.st_mode):
            fail(f"Installer lock is not a regular file: {lock_path}")
        if metadata.st_size == 0:
            if check_only:
                fail(f"Installer lock is missing initialization state: {lock_path}")
            os.write(fd, b"\0")
            os.fsync(fd)
        lock_file(fd)
        locked = True
        yield
    finally:
        if locked:
            unlock_file(fd)
        os.close(fd)


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
    required = {"profile_file", "agent_type", "model", "effort", "mutation_authority"}
    seen_files: set[str] = set()
    seen_names: set[str] = set()
    for role, spec in roles.items():
        if not isinstance(spec, dict) or not required <= set(spec):
            fail(f"Policy contract role {role!r} is incomplete")
        values = [spec.get(key) for key in required]
        if not all(isinstance(value, str) and value.strip() for value in values):
            fail(f"Policy contract role {role!r} contains an empty/non-string constant")
        sandbox_mode = spec.get("sandbox_mode")
        if spec["mutation_authority"] == "none":
            if sandbox_mode != "read-only":
                fail(f"Read-only policy role {role!r} must pin sandbox_mode='read-only'")
        elif sandbox_mode is not None:
            fail(f"Writable policy role {role!r} must inherit Host sandbox permission")
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
        spec.get("sandbox_mode"),
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
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify current managed state without mutation.",
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
            data.get("sandbox_mode"),
        )
        if actual != expected:
            fail(f"Agent profile {filename} pins {actual!r}; expected {expected!r}")
        if not str(data.get("description", "")).strip() or not str(
            data.get("developer_instructions", "")
        ).strip():
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
            f"Not installed: managed Agent profiles are not set up (agents directory missing: {path}). "
            "Run Orchestrate when delegation is needed, or run Doctor repair. "
            "Start a fresh Codex session after profiles are installed."
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
) -> dict[str, str]:
    upgrades: dict[str, str] = {}
    for filename in PROFILE_FILES:
        source = PROFILE_SOURCE / filename
        target = agents_dir / filename
        if target.is_symlink():
            fail(f"Refusing symlinked Agent profile destination: {target}")
        if not target.exists():
            if check_only:
                fail(
                    f"Not installed: managed Agent profile is missing ({target}). "
                    "Run Orchestrate when delegation is needed, or run Doctor repair. "
                    "Start a fresh Codex session after profiles are installed."
                )
            continue
        if not target.is_file():
            fail(f"Agent profile destination is not a regular file: {target}")
        if target.read_bytes() == source.read_bytes():
            continue
        target_hash = file_hash(target)
        if not check_only and managed_hashes.get(filename) == target_hash:
            upgrades[filename] = target_hash
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


def assert_upgrade_target_unchanged(target: Path, expected_hash: str) -> None:
    if target.is_symlink() or not target.is_file():
        fail(f"Managed Agent profile changed after preflight and will not be replaced: {target}")
    if file_hash(target) != expected_hash:
        fail(f"Managed Agent profile changed after preflight and will not be replaced: {target}")


def publish_staged_no_clobber(staged: Path, target: Path) -> None:
    try:
        os.link(staged, target)
    except FileExistsError as exc:
        raise RuntimeError(
            f"Agent profile destination appeared after preflight and will not be overwritten: {target}"
        ) from exc
    except OSError as exc:
        raise RuntimeError(
            f"Could not publish Agent profile without clobbering an existing destination {target}: {exc}"
        ) from exc
    finally:
        staged.unlink(missing_ok=True)


def apply_profile_changes(
    agents_dir: Path,
    upgrades: dict[str, str],
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
            if filename in upgrades:
                expected_hash = upgrades[filename]
                assert_upgrade_target_unchanged(target, expected_hash)
                backup = target.parent / f".{target.name}.backup-{uuid.uuid4().hex}"
                target.rename(backup)
                backups[target] = backup
                if backup.is_symlink() or not backup.is_file() or file_hash(backup) != expected_hash:
                    fail(
                        f"Managed Agent profile changed while being replaced; preserving rollback copy: {backup}"
                    )
            publish_staged_no_clobber(staged, target)
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
            source = PROFILE_SOURCE / path.name
            if path.exists():
                if path.is_symlink() or not path.is_file() or path.read_bytes() != source.read_bytes():
                    errors.append(
                        f"refusing to remove drifted created profile during rollback: {path}"
                    )
                    continue
                path.unlink()
        except OSError as exc:
            errors.append(f"could not remove created profile {path}: {exc}")
    for target, backup in reversed(list(backups.items())):
        try:
            if target.exists():
                source = PROFILE_SOURCE / target.name
                if target.is_symlink() or not target.is_file() or target.read_bytes() != source.read_bytes():
                    errors.append(
                        f"refusing to clobber drifted profile while restoring rollback copy {backup}: {target}"
                    )
                    continue
                target.unlink()
            os.link(backup, target)
            backup.unlink()
        except FileExistsError:
            errors.append(
                f"destination reappeared while restoring rollback copy {backup}; preserved both paths: {target}"
            )
        except OSError as exc:
            errors.append(f"could not restore {target} from {backup}: {exc}")
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


def install_locked(codex_home: Path, check_only: bool) -> None:
    agents_dir = codex_home / "agents"
    manifest_path = codex_home / MANIFEST_NAME

    validate_sources()
    preflight_agents_dir(agents_dir, check_only=check_only)
    manifest = load_manifest(manifest_path)
    upgrades = preflight_profiles(
        agents_dir,
        check_only=check_only,
        managed_hashes=manifest_hashes(manifest),
    )

    if check_only:
        verify_profiles(agents_dir)
        if manifest != desired_manifest():
            fail(f"Current managed-profile manifest is missing or stale: {manifest_path}")
        print("CHECK PASSED: Managed Agent profiles are installed and valid.")
        return

    previous_manifest = manifest_path.read_bytes() if manifest_path.is_file() else None
    profiles_exact = agents_dir.is_dir() and all(
        (agents_dir / filename).is_file()
        and not (agents_dir / filename).is_symlink()
        and (agents_dir / filename).read_bytes() == (PROFILE_SOURCE / filename).read_bytes()
        for filename in PROFILE_FILES
    )
    if profiles_exact and manifest == desired_manifest():
        print("Managed Agent profiles are already up to date; no changes made.")
        return

    codex_home.mkdir(parents=True, exist_ok=True)
    agents_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    backups: dict[Path, Path] = {}

    try:
        apply_profile_changes(agents_dir, upgrades, created, backups)
        verify_profiles(agents_dir)
        write_manifest(manifest_path, desired_manifest())
        verify_profiles(agents_dir)
    except BaseException as exc:
        rollback_errors = rollback(created, backups, manifest_path, previous_manifest)
        if rollback_errors:
            fail(
                f"INSTALL FAILED: {exc}\nROLLBACK INCOMPLETE:\n- "
                + "\n- ".join(rollback_errors)
            )
        raise
    else:
        for backup in backups.values():
            backup.unlink(missing_ok=True)

    print(f"Managed Agent profiles installed under: {agents_dir}")
    print("Restart required: Start a fresh Codex session before using Orchestrate.")


def install(codex_home: Path, check_only: bool) -> None:
    codex_home = codex_home.expanduser()
    if codex_home.is_symlink():
        fail(f"Refusing symlinked Codex home: {codex_home}")
    codex_home = codex_home.resolve()
    with managed_lock(codex_home, check_only=check_only):
        install_locked(codex_home, check_only)


def main() -> None:
    args = parse_args()
    install(args.codex_home, args.check)


if __name__ == "__main__":
    main()
