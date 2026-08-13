from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tomllib

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "calibration_profiles.py"


def test_directory_fsync_is_not_attempted_on_windows(monkeypatch: pytest.MonkeyPatch):
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import calibration_profiles as profiles
    finally:
        sys.path.pop(0)
    opened = False

    def unexpected_open(*args, **kwargs):
        nonlocal opened
        opened = True

    monkeypatch.setattr(profiles.os, "open", unexpected_open)
    profiles._fsync_directory(Path("unused"), platform="nt")
    assert opened is False


def test_windows_lock_uses_binary_mode(monkeypatch: pytest.MonkeyPatch):
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import calibration_profiles as profiles
    finally:
        sys.path.pop(0)
    monkeypatch.setattr(profiles.os, "O_BINARY", 0x8000, raising=False)
    assert profiles._lock_open_flags(platform="nt") & 0x8000


def init(evidence: Path) -> None:
    evidence.mkdir()
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "init", "--evaluator-root", str(evidence)],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    assert result.returncode == 0, result.stderr


def campaign(evidence: Path) -> Path:
    sys.path.insert(0, str(ROOT / "tests"))
    try:
        from test_experiment_campaign import role_campaign
        payload = role_campaign()
    finally:
        sys.path.pop(0)
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        from calibration_profile_contract import materialized_agent_type, role_contract_digest
        profile = tomllib.loads((ROOT / "agent-profiles" / "subagents-dispatch-reader.toml").read_text())
        digest = role_contract_digest("reader", profile["description"], profile["developer_instructions"], "none")
        spec = payload["experiment"]["roles"][0]
        for route in [spec["control"], *spec["challengers"]]:
            route.update(
                semantic_role="reader",
                configured_model=route["model"],
                configured_effort=route["effort"],
                materialized_agent_type=materialized_agent_type(payload["campaign_id"], "reader", route["id"]),
                role_contract_digest=digest,
            )
    finally:
        sys.path.pop(0)
    path = evidence / "campaign.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(evidence: Path, home: Path, path: Path, command: str, *extra: str):
    sessions = home / "sessions" / "2026" / "08" / "13"
    sessions.mkdir(parents=True, exist_ok=True)
    rollout = sessions / "rollout-test-provisioning-task-1.jsonl"
    rollout.write_text("\n".join([
        json.dumps({"type": "session_meta", "payload": {"id": "provisioning-task-1"}}),
        json.dumps({"type": "turn_context", "payload": {"model": "test"}}),
    ]) + "\n", encoding="utf-8")
    host_home_evidence = evidence / "host-home.json"
    host_home_evidence.write_text(json.dumps({
        "active_codex_home": str(home),
        "provisioning_rollout_path": str(rollout),
        "provisioning_rollout_sha256": hashlib.sha256(rollout.read_bytes()).hexdigest(),
    }), encoding="utf-8")
    runner = (
        "import sys; from pathlib import Path; "
        "scripts=sys.argv[1]; home=sys.argv[2]; del sys.argv[1:3]; "
        "sys.path.insert(0, scripts); import calibration_profiles as m; "
        "m._normal_codex_home=lambda: Path(home).resolve(); m.main()"
    )
    return subprocess.run(
        [sys.executable, "-c", runner, str(ROOT / "scripts"), str(home), command,
         "--evaluator-root", str(evidence),
         "--codex-home", str(home), "--campaign", str(path),
         "--host-home-evidence", str(host_home_evidence),
         "--provisioning-task-id", "provisioning-task-1", *extra],
        cwd=ROOT, env={**__import__("os").environ, "CODEX_THREAD_ID": "provisioning-task-1"},
        text=True, capture_output=True, check=False,
    )


def setup(tmp_path: Path) -> tuple[Path, Path, Path, bytes]:
    evidence = tmp_path / "evidence"
    home = tmp_path / ".codex"
    agents = home / "agents"
    agents.mkdir(parents=True)
    config = b'model = "cc-switch"\nmodel_provider = "custom"\n'
    (home / "config.toml").write_bytes(config)
    (agents / "unrelated.toml").write_text(
        'name="unrelated"\ndescription="keep"\ndeveloper_instructions="keep"\n', encoding="utf-8"
    )
    init(evidence)
    return evidence, home, campaign(evidence), config


def manifest(evidence: Path) -> dict:
    return json.loads((evidence / ".subagents-dispatch-calibration.json").read_text())


