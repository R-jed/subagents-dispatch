#!/usr/bin/env python3
"""Deterministic read-only production diagnostics for subagents-dispatch."""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from typing import Any, Mapping

from dispatch_state import (  # type: ignore[import-not-found]
    ACTIVE_STATES,
    DEFAULT_STALE_AFTER,
    LOCK_FILE,
    STATE_DIRECTORY,
    StateCorruptError,
    StateIdentityError,
    StatePathError,
    _reject_symlink,
    _temporary_root,
    is_stale,
    load_state,
    resolve_thread_id,
)
from legacy_migration import detect_legacy_state, format_migration_state
from policy import load_policy_contract


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_MANIFEST = ROOT / ".codex-plugin" / "plugin.json"
HOOKS_MANIFEST = ROOT / "hooks" / "hooks.json"
MARKETPLACE_MANIFEST = ROOT / ".agents" / "plugins" / "marketplace.json"
SPAWN_GUARD = ROOT / "scripts" / "spawn_guard.py"
UNIX_HOOK_LAUNCHER = ROOT / "hooks" / "run-python.sh"
WINDOWS_HOOK_LAUNCHER = ROOT / "hooks" / "run-python.cmd"
EXPECTED_SKILLS = ("dispatch", "preview", "status", "steer", "takeover", "doctor")
PRODUCTION_LAYERS = (
    "Plugin",
    "Skills",
    "Spawn guard package",
    "Managed Agent profiles",
    "Dispatch state",
    "Codex Host",
    "Spawn guard runtime",
    "Runtime route",
    "Effective permission state",
    "Permission-source provenance",
)
EXPECTED_HOOK_COMMAND = '"${PLUGIN_ROOT}/hooks/run-python.sh" "${PLUGIN_ROOT}/scripts/spawn_guard.py"'
EXPECTED_HOOK_COMMAND_WINDOWS = '"%PLUGIN_ROOT%\\hooks\\run-python.cmd" "%PLUGIN_ROOT%\\scripts\\spawn_guard.py"'


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


def read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, str(exc)
    if not isinstance(payload, dict):
        return None, "JSON value must be an object"
    return payload, None


