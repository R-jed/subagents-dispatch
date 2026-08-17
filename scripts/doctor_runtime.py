#!/usr/bin/env python3
"""Deterministic V4 Doctor runtime.

Diagnostics are read-only by default. Explicit repair, migration, stale cleanup,
and update actions remain opt-in. Real Host smoke is reported separately from
offline package health and can never be inferred from CI or packaged Hooks.
"""

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

import dispatch_state as state
import dispatch_state_v3_legacy as legacy_state
from host_capabilities import HostCapabilityError, normalize_host_capabilities
from legacy_migration import detect_legacy_state, format_migration_state
from plugin_update import diagnose_installation, package_version as plugin_package_version
import release_gate_v4


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SKILLS = ("doctor", "orchestrate")
LIFECYCLE_MATCHER = "spawn_agent|followup_task|interrupt_agent"
PROFILE_EXPECTATIONS = {
    "subagents-dispatch-reader.toml": ("gpt-5.6-luna", "max"),
    "subagents-dispatch-worker.toml": ("gpt-5.6-luna", "max"),
    "subagents-dispatch-investigator.toml": ("gpt-5.6-terra", "high"),
    "subagents-dispatch-solver.toml": ("gpt-5.6-sol", "high"),
    "subagents-dispatch-advisor.toml": ("gpt-5.6-sol", "high"),
}


