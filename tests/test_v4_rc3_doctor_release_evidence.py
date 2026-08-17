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


def test_doctor_without_external_release_evidence_is_never_release_ready():
    doctor = load_module("rc3_doctor_release_missing", "doctor_runtime.py")
    layer = doctor.diagnose_release_evidence(None)

    assert layer["name"] == "Release readiness"
    assert layer["status"] == "UNKNOWN"
    assert layer["details"]["release_ready"] is False
    assert doctor.release_predicate({"healthy": True, "release_ready": False}) is False


def test_arbitrary_all_green_release_json_is_fail_closed(tmp_path: Path):
    doctor = load_module("rc3_doctor_release_fake", "doctor_runtime.py")
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


def test_release_check_argument_is_exposed_by_doctor_parser(monkeypatch):
    doctor = load_module("rc3_doctor_release_arg", "doctor_runtime.py")
    monkeypatch.setattr(sys, "argv", ["doctor_runtime.py", "--release-evidence", "/tmp/evidence.json"])
    args = doctor.parse_args()
    assert args.release_evidence == Path("/tmp/evidence.json")
