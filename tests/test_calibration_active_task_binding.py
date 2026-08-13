from __future__ import annotations

import json
import hashlib
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import calibration_profiles as profiles  # noqa: E402
sys.path.pop(0)

@pytest.fixture(autouse=True)
def isolated_nonce_receipts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(
        profiles, "ACTIVE_TASK_NONCE_RECEIPT_ROOT", tmp_path / "nonce-receipts"
    )


def test_exposed_matching_thread_id_uses_hardened_validator(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    expected = {"validated": "host-home"}
    calls = []
    monkeypatch.setenv("CODEX_THREAD_ID", "task-1")
    monkeypatch.setattr(
        profiles,
        "_legacy_host_home_identity",
        lambda *args, **kwargs: calls.append((*args, kwargs)) or expected,
    )

    result = profiles._host_home_identity(
        tmp_path, tmp_path / "evidence.json", "task-1", require_active_task=True
    )

    assert result == expected
    assert calls == [
        (
            tmp_path,
            tmp_path / "evidence.json",
            "task-1",
            {"require_active_task": False},
        )
    ]


def test_exposed_mismatching_thread_id_fails_before_nonce_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.setenv("CODEX_THREAD_ID", "different-task")
    monkeypatch.setenv(profiles.ACTIVE_TASK_NONCE_ENV, "a" * 64)
    monkeypatch.setattr(
        profiles,
        "_legacy_host_home_identity",
        lambda *args, **kwargs: pytest.fail("legacy validator must not run"),
    )

    with pytest.raises(SystemExit, match="does not match"):
        profiles._host_home_identity(
            tmp_path, tmp_path / "evidence.json", "task-1", require_active_task=True
        )


@pytest.mark.parametrize("nonce", [None, "", "a" * 63, "A" * 64, "g" * 64])
def test_missing_thread_id_rejects_absent_or_malformed_nonce(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, nonce: str | None
):
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    if nonce is None:
        monkeypatch.delenv(profiles.ACTIVE_TASK_NONCE_ENV, raising=False)
    else:
        monkeypatch.setenv(profiles.ACTIVE_TASK_NONCE_ENV, nonce)

    with pytest.raises(SystemExit, match="nonce"):
        profiles._host_home_identity(
            tmp_path, tmp_path / "evidence.json", "task-1", require_active_task=True
        )


def _evidence(tmp_path: Path, records: list[dict]) -> Path:
    rollout = tmp_path / "rollout-task-1.jsonl"
    rollout.write_text(
        "".join(json.dumps(record) + "\n" for record in records), encoding="utf-8"
    )
    evidence = tmp_path / "evidence.json"
    evidence.write_text(
        json.dumps({"provisioning_rollout_path": str(rollout)}), encoding="utf-8"
    )
    return evidence


@pytest.mark.parametrize(
    "record",
    [
        {"command": "calibration_profiles.py create"},
        {"command": f"{'b' * 64} calibration_profiles.py check"},
    ],
)
def test_nonce_fallback_requires_all_markers_in_one_record(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, record: dict
):
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.setenv(profiles.ACTIVE_TASK_NONCE_ENV, "b" * 64)
    evidence = _evidence(tmp_path, [record])

    with pytest.raises(SystemExit, match="nonce"):
        profiles._host_home_identity(
            tmp_path, evidence, "task-1", require_active_task=True
        )


def test_nonce_fallback_requires_markers_in_the_same_record(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    nonce = "b" * 64
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.setenv(profiles.ACTIVE_TASK_NONCE_ENV, nonce)
    evidence = _evidence(
        tmp_path,
        [
            {"command": f"{nonce} calibration_profiles.py"},
            {"command": "create"},
        ],
    )

    with pytest.raises(SystemExit, match="nonce"):
        profiles._host_home_identity(
            tmp_path, evidence, "task-1", require_active_task=True
        )


def test_nonce_fallback_delegates_to_hardened_validator(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    nonce = "c" * 64
    expected = {"validated": "host-home"}
    calls = []
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.setenv(profiles.ACTIVE_TASK_NONCE_ENV, nonce)
    evidence = _evidence(
        tmp_path, [{"command": f"{nonce} calibration_profiles.py create"}]
    )
    rollout = Path(json.loads(evidence.read_text())["provisioning_rollout_path"])
    expected = {
        "validated": "host-home",
        "provisioning_rollout_path": str(rollout.resolve()),
        "provisioning_rollout_sha256": hashlib.sha256(rollout.read_bytes()).hexdigest(),
    }
    monkeypatch.setattr(
        profiles,
        "_legacy_host_home_identity",
        lambda *args, **kwargs: calls.append((*args, kwargs)) or expected,
    )

    result = profiles._host_home_identity(
        tmp_path, evidence, "task-1", require_active_task=True
    )

    assert result == expected
    assert calls == [
        (tmp_path, evidence, "task-1", {"require_active_task": False})
    ]


def test_nonce_fallback_is_one_time(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    nonce = "f" * 64
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.setenv(profiles.ACTIVE_TASK_NONCE_ENV, nonce)
    evidence = _evidence(
        tmp_path, [{"command": f"{nonce} calibration_profiles.py create"}]
    )
    rollout = Path(json.loads(evidence.read_text())["provisioning_rollout_path"])
    validated = {
        "provisioning_rollout_path": str(rollout.resolve()),
        "provisioning_rollout_sha256": hashlib.sha256(rollout.read_bytes()).hexdigest(),
    }
    monkeypatch.setattr(
        profiles, "_legacy_host_home_identity", lambda *args, **kwargs: validated
    )

    profiles._host_home_identity(
        tmp_path, evidence, "task-1", require_active_task=True
    )
    with pytest.raises(SystemExit, match="already been used"):
        profiles._host_home_identity(
            tmp_path, evidence, "task-1", require_active_task=True
        )


def test_nonce_cannot_be_replayed_from_another_evidence_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    nonce = "2" * 64
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.setenv(profiles.ACTIVE_TASK_NONCE_ENV, nonce)
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    first_evidence = _evidence(
        first, [{"command": f"{nonce} calibration_profiles.py create"}]
    )
    second_evidence = second / "evidence.json"
    second_evidence.write_bytes(first_evidence.read_bytes())
    rollout = Path(json.loads(first_evidence.read_text())["provisioning_rollout_path"])
    validated = {
        "provisioning_rollout_path": str(rollout.resolve()),
        "provisioning_rollout_sha256": hashlib.sha256(rollout.read_bytes()).hexdigest(),
    }
    monkeypatch.setattr(
        profiles, "_legacy_host_home_identity", lambda *args, **kwargs: validated
    )

    profiles._host_home_identity(
        tmp_path, first_evidence, "task-1", require_active_task=True
    )
    with pytest.raises(SystemExit, match="already been used"):
        profiles._host_home_identity(
            tmp_path, second_evidence, "task-1", require_active_task=True
        )


def test_nonce_receipt_namespace_ignores_home_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    nonce = "3" * 64
    real_home = tmp_path / "account"
    real_home.mkdir()
    normal_codex_home = real_home / ".codex"
    monkeypatch.setattr(profiles, "ACTIVE_TASK_NONCE_RECEIPT_ROOT", None)
    monkeypatch.setattr(
        profiles._core, "_normal_codex_home", lambda: normal_codex_home
    )
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.setenv(profiles.ACTIVE_TASK_NONCE_ENV, nonce)
    evidence = _evidence(
        tmp_path, [{"command": f"{nonce} calibration_profiles.py create"}]
    )
    rollout = Path(json.loads(evidence.read_text())["provisioning_rollout_path"])
    validated = {
        "provisioning_rollout_path": str(rollout.resolve()),
        "provisioning_rollout_sha256": hashlib.sha256(rollout.read_bytes()).hexdigest(),
    }
    monkeypatch.setattr(
        profiles, "_legacy_host_home_identity", lambda *args, **kwargs: validated
    )

    monkeypatch.setenv("HOME", str(tmp_path / "override-a"))
    profiles._host_home_identity(
        tmp_path, evidence, "task-1", require_active_task=True
    )
    monkeypatch.setenv("HOME", str(tmp_path / "override-b"))
    with pytest.raises(SystemExit, match="already been used"):
        profiles._host_home_identity(
            tmp_path, evidence, "task-1", require_active_task=True
        )


def test_nonce_receipt_root_rejects_symlink(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    target = tmp_path / "target"
    target.mkdir()
    receipt_root = tmp_path / "receipt-root"
    try:
        receipt_root.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable")
    monkeypatch.setattr(profiles, "ACTIVE_TASK_NONCE_RECEIPT_ROOT", receipt_root)

    with pytest.raises(SystemExit, match="real directory"):
        profiles._consume_active_task_nonce(receipt_root, "4" * 64)


def test_windows_directory_lock_rejects_invalid_handle(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    class Function:
        def __init__(self, result):
            self.result = result

        def __call__(self, *args):
            return self.result

    class Kernel32:
        CreateFileW = Function(profiles.wintypes.HANDLE(-1).value)
        CloseHandle = Function(1)

    monkeypatch.setattr(
        profiles.ctypes,
        "windll",
        type("Windll", (), {"kernel32": Kernel32()})(),
        raising=False,
    )
    with pytest.raises(SystemExit, match="could not lock"):
        profiles._open_windows_directory_handle(tmp_path)


def test_nonce_fallback_rejects_evidence_switch_after_scan(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    nonce = "1" * 64
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.setenv(profiles.ACTIVE_TASK_NONCE_ENV, nonce)
    evidence = _evidence(
        tmp_path, [{"command": f"{nonce} calibration_profiles.py create"}]
    )
    other = tmp_path / "other.jsonl"
    other.write_text("other\n", encoding="utf-8")

    def switch_evidence(*args, **kwargs):
        evidence.write_text(
            json.dumps({"provisioning_rollout_path": str(other)}), encoding="utf-8"
        )
        return {
            "provisioning_rollout_path": str(other.resolve()),
            "provisioning_rollout_sha256": hashlib.sha256(other.read_bytes()).hexdigest(),
        }

    monkeypatch.setattr(profiles, "_legacy_host_home_identity", switch_evidence)
    with pytest.raises(SystemExit, match="same rollout"):
        profiles._host_home_identity(
            tmp_path, evidence, "task-1", require_active_task=True
        )


def test_rollout_scan_opens_in_binary_mode(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    path = tmp_path / "rollout.jsonl"
    path.write_bytes(b"exact bytes")
    seen = []
    real_open = profiles.os.open
    binary = 0x8000

    def recording_open(path, flags, *args):
        seen.append(flags)
        return real_open(path, flags & ~binary, *args)

    monkeypatch.setattr(profiles.os, "O_BINARY", binary, raising=False)
    monkeypatch.setattr(profiles.os, "open", recording_open)
    assert profiles._read_regular_bytes_without_following(path, "rollout") == b"exact bytes"
    assert seen[0] & binary


def test_nonce_fallback_does_not_hide_hardened_validation_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    nonce = "d" * 64
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.setenv(profiles.ACTIVE_TASK_NONCE_ENV, nonce)
    evidence = _evidence(
        tmp_path, [{"command": f"{nonce} calibration_profiles.py create"}]
    )

    def stale_sha(*args, **kwargs):
        profiles._core.fail("provisioning rollout evidence SHA256 does not match")

    monkeypatch.setattr(profiles, "_legacy_host_home_identity", stale_sha)
    with pytest.raises(SystemExit, match="SHA256 does not match"):
        profiles._host_home_identity(
            tmp_path, evidence, "task-1", require_active_task=True
        )


def test_non_create_operation_preserves_legacy_behavior_without_binding(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    expected = {"validated": "host-home"}
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.delenv(profiles.ACTIVE_TASK_NONCE_ENV, raising=False)
    monkeypatch.setattr(
        profiles, "_legacy_host_home_identity", lambda *args, **kwargs: expected
    )
    assert (
        profiles._host_home_identity(
            tmp_path, tmp_path / "evidence.json", "task-1", require_active_task=False
        )
        == expected
    )


def test_profile_create_without_thread_id_uses_rollout_bound_nonce(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    import test_calibration_profiles as lifecycle

    evidence, home, campaign, config = lifecycle.setup(tmp_path)
    unrelated = (home / "agents" / "unrelated.toml").read_bytes()
    nonce = "e" * 64
    sessions = home / "sessions" / "2026" / "08" / "13"
    sessions.mkdir(parents=True)
    rollout = sessions / "rollout-test-provisioning-task-1.jsonl"
    rollout.write_text(
        "\n".join(
            [
                json.dumps(
                    {"type": "session_meta", "payload": {"id": "provisioning-task-1"}}
                ),
                json.dumps({"type": "turn_context", "payload": {"model": "test"}}),
                json.dumps({"command": f"{nonce} calibration_profiles.py create"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    host_home = evidence / "host-home.json"
    host_home.write_text(
        json.dumps(
            {
                "active_codex_home": str(home),
                "provisioning_rollout_path": str(rollout),
                "provisioning_rollout_sha256": hashlib.sha256(
                    rollout.read_bytes()
                ).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.setenv(profiles.ACTIVE_TASK_NONCE_ENV, nonce)
    monkeypatch.setattr(profiles, "_normal_codex_home", lambda: home.resolve())
    monkeypatch.setattr(profiles._core, "_normal_codex_home", lambda: home.resolve())

    profiles._core.create(
        evidence, home, campaign, host_home, "provisioning-task-1"
    )

    owned = lifecycle.manifest(evidence)
    assert len(owned["profiles"]) == 2
    assert all(item["status"] == "COMMITTED" for item in owned["profiles"])
    assert (home / "config.toml").read_bytes() == config
    assert (home / "agents" / "unrelated.toml").read_bytes() == unrelated
