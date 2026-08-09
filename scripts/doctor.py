#!/usr/bin/env python3
"""Deterministic, read-only diagnostics for subagents-dispatch."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dispatch_state import (  # type: ignore[import-not-found]
    ACTIVE_STATES,
    DEFAULT_STALE_AFTER,
    LOCK_FILE,
    STATE_DIRECTORY,
    StateCorruptError,
    StateIdentityError,
    StatePathError,
    cleanup_stale_states,
    is_stale,
    load_state,
    resolve_thread_id,
)
from legacy_migration import (
    LEGACY_LOCK_NAME,
    LEGACY_MANIFEST_NAME,
    LEGACY_PROFILE_FILES,
    MigrationState,
    detect_legacy_state,
    format_migration_state,
    legacy_manifest_status,
)


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_MANIFEST = ROOT / ".codex-plugin" / "plugin.json"
MARKETPLACE_MANIFEST = ROOT / ".agents" / "plugins" / "marketplace.json"
EXPECTED_SKILLS = ("dispatch", "preview", "status", "steer", "takeover", "doctor")


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose subagents-dispatch installation and runtime evidence."
    )
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")),
        help="Codex home directory (default: $CODEX_HOME or ~/.codex).",
    )
    parser.add_argument("--check", action="store_true", help="Exit non-zero when a diagnostic is unhealthy.")
    parser.add_argument("--legacy", action="store_true", help="Show legacy migration diagnostics only.")
    parser.add_argument(
        "--temp-root",
        type=Path,
        default=Path(tempfile.gettempdir()),
        help="OS temporary root containing thread-scoped dispatch state.",
    )
    parser.add_argument(
        "--thread-id",
        help="Thread identity for state diagnostics (default: CODEX_THREAD_ID).",
    )
    parser.add_argument(
        "--runtime-evidence",
        type=Path,
        help="Explicit JSON evidence input for scripts/runtime-evidence.py; never collected automatically.",
    )
    parser.add_argument(
        "--live-route",
        action="store_true",
        help="Enable explicit route-evidence diagnostics; this never spawns or contacts a Host.",
    )
    parser.add_argument(
        "--host-evidence",
        type=Path,
        help="Explicit JSON Host capability evidence captured outside Doctor.",
    )
    parser.add_argument(
        "--repair",
        action="store_true",
        help="Explicitly run the bundled installer repair/install operation.",
    )
    parser.add_argument(
        "--migrate-legacy",
        action="store_true",
        help="Explicitly run the bundled legacy migration operation.",
    )
    parser.add_argument(
        "--cleanup-stale",
        action="store_true",
        help="Explicitly remove only stale terminal state; unresolved active state is retained.",
    )
    parser.add_argument("--json", action="store_true", help="Print the deterministic report as JSON.")
    return parser.parse_args()


def _layer(name: str, status: str, summary: str, **details: Any) -> dict[str, Any]:
    return {"name": name, "status": status, "summary": summary, "details": details}


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, str(exc)
    if not isinstance(payload, dict):
        return None, "JSON value must be an object"
    return payload, None


def diagnose_plugin() -> dict[str, Any]:
    payload, error = _read_json(PLUGIN_MANIFEST)
    if error:
        return _layer("Plugin", "FAIL", f"cannot read plugin manifest: {error}")
    assert payload is not None
    mismatches: list[str] = []
    if payload.get("name") != "subagents-dispatch":
        mismatches.append("name")
    version = payload.get("version")
    if not isinstance(version, str) or not version.strip():
        mismatches.append("version")
    if payload.get("skills") != "./skills/":
        mismatches.append("skills path")
    if mismatches:
        return _layer("Plugin", "FAIL", "manifest does not match the packaged identity", mismatches=mismatches)
    marketplace, marketplace_error = _read_json(MARKETPLACE_MANIFEST)
    if marketplace_error:
        return _layer("Plugin", "FAIL", f"cannot read marketplace manifest: {marketplace_error}")
    assert marketplace is not None
    plugins = marketplace.get("plugins")
    source = plugins[0].get("source") if isinstance(plugins, list) and plugins and isinstance(plugins[0], dict) else None
    if not isinstance(source, dict) or source.get("ref") != f"v{version}":
        return _layer(
            "Plugin",
            "FAIL",
            "marketplace source is not pinned to the packaged release",
            expected_ref=f"v{version}",
        )
    return _layer("Plugin", "OK", "manifest and packaged identity match", version=version)


def diagnose_skills() -> dict[str, Any]:
    missing: list[str] = []
    invalid: list[str] = []
    for skill_id in EXPECTED_SKILLS:
        skill_root = ROOT / "skills" / skill_id
        skill_file = skill_root / "SKILL.md"
        metadata = skill_root / "agents" / "openai.yaml"
        if not skill_file.is_file() or not metadata.is_file():
            missing.append(skill_id)
            continue
        try:
            text = skill_file.read_text(encoding="utf-8")
            ui = metadata.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            invalid.append(skill_id)
            continue
        if f"name: {skill_id}\n" not in text or "allow_implicit_invocation: false" not in ui:
            invalid.append(skill_id)
    if missing or invalid:
        return _layer(
            "Skills",
            "FAIL",
            "explicit Skill adapters are incomplete",
            missing=missing,
            invalid=invalid,
        )
    return _layer("Skills", "OK", "six explicit Skill adapters are present", count=len(EXPECTED_SKILLS))


def check_current_installation(codex_home: Path) -> tuple[bool, list[str]]:
    """Use install-agents.py --check as the canonical managed-profile verifier."""
    installer_path = Path(__file__).parent / "install-agents.py"
    if not installer_path.is_file():
        return False, ["Installer not found"]
    try:
        result = subprocess.run(
            [sys.executable, str(installer_path), "--codex-home", str(codex_home), "--check"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return False, ["Installer --check timed out"]
    except OSError as exc:
        return False, [f"Installer --check error: {exc}"]
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
        return False, [f"Installer --check failed: {detail}"]
    return True, []


def diagnose_profiles(codex_home: Path) -> dict[str, Any]:
    healthy, issues = check_current_installation(codex_home)
    legacy = detect_legacy_state(codex_home)
    legacy_status = format_migration_state(legacy)
    legacy_requires_review = legacy.legacy_only or legacy.mixed or legacy.ownership_unknown
    if healthy:
        return _layer(
            "Managed Agent profiles",
            "WARN" if legacy_requires_review else "OK",
            "installer --check passed; legacy state requires explicit review"
            if legacy_requires_review
            else "installer --check passed",
            verifier="install-agents.py --check",
            legacy_status=legacy_status,
        )
    detail = " ".join(issues)
    status = "WARN" if "Not installed" in detail or "missing" in detail.lower() else "FAIL"
    return _layer(
        "Managed Agent profiles",
        status,
        "installer --check did not report an exact managed set",
        issues=issues,
        verifier="install-agents.py --check",
        legacy_status=legacy_status,
    )


def _latest_units(payload: dict[str, Any]) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for record in payload.get("units", []):
        unit_id = record.get("unit_id")
        if isinstance(unit_id, str) and (
            unit_id not in latest or record.get("attempt", 0) > latest[unit_id].get("attempt", 0)
        ):
            latest[unit_id] = record
    return list(latest.values())


def _state_entries(temp_root: Path) -> tuple[Path | None, list[Path], str | None]:
    candidate = temp_root.expanduser()
    if not candidate.is_absolute():
        return None, [], "temporary root must be absolute"
    if candidate.is_symlink():
        return None, [], "temporary root is a symlink"
    try:
        root_base = candidate.resolve()
    except (OSError, RuntimeError) as exc:
        return None, [], f"temporary root unavailable: {exc}"
    system_temp = Path(tempfile.gettempdir()).resolve()
    if root_base != system_temp and system_temp not in root_base.parents:
        return None, [], "temporary root must remain inside the OS temporary directory"
    root = root_base / STATE_DIRECTORY
    if root.is_symlink():
        return root, [], "dispatch state root is a symlink"
    if not root.exists():
        return root, [], None
    if not root.is_dir():
        return root, [], "dispatch state root is not a directory"
    return root, sorted(root.iterdir(), key=lambda item: item.name), None


def _unexpected_repository_state() -> list[str]:
    ignored = {".git", ".venv", ".pytest_cache", ".ruff_cache", "__pycache__"}
    unexpected: list[str] = []
    for path in ROOT.rglob("active.json"):
        relative = path.relative_to(ROOT)
        if any(part in ignored for part in relative.parts):
            continue
        if STATE_DIRECTORY in relative.parts[:-1]:
            unexpected.append(relative.as_posix())
    return sorted(unexpected)


def diagnose_dispatch_state(temp_root: Path, thread_id: str | None) -> dict[str, Any]:
    root, entries, root_error = _state_entries(temp_root)
    if root_error:
        return _layer("Dispatch state", "FAIL", root_error, mutated=False)
    if root is None:
        return _layer("Dispatch state", "FAIL", "dispatch state root cannot be resolved", mutated=False)
    identity: str | None = None
    thread_issue: str | None = None
    if thread_id is None or not thread_id.strip():
        thread_issue = "CODEX_THREAD_ID is unavailable; all existing state was scanned read-only"
    else:
        try:
            identity = resolve_thread_id(thread_id)
        except StateIdentityError as exc:
            thread_issue = f"invalid CODEX_THREAD_ID: {exc}; all existing state was scanned read-only"

    corrupt: list[str] = []
    unsafe: list[str] = []
    stale: list[str] = []
    active_writers: list[str] = []
    ambiguous_writers: list[str] = []
    active_units: list[str] = []
    lock_issues: list[str] = []
    readable = 0
    for entry in entries:
        if entry.is_symlink() or not entry.is_dir():
            unsafe.append(entry.name)
            continue
        try:
            entry_id = resolve_thread_id(entry.name)
        except StateIdentityError:
            unsafe.append(entry.name)
            continue
        try:
            payload = load_state(entry_id, temp_root=temp_root)
        except (StateCorruptError, StatePathError, StateIdentityError):
            corrupt.append(entry_id)
            continue
        if payload is None:
            continue
        readable += 1
        lock_path = entry / LOCK_FILE
        if lock_path.is_symlink() or (lock_path.exists() and not lock_path.is_file()):
            lock_issues.append(entry_id)
        elif not lock_path.exists():
            lock_issues.append(entry_id)
        try:
            if is_stale(payload):
                stale.append(entry_id)
        except (TypeError, ValueError, KeyError):
            corrupt.append(entry_id)
            continue
        latest = _latest_units(payload)
        active_units.extend(
            f"{entry_id}:{record.get('unit_id', '?')}"
            for record in latest
            if record.get("control_state") in ACTIVE_STATES
        )
        writers = [
            record
            for record in latest
            if record.get("writer") is True and record.get("control_state") in ACTIVE_STATES
        ]
        if writers:
            active_writers.extend(f"{entry_id}:{record.get('unit_id', '?')}" for record in writers)
            if len(writers) > 1:
                ambiguous_writers.append(entry_id)

    details = {
        "current_thread": identity,
        "current_state": "unknown"
        if identity is None
        else ("present" if any(entry.name == identity for entry in entries) else "absent"),
        "active_orchestration": bool(active_units),
        "active_units": sorted(set(active_units)),
        "stale_count": len(set(stale)),
        "state_lock_health": "issue" if lock_issues else ("ok" if entries else "not_present"),
        "lock_issues": sorted(set(lock_issues)),
        "schema_health": "issue" if corrupt else "ok",
        "unexpected_repository_state": _unexpected_repository_state(),
        "mutated": False,
    }
    if corrupt or unsafe or details["unexpected_repository_state"]:
        return _layer(
            "Dispatch state",
            "FAIL",
            "corrupt or unsafe state is preserved for explicit review",
            corrupt=sorted(set(corrupt)),
            unsafe=sorted(set(unsafe)),
            **details,
        )
    if stale or active_writers or ambiguous_writers or lock_issues:
        return _layer(
            "Dispatch state",
            "WARN",
            "stale or unresolved writer state is retained; no automatic deletion occurred",
            stale=sorted(set(stale)),
            active_writers=sorted(set(active_writers)),
            ambiguous_writers=sorted(set(ambiguous_writers)),
            stale_after_days=int(DEFAULT_STALE_AFTER.total_seconds() // 86400),
            **details,
        )
    if thread_issue is not None:
        return _layer("Dispatch state", "UNKNOWN", thread_issue, capsules_read=readable, **details)
    return _layer(
        "Dispatch state",
        "OK",
        "thread-scoped state is absent or valid",
        capsules_read=readable,
        **details,
    )


def diagnose_host(host_evidence: Path | None) -> dict[str, Any]:
    evidence_path = host_evidence
    if evidence_path is None:
        raw = os.environ.get("SUBAGENTS_DISPATCH_HOST_EVIDENCE")
        evidence_path = Path(raw) if raw else None
    if evidence_path is None:
        return _layer(
            "Codex Host",
            "UNKNOWN",
            "Host capability evidence is unavailable; supported limitation",
            observed=False,
        )
    payload, error = _read_json(evidence_path)
    if error:
        return _layer("Codex Host", "FAIL", f"invalid explicit Host evidence: {error}", observed=False)
    assert payload is not None
    capabilities = payload.get("capabilities")
    if capabilities is None:
        return _layer(
            "Codex Host",
            "UNKNOWN",
            "explicit Host evidence does not expose capabilities; supported limitation",
            observed=False,
        )
    if not isinstance(capabilities, list) or not all(isinstance(item, str) and item.strip() for item in capabilities):
        return _layer("Codex Host", "FAIL", "explicit Host evidence requires a capabilities list", observed=False)
    if not capabilities:
        return _layer(
            "Codex Host",
            "UNKNOWN",
            "Host reported no supported capabilities; supported limitation",
            capabilities=[],
            observed=True,
        )
    return _layer(
        "Codex Host",
        "OK",
        "explicit Host capability evidence was supplied",
        capabilities=sorted(set(capabilities)),
        observed=True,
    )


def _runtime_status(result: dict[str, Any]) -> tuple[str, str]:
    status = result.get("status")
    violations = result.get("violations")
    if status in {"conflict", "mismatch"} or (isinstance(violations, list) and violations):
        return "FAIL", "runtime route evidence conflicts with the requested or accepted route"
    route = result.get("route_evidence", {})
    source = route.get("source") if isinstance(route, dict) else None
    if status in {"observed", "matched"} and source in {"native", "both"}:
        return "OK", "observed runtime route evidence is consistent"
    if status in {"observed", "matched", "partial", "not_exposed", "not_observed"}:
        return "UNKNOWN", "configured/requested values are not observed runtime proof; observed runtime route was not reported"
    return "UNKNOWN", "observed runtime route was not reported"


def diagnose_runtime(evidence_path: Path | None, live_route: bool) -> dict[str, Any]:
    if evidence_path is None:
        return _layer(
            "Runtime route evidence",
            "UNKNOWN",
            "not run; pass --runtime-evidence with explicit evidence (or --live-route to record the limitation)",
            observed=False,
        )
    verifier = Path(__file__).parent / "runtime-evidence.py"
    try:
        result = subprocess.run(
            [sys.executable, str(verifier), "--input", str(evidence_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _layer("Runtime route evidence", "FAIL", f"runtime-evidence normalizer failed: {exc}")
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
        return _layer("Runtime route evidence", "FAIL", f"runtime-evidence normalizer failed: {detail}")
    payload, error = _read_json_from_text(result.stdout)
    if error:
        return _layer("Runtime route evidence", "FAIL", f"runtime-evidence output is invalid: {error}")
    assert payload is not None
    status, summary = _runtime_status(payload)
    return _layer(
        "Runtime route evidence",
        status,
        summary,
        explicit=True,
        live_route=live_route,
        normalizer="runtime-evidence.py",
        evidence_grade=payload.get("evidence_grade"),
        route_status=payload.get("route_evidence", {}).get("status") if isinstance(payload.get("route_evidence"), dict) else None,
    )


def _read_json_from_text(raw: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, str(exc)
    if not isinstance(payload, dict):
        return None, "JSON value must be an object"
    return payload, None


def run_explicit_actions(args: argparse.Namespace, codex_home: Path) -> list[str]:
    actions: list[str] = []
    if args.repair or args.migrate_legacy:
        installer = Path(__file__).parent / "install-agents.py"
        command = [sys.executable, str(installer), "--codex-home", str(codex_home)]
        if args.migrate_legacy:
            command.append("--migrate-legacy")
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            fail(result.stderr.strip() or result.stdout.strip() or "explicit installer operation failed")
        actions.append("installer migration" if args.migrate_legacy else "installer repair")
    if args.cleanup_stale:
        try:
            report = cleanup_stale_states(
                temp_root=args.temp_root,
                active_thread_id=args.thread_id or os.environ.get("CODEX_THREAD_ID"),
            )
        except (StateIdentityError, StatePathError) as exc:
            fail(f"explicit stale cleanup failed safely: {exc}")
        actions.append(
            "stale cleanup removed "
            + str(len(report["removed"]))
            + " terminal capsule(s); retained active/corrupt state"
        )
    return actions


def print_legacy_recommendation(state: MigrationState) -> None:
    if state.migration_complete or state.current_only:
        print("  ✓ Migration complete. No legacy cleanup is needed.")
    elif state.preserved_legacy:
        print("  ⚠ Current profiles are installed and user-owned legacy state was preserved. Do not repeat automatic migration; review the preserved files explicitly.")
    elif state.ownership_unknown:
        print("  ⚠ Legacy ownership metadata is missing, invalid, or unsafe. Automatic migration is blocked until the legacy state is resolved explicitly.")
    elif state.legacy_only:
        print("  → Run the installer with --migrate-legacy to migrate the owned legacy state.")
    elif state.mixed:
        print("  → Run the installer with --migrate-legacy to clean up proven-owned legacy state.")
    else:
        print("  → No actionable legacy installation was detected.")


def show_legacy_diagnostics(codex_home: Path) -> None:
    state = detect_legacy_state(codex_home)
    print("=== Legacy Migration Diagnostics ===")
    print(f"State: {format_migration_state(state)}")
    print()
    print("State flags:")
    print(f"  Legacy only: {state.legacy_only}")
    print(f"  Current only: {state.current_only}")
    print(f"  Mixed: {state.mixed}")
    print(f"  Legacy modified: {state.legacy_modified}")
    print(f"  Ownership unknown: {state.ownership_unknown}")
    print(f"  Preserved legacy: {state.preserved_legacy}")
    print(f"  Migration complete: {state.migration_complete}")
    print()

    agents_dir = codex_home / "agents"
    manifest_path = codex_home / LEGACY_MANIFEST_NAME
    lock_path = codex_home / LEGACY_LOCK_NAME
    manifest_status, manifest = legacy_manifest_status(manifest_path)
    print("Legacy files:")
    if manifest_path.exists() or manifest_path.is_symlink():
        print(f"  Manifest: {manifest_path} ({manifest_status})")
        if manifest:
            print(f"    Schema version: {manifest.schema_version}")
            print(f"    Managed by: {manifest.managed_by}")
            print(f"    Owned profiles: {', '.join(manifest.profile_hashes.keys())}")
    else:
        print("  Manifest: not found")
    print(f"  Lock: {lock_path}" if lock_path.exists() else "  Lock: not found")
    if agents_dir.is_dir() and not agents_dir.is_symlink():
        profiles = [name for name in LEGACY_PROFILE_FILES if (agents_dir / name).is_file() and not (agents_dir / name).is_symlink()]
        print(f"  Active legacy profiles: {', '.join(profiles) if profiles else 'none'}")
    else:
        print("  Active legacy profiles: agents directory not available")
    print()
    print("Recommendations:")
    print_legacy_recommendation(state)


def diagnose(args: argparse.Namespace, codex_home: Path) -> dict[str, Any]:
    thread_id = args.thread_id if args.thread_id is not None else os.environ.get("CODEX_THREAD_ID")
    return {
        "layers": [
            diagnose_plugin(),
            diagnose_skills(),
            diagnose_profiles(codex_home),
            diagnose_dispatch_state(args.temp_root, thread_id),
            diagnose_host(args.host_evidence),
            diagnose_runtime(args.runtime_evidence if args.live_route or args.runtime_evidence else None, args.live_route),
        ]
    }


def main() -> None:
    args = parse_args()
    codex_home = args.codex_home.expanduser()
    if codex_home.is_symlink():
        fail(f"Refusing symlinked Codex home: {codex_home}")
    codex_home = codex_home.resolve()

    if args.legacy:
        show_legacy_diagnostics(codex_home)
        return

    actions = run_explicit_actions(args, codex_home)
    report = diagnose(args, codex_home)
    statuses = [layer["status"] for layer in report["layers"]]
    healthy = not any(status in {"WARN", "FAIL"} for status in statuses)
    report["healthy"] = healthy
    report["actions"] = actions

    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    else:
        print("=== subagents-dispatch Doctor ===")
        print("Mode: deterministic read-only diagnostics; no child spawn or Host control")
        for layer in report["layers"]:
            print(f"Layer: {layer['name']}: {layer['status']} — {layer['summary']}")
        for action in actions:
            print(f"Action: {action}")
        print(f"Overall: {'OK' if healthy else 'UNHEALTHY'}")

    if args.check and not healthy:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