def test_profile_only_lifecycle_has_exact_host_surface_and_preserves_environment(tmp_path: Path):
    evidence, home, path, config = setup(tmp_path)
    before = (home / "agents" / "unrelated.toml").read_bytes()
    created = run(evidence, home, path, "create")
    assert created.returncode == 0, created.stderr
    assert created.stdout.strip() == "NEW TASK REQUIRED: YES"
    owned = manifest(evidence)
    assert owned["materialization_mode"] == "profile_only"
    assert owned["shared_config_mutations"] == []
    assert len(owned["profiles"]) == 2
    assert len(owned["owned_objects"]) == 2
    assert all(item["status"] == "COMMITTED" for item in owned["profiles"])
    assert (home / "config.toml").read_bytes() == config
    assert (home / "agents" / "unrelated.toml").read_bytes() == before
    for item in owned["profiles"]:
        profile = Path(item["path"])
        parsed = tomllib.loads(profile.read_text())
        assert parsed["name"] == item["materialized_agent_type"]
        assert hashlib.sha256(profile.read_bytes()).hexdigest() == item["sha256"]
        assert item["filename"] == item["materialized_agent_type"] + ".toml"
        assert Path(item["staging_path"]).parent == home / "agents"
        assert not Path(item["staging_path"]).name.endswith(".toml")
    host_identity = owned["host_home_identity"]
    assert Path(host_identity["provisioning_rollout_path"]).is_relative_to(home / "sessions")
    assert len(host_identity["provisioning_rollout_sha256"]) == 64
    assert len({item["role_contract_digest"] for item in owned["profiles"]}) == 1
    assert run(evidence, home, path, "check").returncode == 0
    assert run(evidence, home, path, "create").returncode == 0
    assert run(evidence, home, path, "cleanup").returncode == 0
    assert run(evidence, home, path, "cleanup").returncode == 0
    assert sorted(p.name for p in (home / "agents").glob("*.toml")) == ["unrelated.toml"]


def test_profile_only_rejects_obsolete_marketplace_and_config_arguments(tmp_path: Path):
    evidence, home, path, _ = setup(tmp_path)
    result = run(evidence, home, path, "create", "--shared-config", str(home / "config.toml"))
    assert result.returncode != 0
    assert "profile_only rejects" in result.stderr
    assert not (evidence / ".subagents-dispatch-calibration.json").exists()


@pytest.mark.parametrize("boundary", ["profile_1_prepared", "profile_1_committed", "profile_2_prepared"])
def test_partial_preparation_rolls_back_only_exact_owned_profiles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, boundary: str
):
    evidence, home, path, config = setup(tmp_path)
    monkeypatch.setenv("SUBAGENTS_DISPATCH_CALIBRATION_FAIL_AT", boundary)
    result = run(evidence, home, path, "create")
    assert result.returncode != 0
    assert sorted(p.name for p in (home / "agents").glob("*.toml")) == ["unrelated.toml"]
    assert (home / "config.toml").read_bytes() == config
    monkeypatch.delenv("SUBAGENTS_DISPATCH_CALIBRATION_FAIL_AT")
    assert run(evidence, home, path, "create").returncode == 0


@pytest.mark.parametrize(
    "boundary",
    ["after_profile_current_link", "after_profile_current_applied", "after_profile_candidate_cleanup_unlink"],
)
def test_profile_crash_boundaries_recover_idempotently(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, boundary: str
):
    evidence, home, path, config = setup(tmp_path)
    if boundary.endswith("cleanup_unlink"):
        assert run(evidence, home, path, "create").returncode == 0
        command = "cleanup"
    else:
        command = "create"
    monkeypatch.setenv("SUBAGENTS_DISPATCH_CALIBRATION_CRASH_AT", boundary)
    assert run(evidence, home, path, command).returncode == 86
    monkeypatch.delenv("SUBAGENTS_DISPATCH_CALIBRATION_CRASH_AT")
    assert run(evidence, home, path, "recover").returncode == 0
    assert run(evidence, home, path, "recover").returncode == 0
    assert sorted(p.name for p in (home / "agents").glob("*.toml")) == ["unrelated.toml"]
    assert (home / "config.toml").read_bytes() == config


