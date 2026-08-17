#!/usr/bin/env python3
"""V4 deterministic Doctor runtime with bounded V3.x compatibility diagnostics."""

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
import doctor_core as compatibility_core
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
STAGED_HOOKS = ROOT / "docs" / "v4" / "hooks.json"
HOST_SMOKE = ROOT / "docs" / "v4" / "host-smoke.json"
PROFILE_DIR = ROOT / "agent-profiles"
SKILLS = ROOT / "skills"
EXPECTED_SKILLS = ("orchestrate", "doctor")
EXPECTED_HOST_PROBES = tuple(f"H{index:02d}" for index in range(11))
EXPECTED_PROFILES = {
    "reader": ("gpt-5.6-luna", "max"),
    "worker": ("gpt-5.6-luna", "max"),
    "investigator": ("gpt-5.6-terra", "high"),
    "solver": ("gpt-5.6-sol", "high"),
    "advisor": ("gpt-5.6-sol", "high"),
}
LAYER_ORDER = (
    "Plugin",
    "Public Skills",
    "Fixed execution profiles",
    "V4 state",
    "Legacy V3.x state",
    "Work Graph",
    "WriterLease",
    "PendingControl",
    "Host capabilities",
    "Lifecycle Hook coverage",
    "Release readiness",
)


class DoctorError(RuntimeError):
    """Deterministic diagnostic input is unsafe or malformed."""


def layer(name: str, status: str, summary: str, **details: Any) -> dict[str, Any]:
    return {"name": name, "status": status, "summary": summary, "details": details}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def release_predicate(report: Mapping[str, Any]) -> bool:
    """Return the single publication predicate for one Doctor report."""
    if not isinstance(report, Mapping):
        return False
    return report.get("healthy") is True and report.get("release_ready") is True


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DoctorError(f"cannot read {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise DoctorError(f"{path} must contain a JSON object")
    return payload


def _is_hex64(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _validate_host_smoke_evidence(smoke: Mapping[str, Any]) -> tuple[bool, bool, str | None]:
    """Validate Host-smoke structure and independently derive completeness."""
    status = smoke.get("status")
    if status not in {"PENDING", "PASS"}:
        return False, False, "Host-smoke status must be PENDING or PASS"
    required = smoke.get("required_probes")
    if not isinstance(required, list):
        return False, False, "Host-smoke required_probes must be an array"
    required_ids: list[str] = []
    for probe in required:
        if not isinstance(probe, Mapping) or not isinstance(probe.get("id"), str):
            return False, False, "Host-smoke required probe is malformed"
        required_ids.append(probe["id"])
    if len(required_ids) != len(set(required_ids)) or set(required_ids) != set(EXPECTED_HOST_PROBES):
        return False, False, "Host-smoke required probes must be exactly H00-H10"

    results = smoke.get("results")
    if not isinstance(results, Mapping):
        return False, False, "Host-smoke results must be an object"
    unknown = set(results) - set(EXPECTED_HOST_PROBES)
    if unknown:
        return False, False, "Host-smoke results contain unsupported probe ids"

    for probe_id, result in results.items():
        if not isinstance(result, Mapping):
            return False, False, f"Host-smoke result {probe_id} must be an object"
        result_status = result.get("status")
        if result_status not in {"PASS", "FAIL"}:
            return False, False, f"Host-smoke result {probe_id} has invalid status"
        evidence_ref = result.get("evidence_ref")
        if result_status == "PASS" and (
            not isinstance(evidence_ref, str) or not evidence_ref.strip()
        ):
            return False, False, f"Host-smoke result {probe_id} PASS requires evidence_ref"
        if probe_id == "H00" and result_status == "PASS":
            if not _is_hex64(result.get("manifest_sha256")):
                return False, False, "Host-smoke H00 PASS requires manifest_sha256"
            if result.get("trusted_current_definition") is not True:
                return False, False, "Host-smoke H00 PASS requires current Hook trust"

    complete = (
        status == "PASS"
        and set(results) == set(EXPECTED_HOST_PROBES)
        and all(
            isinstance(results[probe_id], Mapping)
            and results[probe_id].get("status") == "PASS"
            for probe_id in EXPECTED_HOST_PROBES
        )
    )
    if status == "PASS" and not complete:
        return False, False, "Host-smoke top-level PASS requires PASS evidence for every H00-H10 probe"
    return True, complete, None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose subagents-dispatch V4 health and release readiness.")
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")),
    )
    parser.add_argument("--temp-root", type=Path, default=Path(tempfile.gettempdir()))
    parser.add_argument("--thread-id")
    parser.add_argument("--host-evidence", type=Path)
    parser.add_argument("--runtime-evidence", type=Path)
    parser.add_argument("--live-route", action="store_true")
    parser.add_argument("--calibration-evidence-root", type=Path)
    parser.add_argument("--calibration-campaign", type=Path)
    parser.add_argument("--calibration-host-home-evidence", type=Path)
    parser.add_argument("--calibration-provisioning-task-id")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--release-check", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--legacy", action="store_true")
    parser.add_argument("--repair", action="store_true")
    parser.add_argument("--migrate-legacy", action="store_true")
    parser.add_argument("--cleanup-stale", action="store_true")
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
        print("  Run the installer with --migrate-legacy to reconcile proven-owned legacy state.")
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


