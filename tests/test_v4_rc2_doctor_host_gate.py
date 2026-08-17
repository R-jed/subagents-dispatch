from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
HOST_SMOKE = ROOT / "docs" / "v4" / "host-smoke.json"


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


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def tracked_contract() -> dict:
    return json.loads(HOST_SMOKE.read_text(encoding="utf-8"))


def bind_files(module, tmp_path: Path, *, smoke: dict, production_events: list[str]) -> None:
    smoke_path = tmp_path / "host-smoke.json"
    production_path = tmp_path / "hooks.json"
    staged_path = tmp_path / "staged-hooks.json"
    write_json(smoke_path, smoke)
    write_json(production_path, {"hooks": {event: [] for event in production_events}})
    write_json(
        staged_path,
        {"hooks": {event: [] for event in ("PreToolUse", "PostToolUse", "SubagentStop")}},
    )
    module.HOST_SMOKE = smoke_path
    module.HOOKS = production_path
    module.STAGED_HOOKS = staged_path


def test_tracked_top_level_pass_is_rejected_even_without_embedded_results(tmp_path: Path):
    doctor = load_module("rc4_doctor_spoof", "doctor_runtime.py")
    smoke = tracked_contract()
    smoke["status"] = "PASS"
    bind_files(
        doctor,
        tmp_path,
        smoke=smoke,
        production_events=["PreToolUse", "PostToolUse", "SubagentStop"],
    )

    hook, release = doctor.diagnose_hook_and_release()
    assert hook["status"] == "FAIL"
    assert "tracked Host-smoke contract must remain PENDING" in hook["summary"]
    assert release["details"]["release_ready"] is False


def test_complete_production_hooks_cannot_close_gate_without_external_campaign(tmp_path: Path):
    doctor = load_module("rc4_doctor_external_boundary", "doctor_runtime.py")
    bind_files(
        doctor,
        tmp_path,
        smoke=tracked_contract(),
        production_events=["PreToolUse", "PostToolUse", "SubagentStop"],
    )

    hook, release = doctor.diagnose_hook_and_release()
    assert hook["status"] == "UNKNOWN"
    assert hook["details"]["smoke_complete"] is False
    assert release["status"] == "UNKNOWN"
    assert release["details"]["release_ready"] is False


def test_pending_empty_results_remains_valid_but_release_blocked(tmp_path: Path):
    doctor = load_module("rc4_doctor_pending", "doctor_runtime.py")
    bind_files(
        doctor,
        tmp_path,
        smoke=tracked_contract(),
        production_events=["PreToolUse"],
    )

    hook, release = doctor.diagnose_hook_and_release()
    assert hook["status"] == "UNKNOWN"
    assert hook["details"]["smoke_complete"] is False
    assert release["details"]["release_ready"] is False