def test_externally_modified_owned_profile_blocks_cleanup(tmp_path: Path):
    evidence, home, path, _ = setup(tmp_path)
    assert run(evidence, home, path, "create").returncode == 0
    target = Path(manifest(evidence)["profiles"][0]["path"])
    target.write_text(target.read_text() + "\n# external\n")
    cleanup = run(evidence, home, path, "cleanup")
    assert cleanup.returncode != 0
    assert "drifted" in cleanup.stderr
    assert target.exists()


def test_unexpected_third_calibration_profile_blocks_readiness(tmp_path: Path):
    evidence, home, path, _ = setup(tmp_path)
    assert run(evidence, home, path, "create").returncode == 0
    extra = home / "agents" / "subagents_dispatch_calibration_extra.toml"
    extra.write_text('name="extra"\ndescription="x"\ndeveloper_instructions="x"\n')
    checked = run(evidence, home, path, "check")
    assert checked.returncode != 0
    assert "unexpected third" in checked.stderr


def test_existing_path_symlink_and_duplicate_name_fail_before_writes(tmp_path: Path):
    evidence, home, path, _ = setup(tmp_path)
    payload = json.loads(path.read_text())
    identity = payload["experiment"]["roles"][0]["control"]["materialized_agent_type"]
    target = home / "agents" / f"{identity}.toml"
    target.write_text('name="preexisting"\ndescription="x"\ndeveloper_instructions="x"\n')
    assert run(evidence, home, path, "create").returncode != 0
    target.unlink()
    target.symlink_to(home / "agents" / "unrelated.toml")
    assert run(evidence, home, path, "create").returncode != 0


def test_symlinked_normal_home_ancestor_is_rejected(tmp_path: Path):
    evidence, home, path, _ = setup(tmp_path)
    real_parent = tmp_path / "real-parent"
    home.rename(real_parent)
    linked_parent = tmp_path / "linked-parent"
    linked_parent.symlink_to(real_parent)
    result = run(evidence, linked_parent, path, "create")
    assert result.returncode != 0
    assert "symlinked calibration" in result.stderr


def test_profile_only_rejects_unconfirmed_or_alternate_host_home_before_writes(tmp_path: Path):
    evidence, home, path, _ = setup(tmp_path)
    evidence_path = evidence / "host-home.json"
    evidence_path.write_text(json.dumps({
        "active_codex_home": str(tmp_path / "other" / ".codex"),
        "provisioning_rollout_path": str(home / "sessions" / "missing.jsonl"),
        "provisioning_rollout_sha256": "0" * 64,
    }))
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "create", "--evaluator-root", str(evidence),
         "--codex-home", str(home), "--campaign", str(path),
         "--host-home-evidence", str(evidence_path),
         "--provisioning-task-id", "provisioning-task-1"],
        cwd=ROOT, env={
            **__import__("os").environ,
            "HOME": str(home.parent),
            "CODEX_THREAD_ID": "provisioning-task-1",
        },
        text=True, capture_output=True, check=False,
    )
    assert result.returncode != 0
    assert "active normal" in result.stderr
    assert list((home / "agents").glob("subagents_dispatch_calibration_*.toml")) == []


def test_profile_only_rejects_replayed_rollout_from_inactive_task(tmp_path: Path):
    evidence, home, path, _ = setup(tmp_path)
    result = run(evidence, home, path, "create")
    assert result.returncode == 0
    result = subprocess.run(
        result.args, cwd=ROOT,
        env={**__import__("os").environ, "CODEX_THREAD_ID": "different-active-task"},
        text=True, capture_output=True, check=False,
    )
    assert result.returncode != 0
    assert "does not match the active Codex task" in result.stderr


def test_profile_only_rejects_caller_authored_home_claim_without_host_rollout(tmp_path: Path):
    evidence, home, path, _ = setup(tmp_path)
    evidence_path = evidence / "host-home.json"
    evidence_path.write_text(json.dumps({
        "active_codex_home": str(home),
        "provisioning_rollout_path": str(evidence / "forged.jsonl"),
        "provisioning_rollout_sha256": "0" * 64,
    }))
    runner = (
        "import sys; from pathlib import Path; "
        "scripts=sys.argv[1]; home=sys.argv[2]; del sys.argv[1:3]; "
        "sys.path.insert(0, scripts); import calibration_profiles as m; "
        "m._normal_codex_home=lambda: Path(home).resolve(); m.main()"
    )
    result = subprocess.run(
        [sys.executable, "-c", runner, str(ROOT / "scripts"), str(home), "create",
         "--evaluator-root", str(evidence), "--codex-home", str(home),
         "--campaign", str(path), "--host-home-evidence", str(evidence_path),
         "--provisioning-task-id", "provisioning-task-1"], cwd=ROOT,
        env={**__import__("os").environ, "CODEX_THREAD_ID": "provisioning-task-1"},
        text=True, capture_output=True, check=False,
    )
    assert result.returncode != 0
    assert "missing provisioning rollout evidence" in result.stderr
    assert list((home / "agents").glob("subagents_dispatch_calibration_*.toml")) == []


