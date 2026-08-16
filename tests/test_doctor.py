from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DOCTOR = ROOT / "scripts" / "doctor.py"
DOCTOR_CORE = ROOT / "scripts" / "doctor_core.py"
INSTALLER = ROOT / "scripts" / "install-agents.py"
PRODUCTION_LAYERS = [
    "Plugin",
    "Plugin installation",
    "Skills",
    "Spawn guard package",
    "Managed Agent profiles",
    "Dispatch state",
    "Codex Host",
    "Spawn guard runtime",
    "Runtime route",
    "Effective permission state",
    "Permission-source provenance",
]


def run_doctor(
    home: Path,
    *args: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
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


def load_core():
    scripts = str(ROOT / "scripts")
    sys.path.insert(0, scripts)
    try:
        spec = importlib.util.spec_from_file_location("doctor_core_under_test", DOCTOR_CORE)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts)


def host_evidence(path: Path, *rows: dict) -> Path:
    path.write_text(
        json.dumps({"capabilities": ["hooks", "multi_agent"], "plugin_hooks": list(rows)}),
        encoding="utf-8",
    )
    return path


def hook_row(**overrides) -> dict:
    row = {
        "plugin": "subagents-dispatch",
        "event": "PreToolUse",
        "source": "plugin",
        "handler_type": "command",
        "execution_mode": "sync",
        "trust_status": "trusted",
        "enabled": True,
    }
    row.update(overrides)
    return row


