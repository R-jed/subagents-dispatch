from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


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


def required_probes() -> list[dict]:
    return [{"id": f"H{index:02d}", "operation": "fixture", "requires": []} for index in range(11)]


def complete_results() -> dict:
    results = {
        f"H{index:02d}": {
            "status": "PASS",
            "evidence_ref": f"host-evidence:H{index:02d}",
        }
        for index in range(11)
    }
    results["H00"]["manifest_sha256"] = "a" * 64
    results["H00"]["trusted_current_definition"] = True
    return results


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


def test_top_level_pass_without_per_probe_evidence_is_rejected(tmp_path: Path):
    doctor = load_module("rc2_doctor_spoof", "doctor_runtime.py")
    bind_files(
        doctor,
        tmp_path,
        smoke={
            "status": "PASS",
            "gate_id": "phase8-real-host-lifecycle-coverage",
            "required_probes": required_probes(),
            "results": {},
        },
        production_events=["PreToolUse", "PostToolUse", "SubagentStop"],
    )

    hook, release = doctor.diagnose_hook_and_release()
    assert hook["status"] == "FAIL"
    assert "every H00-H10" in hook["summary"]
    assert release["details"]["release_ready"] is False


def test_complete_per_probe_evidence_and_production_hooks_can_close_release_gate(tmp_path: Path):
    doctor = load_module("rc2_doctor_complete", "doctor_runtime.py")
    bind_files(
        doctor,
        tmp_path,
        smoke={
            "status": "PASS",
            "gate_id": "phase8-real-host-lifecycle-coverage",
            "required_probes": required_probes(),
            "results": complete_results(),
        },
        production_events=["PreToolUse", "PostToolUse", "SubagentStop"],
    )

    hook, release = doctor.diagnose_hook_and_release()
    assert hook["status"] == "OK"
    assert hook["details"]["smoke_complete"] is True
    assert release["status"] == "OK"
    assert release["details"]["release_ready"] is True


def test_pending_empty_results_remains_valid_but_release_blocked(tmp_path: Path):
    doctor = load_module("rc2_doctor_pending", "doctor_runtime.py")
    bind_files(
        doctor,
        tmp_path,
        smoke={
            "status": "PENDING",
            "gate_id": "phase8-real-host-lifecycle-coverage",
            "required_probes": required_probes(),
            "results": {},
        },
        production_events=["PreToolUse"],
    )

    hook, release = doctor.diagnose_hook_and_release()
    assert hook["status"] == "UNKNOWN"
    assert hook["details"]["smoke_complete"] is False
    assert release["details"]["release_ready"] is False
