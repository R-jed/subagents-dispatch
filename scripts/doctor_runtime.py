#!/usr/bin/env python3
"""V4 deterministic Doctor runtime.

Package integrity is verified by scripts/doctor.py before this module runs.
Diagnosis is read-only unless an explicit lifecycle action is requested.
"""

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


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / ".codex-plugin" / "plugin.json"
POLICY = ROOT / "contracts" / "policy.json"
HOOKS = ROOT / "hooks" / "hooks.json"
STAGED_HOOKS = ROOT / "docs" / "v4" / "hooks.json"
HOST_SMOKE = ROOT / "docs" / "v4" / "host-smoke.json"
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


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DoctorError(f"cannot read {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(payload, dict):
        raise DoctorError(f"{path.relative_to(ROOT)} must contain a JSON object")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose subagents-dispatch V4 health.")
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")),
    )
    parser.add_argument("--temp-root", type=Path, default=Path(tempfile.gettempdir()))
    parser.add_argument("--thread-id")
    parser.add_argument("--host-evidence", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--release-check", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--legacy", action="store_true")
    parser.add_argument("--repair", action="store_true")
    parser.add_argument("--migrate-legacy", action="store_true")
    parser.add_argument("--cleanup-stale", action="store_true")
    return parser.parse_args()


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
        thread_id = args.thread_id or os.environ.get("CODEX_THREAD_ID")
        if thread_id is None:
            raise DoctorError("--cleanup-stale requires an explicit thread identity")
        report = legacy_state.cleanup_stale_states(temp_root=args.temp_root, active_thread_id=thread_id)
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
    missing: list[str] = []
    for skill_id in EXPECTED_SKILLS:
        root = SKILLS / skill_id
        if not (root / "SKILL.md").is_file() or not (root / "agents" / "openai.yaml").is_file():
            missing.append(skill_id)
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
        if not isinstance(spec, Mapping):
            mismatches.append(role)
            continue
        profile_file = spec.get("profile_file")
        if not isinstance(profile_file, str):
            mismatches.append(role)
            continue
        try:
            profile = tomllib.loads((PROFILE_DIR / profile_file).read_text(encoding="utf-8"))
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
        else "bundled profile contract is exact; Codex-home installation is not currently exact",
        installed_exact=installed,
        luna="max",
        terra="high",
        sol="high",
    )


def _state_snapshot(temp_root: Path, thread_id: str | None) -> tuple[str, dict[str, Any] | None, str | None]:
    if thread_id is None or not thread_id.strip():
        return "unknown", None, "thread identity unavailable"
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
        fail = layer("V4 state", "FAIL", f"state is unsafe or corrupt: {error}")
        return [
            fail,
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
                "WARN",
                "legacy V3.x state is present and will not be silently migrated",
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
        evidence = json.loads(host_evidence.read_text(encoding="utf-8"))
        snapshot = host_capabilities.normalize_host_capabilities(evidence)
    except (OSError, UnicodeError, json.JSONDecodeError, host_capabilities.HostCapabilityError) as exc:
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
    production_events = sorted((production.get("hooks") or {}).keys()) if isinstance(production.get("hooks"), Mapping) else []
    staged_events = sorted((staged.get("hooks") or {}).keys()) if isinstance(staged.get("hooks"), Mapping) else []
    hook_status = "OK" if smoke_status == "PASS" else "UNKNOWN"
    hook = layer(
        "Lifecycle Hook coverage",
        hook_status,
        "real Host lifecycle Hook coverage is verified"
        if smoke_status == "PASS"
        else "V4 lifecycle Hooks remain staged pending real Host smoke",
        smoke_status=smoke_status,
        production_events=production_events,
        staged_events=staged_events,
        activation_manifest="docs/v4/hooks.json",
    )
    release_ready = smoke_status == "PASS" and {"PreToolUse", "PostToolUse", "SubagentStop"}.issubset(production_events)
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


def diagnose(args: argparse.Namespace, codex_home: Path) -> dict[str, Any]:
    thread_id = args.thread_id or os.environ.get("CODEX_THREAD_ID")
    layers = [diagnose_plugin(), diagnose_skills(), diagnose_profiles(codex_home)]
    layers.extend(diagnose_state_layers(args.temp_root, thread_id))
    layers.append(diagnose_host(args.host_evidence))
    hook, release = diagnose_hook_and_release()
    layers.extend([hook, release])
    by_name = {item["name"]: item for item in layers}
    ordered = [by_name[name] for name in LAYER_ORDER]
    healthy = not any(item["status"] == "FAIL" for item in ordered)
    release_ready = bool(by_name["Release readiness"]["details"].get("release_ready"))
    return {
        "schema_version": 4,
        "healthy": healthy,
        "release_ready": release_ready,
        "layers": ordered,
    }


def render_text(report: Mapping[str, Any], actions: list[str]) -> str:
    lines = [
        "Subagents Dispatch Doctor",
        "Mode: V4 deterministic diagnostics; read-only unless an explicit lifecycle action was requested",
        "",
    ]
    for item in report["layers"]:
        lines.append(f"[{item['status']}] {item['name']}: {item['summary']}")
    if actions:
        lines.append("")
        lines.append("Actions: " + "; ".join(actions))
    lines.extend(
        [
            "",
            f"Health: {'HEALTHY' if report['healthy'] else 'UNHEALTHY'}",
            f"Release readiness: {'READY' if report['release_ready'] else 'BLOCKED'}",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    codex_home = args.codex_home.expanduser()
    if codex_home.is_symlink():
        raise SystemExit("ERROR: refusing symlinked Codex home")
    codex_home = codex_home.resolve()
    try:
        actions = _explicit_actions(args, codex_home)
        report = diagnose(args, codex_home)
    except DoctorError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from None

    if args.legacy:
        selected = next(item for item in report["layers"] if item["name"] == "Legacy V3.x state")
        if args.json:
            print(json.dumps(selected, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        else:
            print(f"[{selected['status']}] {selected['name']}: {selected['summary']}")
    elif args.json:
        output = dict(report)
        output["actions"] = actions
        print(json.dumps(output, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    else:
        print(render_text(report, actions))

    if args.check and not report["healthy"]:
        raise SystemExit(1)
    if args.release_check and not report["release_ready"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
