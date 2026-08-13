from __future__ import annotations

import hashlib
import copy
from pathlib import Path
import sys
import tomllib

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import calibration_config_transaction as tx  # noqa: E402
sys.path.pop(0)

CANDIDATE = "d" * 40
SOURCE = Path("/exact/source")
requires_atomic_exchange = pytest.mark.skipif(
    not tx.atomic_exchange_supported(),
    reason="platform lacks the atomic path exchange required by shared-config mutation",
)


def record(tmp_path: Path) -> tuple[Path, dict]:
    config = tmp_path / "config.toml"
    config.write_text('model="keep"\n[features]\nkeep=true\n')
    return config, tx.new_record(
        config, ["marketplaces", "temporary"], SOURCE, "campaign", CANDIDATE
    )


def test_unsupported_atomic_exchange_refuses_before_shared_config_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    config, item = record(tmp_path)
    original = config.read_bytes()
    persisted = False
    monkeypatch.setattr(tx.sys, "platform", "win32")
    assert tx.atomic_exchange_supported() is False

    def persist() -> None:
        nonlocal persisted
        persisted = True

    with pytest.raises(SystemExit, match="lacks atomic path exchange"):
        tx.apply(item, persist)
    with pytest.raises(SystemExit, match="lacks atomic path exchange"):
        tx.cleanup(item, persist)

    assert config.read_bytes() == original
    assert persisted is False
    assert item["status"] == "PREPARED"
    assert "exchange_identity" not in item
    assert not Path(item["exchange_path"]).exists()
    assert not Path(item["cleanup_exchange_path"]).exists()


@requires_atomic_exchange
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


@requires_atomic_exchange
def test_shared_config_conflict_and_symlink_fail_closed(tmp_path: Path):
    config, item = record(tmp_path)
    tx.apply(item, lambda: None)
    tx.commit(item, lambda: None)
    config.write_text(config.read_text().replace(str(SOURCE), "/external"))
    with pytest.raises(SystemExit, match="externally modified"):
        tx.cleanup(item, lambda: None)


def test_symlinked_shared_config_fails_closed_without_exchange(tmp_path: Path):
    config = tmp_path / "config.toml"
    target = tmp_path / "target.toml"
    target.write_text('model="keep"\n')
    config.symlink_to(target)
    with pytest.raises(SystemExit, match="symlinked shared config"):
        tx._read_config(config)


def test_prepared_intent_binds_exact_semantics_and_candidate(tmp_path: Path):
    config, item = record(tmp_path)
    assert item["status"] == "PREPARED"
    assert item["pre_state"] == {"exists": False}
    assert item["expected_applied_state"] == {"source": str(SOURCE)}
    assert item["semantic_path"] == ["marketplaces", "temporary"]
    assert item["config_sha256_before"] == hashlib.sha256(config.read_bytes()).hexdigest()
    assert item["rollback_operation"] == "remove_exact_semantic_table"
    assert not any("file" in key and "sha256" not in key for key in item)
    tx.validate_record(item, "campaign", CANDIDATE)


@requires_atomic_exchange
def test_cleanup_rejects_atomic_target_substitution_even_with_identical_semantics(tmp_path: Path):
    config, item = record(tmp_path)
    tx.apply(item, lambda: None)
    tx.commit(item, lambda: None)
    replacement = tmp_path / "replacement.toml"
    replacement.write_bytes(config.read_bytes())
    replacement.replace(config)
    with pytest.raises(SystemExit, match="identity changed"):
        tx.cleanup(item, lambda: None)
    assert tomllib.loads(config.read_text())["marketplaces"]["temporary"] == {
        "source": str(SOURCE)
    }


@requires_atomic_exchange
def test_prepared_external_identical_write_is_preserved_as_conflict(tmp_path: Path):
    config, item = record(tmp_path)
    config.write_bytes(tx._add_table(config.read_bytes(), item["semantic_path"], item["expected_applied_state"]))
    with pytest.raises(SystemExit, match="appeared after PREPARED"):
        tx.apply(item, lambda: None)
    assert tomllib.loads(config.read_text())["marketplaces"]["temporary"] == item["expected_applied_state"]


