from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load_storage():
    sys.path.insert(0, str(SCRIPTS))
    try:
        spec = importlib.util.spec_from_file_location("state_storage_under_test", SCRIPTS / "state_storage.py")
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPTS))


def test_thread_identity_and_path_boundary_are_schema_neutral(tmp_path: Path):
    storage = load_storage()
    path = storage.state_path("thread-1", temp_root=tmp_path)
    assert path == tmp_path / "subagents-dispatch" / "thread-1" / "active.json"
    for invalid in ["", ".", "..", "a/b", "a\\b", " space", "x" * 129]:
        with pytest.raises(storage.StateIdentityError):
            storage.state_path(invalid, temp_root=tmp_path)


def test_lock_and_atomic_write_are_private(tmp_path: Path):
    storage = load_storage()
    with storage.state_lock("thread-1", temp_root=tmp_path):
        _, _, path, lock = storage._paths("thread-1", tmp_path, create=True)
        storage._write_unlocked(path, json.dumps({"schema_version": "test"}).encode())
        if os.name != "nt":
            assert path.stat().st_mode & 0o777 == 0o600
            assert lock.stat().st_mode & 0o777 == 0o600
        with pytest.raises(storage.StateLockError, match="locked"):
            with storage.state_lock("thread-1", temp_root=tmp_path, blocking=False):
                pass
    assert not list(path.parent.glob(".active.*.tmp"))


def test_forbidden_persisted_content_is_rejected_independent_of_schema():
    storage = load_storage()
    with pytest.raises(storage.StatePayloadError, match="forbidden persisted field"):
        storage._reject_forbidden_persisted_fields(
            {"safe": [{"raw_transcript": "private child output"}]}
        )


@pytest.mark.skipif(os.name == "nt", reason="symlink creation is not guaranteed on Windows")
def test_symlinked_state_root_is_rejected(tmp_path: Path):
    storage = load_storage()
    outside = tmp_path / "outside"
    outside.mkdir()
    dispatch_root = tmp_path / "subagents-dispatch"
    dispatch_root.symlink_to(outside, target_is_directory=True)
    with pytest.raises(storage.StatePathError, match="symlink"):
        with storage.state_lock("thread-1", temp_root=tmp_path):
            pass
