#!/usr/bin/env python3
"""Deterministic product Doctor for the installed subagents-dispatch plugin."""

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
LAYER_ORDER = (
    "Plugin package",
    "Managed Agents",
    "Host integration",
    "Orchestration state",
    "Legacy compatibility",
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
        description="Diagnose and explicitly maintain the installed subagents-dispatch plugin."
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
        suffix = f": {detail}" if detail else ""
        raise DoctorError(f"{label} failed{suffix}")
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
        _run_owned_action(
            command,
            label="managed profile migration" if args.migrate_legacy else "managed profile repair",
        )
        actions.append(
            "managed profile migration completed"
            if args.migrate_legacy
            else "managed profile repair completed"
        )

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

    actual_skills = (
        sorted(path.name for path in SKILLS.iterdir() if path.is_dir())
        if SKILLS.is_dir()
        else []
    )
    if actual_skills != sorted(EXPECTED_SKILLS):
        return layer(
            "Plugin package",
            "FAIL",
            "public Skill surface is invalid",
            expected=list(EXPECTED_SKILLS),
            actual=actual_skills,
        )

    missing = [
        skill_id
        for skill_id in EXPECTED_SKILLS
        if not (SKILLS / skill_id / "SKILL.md").is_file()
        or not (SKILLS / skill_id / "agents" / "openai.yaml").is_file()
    ]
    if missing:
        return layer(
            "Plugin package",
            "FAIL",
            "public Skill package is incomplete",
            missing=missing,
        )

    return layer(
        "Plugin package",
        "OK",
        "package identity and two-Skill surface are intact",
        version=version,
        skills=list(EXPECTED_SKILLS),
    )


def diagnose_managed_agents(codex_home: Path) -> dict[str, Any]:
    try:
        policy = _read_json(POLICY)
        roles = policy["roles"]
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

    return layer(
        "Managed Agents",
        "WARN",
        "bundled profiles are valid but the active Codex home is not installed exactly",
        action="Run Doctor repair, then start a fresh Codex task if profiles changed.",
        profiles=5,
    )


def _hook_events() -> tuple[set[str], str | None]:
    try:
        payload = _read_json(HOOKS)
    except DoctorError as exc:
        return set(), str(exc)
    hooks = payload.get("hooks")
    if not isinstance(hooks, Mapping):
        return set(), "hooks/hooks.json does not contain a Hook map"
    return set(str(name) for name in hooks), None


def diagnose_host_integration(host_evidence: Path | None) -> dict[str, Any]:
    events, hook_error = _hook_events()
    if hook_error is not None:
        return layer("Host integration", "FAIL", hook_error)

    missing_events = sorted(REQUIRED_HOOK_EVENTS - events)

    if host_evidence is None:
        if missing_events:
            return layer(
                "Host integration",
                "WARN",
                "local lifecycle Hook configuration is incomplete",
                action="Use a package with the complete production lifecycle Hook set before relying on delegated execution.",
                configured_events=sorted(events),
                missing_events=missing_events,
                live_host_observed=False,
            )
        return layer(
            "Host integration",
            "UNKNOWN",
            "local lifecycle Hooks are configured; live Host capability evidence was not supplied",
            configured_events=sorted(events),
            missing_events=[],
            live_host_observed=False,
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

    if missing_events:
        return layer(
            "Host integration",
            "FAIL",
            "Host capabilities are evidenced but the installed lifecycle Hook configuration is incomplete",
            action="Install a package with the complete production lifecycle Hook set.",
            configured_events=sorted(events),
            missing_events=missing_events,
            live_host_observed=True,
            host=snapshot,
        )

    if snapshot["execution_ready"] is not True:
        return layer(
            "Host integration",
            "FAIL",
            "the current Host is missing required managed-orchestration capabilities",
            missing=snapshot["missing"],
            live_host_observed=True,
            host=snapshot,
        )

    return layer(
        "Host integration",
        "OK",
        "required Host capabilities and local lifecycle Hooks are evidenced",
        configured_events=sorted(events),
        live_host_observed=True,
        host=snapshot,
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

    schema = payload.get("schema_version")
    try:
        if schema == state_v4.SCHEMA_VERSION:
            return "v4", state_v4.load_state(thread_id, temp_root=temp_root), None
        if schema == legacy_state.SCHEMA_VERSION:
            return "v3", legacy_state.load_state(thread_id, temp_root=temp_root), None
    except (state_v4.StateError, legacy_state.StateError) as exc:
        return "unsafe", None, str(exc)
    return "unsafe", None, f"unsupported state schema {schema!r}"


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
    return ("OK", "legacy managed-profile installation state is clear", None, details)


def diagnose_state(
    temp_root: Path,
    thread_id: str | None,
    codex_home: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    family, payload, error = _state_snapshot(temp_root, thread_id)
    profile_status, profile_summary, profile_action, profile_details = _legacy_profile_status(
        codex_home
    )

    if family == "unsafe":
        return (
            layer(
                "Orchestration state",
                "FAIL",
                f"thread state is unsafe or corrupt: {error}",
            ),
            layer(
                "Legacy compatibility",
                profile_status if profile_status != "OK" else "UNKNOWN",
                profile_summary
                if profile_status != "OK"
                else "state family cannot be classified safely",
                action=profile_action,
                **profile_details,
            ),
        )

    if family == "unknown":
        return (
            layer(
                "Orchestration state",
                "UNKNOWN",
                "no active thread identity is available; thread-specific checks were skipped",
            ),
            layer(
                "Legacy compatibility",
                profile_status,
                profile_summary,
                action=profile_action,
                **profile_details,
            ),
        )

    if family == "absent":
        return (
            layer(
                "Orchestration state",
                "OK",
                "no thread-scoped orchestration state is active",
            ),
            layer(
                "Legacy compatibility",
                profile_status,
                profile_summary,
                action=profile_action,
                **profile_details,
            ),
        )

    if family == "v3":
        assert payload is not None
        unresolved = bool(payload.get("pending_takeover")) or any(
            isinstance(record, Mapping)
            and record.get("control_state") in legacy_state.ACTIVE_STATES
            for record in payload.get("units", [])
        )
        status = "FAIL" if unresolved else "WARN"
        summary = (
            "unresolved legacy orchestration state blocks managed execution"
            if unresolved
            else "terminal legacy orchestration state is present"
        )
        legacy_status = "FAIL" if unresolved else "WARN"
        return (
            layer(
                "Orchestration state",
                status,
                summary,
                action=(
                    "Resolve the legacy active writer/control state before using Orchestrate."
                    if unresolved
                    else "Terminal legacy state may be cleaned only with explicit Doctor cleanup intent."
                ),
                state_family="v3",
            ),
            layer(
                "Legacy compatibility",
                legacy_status,
                "legacy orchestration state will not be silently migrated",
                action=(
                    "Resolve active legacy ownership first."
                    if unresolved
                    else "Use explicit stale cleanup only after confirming the state is terminal."
                ),
                **profile_details,
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

    unknown_controls = [
        item["control_id"] for item in controls if item.get("state") == "UNKNOWN"
    ]
    if unknown_controls:
        critical.append("PendingControl.UNKNOWN")

    pending_controls = [
        item["control_id"]
        for item in controls
        if item.get("state") in {"PREPARED", "IN_FLIGHT"}
    ]
    if pending_controls:
        attention.append("PendingControl active")

    unknown_executions = [
        item["execution_id"]
        for item in executions
        if item.get("lifecycle") == "UNKNOWN"
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

    legacy = layer(
        "Legacy compatibility",
        profile_status,
        "active thread uses V4 state; " + profile_summary,
        action=profile_action,
        **profile_details,
    )
    return orchestration, legacy


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
    overall = "BLOCKED" if blocked else "DEGRADED" if degraded else "HEALTHY"
    return {
        "schema_version": 5,
        "healthy": not blocked,
        "status": overall,
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
        action = item.get("action")
        if isinstance(action, str) and action.strip():
            lines.append(f"       Action: {action}")

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
