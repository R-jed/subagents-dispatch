#!/usr/bin/env python3
"""Remove only subagents-dispatch managed Agent profiles with proven ownership."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import runpy
import stat
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install-agents.py"


def fail(message: str) -> NoReturn:
    raise SystemExit(message)


def load_installer() -> dict[str, Any]:
    try:
        namespace = runpy.run_path(str(INSTALLER))
    except (OSError, RuntimeError) as exc:
        fail(f"Could not load managed-profile lifecycle owner {INSTALLER}: {exc}")
    required = {
        "LOCK_NAME",
        "MANIFEST_NAME",
        "PROFILE_FILES",
        "file_hash",
        "load_manifest",
        "manifest_hashes",
        "managed_lock",
    }
    missing = sorted(required - set(namespace))
    if missing:
        fail("Managed-profile lifecycle owner is incomplete: " + ", ".join(missing))
    return namespace


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Safely remove subagents-dispatch managed custom-Agent profiles."
    )
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")),
        help="Codex home directory (default: $CODEX_HOME or ~/.codex).",
    )
    return parser.parse_args()


def _looks_installed(codex_home: Path, lifecycle: dict[str, Any]) -> bool:
    manifest_path = codex_home / lifecycle["MANIFEST_NAME"]
    if manifest_path.exists() or manifest_path.is_symlink():
        return True
    agents_dir = codex_home / "agents"
    return any(
        (agents_dir / filename).exists() or (agents_dir / filename).is_symlink()
        for filename in lifecycle["PROFILE_FILES"]
    )


def _owned_targets(
    codex_home: Path,
    lifecycle: dict[str, Any],
) -> tuple[Path, list[tuple[Path, int, int, str]]]:
    manifest_path = codex_home / lifecycle["MANIFEST_NAME"]
    manifest = lifecycle["load_manifest"](manifest_path)
    agents_dir = codex_home / "agents"

    if manifest is None:
        collisions = [
            agents_dir / filename
            for filename in lifecycle["PROFILE_FILES"]
            if (agents_dir / filename).exists() or (agents_dir / filename).is_symlink()
        ]
        if collisions:
            fail(
                "Refusing uninstall because managed-profile ownership metadata is missing while reserved paths exist: "
                + ", ".join(str(path) for path in collisions)
            )
        return manifest_path, []

    managed_hashes = lifecycle["manifest_hashes"](manifest)
    expected_files = set(lifecycle["PROFILE_FILES"])
    if set(managed_hashes) != expected_files:
        fail("Refusing uninstall because the managed-profile manifest does not own the exact current profile set")

    owned: list[tuple[Path, int, int, str]] = []
    for filename in lifecycle["PROFILE_FILES"]:
        expected_sha = managed_hashes[filename]
        if len(expected_sha) != 64 or any(ch not in "0123456789abcdef" for ch in expected_sha):
            fail(f"Refusing uninstall because the recorded ownership hash is invalid for {filename}")
        target = agents_dir / filename
        if target.is_symlink():
            fail(f"Refusing symlinked managed Agent profile during uninstall: {target}")
        if not target.exists():
            continue
        try:
            identity = os.stat(target, follow_symlinks=False)
        except OSError as exc:
            fail(f"Could not inspect managed Agent profile during uninstall: {target}: {exc}")
        if not stat.S_ISREG(identity.st_mode):
            fail(f"Managed Agent profile is not a regular file during uninstall: {target}")
        actual_sha = lifecycle["file_hash"](target)
        if actual_sha != expected_sha:
            fail(
                "Refusing to remove a managed Agent profile that changed after the ownership manifest was written: "
                f"{target}"
            )
        owned.append((target, identity.st_dev, identity.st_ino, expected_sha))
    return manifest_path, owned


def uninstall(codex_home_arg: Path) -> None:
    lifecycle = load_installer()
    codex_home = codex_home_arg.expanduser()
    if codex_home.is_symlink():
        fail(f"Refusing symlinked Codex home: {codex_home}")
    if not codex_home.exists():
        print("Managed Agent profiles are not installed; no changes made.")
        return
    if not codex_home.is_dir():
        fail(f"Codex home is not a directory: {codex_home}")
    codex_home = codex_home.resolve()

    # Avoid creating a coordination lock in an unrelated existing Codex home
    # when neither the ownership manifest nor any reserved managed path exists.
    if not _looks_installed(codex_home, lifecycle):
        print("Managed Agent profiles are not installed; no changes made.")
        return

    with lifecycle["managed_lock"](
        codex_home,
        lifecycle["LOCK_NAME"],
        check_only=False,
        label="installer",
    ):
        manifest_path, owned = _owned_targets(codex_home, lifecycle)
        if not manifest_path.exists() and not manifest_path.is_symlink():
            if not owned:
                print("Managed Agent profiles are not installed; no changes made.")
                return
            fail("Refusing uninstall without the managed-profile ownership manifest")

        # Revalidate every owned path immediately before the first deletion so
        # a partial uninstall never begins from stale ownership evidence.
        for target, device, inode, expected_sha in owned:
            try:
                identity = os.stat(target, follow_symlinks=False)
            except OSError as exc:
                fail(f"Managed Agent profile changed before uninstall commit: {target}: {exc}")
            if (
                not stat.S_ISREG(identity.st_mode)
                or (identity.st_dev, identity.st_ino) != (device, inode)
                or lifecycle["file_hash"](target) != expected_sha
            ):
                fail(f"Managed Agent profile changed before uninstall commit: {target}")

        for target, _, _, _ in owned:
            target.unlink()
        manifest_path.unlink()

    print(
        "UNINSTALL COMPLETE: exact owned managed Agent profiles and ownership manifest removed; "
        "installer lock retained."
    )


def main() -> None:
    args = parse_args()
    uninstall(args.codex_home)


if __name__ == "__main__":
    main()
