from __future__ import annotations

import json
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


def test_doctor_reports_exact_six_layers_and_unobserved_runtime_is_not_unhealthy(tmp_path: Path):
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
        "Runtime route evidence",
    ]
    layer_lines = [line for line in output.splitlines() if line.startswith("Layer:")]
    assert len(layer_lines) == len(labels)
    for line, label in zip(layer_lines, labels):
        assert line.startswith(f"Layer: {label}:")
    assert "Layer: Codex Host: UNKNOWN" in output
    assert "Layer: Runtime route evidence: UNKNOWN" in output
    assert "not run" in output


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
    assert "Layer: Runtime route evidence: UNKNOWN" in result.stdout
    assert "configured/requested" in result.stdout
    assert "observed runtime route was not reported" in result.stdout


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
    result = run_doctor(home, "--check", "--temp-root", str(temp_root), env={"CODEX_THREAD_ID": ""})

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Layer: Dispatch state: UNKNOWN" in result.stdout
    assert "CODEX_THREAD_ID" in result.stdout
    assert not temp_root.exists()
