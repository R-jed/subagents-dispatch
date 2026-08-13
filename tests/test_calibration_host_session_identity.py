from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import calibration_profiles_core as core  # noqa: E402
sys.path.pop(0)

TASK_ID = "019ffd2d-2c2e-7330-9c22-1e5868987b9f"
OTHER_ID = "11111111-1111-4111-8111-111111111111"


def session_meta(thread_id: str) -> dict:
    return {"type": "session_meta", "payload": {"id": thread_id}}


def turn_context() -> dict:
    return {"type": "turn_context", "payload": {"model": "test"}}


def host_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    records: list[dict],
) -> tuple[Path, Path]:
    codex_home = tmp_path / ".codex"
    sessions = codex_home / "sessions" / "2026" / "08" / "14"
    sessions.mkdir(parents=True)
    rollout = sessions / f"rollout-test-{TASK_ID}.jsonl"
    raw = "".join(json.dumps(record) + "\n" for record in records).encode("utf-8")
    rollout.write_bytes(raw)
    evidence = tmp_path / "host-home-evidence.json"
    evidence.write_text(
        json.dumps(
            {
                "active_codex_home": str(codex_home),
                "provisioning_rollout_path": str(rollout),
                "provisioning_rollout_sha256": hashlib.sha256(raw).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(core, "_normal_codex_home", lambda: codex_home.resolve())
    return codex_home.resolve(), evidence


def validate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    records: list[dict],
) -> dict[str, str]:
    codex_home, evidence = host_evidence(tmp_path, monkeypatch, records)
    return core._host_home_identity(
        codex_home,
        evidence,
        TASK_ID,
        require_active_task=False,
    )


def test_duplicate_canonical_session_meta_is_valid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    result = validate(
        tmp_path,
        monkeypatch,
        [session_meta(TASK_ID), turn_context(), session_meta(TASK_ID), turn_context()],
    )
    assert result["active_codex_home"].endswith(".codex")


def test_later_different_session_meta_does_not_redefine_canonical_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    validate(
        tmp_path,
        monkeypatch,
        [session_meta(TASK_ID), turn_context(), session_meta(OTHER_ID), turn_context()],
    )


def test_wrong_first_session_meta_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    with pytest.raises(SystemExit, match="does not identify the preparation task"):
        validate(
            tmp_path,
            monkeypatch,
            [session_meta(OTHER_ID), turn_context(), session_meta(TASK_ID)],
        )


def test_missing_session_meta_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    with pytest.raises(SystemExit, match="does not identify the preparation task"):
        validate(tmp_path, monkeypatch, [turn_context()])


def test_missing_turn_context_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    with pytest.raises(SystemExit, match="does not identify the preparation task"):
        validate(tmp_path, monkeypatch, [session_meta(TASK_ID), session_meta(TASK_ID)])


def test_malformed_session_meta_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    with pytest.raises(SystemExit, match="session_meta is incomplete"):
        validate(
            tmp_path,
            monkeypatch,
            [{"type": "session_meta", "payload": {}}, turn_context()],
        )
