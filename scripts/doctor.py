#!/usr/bin/env python3
"""Deterministic Doctor for the subagents-dispatch Plugin."""

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

import dispatch_state_v4 as state_v4
import host_capabilities
import package_integrity
import policy as policy_contract


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / ".codex-plugin" / "plugin.json"
PROFILE_DIR = ROOT / "agent-profiles"
SKILLS = ROOT / "skills"
EXPECTED_SKILLS = ("orchestrate", "doctor")
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


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DoctorError(f"cannot read {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise DoctorError(f"{path} must contain a JSON object")
    return payload


def _profile_disables_child_collaboration(profile: Mapping[str, Any]) -> bool:
    instructions = str(profile.get("developer_instructions", "")).lower()
    return (
        profile.get("agents", {}).get("enabled") is False
        and profile.get("features", {}).get("multi_agent_v2") is False
        and "create further subagents" in instructions
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check subagents-dispatch health and safe maintenance options."
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
    parser.add_argument("--repair", action="store_true")
    parser.add_argument("--uninstall-managed", action="store_true")
    return parser.parse_args()


def _validate_thread_input(thread_id: str | None) -> None:
    if thread_id is not None and not thread_id.strip():
        raise DoctorError("explicit --thread-id must be non-empty")


def _run_owned_action(command: list[str], *, label: str) -> None:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise DoctorError(f"{label} failed{': ' + detail if detail else ''}")


def _explicit_actions(args: argparse.Namespace, codex_home: Path) -> list[str]:
    if args.repair and args.uninstall_managed:
        raise DoctorError("explicit Doctor maintenance actions are mutually exclusive")
    actions: list[str] = []
    if args.repair:
        _run_owned_action(
            [
                sys.executable,
                str(ROOT / "scripts" / "install-agents.py"),
                "--codex-home",
                str(codex_home),
            ],
            label="managed profile repair",
        )
        actions.append("Managed Agent profiles repaired")
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
        actions.append("Managed Agent profiles removed")
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
        return layer("Plugin package", "FAIL", "Plugin package is invalid")
    actual = sorted(path.name for path in SKILLS.iterdir() if path.is_dir()) if SKILLS.is_dir() else []
    if actual != sorted(EXPECTED_SKILLS):
        return layer(
            "Plugin package",
            "FAIL",
            "Public skills are incomplete or unexpected",
            expected=list(EXPECTED_SKILLS),
            actual=actual,
        )
    return layer(
        "Plugin package",
        "OK",
        "Plugin files and public skills are valid",
        version=version,
        skills=list(EXPECTED_SKILLS),
    )


def diagnose_managed_agents(codex_home: Path) -> dict[str, Any]:
    try:
        profiles = policy_contract.profile_contracts()
    except RuntimeError as exc:
        return layer("Managed Agents", "FAIL", f"Managed Agent configuration is unavailable: {exc}")
    mismatches: list[str] = []
    for role, spec in profiles.items():
        try:
            profile = tomllib.loads(
                (PROFILE_DIR / spec["profile_file"]).read_text(encoding="utf-8")
            )
        except (OSError, UnicodeError, tomllib.TOMLDecodeError):
            mismatches.append(role)
            continue
        if (
            profile.get("model") != spec["model"]
            or profile.get("model_reasoning_effort") != spec["effort"]
            or not _profile_disables_child_collaboration(profile)
        ):
            mismatches.append(role)
    if mismatches:
        return layer(
            "Managed Agents",
            "FAIL",
            "Managed Agent profiles do not match this Plugin version",
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
            "All 5 managed Agent profiles are installed and match this Plugin version",
            profiles=5,
        )
    diagnostic = (verifier.stderr or verifier.stdout).strip()
    recoverable = any(diagnostic.startswith(prefix) for prefix in RECOVERABLE_PROFILE_CHECK_PREFIXES)
    if recoverable:
        return layer(
            "Managed Agents",
            "WARN",
            "Managed Agent profiles need setup or repair",
            action="Run Doctor repair. Start a fresh Codex session if profiles change.",
            diagnostic=diagnostic,
            profiles=5,
        )
    return layer(
        "Managed Agents",
        "FAIL",
        "Managed Agent profiles cannot be changed safely",
        action="Resolve the reported file ownership or filesystem conflict, then run Doctor repair.",
        diagnostic=diagnostic,
        profiles=5,
    )


def diagnose_host_integration(host_evidence: Path | None) -> dict[str, Any]:
    if host_evidence is None:
        return layer(
            "Host integration",
            "UNKNOWN",
            "Current Host capabilities were not checked",
            action="Provide current Host capability evidence when delegated execution must be verified.",
        )
    try:
        evidence = _read_json(host_evidence)
        normalized = host_capabilities.normalize_host_capabilities(evidence)
    except (DoctorError, host_capabilities.HostCapabilityError) as exc:
        return layer("Host integration", "FAIL", f"Host capability data is invalid: {exc}")
    if normalized["execution_ready"] is not True:
        return layer(
            "Host integration",
            "FAIL",
            "Required Native Subagent capabilities are unavailable",
            missing=normalized["missing"],
        )
    return layer(
        "Host integration",
        "OK",
        "Native Subagent capabilities are ready",
        capabilities=normalized["capabilities"],
        fork_turns_none=normalized["fork_turns_none"],
        max_concurrent_threads_per_session=normalized["max_concurrent_threads_per_session"],
        capacity_includes_primary=normalized["capacity_includes_primary"],
    )


def diagnose_orchestration_state(thread_id: str | None, temp_root: Path) -> dict[str, Any]:
    if thread_id is None:
        return layer(
            "Orchestration state",
            "UNKNOWN",
            "No active task was selected for state inspection",
        )
    try:
        current = state_v4.load_state(thread_id, temp_root=temp_root)
    except (state_v4.StateError, ValueError) as exc:
        return layer("Orchestration state", "FAIL", f"Current orchestration state is invalid: {exc}")
    if current is None:
        return layer("Orchestration state", "OK", "No active orchestration state")
    active = [
        item["execution_id"]
        for item in current["executions"]
        if item["lifecycle"] in {"SPAWN_PENDING", "RUNNING", "UNKNOWN"}
    ]
    lease = current.get("writer_lease")
    return layer(
        "Orchestration state",
        "OK",
        "Current orchestration state is healthy",
        state_revision=current["state_revision"],
        active_executions=active,
        writer_state=lease.get("state") if isinstance(lease, Mapping) else None,
    )


def run_diagnosis(args: argparse.Namespace) -> dict[str, Any]:
    _validate_thread_input(args.thread_id)
    actions = _explicit_actions(args, args.codex_home)
    layers = [
        diagnose_plugin_package(),
        diagnose_managed_agents(args.codex_home),
        diagnose_host_integration(args.host_evidence),
        diagnose_orchestration_state(args.thread_id, args.temp_root),
    ]
    return {"layers": layers, "actions": actions}


def _print_report(report: Mapping[str, Any]) -> None:
    for item in report["layers"]:
        print(f"[{item['status']}] {item['name']}: {item['summary']}")
        if item.get("action"):
            print(f"  Action: {item['action']}")
    for action in report.get("actions", []):
        print(f"[OK] Action: {action}")


def main() -> None:
    args = parse_args()
    integrity = package_integrity.verify_package(ROOT, profile="full")
    if integrity.get("ok") is not True:
        message = package_integrity._format_result(integrity)
        if args.json:
            print(json.dumps({"integrity": integrity}, ensure_ascii=False, sort_keys=True))
        else:
            print(message, file=sys.stderr)
        raise SystemExit(1)
    try:
        report = run_diagnosis(args)
    except (DoctorError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    else:
        _print_report(report)
    if args.check and any(item["status"] == "FAIL" for item in report["layers"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
