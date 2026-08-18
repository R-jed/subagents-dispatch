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


def test_tracked_host_contract_cannot_self_attest_pass(tmp_path: Path):
    doctor = load_module("doctor_gate_spoof", "doctor_runtime.py")
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
    assert release["details"]["release_ready"] is False


def test_complete_production_hooks_cannot_replace_external_campaign(tmp_path: Path):
    doctor = load_module("doctor_gate_external_boundary", "doctor_runtime.py")
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
    doctor = load_module("doctor_gate_pending", "doctor_runtime.py")
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


def test_doctor_without_external_release_evidence_is_never_release_ready():
    doctor = load_module("doctor_release_missing", "doctor_runtime.py")
    layer = doctor.diagnose_release_evidence(None)

    assert layer["name"] == "Release readiness"
    assert layer["status"] == "UNKNOWN"
    assert layer["details"]["release_ready"] is False
    assert doctor.release_predicate({"healthy": True, "release_ready": False}) is False


def test_arbitrary_all_green_release_json_is_fail_closed(tmp_path: Path):
    doctor = load_module("doctor_release_fake", "doctor_runtime.py")
    evidence = tmp_path / "release.json"
    evidence.write_text(
        json.dumps(
            {
                "schema_version": "4.0.0-release-evidence-1",
                "repository": "R-jed/subagents-dispatch",
                "candidate_commit": "a" * 40,
                "candidate_tree": "b" * 40,
                "runtime_manifest_sha256": "c" * 64,
                "production_hook_sha256": "d" * 64,
                "profile_contract_sha256": "e" * 64,
                "host_campaign": {"status": "PASS"},
                "final_review": {"verdict": "ship"},
            }
        ),
        encoding="utf-8",
    )

    layer = doctor.diagnose_release_evidence(evidence)
    assert layer["status"] == "FAIL"
    assert layer["details"]["release_ready"] is False
    assert layer["details"]["issues"]


def test_release_evidence_argument_is_exposed_by_doctor_parser(monkeypatch):
    doctor = load_module("doctor_release_arg", "doctor_runtime.py")
    monkeypatch.setattr(sys, "argv", ["doctor_runtime.py", "--release-evidence", "/tmp/evidence.json"])
    args = doctor.parse_args()
    assert args.release_evidence == Path("/tmp/evidence.json")


def test_doctor_and_release_owner_share_the_static_host_contract():
    release = load_module("doctor_gate_release_owner", "release_evidence_v4.py")
    core = load_module("doctor_gate_core", "doctor_runtime_core.py")
    smoke = tracked_contract()

    assert core.EXPECTED_HOST_PROBES == release.REQUIRED_HOST_PROBES
    valid, complete, reason = core._validate_host_smoke_evidence(smoke)
    assert valid is True, reason
    assert complete is False

    spoofed = dict(smoke)
    spoofed["status"] = "PASS"
    valid, complete, reason = core._validate_host_smoke_evidence(spoofed)
    assert valid is False
    assert complete is False
    assert reason