def test_malformed_duplicate_and_unrelated_marketplace_changes_fail_or_preserve(tmp_path: Path):
    config = tmp_path / "config.toml"
    config.write_text("[broken\n")
    with pytest.raises(SystemExit, match="malformed"):
        tx.new_record(config, ["marketplaces", "temporary"], Path("/exact/source"), "campaign", CANDIDATE)

    config.write_text('[marketplaces.temporary]\nsource="/exact/source"\n')
    with pytest.raises(SystemExit, match="pre-existing"):
        tx.new_record(config, ["marketplaces", "temporary"], Path("/exact/source"), "campaign", CANDIDATE)


@requires_atomic_exchange
def test_cleanup_preserves_provider_and_unrelated_marketplaces(tmp_path: Path):
    config, item = record(tmp_path)
    tx.apply(item, lambda: None)
    tx.commit(item, lambda: None)
    config.write_text(config.read_text().replace('model="keep"', 'model="cc-switch"') + '\n[marketplaces.keep]\nsource="/keep"\n')
    tx.cleanup(item, lambda: None)
    parsed = tomllib.loads(config.read_text())
    assert parsed["model"] == "cc-switch"
    assert parsed["marketplaces"]["keep"] == {"source": "/keep"}


@requires_atomic_exchange
def test_true_write_before_applied_persistence_remains_unresolved_and_preserved(tmp_path: Path):
    config, item = record(tmp_path)
    durable: dict = {}
    def persist() -> None:
        if item["status"] == "APPLIED":
            raise RuntimeError("persist failed")
        durable.clear()
        durable.update(__import__("copy").deepcopy(item))
    with pytest.raises(RuntimeError, match="persist failed"):
        tx.apply(item, persist)
    tx.apply(durable, lambda: None)
    assert durable["status"] == "APPLIED"
    assert tomllib.loads(config.read_text())["marketplaces"]["temporary"] == item["expected_applied_state"]


@requires_atomic_exchange
def test_prepared_stage_persisted_before_exchange_resumes_exact_write(tmp_path: Path):
    config, item = record(tmp_path)
    durable: dict = {}

    def crash_after_stage() -> None:
        durable.clear()
        durable.update(copy.deepcopy(item))
        if "exchange_identity" in item:
            raise RuntimeError("crash before exchange")

    with pytest.raises(RuntimeError, match="crash before exchange"):
        tx.apply(item, crash_after_stage)
    assert "marketplaces" not in tomllib.loads(config.read_text())
    tx.apply(durable, lambda: None)
    assert durable["status"] == "APPLIED"
    assert tomllib.loads(config.read_text())["marketplaces"]["temporary"] == durable[
        "expected_applied_state"
    ]


@requires_atomic_exchange
def test_applied_commit_cleanup_and_repeated_cleanup_are_idempotent(tmp_path: Path):
    config, item = record(tmp_path)
    statuses: list[str] = []
    tx.apply(item, lambda: statuses.append(item["status"]))
    assert item["status"] == "APPLIED"
    tx.commit(item, lambda: statuses.append(item["status"]))
    assert item["status"] == "COMMITTED"
    tx.cleanup(item, lambda: statuses.append(item["status"]))
    tx.cleanup(item, lambda: statuses.append(item["status"]))
    assert item["status"] == "CLEANED"
    assert statuses == [
        "PREPARED", "APPLIED", "COMMITTED", "CLEANUP_PENDING",
        "CLEANUP_PENDING", "CLEANED",
    ]
    assert "marketplaces" not in tomllib.loads(config.read_text())


