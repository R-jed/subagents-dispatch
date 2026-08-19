from __future__ import annotations

import argparse
import ast
import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
DOCTOR = SCRIPTS / "doctor.py"


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


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_product_doctor_has_no_release_or_calibration_dependencies():
    imports = imported_modules(SCRIPTS / "doctor_runtime.py") | imported_modules(
        SCRIPTS / "doctor_runtime_core.py"
    )
    forbidden = {
        "release_evidence_v4",
        "calibration_profiles",
        "calibration_profiles_core",
        "calibration_profile_contract",
    }
    assert imports.isdisjoint(forbidden)


@pytest.mark.parametrize(
    "flag",
    [
        "--release-check",
        "--release-evidence",
        "--calibration-evidence-root",
        "--calibration-campaign",
        "--calibration-host-home-evidence",
        "--calibration-provisioning-task-id",
        "--runtime-evidence",
        "--live-route",
    ],
)
def test_public_doctor_rejects_maintainer_and_experiment_flags(tmp_path: Path, flag: str):
    command = [
        sys.executable,
        str(DOCTOR),
        "--codex-home",
        str(tmp_path / "codex-home"),
        flag,
    ]
    if flag in {
        "--release-evidence",
        "--calibration-evidence-root",
        "--calibration-campaign",
        "--calibration-host-home-evidence",
        "--calibration-provisioning-task-id",
        "--runtime-evidence",
    }:
        command.append(str(tmp_path / "evidence.json"))
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "unrecognized arguments" in result.stderr


def test_default_diagnosis_invokes_only_local_managed_profile_check(monkeypatch, tmp_path: Path):
    runtime = load_module("doctor_product_default_runtime", "doctor_runtime.py")
    runtime.configure_core()
    doctor = runtime.core
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append([str(item) for item in command])
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(doctor.subprocess, "run", fake_run)
    args = argparse.Namespace(
        codex_home=tmp_path / "codex-home",
        temp_root=tmp_path,
        thread_id=None,
        host_evidence=None,
        check=False,
        json=False,
        legacy=False,
        repair=False,
        migrate_legacy=False,
        cleanup_stale=False,
        uninstall_managed=False,
    )
    report = doctor.diagnose(args, args.codex_home)

    assert report["healthy"] is True
    assert calls
    assert all("install-agents.py" in " ".join(call) for call in calls)
    assert all("marketplace" not in " ".join(call) for call in calls)
    assert all("codex" not in Path(call[0]).name.lower() for call in calls)


def test_missing_managed_profiles_are_degraded_and_repairable(monkeypatch, tmp_path: Path):
    doctor = load_module("doctor_product_missing_profiles", "doctor_runtime_core.py")

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(
            command,
            1,
            "",
            "Not installed: managed Agent profile is missing (/tmp/profile.toml).",
        )

    monkeypatch.setattr(doctor.subprocess, "run", fake_run)
    result = doctor.diagnose_managed_agents(tmp_path / "home")
    assert result["status"] == "WARN"
    assert "repair" in result["action"].lower()


def test_unsafe_managed_profile_ownership_is_blocked(monkeypatch, tmp_path: Path):
    doctor = load_module("doctor_product_unsafe_profiles", "doctor_runtime_core.py")

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(
            command,
            1,
            "",
            "Refusing symlinked Agent profile destination: /tmp/profile.toml",
        )

    monkeypatch.setattr(doctor.subprocess, "run", fake_run)
    result = doctor.diagnose_managed_agents(tmp_path / "home")
    assert result["status"] == "FAIL"
    assert "ownership or filesystem safety" in result["summary"]


def test_safety_critical_unknown_state_is_blocked(monkeypatch, tmp_path: Path):
    doctor = load_module("doctor_product_unknown_state", "doctor_runtime_core.py")
    payload = {
        "writer_lease": {"state": "UNKNOWN"},
        "pending_controls": [],
        "executions": [],
        "work_units": [],
        "state_revision": 3,
    }
    monkeypatch.setattr(doctor, "_state_snapshot", lambda *_: ("v4", payload, None))
    monkeypatch.setattr(
        doctor,
        "_legacy_profile_status",
        lambda *_: ("OK", "legacy clear", None, {}),
    )

    orchestration, legacy = doctor.diagnose_state(tmp_path, "thread", tmp_path / "home")
    assert orchestration["status"] == "FAIL"
    assert "WriterLease.UNKNOWN" in orchestration["details"]["critical"]
    assert legacy["status"] == "OK"


def test_in_flight_control_is_degraded_without_becoming_a_false_failure(monkeypatch, tmp_path: Path):
    doctor = load_module("doctor_product_inflight_state", "doctor_runtime_core.py")
    payload = {
        "writer_lease": None,
        "pending_controls": [{"control_id": "C1", "state": "IN_FLIGHT"}],
        "executions": [],
        "work_units": [],
        "state_revision": 4,
    }
    monkeypatch.setattr(doctor, "_state_snapshot", lambda *_: ("v4", payload, None))
    monkeypatch.setattr(
        doctor,
        "_legacy_profile_status",
        lambda *_: ("OK", "legacy clear", None, {}),
    )

    orchestration, _ = doctor.diagnose_state(tmp_path, "thread", tmp_path / "home")
    assert orchestration["status"] == "WARN"
    assert orchestration["details"]["active"] == ["PendingControl active"]


def test_explicit_maintenance_actions_are_mutually_exclusive(tmp_path: Path):
    doctor = load_module("doctor_product_action_exclusivity", "doctor_runtime_core.py")
    args = argparse.Namespace(
        repair=True,
        migrate_legacy=False,
        cleanup_stale=True,
        uninstall_managed=False,
        thread_id=None,
        temp_root=tmp_path,
    )
    with pytest.raises(doctor.DoctorError, match="mutually exclusive"):
        doctor._explicit_actions(args, tmp_path / "home")
