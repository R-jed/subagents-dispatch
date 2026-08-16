#!/usr/bin/env python3
"""CLI runtime for deterministic subagents-dispatch diagnostics."""

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
    StateIdentityError,
    StatePathError,
    cleanup_stale_states,
    resolve_thread_id,
)
from doctor_core import calculate_health, diagnose, layer, render_text
from legacy_migration import (
    LEGACY_LOCK_NAME,
    LEGACY_MANIFEST_NAME,
    LEGACY_PROFILE_FILES,
    MigrationState,
    detect_legacy_state,
    format_migration_state,
    legacy_manifest_status,
)
from plugin_update import diagnose_installation, package_version as plugin_package_version


ROOT = Path(__file__).resolve().parents[1]


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
    parser.add_argument("--thread-id", help="Thread identity for state diagnostics (default: CODEX_THREAD_ID).")
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
        help="Explicit normalized Host capability/Plugin-Hook evidence captured outside Doctor.",
    )
    parser.add_argument("--calibration-evidence-root", type=Path)
    parser.add_argument("--calibration-campaign", type=Path)
    parser.add_argument("--calibration-host-home-evidence", type=Path)
    parser.add_argument("--calibration-provisioning-task-id")
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
    parser.add_argument(
        "--update",
        action="store_true",
        help="Explicitly refresh the configured Marketplace and update the installed Plugin with post-write verification.",
    )
    parser.add_argument("--json", action="store_true", help="Print the deterministic report as JSON.")
    return parser.parse_args()


def _update_is_exclusive(args: argparse.Namespace) -> bool:
    incompatible = (
        args.check,
        args.legacy,
        args.repair,
        args.migrate_legacy,
        args.cleanup_stale,
        args.live_route,
        args.runtime_evidence is not None,
        args.host_evidence is not None,
        args.calibration_evidence_root is not None,
        args.calibration_campaign is not None,
        args.calibration_host_home_evidence is not None,
        args.calibration_provisioning_task_id is not None,
    )
    return not any(incompatible)