def _explicit_actions(args: argparse.Namespace, codex_home: Path) -> list[str]:
    selected = sum(bool(value) for value in (args.repair, args.migrate_legacy, args.cleanup_stale))
    if selected > 1:
        raise DoctorError("explicit lifecycle actions are mutually exclusive")
    actions: list[str] = []
    if args.repair or args.migrate_legacy:
        command = [sys.executable, str(ROOT / "scripts" / "install-agents.py"), "--codex-home", str(codex_home)]
        if args.migrate_legacy:
            command.append("--migrate-legacy")
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise DoctorError("managed-profile lifecycle operation failed")
        actions.append("managed profile migration" if args.migrate_legacy else "managed profile repair")
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
                raise DoctorError(f"--cleanup-stale requires a valid CODEX_THREAD_ID: {exc}") from exc
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
            f"legacy stale cleanup removed {len(report['removed'])} terminal capsule(s); active/corrupt state retained"
        )
    return actions


def diagnose_plugin() -> dict[str, Any]:
    try:
        payload = _read_json(PLUGIN)
    except DoctorError as exc:
        return layer("Plugin", "FAIL", str(exc))
    version = payload.get("version")
    if payload.get("name") != "subagents-dispatch" or not isinstance(version, str) or not version.strip():
        return layer("Plugin", "FAIL", "plugin identity is malformed")
    return layer("Plugin", "OK", "plugin identity is readable", version=version)


def diagnose_skills() -> dict[str, Any]:
    actual = sorted(path.name for path in SKILLS.iterdir() if path.is_dir()) if SKILLS.is_dir() else []
    if actual != sorted(EXPECTED_SKILLS):
        return layer(
            "Public Skills",
            "FAIL",
            "public Skill surface is not the V4 two-entry contract",
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
        return layer("Public Skills", "FAIL", "V4 Skill adapters are incomplete", missing=missing)
    return layer("Public Skills", "OK", "exactly Orchestrate and Doctor are public", count=2)


def diagnose_profiles(codex_home: Path) -> dict[str, Any]:
    try:
        policy = _read_json(POLICY)
        roles = policy["roles"]
    except (DoctorError, KeyError, TypeError) as exc:
        return layer("Fixed execution profiles", "FAIL", f"profile policy is unavailable: {exc}")
    if not isinstance(roles, Mapping) or set(roles) != set(EXPECTED_PROFILES):
        return layer("Fixed execution profiles", "FAIL", "profile role set is invalid")
    mismatches: list[str] = []
    for role, (model, effort) in EXPECTED_PROFILES.items():
        spec = roles.get(role)
        if not isinstance(spec, Mapping) or not isinstance(spec.get("profile_file"), str):
            mismatches.append(role)
            continue
        try:
            profile = tomllib.loads((PROFILE_DIR / str(spec["profile_file"])).read_text(encoding="utf-8"))
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
        return layer("Fixed execution profiles", "FAIL", "fixed model/effort contract differs", mismatches=mismatches)
    verifier = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "install-agents.py"), "--codex-home", str(codex_home), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    installed = verifier.returncode == 0
    return layer(
        "Fixed execution profiles",
        "OK" if installed else "WARN",
        "Luna Max, Terra High, and Sol High contract is exact"
        if installed
        else "bundled fixed profile contract is exact; Codex-home installation is not currently exact",
        installed_exact=installed,
        luna="max",
        terra="high",
        sol="high",
    )


