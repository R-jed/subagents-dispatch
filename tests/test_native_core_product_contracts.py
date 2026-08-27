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
    for flag in ("--check", "--repair", "--uninstall-managed"):
        assert flag in doctor_help.stdout
    for removed_flag in ("--legacy", "--migrate-legacy", "--cleanup-stale"):
        assert removed_flag not in doctor_help.stdout

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


def test_real_host_procedure_cannot_invent_release_gates():
    plan = (ROOT / "tasks" / "real-host-qualification-plan.md").read_text(encoding="utf-8")
    checklist = (ROOT / "docs" / "release-checklist.md").read_text(encoding="utf-8")

    authority_rule = (
        "Only requirements in `docs/v4/host-smoke.json` may decide whether an N0-N8 "
        "product probe passes or fails."
    )
    diagnostic_rule = (
        "Procedure-only or diagnostic evidence may explain a verdict, but it cannot create a "
        "new product PASS/FAIL gate."
    )
    same_boundary_rule = (
        "Compare payload equality only at the same transport boundary; do not compare a prepared "
        "Host tool argument with Host-rendered child communication."
    )

    for text in (plan, checklist):
        assert authority_rule in text
        assert diagnostic_rule in text
        assert same_boundary_rule in text


def test_ai_and_runtime_docs_match_current_public_roles_and_child_ceiling():
    ai = (ROOT / "README_AI.md").read_text(encoding="utf-8")
    runtime = (ROOT / "docs" / "native-subagent-runtime.md").read_text(encoding="utf-8")
    for text in (ai, runtime):
        assert "Orchestrate" in text and "Doctor" in text
        assert "gpt-5.6-terra" in text
        assert "high" in text
        assert "managed children <= 4" in text
        assert "initial managed children <= 2" not in text
        assert "normal managed children <= 3" not in text


def test_repository_privacy_policy_is_not_tracked():
    assert not (ROOT / "PRIVACY.md").exists()