def layer(name: str, status: str, summary: str, *, action: str | None = None, **details: Any) -> dict[str, Any]:
    result: dict[str, Any] = {"name": name, "status": status, "summary": summary, "details": details}
    if action is not None:
        result["action"] = action
    return result


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose subagents-dispatch V4 installation and runtime readiness.")
    parser.add_argument("--codex-home", type=Path, default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--legacy", action="store_true")
    parser.add_argument("--temp-root", type=Path, default=Path(tempfile.gettempdir()))
    parser.add_argument("--thread-id")
    parser.add_argument("--runtime-evidence", type=Path)
    parser.add_argument("--live-route", action="store_true")
    parser.add_argument("--host-evidence", type=Path)
    parser.add_argument("--repair", action="store_true")
    parser.add_argument("--migrate-legacy", action="store_true")
    parser.add_argument("--cleanup-stale", action="store_true")
    parser.add_argument("--update", action="store_true")
    parser.add_argument("--calibration-evidence-root", type=Path)
    parser.add_argument("--calibration-campaign", type=Path)
    parser.add_argument("--calibration-host-home-evidence", type=Path)
    parser.add_argument("--calibration-provisioning-task-id")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, str(exc)
    if not isinstance(value, dict):
        return None, "JSON value must be an object"
    return value, None


def diagnose_plugin() -> dict[str, Any]:
    manifest, error = _read_json(ROOT / ".codex-plugin" / "plugin.json")
    if error or manifest is None:
        return layer("Plugin", "FAIL", f"plugin manifest is unreadable: {error}")
    version = manifest.get("version")
    if manifest.get("name") != "subagents-dispatch" or version != "4.0.0" or manifest.get("skills") != "./skills/":
        return layer("Plugin", "FAIL", "packaged V4 identity is inconsistent")
    marketplace, marketplace_error = _read_json(ROOT / ".agents" / "plugins" / "marketplace.json")
    if marketplace_error or marketplace is None:
        return layer("Plugin", "FAIL", f"marketplace manifest is unreadable: {marketplace_error}")
    plugins = marketplace.get("plugins")
    source = plugins[0].get("source") if isinstance(plugins, list) and plugins and isinstance(plugins[0], dict) else None
    if not isinstance(source, dict) or source.get("ref") != "v4.0.0":
        return layer("Plugin", "FAIL", "marketplace source is not pinned to v4.0.0")
    return layer("Plugin", "OK", "V4 packaged identity is exact", version=version)


def diagnose_skills() -> dict[str, Any]:
    skills_root = ROOT / "skills"
    present = sorted(path.name for path in skills_root.iterdir() if path.is_dir()) if skills_root.is_dir() else []
    if present != list(EXPECTED_SKILLS):
        return layer("Skills", "FAIL", "public Skill surface must contain exactly Doctor and Orchestrate", present=present)
    invalid: list[str] = []
    for skill_id in EXPECTED_SKILLS:
        skill = skills_root / skill_id / "SKILL.md"
        metadata = skills_root / skill_id / "agents" / "openai.yaml"
        try:
            skill_text = skill.read_text(encoding="utf-8")
            metadata_text = metadata.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            invalid.append(skill_id)
            continue
        if f"name: {skill_id}\n" not in skill_text or "allow_implicit_invocation: false" not in metadata_text:
            invalid.append(skill_id)
    if invalid:
        return layer("Skills", "FAIL", "V4 Skill adapters are incomplete", invalid=invalid)
    return layer("Skills", "OK", "two explicit V4 Skill adapters are present", count=2)


def _handler_exact(handler: Any) -> bool:
    if not isinstance(handler, dict):
        return False
    command = handler.get("command")
    command_windows = handler.get("commandWindows")
    return (
        handler.get("type") == "command"
        and isinstance(command, str)
        and command.endswith('/scripts/orchestration_guard.py\"')
        and isinstance(command_windows, str)
        and command_windows.endswith('\\scripts\\orchestration_guard.py\"')
        and handler.get("timeout") == 5
        and handler.get("async", False) is False
    )


def diagnose_guard_package() -> dict[str, Any]:
    hooks, error = _read_json(ROOT / "hooks" / "hooks.json")
    if error or hooks is None:
        return layer("Managed lifecycle guard package", "FAIL", f"hooks config is unreadable: {error}")
    events = hooks.get("hooks")
    if not isinstance(events, dict) or set(events) != {"PreToolUse", "PostToolUse", "SubagentStop"}:
        return layer("Managed lifecycle guard package", "FAIL", "V4 Hook events are incomplete")
    for event in ("PreToolUse", "PostToolUse"):
        groups = events.get(event)
        if not isinstance(groups, list) or len(groups) != 1 or groups[0].get("matcher") != LIFECYCLE_MATCHER:
            return layer("Managed lifecycle guard package", "FAIL", f"{event} lifecycle matcher is invalid")
        handlers = groups[0].get("hooks")
        if not isinstance(handlers, list) or len(handlers) != 1 or not _handler_exact(handlers[0]):
            return layer("Managed lifecycle guard package", "FAIL", f"{event} handler is invalid")
    stop_groups = events.get("SubagentStop")
    if not isinstance(stop_groups, list) or len(stop_groups) != 1:
        return layer("Managed lifecycle guard package", "FAIL", "SubagentStop guard is invalid")
    stop_handlers = stop_groups[0].get("hooks") if isinstance(stop_groups[0], dict) else None
    if not isinstance(stop_handlers, list) or len(stop_handlers) != 1 or not _handler_exact(stop_handlers[0]):
        return layer("Managed lifecycle guard package", "FAIL", "SubagentStop handler is invalid")
    if not (ROOT / "scripts" / "orchestration_guard.py").is_file():
        return layer("Managed lifecycle guard package", "FAIL", "orchestration_guard.py is missing")
    return layer(
        "Managed lifecycle guard package",
        "OK",
        "V4 PreToolUse, PostToolUse, and SubagentStop guards are packaged exactly",
        runtime_proven=False,
    )


def diagnose_profiles(codex_home: Path) -> dict[str, Any]:
    verifier = ROOT / "scripts" / "install-agents.py"
    result = subprocess.run(
        [sys.executable, str(verifier), "--codex-home", str(codex_home), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return layer(
            "Managed Agent profiles",
            "WARN",
            "managed profile set is not installed exactly",
            action="Run Doctor --repair, then start a fresh Codex task/session before managed execution.",
        )
    return layer("Managed Agent profiles", "OK", "five fixed managed profiles pass installer verification")


def _latest_legacy_units(payload: dict[str, Any]) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for record in payload.get("units", []):
        if not isinstance(record, dict):
            continue
        unit_id = record.get("unit_id")
        attempt = record.get("attempt", 0)
        if isinstance(unit_id, str) and (unit_id not in latest or attempt > latest[unit_id].get("attempt", 0)):
            latest[unit_id] = record
    return list(latest.values())


def _legacy_unresolved(payload: dict[str, Any]) -> bool:
    if payload.get("pending_takeover") is not None:
        return True
    return any(
        record.get("control_state") in legacy_state.ACTIVE_STATES
        for record in _latest_legacy_units(payload)
    )


def diagnose_state(temp_root: Path, thread_id: str | None) -> dict[str, Any]:
    if thread_id is None or not thread_id.strip():
        return layer("V4 state", "UNKNOWN", "thread identity is unavailable; no state was mutated")
    try:
        identity = state.resolve_thread_id(thread_id)
    except state.StateIdentityError as exc:
        return layer("V4 state", "FAIL", f"invalid thread identity: {exc}")
    try:
        payload = state.load_state(identity, temp_root=temp_root)
    except (state.StatePayloadError, state.StateCorruptError, state.StatePathError):
        try:
            legacy = legacy_state.load_state(identity, temp_root=temp_root)
        except Exception as exc:
            return layer("V4 state", "FAIL", f"state is corrupt or unsupported: {exc}")
        if legacy is None:
            return layer("V4 state", "FAIL", "state exists but cannot be parsed as V4 or V3.x")
        if _legacy_unresolved(legacy):
            return layer(
                "V4 state",
                "FAIL",
                "unresolved V3.x state blocks V4 execution and cannot be silently migrated",
                action="Finish, take over, or explicitly settle the V3.x orchestration before V4 execution.",
                legacy_schema=legacy.get("schema_version"),
            )
        return layer(
            "V4 state",
            "WARN",
            "terminal V3.x state is present and remains separate from V4",
            action="Use explicit stale cleanup after confirming the legacy orchestration is terminal.",
        )
    if payload is None:
        return layer("V4 state", "OK", "thread-scoped V4 state is absent")
    lease = payload.get("writer_lease")
    unresolved_controls = [
        control.get("control_id")
        for control in payload.get("pending_controls", [])
        if control.get("state") in state.UNRESOLVED_CONTROL_STATES
    ]
    return layer(
        "V4 state",
        "OK",
        "thread-scoped V4 state validates",
        state_revision=payload.get("state_revision"),
        team_plan_revision=payload.get("team_plan_revision"),
        work_units=len(payload.get("work_units", [])),
        executions=len(payload.get("executions", [])),
        writer_lease=lease,
        unresolved_controls=unresolved_controls,
    )


def diagnose_host_evidence(path: Path | None) -> dict[str, Any]:
    if path is None:
        return layer("Codex Host capabilities", "UNKNOWN", "explicit Host capability evidence was not supplied")
    payload, error = _read_json(path)
    if error or payload is None:
        return layer("Codex Host capabilities", "FAIL", f"Host evidence is unreadable: {error}")
    try:
        snapshot = normalize_host_capabilities(payload)
    except HostCapabilityError as exc:
        return layer("Codex Host capabilities", "FAIL", f"Host evidence is invalid: {exc}")
    return layer(
        "Codex Host capabilities",
        "OK" if snapshot["execution_ready"] else "WARN",
        "required V4 Host capability surface is present"
        if snapshot["execution_ready"]
        else "required V4 Host capability surface is incomplete",
        snapshot=snapshot,
    )


def diagnose_release_gate() -> dict[str, Any]:
    readiness = release_gate_v4.managed_execution_readiness()
    if readiness.get("ready") is True:
        return layer("Supported execution gate", "OK", "real Host smoke H01-H07 is PASS", **readiness)
    return layer(
        "Supported execution gate",
        "UNKNOWN",
        "managed execution remains blocked pending real Host smoke H01-H07",
        action="Run the canonical Host smoke plan when Codex quota is available; do not substitute offline CI.",
        **readiness,
    )


def calibration_layer(args: argparse.Namespace, codex_home: Path) -> dict[str, Any] | None:
    values = (
        args.calibration_evidence_root,
        args.calibration_campaign,
        args.calibration_host_home_evidence,
        args.calibration_provisioning_task_id,
    )
    if not any(value is not None for value in values):
        return None
    if not all(value is not None for value in values):
        return layer("Calibration readiness", "FAIL", "all calibration evidence arguments are required together")
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
        capture_output=True,
        text=True,
        check=False,
    )
    return layer(
        "Calibration readiness",
        "OK" if result.returncode == 0 else "FAIL",
        "fixed-profile calibration evidence is valid" if result.returncode == 0 else "calibration evidence is not ready",
    )


def run_explicit_actions(args: argparse.Namespace, codex_home: Path) -> list[str]:
    actions: list[str] = []
    if args.repair or args.migrate_legacy:
        command = [sys.executable, str(ROOT / "scripts" / "install-agents.py"), "--codex-home", str(codex_home)]
        if args.migrate_legacy:
            command.append("--migrate-legacy")
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            fail("explicit managed-profile lifecycle operation failed")
        actions.append("installer migration" if args.migrate_legacy else "installer repair")
    if args.cleanup_stale:
        active_thread_id = args.thread_id if args.thread_id is not None else os.environ.get("CODEX_THREAD_ID")
        report = legacy_state.cleanup_stale_states(temp_root=args.temp_root, active_thread_id=active_thread_id)
        actions.append(f"legacy stale cleanup removed {len(report['removed'])} terminal capsule(s)")
    return actions


def show_legacy(codex_home: Path, *, as_json: bool) -> None:
    migration = detect_legacy_state(codex_home)
    payload = {
        "state": format_migration_state(migration),
        "legacy_only": migration.legacy_only,
        "current_only": migration.current_only,
        "mixed": migration.mixed,
        "ownership_unknown": migration.ownership_unknown,
        "preserved_legacy": migration.preserved_legacy,
        "migration_complete": migration.migration_complete,
    }
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    else:
        print("Legacy Migration Diagnostics")
        for key, value in payload.items():
            print(f"{key}: {value}")


def render(report: dict[str, Any]) -> str:
    lines = ["Subagents Dispatch Doctor", "Mode: deterministic V4 diagnostics", ""]
    for item in report["layers"]:
        lines.append(f"[{item['status']}] {item['name']}: {item['summary']}")
        if item.get("action"):
            lines.append(f"       Action: {item['action']}")
    lines.extend(["", f"Overall: {'HEALTHY' if report['healthy'] else 'UNHEALTHY'}"])
    counts = {status: sum(1 for item in report["layers"] if item["status"] == status) for status in ("FAIL", "WARN", "UNKNOWN")}
    lines.append(f"{counts['FAIL']} failed · {counts['WARN']} warnings · {counts['UNKNOWN']} unknown")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    codex_home = args.codex_home.expanduser()
    if codex_home.is_symlink():
        fail(f"Refusing symlinked Codex home: {codex_home}")
    codex_home = codex_home.resolve()

    if args.update:
        command = [sys.executable, str(ROOT / "scripts" / "plugin_update.py"), "--codex-home", str(codex_home)]
        if args.json:
            command.append("--json")
        raise SystemExit(subprocess.call(command))
    if args.legacy:
        show_legacy(codex_home, as_json=args.json)
        return

    actions = run_explicit_actions(args, codex_home)
    thread_id = args.thread_id if args.thread_id is not None else os.environ.get("CODEX_THREAD_ID")
    layers = [
        diagnose_plugin(),
        diagnose_installation(codex_home=codex_home, package_version_value=plugin_package_version()),
        diagnose_skills(),
        diagnose_guard_package(),
        diagnose_profiles(codex_home),
        diagnose_state(args.temp_root, thread_id),
        diagnose_host_evidence(args.host_evidence),
        diagnose_release_gate(),
    ]
    calibration = calibration_layer(args, codex_home)
    if calibration is not None:
        layers.append(calibration)
    healthy = not any(item["status"] in {"FAIL", "WARN"} for item in layers)
    report = {"schema_version": 4, "layers": layers, "actions": actions, "healthy": healthy}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    else:
        print(render(report))
    if args.check and not healthy:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