def read_json_text(raw: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, str(exc)
    if not isinstance(payload, dict):
        return None, "JSON value must be an object"
    return payload, None


def diagnose_plugin() -> dict[str, Any]:
    payload, error = read_json(PLUGIN_MANIFEST)
    if error:
        return layer("Plugin", "FAIL", f"cannot read plugin manifest: {error}")
    assert payload is not None
    mismatches: list[str] = []
    if payload.get("name") != "subagents-dispatch":
        mismatches.append("name")
    version = payload.get("version")
    if not isinstance(version, str) or not version.strip():
        mismatches.append("version")
    if payload.get("skills") != "./skills/":
        mismatches.append("skills path")
    if "hooks" in payload:
        mismatches.append("explicit hooks field")
    if mismatches:
        return layer(
            "Plugin",
            "FAIL",
            "manifest does not match the packaged identity",
            mismatches=mismatches,
        )
    marketplace, marketplace_error = read_json(MARKETPLACE_MANIFEST)
    if marketplace_error:
        return layer("Plugin", "FAIL", f"cannot read marketplace manifest: {marketplace_error}")
    assert marketplace is not None
    plugins = marketplace.get("plugins")
    source = (
        plugins[0].get("source")
        if isinstance(plugins, list) and plugins and isinstance(plugins[0], dict)
        else None
    )
    if not isinstance(source, dict) or source.get("ref") != f"v{version}":
        return layer(
            "Plugin",
            "FAIL",
            "marketplace source is not pinned to the packaged release",
            expected_ref=f"v{version}",
        )
    return layer("Plugin", "OK", "manifest and packaged identity match", version=version)


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
        return layer(
            "Skills",
            "FAIL",
            "explicit Skill adapters are incomplete",
            missing=missing,
            invalid=invalid,
        )
    return layer("Skills", "OK", "six explicit Skill adapters are present", count=6)


def _hook_handler() -> tuple[dict[str, Any] | None, str | None]:
    hooks, error = read_json(HOOKS_MANIFEST)
    if error:
        return None, f"default hooks config is unreadable: {error}"
    assert hooks is not None
    events = hooks.get("hooks")
    if not isinstance(events, dict) or set(events) != {"PreToolUse"}:
        return None, "hooks config must contain only PreToolUse"
    groups = events.get("PreToolUse")
    if not isinstance(groups, list) or len(groups) != 1 or not isinstance(groups[0], dict):
        return None, "PreToolUse must contain exactly one matcher group"
    group = groups[0]
    if group.get("matcher") != "spawn_agent":
        return None, "PreToolUse matcher must be exactly spawn_agent"
    handlers = group.get("hooks")
    if not isinstance(handlers, list) or len(handlers) != 1 or not isinstance(handlers[0], dict):
        return None, "spawn_agent matcher must contain exactly one handler"
    return handlers[0], None


def diagnose_spawn_guard_package() -> dict[str, Any]:
    handler, error = _hook_handler()
    if error:
        return layer("Spawn guard package", "FAIL", error)
    assert handler is not None
    mismatches: list[str] = []
    if handler.get("type") != "command":
        mismatches.append("handler type")
    if handler.get("command") != EXPECTED_HOOK_COMMAND:
        mismatches.append("Unix command")
    if handler.get("commandWindows") != EXPECTED_HOOK_COMMAND_WINDOWS:
        mismatches.append("Windows command")
    if handler.get("timeout") != 5:
        mismatches.append("timeout")
    if handler.get("async", False) is not False:
        mismatches.append("execution mode")
    required = (SPAWN_GUARD, UNIX_HOOK_LAUNCHER, WINDOWS_HOOK_LAUNCHER)
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if os.name != "nt" and UNIX_HOOK_LAUNCHER.is_file():
        try:
            if not UNIX_HOOK_LAUNCHER.stat().st_mode & stat.S_IXUSR:
                mismatches.append("Unix launcher executable bit")
        except OSError:
            mismatches.append("Unix launcher metadata")
    try:
        policy = load_policy_contract()
    except RuntimeError:
        policy = {}
    if policy.get("delegation") != {"max_depth": 1, "fork_turns": "none"}:
        mismatches.append("delegation policy")
    if missing or mismatches:
        return layer(
            "Spawn guard package",
            "FAIL",
            "packaged spawn guard differs from its deterministic boundary",
            missing=missing,
            mismatches=mismatches,
        )
    return layer(
        "Spawn guard package",
        "OK",
        "one synchronous default-discovered spawn_agent PreToolUse guard is packaged exactly",
        matcher="spawn_agent",
        timeout_seconds=5,
        mutation=False,
        discovery_path="hooks/hooks.json",
    )


def _expected_profile_paths(codex_home: Path) -> list[Path]:
    try:
        roles = load_policy_contract().get("roles")
    except RuntimeError:
        return []
    if not isinstance(roles, dict):
        return []
    return [
        codex_home / "agents" / spec["profile_file"]
        for spec in roles.values()
        if isinstance(spec, dict) and isinstance(spec.get("profile_file"), str)
    ]


def diagnose_profiles(codex_home: Path) -> dict[str, Any]:
    expected = _expected_profile_paths(codex_home)
    if len(expected) != 5:
        return layer("Managed Agent profiles", "FAIL", "policy-owned managed profile set is invalid")
    missing = [str(path) for path in expected if not path.is_file() or path.is_symlink()]
    legacy = detect_legacy_state(codex_home)
    legacy_status = format_migration_state(legacy)
    legacy_review = legacy.legacy_only or legacy.mixed or legacy.ownership_unknown
    if missing:
        return layer(
            "Managed Agent profiles",
            "WARN",
            "managed Agent profiles are not provisioned as one complete exact set",
            action="Use an explicit Dispatch that needs delegation or Doctor repair, then start a fresh Codex task/session.",
            missing=missing,
            legacy_status=legacy_status,
        )
    verifier = ROOT / "scripts" / "install-agents.py"
    try:
        result = subprocess.run(
            [sys.executable, str(verifier), "--codex-home", str(codex_home), "--check"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return layer("Managed Agent profiles", "FAIL", "installer exact-state verifier timed out")
    except OSError as exc:
        return layer("Managed Agent profiles", "FAIL", f"installer exact-state verifier failed: {exc}")
    if result.returncode != 0:
        return layer(
            "Managed Agent profiles",
            "FAIL",
            "installer exact-state verifier rejected the installed managed set",
            action="Review the managed profile conflict before running an explicit repair.",
            verifier_returncode=result.returncode,
            legacy_status=legacy_status,
        )
    return layer(
        "Managed Agent profiles",
        "WARN" if legacy_review else "OK",
        "installer --check passed; legacy state requires explicit review"
        if legacy_review
        else "installer --check passed",
        action="Review preserved legacy ownership before cleanup." if legacy_review else None,
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
    try:
        root_base = _temporary_root(temp_root)
    except StatePathError as exc:
        return None, [], str(exc)
    root = root_base / STATE_DIRECTORY
    try:
        _reject_symlink(root, "dispatch state root")
    except StatePathError as exc:
        return root, [], str(exc)
    if not root.exists():
        return root, [], None
    if not root.is_dir():
        return root, [], "dispatch state root is not a directory"
    try:
        return root, sorted(root.iterdir(), key=lambda item: item.name), None
    except OSError as exc:
        return root, [], f"dispatch state root is unreadable: {exc}"


def _unexpected_repository_state(root: Path = ROOT) -> list[str]:
    ignored = {".git", ".venv", ".pytest_cache", ".ruff_cache", "__pycache__"}
    forbidden_prefixes = ("team-plan-", "ledger-", "receipt-", "recovery-")
    unexpected: list[str] = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if any(part in ignored for part in relative.parts):
            continue
        if path.name.startswith(forbidden_prefixes) or (
            path.name == "active.json" and STATE_DIRECTORY in relative.parts[:-1]
        ):
            unexpected.append(relative.as_posix())
    return sorted(unexpected)


def diagnose_dispatch_state(temp_root: Path, thread_id: str | None) -> dict[str, Any]:
    root, entries, root_error = _state_entries(temp_root)
    if root_error:
        return layer("Dispatch state", "FAIL", root_error, mutated=False)
    if root is None:
        return layer("Dispatch state", "FAIL", "dispatch state root cannot be resolved", mutated=False)
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
    pending_takeovers: list[str] = []
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
        if payload.get("pending_takeover") is not None:
            pending_takeovers.append(entry_id)
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
        "active_orchestration": bool(active_units or pending_takeovers),
        "active_units": sorted(set(active_units)),
        "pending_takeovers": sorted(set(pending_takeovers)),
        "stale_count": len(set(stale)),
        "state_lock_health": "issue" if lock_issues else ("ok" if entries else "not_present"),
        "lock_issues": sorted(set(lock_issues)),
        "schema_health": "issue" if corrupt else "ok",
        "unexpected_repository_state": _unexpected_repository_state(),
        "mutated": False,
    }
    if corrupt or unsafe or details["unexpected_repository_state"]:
        return layer(
            "Dispatch state",
            "FAIL",
            "corrupt or unsafe state is preserved for explicit review",
            action="Resolve the preserved unsafe state explicitly; Doctor will not delete it automatically.",
            corrupt=sorted(set(corrupt)),
            unsafe=sorted(set(unsafe)),
            **details,
        )
    if stale or active_writers or ambiguous_writers or pending_takeovers or lock_issues:
        return layer(
            "Dispatch state",
            "WARN",
            "stale or unresolved writer state is retained; no automatic deletion occurred",
            action="Use Status or explicit Takeover/cleanup according to the reported state.",
            stale=sorted(set(stale)),
            active_writers=sorted(set(active_writers)),
            ambiguous_writers=sorted(set(ambiguous_writers)),
            stale_after_days=int(DEFAULT_STALE_AFTER.total_seconds() // 86400),
            **details,
        )
    if thread_issue is not None:
        return layer("Dispatch state", "UNKNOWN", thread_issue, capsules_read=readable, **details)
    return layer(
        "Dispatch state",
        "OK",
        "thread-scoped state is absent or valid",
        capsules_read=readable,
        **details,
    )


def _host_payload(host_evidence: Path | None) -> tuple[dict[str, Any] | None, str | None]:
    evidence_path = host_evidence
    if evidence_path is None:
        raw = os.environ.get("SUBAGENTS_DISPATCH_HOST_EVIDENCE")
        evidence_path = Path(raw) if raw else None
    if evidence_path is None:
        return None, None
    return read_json(evidence_path)


def diagnose_host(host_evidence: Path | None) -> dict[str, Any]:
    payload, error = _host_payload(host_evidence)
    if payload is None and error is None:
        return layer(
            "Codex Host",
            "UNKNOWN",
            "Host capability evidence is unavailable; supported limitation",
            observed=False,
        )
    if error:
        return layer("Codex Host", "FAIL", f"invalid explicit Host evidence: {error}", observed=False)
    assert payload is not None
    capabilities = payload.get("capabilities")
    if capabilities is None:
        return layer(
            "Codex Host",
            "UNKNOWN",
            "explicit Host evidence does not expose capabilities; supported limitation",
            observed=False,
        )
    if not isinstance(capabilities, list) or not all(
        isinstance(item, str) and item.strip() for item in capabilities
    ):
        return layer("Codex Host", "FAIL", "explicit Host evidence requires a capabilities list", observed=False)
    if not capabilities:
        return layer(
            "Codex Host",
            "UNKNOWN",
            "Host reported no supported capabilities; supported limitation",
            capabilities=[],
            observed=True,
        )
    return layer(
        "Codex Host",
        "OK",
        "explicit Host capability evidence was supplied",
        capabilities=sorted(set(capabilities)),
        observed=True,
    )


def diagnose_spawn_guard_runtime(host_evidence: Path | None) -> dict[str, Any]:
    payload, error = _host_payload(host_evidence)
    if payload is None and error is None:
        return layer(
            "Spawn guard runtime",
            "UNKNOWN",
            "Host Hook discovery/trust evidence was not supplied",
            observed=False,
        )
    if error:
        return layer("Spawn guard runtime", "FAIL", f"invalid explicit Host evidence: {error}", observed=False)
    assert payload is not None
    capabilities = payload.get("capabilities")
    if isinstance(capabilities, list):
        normalized = {str(item).strip().lower() for item in capabilities}
        if "hooks" not in normalized:
            return layer(
                "Spawn guard runtime",
                "UNKNOWN",
                "current Host evidence does not establish Hook support",
                observed=True,
            )
    rows = payload.get("plugin_hooks")
    if rows is None:
        return layer(
            "Spawn guard runtime",
            "UNKNOWN",
            "Host evidence does not include normalized Plugin Hook state",
            observed=False,
        )
    if not isinstance(rows, list) or not all(isinstance(item, dict) for item in rows):
        return layer("Spawn guard runtime", "FAIL", "plugin_hooks evidence must be an array of objects")
    matches = [
        item
        for item in rows
        if item.get("plugin") == "subagents-dispatch" and item.get("event") == "PreToolUse"
    ]
    if not matches:
        return layer(
            "Spawn guard runtime",
            "WARN",
            "Host reports Hook support but no active subagents-dispatch PreToolUse guard",
            action="Review Plugin Hook trust/enablement and restart Codex if the installed Plugin changed.",
            observed=True,
        )
    if len(matches) != 1:
        return layer(
            "Spawn guard runtime",
            "FAIL",
            "Host reports duplicate subagents-dispatch PreToolUse guards",
            action="Remove duplicate or conflicting Hook registration before Dispatch delegation.",
            count=len(matches),
            observed=True,
        )
    row = matches[0]
    source = str(row.get("source", "")).lower()
    handler_type = str(row.get("handler_type", "")).lower()
    execution_mode = str(row.get("execution_mode", "")).lower()
    trust_status = str(row.get("trust_status", "")).lower()
    enabled = row.get("enabled")
    if source != "plugin" or handler_type != "command" or execution_mode != "sync":
        return layer(
            "Spawn guard runtime",
            "FAIL",
            "Host Hook identity or execution mode differs from the packaged guard",
            source=source,
            handler_type=handler_type,
            execution_mode=execution_mode,
            observed=True,
        )
    if trust_status == "modified":
        return layer(
            "Spawn guard runtime",
            "FAIL",
            "Host reports the trusted Plugin Hook changed after review",
            action="Review the changed Plugin Hook before trusting the new hash.",
            trust_status=trust_status,
            observed=True,
        )
    if enabled is False or trust_status == "untrusted":
        return layer(
            "Spawn guard runtime",
            "WARN",
            "Plugin Hook is present but is not currently trusted and enabled",
            action="Review and trust/enable the packaged Hook in Codex if you want the mechanical spawn guard active.",
            trust_status=trust_status or None,
            enabled=enabled,
            observed=True,
        )
    if enabled is True and trust_status in {"trusted", "managed"}:
        return layer(
            "Spawn guard runtime",
            "OK",
            "Host reports one trusted synchronous Plugin spawn guard",
            trust_status=trust_status,
            enabled=True,
            observed=True,
        )
    return layer(
        "Spawn guard runtime",
        "UNKNOWN",
        "Host Hook evidence is incomplete for trust or enablement",
        trust_status=trust_status or None,
        enabled=enabled,
        observed=True,
    )


def _assurance_layer(
    name: str,
    assurance: Any,
    *,
    required: bool,
    live_route: bool,
) -> dict[str, Any]:
    item = assurance if isinstance(assurance, dict) else {}
    raw_status = item.get("status", "unknown")
    status = {"verified": "OK", "failed": "FAIL", "unknown": "UNKNOWN"}.get(
        raw_status,
        "UNKNOWN",
    )
    summaries = {
        "verified": f"{name.lower()} is verified by observed Host evidence",
        "failed": f"{name.lower()} conflicts with observed Host evidence",
        "unknown": f"{name.lower()} is not exposed by current Host evidence",
    }
    return layer(
        name,
        status,
        summaries.get(raw_status, summaries["unknown"]),
        assurance_status=raw_status,
        required=required,
        live_route=live_route,
        source=item.get("source"),
        violations=item.get("violations", []),
    )


def _formal_live_route_issue(payload: dict[str, Any]) -> str | None:
    if payload.get("subject") != "child":
        return "formal --live-route evidence must explicitly declare subject=child"
    expected = payload.get("expected")
    if not isinstance(expected, dict):
        return "formal --live-route evidence requires an expected child route"
    for field in ("thread_id", "parent_thread_id"):
        value = expected.get(field)
        if not isinstance(value, str) or not value.strip():
            return f"formal --live-route evidence requires expected.{field}"
    for flag in ("runtime_observation_required", "requires_permission_observation"):
        if expected.get(flag) is not True:
            return f"formal --live-route evidence requires expected.{flag}=true"
    return None


def diagnose_runtime(evidence_path: Path | None, live_route: bool) -> list[dict[str, Any]]:
    def unavailable(route_status: str, summary: str) -> list[dict[str, Any]]:
        return [
            layer("Runtime route", route_status, summary, observed=False),
            layer("Effective permission state", "UNKNOWN", summary, observed=False),
            layer("Permission-source provenance", "UNKNOWN", summary, observed=False),
        ]

    if evidence_path is None:
        return unavailable(
            "UNKNOWN",
            "not run; pass --runtime-evidence with explicit evidence (or --live-route to record the limitation)",
        )
    evidence_payload, evidence_error = read_json(evidence_path)
    if evidence_error:
        return unavailable("FAIL", f"invalid runtime evidence: {evidence_error}")
    assert evidence_payload is not None
    if live_route:
        issue = _formal_live_route_issue(evidence_payload)
        if issue is not None:
            return unavailable("FAIL", issue)
    verifier = ROOT / "scripts" / "runtime-evidence.py"
    try:
        result = subprocess.run(
            [sys.executable, str(verifier), "--input", str(evidence_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return unavailable("FAIL", f"runtime-evidence normalizer failed: {exc}")
    if result.returncode != 0:
        return unavailable("FAIL", "runtime-evidence normalizer rejected the supplied evidence")
    payload, error = read_json_text(result.stdout)
    if error:
        return unavailable("FAIL", f"runtime-evidence output is invalid: {error}")
    assert payload is not None
    expected = evidence_payload.get("expected")
    requirements = expected if live_route and isinstance(expected, dict) else {}
    return [
        _assurance_layer(
            "Runtime route",
            payload.get("route_assurance"),
            required=requirements.get("runtime_observation_required") is True,
            live_route=live_route,
        ),
        _assurance_layer(
            "Effective permission state",
            payload.get("permission_state_assurance"),
            required=requirements.get("requires_permission_observation") is True,
            live_route=live_route,
        ),
        _assurance_layer(
            "Permission-source provenance",
            payload.get("permission_provenance_assurance"),
            required=requirements.get("requires_permission_provenance") is True,
            live_route=live_route,
        ),
    ]


def diagnose(
    *,
    codex_home: Path,
    temp_root: Path,
    thread_id: str | None,
    runtime_evidence: Path | None,
    live_route: bool,
    host_evidence: Path | None,
) -> dict[str, Any]:
    layers = [
        diagnose_plugin(),
        diagnose_skills(),
        diagnose_spawn_guard_package(),
        diagnose_profiles(codex_home),
        diagnose_dispatch_state(temp_root, thread_id),
        diagnose_host(host_evidence),
        diagnose_spawn_guard_runtime(host_evidence),
        *diagnose_runtime(runtime_evidence, live_route),
    ]
    assert tuple(item["name"] for item in layers) == PRODUCTION_LAYERS
    return {"schema_version": 2, "layers": layers}


def calculate_health(layers: list[dict[str, Any]], *, live_route: bool) -> bool:
    healthy = not any(item.get("status") in {"WARN", "FAIL"} for item in layers)
    if live_route:
        required = [
            item
            for item in layers
            if item.get("details", {}).get("live_route") is True
            and item.get("details", {}).get("required") is True
        ]
        healthy = healthy and all(item.get("status") == "OK" for item in required)
    return healthy


def render_text(report: Mapping[str, Any]) -> str:
    lines = [
        "Subagents Dispatch Doctor",
        "Mode: deterministic diagnostics; read-only unless an explicit lifecycle action was requested",
        "",
    ]
    layers = report.get("layers", [])
    for item in layers:
        if not isinstance(item, Mapping):
            continue
        status = str(item.get("status", "UNKNOWN"))
        lines.append(f"[{status}] {item.get('name', 'Unknown')}: {item.get('summary', '')}")
        action = item.get("action")
        if isinstance(action, str) and action:
            lines.append(f"       Action: {action}")
    development = report.get("development_layers", [])
    if isinstance(development, list) and development:
        lines.extend(["", "Development checks"])
        for item in development:
            if isinstance(item, Mapping):
                lines.append(
                    f"[{item.get('status', 'UNKNOWN')}] {item.get('name', 'Unknown')}: {item.get('summary', '')}"
                )
    actions = report.get("actions", [])
    if isinstance(actions, list) and actions:
        lines.extend(["", "Actions applied"])
        lines.extend(f"[OK] {action}" for action in actions)
    counts = {
        key: sum(
            1
            for item in layers
            if isinstance(item, Mapping) and item.get("status") == key
        )
        for key in ("OK", "WARN", "FAIL", "UNKNOWN")
    }
    verdict = "HEALTHY" if report.get("healthy") is True else "ATTENTION"
    if counts["FAIL"]:
        verdict = "UNHEALTHY"
    lines.extend(
        [
            "",
            f"Overall: {verdict}",
            f"{counts['FAIL']} failed · {counts['WARN']} warnings · {counts['UNKNOWN']} unknown",
        ]
    )
    return "\n".join(lines)