@requires_atomic_exchange
def test_owned_table_already_removed_is_recorded_without_touching_unrelated_state(tmp_path: Path):
    config, item = record(tmp_path)
    tx.apply(item, lambda: None)
    tx.commit(item, lambda: None)
    raw = config.read_bytes()
    replacement = tmp_path / "external.toml"
    replacement.write_bytes(
        tx._remove_table(raw, item["semantic_path"]) + b'\n[user]\nkeep=true\n'
    )
    replacement.replace(config)
    new_identity = (config.stat().st_dev, config.stat().st_ino)
    item["target_identity"] = {"device": new_identity[0], "inode": new_identity[1]}
    tx.cleanup(item, lambda: None)
    assert item["cleanup_result"] == "already_absent"
    assert tomllib.loads(config.read_text())["user"]["keep"] is True


@requires_atomic_exchange
def test_cleanup_interruption_after_pending_recovers_exactly(tmp_path: Path):
    config, item = record(tmp_path)
    tx.apply(item, lambda: None)
    tx.commit(item, lambda: None)
    calls = 0
    def fail_first() -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("interrupted")
    with pytest.raises(RuntimeError, match="interrupted"):
        tx.cleanup(item, fail_first)
    assert item["status"] == "CLEANUP_PENDING"
    tx.cleanup(item, lambda: None)
    assert item["status"] == "CLEANED"
    assert "marketplaces" not in tomllib.loads(config.read_text())


@requires_atomic_exchange
def test_apply_toctou_substitution_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    config, item = record(tmp_path)
    original = tx._atomic_replace
    def substitute(
        path: Path,
        raw: bytes,
        identity: tuple[int, int],
        expected: bytes,
        exchange: Path,
        exchange_identity: tuple[int, int] | None,
        persist_exchange_identity,
    ):
        replacement = tmp_path / "toctou.toml"
        replacement.write_bytes(expected)
        replacement.replace(path)
        return original(
            path, raw, identity, expected, exchange, exchange_identity,
            persist_exchange_identity,
        )
    monkeypatch.setattr(tx, "_atomic_replace", substitute)
    with pytest.raises(SystemExit, match="identity changed"):
        tx.apply(item, lambda: None)


