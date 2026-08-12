from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tomllib

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "calibration_profiles.py"


def load_module():
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("calibration_profiles", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.path.pop(0)
    return module


MODULE = load_module()


def campaign(tmp_path: Path) -> Path:
    initialized = subprocess.run(
        [sys.executable, str(SCRIPT), "init", "--evaluator-root", str(tmp_path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert initialized.returncode == 0, initialized.stderr
    sys.path.insert(0, str(ROOT / "tests"))
    try:
        from test_experiment_campaign import role_campaign

        payload = role_campaign()
    finally:
        sys.path.pop(0)
    path = tmp_path / "campaign.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def prepare_campaign(tmp_path: Path) -> Path:
    path = campaign(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    scripts = ROOT / "scripts"
    sys.path.insert(0, str(scripts))
    try:
        import calibration_profile_contract as contract
        import tomllib

        profile = tomllib.loads((ROOT / "agent-profiles" / "subagents-dispatch-reader.toml").read_text())
        digest = contract.role_contract_digest("reader", profile["description"], profile["developer_instructions"], "none")
        routes = [payload["experiment"]["roles"][0]["control"], *payload["experiment"]["roles"][0]["challengers"]]
        for route in routes:
            route.update(
                semantic_role="reader",
                configured_model=route["model"],
                configured_effort=route["effort"],
                materialized_agent_type=contract.materialized_agent_type(payload["campaign_id"], "reader", route["id"]),
                role_contract_digest=digest,
            )
    finally:
        sys.path.pop(0)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(tmp_path: Path, command: str, *, home: Path | None = None, campaign_path: Path | None = None):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir(exist_ok=True)
    home = home or evaluator / "isolated-codex"
    campaign_path = campaign_path or prepare_campaign(evaluator)
    config = evaluator / "config.toml"
    if not config.exists():
        config.write_text('model = "keep"\n', encoding="utf-8")
    marketplace = evaluator / "marketplace"
    plugin = marketplace / "plugins" / "subagents-dispatch"
    plugin.mkdir(parents=True, exist_ok=True)
    (plugin / ".codex-plugin").mkdir(exist_ok=True)
    (plugin / ".codex-plugin" / "plugin.json").write_text(
        '{"name":"subagents-dispatch","version":"3.0.0"}', encoding="utf-8"
    )
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            command,
            "--evaluator-root",
            str(evaluator),
            "--codex-home",
            str(home),
            "--campaign",
            str(campaign_path),
            "--shared-config",
            str(evaluator / "config.toml"),
            "--marketplace-source",
            str(evaluator / "marketplace"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_create_rejects_preexisting_identical_shared_marketplace(tmp_path: Path):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    source = evaluator / "marketplace"
    (source / "plugins" / "subagents-dispatch").mkdir(parents=True)
    payload = json.loads(path.read_text(encoding="utf-8"))
    marketplace = f"subagents-dispatch-v3-exact-{payload['plugin_candidate_sha'][:8]}"
    (evaluator / "config.toml").write_text(
        f'[marketplaces.{marketplace}]\nsource = "{source}"\n', encoding="utf-8"
    )
    result = run(tmp_path, "create", campaign_path=path)
    assert result.returncode != 0
    assert "pre-existing shared config object" in result.stderr


def test_failure_after_prepared_leaves_durable_intent_without_config_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    source = evaluator / "marketplace"
    (source / "plugins" / "subagents-dispatch").mkdir(parents=True)
    config = evaluator / "config.toml"
    config.write_text('model = "keep"\n', encoding="utf-8")
    monkeypatch.setenv("SUBAGENTS_DISPATCH_CALIBRATION_FAIL_AT", "after_prepared")
    result = run(tmp_path, "create", campaign_path=path)
    assert result.returncode != 0
    assert "marketplaces." not in config.read_text(encoding="utf-8")
    journal = json.loads(
        (evaluator / "isolated-codex" / ".subagents-dispatch-calibration.json").read_text(
            encoding="utf-8"
        )
    )
    assert journal["shared_config_mutations"][0]["status"] == "PREPARED"


def test_recover_preserves_identical_external_write_after_prepared(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    monkeypatch.setenv("SUBAGENTS_DISPATCH_CALIBRATION_FAIL_AT", "after_prepared")
    assert run(tmp_path, "create", campaign_path=path).returncode != 0
    monkeypatch.delenv("SUBAGENTS_DISPATCH_CALIBRATION_FAIL_AT")
    manifest = json.loads(
        (evaluator / "isolated-codex" / ".subagents-dispatch-calibration.json").read_text(
            encoding="utf-8"
        )
    )
    record = manifest["shared_config_mutations"][0]
    config = evaluator / "config.toml"
    config.write_bytes(
        MODULE.config_transaction._add_table(
            config.read_bytes(), record["semantic_path"], record["expected_applied_state"]
        )
    )

    recovered = run(tmp_path, "recover", campaign_path=path)
    assert recovered.returncode != 0
    assert "unresolved write attribution" in recovered.stderr
    parsed = tomllib.loads(config.read_text(encoding="utf-8"))
    assert MODULE.config_transaction._semantic_value(parsed, record["semantic_path"]) == record[
        "expected_applied_state"
    ]


def test_true_write_before_applied_remains_unresolved_and_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    monkeypatch.setenv("SUBAGENTS_DISPATCH_CALIBRATION_CRASH_AT", "after_config_mutation")
    assert run(tmp_path, "create", campaign_path=path).returncode == 86
    monkeypatch.delenv("SUBAGENTS_DISPATCH_CALIBRATION_CRASH_AT")
    config = evaluator / "config.toml"
    before = config.read_bytes()

    recovered = run(tmp_path, "recover", campaign_path=path)
    assert recovered.returncode != 0
    assert "unresolved write attribution" in recovered.stderr
    assert config.read_bytes() == before


def test_cleanup_preserves_cc_switch_and_unrelated_config_changes(tmp_path: Path):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    assert run(tmp_path, "create", campaign_path=path).returncode == 0
    config = evaluator / "config.toml"
    owned_table = config.read_text(encoding="utf-8").split("\n", 1)[1]
    config.write_text(
        'model = "cc-switch-model"\nmodel_provider = "cc-switch-provider"\n'
        + '[model_providers.cc-switch-provider]\nbase_url = "https://example.invalid"\n'
        + '[features]\nnew_feature = true\n'
        + '[projects."/unrelated"]\ntrust_level = "trusted"\n'
        + '[mcp_servers.unrelated]\ncommand = "keep"\n'
        + '[marketplaces.user-added]\nsource = "/unrelated"\n'
        + owned_table,
        encoding="utf-8",
    )
    cleaned = run(tmp_path, "cleanup", campaign_path=path)
    assert cleaned.returncode == 0, cleaned.stderr
    parsed = tomllib.loads(config.read_text(encoding="utf-8"))
    assert parsed["model"] == "cc-switch-model"
    assert parsed["model_provider"] == "cc-switch-provider"
    assert parsed["model_providers"]["cc-switch-provider"]["base_url"] == "https://example.invalid"
    assert parsed["features"]["new_feature"] is True
    assert parsed["projects"]["/unrelated"]["trust_level"] == "trusted"
    assert parsed["mcp_servers"]["unrelated"]["command"] == "keep"
    assert parsed["marketplaces"]["user-added"]["source"] == "/unrelated"
    assert all("subagents-dispatch-v3-exact" not in key for key in parsed["marketplaces"])


def test_recover_after_config_write_before_applied_preserves_unresolved_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    monkeypatch.setenv("SUBAGENTS_DISPATCH_CALIBRATION_CRASH_AT", "after_config_mutation")
    failed = run(tmp_path, "create", campaign_path=path)
    assert failed.returncode == 86
    monkeypatch.delenv("SUBAGENTS_DISPATCH_CALIBRATION_CRASH_AT")
    before = (evaluator / "config.toml").read_bytes()
    recovered = run(tmp_path, "recover", campaign_path=path)
    assert recovered.returncode != 0
    assert "unresolved write attribution" in recovered.stderr
    assert (evaluator / "config.toml").read_bytes() == before
    parsed = tomllib.loads((evaluator / "config.toml").read_text(encoding="utf-8"))
    assert "marketplaces" in parsed


@pytest.mark.parametrize(
    "boundary",
    ["after_applied", "after_committed", "after_cleanup_pending", "after_cleanup_mutation"],
)
def test_crash_boundaries_recover_idempotently(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, boundary: str
):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    if boundary.startswith("after_cleanup"):
        assert run(tmp_path, "create", campaign_path=path).returncode == 0
        command = "cleanup"
    else:
        command = "create"
    monkeypatch.setenv("SUBAGENTS_DISPATCH_CALIBRATION_CRASH_AT", boundary)
    crashed = run(tmp_path, command, campaign_path=path)
    assert crashed.returncode == 86
    monkeypatch.delenv("SUBAGENTS_DISPATCH_CALIBRATION_CRASH_AT")
    assert run(tmp_path, "recover", campaign_path=path).returncode == 0
    assert run(tmp_path, "recover", campaign_path=path).returncode == 0
    parsed = tomllib.loads((evaluator / "config.toml").read_text(encoding="utf-8"))
    assert all("subagents-dispatch-v3-exact" not in key for key in parsed.get("marketplaces", {}))


def test_cleanup_conflicts_when_owned_marketplace_changes(tmp_path: Path):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    assert run(tmp_path, "create", campaign_path=path).returncode == 0
    config = evaluator / "config.toml"
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            str(evaluator / "marketplace"), "/externally-modified"
        ),
        encoding="utf-8",
    )
    result = run(tmp_path, "cleanup", campaign_path=path)
    assert result.returncode != 0
    assert "externally modified" in result.stderr
    assert "/externally-modified" in config.read_text(encoding="utf-8")


def test_shared_config_symlink_is_rejected(tmp_path: Path):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    target = evaluator / "real.toml"
    target.write_text('model = "keep"\n', encoding="utf-8")
    (evaluator / "config.toml").symlink_to(target)
    result = run(tmp_path, "create", campaign_path=path)
    assert result.returncode != 0
    assert "symlinked shared config" in result.stderr


def test_malformed_shared_config_is_rejected_before_setup_and_cleanup(tmp_path: Path):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    config = evaluator / "config.toml"
    config.write_text("[broken", encoding="utf-8")
    assert run(tmp_path, "create", campaign_path=path).returncode != 0
    config.write_text('model = "keep"\n', encoding="utf-8")
    assert run(tmp_path, "create", campaign_path=path).returncode == 0
    config.write_text("[broken", encoding="utf-8")
    result = run(tmp_path, "cleanup", campaign_path=path)
    assert result.returncode != 0
    assert "malformed shared config" in result.stderr


def test_config_replaced_after_prepared_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    monkeypatch.setenv("SUBAGENTS_DISPATCH_CALIBRATION_FAIL_AT", "after_prepared")
    assert run(tmp_path, "create", campaign_path=path).returncode != 0
    monkeypatch.delenv("SUBAGENTS_DISPATCH_CALIBRATION_FAIL_AT")
    config = evaluator / "config.toml"
    replacement = evaluator / "replacement.toml"
    replacement.write_text(config.read_text(encoding="utf-8"), encoding="utf-8")
    replacement.replace(config)
    result = run(tmp_path, "create", campaign_path=path)
    assert result.returncode != 0
    assert "unresolved shared config transaction" in result.stderr
    recover = run(tmp_path, "recover", campaign_path=path)
    assert recover.returncode == 0, recover.stderr


def test_manifest_and_transaction_tampering_fail_closed(tmp_path: Path):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    assert run(tmp_path, "create", campaign_path=path).returncode == 0
    manifest = evaluator / "isolated-codex" / ".subagents-dispatch-calibration.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["shared_config_mutations"][0]["semantic_path"] = ["model"]
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    result = run(tmp_path, "cleanup", campaign_path=path)
    assert result.returncode != 0
    assert "semantic path" in result.stderr


@pytest.mark.parametrize("field", ["campaign_id", "candidate_sha", "transaction_id"])
def test_transaction_identity_tampering_fails_closed(tmp_path: Path, field: str):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    assert run(tmp_path, "create", campaign_path=path).returncode == 0
    manifest = evaluator / "isolated-codex" / ".subagents-dispatch-calibration.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["shared_config_mutations"][0][field] = "tampered"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    result = run(tmp_path, "cleanup", campaign_path=path)
    assert result.returncode != 0
    assert "mismatch" in result.stderr or "identity drifted" in result.stderr


def test_owned_entry_already_removed_cleanup_is_idempotent(tmp_path: Path):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    assert run(tmp_path, "create", campaign_path=path).returncode == 0
    config = evaluator / "config.toml"
    text = config.read_text(encoding="utf-8")
    config.write_text(text[: text.index("\n[marketplaces.")] + "\n", encoding="utf-8")
    first = run(tmp_path, "cleanup", campaign_path=path)
    second = run(tmp_path, "cleanup", campaign_path=path)
    assert first.returncode == second.returncode == 0


def test_cleanup_recovers_after_one_profile_was_already_removed(tmp_path: Path):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    home = evaluator / "isolated-codex"
    assert run(tmp_path, "create", home=home, campaign_path=path).returncode == 0
    sorted((home / "agents").glob("*.toml"))[0].unlink()
    result = run(tmp_path, "recover", home=home, campaign_path=path)
    assert result.returncode == 0, result.stderr
    assert list((home / "agents").glob("*.toml")) == []


def test_plugin_setup_failure_rolls_back_shared_config_and_profiles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    monkeypatch.setenv("SUBAGENTS_DISPATCH_CALIBRATION_FAIL_AT", "plugin_install")
    result = run(tmp_path, "create", campaign_path=path)
    assert result.returncode != 0
    parsed = tomllib.loads((evaluator / "config.toml").read_text(encoding="utf-8"))
    assert "marketplaces" not in parsed
    assert "plugins" not in parsed
    assert list((evaluator / "isolated-codex" / "agents").glob("*.toml")) == []


def test_check_rejects_orphaned_plugin_cache(tmp_path: Path):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    assert run(tmp_path, "create", campaign_path=path).returncode == 0
    manifest = json.loads(
        (evaluator / "isolated-codex" / ".subagents-dispatch-calibration.json").read_text(
            encoding="utf-8"
        )
    )
    cache = next(
        Path(item["path"])
        for item in manifest["owned_objects"]
        if item["object_type"] == "directory" and "/plugins/cache/" in item["path"]
    )
    import shutil

    shutil.rmtree(cache)
    checked = run(tmp_path, "check", campaign_path=path)
    assert checked.returncode != 0
    assert "filesystem ownership is incomplete" in checked.stderr


def test_directory_ownership_tampering_cannot_delete_unrelated_directory(tmp_path: Path):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    assert run(tmp_path, "create", campaign_path=path).returncode == 0
    unrelated = evaluator / "unrelated-directory"
    unrelated.mkdir()
    (unrelated / "keep").write_text("keep", encoding="utf-8")
    manifest = evaluator / "isolated-codex" / ".subagents-dispatch-calibration.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    next(item for item in payload["owned_objects"] if item["object_type"] == "directory")["path"] = str(unrelated)
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    result = run(tmp_path, "cleanup", campaign_path=path)
    assert result.returncode != 0
    assert (unrelated / "keep").read_text(encoding="utf-8") == "keep"


def test_modified_owned_directory_is_preserved_as_conflict(tmp_path: Path):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    assert run(tmp_path, "create", campaign_path=path).returncode == 0
    manifest = json.loads(
        (evaluator / "isolated-codex" / ".subagents-dispatch-calibration.json").read_text(
            encoding="utf-8"
        )
    )
    directory = Path(next(item for item in manifest["owned_objects"] if item["object_type"] == "directory")["path"])
    (directory / "externally-added").write_text("preserve", encoding="utf-8")
    result = run(tmp_path, "cleanup", campaign_path=path)
    assert result.returncode != 0
    assert (directory / "externally-added").read_text(encoding="utf-8") == "preserve"


def test_recover_after_directory_rename_before_identity_persistence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    monkeypatch.setenv("SUBAGENTS_DISPATCH_CALIBRATION_CRASH_AT", "after_directory_rename")
    crashed = run(tmp_path, "create", campaign_path=path)
    assert crashed.returncode == 86
    monkeypatch.delenv("SUBAGENTS_DISPATCH_CALIBRATION_CRASH_AT")
    recovered = run(tmp_path, "recover", campaign_path=path)
    assert recovered.returncode == 0, recovered.stderr
    manifest = json.loads(
        (evaluator / "isolated-codex" / ".subagents-dispatch-calibration.json").read_text(
            encoding="utf-8"
        )
    )
    assert all(
        not Path(item["path"]).exists()
        for item in manifest["owned_objects"]
        if item["object_type"] == "directory"
    )


def test_recover_rejects_same_content_directory_substitution_after_rename_crash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    monkeypatch.setenv("SUBAGENTS_DISPATCH_CALIBRATION_CRASH_AT", "after_directory_rename")
    assert run(tmp_path, "create", campaign_path=path).returncode == 86
    monkeypatch.delenv("SUBAGENTS_DISPATCH_CALIBRATION_CRASH_AT")

    manifest_path = evaluator / "isolated-codex" / ".subagents-dispatch-calibration.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    directory = next(
        Path(item["path"])
        for item in manifest["owned_objects"]
        if item["object_type"] == "directory" and Path(item["path"]).exists()
    )
    original = directory.with_name(f"{directory.name}.original")
    directory.rename(original)
    import shutil

    shutil.copytree(original, directory)
    replacement_inode = directory.stat().st_ino

    recovered = run(tmp_path, "recover", campaign_path=path)
    assert recovered.returncode != 0
    assert directory.exists()
    assert directory.stat().st_ino == replacement_inode


def test_preexisting_staging_directory_is_preserved(tmp_path: Path):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    candidate = json.loads(path.read_text(encoding="utf-8"))["plugin_candidate_sha"]
    staging = evaluator / "local-marketplaces" / f".subagents-dispatch-v3-exact-{candidate[:8]}.calibration-staging"
    staging.parent.mkdir()
    staging.mkdir()
    (staging / "keep").write_text("keep", encoding="utf-8")

    created = run(tmp_path, "create", campaign_path=path)
    assert created.returncode != 0
    assert (staging / "keep").read_text(encoding="utf-8") == "keep"


def test_recover_preserves_substituted_staging_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    monkeypatch.setenv("SUBAGENTS_DISPATCH_CALIBRATION_CRASH_AT", "after_staging_prepared")
    assert run(tmp_path, "create", campaign_path=path).returncode == 86
    monkeypatch.delenv("SUBAGENTS_DISPATCH_CALIBRATION_CRASH_AT")

    manifest_path = evaluator / "isolated-codex" / ".subagents-dispatch-calibration.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    staging = next(
        Path(item["staging_path"])
        for item in manifest["owned_objects"]
        if item["object_type"] == "directory" and Path(item["staging_path"]).exists()
    )
    original = staging.with_name(f"{staging.name}.original")
    staging.rename(original)
    staging.mkdir()
    (staging / "keep").write_text("keep", encoding="utf-8")

    recovered = run(tmp_path, "recover", campaign_path=path)
    assert recovered.returncode != 0
    assert (staging / "keep").read_text(encoding="utf-8") == "keep"


def test_crash_before_staging_identity_persistence_leaves_no_orphan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    candidate = json.loads(path.read_text(encoding="utf-8"))["plugin_candidate_sha"]
    staging = evaluator / "local-marketplaces" / f".subagents-dispatch-v3-exact-{candidate[:8]}.calibration-staging"
    monkeypatch.setenv("SUBAGENTS_DISPATCH_CALIBRATION_CRASH_AT", "after_staging_mkdir")
    assert run(tmp_path, "create", campaign_path=path).returncode == 86
    monkeypatch.delenv("SUBAGENTS_DISPATCH_CALIBRATION_CRASH_AT")
    for _ in range(100):
        if not staging.exists():
            break
        import time

        time.sleep(0.01)
    assert not staging.exists()


def test_directory_replacement_during_cleanup_is_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    assert run(tmp_path, "create", campaign_path=path).returncode == 0
    manifest = json.loads(
        (evaluator / "isolated-codex" / ".subagents-dispatch-calibration.json").read_text(
            encoding="utf-8"
        )
    )
    directory = Path(
        next(item for item in manifest["owned_objects"] if item["object_type"] == "directory")["path"]
    )
    original = directory.with_name(f"{directory.name}.external-original")
    real_digest = MODULE._tree_digest
    substituted = False

    def substitute_after_verification(target: Path):
        nonlocal substituted
        digest = real_digest(target)
        if target == directory and not substituted:
            target.rename(original)
            target.mkdir()
            (target / "keep").write_text("keep", encoding="utf-8")
            substituted = True
        return digest

    monkeypatch.setattr(MODULE, "_tree_digest", substitute_after_verification)
    item = next(item for item in manifest["owned_objects"] if item["path"] == str(directory))
    with pytest.raises(SystemExit):
        MODULE._remove_owned_directory(
            directory, item["device"], item["inode"], item["tree_sha256"]
        )
    assert (directory / "keep").read_text(encoding="utf-8") == "keep"
    assert original.exists()


def test_recover_after_cleanup_quarantine_rename_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    assert run(tmp_path, "create", campaign_path=path).returncode == 0
    monkeypatch.setenv("SUBAGENTS_DISPATCH_CALIBRATION_CRASH_AT", "after_cleanup_rename")
    assert run(tmp_path, "cleanup", campaign_path=path).returncode == 86
    monkeypatch.delenv("SUBAGENTS_DISPATCH_CALIBRATION_CRASH_AT")

    recovered = run(tmp_path, "recover", campaign_path=path)
    assert recovered.returncode == 0, recovered.stderr
    assert run(tmp_path, "recover", campaign_path=path).returncode == 0
    assert not list(evaluator.rglob("*.calibration-cleanup"))


def test_in_place_change_during_directory_cleanup_is_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    assert run(tmp_path, "create", campaign_path=path).returncode == 0
    manifest = json.loads(
        (evaluator / "isolated-codex" / ".subagents-dispatch-calibration.json").read_text(
            encoding="utf-8"
        )
    )
    item = next(item for item in manifest["owned_objects"] if item["object_type"] == "directory")
    directory = Path(item["path"])
    real_digest = MODULE._tree_digest
    calls = 0

    def modify_after_first_digest(target: Path):
        nonlocal calls
        digest = real_digest(target)
        calls += 1
        if calls == 1:
            (target / "external-change").write_text("preserve", encoding="utf-8")
        return digest

    monkeypatch.setattr(MODULE, "_tree_digest", modify_after_first_digest)
    with pytest.raises(SystemExit):
        MODULE._remove_owned_directory(
            directory, item["device"], item["inode"], item["tree_sha256"]
        )
    assert (directory / "external-change").read_text(encoding="utf-8") == "preserve"


def test_whole_file_rollback_authority_and_wildcards_are_prohibited(tmp_path: Path):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    assert run(tmp_path, "create", campaign_path=path).returncode == 0
    manifest = json.loads(
        (evaluator / "isolated-codex" / ".subagents-dispatch-calibration.json").read_text(
            encoding="utf-8"
        )
    )
    for mutation in manifest["shared_config_mutations"]:
        assert "config_contents" not in mutation
        assert "rollback_file" not in mutation
        assert mutation["pre_state"] == {"exists": False}
    assert [mutation["semantic_path"][0] for mutation in manifest["shared_config_mutations"]] == ["marketplaces", "plugins"]
    assert all("*" not in item["path"] for item in manifest["owned_objects"])


def test_create_check_cleanup_is_idempotent_and_preserves_unrelated(tmp_path: Path):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    home = evaluator / "isolated-codex"
    campaign_path = prepare_campaign(evaluator)
    unrelated = evaluator / "unrelated.txt"
    unrelated.write_text("keep", encoding="utf-8")

    created = run(tmp_path, "create", home=home, campaign_path=campaign_path)
    assert created.returncode == 0, created.stderr
    assert "RESTART_REQUIRED" in created.stdout
    created_again = run(tmp_path, "create", home=home, campaign_path=campaign_path)
    assert created_again.returncode == 0, created_again.stderr
    checked = run(tmp_path, "check", home=home, campaign_path=campaign_path)
    assert checked.returncode == 0, checked.stderr
    assert len(list((home / "agents").glob("*.toml"))) == 2
    cleaned = run(tmp_path, "cleanup", home=home, campaign_path=campaign_path)
    assert cleaned.returncode == 0, cleaned.stderr
    assert unrelated.read_text(encoding="utf-8") == "keep"
    assert not list((home / "agents").glob("*.toml"))
    assert (home / ".subagents-dispatch-calibration.lock").exists()


def test_create_rejects_production_or_escaping_root(tmp_path: Path):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    outside = tmp_path / "outside"
    outside.mkdir()
    escaped = run(tmp_path, "create", home=outside, campaign_path=path)
    assert escaped.returncode != 0
    assert "inside --evaluator-root" in escaped.stderr


def test_init_refuses_nonempty_unowned_evaluator_root(tmp_path: Path):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    (evaluator / "unrelated.txt").write_text("keep", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "init", "--evaluator-root", str(evaluator)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "non-empty evaluator root" in result.stderr


def test_create_rejects_symlinked_codex_home_and_agents_dir(tmp_path: Path):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    target = tmp_path / "real-home"
    target.mkdir()
    (evaluator / "linked-home").symlink_to(target, target_is_directory=True)
    result = run(tmp_path, "create", home=evaluator / "linked-home", campaign_path=path)
    assert result.returncode != 0
    assert "symlink" in result.stderr


def test_create_rejects_symlinked_intermediate_path_component(tmp_path: Path):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    real_parent = tmp_path / "real-parent"
    real_parent.mkdir()
    (evaluator / "linked-parent").symlink_to(real_parent, target_is_directory=True)
    result = run(tmp_path, "create", home=evaluator / "linked-parent" / "home", campaign_path=path)
    assert result.returncode != 0
    assert "path component" in result.stderr
    home = evaluator / "home"
    home.mkdir()
    (home / "agents-target").mkdir()
    (home / "agents").symlink_to(home / "agents-target", target_is_directory=True)
    result = run(tmp_path, "create", home=home, campaign_path=path)
    assert result.returncode != 0
    assert "symlink" in result.stderr


def test_cleanup_refuses_modified_owned_profile(tmp_path: Path):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    home = evaluator / "isolated-codex"
    path = prepare_campaign(evaluator)
    assert run(tmp_path, "create", home=home, campaign_path=path).returncode == 0
    profile = next((home / "agents").glob("*.toml"))
    profile.write_text(profile.read_text(encoding="utf-8") + "\n# drift\n", encoding="utf-8")
    result = run(tmp_path, "cleanup", home=home, campaign_path=path)
    assert result.returncode != 0
    assert "drifted" in result.stderr
    assert profile.exists()


def test_cleanup_refuses_symlinked_owned_profile_and_preserves_unrelated_agent(tmp_path: Path):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    home = evaluator / "isolated-codex"
    path = prepare_campaign(evaluator)
    assert run(tmp_path, "create", home=home, campaign_path=path).returncode == 0
    unrelated = home / "agents" / "user-owned.toml"
    unrelated.write_bytes(b'name = "user_owned"\n')
    owned = next((home / "agents").glob("*.toml"))
    backup = home / "backup.toml"
    backup.write_bytes(owned.read_bytes())
    owned.unlink()
    owned.symlink_to(backup)
    result = run(tmp_path, "cleanup", home=home, campaign_path=path)
    assert result.returncode != 0
    assert "symlink" in result.stderr
    assert unrelated.read_bytes() == b'name = "user_owned"\n'


@pytest.mark.parametrize("owned_state", ["missing", "duplicate_identity"])
def test_cleanup_and_create_fail_closed_for_owned_or_existing_identity_drift(
    tmp_path: Path, owned_state: str
):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    home = evaluator / "isolated-codex"
    path = prepare_campaign(evaluator)
    assert run(tmp_path, "create", home=home, campaign_path=path).returncode == 0
    owned = sorted((home / "agents").glob("*.toml"))[0]
    if owned_state == "missing":
        owned.unlink()
        result = run(tmp_path, "cleanup", home=home, campaign_path=path)
        assert result.returncode == 0, result.stderr
    else:
        duplicate = home / "agents" / "duplicate.toml"
        duplicate.write_bytes(owned.read_bytes())
        result = run(tmp_path, "check", home=home, campaign_path=path)
        assert result.returncode != 0
        assert "duplicate Agent identity" in result.stderr


def test_manifest_and_lock_symlinks_are_rejected(tmp_path: Path):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    home = evaluator / "isolated-codex"
    path = prepare_campaign(evaluator)
    assert run(tmp_path, "create", home=home, campaign_path=path).returncode == 0

    manifest = home / ".subagents-dispatch-calibration.json"
    manifest_backup = home / "manifest-backup.json"
    manifest_backup.write_bytes(manifest.read_bytes())
    manifest.unlink()
    manifest.symlink_to(manifest_backup)
    result = run(tmp_path, "check", home=home, campaign_path=path)
    assert result.returncode != 0
    assert "symlink" in result.stderr

    manifest.unlink()
    manifest.write_bytes(manifest_backup.read_bytes())
    lock = home / ".subagents-dispatch-calibration.lock"
    lock_backup = home / "lock-backup"
    lock_backup.write_bytes(lock.read_bytes())
    lock.unlink()
    lock.symlink_to(lock_backup)
    result = run(tmp_path, "check", home=home, campaign_path=path)
    assert result.returncode != 0
    assert "symlink" in result.stderr


def test_cleanup_rejects_manifest_injection_for_unrelated_profile(tmp_path: Path):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    home = evaluator / "isolated-codex"
    path = prepare_campaign(evaluator)
    assert run(tmp_path, "create", home=home, campaign_path=path).returncode == 0
    unrelated = home / "agents" / "unrelated.toml"
    unrelated_bytes = b'name = "unrelated"\n'
    unrelated.write_bytes(unrelated_bytes)
    manifest = home / ".subagents-dispatch-calibration.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["profiles"][0]["filename"] = unrelated.name
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    result = run(tmp_path, "cleanup", home=home, campaign_path=path)
    assert result.returncode != 0
    assert "manifest" in result.stderr
    assert unrelated.read_bytes() == unrelated_bytes

def test_successful_cleanup_preserves_unrelated_agent_bytes(tmp_path: Path):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    home = evaluator / "isolated-codex"
    path = prepare_campaign(evaluator)
    assert run(tmp_path, "create", home=home, campaign_path=path).returncode == 0
    unrelated = home / "agents" / "unrelated.toml"
    unrelated_bytes = b'name = "unrelated"\ndescription = "keep exact bytes"\n'
    unrelated.write_bytes(unrelated_bytes)
    result = run(tmp_path, "cleanup", home=home, campaign_path=path)
    assert result.returncode == 0, result.stderr
    assert unrelated.read_bytes() == unrelated_bytes


def test_create_collision_is_preflighted_without_partial_profiles(tmp_path: Path):
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    home = evaluator / "isolated-codex"
    path = prepare_campaign(evaluator)
    home.mkdir()
    agents = home / "agents"
    agents.mkdir()
    payload = json.loads(path.read_text(encoding="utf-8"))
    second = payload["experiment"]["roles"][0]["challengers"][0]["materialized_agent_type"]
    (agents / f"{second}.toml").write_bytes(b'name = "collision"\n')
    result = run(tmp_path, "create", home=home, campaign_path=path)
    assert result.returncode != 0
    assert list(agents.glob("subagents_dispatch_calibration_*.toml")) == [agents / f"{second}.toml"]
    assert not (home / ".subagents-dispatch-calibration.json").exists()


def test_digest_excludes_route_identity_and_includes_contract_fields():
    first = MODULE.role_contract_digest("reader", "d", "i", "none")
    second = MODULE.role_contract_digest("reader", "d", "i", "none")
    assert first == second
    assert first != MODULE.role_contract_digest("reader", "changed", "i", "none")


@pytest.mark.parametrize("field", ["campaign_id", "route_id"])
def test_materialized_identity_is_deterministic_and_collision_safe(field: str):
    kwargs = {"campaign_id": "campaign", "semantic_role": "reader", "route_id": "control"}
    first = MODULE.materialized_agent_type(**kwargs)
    kwargs[field] = kwargs[field] + "-other"
    second = MODULE.materialized_agent_type(**kwargs)
    assert first != second
    assert first.startswith("subagents_dispatch_calibration_reader_")


def test_production_reader_source_and_install_files_remain_byte_identical(tmp_path: Path):
    source = ROOT / "agent-profiles" / "subagents-dispatch-reader.toml"
    installer = ROOT / "scripts" / "install-agents.py"
    before = source.read_bytes()
    installer_before = installer.read_bytes()
    evaluator = tmp_path / "evaluator"
    evaluator.mkdir()
    path = prepare_campaign(evaluator)
    assert run(tmp_path, "create", home=evaluator / "isolated-codex", campaign_path=path).returncode == 0
    assert source.read_bytes() == before
    assert installer.read_bytes() == installer_before
    assert not (ROOT / "agent-profiles" / "subagents-dispatch-reader.toml").is_symlink()


def test_production_profile_set_has_only_five_packaged_roles():
    profiles = sorted((ROOT / "agent-profiles").glob("*.toml"))
    assert [path.name for path in profiles] == [
        "subagents-dispatch-advisor.toml",
        "subagents-dispatch-investigator.toml",
        "subagents-dispatch-reader.toml",
        "subagents-dispatch-solver.toml",
        "subagents-dispatch-worker.toml",
    ]
    assert all(not path.read_text(encoding="utf-8").startswith("name = \"subagents_dispatch_calibration_") for path in profiles)
