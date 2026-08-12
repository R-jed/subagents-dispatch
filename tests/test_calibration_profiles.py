from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

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
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


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
        assert result.returncode != 0
        assert "missing" in result.stderr
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
