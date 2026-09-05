#!/usr/bin/env python3
"""Deterministic installation identity and explicit Plugin update lifecycle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ID = "subagents-dispatch@subagents-dispatch"
PLUGIN_NAME = "subagents-dispatch"
MARKETPLACE_NAME = "subagents-dispatch"
CANONICAL_REPOSITORY = "R-jed/subagents-dispatch"
CANONICAL_GIT_URLS = {
    "https://github.com/R-jed/subagents-dispatch",
    "https://github.com/R-jed/subagents-dispatch.git",
}
CANONICAL_MARKETPLACE_SOURCES = {CANONICAL_REPOSITORY, *CANONICAL_GIT_URLS}
MANAGED_PROFILE_MANIFEST = ".subagents-dispatch-agents.json"
PLUGIN_CACHE_RELATIVE = Path("plugins") / "cache" / MARKETPLACE_NAME / PLUGIN_NAME


class UpdateError(RuntimeError):
    """Explicit Plugin update cannot be completed safely."""


def _normalized_runtime_bytes(path: Path) -> bytes:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise UpdateError(f"runtime file is not readable UTF-8 text: {path}") from exc
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def _safe_relative_runtime_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise UpdateError(f"package identity contains unsafe runtime path: {value!r}")
    return path


def _package_identity(root: Path) -> str:
    """Return one exact runtime-package identity after verifying every manifested byte."""
    try:
        resolved_root = root.expanduser().resolve(strict=True)
    except OSError as exc:
        raise UpdateError("Plugin package root is unavailable for exact identity") from exc
    if not resolved_root.is_dir() or root.is_symlink():
        raise UpdateError("Plugin package root is unsafe for exact identity")

    manifest_path = resolved_root / ".codex-plugin" / "package-integrity.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise UpdateError("Plugin package integrity manifest is unavailable for exact identity")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise UpdateError("Plugin package integrity manifest is unreadable") from exc
    if not isinstance(manifest, dict):
        raise UpdateError("Plugin package integrity manifest is invalid")
    if manifest.get("algorithm") != "sha256" or manifest.get("normalization") != "utf-8-lf":
        raise UpdateError("Plugin package integrity contract is unsupported")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise UpdateError("Plugin package integrity manifest has no runtime files")
    plugin_version = package_version(resolved_root)
    if manifest.get("plugin_version") != plugin_version:
        raise UpdateError("Plugin package integrity version does not match plugin.json")

    for relative_text, expected in files.items():
        if not isinstance(relative_text, str) or not isinstance(expected, str) or len(expected) != 64:
            raise UpdateError("Plugin package integrity manifest contains an invalid file entry")
        relative = _safe_relative_runtime_path(relative_text)
        candidate = resolved_root.joinpath(*relative.parts)
        if candidate.is_symlink() or not candidate.is_file():
            raise UpdateError(f"Plugin package runtime file is unavailable: {relative_text}")
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(resolved_root)
        except (OSError, ValueError) as exc:
            raise UpdateError(f"Plugin package runtime file escapes package root: {relative_text}") from exc
        actual = hashlib.sha256(_normalized_runtime_bytes(candidate)).hexdigest()
        if actual != expected:
            raise UpdateError(f"Plugin package runtime bytes do not match integrity manifest: {relative_text}")

    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return hashlib.sha256(canonical).hexdigest()


def _plugin_cache_base(codex_home: Path) -> Path:
    return codex_home / PLUGIN_CACHE_RELATIVE


def _installed_cache_root(codex_home: Path, version: str) -> Path:
    root = _plugin_cache_base(codex_home) / version
    if root.is_symlink():
        raise UpdateError("installed Plugin cache root must not be a symlink")
    try:
        resolved = root.resolve(strict=True)
    except OSError as exc:
        raise UpdateError("installed Plugin cache root is unavailable") from exc
    if not resolved.is_dir():
        raise UpdateError("installed Plugin cache root is not a directory")
    return resolved


def _profile_manifest_records(codex_home: Path) -> tuple[bytes | None, dict[str, str]]:
    manifest_path = codex_home / MANAGED_PROFILE_MANIFEST
    if manifest_path.is_symlink():
        raise UpdateError("managed-profile manifest must not be a symlink")
    if not manifest_path.exists():
        return None, {}
    if not manifest_path.is_file():
        raise UpdateError("managed-profile manifest is not a regular file")
    raw = manifest_path.read_bytes()
    try:
        payload = json.loads(raw)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise UpdateError("managed-profile manifest is unreadable") from exc
    if not isinstance(payload, dict) or payload.get("managed_by") != "subagents-dispatch":
        raise UpdateError("managed-profile manifest ownership is invalid")
    hashes = payload.get("profile_hashes")
    if not isinstance(hashes, dict):
        raise UpdateError("managed-profile manifest has invalid profile hashes")
    result: dict[str, str] = {}
    for filename, digest in hashes.items():
        if (
            not isinstance(filename, str)
            or Path(filename).name != filename
            or not filename.endswith(".toml")
            or not isinstance(digest, str)
            or len(digest) != 64
        ):
            raise UpdateError("managed-profile manifest contains an unsafe profile record")
        result[filename] = digest
    return raw, result


def _verified_profile_bytes(codex_home: Path, records: Mapping[str, str]) -> dict[str, bytes]:
    agents_dir = codex_home / "agents"
    result: dict[str, bytes] = {}
    for filename, expected in records.items():
        path = agents_dir / filename
        if path.is_symlink() or not path.is_file():
            raise UpdateError(f"managed profile is unavailable before update: {filename}")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise UpdateError(f"managed profile drift blocks transactional update: {filename}")
        result[filename] = raw
    return result


def _reject_tree_symlinks(root: Path) -> None:
    if root.is_symlink():
        raise UpdateError(f"refusing symlinked Plugin-owned tree: {root}")
    for path in root.rglob("*"):
        if path.is_symlink():
            raise UpdateError(f"refusing symlink inside Plugin-owned tree: {path}")


def _snapshot_installed_product(
    codex_home: Path,
    *,
    before_version: str,
    backup_root: Path,
) -> dict[str, Any]:
    """Freeze only Plugin-owned cache/profile state needed for exact rollback."""
    cache_base = _plugin_cache_base(codex_home)
    if cache_base.is_symlink() or not cache_base.is_dir():
        raise UpdateError("installed Plugin cache base is unavailable for transactional update")
    _reject_tree_symlinks(cache_base)
    installed_root = _installed_cache_root(codex_home, before_version)
    before_identity = _package_identity(installed_root)

    cache_backup = backup_root / "plugin-cache"
    shutil.copytree(cache_base, cache_backup, symlinks=False)
    manifest_bytes, profile_records = _profile_manifest_records(codex_home)
    profile_bytes = _verified_profile_bytes(codex_home, profile_records)
    return {
        "before_version": before_version,
        "before_identity": before_identity,
        "cache_backup": cache_backup,
        "profile_manifest": manifest_bytes,
        "profile_records": dict(profile_records),
        "profile_bytes": profile_bytes,
    }


def _restore_profile_snapshot(codex_home: Path, snapshot: Mapping[str, Any]) -> None:
    agents_dir = codex_home / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    before_records = dict(snapshot.get("profile_records", {}))
    before_bytes = dict(snapshot.get("profile_bytes", {}))
    current_manifest, current_records = _profile_manifest_records(codex_home)
    del current_manifest

    for filename, digest in current_records.items():
        if filename in before_records:
            continue
        path = agents_dir / filename
        if not path.exists():
            continue
        if path.is_symlink() or not path.is_file():
            raise UpdateError(f"rollback cannot safely remove managed profile: {filename}")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise UpdateError(f"rollback found drift in newly managed profile: {filename}")
        path.unlink()

    for filename, raw in before_bytes.items():
        path = agents_dir / filename
        if path.is_symlink():
            raise UpdateError(f"rollback refuses symlinked managed profile: {filename}")
        path.write_bytes(raw)

    manifest_path = codex_home / MANAGED_PROFILE_MANIFEST
    manifest_before = snapshot.get("profile_manifest")
    if manifest_before is None:
        manifest_path.unlink(missing_ok=True)
    elif isinstance(manifest_before, bytes):
        manifest_path.write_bytes(manifest_before)
    else:
        raise UpdateError("rollback snapshot has invalid managed-profile manifest")


def _rollback_installed_product(codex_home: Path, snapshot: Mapping[str, Any]) -> None:
    """Restore the exact previous Plugin cache and Plugin-owned profile unit."""
    cache_base = _plugin_cache_base(codex_home)
    cache_backup = snapshot.get("cache_backup")
    if not isinstance(cache_backup, Path) or not cache_backup.is_dir():
        raise UpdateError("transaction rollback cache snapshot is unavailable")
    if cache_base.is_symlink():
        raise UpdateError("transaction rollback refuses symlinked Plugin cache base")
    if cache_base.exists():
        shutil.rmtree(cache_base)
    cache_base.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(cache_backup, cache_base, symlinks=False)
    _restore_profile_snapshot(codex_home, snapshot)

    version = snapshot.get("before_version")
    identity = snapshot.get("before_identity")
    if not isinstance(version, str) or not isinstance(identity, str):
        raise UpdateError("transaction rollback snapshot identity is invalid")
    restored_root = _installed_cache_root(codex_home, version)
    if _package_identity(restored_root) != identity:
        raise UpdateError("transaction rollback did not restore the previous Plugin identity")
    _, records = _profile_manifest_records(codex_home)
    _verified_profile_bytes(codex_home, records)


def _layer(
    status: str,
    summary: str,
    *,
    action: str | None = None,
    **details: Any,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": "Plugin installation",
        "status": status,
        "summary": summary,
        "details": details,
    }
    if action is not None:
        result["action"] = action
    return result


def package_version(root: Path = ROOT) -> str:
    path = root / ".codex-plugin" / "plugin.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise UpdateError(f"packaged Plugin manifest is unreadable: {exc}") from exc
    version = payload.get("version") if isinstance(payload, dict) else None
    if not isinstance(version, str) or not version.strip():
        raise UpdateError("packaged Plugin version is missing")
    return version.strip()


def _core_semver(value: str) -> tuple[int, int, int] | None:
    parts = value.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)  # type: ignore[return-value]


def _matching_installed(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = payload.get("installed")
    if not isinstance(rows, list):
        return []
    return [
        item
        for item in rows
        if isinstance(item, Mapping)
        and item.get("pluginId") == PLUGIN_ID
        and item.get("name") == PLUGIN_NAME
        and item.get("marketplaceName") == MARKETPLACE_NAME
        and item.get("installed") is True
    ]


def _canonical_marketplace_issue(row: Mapping[str, Any]) -> str | None:
    marketplace_source = row.get("marketplaceSource")
    if not isinstance(marketplace_source, Mapping):
        return "installed Marketplace source metadata is unavailable"
    if marketplace_source.get("sourceType") != "git":
        return "configured Marketplace source is not a Git source"
    if marketplace_source.get("source") not in CANONICAL_MARKETPLACE_SOURCES:
        return "configured Marketplace origin does not match R-jed/subagents-dispatch"
    return None


def _local_source_root(row: Mapping[str, Any]) -> Path:
    source = row.get("source")
    if not isinstance(source, Mapping) or source.get("source") != "local":
        raise UpdateError("installed Plugin source must be the Marketplace-local source")
    raw_path = source.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise UpdateError("Marketplace-local Plugin source path is unavailable")
    root = Path(raw_path).expanduser()
    if not root.is_absolute():
        raise UpdateError("Marketplace-local Plugin source path must be absolute")
    if root.is_symlink():
        raise UpdateError("Marketplace-local Plugin source root must not be a symlink")
    try:
        root = root.resolve(strict=True)
    except OSError as exc:
        raise UpdateError("Marketplace-local Plugin source root is unavailable") from exc
    if not root.is_dir():
        raise UpdateError("Marketplace-local Plugin source root is not a directory")
    return root


def _available_version_from_local_source(row: Mapping[str, Any]) -> str:
    root = _local_source_root(row)
    manifest = root / ".codex-plugin" / "plugin.json"
    if manifest.is_symlink() or not manifest.is_file():
        raise UpdateError("Marketplace-local Plugin manifest is unavailable or unsafe")
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise UpdateError("Marketplace-local Plugin manifest is unreadable") from exc
    if not isinstance(payload, dict) or payload.get("name") != PLUGIN_NAME:
        raise UpdateError("Marketplace-local Plugin manifest identity is invalid")
    version = payload.get("version")
    if not isinstance(version, str) or _core_semver(version.strip()) is None:
        raise UpdateError("Marketplace-local Plugin version is not a stable semantic version")
    return version.strip()


def _source_mode(row: Mapping[str, Any]) -> str:
    _local_source_root(row)
    return "marketplace-local"


def _available_version(row: Mapping[str, Any]) -> str:
    _source_mode(row)
    return _available_version_from_local_source(row)


def _canonical_source_issue(row: Mapping[str, Any]) -> str | None:
    issue = _canonical_marketplace_issue(row)
    if issue is not None:
        return issue
    try:
        _source_mode(row)
    except UpdateError as exc:
        return str(exc)
    return None


def require_canonical_installed_source(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    matches = _matching_installed(payload)
    if len(matches) != 1:
        raise UpdateError("exactly one installed subagents-dispatch Plugin is required")
    issue = _canonical_source_issue(matches[0])
    if issue is not None:
        raise UpdateError(issue)
    return matches[0]


def installation_layer_from_payload(
    payload: Mapping[str, Any],
    *,
    package_version: str,
    exact_identity_match: bool | None = None,
) -> dict[str, Any]:
    rows = payload.get("installed")
    if not isinstance(rows, list):
        return _layer("FAIL", "Codex Plugin information is unavailable", matches=0)

    matches = _matching_installed(payload)
    if len(matches) == 0:
        return _layer(
            "WARN",
            "subagents-dispatch is not installed",
            action="Install subagents-dispatch, then start a fresh Codex session.",
            matches=0,
            package_version=package_version,
        )
    if len(matches) != 1:
        return _layer(
            "FAIL",
            "Multiple subagents-dispatch installations were found",
            action="Resolve the duplicate Plugin installation before using Orchestrate or updating.",
            matches=len(matches),
            package_version=package_version,
        )

    row = matches[0]
    source = row.get("source")
    marketplace_source = row.get("marketplaceSource")
    source_path = source.get("path") if isinstance(source, Mapping) else None
    marketplace_origin = (
        marketplace_source.get("source") if isinstance(marketplace_source, Mapping) else None
    )
    base_details = {
        "matches": 1,
        "package_version": package_version,
        "source_path": source_path,
        "marketplace_source": marketplace_origin,
    }
    source_issue = _canonical_source_issue(row)
    if source_issue is not None:
        return _layer(
            "FAIL",
            "Installed Plugin source cannot be verified",
            action="Reinstall from the official R-jed/subagents-dispatch Marketplace source.",
            source_issue=source_issue,
            **base_details,
        )

    try:
        source_mode = _source_mode(row)
        available_version = _available_version(row)
    except UpdateError as exc:
        return _layer(
            "FAIL",
            "Plugin source cannot be verified",
            action="Repair or reinstall from the official Marketplace source before using the Plugin.",
            source_error=str(exc),
            **base_details,
        )

    installed_version = row.get("version")
    if not isinstance(installed_version, str) or not installed_version.strip():
        return _layer(
            "FAIL",
            "Installed Plugin version cannot be verified",
            source_mode=source_mode,
            **base_details,
        )
    installed_version = installed_version.strip()
    installed_core = _core_semver(installed_version)
    available_core = _core_semver(available_version)
    if installed_core is None:
        return _layer(
            "FAIL",
            "Installed Plugin version is invalid",
            action="Reinstall the Plugin from the official Marketplace source.",
            installed_version=installed_version,
            available_version=available_version,
            source_mode=source_mode,
            **base_details,
        )
    assert available_core is not None

    update_available = available_core > installed_core or exact_identity_match is False
    source_older = available_core < installed_core
    package_cache_skew = package_version != installed_version
    enabled = row.get("enabled")
    details = {
        **base_details,
        "source_mode": source_mode,
        "installed_version": installed_version,
        "available_version": available_version,
        "enabled": enabled,
        "update_available": update_available,
        "package_cache_skew": package_cache_skew,
        "exact_identity_match": exact_identity_match,
    }

    if source_older:
        return _layer(
            "FAIL",
            "Marketplace version is older than the installed Plugin",
            action="Review the configured Marketplace source before changing the installed Plugin.",
            **details,
        )
    if enabled is False:
        return _layer(
            "WARN",
            "subagents-dispatch is installed but disabled in Codex",
            action="Enable the Plugin and start a fresh Codex session before using Orchestrate.",
            **details,
        )
    if update_available:
        if available_core == installed_core and exact_identity_match is False:
            return _layer(
                "WARN",
                "Marketplace package bytes differ from the installed Plugin at the same version",
                action="Run the Plugin updater, then start a fresh Codex session.",
                **details,
            )
        return _layer(
            "WARN",
            "A newer stable version is available",
            action="Run the Plugin updater, then start a fresh Codex session.",
            **details,
        )
    if package_cache_skew:
        return _layer(
            "WARN",
            "This Codex session is using a different Plugin version than the installed version",
            action="Start a fresh Codex session to load the installed Plugin version.",
            **details,
        )
    if available_version != installed_version:
        return _layer(
            "WARN",
            "Marketplace and installed Plugin versions differ",
            action="Run the Plugin updater, then review the installed version.",
            **details,
        )
    return _layer("OK", "Installed Plugin is current", **details)


def resolve_codex_binary(explicit: str | None = None) -> str | None:
    candidate = explicit or os.environ.get("SUBAGENTS_DISPATCH_CODEX_BIN")
    if candidate:
        path = Path(candidate).expanduser()
        if path.is_file():
            return str(path.resolve())
        return shutil.which(candidate)
    return shutil.which("codex")


def _run_json(
    codex_bin: str,
    args: Sequence[str],
    *,
    codex_home: Path,
    timeout: int = 60,
) -> dict[str, Any]:
    env = os.environ.copy()
    env["CODEX_HOME"] = str(codex_home)
    try:
        result = subprocess.run(
            [codex_bin, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise UpdateError(
            f"Codex command could not complete: {args[0] if args else 'unknown'}"
        ) from exc
    if result.returncode != 0:
        raise UpdateError(f"Codex command failed safely: {' '.join(args[:3])}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise UpdateError("Codex command did not return valid JSON") from exc
    if not isinstance(payload, dict):
        raise UpdateError("Codex command JSON must be an object")
    return payload


def _run_python(
    python: str,
    script: Path,
    args: Sequence[str],
    *,
    timeout: int = 90,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            [python, str(script), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=dict(env) if env is not None else None,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise UpdateError(
            f"bundled verification helper could not complete: {script.name}"
        ) from exc


def _validate_add_result(payload: Mapping[str, Any]) -> tuple[str, Path]:
    if payload.get("pluginId") != PLUGIN_ID:
        raise UpdateError("Codex installed an unexpected Plugin identity")
    if payload.get("name") != PLUGIN_NAME or payload.get("marketplaceName") != MARKETPLACE_NAME:
        raise UpdateError("Codex installed Plugin metadata does not match subagents-dispatch")
    version = payload.get("version")
    installed_path = payload.get("installedPath")
    if not isinstance(version, str) or not version.strip():
        raise UpdateError("Codex install result omitted the Plugin version")
    if _core_semver(version.strip()) is None:
        raise UpdateError("Codex install result version is not a stable semantic version")
    if not isinstance(installed_path, str) or not installed_path.strip():
        raise UpdateError("Codex install result omitted the installed Plugin root")
    root = Path(installed_path).expanduser()
    if not root.is_absolute():
        raise UpdateError("Codex installed Plugin root must be absolute")
    try:
        root = root.resolve(strict=True)
    except OSError as exc:
        raise UpdateError("Codex installed Plugin root is unavailable") from exc
    if not root.is_dir():
        raise UpdateError("Codex installed Plugin root is not a directory")
    return version.strip(), root


def _verify_installed_manifest(root: Path, expected_version: str) -> None:
    manifest = root / ".codex-plugin" / "plugin.json"
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise UpdateError("updated installed Plugin manifest is unreadable") from exc
    if not isinstance(payload, dict):
        raise UpdateError("updated installed Plugin manifest is invalid")
    if payload.get("name") != PLUGIN_NAME or payload.get("version") != expected_version:
        raise UpdateError(
            "updated installed Plugin manifest does not match Codex install result"
        )


def _verify_new_package(
    root: Path,
    *,
    codex_home: Path,
    codex_bin: str,
    expected_version: str,
) -> None:
    integrity = root / "scripts" / "package_integrity.py"
    installer = root / "scripts" / "install-agents.py"
    doctor = root / "scripts" / "doctor.py"
    for path in (integrity, installer, doctor):
        if not path.is_file() or path.is_symlink():
            raise UpdateError(f"updated Plugin is missing a safe {path.name}")

    integrity_result = _run_python(sys.executable, integrity, ["--root", str(root)])
    if integrity_result.returncode != 0:
        raise UpdateError("updated Plugin package integrity verification failed")
    install_result = _run_python(
        sys.executable, installer, ["--codex-home", str(codex_home)]
    )
    if install_result.returncode != 0:
        raise UpdateError("updated managed-Agent profile reconciliation failed")
    check_result = _run_python(
        sys.executable,
        installer,
        ["--codex-home", str(codex_home), "--check"],
    )
    if check_result.returncode != 0:
        raise UpdateError("updated managed-Agent profile verification failed")

    env = os.environ.copy()
    env["CODEX_HOME"] = str(codex_home)
    env["SUBAGENTS_DISPATCH_CODEX_BIN"] = codex_bin
    doctor_result = _run_python(
        sys.executable,
        doctor,
        [
            "--codex-home",
            str(codex_home),
            "--json",
            "--check",
            "--thread-id",
            "plugin-update-verification",
        ],
        env=env,
    )
    if doctor_result.returncode != 0:
        raise UpdateError("updated Plugin health check reported a blocking failure")
    try:
        report = json.loads(doctor_result.stdout)
    except json.JSONDecodeError as exc:
        raise UpdateError("updated Plugin health check returned invalid JSON") from exc
    if not isinstance(report, dict) or set(report) != {"layers", "actions"}:
        raise UpdateError("updated Plugin health report format is unsupported")
    layers = report.get("layers")
    actions = report.get("actions")
    if not isinstance(layers, list) or not isinstance(actions, list):
        raise UpdateError("updated Plugin health report is invalid")
    if actions:
        raise UpdateError(
            "post-update health check performed an unexpected maintenance action"
        )

    observed = {
        item.get("name"): item.get("status")
        for item in layers
        if isinstance(item, dict)
    }
    expected_layers = {
        "Plugin package",
        "Managed Agents",
        "Host integration",
        "Orchestration state",
    }
    if set(observed) != expected_layers:
        raise UpdateError("updated Plugin health report is unsupported")
    if observed["Plugin package"] != "OK":
        raise UpdateError("updated Plugin health check did not verify the Plugin package")
    if observed["Managed Agents"] != "OK":
        raise UpdateError(
            "updated Plugin health check did not verify managed Agent profiles"
        )
    if observed["Host integration"] not in {"OK", "WARN", "UNKNOWN"}:
        raise UpdateError(
            "updated Plugin health check reported an unsafe Host integration state"
        )
    if observed["Orchestration state"] != "OK":
        raise UpdateError(
            "updated Plugin health check reported an unsafe orchestration state"
        )
    if package_version(root) != expected_version:
        raise UpdateError("updated package version changed during post-update verification")


def update_plugin(
    *,
    codex_home: Path,
    codex_bin: str | None = None,
) -> dict[str, Any]:
    binary = resolve_codex_binary(codex_bin)
    if binary is None:
        raise UpdateError("Codex CLI is unavailable; explicit Plugin update cannot run")

    before_payload = _run_json(
        binary, ["plugin", "list", "--json"], codex_home=codex_home
    )
    before_row = require_canonical_installed_source(before_payload)
    before_version = before_row.get("version")
    if not isinstance(before_version, str) or _core_semver(before_version.strip()) is None:
        raise UpdateError(
            "installed Plugin version is unavailable or not a stable semantic version before update"
        )
    before_version = before_version.strip()

    with tempfile.TemporaryDirectory(prefix="subagents-dispatch-update-") as temp_name:
        snapshot = _snapshot_installed_product(
            codex_home,
            before_version=before_version,
            backup_root=Path(temp_name),
        )

        upgrade_result = _run_json(
            binary,
            ["plugin", "marketplace", "upgrade", MARKETPLACE_NAME, "--json"],
            codex_home=codex_home,
            timeout=120,
        )
        errors = upgrade_result.get("errors")
        if not isinstance(errors, list) or errors:
            raise UpdateError("Marketplace upgrade did not complete cleanly")

        refreshed_payload = _run_json(
            binary, ["plugin", "list", "--json"], codex_home=codex_home
        )
        refreshed_row = require_canonical_installed_source(refreshed_payload)
        target_version = _available_version(refreshed_row)
        target_source_root = _local_source_root(refreshed_row)
        target_identity = _package_identity(target_source_root)

        before_core = _core_semver(before_version)
        target_core = _core_semver(target_version)
        assert before_core is not None and target_core is not None
        if target_core < before_core:
            raise UpdateError("refreshed Marketplace source is older than the installed Plugin")

        if target_version == before_version and target_identity == snapshot["before_identity"]:
            return {
                "schema_version": 3,
                "changed": False,
                "from_version": before_version,
                "to_version": before_version,
                "marketplace_version": target_version,
                "package_identity": target_identity,
                "restart_required": package_version() != before_version,
                "steps": [
                    {
                        "name": "Marketplace",
                        "status": "OK",
                        "summary": "Marketplace is current",
                    },
                    {
                        "name": "Plugin",
                        "status": "OK",
                        "summary": "Installed Plugin exact identity is already current",
                    },
                ],
            }

        try:
            add_result = _run_json(
                binary,
                ["plugin", "add", PLUGIN_ID, "--json"],
                codex_home=codex_home,
                timeout=120,
            )
            installed_version, installed_root = _validate_add_result(add_result)
            if installed_version != target_version:
                raise UpdateError(
                    "Codex installed version does not match the refreshed Marketplace package"
                )
            _verify_installed_manifest(installed_root, installed_version)
            if _package_identity(installed_root) != target_identity:
                raise UpdateError(
                    "installed Plugin exact identity does not match the refreshed Marketplace package"
                )

            post_payload = _run_json(
                binary, ["plugin", "list", "--json"], codex_home=codex_home
            )
            post_layer = installation_layer_from_payload(
                post_payload, package_version=installed_version
            )
            if post_layer.get("status") != "OK":
                raise UpdateError(
                    "post-update Codex Plugin inventory did not converge to the canonical installed release"
                )

            _verify_new_package(
                installed_root,
                codex_home=codex_home,
                codex_bin=binary,
                expected_version=installed_version,
            )
        except Exception as exc:
            try:
                _rollback_installed_product(codex_home, snapshot)
            except Exception as rollback_exc:
                raise UpdateError(
                    f"update failed and exact previous installed product could not be restored: {rollback_exc}"
                ) from exc
            if isinstance(exc, UpdateError):
                detail = str(exc)
            else:
                detail = exc.__class__.__name__
            raise UpdateError(
                f"update failed; exact previous installed product restored: {detail}"
            ) from exc

        return {
            "schema_version": 3,
            "changed": True,
            "from_version": before_version,
            "to_version": installed_version,
            "marketplace_version": target_version,
            "package_identity": target_identity,
            "installed_root": str(installed_root),
            "restart_required": True,
            "steps": [
                {
                    "name": "Marketplace",
                    "status": "OK",
                    "summary": f"Version {target_version} is available",
                },
                {
                    "name": "Plugin",
                    "status": "OK",
                    "summary": f"Installed {installed_version} with exact package identity",
                },
                {
                    "name": "Managed Agent profiles",
                    "status": "OK",
                    "summary": "Managed Agent profiles are current",
                },
                {"name": "Health check", "status": "OK", "summary": "Passed"},
            ],
        }


def render_update(report: Mapping[str, Any]) -> str:
    lines = ["Subagents Dispatch Update", ""]
    for item in report.get("steps", []):
        if isinstance(item, Mapping):
            lines.append(
                f"[{item.get('status', 'UNKNOWN')}] {item.get('name', 'Unknown')}: {item.get('summary', '')}"
            )
    lines.extend(
        ["", f"Version: {report.get('from_version')} -> {report.get('to_version')}"]
    )
    if report.get("restart_required") is True:
        lines.append(
            "[RESTART] Start a fresh Codex session to use the installed version."
        )
    else:
        lines.append("[OK] Installed Plugin is already current.")
    lines.extend(["", "Overall: UPDATE COMPLETE"])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Explicitly update the installed subagents-dispatch Plugin."
    )
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")),
    )
    parser.add_argument("--codex-bin")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    codex_home = args.codex_home.expanduser()
    if codex_home.is_symlink():
        print("ERROR: refusing symlinked Codex home", file=sys.stderr)
        raise SystemExit(1)
    try:
        codex_home = codex_home.resolve(strict=True)
    except OSError:
        print("ERROR: Codex home is unavailable", file=sys.stderr)
        raise SystemExit(1)
    try:
        report = update_plugin(codex_home=codex_home, codex_bin=args.codex_bin)
    except UpdateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
    if args.json:
        print(
            json.dumps(
                report, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
        )
    else:
        print(render_update(report))


if __name__ == "__main__":
    main()