def _state_snapshot(temp_root: Path, thread_id: str | None) -> tuple[str, dict[str, Any] | None, str | None]:
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


def diagnose_state_layers(temp_root: Path, thread_id: str | None) -> list[dict[str, Any]]:
    family, payload, error = _state_snapshot(temp_root, thread_id)
    if family == "unsafe":
        return [
            layer("V4 state", "FAIL", f"state is unsafe or corrupt: {error}"),
            layer("Legacy V3.x state", "UNKNOWN", "state family cannot be classified safely"),
            layer("Work Graph", "UNKNOWN", "state family cannot be classified safely"),
            layer("WriterLease", "UNKNOWN", "state family cannot be classified safely"),
            layer("PendingControl", "UNKNOWN", "state family cannot be classified safely"),
        ]
    if family == "unknown":
        return [
            layer("V4 state", "UNKNOWN", error or "thread identity unavailable"),
            layer("Legacy V3.x state", "UNKNOWN", "thread identity unavailable"),
            layer("Work Graph", "UNKNOWN", "thread identity unavailable"),
            layer("WriterLease", "UNKNOWN", "thread identity unavailable"),
            layer("PendingControl", "UNKNOWN", "thread identity unavailable"),
        ]
    if family == "absent":
        return [
            layer("V4 state", "OK", "thread-scoped state is absent"),
            layer("Legacy V3.x state", "OK", "no legacy V3.x state is present"),
            layer("Work Graph", "OK", "no active Work Graph"),
            layer("WriterLease", "OK", "no active WriterLease"),
            layer("PendingControl", "OK", "no unresolved PendingControl"),
        ]
    if family == "v3":
        assert payload is not None
        unresolved = bool(payload.get("pending_takeover")) or any(
            isinstance(record, Mapping) and record.get("control_state") in legacy_state.ACTIVE_STATES
            for record in payload.get("units", [])
        )
        return [
            layer("V4 state", "OK", "no V4 state is active for this thread"),
            layer(
                "Legacy V3.x state",
                "FAIL" if unresolved else "WARN",
                "unresolved legacy V3.x state blocks V4 execution and will not be silently migrated"
                if unresolved
                else "terminal legacy V3.x state is present and will not be silently migrated",
                unresolved=unresolved,
                v4_execution_allowed=False,
            ),
            layer("Work Graph", "UNKNOWN", "V4 Work Graph unavailable while legacy state exists"),
            layer("WriterLease", "UNKNOWN", "V4 WriterLease unavailable while legacy state exists"),
            layer("PendingControl", "UNKNOWN", "V4 PendingControl unavailable while legacy state exists"),
        ]
    assert family == "v4" and payload is not None
    lease = payload["writer_lease"]
    unresolved_controls = [
        item["control_id"]
        for item in payload["pending_controls"]
        if item["state"] in state_v4.UNRESOLVED_CONTROL_STATES
    ]
    lease_status = "WARN" if lease is not None and lease["state"] == "UNKNOWN" else "OK"
    control_status = "WARN" if unresolved_controls else "OK"
    return [
        layer(
            "V4 state",
            "OK",
            "state v4 validates exactly",
            schema_version=payload["schema_version"],
            state_revision=payload["state_revision"],
            team_plan_revision=payload["team_plan_revision"],
        ),
        layer("Legacy V3.x state", "OK", "active thread is on state v4"),
        layer(
            "Work Graph",
            "OK",
            "compact Work Graph validates",
            work_units=len(payload["work_units"]),
            executions=len(payload["executions"]),
        ),
        layer(
            "WriterLease",
            lease_status,
            "WriterLease invariant validates" if lease_status == "OK" else "WriterLease is quarantined UNKNOWN",
            lease=lease,
        ),
        layer(
            "PendingControl",
            control_status,
            "no unresolved controls" if not unresolved_controls else "unresolved controls remain fail closed",
            unresolved=unresolved_controls,
        ),
    ]


