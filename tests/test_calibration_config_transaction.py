from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tomllib

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import calibration_config_transaction as tx  # noqa: E402
sys.path.pop(0)

CANDIDATE = "d" * 40


def record(tmp_path: Path) -> tuple[Path, dict]:
    config = tmp_path / "config.toml"
    config.write_text('model="keep"\n[features]\nkeep=true\n')
    return config, tx.new_record(
        config, ["marketplaces", "temporary"], Path("/exact/source"), "campaign", CANDIDATE
    )


def test_shared_config_transaction_preserves_unrelated_changes_and_never_owns_whole_file(tmp_path: Path):
    config, item = record(tmp_path)
    persisted: list[str] = []
    tx.apply(item, lambda: persisted.append(item["status"]))
    tx.commit(item, lambda: persisted.append(item["status"]))
    raw = config.read_text()
    config.write_text(raw.replace('model="keep"', 'model="cc-switch"') + '\n[user]\nkeep=true\n')
    tx.cleanup(item, lambda: persisted.append(item["status"]))
    parsed = tomllib.loads(config.read_text())
    assert parsed["model"] == "cc-switch"
    assert parsed["features"]["keep"] is True
    assert parsed["user"]["keep"] is True
    assert "marketplaces" not in parsed
    assert item["rollback_operation"] == "remove_exact_semantic_table"
    assert not any("file" in key and "sha256" not in key for key in item)


def test_shared_config_conflict_and_symlink_fail_closed(tmp_path: Path):
    config, item = record(tmp_path)
    tx.apply(item, lambda: None)
    tx.commit(item, lambda: None)
    config.write_text(config.read_text().replace("/exact/source", "/external"))
    with pytest.raises(SystemExit, match="externally modified"):
        tx.cleanup(item, lambda: None)
    target = tmp_path / "target.toml"
    target.write_text('model="keep"\n')
    config.unlink()
    config.symlink_to(target)
    with pytest.raises(SystemExit, match="symlinked shared config"):
        tx._read_config(config)


def test_prepared_intent_binds_exact_semantics_and_candidate(tmp_path: Path):
    config, item = record(tmp_path)
    assert item["status"] == "PREPARED"
    assert item["pre_state"] == {"exists": False}
    assert item["expected_applied_state"] == {"source": "/exact/source"}
    assert item["semantic_path"] == ["marketplaces", "temporary"]
    assert item["config_sha256_before"] == hashlib.sha256(config.read_bytes()).hexdigest()
    tx.validate_record(item, "campaign", CANDIDATE)
