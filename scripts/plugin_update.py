#!/usr/bin/env python3
"""Deterministic installation identity and explicit Plugin update lifecycle."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
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


class UpdateError(RuntimeError):
    """Explicit Plugin update cannot be completed safely."""


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

    update_available = available_core > installed_core
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


def read_plugin_inventory(
    *,
    codex_home: Path,
    codex_bin: str | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    binary = resolve_codex_binary(codex_bin)
    if binary is None:
        return None, "Codex CLI is unavailable"
    try:
        return _run_json(
            binary, ["plugin", "list", "--json"], codex_home=codex_home
        ), None
    except UpdateError as exc:
        return None, str(exc)


def diagnose_installation(
    *,
    codex_home: Path,
    package_version_value: str,
    codex_bin: str | None = None,
) -> dict[str, Any]:
    payload, error = read_plugin_inventory(codex_home=codex_home, codex_bin=codex_bin)
    if payload is None:
        return _layer(
            "UNKNOWN",
            "Installed Plugin status could not be checked",
            action="Run Doctor in a Codex environment with the Codex CLI available.",
            package_version=package_version_value,
            observed=False,
            limitation=error,
        )
    result = installation_layer_from_payload(payload, package_version=package_version_value)
    result["details"]["observed"] = True
    return result


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

    before_core = _core_semver(before_version)
    target_core = _core_semver(target_version)
    assert before_core is not None and target_core is not None
    if target_core < before_core:
        raise UpdateError("refreshed Marketplace source is older than the installed Plugin")

    if target_version == before_version:
        return {
            "schema_version": 2,
            "changed": False,
            "from_version": before_version,
            "to_version": before_version,
            "marketplace_version": target_version,
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
                    "summary": "Installed Plugin is already current",
                },
            ],
        }

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

    return {
        "schema_version": 2,
        "changed": True,
        "from_version": before_version,
        "to_version": installed_version,
        "marketplace_version": target_version,
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
                "summary": f"Installed {installed_version}",
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
