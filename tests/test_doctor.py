from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
DOCTOR = ROOT / "scripts" / "doctor.py"
INSTALLER = ROOT / "scripts" / "install-agents.py"
SCRIPTS = ROOT / "scripts"
THREAD = "doctor-v4-thread"


def load_module(name: str, filename: str):
    scripts = str(SCRIPTS)
    sys.path.insert(0, scripts)
    try:
        spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts)


def install(home: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(INSTALLER), "--codex-home", str(home)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def run_doctor(home: Path, temp_root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(DOCTOR),
            "--codex-home",
            str(home),
            "--temp-root",
            str(temp_root),
            "--thread-id",
            THREAD,
            *extra,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "SUBAGENTS_DISPATCH_CODEX_BIN": "subagents-dispatch-test-codex-unavailable"},
    )


def test_doctor_reports_product_layers_and_keeps_pre_cutover_hook_gap_degraded(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    result = run_doctor(home, tmp_path, "--check")
    assert result.returncode == 0, result.stdout + result.stderr
    order = [
        "Plugin package",
        "Managed Agents",
        "Host integration",
        "Orchestration state",
        "Legacy compatibility",
    ]
    positions = [result.stdout.index(f"] {name}:") for name in order]
    assert positions == sorted(positions)
    assert "[UNKNOWN] Plugin package:" in result.stdout
    assert "[OK] Managed Agents: 5/5 managed Agent profiles are installed exactly" in result.stdout
    assert "[WARN] Host integration:" in result.stdout
    assert "[OK] Orchestration state: no thread-scoped orchestration state is active" in result.stdout
    assert "Overall: DEGRADED" in result.stdout


def test_doctor_json_contains_only_product_health_contract(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    result = run_doctor(home, tmp_path, "--json", "--check")
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == 5
    assert payload["healthy"] is True
    assert payload["status"] == "DEGRADED"
    assert [item["name"] for item in payload["layers"]] == [
        "Plugin package",
        "Managed Agents",
        "Host integration",
        "Orchestration state",
        "Legacy compatibility",
    ]
    assert "release_ready" not in payload
    assert "development_layers" not in payload


def test_valid_v4_state_is_diagnosed_without_legacy_migration(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    state = load_module("doctor_v4_state", "dispatch_state_v4.py")
    state.write_state(state.new_state(thread_id=THREAD), temp_root=tmp_path)
    result = run_doctor(home, tmp_path, "--check")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "[OK] Orchestration state: thread-scoped V4 orchestration state validates" in result.stdout
    assert "[OK] Legacy compatibility: active thread uses V4 state;" in result.stdout


def test_unresolved_v3_state_blocks_plugin_health_and_is_not_silently_migrated(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    legacy = load_module("doctor_legacy_state", "dispatch_state.py")
    payload = legacy.new_state(thread_id=THREAD)
    payload["units"].append(
        {
            "unit_id": "U1",
            "task_id": "task-1",
            "attempt": 1,
            "native_task_name": "sd_u1_a1_execute",
            "agent_id": None,
            "role": "worker",
            "model_lane": "Luna Max",
            "responsibility": {"outcome": "bounded change", "acceptance": "focused test passes"},
            "authority": {"write_scope": ["owned.py"]},
            "writer": True,
            "control_state": "SPAWN_PENDING",
            "adopted": False,
            "accepted": False,
            "failure_origin": "none",
            "blocker": "none",
            "quarantine_reason": None,
        }
    )
    legacy.write_state(payload, temp_root=tmp_path)
    result = run_doctor(home, tmp_path, "--check")
    assert result.returncode != 0
    assert "[FAIL] Orchestration state: unresolved legacy orchestration state blocks managed execution" in result.stdout
    assert "[FAIL] Legacy compatibility: legacy orchestration state will not be silently migrated" in result.stdout
    assert "Overall: BLOCKED" in result.stdout


def test_corrupt_state_fails_closed_without_traceback(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    legacy = load_module("doctor_corrupt_path", "dispatch_state.py")
    path = legacy.state_path(THREAD, temp_root=tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{broken", encoding="utf-8")
    result = run_doctor(home, tmp_path, "--check")
    assert result.returncode != 0
    assert "[FAIL] Orchestration state: thread state is unsafe or corrupt" in result.stdout
    assert "Overall: BLOCKED" in result.stdout
    assert "Traceback" not in result.stdout + result.stderr


def test_cleanup_stale_rejects_explicit_blank_thread_identity_safely(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    result = subprocess.run(
        [
            sys.executable,
            str(DOCTOR),
            "--codex-home",
            str(home),
            "--temp-root",
            str(tmp_path),
            "--thread-id",
            "",
            "--cleanup-stale",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "valid CODEX_THREAD_ID" in result.stderr
    assert "Traceback" not in result.stderr


def test_legacy_flag_remains_managed_profile_migration_diagnostic(tmp_path: Path):
    result = subprocess.run(
        [sys.executable, str(DOCTOR), "--codex-home", str(tmp_path / "codex-home"), "--legacy"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Legacy Migration Diagnostics" in result.stdout
    assert "State:" in result.stdout


def test_doctor_can_explicitly_uninstall_only_owned_managed_profiles(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    result = run_doctor(home, tmp_path, "--uninstall-managed")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "[OK] owned managed Agent profiles removed" in result.stdout
    assert "[WARN] Managed Agents:" in result.stdout

    verifier = subprocess.run(
        [sys.executable, str(INSTALLER), "--codex-home", str(home), "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert verifier.returncode != 0