def run_update(args: argparse.Namespace, codex_home: Path) -> None:
    if not _update_is_exclusive(args):
        fail("--update is an explicit lifecycle operation and cannot be combined with other Doctor checks or mutations")
    updater = ROOT / "scripts" / "plugin_update.py"
    command = [sys.executable, str(updater), "--codex-home", str(codex_home)]
    if args.json:
        command.append("--json")
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def run_explicit_actions(args: argparse.Namespace, codex_home: Path) -> list[str]:
    actions: list[str] = []
    if args.repair or args.migrate_legacy:
        installer = ROOT / "scripts" / "install-agents.py"
        command = [sys.executable, str(installer), "--codex-home", str(codex_home)]
        if args.migrate_legacy:
            command.append("--migrate-legacy")
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            fail("explicit managed-profile lifecycle operation failed")
        actions.append("installer migration" if args.migrate_legacy else "installer repair")
    if args.cleanup_stale:
        try:
            active_thread_id = args.thread_id if args.thread_id is not None else os.environ.get("CODEX_THREAD_ID")
            if active_thread_id is not None:
                resolve_thread_id(active_thread_id)
            report = cleanup_stale_states(
                temp_root=args.temp_root,
                active_thread_id=active_thread_id,
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
        print("  Migration complete. No legacy cleanup is needed.")
    elif state.preserved_legacy:
        print(
            "  Current profiles are installed and user-owned legacy state was preserved. "
            "Do not repeat automatic migration. Review it explicitly."
        )
    elif state.ownership_unknown:
        print("  Legacy ownership metadata is missing, invalid, or unsafe. Automatic migration is blocked.")
    elif state.legacy_only or state.mixed:
        print("  Run the installer with --migrate-legacy to reconcile proven-owned legacy state.")
    else:
        print("  No actionable legacy installation was detected.")


def show_legacy_diagnostics(codex_home: Path) -> None:
    state = detect_legacy_state(codex_home)
    print("Legacy Migration Diagnostics")
    print(f"State: {format_migration_state(state)}")
    print(f"Legacy only: {state.legacy_only}")
    print(f"Current only: {state.current_only}")
    print(f"Mixed: {state.mixed}")
    print(f"Ownership unknown: {state.ownership_unknown}")
    print(f"Preserved legacy: {state.preserved_legacy}")
    print(f"Migration complete: {state.migration_complete}")
    agents_dir = codex_home / "agents"
    manifest_path = codex_home / LEGACY_MANIFEST_NAME
    lock_path = codex_home / LEGACY_LOCK_NAME
    manifest_status, manifest = legacy_manifest_status(manifest_path)
    print(f"Manifest: {manifest_status if manifest_path.exists() else 'not found'}")
    if manifest:
        print(f"Managed by: {manifest.managed_by}")
        print(f"Owned profiles: {', '.join(manifest.profile_hashes.keys())}")
    print(f"Lock: {'present' if lock_path.exists() else 'not found'}")
    if agents_dir.is_dir() and not agents_dir.is_symlink():
        profiles = [
            name
            for name in LEGACY_PROFILE_FILES
            if (agents_dir / name).is_file() and not (agents_dir / name).is_symlink()
        ]
        print(f"Active legacy profiles: {', '.join(profiles) if profiles else 'none'}")
    print_legacy_recommendation(state)


def development_calibration_layer(args: argparse.Namespace, codex_home: Path) -> dict[str, Any] | None:
    values = (
        args.calibration_evidence_root,
        args.calibration_campaign,
        args.calibration_host_home_evidence,
        args.calibration_provisioning_task_id,
    )
    if not any(item is not None for item in values):
        return None
    if not all(item is not None for item in values):
        return layer(
            "Calibration readiness",
            "FAIL",
            "calibration evidence root, campaign, Host-home evidence, and provisioning task id are all required",
        )
    repository_status = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--porcelain"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    repository_dirty = repository_status.returncode != 0 or bool(repository_status.stdout.strip())
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "calibration_profiles.py"),
            "check",
            "--evaluator-root",
            str(args.calibration_evidence_root),
            "--codex-home",
            str(codex_home),
            "--campaign",
            str(args.calibration_campaign),
            "--host-home-evidence",
            str(args.calibration_host_home_evidence),
            "--provisioning-task-id",
            str(args.calibration_provisioning_task_id),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    ready = result.returncode == 0 and not repository_dirty
    return layer(
        "Calibration readiness",
        "OK" if ready else "FAIL",
        "Experiment Plane profile-only calibration state is exact"
        if ready
        else "Experiment Plane profile-only calibration state is not ready",
        materialization_mode="profile_only",
        repository_clean=not repository_dirty,
        verifier_returncode=result.returncode,
    )


def main() -> None:
    args = parse_args()
    codex_home = args.codex_home.expanduser()
    if codex_home.is_symlink():
        fail(f"Refusing symlinked Codex home: {codex_home}")
    codex_home = codex_home.resolve()

    if args.update:
        run_update(args, codex_home)
        return

    if args.legacy:
        show_legacy_diagnostics(codex_home)
        return

    actions = run_explicit_actions(args, codex_home)
    thread_id = args.thread_id if args.thread_id is not None else os.environ.get("CODEX_THREAD_ID")
    report = diagnose(
        codex_home=codex_home,
        temp_root=args.temp_root,
        thread_id=thread_id,
        runtime_evidence=args.runtime_evidence,
        live_route=args.live_route,
        host_evidence=args.host_evidence,
    )
    installation = diagnose_installation(
        codex_home=codex_home,
        package_version_value=plugin_package_version(),
    )
    report["layers"].insert(1, installation)
    report["schema_version"] = 3
    development = development_calibration_layer(args, codex_home)
    development_layers = [development] if development is not None else []
    healthy = calculate_health(report["layers"], live_route=args.live_route)
    if development_layers:
        healthy = healthy and not any(item["status"] in {"WARN", "FAIL"} for item in development_layers)
    report["development_layers"] = development_layers
    report["actions"] = actions
    report["healthy"] = healthy

    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    else:
        print(render_text(report))

    if args.check and not healthy:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
