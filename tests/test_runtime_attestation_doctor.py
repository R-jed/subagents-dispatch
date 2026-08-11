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


def test_doctor_accepts_complete_exact_rollout_attestation_without_public_route_metadata(
    tmp_path: Path,
):
    home = tmp_path / "codex-home"
    install(home)
    evidence = tmp_path / "runtime.json"
    route = {
        "thread_id": THREAD,
        "parent_thread_id": PARENT,
        "agent_role": WORKER["agent_type"],
        "model": WORKER["model"],
        "effort": WORKER["effort"],
        "sandbox_policy_type": "danger-full-access",
        "permission_profile_type": "disabled",
    }
    evidence.write_text(
        json.dumps(
            {
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
                "local": route,
                "effective_permission_source": {
                    "source_kind": "parent_turn",
                    "sandbox_policy_type": "danger-full-access",
                    "permission_profile_type": "disabled",
                },
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(DOCTOR),
            "--codex-home",
            str(home),
            "--check",
            "--runtime-evidence",
            str(evidence),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Layer: Runtime route evidence: OK" in result.stdout
