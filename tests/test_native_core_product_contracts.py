from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_public_installation_commands_match_current_cli_surface():
    install = (ROOT / "docs" / "plugin-installation.md").read_text(encoding="utf-8")
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
    for flag in (
        "--check",
        "--repair",
        "--migrate-legacy",
        "--cleanup-stale",
        "--uninstall-managed",
    ):
        assert flag in doctor_help.stdout

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
    smoke = json.loads(
        (ROOT / "docs" / "v4" / "host-smoke.json").read_text(encoding="utf-8")
    )
    expected = [f"N{index}" for index in range(9)]
    assert [item["id"] for item in smoke["required_probes"]] == expected

    checklist = (ROOT / "docs" / "release-checklist.md").read_text(encoding="utf-8")
    for probe in expected:
        assert f"{probe} " in checklist


def test_ai_and_runtime_docs_match_current_public_roles_and_child_ceiling():
    ai = (ROOT / "README_AI.md").read_text(encoding="utf-8")
    runtime = (ROOT / "docs" / "native-subagent-runtime.md").read_text(encoding="utf-8")
    for text in (ai, runtime):
        assert "Orchestrate" in text and "Doctor" in text
        assert "gpt-5.6-luna" in text
        assert "max" in text
        assert "managed children <= 4" in text
        assert "initial managed children <= 2" not in text
        assert "normal managed children <= 3" not in text


def test_repository_privacy_policy_is_not_tracked():
    assert not (ROOT / "PRIVACY.md").exists()
