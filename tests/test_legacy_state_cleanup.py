from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load_modules():
    sys.path.insert(0, str(SCRIPTS))
    try:
        storage_spec = importlib.util.spec_from_file_location("legacy_storage", SCRIPTS / "state_storage.py")
        assert storage_spec and storage_spec.loader
        storage = importlib.util.module_from_spec(storage_spec)
        sys.modules[storage_spec.name] = storage
        storage_spec.loader.exec_module(storage)
        sys.modules["state_storage"] = storage
        cleanup_spec = importlib.util.spec_from_file_location(
            "legacy_cleanup_under_test", SCRIPTS / "legacy_state_cleanup.py"
        )
        assert cleanup_spec and cleanup_spec.loader
        cleanup = importlib.util.module_from_spec(cleanup_spec)
        sys.modules[cleanup_spec.name] = cleanup
        cleanup_spec.loader.exec_module(cleanup)
        return storage, cleanup
    finally:
        sys.path.remove(str(SCRIPTS))


def legacy_payload(thread_id: str, *, state: str = "CLOSED", pending=None, updated_at="2026-07-01T00:00:00Z"):
    return {
        "schema_version": "1.0",
        "root_thread_id": thread_id,
        "locale": "en",
        "created_at": updated_at,
        "updated_at": updated_at,
        "team_plan_revision": None,
        "units": [
            {
                "unit_id": "U1",
                "attempt": 1,
                "control_state": state,
            }
        ],
        "accounting_refs": [],
        "controls": [],
        "pending_takeover": pending,
    }


def write_payload(storage, tmp_path: Path, thread_id: str, payload: dict) -> None:
    encoded = json.dumps(payload, separators=(",", ":")).encode()
    with storage.state_lock(thread_id, temp_root=tmp_path):
        _, _, path, _ = storage._paths(thread_id, tmp_path, create=True)
        storage._write_unlocked(path, encoded)


def test_stale_terminal_v3_capsule_is_removed(tmp_path: Path):
    storage, cleanup = load_modules()
    write_payload(storage, tmp_path, "legacy-terminal", legacy_payload("legacy-terminal"))

    report = cleanup.cleanup_stale_states(
        temp_root=tmp_path, now="2026-08-21T00:00:00Z"
    )

    assert report["removed"] == ["legacy-terminal"]
    assert not storage.state_path("legacy-terminal", temp_root=tmp_path).exists()


def test_unresolved_or_pending_v3_capsule_is_retained(tmp_path: Path):
    storage, cleanup = load_modules()
    write_payload(
        storage,
        tmp_path,
        "legacy-running",
        legacy_payload("legacy-running", state="RUNNING"),
    )
    write_payload(
        storage,
        tmp_path,
        "legacy-takeover",
        legacy_payload(
            "legacy-takeover",
            pending={"unit_id": "U1", "status": "pending"},
        ),
    )

    report = cleanup.cleanup_stale_states(
        temp_root=tmp_path, now="2026-08-21T00:00:00Z"
    )

    assert report["retained_active"] == ["legacy-running", "legacy-takeover"]
    assert storage.state_path("legacy-running", temp_root=tmp_path).exists()
    assert storage.state_path("legacy-takeover", temp_root=tmp_path).exists()


def test_current_thread_and_v4_capsule_are_never_legacy-cleaned(tmp_path: Path):
    storage, cleanup = load_modules()
    write_payload(storage, tmp_path, "current-v3", legacy_payload("current-v3"))
    write_payload(
        storage,
        tmp_path,
        "native-v4",
        {
            "schema_version": "4.0",
            "root_session_id": "native-v4",
            "updated_at": "2026-07-01T00:00:00Z",
        },
    )

    report = cleanup.cleanup_stale_states(
        temp_root=tmp_path,
        active_thread_id="current-v3",
        now="2026-08-21T00:00:00Z",
    )

    assert report["current"] == ["current-v3"]
    assert report["nonlegacy"] == ["native-v4"]
    assert storage.state_path("current-v3", temp_root=tmp_path).exists()
    assert storage.state_path("native-v4", temp_root=tmp_path).exists()


def test_cleanup_rechecks_before_delete_and_preserves_changed_capsule(tmp_path: Path):
    storage, cleanup = load_modules()
    original = legacy_payload("legacy-race")
    write_payload(storage, tmp_path, "legacy-race", original)
    real_read = cleanup._read_payload
    reads = 0

    def refresh_on_second_read(*args, **kwargs):
        nonlocal reads
        reads += 1
        payload = real_read(*args, **kwargs)
        if reads == 2 and payload is not None:
            fresh = dict(payload)
            fresh["updated_at"] = "2026-08-21T00:00:00Z"
            write_payload(storage, tmp_path, "legacy-race", fresh)
            return fresh
        return payload

    cleanup._read_payload = refresh_on_second_read
    report = cleanup.cleanup_stale_states(
        temp_root=tmp_path, now="2026-08-21T00:00:01Z"
    )

    assert report["removed"] == []
    assert report["fresh"] == ["legacy-race"]
    assert storage.state_path("legacy-race", temp_root=tmp_path).exists()
