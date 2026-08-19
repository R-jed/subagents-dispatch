#!/usr/bin/env python3
"""Generate and verify the deterministic subagents-dispatch runtime package manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_RELATIVE = PurePosixPath(".codex-plugin/package-integrity.json")
SCHEMA_VERSION = 1
ALGORITHM = "sha256"
NORMALIZATION = "utf-8-lf"
STATIC_FILES = (
    PurePosixPath(".codex-plugin/plugin.json"),
    PurePosixPath(".agents/plugins/marketplace.json"),
    PurePosixPath("docs/python-runtime.md"),
)
RUNTIME_DIRECTORIES = (
    PurePosixPath("agent-profiles"),
    PurePosixPath("contracts"),
    PurePosixPath("hooks"),
    PurePosixPath("skills"),
)
RUNTIME_SCRIPT_FILES = tuple(
    PurePosixPath(path)
    for path in (
        "scripts/check-plugin-update.py",
        "scripts/dispatch_control_v4.py",
        "scripts/dispatch_state.py",
        "scripts/dispatch_state_v4.py",
        "scripts/dispatch_state_v4_core.py",
        "scripts/doctor.py",
        "scripts/doctor_runtime.py",
        "scripts/doctor_runtime_core.py",
        "scripts/execution_lifecycle_v4.py",
        "scripts/execution_lifecycle_v4_core.py",
        "scripts/host_capabilities.py",
        "scripts/host_evidence_v4.py",
        "scripts/inspect-agent-runtime.py",
        "scripts/install-agents.py",
        "scripts/legacy_migration.py",
        "scripts/managed_execution_v4.py",
        "scripts/orchestrate_v4.py",
        "scripts/orchestration_guard.py",
        "scripts/package_integrity.py",
        "scripts/plugin_update.py",
        "scripts/policy.py",
        "scripts/review-artifact.py",
        "scripts/runtime-evidence.py",
        "scripts/scheduler_v4.py",
        "scripts/spawn_guard.py",
        "scripts/uninstall-agents.py",
        "scripts/validate_team_ledger.py",
        "scripts/validate_team_plan.py",
        "scripts/work_graph_v4.py",
        "scripts/writer_lease_v4.py",
        "scripts/writer_lease_v4_core.py",
    )
)
IGNORED_PARTS = {"__pycache__"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}
UPDATE_BOOTSTRAP_PATHS = (
    ".codex-plugin/plugin.json",
    ".agents/plugins/marketplace.json",
    "scripts/doctor.py",
    "scripts/package_integrity.py",
    "scripts/plugin_update.py",
)


class IntegrityError(RuntimeError):
    """The runtime package integrity contract cannot be evaluated safely."""


def _safe_relative(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise IntegrityError(f"unsafe package-integrity path: {value!r}")
    return path


def _resolved_file(root: Path, relative: PurePosixPath) -> Path:
    candidate = root.joinpath(*relative.parts)
    if candidate.is_symlink():
        raise IntegrityError(f"symlinked runtime file is not allowed: {relative.as_posix()}")
    if not candidate.is_file():
        raise IntegrityError(f"runtime file is missing: {relative.as_posix()}")
    try:
        resolved_root = root.resolve(strict=True)
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise IntegrityError(f"runtime file cannot be resolved: {relative.as_posix()}") from exc
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise IntegrityError(f"runtime file escapes Plugin root: {relative.as_posix()}") from exc
    return resolved


def _normalized_bytes(path: Path) -> bytes:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise IntegrityError(f"runtime file must be readable UTF-8 text: {path}") from exc
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def _digest(path: Path) -> str:
    return hashlib.sha256(_normalized_bytes(path)).hexdigest()


def _iter_directory_files(root: Path, relative_dir: PurePosixPath) -> Iterable[PurePosixPath]:
    directory = root.joinpath(*relative_dir.parts)
    if directory.is_symlink():
        raise IntegrityError(f"symlinked runtime directory is not allowed: {relative_dir.as_posix()}")
    if not directory.is_dir():
        raise IntegrityError(f"runtime directory is missing: {relative_dir.as_posix()}")
    for candidate in sorted(directory.rglob("*"), key=lambda item: item.as_posix()):
        relative = PurePosixPath(candidate.relative_to(root).as_posix())
        if any(part in IGNORED_PARTS for part in relative.parts) or candidate.suffix in IGNORED_SUFFIXES:
            continue
        if candidate.is_symlink():
            raise IntegrityError(f"symlinked runtime path is not allowed: {relative.as_posix()}")
        if candidate.is_file():
            yield relative


def runtime_files(root: Path = ROOT) -> list[PurePosixPath]:
    root = root.expanduser()
    try:
        root = root.resolve(strict=True)
    except OSError as exc:
        raise IntegrityError("Plugin root is unavailable") from exc
    files = set(STATIC_FILES)
    for relative_dir in RUNTIME_DIRECTORIES:
        files.update(_iter_directory_files(root, relative_dir))
    for relative in RUNTIME_SCRIPT_FILES:
        _resolved_file(root, relative)
        files.add(relative)
    files.discard(MANIFEST_RELATIVE)
    return sorted(files, key=lambda item: item.as_posix())


def _plugin_version(root: Path) -> str:
    manifest = _resolved_file(root, PurePosixPath(".codex-plugin/plugin.json"))
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IntegrityError("Plugin manifest is unreadable") from exc
    version = payload.get("version") if isinstance(payload, dict) else None
    if not isinstance(version, str) or not version.strip():
        raise IntegrityError("Plugin version is unavailable")
    return version.strip()


def build_manifest(root: Path = ROOT) -> dict[str, Any]:
    root = root.expanduser().resolve(strict=True)
    files: dict[str, str] = {}
    for relative in runtime_files(root):
        files[relative.as_posix()] = _digest(_resolved_file(root, relative))
    return {
        "schema_version": SCHEMA_VERSION,
        "plugin_version": _plugin_version(root),
        "algorithm": ALGORITHM,
        "normalization": NORMALIZATION,
        "files": files,
    }


def _manifest_path(root: Path) -> Path:
    return root.joinpath(*MANIFEST_RELATIVE.parts)


def load_manifest(root: Path = ROOT) -> dict[str, Any]:
    root = root.expanduser().resolve(strict=True)
    path = _manifest_path(root)
    if path.is_symlink():
        raise IntegrityError("package-integrity manifest must not be a symlink")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IntegrityError("package-integrity manifest is unavailable or invalid") from exc
    if not isinstance(payload, dict):
        raise IntegrityError("package-integrity manifest must be a JSON object")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise IntegrityError("unsupported package-integrity schema version")
    if payload.get("algorithm") != ALGORITHM or payload.get("normalization") != NORMALIZATION:
        raise IntegrityError("package-integrity hash contract is unsupported")
    files = payload.get("files")
    if not isinstance(files, dict) or not files:
        raise IntegrityError("package-integrity manifest has no runtime files")
    for relative, digest in files.items():
        if not isinstance(relative, str) or not isinstance(digest, str) or len(digest) != 64:
            raise IntegrityError("package-integrity manifest contains an invalid file entry")
        _safe_relative(relative)
    return payload


def verify_package(root: Path = ROOT, *, profile: str = "full") -> dict[str, Any]:
    root = root.expanduser()
    try:
        root = root.resolve(strict=True)
        manifest = load_manifest(root)
    except (OSError, IntegrityError) as exc:
        return {
            "ok": False,
            "profile": profile,
            "missing": [],
            "mismatched": [],
            "unsafe": [],
            "manifest_error": str(exc),
        }

    files = manifest["files"]
    assert isinstance(files, Mapping)
    if profile == "full":
        targets = sorted(files)
    elif profile == "update-bootstrap":
        targets = list(UPDATE_BOOTSTRAP_PATHS)
    else:
        raise ValueError(f"unsupported integrity profile: {profile}")

    missing: list[str] = []
    mismatched: list[str] = []
    unsafe: list[str] = []
    for relative_text in targets:
        expected = files.get(relative_text)
        if not isinstance(expected, str):
            missing.append(relative_text)
            continue
        relative = _safe_relative(relative_text)
        candidate = root.joinpath(*relative.parts)
        if candidate.is_symlink():
            unsafe.append(relative_text)
            continue
        if not candidate.is_file():
            missing.append(relative_text)
            continue
        try:
            actual = _digest(_resolved_file(root, relative))
        except IntegrityError:
            unsafe.append(relative_text)
            continue
        if actual != expected:
            mismatched.append(relative_text)

    version_error: str | None = None
    try:
        plugin_version = _plugin_version(root)
        manifest_version = manifest.get("plugin_version")
        if manifest_version != plugin_version:
            version_error = "package-integrity manifest version does not match plugin.json"
    except IntegrityError as exc:
        version_error = str(exc)

    return {
        "ok": not missing and not mismatched and not unsafe and version_error is None,
        "profile": profile,
        "missing": missing,
        "mismatched": mismatched,
        "unsafe": unsafe,
        "manifest_error": version_error,
    }


def check_generated(root: Path = ROOT) -> dict[str, Any]:
    try:
        committed = load_manifest(root)
        generated = build_manifest(root)
    except (OSError, IntegrityError) as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": committed == generated, "committed": committed, "generated": generated}


def write_manifest(root: Path = ROOT) -> Path:
    root = root.expanduser().resolve(strict=True)
    path = _manifest_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_manifest(root)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return path


def _format_result(result: Mapping[str, Any]) -> str:
    if result.get("ok") is True:
        return "PACKAGE INTEGRITY PASS"
    lines = ["PACKAGE INTEGRITY FAIL"]
    for key in ("missing", "mismatched", "unsafe"):
        values = result.get(key)
        if isinstance(values, list) and values:
            lines.append(f"{key}: {', '.join(str(item) for item in values)}")
    error = result.get("manifest_error") or result.get("error")
    if error:
        lines.append(f"manifest: {error}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate or verify subagents-dispatch runtime package integrity.")
    parser.add_argument("--root", type=Path, default=ROOT)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check-generated", action="store_true")
    parser.add_argument("--profile", choices=("full", "update-bootstrap"), default="full")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.write:
        try:
            path = write_manifest(args.root)
        except (OSError, IntegrityError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            raise SystemExit(1) from None
        print(path)
        return
    result = check_generated(args.root) if args.check_generated else verify_package(args.root, profile=args.profile)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    else:
        print(_format_result(result))
    if result.get("ok") is not True:
        if args.check_generated and isinstance(result.get("generated"), dict):
            print(json.dumps(result["generated"], indent=2, sort_keys=True), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
