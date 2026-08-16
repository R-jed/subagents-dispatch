from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCTOR_SKILL = ROOT / "skills" / "doctor" / "SKILL.md"
INSTALL = ROOT / "docs" / "plugin-installation.md"
CHECK_HELPER = ROOT / "scripts" / "check-plugin-update.py"
UPDATE_HELPER = ROOT / "scripts" / "plugin_update.py"


def test_doctor_exposes_separate_check_update_and_update_paths():
    doctor = DOCTOR_SKILL.read_text(encoding="utf-8")
    install = INSTALL.read_text(encoding="utf-8")

    assert CHECK_HELPER.is_file()
    assert UPDATE_HELPER.is_file()
    for text in (doctor, install):
        assert "check-plugin-update.py" in text
        assert "does not" in text
    assert "plugin_update.py" in doctor
    assert "doctor.py --codex-home <active-codex-home> --update" in install
    assert "codex plugin marketplace upgrade subagents-dispatch" in install
    assert "must not run `codex plugin add`" in doctor
    assert "does not run `codex plugin add`" in install
    assert "never falls through into installing an update" in install


def test_update_check_is_not_described_as_ordinary_read_only_doctor():
    doctor = DOCTOR_SKILL.read_text(encoding="utf-8")
    install = INSTALL.read_text(encoding="utf-8")
    assert "explicit network/cache-refresh operation" in doctor
    assert "explicitly allows a network/cache refresh" in install
    assert "never refreshes the Marketplace during ordinary diagnosis" in doctor
    assert "Normal Doctor diagnosis does not run `codex plugin marketplace upgrade`" in install
