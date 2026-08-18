from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
DOCTOR = SCRIPTS / "doctor.py"
INSTALLER = SCRIPTS / "install-agents.py"
PROFILE = "subagents-dispatch-worker.toml"
MANIFEST = ".subagents-dispatch-agents.json"


def load_doctor_core(name: str):
    scripts = str(SCRIPTS)
    sys.path.insert(0, scripts)
    try:
        spec = importlib.util.spec_from_file_location(name, SCRIPTS / "doctor_runtime_core.py")
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts)


def install(home: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(INSTALLER), "--codex-home", str(home)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def run_doctor(home: Path, temp_root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(DOCTOR),
            "--codex-home",
            str(home),
            "--temp-root",
            str(temp_root),
            "--thread-id",
            "doctor-adversarial",
            *extra,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_default_doctor_does_not_create_missing_codex_home(tmp_path: Path):
    home = tmp_path / "missing-codex-home"
    assert not home.exists()

    result = run_doctor(home, tmp_path, "--check")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[WARN] Managed Agents:" in result.stdout
    assert "Overall: DEGRADED" in result.stdout
    assert not home.exists()


def test_modified_owned_profile_blocks_doctor_end_to_end(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    profile = home / "agents" / PROFILE
    profile.write_bytes(profile.read_bytes() + b"\n# adversarial user change\n")

    result = run_doctor(home, tmp_path, "--check")

    assert result.returncode != 0
    assert "[FAIL] Managed Agents: managed Agent profile ownership or filesystem safety check failed" in result.stdout
    assert "Overall: BLOCKED" in result.stdout
    assert profile.read_bytes().endswith(b"# adversarial user change\n")


def test_doctor_uninstall_refuses_modified_owned_profile_without_partial_deletion(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    profile = home / "agents" / PROFILE
    profile.write_bytes(profile.read_bytes() + b"\n# preserve me\n")
    manifest_before = (home / MANIFEST).read_bytes()
    other_profiles = {
        path.name: path.read_bytes()
        for path in (home / "agents").glob("subagents-dispatch-*.toml")
    }

    result = run_doctor(home, tmp_path, "--uninstall-managed")

    assert result.returncode != 0
    assert "managed profile uninstall failed" in result.stderr
    assert (home / MANIFEST).read_bytes() == manifest_before
    assert {
        path.name: path.read_bytes()
        for path in (home / "agents").glob("subagents-dispatch-*.toml")
    } == other_profiles


def test_complete_local_hooks_without_live_host_evidence_remain_unknown(monkeypatch, tmp_path: Path):
    doctor = load_doctor_core("doctor_adversarial_hooks_unknown")
    hooks = tmp_path / "hooks.json"
    hooks.write_text(
        json.dumps(
            {
                "hooks": {
                    "PreToolUse": [],
                    "PostToolUse": [],
                    "SubagentStop": [],
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(doctor, "HOOKS", hooks)

    result = doctor.diagnose_host_integration(None)

    assert result["status"] == "UNKNOWN"
    assert result["details"]["live_host_observed"] is False
    assert result["details"]["missing_events"] == []


def test_invalid_explicit_host_evidence_fails_closed_even_with_complete_local_hooks(
    monkeypatch, tmp_path: Path
):
    doctor = load_doctor_core("doctor_adversarial_host_evidence")
    hooks = tmp_path / "hooks.json"
    hooks.write_text(
        json.dumps(
            {
                "hooks": {
                    "PreToolUse": [],
                    "PostToolUse": [],
                    "SubagentStop": [],
                }
            }
        ),
        encoding="utf-8",
    )
    evidence = tmp_path / "host.json"
    evidence.write_text('{"surface":"multi_agent_v2"}', encoding="utf-8")
    monkeypatch.setattr(doctor, "HOOKS", hooks)

    result = doctor.diagnose_host_integration(evidence)

    assert result["status"] == "FAIL"
    assert "Host evidence is invalid" in result["summary"]
