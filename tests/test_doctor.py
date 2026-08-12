from __future__ import annotations

import json
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DOCTOR = ROOT / "scripts" / "doctor.py"
INSTALLER = ROOT / "scripts" / "install-agents.py"


def run_doctor(home: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env is not None:
        merged.update(env)
    return subprocess.run(
        [sys.executable, str(DOCTOR), "--codex-home", str(home), *args],
        cwd=ROOT,
        env=merged,
        text=True,
        capture_output=True,
        check=False,
    )


def install(home: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(INSTALLER), "--codex-home", str(home)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def load_doctor_module():
    scripts = str(ROOT / "scripts")
    sys.path.insert(0, scripts)
    try:
        spec = importlib.util.spec_from_file_location("doctor_under_test", DOCTOR)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts)


def test_doctor_reports_independent_assurance_layers_and_unobserved_runtime_is_not_unhealthy(
    tmp_path: Path,
):
    home = tmp_path / "codex-home"
    install(home)
    result = run_doctor(home, "--check", env={"CODEX_THREAD_ID": "doctor-test"})

    assert result.returncode == 0, result.stdout + result.stderr
    output = result.stdout
    labels = [
        "Plugin",
        "Skills",
        "Managed Agent profiles",
        "Dispatch state",
        "Codex Host",
        "Runtime route",
        "Effective permission state",
        "Permission-source provenance",
    ]
    layer_lines = [line for line in output.splitlines() if line.startswith("Layer:")]
    assert len(layer_lines) == len(labels)
    for line, label in zip(layer_lines, labels):
        assert line.startswith(f"Layer: {label}:")
    assert "Layer: Codex Host: UNKNOWN" in output
    assert "Layer: Runtime route: UNKNOWN" in output
    assert "Layer: Effective permission state: UNKNOWN" in output
    assert "Layer: Permission-source provenance: UNKNOWN" in output
    assert "not run" in output

    temp_root = tmp_path / "temp"
    temp_root.mkdir()
    json_result = run_doctor(
        home,
        "--check",
        "--json",
        "--temp-root",
        str(temp_root),
        env={"CODEX_THREAD_ID": "doctor-test"},
    )
    assert json_result.returncode == 0, json_result.stdout + json_result.stderr
    report = json.loads(json_result.stdout)
    profiles = next(layer for layer in report["layers"] if layer["name"] == "Managed Agent profiles")
    state = next(layer for layer in report["layers"] if layer["name"] == "Dispatch state")
    assert profiles["details"]["legacy_status"] == "migration_complete"
    assert state["details"]["state_lock_health"] == "not_present"
    assert state["details"]["schema_health"] == "ok"
    assert state["details"]["unexpected_repository_state"] == []


def test_doctor_calibration_readiness_uses_profile_only_checker(tmp_path: Path):
    home = tmp_path / ".codex"
    (home / "agents").mkdir(parents=True)
    (home / "config.toml").write_text('model="keep"\n')
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    initialized = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "calibration_profiles.py"), "init",
         "--evaluator-root", str(evidence)], cwd=ROOT, text=True, capture_output=True,
    )
    assert initialized.returncode == 0, initialized.stderr
    sys.path.insert(0, str(ROOT / "tests"))
    try:
        from test_calibration_profiles import campaign, run
        campaign_path = campaign(evidence)
        assert run(evidence, home, campaign_path, "create").returncode == 0
    finally:
        sys.path.pop(0)
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_git = fake_bin / "git"
    fake_git.write_text("#!/bin/sh\nprintf ' M controlled-test-change\\n'\n")
    fake_git.chmod(0o755)
    result = run_doctor(
        home, "--json", "--calibration-evidence-root", str(evidence),
        "--calibration-campaign", str(campaign_path),
        env={"PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}"},
    )
    assert result.returncode == 0, result.stderr
    layer = next(item for item in json.loads(result.stdout)["layers"] if item["name"] == "Calibration readiness")
    assert layer["status"] == "FAIL"
    assert layer["details"]["repository_clean"] is False
    assert layer["details"]["shared_config_mutations"] == 0
    assert layer["details"]["exact_calibration_profiles"] == 2


def test_doctor_detects_all_forbidden_repository_local_state_names(tmp_path: Path):
    module = load_doctor_module()
    forbidden = [
        "subagents-dispatch/thread-1/active.json",
        "team-plan-orphan.json",
        "nested/ledger-old.json",
        "nested/receipt-final.md",
        "recovery-stale.json",
    ]
    for relative in forbidden:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
    ignored = tmp_path / ".venv" / "receipt-ignored.json"
    ignored.parent.mkdir()
    ignored.write_text("{}", encoding="utf-8")

    assert module._unexpected_repository_state(tmp_path) == sorted(forbidden)


