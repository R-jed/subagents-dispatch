from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install-agents.py"


def load_installer():
    scripts_dir = str(INSTALLER.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("subagents_dispatch_installer_no_clobber", INSTALLER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_missing_profile_late_create_is_never_clobbered(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    installer = load_installer()
    home = tmp_path / "codex-home"
    agents_dir = home / "agents"
    target = agents_dir / installer.PROFILE_FILES[0]
    external = b'name = "external_owner"\nmodel = "custom"\n'
    original_stage = installer.stage_file
    injected = False

    def stage_then_claim(directory: Path, data: bytes) -> Path:
        nonlocal injected
        staged = original_stage(directory, data)
        if not injected and Path(directory) == agents_dir:
            target.write_bytes(external)
            injected = True
        return staged

    monkeypatch.setattr(installer, "stage_file", stage_then_claim)

    with pytest.raises(RuntimeError, match="appeared after preflight"):
        installer.install(home, False)

    assert injected
    assert target.read_bytes() == external
    assert not (home / installer.MANIFEST_NAME).exists()


def test_owned_upgrade_revalidates_hash_after_staging(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    installer = load_installer()
    home = tmp_path / "codex-home"
    installer.install(home, False)

    filename = installer.PROFILE_FILES[1]
    target = home / "agents" / filename
    previous = target.read_bytes() + b"\n# previous managed generation\n"
    target.write_bytes(previous)
    manifest_path = home / installer.MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["profile_hashes"][filename] = installer.sha256_bytes(previous)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    previous_manifest = manifest_path.read_bytes()
    late_drift = previous + b"# external late drift\n"
    original_stage = installer.stage_file
    injected = False

    def stage_then_drift(directory: Path, data: bytes) -> Path:
        nonlocal injected
        staged = original_stage(directory, data)
        if not injected and Path(directory) == target.parent:
            target.write_bytes(late_drift)
            injected = True
        return staged

    monkeypatch.setattr(installer, "stage_file", stage_then_drift)

    with pytest.raises(SystemExit, match="changed after preflight"):
        installer.install(home, False)

    assert injected
    assert target.read_bytes() == late_drift
    assert manifest_path.read_bytes() == previous_manifest


def test_upgrade_publish_race_preserves_external_target_and_rollback_copy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    installer = load_installer()
    home = tmp_path / "codex-home"
    installer.install(home, False)

    filename = installer.PROFILE_FILES[1]
    target = home / "agents" / filename
    previous = target.read_bytes() + b"\n# previous managed generation\n"
    target.write_bytes(previous)
    manifest_path = home / installer.MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["profile_hashes"][filename] = installer.sha256_bytes(previous)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    external = b'name = "late_external_owner"\nmodel = "custom"\n'
    original_publish = installer.publish_staged_no_clobber
    injected = False

    def claim_before_publish(staged: Path, destination: Path) -> None:
        nonlocal injected
        if not injected and destination == target:
            destination.write_bytes(external)
            injected = True
        original_publish(staged, destination)

    monkeypatch.setattr(installer, "publish_staged_no_clobber", claim_before_publish)

    with pytest.raises(SystemExit, match="ROLLBACK INCOMPLETE"):
        installer.install(home, False)

    assert injected
    assert target.read_bytes() == external
    backups = list(target.parent.glob(f".{target.name}.backup-*"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == previous
