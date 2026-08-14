from __future__ import annotations

from pathlib import Path
import sys

import pytest

from test_calibration_profiles import manifest, run, setup


def _owned_paths(evidence: Path) -> list[Path]:
    return [Path(item["path"]) for item in manifest(evidence)["profiles"]]


def _apply_external_environment_drift(home: Path) -> tuple[bytes, Path]:
    config = b'model = "cc-switch-updated"\nmodel_provider = "custom"\n'
    (home / "config.toml").write_bytes(config)
    cache_entry = home / "plugins" / "cache" / "external" / "state.json"
    cache_entry.parent.mkdir(parents=True, exist_ok=True)
    cache_entry.write_text('{"state":"external"}\n', encoding="utf-8")
    return config, cache_entry


def test_cleanup_preserves_environment_drift_that_predates_cleanup(tmp_path: Path):
    evidence, home, campaign, _ = setup(tmp_path)
    assert run(evidence, home, campaign, "create").returncode == 0
    owned_paths = _owned_paths(evidence)
    changed_config, cache_entry = _apply_external_environment_drift(home)

    cleanup = run(evidence, home, campaign, "cleanup")

    assert cleanup.returncode == 0, cleanup.stderr
    assert all(not path.exists() for path in owned_paths)
    assert all(item["status"] == "CLEANED" for item in manifest(evidence)["profiles"])
    assert (home / "config.toml").read_bytes() == changed_config
    assert cache_entry.read_text(encoding="utf-8") == '{"state":"external"}\n'


def test_unexpected_third_calibration_profile_blocks_cleanup_before_owned_deletion(
    tmp_path: Path,
):
    evidence, home, campaign, _ = setup(tmp_path)
    assert run(evidence, home, campaign, "create").returncode == 0
    owned_paths = _owned_paths(evidence)
    extra = home / "agents" / "subagents_dispatch_calibration_external.toml"
    extra.write_text(
        'name="external-calibration"\ndescription="keep"\ndeveloper_instructions="keep"\n',
        encoding="utf-8",
    )

    cleanup = run(evidence, home, campaign, "cleanup")

    assert cleanup.returncode != 0
    assert "unexpected third calibration profile blocks cleanup" in cleanup.stderr
    assert all(path.exists() for path in owned_paths)
    assert all(item["status"] == "COMMITTED" for item in manifest(evidence)["profiles"])
    assert extra.exists()


def test_recover_preserves_preexisting_environment_drift_after_partial_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    evidence, home, campaign, _ = setup(tmp_path)
    assert run(evidence, home, campaign, "create").returncode == 0
    changed_config, cache_entry = _apply_external_environment_drift(home)

    monkeypatch.setenv(
        "SUBAGENTS_DISPATCH_CALIBRATION_CRASH_AT",
        "after_profile_candidate_cleanup_unlink",
    )
    crashed = run(evidence, home, campaign, "cleanup")
    assert crashed.returncode == 86
    monkeypatch.delenv("SUBAGENTS_DISPATCH_CALIBRATION_CRASH_AT")

    recovered = run(evidence, home, campaign, "recover")

    assert recovered.returncode == 0, recovered.stderr
    assert all(item["status"] == "CLEANED" for item in manifest(evidence)["profiles"])
    assert list((home / "agents").glob("subagents_dispatch_calibration_*.toml")) == []
    assert (home / "config.toml").read_bytes() == changed_config
    assert cache_entry.read_text(encoding="utf-8") == '{"state":"external"}\n'


def test_cleanup_transaction_detects_environment_change_after_start(tmp_path: Path):
    evidence, home, campaign, _ = setup(tmp_path)
    assert run(evidence, home, campaign, "create").returncode == 0

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    try:
        import calibration_profiles as profiles
    finally:
        sys.path.pop(0)

    baseline = profiles._cleanup_transaction_baseline(home, manifest(evidence))
    (home / "config.toml").write_text(
        'model = "changed-during-cleanup"\nmodel_provider = "custom"\n',
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="config_sha256"):
        profiles._verify_environment_baseline(home, baseline, set())