def diagnose_host(host_evidence: Path | None) -> dict[str, Any]:
    if host_evidence is None:
        return layer("Host capabilities", "UNKNOWN", "explicit Host capability evidence was not supplied")
    try:
        payload = json.loads(host_evidence.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return layer("Host capabilities", "FAIL", f"Host evidence is invalid: {exc}")
    if not isinstance(payload, dict):
        return layer("Host capabilities", "FAIL", "Host evidence must be an object")
    if "capabilities" in payload or "plugin_hooks" in payload:
        host = compatibility_core.diagnose_host(host_evidence)
        guard = compatibility_core.diagnose_spawn_guard_runtime(host_evidence)
        severity = {"OK": 0, "UNKNOWN": 1, "WARN": 2, "FAIL": 3}
        status = host["status"] if severity[host["status"]] >= severity[guard["status"]] else guard["status"]
        return layer(
            "Host capabilities",
            status,
            "legacy Host capability/Hook evidence was normalized without satisfying the V4 Host-smoke gate",
            host=host,
            legacy_spawn_guard=guard,
        )
    try:
        snapshot = host_capabilities.normalize_host_capabilities(payload)
    except host_capabilities.HostCapabilityError as exc:
        return layer("Host capabilities", "FAIL", f"Host evidence is invalid: {exc}")
    return layer(
        "Host capabilities",
        "OK" if snapshot["execution_ready"] else "FAIL",
        "required Host capabilities are evidenced"
        if snapshot["execution_ready"]
        else "required Host capabilities are missing",
        **snapshot,
    )


def diagnose_hook_and_release() -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        smoke = _read_json(HOST_SMOKE)
        production = _read_json(HOOKS)
        staged = _read_json(STAGED_HOOKS)
    except DoctorError as exc:
        hook = layer("Lifecycle Hook coverage", "FAIL", str(exc))
        return hook, layer("Release readiness", "UNKNOWN", "Hook state cannot be classified")
    smoke_status = smoke.get("status")
    valid_smoke, smoke_complete, smoke_error = _validate_host_smoke_evidence(smoke)
    production_events = sorted((production.get("hooks") or {}).keys()) if isinstance(production.get("hooks"), Mapping) else []
    staged_events = sorted((staged.get("hooks") or {}).keys()) if isinstance(staged.get("hooks"), Mapping) else []
    if not valid_smoke:
        hook = layer(
            "Lifecycle Hook coverage",
            "FAIL",
            f"Host-smoke evidence is malformed: {smoke_error}",
            smoke_status=smoke_status,
            production_events=production_events,
            staged_events=staged_events,
            activation_manifest="docs/v4/hooks.json",
            required_probes=list(EXPECTED_HOST_PROBES),
        )
        return hook, layer(
            "Release readiness",
            "UNKNOWN",
            "V4.0.0 publication remains blocked by invalid Host-smoke evidence",
            release_ready=False,
            blocking_gate=smoke.get("gate_id"),
        )
    hook = layer(
        "Lifecycle Hook coverage",
        "OK" if smoke_complete else "UNKNOWN",
        "real Host lifecycle Hook coverage is verified"
        if smoke_complete
        else "V4 lifecycle Hooks remain staged pending real Host smoke",
        smoke_status=smoke_status,
        smoke_complete=smoke_complete,
        production_events=production_events,
        staged_events=staged_events,
        activation_manifest="docs/v4/hooks.json",
        required_probes=list(EXPECTED_HOST_PROBES),
    )
    release_ready = smoke_complete and {"PreToolUse", "PostToolUse", "SubagentStop"}.issubset(production_events)
    release = layer(
        "Release readiness",
        "OK" if release_ready else "UNKNOWN",
        "V4.0.0 runtime release gates are satisfied"
        if release_ready
        else "V4.0.0 publication remains blocked by real Host validation",
        release_ready=release_ready,
        blocking_gate=smoke.get("gate_id") if not release_ready else None,
    )
    return hook, release


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


def diagnose(args: argparse.Namespace, codex_home: Path) -> dict[str, Any]:
    thread_id = args.thread_id if args.thread_id is not None else os.environ.get("CODEX_THREAD_ID")
    layers = [diagnose_plugin(), diagnose_skills(), diagnose_profiles(codex_home)]
    layers.extend(diagnose_state_layers(args.temp_root, thread_id))
    layers.append(diagnose_host(args.host_evidence))
    hook, release = diagnose_hook_and_release()
    layers.extend([hook, release])
    by_name = {item["name"]: item for item in layers}
    ordered = [by_name[name] for name in LAYER_ORDER]

    development_layers = compatibility_core.diagnose_runtime(args.runtime_evidence, args.live_route)
    calibration = development_calibration_layer(args, codex_home)
    if calibration is not None:
        development_layers.append(calibration)

    excluded_unknown = {
        "V4 state",
        "Legacy V3.x state",
        "Work Graph",
        "WriterLease",
        "PendingControl",
        "Host capabilities",
        "Lifecycle Hook coverage",
        "Release readiness",
    }
    production_unhealthy = any(
        item["status"] in {"WARN", "FAIL"}
        or (item["status"] == "UNKNOWN" and item["name"] not in excluded_unknown)
        for item in ordered
    )
    development_fail = any(item["status"] == "FAIL" for item in development_layers)
    live_required_unverified = args.live_route and any(
        item.get("details", {}).get("required") is True and item.get("status") != "OK"
        for item in development_layers
    )
    healthy = not production_unhealthy and not development_fail and not live_required_unverified
    release_candidate = bool(by_name["Release readiness"]["details"].get("release_ready"))
    report = {
        "schema_version": 4,
        "healthy": healthy,
        "release_ready": release_candidate,
        "layers": ordered,
        "development_layers": development_layers,
    }
    report["release_ready"] = release_predicate(report)
    return report


def render_text(report: Mapping[str, Any], actions: list[str]) -> str:
    lines = [
        "Subagents Dispatch Doctor",
        "Mode: V4 deterministic diagnostics; read-only unless an explicit lifecycle action was requested",
        "",
    ]
    layers = report.get("layers", [])
    for item in layers:
        lines.append(f"[{item['status']}] {item['name']}: {item['summary']}")
    development = report.get("development_layers", [])
    if development:
        lines.extend(["", "Development checks"])
        for item in development:
            lines.append(f"[{item['status']}] {item['name']}: {item['summary']}")
    if actions:
        lines.extend(["", "Actions applied"])
        lines.extend(f"[OK] {action}" for action in actions)
    all_layers = list(layers) + list(development)
    failures = sum(item.get("status") == "FAIL" for item in all_layers)
    if failures:
        verdict = "UNHEALTHY"
    elif report.get("healthy") is True:
        verdict = "HEALTHY"
    else:
        verdict = "ATTENTION"
    lines.extend(
        [
            "",
            f"Overall: {verdict}",
            f"Release readiness: {'READY' if report.get('release_ready') else 'BLOCKED'}",
        ]
    )
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

    if args.check and not report["healthy"]:
        raise SystemExit(1)
    if args.release_check and not release_predicate(report):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