def test_profile_staging_reopen_rejects_symlink_substitution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import calibration_profiles as profiles
    finally:
        sys.path.pop(0)
    staging = tmp_path / ".owned.calibration-staging"
    victim = tmp_path / "victim"
    victim.write_text("keep")
    staging.write_text("")
    identity = staging.stat()
    target = tmp_path / "owned.toml"
    parent = tmp_path.stat()
    record = {
        "path": str(target), "staging_path": str(staging),
        "device": identity.st_dev, "inode": identity.st_ino,
        "parent_device": parent.st_dev, "parent_inode": parent.st_ino,
        "sha256": hashlib.sha256(b"profile").hexdigest(), "route_id": "current",
    }
    real_open = profiles.os.open
    def substitute(path, flags, *args):
        if Path(path) == staging and flags & profiles.os.O_WRONLY:
            staging.unlink()
            staging.symlink_to(victim)
        return real_open(path, flags, *args)
    monkeypatch.setattr(profiles.os, "open", substitute)
    with pytest.raises(SystemExit, match="could not reopen|identity drifted"):
        profiles._apply_profile(record, b"profile", lambda: None)
    assert victim.read_text() == "keep"


def test_profile_publication_rejects_staging_substitution_after_close(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import calibration_profiles as profiles
    finally:
        sys.path.pop(0)
    staging = tmp_path / ".owned.calibration-staging"
    staging.write_bytes(b"profile")
    identity = staging.stat()
    target = tmp_path / "owned.toml"
    parent = tmp_path.stat()
    record = {
        "path": str(target), "staging_path": str(staging),
        "device": identity.st_dev, "inode": identity.st_ino,
        "parent_device": parent.st_dev, "parent_inode": parent.st_ino,
        "sha256": hashlib.sha256(b"profile").hexdigest(), "route_id": "current",
    }
    real_link = profiles.os.link
    def substitute(source, destination, **kwargs):
        replacement = tmp_path / "replacement"
        replacement.write_bytes(b"profile")
        replacement.replace(source)
        return real_link(source, destination, **kwargs)
    monkeypatch.setattr(profiles.os, "link", substitute)
    with pytest.raises(SystemExit, match="published calibration profile identity is unsafe"):
        profiles._apply_profile(record, b"profile", lambda: None)
    assert target.exists()


def test_profile_publication_rejects_agent_directory_substitution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import calibration_profiles as profiles
    finally:
        sys.path.pop(0)
    agents = tmp_path / "agents"
    agents.mkdir()
    staging = agents / ".owned.calibration-staging"
    staging.write_bytes(b"profile")
    identity = staging.stat()
    parent = agents.stat()
    target = agents / "owned.toml"
    record = {
        "path": str(target), "staging_path": str(staging),
        "device": identity.st_dev, "inode": identity.st_ino,
        "parent_device": parent.st_dev, "parent_inode": parent.st_ino,
        "sha256": hashlib.sha256(b"profile").hexdigest(), "route_id": "current",
    }
    real_link = profiles.os.link
    def substitute(source, destination, **kwargs):
        original = tmp_path / "original-agents"
        agents.rename(original)
        agents.mkdir()
        new_staging = agents / staging.name
        real_link(original / staging.name, new_staging)
        return real_link(new_staging, destination, **kwargs)
    monkeypatch.setattr(profiles.os, "link", substitute)
    with pytest.raises(SystemExit, match="Agent directory identity drifted during publication"):
        profiles._apply_profile(record, b"profile", lambda: None)
    assert target.exists()


def test_production_surface_remains_exact():
    assert sorted(path.name for path in (ROOT / "agent-profiles").glob("*.toml")) == [
        "subagents-dispatch-advisor.toml", "subagents-dispatch-investigator.toml",
        "subagents-dispatch-reader.toml", "subagents-dispatch-solver.toml",
        "subagents-dispatch-worker.toml",
    ]
