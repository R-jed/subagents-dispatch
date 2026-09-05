#!/usr/bin/env python3
"""Explicitly refresh the canonical subagents-dispatch Marketplace and report update state."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping

from plugin_update import (
    MARKETPLACE_NAME,
    UpdateError,
    _installed_cache_root,
    _local_source_root,
    _package_identity,
    _run_json,
    installation_layer_from_payload,
    package_version,
    require_canonical_installed_source,
    resolve_codex_binary,
)


def check_update(
    *,
    codex_home: Path,
    codex_bin: str | None = None,
) -> dict[str, Any]:
    binary = resolve_codex_binary(codex_bin)
    if binary is None:
        raise UpdateError("Codex CLI is unavailable; explicit update check cannot run")

    before = _run_json(binary, ["plugin", "list", "--json"], codex_home=codex_home)
    before_row = require_canonical_installed_source(before)

    upgrade_result = _run_json(
        binary,
        ["plugin", "marketplace", "upgrade", MARKETPLACE_NAME, "--json"],
        codex_home=codex_home,
        timeout=120,
    )
    errors = upgrade_result.get("errors")
    if not isinstance(errors, list) or errors:
        raise UpdateError("Marketplace refresh did not complete cleanly")

    inventory = _run_json(binary, ["plugin", "list", "--json"], codex_home=codex_home)
    refreshed_row = require_canonical_installed_source(inventory)
    installed_version = before_row.get("version")
    if not isinstance(installed_version, str) or not installed_version.strip():
        raise UpdateError("installed Plugin version is unavailable for exact identity check")
    installed_identity = _package_identity(
        _installed_cache_root(codex_home, installed_version.strip())
    )
    available_identity = _package_identity(_local_source_root(refreshed_row))
    installation = installation_layer_from_payload(
        inventory,
        package_version=package_version(),
        exact_identity_match=installed_identity == available_identity,
    )
    details = installation.get("details")
    if not isinstance(details, dict):
        raise UpdateError("refreshed Plugin installation report is invalid")

    return {
        "schema_version": 1,
        "marketplace_refreshed": True,
        "plugin_install_performed": False,
        "managed_profiles_mutated": False,
        "installed_package_identity": installed_identity,
        "available_package_identity": available_identity,
        "installation": installation,
    }


def render(report: Mapping[str, Any]) -> str:
    installation = report.get("installation")
    item = installation if isinstance(installation, Mapping) else {}
    details = item.get("details")
    detail_map = details if isinstance(details, Mapping) else {}
    update_available = detail_map.get("update_available") is True
    status = str(item.get("status", "UNKNOWN"))

    lines = [
        "Subagents Dispatch Update Check",
        "",
        "[OK] Marketplace: refreshed",
        f"[{status}] Plugin: {item.get('summary', '')}",
        f"Installed: {detail_map.get('installed_version', 'UNKNOWN')}",
        f"Available: {detail_map.get('available_version', 'UNKNOWN')}",
    ]
    action = item.get("action")
    if isinstance(action, str) and action.strip():
        lines.append(f"Action: {action.strip()}")
    lines.append("")
    if status == "FAIL":
        lines.append("Overall: REVIEW REQUIRED")
    elif update_available:
        lines.append("Overall: UPDATE AVAILABLE")
    elif status == "OK":
        lines.append("Overall: CURRENT")
    else:
        lines.append("Overall: CHECK COMPLETE WITH LIMITATION")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh the subagents-dispatch Marketplace and report update state without installing a Plugin."
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
        report = check_update(codex_home=codex_home, codex_bin=args.codex_bin)
    except UpdateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from None

    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    else:
        print(render(report))

    installation = report.get("installation")
    if isinstance(installation, dict) and installation.get("status") == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
