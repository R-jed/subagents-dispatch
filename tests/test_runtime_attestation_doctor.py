from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
DOCTOR = ROOT / "scripts" / "doctor.py"
INSTALLER = ROOT / "scripts" / "install-agents.py"
POLICY = json.loads((ROOT / "contracts" / "policy.json").read_text(encoding="utf-8"))
THREAD = "11111111-1111-7111-8111-111111111111"
PARENT = "00000000-0000-7000-8000-000000000000"
WORKER = POLICY["roles"]["worker"]


def install(home: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(INSTALLER), "--codex-home", str(home)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def route() -> dict:
    return {
        "thread_id": THREAD,
        "parent_thread_id": PARENT,
        "agent_role": WORKER["agent_type"],
        "model": WORKER["model"],
        "effort": WORKER["effort"],
        "sandbox_policy_type": "danger-full-access",
        "permission_profile_type": "disabled",
    }


def formal_evidence(*, include_permission_provenance: bool = True) -> dict:
    source = {
        "source_kind": "parent_turn",
        "source_id": PARENT,
        "sandbox_policy_type": "danger-full-access",
        "permission_profile_type": "disabled",
    }
    if include_permission_provenance:
        source.update(
            {
                "evidence_source": "local",
                "evidence_ref": "rollout:parent",
                "selection_evidence_ref": "host:permission-source-selection",
            }
        )
    return {
        "subject": "child",
        "expected": {
            "thread_id": THREAD,
            "parent_thread_id": PARENT,
            "agent_role": WORKER["agent_type"],
            "model": WORKER["model"],
            "effort": WORKER["effort"],
            "runtime_observation_required": True,
            "requires_permission_observation": True,
        },
        "local": route(),
        "effective_permission_source": source,
    }


def run_doctor(home: Path, evidence: Path, *, live_route: bool = True) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(DOCTOR),
        "--codex-home",
        str(home),
        "--check",
        "--runtime-evidence",
        str(evidence),
    ]
    if live_route:
        command.append("--live-route")
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_doctor_accepts_complete_exact_rollout_attestation_without_public_route_metadata(
    tmp_path: Path,
):
    home = tmp_path / "codex-home"
    install(home)
    evidence = tmp_path / "runtime.json"
    evidence.write_text(json.dumps(formal_evidence()), encoding="utf-8")

    result = run_doctor(home, evidence)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Layer: Runtime route evidence: OK" in result.stdout
    assert "Overall: OK" in result.stdout


def test_doctor_live_route_rejects_missing_formal_requirement_flags(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    payload = formal_evidence()
    del payload["expected"]["requires_permission_observation"]
    evidence = tmp_path / "runtime-missing-flag.json"
    evidence.write_text(json.dumps(payload), encoding="utf-8")

    result = run_doctor(home, evidence)

    assert result.returncode == 1
    assert "Layer: Runtime route evidence: FAIL" in result.stdout
    assert "requires expected.requires_permission_observation=true" in result.stdout
    assert "Overall: UNHEALTHY" in result.stdout


def test_doctor_live_route_does_not_pass_unbound_permission_source(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    evidence = tmp_path / "runtime-unbound-source.json"
    evidence.write_text(
        json.dumps(formal_evidence(include_permission_provenance=False)),
        encoding="utf-8",
    )

    result = run_doctor(home, evidence)

    assert result.returncode == 1
    assert "Layer: Runtime route evidence: UNKNOWN" in result.stdout
    assert "Overall: UNHEALTHY" in result.stdout


def test_non_live_doctor_keeps_unknown_runtime_evidence_nonfatal(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    evidence = tmp_path / "runtime-unbound-source.json"
    evidence.write_text(
        json.dumps(formal_evidence(include_permission_provenance=False)),
        encoding="utf-8",
    )

    result = run_doctor(home, evidence, live_route=False)

    assert result.returncode == 0
    assert "Layer: Runtime route evidence: UNKNOWN" in result.stdout
    assert "Overall: OK" in result.stdout
