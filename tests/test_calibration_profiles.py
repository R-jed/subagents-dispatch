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
    return subprocess.run(
        [sys.executable, str(SCRIPT), command, "--evaluator-root", str(evidence),
         "--codex-home", str(home), "--campaign", str(path), *extra],
        cwd=ROOT, text=True, capture_output=True, check=False,
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


def test_production_surface_remains_exact():
    assert sorted(path.name for path in (ROOT / "agent-profiles").glob("*.toml")) == [
        "subagents-dispatch-advisor.toml", "subagents-dispatch-investigator.toml",
        "subagents-dispatch-reader.toml", "subagents-dispatch-solver.toml",
        "subagents-dispatch-worker.toml",
    ]
