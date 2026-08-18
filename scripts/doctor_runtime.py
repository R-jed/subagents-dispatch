#!/usr/bin/env python3
"""Installed-plugin Doctor runtime entry point."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import doctor_runtime_core as core
import plugin_update


_base_diagnose = core.diagnose


def _merge_plugin_installation(report: dict[str, Any], codex_home: Path) -> dict[str, Any]:
    layers = report.get("layers")
    if not isinstance(layers, list) or not layers or not isinstance(layers[0], dict):
        return report
    package = layers[0]
    if package.get("name") != "Plugin package" or package.get("status") == "FAIL":
        return report
    details = package.get("details")
    version = details.get("version") if isinstance(details, dict) else None
    if not isinstance(version, str) or not version.strip():
        return report

    installation = plugin_update.diagnose_installation(
        codex_home=codex_home,
        package_version_value=version,
    )
    install_status = installation.get("status")
    install_details = installation.get("details")
    package_details = dict(details)
    package_details["installation"] = install_details if isinstance(install_details, dict) else {}

    if install_status == "OK":
        package.update(
            status="OK",
            summary="package, public Skills, and Codex Plugin registration agree",
            details=package_details,
        )
        package.pop("action", None)
    elif install_status in {"WARN", "UNKNOWN"}:
        package.update(
            status=install_status,
            summary=f"package and public Skills are intact; {installation.get('summary', 'Codex Plugin registration needs attention')}",
            details=package_details,
        )
        action = installation.get("action")
        if isinstance(action, str) and action.strip():
            package["action"] = action
        else:
            package.pop("action", None)
    else:
        package.update(
            status="FAIL",
            summary=f"Codex Plugin registration is unsafe: {installation.get('summary', 'installation identity is invalid')}",
            details=package_details,
        )
        action = installation.get("action")
        if isinstance(action, str) and action.strip():
            package["action"] = action
        else:
            package.pop("action", None)

    blocked = any(isinstance(item, dict) and item.get("status") == "FAIL" for item in layers)
    degraded = any(
        isinstance(item, dict) and item.get("status") in {"WARN", "UNKNOWN"}
        for item in layers
    )
    report["healthy"] = not blocked
    report["status"] = "BLOCKED" if blocked else "DEGRADED" if degraded else "HEALTHY"
    return report


def diagnose(args, codex_home: Path) -> dict[str, Any]:
    return _merge_plugin_installation(_base_diagnose(args, codex_home), codex_home)


def main() -> None:
    core.diagnose = diagnose
    core.main()


if __name__ == "__main__":
    main()