@requires_atomic_exchange
def test_atomic_exchange_detects_change_after_final_validation_and_preserves_both_states(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    config, item = record(tmp_path)
    exchange = tx._atomic_exchange
    changed = config.read_bytes() + b'\n[malformed\n'
    called = False
    def race(first: Path, second: Path) -> None:
        nonlocal called
        if not called:
            called = True
            second.write_bytes(changed)
        exchange(first, second)
    monkeypatch.setattr(tx, "_atomic_exchange", race)
    with pytest.raises(SystemExit, match="changed during atomic write"):
        tx.apply(item, lambda: None)
    assert tomllib.loads(config.read_text())["marketplaces"]["temporary"] == item[
        "expected_applied_state"
    ]
    assert Path(item["exchange_path"]).read_bytes() == changed


@requires_atomic_exchange
def test_atomic_exchange_detects_live_path_substitution_without_deleting_external_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    config, item = record(tmp_path)
    exchange = tx._atomic_exchange
    external = b'external="keep"\n'

    def substitute_live_path(first: Path, second: Path) -> None:
        exchange(first, second)
        second.unlink()
        second.write_bytes(external)

    monkeypatch.setattr(tx, "_atomic_exchange", substitute_live_path)
    with pytest.raises(SystemExit, match="changed during atomic write"):
        tx.apply(item, lambda: None)
    assert config.read_bytes() == external
    assert Path(item["exchange_path"]).read_bytes() == b'model="keep"\n[features]\nkeep=true\n'


@requires_atomic_exchange
def test_post_exchange_live_substitution_is_never_claimed_owned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    config, item = record(tmp_path)
    exchange = tx._atomic_exchange
    external = tx._add_table(
        b'external="keep"\n', item["semantic_path"], item["expected_applied_state"]
    )

    def substitute_after_exchange(first: Path, second: Path) -> None:
        exchange(first, second)
        second.unlink()
        second.write_bytes(external)

    monkeypatch.setattr(tx, "_atomic_exchange", substitute_after_exchange)
    with pytest.raises(SystemExit, match="changed during atomic write"):
        tx.apply(item, lambda: None)
    assert config.read_bytes() == external
    assert item["target_identity"] != {
        "device": config.stat().st_dev, "inode": config.stat().st_ino
    }


@requires_atomic_exchange
def test_missing_retained_exchange_evidence_blocks_cleanup(tmp_path: Path):
    config, item = record(tmp_path)
    tx.apply(item, lambda: None)
    tx.commit(item, lambda: None)
    Path(item["exchange_path"]).unlink()
    with pytest.raises(SystemExit, match="evidence is missing"):
        tx.cleanup(item, lambda: None)
    assert tomllib.loads(config.read_text())["marketplaces"]["temporary"] == item[
        "expected_applied_state"
    ]


@requires_atomic_exchange
def test_in_place_retained_evidence_change_blocks_cleanup(tmp_path: Path):
    config, item = record(tmp_path)
    tx.apply(item, lambda: None)
    tx.commit(item, lambda: None)
    exchange = Path(item["exchange_path"])
    exchange.write_bytes(b"changed in place")
    with pytest.raises(SystemExit, match="evidence content changed"):
        tx.cleanup(item, lambda: None)
    assert tomllib.loads(config.read_text())["marketplaces"]["temporary"] == item[
        "expected_applied_state"
    ]


@requires_atomic_exchange
def test_short_stage_write_is_completed_before_exchange(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    config, item = record(tmp_path)
    write = tx.os.write
    first = True

    def short_write(fd: int, raw) -> int:
        nonlocal first
        if first and len(raw) > 1:
            first = False
            return write(fd, raw[: len(raw) // 2])
        return write(fd, raw)

    monkeypatch.setattr(tx.os, "write", short_write)
    tx.apply(item, lambda: None)
    assert item["status"] == "APPLIED"
    assert tomllib.loads(config.read_text())["marketplaces"]["temporary"] == item[
        "expected_applied_state"
    ]


@requires_atomic_exchange
def test_late_retained_evidence_substitution_blocks_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    config, item = record(tmp_path)
    tx.apply(item, lambda: None)
    tx.commit(item, lambda: None)
    exchange = Path(item["exchange_path"])
    external = b"external replacement"
    read_raw = tx._read_raw

    def substitute_after_validation(path: Path):
        result = read_raw(path)
        if Path(path) == exchange:
            exchange.unlink()
            exchange.write_bytes(external)
        return result

    monkeypatch.setattr(tx, "_read_raw", substitute_after_validation)
    with pytest.raises(SystemExit, match="exchange evidence .*changed|exchange evidence changed"):
        tx.cleanup(item, lambda: None)
    assert exchange.read_bytes() == external
    assert tomllib.loads(config.read_text())["marketplaces"]["temporary"] == item[
        "expected_applied_state"
    ]


@requires_atomic_exchange
def test_live_path_pre_exchange_substitution_is_preserved_and_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    config, item = record(tmp_path)
    external = b'external="keep"\n'
    exchange = tx._atomic_exchange

    def substitute_before_exchange(first: Path, second: Path) -> None:
        second.unlink()
        second.write_bytes(external)
        exchange(first, second)

    monkeypatch.setattr(tx, "_atomic_exchange", substitute_before_exchange)
    with pytest.raises(SystemExit, match="changed during atomic write"):
        tx.apply(item, lambda: None)
    assert Path(item["exchange_path"]).read_bytes() == external
    assert tomllib.loads(config.read_text())["marketplaces"]["temporary"] == item[
        "expected_applied_state"
    ]


@requires_atomic_exchange
def test_success_cleanup_never_path_unlinks_external_exchange_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    config, item = record(tmp_path)
    exchange = tx._atomic_exchange
    external = b"external replacement"

    def replace_after_exchange(first: Path, second: Path) -> None:
        exchange(first, second)
        first.unlink()
        first.write_bytes(external)

    monkeypatch.setattr(tx, "_atomic_exchange", replace_after_exchange)
    with pytest.raises(SystemExit, match="changed during atomic write"):
        tx.apply(item, lambda: None)
    assert Path(item["exchange_path"]).read_bytes() == external
    assert tomllib.loads(config.read_text())["marketplaces"]["temporary"] == item[
        "expected_applied_state"
    ]
    assert Path(item["exchange_path"]).read_bytes() == external


@requires_atomic_exchange
def test_failed_exchange_preserves_durable_stage_for_remediation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    config, item = record(tmp_path)
    monkeypatch.setattr(
        tx, "_atomic_exchange", lambda *_: (_ for _ in ()).throw(RuntimeError("exchange failed"))
    )
    with pytest.raises(RuntimeError, match="exchange failed"):
        tx.apply(item, lambda: None)
    exchange = Path(item["exchange_path"])
    assert exchange.exists()
    assert config.read_text() == 'model="keep"\n[features]\nkeep=true\n'
    with pytest.raises(RuntimeError, match="exchange failed"):
        tx.apply(item, lambda: None)


@requires_atomic_exchange
def test_pre_exchange_crash_discards_staged_candidate_without_touching_original(tmp_path: Path):
    config, item = record(tmp_path)
    original = config.read_bytes()
    exchange = Path(item["exchange_path"])
    exchange.write_bytes(tx._add_table(original, item["semantic_path"], item["expected_applied_state"]))
    with pytest.raises(SystemExit, match="exchange evidence changed"):
        tx.apply(item, lambda: None)
    assert config.read_bytes() == original
    assert exchange.exists()


@requires_atomic_exchange
def test_pre_exchange_crash_preserves_externally_replaced_exchange_path(tmp_path: Path):
    config, item = record(tmp_path)
    original = config.read_bytes()
    exchange = Path(item["exchange_path"])
    exchange.write_bytes(b"external replacement")
    with pytest.raises(SystemExit, match="exchange evidence changed"):
        tx.apply(item, lambda: None)
    assert config.read_bytes() == original
    assert exchange.read_bytes() == b"external replacement"


@requires_atomic_exchange
def test_pre_exchange_recovery_toctou_preserves_external_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    config, item = record(tmp_path)
    exchange = Path(item["exchange_path"])
    exchange.write_bytes(tx._add_table(
        config.read_bytes(), item["semantic_path"], item["expected_applied_state"]
    ))
    real_stat = tx.os.stat
    calls = 0
    def substitute(path, *args, **kwargs):
        nonlocal calls
        if Path(path) == exchange:
            calls += 1
            if calls == 1:
                exchange.unlink()
                exchange.write_bytes(b"external replacement")
        return real_stat(path, *args, **kwargs)
    monkeypatch.setattr(tx.os, "stat", substitute)
    with pytest.raises(SystemExit, match="exchange evidence changed"):
        tx.apply(item, lambda: None)
    assert exchange.read_bytes() == b"external replacement"


def test_tampered_exchange_authority_cannot_delete_unrelated_file(tmp_path: Path):
    _, item = record(tmp_path)
    unrelated = tmp_path / "unrelated"
    unrelated.write_bytes(b"keep")
    item["exchange_path"] = str(unrelated)
    item["exchange_candidate_sha256"] = hashlib.sha256(unrelated.read_bytes()).hexdigest()
    with pytest.raises(SystemExit, match="exchange path drifted"):
        tx.validate_record(item, "campaign", CANDIDATE)
    assert unrelated.read_bytes() == b"keep"


@requires_atomic_exchange
def test_cleanup_pre_exchange_crash_discards_valid_cleaned_stage_and_retries(tmp_path: Path):
    config, item = record(tmp_path)
    tx.apply(item, lambda: None)
    tx.commit(item, lambda: None)
    raw = config.read_bytes()
    cleaned = tx._remove_table(raw, item["semantic_path"])
    item["cleanup_expected_sha256"] = hashlib.sha256(cleaned).hexdigest()
    item["status"] = "CLEANUP_PENDING"
    cleanup_exchange = Path(item["cleanup_exchange_path"])
    cleanup_exchange.write_bytes(cleaned)
    with pytest.raises(SystemExit, match="exchange evidence changed"):
        tx.cleanup(item, lambda: None)
    assert item["status"] == "CLEANUP_PENDING"
    assert tomllib.loads(config.read_text())["marketplaces"]["temporary"] == item[
        "expected_applied_state"
    ]
    assert cleanup_exchange.read_bytes() == cleaned


@requires_atomic_exchange
def test_cleanup_stage_identity_persisted_before_write_resumes(tmp_path: Path):
    config, item = record(tmp_path)
    tx.apply(item, lambda: None)
    tx.commit(item, lambda: None)
    durable: dict = {}

    def crash_after_stage_identity() -> None:
        durable.clear()
        durable.update(copy.deepcopy(item))
        if "cleanup_exchange_identity" in item:
            raise RuntimeError("crash before cleanup stage write")

    with pytest.raises(RuntimeError, match="crash before cleanup stage write"):
        tx.cleanup(item, crash_after_stage_identity)
    assert Path(durable["cleanup_exchange_path"]).read_bytes() == b""
    tx.cleanup(durable, lambda: None)
    assert durable["status"] == "CLEANED"
    assert "marketplaces" not in tomllib.loads(config.read_text())


@requires_atomic_exchange
def test_cleanup_crash_after_mutation_recovers_to_cleaned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    config, item = record(tmp_path)
    durable: dict = {}

    def persist() -> None:
        durable.clear()
        durable.update(copy.deepcopy(item))

    tx.apply(item, persist)
    tx.commit(item, persist)
    def crash(boundary: str) -> None:
        if boundary == "after_cleanup_mutation":
            raise RuntimeError("crash")
    monkeypatch.setattr(tx, "_crash_at", crash)
    with pytest.raises(RuntimeError, match="crash"):
        tx.cleanup(item, persist)
    recovered = copy.deepcopy(durable)
    assert recovered["status"] == "CLEANUP_PENDING"
    monkeypatch.setattr(tx, "_crash_at", lambda _: None)
    tx.cleanup(recovered, lambda: None)
    assert recovered["status"] == "CLEANED"
    assert "marketplaces" not in tomllib.loads(config.read_text())


@requires_atomic_exchange
def test_cleanup_recovery_detects_live_replacement_after_evidence_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    config, item = record(tmp_path)
    durable: dict = {}

    def persist() -> None:
        durable.clear()
        durable.update(copy.deepcopy(item))

    tx.apply(item, persist)
    tx.commit(item, persist)
    monkeypatch.setattr(
        tx,
        "_crash_at",
        lambda boundary: (_ for _ in ()).throw(RuntimeError("crash"))
        if boundary == "after_cleanup_mutation"
        else None,
    )
    with pytest.raises(RuntimeError, match="crash"):
        tx.cleanup(item, persist)
    recovered = copy.deepcopy(durable)
    evidence = Path(recovered["cleanup_exchange_path"])
    read_raw = tx._read_raw
    external = tx._add_table(
        b'external="keep"\n', recovered["semantic_path"], recovered["expected_applied_state"]
    )

    def replace_live_after_evidence(path: Path):
        result = read_raw(path)
        if path == evidence:
            replacement = tmp_path / "external.toml"
            replacement.write_bytes(external)
            replacement.replace(config)
        return result

    monkeypatch.setattr(tx, "_read_raw", replace_live_after_evidence)
    monkeypatch.setattr(tx, "_crash_at", lambda _: None)
    with pytest.raises(SystemExit, match="changed during cleanup recovery"):
        tx.cleanup(recovered, lambda: None)
    assert config.read_bytes() == external
    assert recovered["status"] == "CLEANUP_PENDING"


def test_validate_record_rejects_tampered_authority(tmp_path: Path):
    _, item = record(tmp_path)
    for field, value in [
        ("candidate_sha", "e" * 40),
        ("transaction_id", "0" * 64),
        ("semantic_path", ["marketplaces", "other"]),
        ("rollback_operation", "restore_whole_file"),
    ]:
        tampered = {**item, field: value}
        with pytest.raises(SystemExit):
            tx.validate_record(tampered, "campaign", CANDIDATE)
