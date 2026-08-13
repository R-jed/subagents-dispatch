from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import calibration_profiles as profiles  # noqa: E402
sys.path.pop(0)


def test_environment_snapshot_hashes_regular_file_content(tmp_path: Path):
    root = tmp_path / "cache"
    root.mkdir()
    payload = root / "payload.txt"
    payload.write_text("alpha", encoding="utf-8")

    before = profiles._path_inventory(root)
    payload.write_text("beta", encoding="utf-8")
    after = profiles._path_inventory(root)

    assert before != after
    entry = next(item for item in before if item["path"] == "payload.txt")
    assert entry["type"] == "file"
    assert len(entry["sha256"]) == 64


@pytest.mark.skipif(os.name == "nt", reason="symlink creation is not guaranteed on Windows runners")
def test_environment_snapshot_records_symlink_without_following_it(tmp_path: Path):
    root = tmp_path / "cache"
    version = root / "openai-bundled" / "chrome" / "123"
    version.mkdir(parents=True)
    (version / "payload.txt").write_text("keep", encoding="utf-8")
    latest = version.parent / "latest"
    latest.symlink_to("123", target_is_directory=True)

    snapshot = profiles._path_inventory(root)

    link = next(item for item in snapshot if item["path"] == "openai-bundled/chrome/latest")
    assert link == {
        "path": "openai-bundled/chrome/latest",
        "type": "symlink",
        "target": "123",
    }
    assert all(item["path"] != "openai-bundled/chrome/latest/payload.txt" for item in snapshot)


@pytest.mark.skipif(os.name == "nt", reason="symlink creation is not guaranteed on Windows runners")
def test_environment_snapshot_detects_symlink_target_change(tmp_path: Path):
    root = tmp_path / "cache"
    chrome = root / "openai-bundled" / "chrome"
    (chrome / "123").mkdir(parents=True)
    (chrome / "124").mkdir()
    latest = chrome / "latest"
    latest.symlink_to("123", target_is_directory=True)

    before = profiles._path_inventory(root)
    latest.unlink()
    latest.symlink_to("124", target_is_directory=True)
    after = profiles._path_inventory(root)

    assert before != after


def test_environment_snapshot_manifest_schema_is_current():
    assert profiles.MANIFEST_SCHEMA == 5
    assert profiles._core.MANIFEST_SCHEMA == 5
