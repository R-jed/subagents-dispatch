from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

ACTIVE_PRODUCT_DOCS = (
    ROOT / "docs" / "plugin-installation.md",
    ROOT / "README_AI.md",
    ROOT / "docs" / "native-subagent-runtime.md",
    ROOT / "docs" / "repository-architecture.md",
    ROOT / "docs" / "package-integrity.md",
    ROOT / "docs" / "release-checklist.md",
    ROOT / "PRIVACY.md",
)

RETIRED_RUNTIME_PATHS = (
    "hooks/hooks.json",
    "scripts/orchestration_guard.py",
    "scripts/dispatch_control_v4.py",
    "scripts/host_evidence_v4.py",
    "scripts/spawn_guard.py",
    "docs/v4/hooks.json",
)


def test_active_product_docs_do_not_restore_retired_hook_runtime_paths():
    for path in ACTIVE_PRODUCT_DOCS:
        text = path.read_text(encoding="utf-8")
        for retired in RETIRED_RUNTIME_PATHS:
            assert retired not in text, f"{path} still presents retired path {retired}"
        assert "H00-H20" not in text


def test_public_installation_commands_match_current_cli_surface():
    install = (ROOT / "docs" / "plugin-installation.md").read_text(encoding="utf-8")
    assert "scripts/doctor.py --codex-home <active-codex-home> --update" not in install
    assert "scripts/plugin_update.py --codex-home <active-codex-home>" in install
    assert "scripts/check-plugin-update.py --codex-home <active-codex-home>" in install

    doctor_help = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "doctor.py"), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert doctor_help.returncode == 0
    for flag in ("--check", "--repair", "--migrate-legacy", "--cleanup-stale", "--uninstall-managed"):
        assert flag in doctor_help.stdout
    assert "--update" not in doctor_help.stdout

    for script in ("plugin_update.py", "check-plugin-update.py"):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / script), "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "--codex-home" in result.stdout


def test_release_checklist_uses_same_n0_n8_gate_as_machine_contract():
    smoke = json.loads((ROOT / "docs" / "v4" / "host-smoke.json").read_text(encoding="utf-8"))
    expected = [f"N{index}" for index in range(9)]
    assert [item["id"] for item in smoke["required_probes"]] == expected

    checklist = (ROOT / "docs" / "release-checklist.md").read_text(encoding="utf-8")
    for probe in expected:
        assert f"{probe} " in checklist
    for old in ("H00", "H08", "H20", "PreToolUse", "PostToolUse", "SubagentStop"):
        assert old not in checklist


def test_ai_and_runtime_docs_match_current_public_roles_and_fanout():
    ai = (ROOT / "README_AI.md").read_text(encoding="utf-8")
    runtime = (ROOT / "docs" / "native-subagent-runtime.md").read_text(encoding="utf-8")
    for text in (ai, runtime):
        assert "Orchestrate" in text and "Doctor" in text
        assert "gpt-5.6-terra" in text
        assert "high" in text
        assert "initial managed children <= 2" in text
        assert "normal managed children <= 3" in text
    for retired_skill in ("`dispatch`", "`preview`", "`status`", "`steer`", "`takeover`"):
        assert retired_skill not in runtime


def test_privacy_describes_native_core_state_without_retired_control_records():
    privacy = (ROOT / "PRIVACY.md").read_text(encoding="utf-8")
    assert "WorkUnit" in privacy
    assert "ExecutionBinding" in privacy
    assert "WriterLease" in privacy
    assert "PendingControl" not in privacy
    assert "PreToolUse" not in privacy
    assert "PostToolUse" not in privacy
    assert "SubagentStop" not in privacy
