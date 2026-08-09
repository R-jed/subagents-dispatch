"""Safety-critical migration tests for codex-delegate → subagents-dispatch."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install-agents.py"
DOCTOR = ROOT / "scripts" / "doctor.py"
PROFILE_SOURCE = ROOT / "agent-profiles"
POLICY = json.loads((ROOT / "contracts" / "policy.json").read_text(encoding="utf-8"))
CURRENT_FILES = tuple(spec["profile_file"] for spec in POLICY["roles"].values())
CURRENT_MANIFEST = ".subagents-dispatch-agents.json"
LEGACY_MANIFEST = ".codex-delegate-agents.json"
LEGACY_LOCK = ".codex-delegate-agents.lock"
LEGACY_PROFILE_FILES = (
    "codex-delegate-reader.toml",
    "codex-delegate-worker.toml",
    "codex-delegate-solver.toml",
    "codex-delegate-investigator.toml",
    "codex-delegate-advisor.toml",
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_installer(home: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(INSTALLER), "--codex-home", str(home), *extra],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def run_doctor(home: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(DOCTOR), "--codex-home", str(home), *extra],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def load_legacy_module():
    path = ROOT / "scripts" / "legacy_migration.py"
    spec = importlib.util.spec_from_file_location("subagents_dispatch_legacy", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def state(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }


def legacy_content(index: int) -> bytes:
    return (PROFILE_SOURCE / CURRENT_FILES[index]).read_bytes().replace(
        b"subagents_dispatch_", b"codex_delegate_"
    )


def create_legacy_installation(home: Path) -> dict[str, bytes]:
    agents_dir = home / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    contents: dict[str, bytes] = {}
    hashes: dict[str, str] = {}
    for index, filename in enumerate(LEGACY_PROFILE_FILES):
        data = legacy_content(index)
        (agents_dir / filename).write_bytes(data)
        contents[filename] = data
        hashes[filename] = sha(data)
    (home / LEGACY_MANIFEST).write_text(
        json.dumps(
            {"schema_version": 1, "managed_by": "codex-delegate", "profile_hashes": hashes},
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    (home / LEGACY_LOCK).write_bytes(b"\0")
    return contents


def without_current_lock(value: dict[str, bytes]) -> dict[str, bytes]:
    copy = dict(value)
    copy.pop(".subagents-dispatch-agents.lock", None)
    return copy


def test_clean_migration_is_exact_and_idempotent(tmp_path: Path):
    home = tmp_path / "codex-home"
    create_legacy_installation(home)
    result = run_installer(home, "--migrate-legacy")
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (home / LEGACY_MANIFEST).exists()
    assert (home / LEGACY_LOCK).exists()
    for filename in LEGACY_PROFILE_FILES:
        assert not (home / "agents" / filename).exists()
    check = run_installer(home, "--check")
    assert check.returncode == 0, check.stdout + check.stderr
    before = state(home)
    rerun = run_installer(home, "--migrate-legacy")
    assert rerun.returncode == 0, rerun.stdout + rerun.stderr
    assert state(home) == before


def test_modified_legacy_profile_has_stable_preserved_terminal_state(tmp_path: Path):
    home = tmp_path / "codex-home"
    contents = create_legacy_installation(home)
    modified_name = LEGACY_PROFILE_FILES[0]
    modified = contents[modified_name] + b"\n# user modification\n"
    (home / "agents" / modified_name).write_bytes(modified)

    result = run_installer(home, "--migrate-legacy")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (home / "agents" / modified_name).read_bytes() == modified
    assert (home / LEGACY_MANIFEST).exists(), "ownership evidence must be preserved"
    for filename in LEGACY_PROFILE_FILES[1:]:
        assert not (home / "agents" / filename).exists()
    assert "current_with_preserved_legacy_modified" in result.stdout

    doctor = run_doctor(home, "--legacy")
    assert doctor.returncode == 0
    assert "current_with_preserved_legacy_modified" in doctor.stdout
    assert "Do not repeat automatic migration" in doctor.stdout

    before = state(home)
    rerun = run_installer(home, "--migrate-legacy")
    assert rerun.returncode == 0, rerun.stdout + rerun.stderr
    assert state(home) == before


def test_corrupt_manifest_blocks_automatic_migration_without_mutation(tmp_path: Path):
    home = tmp_path / "codex-home"
    create_legacy_installation(home)
    (home / LEGACY_MANIFEST).write_text("{broken", encoding="utf-8")
    before = state(home)
    result = run_installer(home, "--migrate-legacy")
    assert result.returncode != 0
    assert "ownership metadata is missing, invalid, or unsafe" in (result.stdout + result.stderr)
    assert without_current_lock(state(home)) == before
    doctor = run_doctor(home, "--legacy")
    assert "legacy_ownership_unknown" in doctor.stdout
    assert "Automatic migration is blocked" in doctor.stdout


def test_missing_manifest_with_legacy_profiles_blocks_automatic_migration(tmp_path: Path):
    home = tmp_path / "codex-home"
    create_legacy_installation(home)
    (home / LEGACY_MANIFEST).unlink()
    before = state(home)
    result = run_installer(home, "--migrate-legacy")
    assert result.returncode != 0
    assert without_current_lock(state(home)) == before


def test_unowned_legacy_profile_is_preserved_with_manifest_evidence(tmp_path: Path):
    home = tmp_path / "codex-home"
    create_legacy_installation(home)
    manifest = json.loads((home / LEGACY_MANIFEST).read_text(encoding="utf-8"))
    extra_name = LEGACY_PROFILE_FILES[-1]
    manifest["profile_hashes"].pop(extra_name)
    (home / LEGACY_MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
    extra_bytes = (home / "agents" / extra_name).read_bytes()
    result = run_installer(home, "--migrate-legacy")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (home / "agents" / extra_name).read_bytes() == extra_bytes
    assert (home / LEGACY_MANIFEST).exists()
    doctor = run_doctor(home, "--legacy")
    assert "current_with_preserved_legacy" in doctor.stdout


def test_preserved_legacy_reserved_role_collision_fails_before_cleanup(tmp_path: Path):
    home = tmp_path / "codex-home"
    create_legacy_installation(home)
    target = home / "agents" / LEGACY_PROFILE_FILES[0]
    text = target.read_text(encoding="utf-8").replace(
        "codex_delegate_reader", "subagents_dispatch_reader"
    )
    target.write_text(text, encoding="utf-8")
    before = state(home)
    result = run_installer(home, "--migrate-legacy")
    assert result.returncode != 0
    assert "reserved current role name" in (result.stdout + result.stderr)
    assert without_current_lock(state(home)) == before


def test_cleanup_detects_snapshot_drift_before_deleting_anything(tmp_path: Path):
    home = tmp_path / "codex-home"
    create_legacy_installation(home)
    legacy = load_legacy_module()
    backup, _ = legacy.backup_legacy_files(home)
    target = home / "agents" / LEGACY_PROFILE_FILES[0]
    target.write_bytes(target.read_bytes() + b"\n# concurrent edit\n")
    before = state(home)
    with pytest.raises(RuntimeError, match="drift detected"):
        legacy.commit_legacy_cleanup(home, backup)
    assert state(home) == before


def test_partial_cleanup_failure_rolls_back_already_removed_files(tmp_path: Path, monkeypatch):
    home = tmp_path / "codex-home"
    create_legacy_installation(home)
    legacy = load_legacy_module()
    backup, _ = legacy.backup_legacy_files(home)
    before = state(home)
    real_remove = legacy.remove_legacy_target
    calls = 0

    def fail_second(path: Path):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise PermissionError("injected cleanup failure")
        real_remove(path)

    monkeypatch.setattr(legacy, "remove_legacy_target", fail_second)
    with pytest.raises(PermissionError, match="injected cleanup failure"):
        legacy.commit_legacy_cleanup(home, backup)
    assert state(home) == before


def test_current_install_failure_restores_legacy_cleanup(tmp_path: Path, monkeypatch):
    home = tmp_path / "codex-home"
    create_legacy_installation(home)
    before = state(home)
    scripts_dir = str(INSTALLER.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("subagents_dispatch_installer_migration", INSTALLER)
    assert spec and spec.loader
    installer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer)

    def fail_manifest(path, payload):
        raise RuntimeError("injected current install failure")

    monkeypatch.setattr(installer, "write_manifest", fail_manifest)
    with pytest.raises(RuntimeError, match="injected current install failure"):
        installer.install(home, False, True)
    after = state(home)
    for path, data in before.items():
        assert after.get(path) == data, f"legacy path was not restored: {path}"
    assert CURRENT_MANIFEST not in after


def test_legacy_manifest_symlink_fails_closed(tmp_path: Path):
    home = tmp_path / "codex-home"
    home.mkdir(parents=True)
    external = tmp_path / "external.json"
    external.write_text("{}", encoding="utf-8")
    try:
        (home / LEGACY_MANIFEST).symlink_to(external)
    except OSError:
        pytest.skip("symlink creation unavailable")
    before = external.read_bytes()
    result = run_installer(home, "--migrate-legacy")
    assert result.returncode != 0
    assert external.read_bytes() == before
