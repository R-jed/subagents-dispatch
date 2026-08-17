from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load_module(name: str, filename: str):
    scripts = str(SCRIPTS)
    sys.path.insert(0, scripts)
    try:
        spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts)


def run(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout.strip()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def make_candidate(tmp_path: Path) -> Path:
    repo = tmp_path / "candidate"
    for directory in (
        "agent-profiles",
        "contracts",
        "hooks",
        "scripts",
        "skills",
        ".codex-plugin",
        ".agents/plugins",
        "docs",
    ):
        (repo / directory).mkdir(parents=True, exist_ok=True)
    write(repo / ".codex-plugin" / "plugin.json", '{"name":"subagents-dispatch","version":"4.0.0"}\n')
    write(repo / ".agents" / "plugins" / "marketplace.json", "{}\n")
    write(repo / "docs" / "python-runtime.md", "runtime\n")
    write(repo / "contracts" / "policy.json", '{"schema_version":9}\n')
    write(
        repo / "hooks" / "hooks.json",
        '{"hooks":{"PreToolUse":[],"PostToolUse":[],"SubagentStop":[]}}\n',
    )
    package = load_module("rc3_release_package_builder", "package_integrity.py")
    package.write_manifest(repo)

    run(repo, "init")
    run(repo, "config", "user.email", "test@example.com")
    run(repo, "config", "user.name", "RC3 Test")
    run(repo, "add", ".")
    run(repo, "commit", "-m", "candidate A")
    return repo


def build_valid_evidence(module, repo: Path) -> dict:
    identity = module.current_candidate_identity(repo)
    results = {
        probe_id: {"status": "PASS", "evidence_ref": f"host:{probe_id}"}
        for probe_id in module.REQUIRED_HOST_PROBES
    }
    campaign = {
        "schema_version": module.HOST_CAMPAIGN_SCHEMA,
        "repository": module.EXPECTED_REPOSITORY,
        **identity,
        "contract_version": module.HOST_CAMPAIGN_CONTRACT_VERSION,
        "results": results,
    }
    review = {
        "schema_version": module.FINAL_REVIEW_SCHEMA,
        "candidate_commit": identity["candidate_commit"],
        "candidate_tree": identity["candidate_tree"],
        "review_artifact_id": module.current_review_artifact_id(repo),
        "verdict": "ship",
        "evidence_ref": "review:fresh-advisor",
    }
    return {
        "schema_version": module.RELEASE_EVIDENCE_SCHEMA,
        "repository": module.EXPECTED_REPOSITORY,
        **identity,
        "host_campaign": campaign,
        "final_review": review,
    }


def test_exact_candidate_bound_release_evidence_passes(tmp_path: Path):
    module = load_module("rc3_release_valid", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_valid_evidence(module, repo)

    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is True
    assert result["issues"] == []
    assert result["candidate_commit"] == run(repo, "rev-parse", "HEAD")
    assert result["candidate_tree"] == run(repo, "rev-parse", "HEAD^{tree}")


def test_candidate_a_evidence_is_rejected_after_candidate_b_commit(tmp_path: Path):
    module = load_module("rc3_release_drift", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_valid_evidence(module, repo)

    write(repo / "docs" / "python-runtime.md", "runtime changed\n")
    package = load_module("rc3_release_package_b", "package_integrity.py")
    package.write_manifest(repo)
    run(repo, "add", ".")
    run(repo, "commit", "-m", "candidate B")

    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is False
    assert any("candidate_commit" in issue or "candidate_tree" in issue for issue in result["issues"])


def test_runtime_hook_and_profile_digest_drift_are_each_rejected(tmp_path: Path):
    module = load_module("rc3_release_digests", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_valid_evidence(module, repo)

    cases = (
        "runtime_manifest_sha256",
        "production_hook_sha256",
        "profile_contract_sha256",
    )
    for field in cases:
        tampered = copy.deepcopy(evidence)
        tampered[field] = "0" * 64
        tampered["host_campaign"][field] = "0" * 64
        result = module.verify_release_evidence(repo, tampered)
        assert result["ok"] is False
        assert any(field in issue for issue in result["issues"])


def test_host_campaign_requires_every_h00_through_h20_pass(tmp_path: Path):
    module = load_module("rc3_release_host", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_valid_evidence(module, repo)

    del evidence["host_campaign"]["results"]["H17"]
    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is False
    assert any("H17" in issue or "host campaign" in issue.lower() for issue in result["issues"])

    evidence = build_valid_evidence(module, repo)
    evidence["host_campaign"]["results"]["H12"]["status"] = "FAIL"
    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is False
    assert any("H12" in issue for issue in result["issues"])


def test_final_review_must_be_ship_and_match_current_review_artifact(tmp_path: Path):
    module = load_module("rc3_release_review", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_valid_evidence(module, repo)

    evidence["final_review"]["verdict"] = "fix-first"
    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is False
    assert any("verdict" in issue for issue in result["issues"])

    evidence = build_valid_evidence(module, repo)
    evidence["final_review"]["review_artifact_id"] = "0" * 64
    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is False
    assert any("review_artifact_id" in issue for issue in result["issues"])


def test_malformed_all_green_json_does_not_create_release_authority(tmp_path: Path):
    module = load_module("rc3_release_fake", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    fake = {
        "schema_version": module.RELEASE_EVIDENCE_SCHEMA,
        "repository": module.EXPECTED_REPOSITORY,
        "candidate_commit": run(repo, "rev-parse", "HEAD"),
        "candidate_tree": run(repo, "rev-parse", "HEAD^{tree}"),
        "runtime_manifest_sha256": "a" * 64,
        "production_hook_sha256": "b" * 64,
        "profile_contract_sha256": "c" * 64,
        "host_campaign": {"status": "PASS"},
        "final_review": {"verdict": "ship"},
    }
    result = module.verify_release_evidence(repo, fake)
    assert result["ok"] is False
    assert result["issues"]


def test_evidence_file_must_live_outside_candidate_repository(tmp_path: Path):
    module = load_module("rc3_release_external", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_valid_evidence(module, repo)
    inside = repo / "release-evidence.json"
    inside.write_text(json.dumps(evidence), encoding="utf-8")

    result = module.verify_release_evidence(repo, inside)
    assert result["ok"] is False
    assert any("outside" in issue.lower() for issue in result["issues"])
