from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
DOCTOR = ROOT / "scripts" / "doctor.py"
INSTALLER = ROOT / "scripts" / "install-agents.py"
SCRIPTS = ROOT / "scripts"
THREAD = "doctor-v4-thread"


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
            THREAD,
            *extra,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def native_host_evidence() -> dict:
    return {
        "surface": "multi_agent_v2",
        "tools": [
            "spawn_agent",
            "followup_task",
            "wait_agent",
            "list_agents",
            "interrupt_agent",
        ],
        "fork_turns_none": True,
        "max_concurrent_threads_per_session": 5,
    }


def test_doctor_reports_product_health_layers_with_host_unknown(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    result = run_doctor(home, tmp_path, "--check")

    assert result.returncode == 0, result.stdout + result.stderr
    order = [
        "Plugin package",
        "Managed Agents",
        "Host integration",
        "Orchestration state",
        "Legacy compatibility",
    ]
    positions = [result.stdout.index(f"] {name}:") for name in order]
    assert positions == sorted(positions)
    assert "[OK] Plugin package: Plugin files and public skills are valid" in result.stdout
    assert (
        "[OK] Managed Agents: All 5 managed Agent profiles are installed and match this Plugin version"
        in result.stdout
    )
    assert "[UNKNOWN] Host integration: Current Host capabilities were not checked" in result.stdout
    assert "[OK] Orchestration state: No active orchestration state" in result.stdout


def test_doctor_json_has_only_current_layers_and_actions(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    result = run_doctor(home, tmp_path, "--json", "--check")

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert set(payload) == {"layers", "actions"}
    assert payload["actions"] == []
    assert [item["name"] for item in payload["layers"]] == [
        "Plugin package",
        "Managed Agents",
        "Host integration",
        "Orchestration state",
        "Legacy compatibility",
    ]
    assert payload["layers"][2]["status"] == "UNKNOWN"


def test_doctor_accepts_current_native_host_capability_snapshot(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    evidence = tmp_path / "host.json"
    evidence.write_text(json.dumps(native_host_evidence()), encoding="utf-8")

    result = run_doctor(home, tmp_path, "--host-evidence", str(evidence), "--check")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[OK] Host integration: Native Subagent capabilities are ready" in result.stdout

    structured = run_doctor(
        home,
        tmp_path,
        "--host-evidence",
        str(evidence),
        "--json",
        "--check",
    )
    assert structured.returncode == 0, structured.stdout + structured.stderr
    host_layer = json.loads(structured.stdout)["layers"][2]
    assert host_layer["details"]["max_concurrent_threads_per_session"] == 5
    assert host_layer["details"]["capacity_includes_primary"] is True
    assert "max_spawned_threads" not in host_layer["details"]


def test_doctor_rejects_missing_required_native_host_primitive(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    payload = native_host_evidence()
    payload["tools"].remove("interrupt_agent")
    evidence = tmp_path / "host.json"
    evidence.write_text(json.dumps(payload), encoding="utf-8")

    result = run_doctor(home, tmp_path, "--host-evidence", str(evidence), "--check")

    assert result.returncode != 0
    assert "[FAIL] Host integration: Required Native Subagent capabilities are unavailable" in result.stdout


def test_valid_v4_state_is_diagnosed_directly(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    state = load_module("doctor_v4_state", "dispatch_state_v4.py")
    state.write_state(state.new_state(thread_id=THREAD), temp_root=tmp_path)

    result = run_doctor(home, tmp_path, "--check")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[OK] Orchestration state: Current orchestration state is healthy" in result.stdout


def test_missing_managed_profiles_are_warning_and_repairable(tmp_path: Path):
    home = tmp_path / "missing-codex-home"
    assert not home.exists()

    result = run_doctor(home, tmp_path, "--check")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[WARN] Managed Agents: Managed Agent profiles need setup or repair" in result.stdout
    assert not home.exists()


def test_modified_owned_profile_blocks_doctor(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    profile = home / "agents" / "subagents-dispatch-reader.toml"
    profile.write_bytes(profile.read_bytes() + b"\n# mutation\n")

    result = run_doctor(home, tmp_path, "--check")

    assert result.returncode != 0
    assert "[FAIL] Managed Agents: Managed Agent profiles cannot be changed safely" in result.stdout


def test_cleanup_stale_rejects_explicit_blank_thread_identity_safely(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    result = subprocess.run(
        [
            sys.executable,
            str(DOCTOR),
            "--codex-home",
            str(home),
            "--temp-root",
            str(tmp_path),
            "--thread-id",
            "",
            "--cleanup-stale",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "explicit --thread-id must be non-empty" in result.stderr
    assert "Traceback" not in result.stderr


def test_legacy_flag_displays_current_migration_state_without_mutation(tmp_path: Path):
    result = subprocess.run(
        [sys.executable, str(DOCTOR), "--codex-home", str(tmp_path / "codex-home"), "--legacy"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "[" in result.stdout
    assert "Legacy compatibility" in result.stdout
    assert "Migration state:" in result.stdout


def test_doctor_can_explicitly_uninstall_only_owned_managed_profiles(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    result = run_doctor(home, tmp_path, "--uninstall-managed")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[OK] Action: Managed Agent profiles removed" in result.stdout
    assert "[WARN] Managed Agents:" in result.stdout

    verifier = subprocess.run(
        [sys.executable, str(INSTALLER), "--codex-home", str(home), "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert verifier.returncode != 0