def test_doctor_cleanup_rejects_explicit_empty_thread_identity(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    result = run_doctor(
        home,
        "--cleanup-stale",
        "--thread-id",
        "",
        "--temp-root",
        str(tmp_path / "temp"),
        env={"CODEX_THREAD_ID": "environment-thread"},
    )
    assert result.returncode != 0
    assert "valid CODEX_THREAD_ID" in result.stderr


def test_doctor_explicit_runtime_evidence_keeps_configured_and_observed_distinct(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    evidence = tmp_path / "runtime.json"
    evidence.write_text(
        json.dumps(
            {
                "subject": "main_session",
                "requested": {"model": "gpt-5.6-sol", "effort": "high"},
                "accepted": {"model": "gpt-5.6-sol", "effort": "high"},
            }
        ),
        encoding="utf-8",
    )
    result = run_doctor(home, "--check", "--runtime-evidence", str(evidence))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Layer: Runtime route: UNKNOWN" in result.stdout
    assert "runtime route is not exposed by current Host evidence" in result.stdout


def test_doctor_accepts_agreeing_native_and_local_route_evidence(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    evidence = tmp_path / "runtime.json"
    route = {
        "thread_id": "11111111-1111-7111-8111-111111111111",
        "parent_thread_id": "22222222-2222-7222-8222-222222222222",
        "agent_role": "subagents_dispatch_worker",
        "model": "gpt-5.6-luna",
        "effort": "max",
        "sandbox_policy_type": "workspace-write",
        "permission_profile_type": "default",
    }
    evidence.write_text(
        json.dumps(
            {
                "subject": "child",
                "expected": {
                    **route,
                    "runtime_observation_required": True,
                    "requires_enforced_read_only": False,
                },
                "native": route,
                "local": route,
            }
        ),
        encoding="utf-8",
    )

    result = run_doctor(home, "--check", "--runtime-evidence", str(evidence))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Layer: Runtime route: OK" in result.stdout
    assert "Layer: Effective permission state: OK" in result.stdout
    assert "Layer: Permission-source provenance: UNKNOWN" in result.stdout


def test_doctor_preserves_corrupt_dispatch_state(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    state_file = tmp_path / "temp" / "subagents-dispatch" / "thread-corrupt" / "active.json"
    state_file.parent.mkdir(parents=True)
    state_file.write_text("{broken", encoding="utf-8")
    state_file.chmod(0o600)

    result = run_doctor(
        home,
        "--check",
        "--temp-root",
        str(tmp_path / "temp"),
        env={"CODEX_THREAD_ID": "thread-corrupt"},
    )

    assert result.returncode != 0
    assert "Layer: Dispatch state: FAIL" in result.stdout
    assert "corrupt" in result.stdout.lower()
    assert state_file.read_text(encoding="utf-8") == "{broken"


def test_doctor_without_thread_id_does_not_create_dispatch_state(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    temp_root = tmp_path / "temp"
    temp_root.mkdir()
    result = run_doctor(home, "--check", "--temp-root", str(temp_root), env={"CODEX_THREAD_ID": ""})

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Layer: Dispatch state: UNKNOWN" in result.stdout
    assert "CODEX_THREAD_ID" in result.stdout
    assert not (temp_root / "subagents-dispatch").exists()


def test_doctor_reports_pending_takeover_as_unresolved_orchestration(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    temp_root = tmp_path / "temp"
    state_dir = temp_root / "subagents-dispatch" / "thread-pending"
    state_dir.mkdir(parents=True)
    state = {
        "schema_version": "1.0",
        "root_thread_id": "thread-pending",
        "locale": "en",
        "created_at": "2026-08-10T00:00:00Z",
        "updated_at": "2026-08-10T00:00:00Z",
        "team_plan_revision": None,
        "units": [
            {
                "unit_id": "U1",
                "task_id": "task-1",
                "attempt": 1,
                "native_task_name": "sd-u1-a1-execute",
                "agent_id": "agent-1",
                "role": "worker",
                "model_lane": "Luna Max",
                "responsibility": {"outcome": "finish bounded work", "acceptance": "Main accepts result"},
                "authority": {"write_scope": ["owned.py"]},
                "writer": True,
                "control_state": "RUNNING",
                "adopted": False,
                "accepted": False,
                "failure_origin": "none",
                "blocker": "none",
                "quarantine_reason": None,
            }
        ],
        "accounting_refs": [],
        "controls": [],
        "pending_takeover": {"unit_id": "U1", "status": "pending"},
    }
    state_file = state_dir / "active.json"
    state_file.write_text(json.dumps(state), encoding="utf-8")
    state_file.chmod(0o600)
    (state_dir / "active.lock").touch(mode=0o600)

    result = run_doctor(
        home,
        "--check",
        "--json",
        "--temp-root",
        str(temp_root),
        env={"CODEX_THREAD_ID": "thread-pending"},
    )
    report = json.loads(result.stdout)
    layer = next(item for item in report["layers"] if item["name"] == "Dispatch state")
    assert layer["status"] == "WARN"
    assert layer["details"]["active_orchestration"] is True
    assert layer["details"]["pending_takeovers"] == ["thread-pending"]


def test_doctor_scans_existing_state_without_thread_id(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    temp_root = tmp_path / "temp"
    state_dir = temp_root / "subagents-dispatch" / "other-thread"
    state_dir.mkdir(parents=True)
    state = {
        "schema_version": "1.0",
        "root_thread_id": "other-thread",
        "locale": "en",
        "created_at": "2026-07-01T00:00:00Z",
        "updated_at": "2026-07-01T00:00:00Z",
        "team_plan_revision": None,
        "units": [],
        "accounting_refs": [],
        "controls": [],
        "pending_takeover": None,
    }
    state_file = state_dir / "active.json"
    state_file.write_text(json.dumps(state), encoding="utf-8")
    state_file.chmod(0o600)
    lock_file = state_dir / "active.lock"
    lock_file.touch(mode=0o600)

    result = run_doctor(
        home,
        "--check",
        "--json",
        "--temp-root",
        str(temp_root),
        env={"CODEX_THREAD_ID": ""},
    )
    report = json.loads(result.stdout)
    layer = next(item for item in report["layers"] if item["name"] == "Dispatch state")

    assert layer["status"] == "WARN"
    assert layer["details"]["current_thread"] is None
    assert layer["details"]["stale_count"] == 1
