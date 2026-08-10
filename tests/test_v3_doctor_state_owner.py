from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCTOR = ROOT / "scripts" / "doctor.py"


def test_doctor_reuses_dispatch_state_temp_boundary_for_state_scanning():
    text = DOCTOR.read_text(encoding="utf-8")
    assert "_temporary_root," in text
    assert "_reject_symlink," in text
    assert "root_base = _temporary_root(temp_root)" in text

    start = text.index("def _state_entries")
    end = text.index("\ndef _unexpected_repository_state", start)
    helper = text[start:end]
    assert "tempfile.gettempdir()" not in helper
    assert "candidate.is_absolute()" not in helper
    assert "system_temp" not in helper
