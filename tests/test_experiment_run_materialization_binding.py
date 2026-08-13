from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import test_experiment_run as experiment


@pytest.fixture(autouse=True)
def normal_home_is_test_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(experiment.VALIDATOR.Path, "home", lambda: tmp_path)


def prepared_calibration(tmp_path: Path) -> tuple[dict, dict, Path, Path]:
    campaign = experiment.calibration_campaign()
    run = experiment.calibration_run(campaign)
    result = experiment.validate(tmp_path, campaign, run)
    assert result["run_valid"] is True
    manifest_path = Path(run["materialization_manifest_ref"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rollout = Path(manifest["host_home_identity"]["provisioning_rollout_path"])
    return campaign, run, manifest_path, rollout


def test_run_validator_accepts_later_host_append_after_frozen_snapshot(tmp_path: Path):
    campaign, run, _, rollout = prepared_calibration(tmp_path)
    with rollout.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"type": "turn_context", "payload": {"model": "later"}}) + "\n")

    result = experiment.VALIDATOR.validate_run(
        run, experiment.write_campaign(tmp_path, campaign)
    )

    assert result["run_valid"] is True


def test_run_validator_keeps_first_session_meta_as_canonical_identity(tmp_path: Path):
    campaign, run, _, rollout = prepared_calibration(tmp_path)
    with rollout.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {"type": "session_meta", "payload": {"id": "provisioning-task-1"}}
            )
            + "\n"
        )
        handle.write(
            json.dumps(
                {"type": "session_meta", "payload": {"id": "embedded-source-task"}}
            )
            + "\n"
        )
        handle.write(json.dumps({"type": "turn_context", "payload": {"model": "later"}}) + "\n")

    result = experiment.VALIDATOR.validate_run(
        run, experiment.write_campaign(tmp_path, campaign)
    )

    assert result["run_valid"] is True


def test_run_validator_rejects_mutated_frozen_prefix(tmp_path: Path):
    campaign, run, _, rollout = prepared_calibration(tmp_path)
    raw = rollout.read_bytes()
    assert b'"model": "test"' in raw
    rollout.write_bytes(raw.replace(b'"model": "test"', b'"model": "rest"', 1))

    with pytest.raises(SystemExit, match="frozen provisioning rollout prefix"):
        experiment.VALIDATOR.validate_run(
            run, experiment.write_campaign(tmp_path, campaign)
        )


def test_run_validator_rejects_truncated_frozen_prefix(tmp_path: Path):
    campaign, run, _, rollout = prepared_calibration(tmp_path)
    lines = rollout.read_bytes().splitlines(keepends=True)
    assert len(lines) >= 2
    rollout.write_bytes(b"".join(lines[:-1]))

    with pytest.raises(SystemExit, match="frozen provisioning rollout prefix"):
        experiment.VALIDATOR.validate_run(
            run, experiment.write_campaign(tmp_path, campaign)
        )


def test_run_validator_rejects_stale_materialization_schema(tmp_path: Path):
    campaign, run, manifest_path, _ = prepared_calibration(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["schema_version"] = experiment.VALIDATOR.CALIBRATION_MANIFEST_SCHEMA - 1
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(SystemExit, match="does not match the frozen campaign"):
        experiment.VALIDATOR.validate_run(
            run, experiment.write_campaign(tmp_path, campaign)
        )


def test_frozen_prefix_hash_matches_only_complete_jsonl_record_boundary(tmp_path: Path):
    rollout = tmp_path / "rollout.jsonl"
    first = json.dumps({"type": "session_meta", "payload": {"id": "task"}}).encode("utf-8") + b"\n"
    second = json.dumps({"type": "turn_context", "payload": {"model": "test"}}).encode("utf-8") + b"\n"
    rollout.write_bytes(first + second)

    expected = hashlib.sha256(first).hexdigest()
    raw = experiment.VALIDATOR.verified_frozen_jsonl_prefix(rollout, expected)

    assert raw == first + second


def test_frozen_prefix_rejects_incomplete_trailing_jsonl_record(tmp_path: Path):
    rollout = tmp_path / "rollout.jsonl"
    first = json.dumps({"type": "session_meta", "payload": {"id": "task"}}).encode("utf-8") + b"\n"
    rollout.write_bytes(first + b'{"type":"turn_context"')

    with pytest.raises(SystemExit, match="incomplete trailing JSONL record"):
        experiment.VALIDATOR.verified_frozen_jsonl_prefix(
            rollout, hashlib.sha256(first).hexdigest()
        )
