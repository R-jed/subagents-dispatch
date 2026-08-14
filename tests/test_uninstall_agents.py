from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install-agents.py"
UNINSTALLER = ROOT / "scripts" / "uninstall-agents.py"
POLICY = json.loads((ROOT / "contracts" / "policy.json").read_text(encoding="utf-8"))
PROFILE_FILES = tuple(spec["profile_file"] for spec in POLICY["roles"].values())
MANIFEST = ".subagents-dispatch-agents.json"
LOCK = ".subagents-dispatch-agents.lock"


def run(script: Path, home: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), "--codex-home", str(home), *extra],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def install(home: Path) -> None:
    result = run(INSTALLER, home)
    assert result.returncode == 0, result.stdout + result.stderr


def test_uninstall_removes_only_exact_owned_profiles_and_manifest(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    unrelated = home / "agents" / "my-agent.toml"
    unrelated.write_text('name = "my_agent"\nmodel = "custom"\n', encoding="utf-8")
    before = unrelated.read_bytes()

    result = run(UNINSTALLER, home)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "UNINSTALL COMPLETE" in result.stdout
    assert all(not (home / "agents" / filename).exists() for filename in PROFILE_FILES)
    assert not (home / MANIFEST).exists()
    assert (home / LOCK).is_file()
    assert unrelated.read_bytes() == before


def test_modified_owned_profile_blocks_entire_uninstall(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    modified = home / "agents" / PROFILE_FILES[2]
    modified.write_bytes(modified.read_bytes() + b"\n# user change\n")
    before = {filename: (home / "agents" / filename).read_bytes() for filename in PROFILE_FILES}
    manifest_before = (home / MANIFEST).read_bytes()

    result = run(UNINSTALLER, home)

    assert result.returncode != 0
    assert "changed after the ownership manifest was written" in result.stderr
    assert {filename: (home / "agents" / filename).read_bytes() for filename in PROFILE_FILES} == before
    assert (home / MANIFEST).read_bytes() == manifest_before


def test_reserved_paths_without_manifest_are_not_claimed_or_deleted(tmp_path: Path):
    home = tmp_path / "codex-home"
    agents = home / "agents"
    agents.mkdir(parents=True)
    target = agents / PROFILE_FILES[0]
    target.write_text('name = "user_owned"\n', encoding="utf-8")
    before = target.read_bytes()

    result = run(UNINSTALLER, home)

    assert result.returncode != 0
    assert "ownership metadata is missing" in result.stderr
    assert target.read_bytes() == before
    assert not (home / MANIFEST).exists()


def test_uninstall_can_finish_after_one_owned_profile_is_already_missing(tmp_path: Path):
    home = tmp_path / "codex-home"
    install(home)
    missing = home / "agents" / PROFILE_FILES[0]
    missing.unlink()

    result = run(UNINSTALLER, home)

    assert result.returncode == 0, result.stdout + result.stderr
    assert all(not (home / "agents" / filename).exists() for filename in PROFILE_FILES)
    assert not (home / MANIFEST).exists()


def test_uninstall_of_absent_install_is_non_mutating(tmp_path: Path):
    missing_home = tmp_path / "missing"
    result = run(UNINSTALLER, missing_home)
    assert result.returncode == 0
    assert "not installed; no changes made" in result.stdout
    assert not missing_home.exists()

    unrelated_home = tmp_path / "unrelated-home"
    (unrelated_home / "agents").mkdir(parents=True)
    unrelated = unrelated_home / "agents" / "other.toml"
    unrelated.write_text('name = "other"\n', encoding="utf-8")
    before = unrelated.read_bytes()
    result = run(UNINSTALLER, unrelated_home)
    assert result.returncode == 0
    assert unrelated.read_bytes() == before
    assert not (unrelated_home / LOCK).exists()
