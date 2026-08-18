#!/usr/bin/env python3
"""Deterministic product Doctor for the installed subagents-dispatch Plugin."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
from typing import Any, Mapping

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import dispatch_state as legacy_state
import dispatch_state_v4 as state_v4
import host_capabilities
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
PLUGIN = ROOT / ".codex-plugin" / "plugin.json"
POLICY = ROOT / "contracts" / "policy.json"
HOOKS = ROOT / "hooks" / "hooks.json"
PROFILE_DIR = ROOT / "agent-profiles"
SKILLS = ROOT / "skills"
EXPECTED_SKILLS = ("orchestrate", "doctor")
EXPECTED_PROFILES = {
    "reader": ("gpt-5.6-luna", "max"),
    "worker": ("gpt-5.6-luna", "max"),
    "investigator": ("gpt-5.6-terra", "high"),
    "solver": ("gpt-5.6-sol", "high"),
    "advisor": ("gpt-5.6-sol", "high"),
}
REQUIRED_HOOK_EVENTS = {"PreToolUse", "PostToolUse", "SubagentStop"}
COMPATIBILITY_HOOK_EVENTS = {"PreToolUse"}
LIFECYCLE_MATCHER = "spawn_agent|followup_task|interrupt_agent|list_agents"
COMPATIBILITY_MATCHER = "spawn_agent"
SUBAGENT_STOP_MATCHER = (
    "subagents_dispatch_reader|subagents_dispatch_worker|"
    "subagents_dispatch_investigator|subagents_dispatch_solver|"
    "subagents_dispatch_advisor"
)
GUARD_SCRIPT = "scripts/orchestration_guard.py"
COMPATIBILITY_GUARD_SCRIPT = "scripts/spawn_guard.py"
HOOK_COMMANDS = {
    "posix": '"${PLUGIN_ROOT}/hooks/run-python.sh" "${PLUGIN_ROOT}/{}"',
    "windows": '"%PLUGIN_ROOT%\\hooks\\run-python.cmd" "%PLUGIN_ROOT%\\{}"',
}
LAYER_ORDER = (
    "Plugin package",
    "Managed Agents",
    "Host integration",
    "Orchestration state",
    "Legacy compatibility",
)
RECOVERABLE_PROFILE_CHECK_PREFIXES = (
    "Not installed:",
    "Required Codex home is missing:",
    "Current managed-profile manifest is missing or stale:",
)


class DoctorError(RuntimeError):
    """Deterministic diagnostic input is unsafe or malformed."""


def layer(
    name: str,
    status: str,
    summary: str,
    *,
    action: str | None = None,
    **details: Any,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": name,
        "status": status,
        "summary": summary,
        "details": details,
    }
    if action is not None:
        result["action"] = action
    return result


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        label = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        raise DoctorError(f"cannot read {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise DoctorError(f"{path} must contain a JSON object")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose and explicitly maintain the installed subagents-dispatch Plugin."
    )
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")),
    )
    parser.add_argument("--temp-root", type=Path, default=Path(tempfile.gettempdir()))
    parser.add_argument("--thread-id")
    parser.add_argument("--host-evidence", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--legacy", action="store_true")
    parser.add_argument("--repair", action="store_true")
    parser.add_argument("--migrate-legacy", action="store_true")
    parser.add_argument("--cleanup-stale", action="store_true")
    parser.add_argument("--uninstall-managed", action="store_true")
    return parser.parse_args()


def print_legacy_recommendation(state: MigrationState) -> None:
    if state.migration_complete or state.current_only:
        print("  Migration complete. No legacy cleanup is needed.")
    elif state.preserved_legacy:
        print("  Current profiles are installed and preserved legacy state requires explicit review.")
        print("  Do not repeat automatic migration for preserved modified legacy state.")
    elif state.ownership_unknown:
        print("  Legacy ownership metadata is missing, invalid, or unsafe. Automatic migration is blocked.")
    elif state.legacy_only or state.mixed:
        print("  Run Doctor with explicit legacy migration intent to reconcile proven-owned profile state.")
    else:
        print("  No actionable legacy installation was detected.")


def show_legacy_profile_diagnostics(codex_home: Path) -> None:
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


def _run_owned_action(command: list[str], *, label: str) -> str:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise DoctorError(f"{label} failed{': ' + detail if detail else ''}")
    return (result.stdout or "").strip()


def _explicit_actions(args: argparse.Namespace, codex_home: Path) -> list[str]:
    selected = sum(
        bool(value)
        for value in (
            args.repair,
            args.migrate_legacy,
            args.cleanup_stale,
            args.uninstall_managed,
        )
    )
    if selected > 1:
        raise DoctorError("explicit Doctor maintenance actions are mutually exclusive")

    actions: list[str] = []
    if args.repair or args.migrate_legacy:
        command = [
            sys.executable,
            str(ROOT / "scripts" / "install-agents.py"),
            "--codex-home",
            str(codex_home),
        ]
        if args.migrate_legacy:
            command.append("--migrate-legacy")
        label = "managed profile migration" if args.migrate_legacy else "managed profile repair"
        _run_owned_action(command, label=label)
        actions.append(f"{label} completed")

    if args.uninstall_managed:
        _run_owned_action(
            [
                sys.executable,
                str(ROOT / "scripts" / "uninstall-agents.py"),
                "--codex-home",
                str(codex_home),
            ],
            label="managed profile uninstall",
        )
        actions.append("owned managed Agent profiles removed")

    if args.cleanup_stale:
        if args.thread_id is not None:
            active_thread_id = args.thread_id
            if not active_thread_id.strip():
                raise DoctorError("--cleanup-stale requires a valid CODEX_THREAD_ID")
        else:
            active_thread_id = os.environ.get("CODEX_THREAD_ID")
            if active_thread_id is not None and not active_thread_id.strip():
                active_thread_id = None
        if active_thread_id is not None:
            try:
                legacy_state.resolve_thread_id(active_thread_id)
            except legacy_state.StateIdentityError as exc:
                raise DoctorError(
                    f"--cleanup-stale requires a valid CODEX_THREAD_ID: {exc}"
                ) from exc
        if not args.temp_root.exists():
            report = {"removed": []}
        else:
            try:
                report = legacy_state.cleanup_stale_states(
                    temp_root=args.temp_root,
                    active_thread_id=active_thread_id,
                )
            except (legacy_state.StateIdentityError, legacy_state.StatePathError) as exc:
                raise DoctorError(f"stale cleanup failed safely: {exc}") from exc
        actions.append(
            f"legacy stale cleanup removed {len(report['removed'])} terminal capsule(s)"
        )
    return actions


def diagnose_plugin_package() -> dict[str, Any]:
    try:
        payload = _read_json(PLUGIN)
    except DoctorError as exc:
        return layer("Plugin package", "FAIL", str(exc))
    version = payload.get("version")
    if (
        payload.get("name") != "subagents-dispatch"
        or payload.get("skills") != "./skills/"
        or not isinstance(version, str)
        or not version.strip()
    ):
        return layer("Plugin package", "FAIL", "plugin identity is malformed")

    actual = sorted(path.name for path in SKILLS.iterdir() if path.is_dir()) if SKILLS.is_dir() else []
    if actual != sorted(EXPECTED_SKILLS):
        return layer(
            "Plugin package",
            "FAIL",
            "public Skill surface is invalid",
            expected=list(EXPECTED_SKILLS),
            actual=actual,
        )
    missing = [
        skill_id
        for skill_id in EXPECTED_SKILLS
        if not (SKILLS / skill_id / "SKILL.md").is_file()
        or not (SKILLS / skill_id / "agents" / "openai.yaml").is_file()
    ]
    if missing:
        return layer("Plugin package", "FAIL", "public Skill package is incomplete", missing=missing)
    return layer(
        "Plugin package",
        "OK",
        "package identity and two-Skill surface are intact",
        version=version,
        skills=list(EXPECTED_SKILLS),
    )


def diagnose_managed_agents(codex_home: Path) -> dict[str, Any]:
    try:
        roles = _read_json(POLICY)["roles"]
    except (DoctorError, KeyError, TypeError) as exc:
        return layer("Managed Agents", "FAIL", f"profile policy is unavailable: {exc}")
    if not isinstance(roles, Mapping) or set(roles) != set(EXPECTED_PROFILES):
        return layer("Managed Agents", "FAIL", "managed role set is invalid")

    mismatches: list[str] = []
    for role, (model, effort) in EXPECTED_PROFILES.items():
        spec = roles.get(role)
        if not isinstance(spec, Mapping) or not isinstance(spec.get("profile_file"), str):
            mismatches.append(role)
            continue
        try:
            profile = tomllib.loads(
                (PROFILE_DIR / str(spec["profile_file"])).read_text(encoding="utf-8")
            )
        except (OSError, UnicodeError, tomllib.TOMLDecodeError):
            mismatches.append(role)
            continue
        if (
            spec.get("model") != model
            or spec.get("effort") != effort
            or profile.get("model") != model
            or profile.get("model_reasoning_effort") != effort
        ):
            mismatches.append(role)
    if mismatches:
        return layer(
            "Managed Agents",
            "FAIL",
            "bundled managed Agent profile contract is inconsistent",
            mismatches=mismatches,
        )

    verifier = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "install-agents.py"),
            "--codex-home",
            str(codex_home),
            "--check",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if verifier.returncode == 0:
        return layer(
            "Managed Agents",
            "OK",
            "5/5 managed Agent profiles are installed exactly",
            profiles=5,
        )

    diagnostic = (verifier.stderr or verifier.stdout).strip()
    recoverable = any(diagnostic.startswith(prefix) for prefix in RECOVERABLE_PROFILE_CHECK_PREFIXES)
    if recoverable:
        return layer(
            "Managed Agents",
            "WARN",
            "managed Agent profiles are absent or safely repairable",
            action="Run Doctor repair, then start a fresh Codex task if profiles changed.",
            diagnostic=diagnostic,
            profiles=5,
        )
    return layer(
        "Managed Agents",
        "FAIL",
        "managed Agent profile ownership or filesystem safety check failed",
        action="Resolve the reported ownership or filesystem conflict before repair or delegated execution.",
        diagnostic=diagnostic,
        profiles=5,
    )


def _command_hook_errors(entry: Any, *, matcher: str, script: str, label: str) -> list[str]:
    if not isinstance(entry, Mapping):
        return [f"{label} entry must be an object"]
    if set(entry) != {"matcher", "hooks"}:
        return [f"{label} entry fields are invalid"]
    if entry.get("matcher") != matcher:
        return [f"{label} matcher is invalid"]
    nested = entry.get("hooks")
    if not isinstance(nested, list) or len(nested) != 1 or not isinstance(nested[0], Mapping):
        return [f"{label} must contain exactly one command Hook"]
    hook = nested[0]
    expected = {
        "type": "command",
        "command": HOOK_COMMANDS["posix"].replace("{}", script),
        "commandWindows": HOOK_COMMANDS["windows"].replace("{}", script.replace("/", "\\")),
        "timeout": 5,
        "async": False,
    }
    if dict(hook) != expected:
        return [f"{label} command binding is invalid"]
    return []


def _local_hook_contract() -> tuple[str, set[str], list[str]]:
    try:
        hooks = _read_json(HOOKS).get("hooks")
    except DoctorError as exc:
        return "invalid", set(), [str(exc)]
    if not isinstance(hooks, Mapping):
        return "invalid", set(), ["hooks/hooks.json does not contain a Hook map"]

    events = {str(name) for name in hooks}
    errors: list[str] = []
    if events == COMPATIBILITY_HOOK_EVENTS:
        pre = hooks.get("PreToolUse")
        if not isinstance(pre, list) or len(pre) != 1:
            errors.append("PreToolUse compatibility Hook must have exactly one entry")
        else:
            errors.extend(
                _command_hook_errors(
                    pre[0],
                    matcher=COMPATIBILITY_MATCHER,
                    script=COMPATIBILITY_GUARD_SCRIPT,
                    label="PreToolUse compatibility Hook",
                )
            )
        mode = "compatibility"
    elif events == REQUIRED_HOOK_EVENTS:
        for event in ("PreToolUse", "PostToolUse"):
            entries = hooks.get(event)
            if not isinstance(entries, list) or len(entries) != 1:
                errors.append(f"{event} lifecycle Hook must have exactly one entry")
                continue
            errors.extend(
                _command_hook_errors(
                    entries[0],
                    matcher=LIFECYCLE_MATCHER,
                    script=GUARD_SCRIPT,
                    label=f"{event} lifecycle Hook",
                )
            )
        stop = hooks.get("SubagentStop")
        if not isinstance(stop, list) or len(stop) != 1:
            errors.append("SubagentStop lifecycle Hook must have exactly one entry")
        else:
            errors.extend(
                _command_hook_errors(
                    stop[0],
                    matcher=SUBAGENT_STOP_MATCHER,
                    script=GUARD_SCRIPT,
                    label="SubagentStop lifecycle Hook",
                )
            )
        mode = "lifecycle"
    else:
        mode = "invalid"
        errors.append("installed Hook event set is unsupported")

    scripts = (
        ROOT / "hooks" / "run-python.sh",
        ROOT / "hooks" / "run-python.cmd",
        ROOT / (COMPATIBILITY_GUARD_SCRIPT if mode == "compatibility" else GUARD_SCRIPT),
    )
    if mode != "invalid":
        for path in scripts:
            if path.is_symlink() or not path.is_file():
                errors.append(f"required Hook runtime path is unavailable or unsafe: {path.relative_to(ROOT)}")
    return ("invalid" if errors else mode), events, errors


def diagnose_host_integration(host_evidence: Path | None) -> dict[str, Any]:
    hook_mode, events, hook_errors = _local_hook_contract()
    missing_events = sorted(REQUIRED_HOOK_EVENTS - events)
    if hook_mode == "invalid":
        return layer(
            "Host integration",
            "FAIL",
            "installed lifecycle Hook contract is invalid",
            action="Restore the canonical Plugin package before relying on delegated execution.",
            configured_events=sorted(events),
            missing_events=missing_events,
            hook_errors=hook_errors,
            host_evidence_supplied=host_evidence is not None,
        )

    if host_evidence is None:
        if hook_mode == "compatibility":
            return layer(
                "Host integration",
                "WARN",
                "installed Hook contract provides compatibility spawn guarding only",
                action="Use a package with the complete production lifecycle Hook set before relying on delegated execution.",
                configured_events=sorted(events),
                missing_events=missing_events,
                hook_mode=hook_mode,
                host_evidence_supplied=False,
            )
        return layer(
            "Host integration",
            "UNKNOWN",
            "installed lifecycle Hooks validate; no explicit Host capability snapshot was supplied",
            configured_events=sorted(events),
            missing_events=[],
            hook_mode=hook_mode,
            host_evidence_supplied=False,
        )

    try:
        payload = json.loads(host_evidence.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return layer("Host integration", "FAIL", f"Host evidence is invalid: {exc}")
    if not isinstance(payload, dict):
        return layer("Host integration", "FAIL", "Host evidence must be an object")
    try:
        snapshot = host_capabilities.normalize_host_capabilities(payload)
    except host_capabilities.HostCapabilityError as exc:
        return layer("Host integration", "FAIL", f"Host evidence is invalid: {exc}")

    evidence_details = {
        "host_evidence_supplied": True,
        "host_evidence_source": str(host_evidence),
        "host_evidence_freshness_verified": False,
        "host": snapshot,
    }
    if hook_mode != "lifecycle":
        return layer(
            "Host integration",
            "FAIL",
            "supplied Host capabilities cannot compensate for incomplete installed lifecycle Hooks",
            action="Install a package with the complete production lifecycle Hook set.",
            configured_events=sorted(events),
            missing_events=missing_events,
            hook_mode=hook_mode,
            **evidence_details,
        )
    if snapshot["execution_ready"] is not True:
        return layer(
            "Host integration",
            "FAIL",
            "supplied Host capability evidence is missing required managed-orchestration capabilities",
            missing=snapshot["missing"],
            configured_events=sorted(events),
            hook_mode=hook_mode,
            **evidence_details,
        )
    return layer(
        "Host integration",
        "OK",
        "supplied Host capability evidence and installed lifecycle Hooks satisfy the runtime contract",
        configured_events=sorted(events),
        hook_mode=hook_mode,
        **evidence_details,
    )


def _state_snapshot(
    temp_root: Path,
    thread_id: str | None,
) -> tuple[str, dict[str, Any] | None, str | None]:
    if thread_id is None or not thread_id.strip():
        return "unknown", None, "thread identity unavailable"
    if not temp_root.exists():
        return "absent", None, None
    try:
        path = legacy_state.state_path(thread_id, temp_root=temp_root)
    except (legacy_state.StateIdentityError, legacy_state.StatePathError) as exc:
        return "unsafe", None, str(exc)
    if not path.exists():
        return "absent", None, None
    try:
        if path.is_symlink() or not path.is_file():
            return "unsafe", None, "state path is not a regular file"
        raw = path.read_bytes()
        if len(raw) > state_v4.DEFAULT_MAX_BYTES:
            return "unsafe", None, "state exceeds bounded size"
        payload = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return "unsafe", None, str(exc)
    if not isinstance(payload, dict):
        return "unsafe", None, "state payload is not an object"
    try:
        if payload.get("schema_version") == state_v4.SCHEMA_VERSION:
            return "v4", state_v4.load_state(thread_id, temp_root=temp_root), None
        if payload.get("schema_version") == legacy_state.SCHEMA_VERSION:
            return "v3", legacy_state.load_state(thread_id, temp_root=temp_root), None
    except (state_v4.StateError, legacy_state.StateError) as exc:
        return "unsafe", None, str(exc)
    return "unsafe", None, f"unsupported state schema {payload.get('schema_version')!r}"


def _legacy_profile_status(codex_home: Path) -> tuple[str, str, str | None, dict[str, Any]]:
    state = detect_legacy_state(codex_home)
    details = {
        "legacy_only": state.legacy_only,
        "current_only": state.current_only,
        "mixed": state.mixed,
        "ownership_unknown": state.ownership_unknown,
        "preserved_legacy": state.preserved_legacy,
        "migration_complete": state.migration_complete,
    }
    if state.ownership_unknown:
        return (
            "WARN",
            "legacy managed-profile ownership is unresolved",
            "Review ownership before requesting legacy migration.",
            details,
        )
    if state.preserved_legacy:
        return (
            "WARN",
            "preserved modified legacy profile state requires explicit review",
            "Do not repeat automatic migration for preserved modified legacy state.",
            details,
        )
    if state.legacy_only or state.mixed:
        return (
            "WARN",
            "legacy managed-profile installation state is present",
            "Run Doctor legacy migration only when the legacy installation is proven-owned.",
            details,
        )
    return "OK", "legacy managed-profile installation state is clear", None, details


def diagnose_state(
    temp_root: Path,
    thread_id: str | None,
    codex_home: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    family, payload, error = _state_snapshot(temp_root, thread_id)
    profile_status, profile_summary, profile_action, profile_details = _legacy_profile_status(codex_home)

    def legacy_layer(status: str | None = None, summary: str | None = None, action: str | None = None):
        return layer(
            "Legacy compatibility",
            status or profile_status,
            summary or profile_summary,
            action=action if action is not None else profile_action,
            **profile_details,
        )

    if family == "unsafe":
        return (
            layer("Orchestration state", "FAIL", f"thread state is unsafe or corrupt: {error}"),
            legacy_layer(
                profile_status if profile_status != "OK" else "UNKNOWN",
                profile_summary if profile_status != "OK" else "state family cannot be classified safely",
            ),
        )
    if family == "unknown":
        return (
            layer(
                "Orchestration state",
                "UNKNOWN",
                "no active thread identity is available; thread-specific checks were skipped",
            ),
            legacy_layer(),
        )
    if family == "absent":
        return (
            layer("Orchestration state", "OK", "no thread-scoped orchestration state is active"),
            legacy_layer(),
        )
    if family == "v3":
        assert payload is not None
        unresolved = bool(payload.get("pending_takeover")) or any(
            isinstance(record, Mapping)
            and record.get("control_state") in legacy_state.ACTIVE_STATES
            for record in payload.get("units", [])
        )
        if unresolved:
            return (
                layer(
                    "Orchestration state",
                    "FAIL",
                    "unresolved legacy orchestration state blocks managed execution",
                    action="Resolve the legacy active writer/control state before using Orchestrate.",
                    state_family="v3",
                ),
                legacy_layer(
                    "FAIL",
                    "legacy orchestration state will not be silently migrated",
                    "Resolve active legacy ownership first.",
                ),
            )
        return (
            layer(
                "Orchestration state",
                "WARN",
                "terminal legacy orchestration state is present",
                action="Terminal legacy state may be cleaned only with explicit Doctor cleanup intent.",
                state_family="v3",
            ),
            legacy_layer(
                "WARN",
                "legacy orchestration state will not be silently migrated",
                "Use explicit stale cleanup only after confirming the state is terminal.",
            ),
        )

    assert family == "v4" and payload is not None
    lease = payload["writer_lease"]
    controls = payload["pending_controls"]
    executions = payload["executions"]
    critical: list[str] = []
    attention: list[str] = []

    if lease is not None:
        if lease["state"] == "UNKNOWN":
            critical.append("WriterLease.UNKNOWN")
        elif lease["state"] in {"RESERVED", "HELD", "REVOKING"}:
            attention.append(f"WriterLease.{lease['state']}")
    unknown_controls = [item["control_id"] for item in controls if item.get("state") == "UNKNOWN"]
    if unknown_controls:
        critical.append("PendingControl.UNKNOWN")
    if any(item.get("state") in {"PREPARED", "IN_FLIGHT"} for item in controls):
        attention.append("PendingControl active")
    unknown_executions = [
        item["execution_id"] for item in executions if item.get("lifecycle") == "UNKNOWN"
    ]
    if unknown_executions:
        critical.append("Execution lifecycle UNKNOWN")

    if critical:
        orchestration = layer(
            "Orchestration state",
            "FAIL",
            "safety-critical orchestration state is unresolved",
            action="Keep delegated writes blocked until fresh authoritative Host evidence resolves the state.",
            critical=critical,
            unknown_controls=unknown_controls,
            unknown_executions=unknown_executions,
            writer_lease=lease,
        )
    elif attention:
        orchestration = layer(
            "Orchestration state",
            "WARN",
            "orchestration is active and currently fail-closed where control is unresolved",
            active=attention,
            work_units=len(payload["work_units"]),
            executions=len(executions),
            state_revision=payload["state_revision"],
        )
    else:
        orchestration = layer(
            "Orchestration state",
            "OK",
            "thread-scoped V4 orchestration state validates",
            work_units=len(payload["work_units"]),
            executions=len(executions),
            state_revision=payload["state_revision"],
        )
    return orchestration, legacy_layer(summary="active thread uses V4 state; " + profile_summary)


def diagnose(args: argparse.Namespace, codex_home: Path) -> dict[str, Any]:
    thread_id = args.thread_id if args.thread_id is not None else os.environ.get("CODEX_THREAD_ID")
    orchestration, legacy = diagnose_state(args.temp_root, thread_id, codex_home)
    layers = [
        diagnose_plugin_package(),
        diagnose_managed_agents(codex_home),
        diagnose_host_integration(args.host_evidence),
        orchestration,
        legacy,
    ]
    by_name = {item["name"]: item for item in layers}
    ordered = [by_name[name] for name in LAYER_ORDER]
    blocked = any(item["status"] == "FAIL" for item in ordered)
    degraded = any(item["status"] in {"WARN", "UNKNOWN"} for item in ordered)
    return {
        "schema_version": 5,
        "healthy": not blocked,
        "status": "BLOCKED" if blocked else "DEGRADED" if degraded else "HEALTHY",
        "layers": ordered,
    }


def render_text(report: Mapping[str, Any], actions: list[str]) -> str:
    lines = [
        "Subagents Dispatch Doctor",
        "Mode: installed-plugin diagnostics; read-only and offline by default",
        "",
    ]
    for item in report.get("layers", []):
        lines.append(f"[{item['status']}] {item['name']}: {item['summary']}")
        if isinstance(item.get("action"), str) and item["action"].strip():
            lines.append(f"       Action: {item['action']}")
    if actions:
        lines.extend(["", "Actions applied"])
        lines.extend(f"[OK] {action}" for action in actions)
    lines.extend(["", f"Overall: {report.get('status', 'BLOCKED')}"])
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    codex_home = args.codex_home.expanduser()
    if codex_home.is_symlink():
        fail(f"Refusing symlinked Codex home: {codex_home}")
    codex_home = codex_home.resolve()
    if args.legacy:
        show_legacy_profile_diagnostics(codex_home)
        return
    try:
        actions = _explicit_actions(args, codex_home)
        report = diagnose(args, codex_home)
    except DoctorError as exc:
        fail(str(exc))
    if args.json:
        output = dict(report)
        output["actions"] = actions
        print(json.dumps(output, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    else:
        print(render_text(report, actions))
    if args.check and report["healthy"] is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