def test_doctor_reports_eleven_production_layers_and_unknown_runtime_is_supported(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    result = run_doctor(home, "--check", env={"CODEX_THREAD_ID": "doctor-test"})

    assert result.returncode == 0, result.stdout + result.stderr
    status_lines = [
        line
        for line in result.stdout.splitlines()
        if line.startswith(("[OK]", "[WARN]", "[FAIL]", "[UNKNOWN]"))
    ]
    assert len(status_lines) == len(PRODUCTION_LAYERS)
    for line, label in zip(status_lines, PRODUCTION_LAYERS):
        assert f"] {label}:" in line
    assert "[UNKNOWN] Plugin installation:" in result.stdout
    assert "[OK] Spawn guard package:" in result.stdout
    assert "[UNKNOWN] Codex Host:" in result.stdout
    assert "[UNKNOWN] Spawn guard runtime:" in result.stdout
    assert "[UNKNOWN] Runtime route:" in result.stdout
    assert "Overall: HEALTHY" in result.stdout

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
    assert report["schema_version"] == 3
    assert [item["name"] for item in report["layers"]] == PRODUCTION_LAYERS
    profiles = next(item for item in report["layers"] if item["name"] == "Managed Agent profiles")
    state = next(item for item in report["layers"] if item["name"] == "Dispatch state")
    guard = next(item for item in report["layers"] if item["name"] == "Spawn guard package")
    installation = next(item for item in report["layers"] if item["name"] == "Plugin installation")
    assert profiles["details"]["legacy_status"] == "migration_complete"
    assert state["details"]["state_lock_health"] == "not_present"
    assert state["details"]["schema_health"] == "ok"
    assert state["details"]["unexpected_repository_state"] == []
    assert guard["details"]["discovery_path"] == "hooks/hooks.json"
    assert guard["details"]["mutation"] is False
    assert installation["status"] == "UNKNOWN"
    assert installation["details"]["observed"] is False


def test_doctor_hook_runtime_uses_explicit_host_truth(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)

    trusted = host_evidence(tmp_path / "trusted.json", hook_row())
    result = run_doctor(
        home,
        "--check",
        "--host-evidence",
        str(trusted),
        env={"CODEX_THREAD_ID": "doctor-hook"},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "[OK] Spawn guard runtime:" in result.stdout

    untrusted = host_evidence(
        tmp_path / "untrusted.json",
        hook_row(trust_status="untrusted", enabled=False),
    )
    result = run_doctor(
        home,
        "--check",
        "--host-evidence",
        str(untrusted),
        env={"CODEX_THREAD_ID": "doctor-hook"},
    )
    assert result.returncode != 0
    assert "[WARN] Spawn guard runtime:" in result.stdout
    assert "Action:" in result.stdout

    duplicate = host_evidence(tmp_path / "duplicate.json", hook_row(), hook_row())
    result = run_doctor(
        home,
        "--check",
        "--host-evidence",
        str(duplicate),
        env={"CODEX_THREAD_ID": "doctor-hook"},
    )
    assert result.returncode != 0
    assert "[FAIL] Spawn guard runtime:" in result.stdout


def test_doctor_modified_or_wrong_mode_hook_fails_closed(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    for name, row in {
        "modified": hook_row(trust_status="modified"),
        "async": hook_row(execution_mode="async"),
        "user": hook_row(source="user"),
    }.items():
        evidence = host_evidence(tmp_path / f"{name}.json", row)
        result = run_doctor(
            home,
            "--check",
            "--host-evidence",
            str(evidence),
            env={"CODEX_THREAD_ID": "doctor-hook"},
        )
        assert result.returncode != 0
        assert "[FAIL] Spawn guard runtime:" in result.stdout


def test_calibration_readiness_remains_outside_production_layers(tmp_path: Path):
    home = tmp_path / ".codex"
    (home / "agents").mkdir(parents=True)
    (home / "config.toml").write_text('model="keep"\n', encoding="utf-8")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    initialized = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "calibration_profiles.py"),
            "init",
            "--evaluator-root",
            str(evidence),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert initialized.returncode == 0, initialized.stderr
    sys.path.insert(0, str(ROOT / "tests"))
    try:
        from test_calibration_profiles import campaign, run

        campaign_path = campaign(evidence)
        assert run(evidence, home, campaign_path, "create").returncode == 0
    finally:
        sys.path.pop(0)
    dirty_marker = ROOT / ".doctor-controlled-test-change"
    dirty_marker.write_text("controlled\n", encoding="utf-8")
    try:
        result = run_doctor(
            home,
            "--json",
            "--calibration-evidence-root",
            str(evidence),
            "--calibration-campaign",
            str(campaign_path),
            "--calibration-host-home-evidence",
            str(evidence / "host-home.json"),
            "--calibration-provisioning-task-id",
            "provisioning-task-1",
        )
    finally:
        dirty_marker.unlink()
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert [item["name"] for item in report["layers"]] == PRODUCTION_LAYERS
    assert len(report["development_layers"]) == 1
    development = report["development_layers"][0]
    assert development["name"] == "Calibration readiness"
    assert development["status"] == "FAIL"
    assert development["details"]["repository_clean"] is False


def test_doctor_detects_all_forbidden_repository_local_state_names(tmp_path: Path):
    core = load_core()
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
    assert core._unexpected_repository_state(tmp_path) == sorted(forbidden)


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
    assert "[UNKNOWN] Runtime route:" in result.stdout
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
    assert "[OK] Runtime route:" in result.stdout
    assert "[OK] Effective permission state:" in result.stdout
    assert "[UNKNOWN] Permission-source provenance:" in result.stdout


def test_doctor_preserves_corrupt_dispatch_state(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    state_file = tmp_path / "temp" / "subagents-dispatch" / "thread-corrupt" / "active.json"
    state_file.parent.mkdir(parents=True)
    state_file.write_text("{broken", encoding="utf-8")
    if os.name != "nt":
        state_file.chmod(0o600)
    result = run_doctor(
        home,
        "--check",
        "--temp-root",
        str(tmp_path / "temp"),
        env={"CODEX_THREAD_ID": "thread-corrupt"},
    )
    assert result.returncode != 0
    assert "[FAIL] Dispatch state:" in result.stdout
    assert "corrupt" in result.stdout.lower()
    assert state_file.read_text(encoding="utf-8") == "{broken"


def test_doctor_without_thread_id_does_not_create_dispatch_state(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    temp_root = tmp_path / "temp"
    temp_root.mkdir()
    result = run_doctor(
        home,
        "--check",
        "--temp-root",
        str(temp_root),
        env={"CODEX_THREAD_ID": ""},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "[UNKNOWN] Dispatch state:" in result.stdout
    assert "CODEX_THREAD_ID" in result.stdout
    assert not (temp_root / "subagents-dispatch").exists()


def test_doctor_reports_pending_takeover_and_stale_state_without_deleting_it(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    temp_root = tmp_path / "temp"
    state_dir = temp_root / "subagents-dispatch" / "thread-pending"
    state_dir.mkdir(parents=True)
    state = {
        "schema_version": "1.0",
        "root_thread_id": "thread-pending",
        "locale": "en",
        "created_at": "2026-07-01T00:00:00Z",
        "updated_at": "2026-07-01T00:00:00Z",
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
                "responsibility": {
                    "outcome": "finish bounded work",
                    "acceptance": "Main accepts result",
                },
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
    if os.name != "nt":
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
    assert result.returncode != 0
    report = json.loads(result.stdout)
    layer = next(item for item in report["layers"] if item["name"] == "Dispatch state")
    assert layer["status"] == "WARN"
    assert layer["details"]["active_orchestration"] is True
    assert layer["details"]["pending_takeovers"] == ["thread-pending"]
    assert state_file.is_file()
