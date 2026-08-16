#!/usr/bin/env python3
"""Integrity bootstrap for deterministic subagents-dispatch Doctor diagnostics."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
INTEGRITY_HELPER = ROOT / "scripts" / "package_integrity.py"
INTEGRITY_MANIFEST = ROOT / ".codex-plugin" / "package-integrity.json"
RUNTIME = ROOT / "scripts" / "doctor_runtime.py"
UPDATER = ROOT / "scripts" / "plugin_update.py"


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def _bootstrap_failure(result: Mapping[str, Any], *, as_json: bool) -> None:
    details: list[str] = []
    for key in ("missing", "mismatched", "unsafe"):
        values = result.get(key)
        if isinstance(values, list):
            details.extend(str(item) for item in values)
    manifest_error = result.get("manifest_error")
    if manifest_error:
        details.append(str(manifest_error))
    summary = "runtime package is incomplete or differs from its shipped integrity manifest"
    if as_json:
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "healthy": False,
                    "bootstrap": {
                        "name": "Plugin package integrity",
                        "status": "FAIL",
                        "summary": summary,
                        "details": result,
                    },
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    else:
        print("Subagents Dispatch Doctor")
        print("Mode: package-integrity bootstrap")
        print()
        print(f"[FAIL] Plugin package integrity: {summary}")
        if details:
            print(f"       Affected: {', '.join(details)}")
        print("       Action: use explicit Plugin update when a newer canonical release is available; otherwise reinstall the canonical Marketplace release.")
        print()
        print("Overall: UNHEALTHY")
    raise SystemExit(1)


def _normalized_digest(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def _verify_integrity_helper_before_import(*, as_json: bool) -> None:
    if INTEGRITY_MANIFEST.is_symlink() or not INTEGRITY_MANIFEST.is_file():
        _bootstrap_failure(
            {
                "ok": False,
                "missing": [".codex-plugin/package-integrity.json"],
                "mismatched": [],
                "unsafe": [],
                "manifest_error": "package-integrity manifest is unavailable",
            },
            as_json=as_json,
        )
    if INTEGRITY_HELPER.is_symlink() or not INTEGRITY_HELPER.is_file():
        _bootstrap_failure(
            {
                "ok": False,
                "missing": ["scripts/package_integrity.py"],
                "mismatched": [],
                "unsafe": [],
                "manifest_error": "package-integrity helper is unavailable",
            },
            as_json=as_json,
        )
    try:
        payload = json.loads(INTEGRITY_MANIFEST.read_text(encoding="utf-8"))
        files = payload.get("files") if isinstance(payload, dict) else None
        expected = files.get("scripts/package_integrity.py") if isinstance(files, dict) else None
        actual = _normalized_digest(INTEGRITY_HELPER)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _bootstrap_failure(
            {
                "ok": False,
                "missing": [],
                "mismatched": [],
                "unsafe": [],
                "manifest_error": f"package-integrity bootstrap is unreadable: {exc}",
            },
            as_json=as_json,
        )
    if not isinstance(expected, str) or len(expected) != 64 or actual != expected:
        _bootstrap_failure(
            {
                "ok": False,
                "missing": [],
                "mismatched": ["scripts/package_integrity.py"],
                "unsafe": [],
                "manifest_error": None,
            },
            as_json=as_json,
        )


def _load_integrity():
    as_json = "--json" in sys.argv[1:]
    _verify_integrity_helper_before_import(as_json=as_json)
    spec = importlib.util.spec_from_file_location("subagents_dispatch_package_integrity", INTEGRITY_HELPER)
    if spec is None or spec.loader is None:
        _bootstrap_failure(
            {
                "ok": False,
                "missing": [],
                "mismatched": [],
                "unsafe": ["scripts/package_integrity.py"],
                "manifest_error": "package-integrity helper cannot be loaded",
            },
            as_json=as_json,
        )
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        _bootstrap_failure(
            {
                "ok": False,
                "missing": [],
                "mismatched": [],
                "unsafe": ["scripts/package_integrity.py"],
                "manifest_error": f"package-integrity helper failed to load: {exc}",
            },
            as_json=as_json,
        )
    return module


def _update_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--update", action="store_true")
    parser.add_argument("--codex-home")
    parser.add_argument("--json", action="store_true")
    parsed, unknown = parser.parse_known_args(argv)
    if unknown or not parsed.update:
        raise ValueError("--update cannot be combined with other Doctor checks or mutations")
    return parsed


def _run_update(argv: list[str], integrity) -> None:
    try:
        args = _update_args(argv)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
    result = integrity.verify_package(ROOT, profile="update-bootstrap")
    if result.get("ok") is not True:
        _bootstrap_failure(result, as_json=args.json)
    command = [sys.executable, str(UPDATER)]
    if args.codex_home is not None:
        command.extend(["--codex-home", args.codex_home])
    if args.json:
        command.append("--json")
    raise SystemExit(subprocess.call(command))


def main() -> None:
    argv = sys.argv[1:]
    integrity = _load_integrity()
    if "--update" in argv:
        _run_update(argv, integrity)
    result = integrity.verify_package(ROOT, profile="full")
    if result.get("ok") is not True:
        _bootstrap_failure(result, as_json="--json" in argv)
    if RUNTIME.is_symlink() or not RUNTIME.is_file():
        _bootstrap_failure(
            {
                "ok": False,
                "missing": ["scripts/doctor_runtime.py"],
                "mismatched": [],
                "unsafe": [],
                "manifest_error": None,
            },
            as_json="--json" in argv,
        )
    raise SystemExit(subprocess.call([sys.executable, str(RUNTIME), *argv]))


if __name__ == "__main__":
    main()
