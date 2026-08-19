from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace


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


def lifecycle_hooks() -> dict:
    lifecycle_matcher = "spawn_agent|followup_task|interrupt_agent|list_agents"
    guard = {
        "type": "command",
        "command": '"${PLUGIN_ROOT}/hooks/run-python.sh" "${PLUGIN_ROOT}/scripts/orchestration_guard.py"',
        "commandWindows": '"%PLUGIN_ROOT%\\hooks\\run-python.cmd" "%PLUGIN_ROOT%\\scripts\\orchestration_guard.py"',
        "timeout": 5,
        "async": False,
    }
    return {
        "hooks": {
            "PreToolUse": [{"matcher": lifecycle_matcher, "hooks": [dict(guard)]}],
            "PostToolUse": [{"matcher": lifecycle_matcher, "hooks": [dict(guard)]}],
            "SubagentStop": [
                {
                    "matcher": (
                        "subagents_dispatch_reader|subagents_dispatch_worker|"
                        "subagents_dispatch_investigator|subagents_dispatch_solver|"
                        "subagents_dispatch_advisor"
                    ),
                    "hooks": [dict(guard)],
                }
            ],
        }
    }


def host_evidence() -> dict:
    lifecycle = ["spawn_agent", "followup_task", "interrupt_agent", "list_agents"]
    return {
        "surface": "multi_agent_v2",
        "tools": [
            "spawn_agent",
            "send_message",
            "followup_task",
            "wait_agent",
            "list_agents",
            "interrupt_agent",
        ],
        "hooks": {
            "PreToolUse": [*lifecycle, "send_message"],
            "PostToolUse": lifecycle,
            "SubagentStop": True,
        },
        "fork_turns_none": True,
        "max_spawned_threads": 4,
    }


def test_default_doctor_does_not_create_missing_codex_home(tmp_path: Path):
    home = tmp_path / "missing-codex-home"
    assert not home.exists()
    result = run_doctor(home, tmp_path, "--check")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "[WARN] Managed Agents:" in result.stdout
    assert "Health: DEGRADED" in result.stdout
    assert not home.exists()


def test_modified_owned_profile_blocks_doctor_end_to_end(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    profile = home / "agents" / PROFILE
    profile.write_bytes(profile.read_bytes() + b"\n# adversarial user change\n")
    result = run_doctor(home, tmp_path, "--check")
    assert result.returncode != 0
    assert "[FAIL] Managed Agents: managed Agent profile ownership or filesystem safety check failed" in result.stdout
    assert "Health: BLOCKED" in result.stdout
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


def test_empty_lifecycle_hook_entries_fail_instead_of_looking_configured(monkeypatch, tmp_path: Path):
    doctor = load_doctor_core("doctor_adversarial_empty_hooks")
    hooks = tmp_path / "hooks.json"
    hooks.write_text(json.dumps({"hooks": {"PreToolUse": [], "PostToolUse": [], "SubagentStop": []}}), encoding="utf-8")
    monkeypatch.setattr(doctor, "HOOKS", hooks)
    result = doctor.diagnose_host_integration(None)
    assert result["status"] == "FAIL"
    assert result["details"]["host_evidence_supplied"] is False
    assert result["details"]["hook_errors"]


def test_valid_local_lifecycle_hooks_without_host_snapshot_remain_unknown(monkeypatch, tmp_path: Path):
    doctor = load_doctor_core("doctor_adversarial_hooks_unknown")
    hooks = tmp_path / "hooks.json"
    hooks.write_text(json.dumps(lifecycle_hooks()), encoding="utf-8")
    monkeypatch.setattr(doctor, "HOOKS", hooks)
    result = doctor.diagnose_host_integration(None)
    assert result["status"] == "UNKNOWN"
    assert result["details"]["hook_mode"] == "lifecycle"
    assert result["details"]["host_evidence_supplied"] is False
    assert result["details"]["missing_events"] == []


def test_missing_host_observation_changes_verification_without_degrading_health(monkeypatch, tmp_path: Path):
    doctor = load_doctor_core("doctor_adversarial_health_axes")
    hooks = tmp_path / "hooks.json"
    hooks.write_text(json.dumps(lifecycle_hooks()), encoding="utf-8")
    monkeypatch.setattr(doctor, "HOOKS", hooks)
    monkeypatch.setattr(doctor, "diagnose_plugin_package", lambda: doctor.layer("Plugin package", "OK", "ok"))
    monkeypatch.setattr(doctor, "diagnose_managed_agents", lambda _home: doctor.layer("Managed Agents", "OK", "ok"))
    monkeypatch.setattr(
        doctor,
        "diagnose_state",
        lambda _temp, _thread, _home: (
            doctor.layer("Orchestration state", "OK", "ok"),
            doctor.layer("Legacy compatibility", "OK", "ok"),
        ),
    )
    args = SimpleNamespace(thread_id="thread", temp_root=tmp_path, host_evidence=None)
    result = doctor.diagnose(args, tmp_path)
    assert result["status"] == "HEALTHY"
    assert result["verification"] == "UNVERIFIED"
    assert result["healthy"] is True


def test_wrong_lifecycle_hook_command_fails_closed(monkeypatch, tmp_path: Path):
    doctor = load_doctor_core("doctor_adversarial_wrong_hook_command")
    payload = lifecycle_hooks()
    payload["hooks"]["PreToolUse"][0]["hooks"][0]["command"] = "python unsafe.py"
    hooks = tmp_path / "hooks.json"
    hooks.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(doctor, "HOOKS", hooks)
    result = doctor.diagnose_host_integration(None)
    assert result["status"] == "FAIL"
    assert any("command binding" in item for item in result["details"]["hook_errors"])


def test_supplied_unbound_host_snapshot_remains_unknown(monkeypatch, tmp_path: Path):
    doctor = load_doctor_core("doctor_adversarial_host_snapshot_provenance")
    hooks = tmp_path / "hooks.json"
    hooks.write_text(json.dumps(lifecycle_hooks()), encoding="utf-8")
    evidence = tmp_path / "host.json"
    evidence.write_text(json.dumps(host_evidence()), encoding="utf-8")
    monkeypatch.setattr(doctor, "HOOKS", hooks)
    result = doctor.diagnose_host_integration(evidence)
    assert result["status"] == "UNKNOWN"
    assert result["details"]["capability_compatible"] is True
    assert result["details"]["host_evidence_supplied"] is True
    assert result["details"]["host_evidence_freshness_verified"] is False
    assert result["details"]["host_evidence_source"] == str(evidence)


def test_invalid_explicit_host_evidence_fails_closed_with_valid_local_hooks(monkeypatch, tmp_path: Path):
    doctor = load_doctor_core("doctor_adversarial_host_evidence")
    hooks = tmp_path / "hooks.json"
    hooks.write_text(json.dumps(lifecycle_hooks()), encoding="utf-8")
    evidence = tmp_path / "host.json"
    evidence.write_text('{"surface":"multi_agent_v2"}', encoding="utf-8")
    monkeypatch.setattr(doctor, "HOOKS", hooks)
    result = doctor.diagnose_host_integration(evidence)
    assert result["status"] == "FAIL"
    assert "Host evidence is invalid" in result["summary"]
