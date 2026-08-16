from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
DOCTOR = ROOT / "scripts" / "doctor.py"


def run_doctor(home: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(
        [sys.executable, str(DOCTOR), "--codex-home", str(home), *args],
        cwd=ROOT,
        env=merged,
        text=True,
        capture_output=True,
        check=False,
    )


def test_update_is_exclusive_with_other_doctor_operations(tmp_path: Path):
    home = tmp_path / "codex-home"
    home.mkdir()
    before = sorted(path.relative_to(home).as_posix() for path in home.rglob("*"))

    result = run_doctor(home, "--update", "--check")

    assert result.returncode != 0
    assert "cannot be combined" in result.stderr
    after = sorted(path.relative_to(home).as_posix() for path in home.rglob("*"))
    assert after == before


def test_update_without_codex_cli_fails_without_mutating_codex_home(tmp_path: Path):
    home = tmp_path / "codex-home"
    home.mkdir()
    sentinel = home / "sentinel.txt"
    sentinel.write_text("keep\n", encoding="utf-8")
    before = {path.relative_to(home).as_posix(): path.read_bytes() for path in home.rglob("*") if path.is_file()}

    result = run_doctor(
        home,
        "--update",
        env={"SUBAGENTS_DISPATCH_CODEX_BIN": str(tmp_path / "definitely-missing-codex")},
    )

    assert result.returncode != 0
    assert "Codex CLI is unavailable" in result.stderr
    after = {path.relative_to(home).as_posix(): path.read_bytes() for path in home.rglob("*") if path.is_file()}
    assert after == before
