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


def native_host_evidence(*, managed_child_containment: str = "verified") -> dict:
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
        "managed_child_containment": managed_child_containment,
        "max_concurrent_threads_per_session": 5,
    }


def test_doctor_reports_current_product_health_layers_with_host_unknown(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    result = run_doctor(home, tmp_path, "--check")

    assert result.returncode == 0, result.stdout + result.stderr
    order = [
        "Plugin package",
        "Managed Agents",
        "Host integration",
        "Orchestration state",
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


def test_doctor_treats_failed_hard_containment_as_diagnostic(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    evidence = tmp_path / "host.json"
    evidence.write_text(
        json.dumps(native_host_evidence(managed_child_containment="failed")),
        encoding="utf-8",
    )

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
    assert host_layer["status"] == "OK"
    assert "missing" not in host_layer["details"]


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


def test_unknown_execution_and_writer_lease_remain_unknown_in_doctor(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    state = load_module("doctor_unknown_state", "dispatch_state_v4.py")
    graph = load_module("doctor_unknown_graph", "work_graph_v4.py")
    lifecycle = load_module("doctor_unknown_lifecycle", "execution_lifecycle_v4.py")
    state.write_state(state.new_state(thread_id=THREAD), temp_root=tmp_path)
    unit = graph.make_work_unit(
        unit_id="U1",
        intent="implement",
        goal="change owned source",
        output="patch",
        ownership_write=["src/a.py"],
        authority_ceiling="bounded-source-write",
        write_scope_ceiling=["src/a.py"],
        done_when="tests pass",
    )
    graph.install_work_graph(THREAD, units=[unit], temp_root=tmp_path)
    lifecycle.allocate_execution(
        THREAD,
        unit_id="U1",
        execution_id="exec-1",
        native_task_name="sd_u1_a1",
        profile_id="worker",
        granted_authority="bounded-source-write",
        granted_write_scope=["src/a.py"],
        writer_lease_id="lease-1",
        temp_root=tmp_path,
    )
    lifecycle.mark_execution_unknown(
        THREAD,
        execution_id="exec-1",
        temp_root=tmp_path,
    )

    result = run_doctor(home, tmp_path, "--check")

    assert result.returncode == 0, result.stdout + result.stderr
    assert (
        "[UNKNOWN] Orchestration state: Current orchestration state contains unresolved Host uncertainty"
        in result.stdout
    )

    structured = run_doctor(home, tmp_path, "--json", "--check")
    assert structured.returncode == 0, structured.stdout + structured.stderr
    orchestration_layer = json.loads(structured.stdout)["layers"][3]
    assert orchestration_layer["status"] == "UNKNOWN"
    assert orchestration_layer["details"]["unknown_executions"] == ["exec-1"]
    assert orchestration_layer["details"]["writer_state"] == "UNKNOWN"


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


def test_explicit_blank_thread_identity_fails_closed(tmp_path: Path):
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
            "--check",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "explicit --thread-id must be non-empty" in result.stderr
    assert "Traceback" not in result.stderr


def test_removed_pre_1_0_doctor_actions_fail_as_unknown_arguments(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    for option in ("--legacy", "--migrate-legacy", "--cleanup-stale"):
        result = subprocess.run(
            [sys.executable, str(DOCTOR), "--codex-home", str(home), option],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode != 0
        assert "unrecognized arguments" in result.stderr


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
