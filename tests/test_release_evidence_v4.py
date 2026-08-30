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
    """Build a realistic candidate from the current product integrity boundary."""
    repo = tmp_path / "candidate"
    repo.mkdir(parents=True, exist_ok=True)
    package = load_module("native_release_package_builder", "package_integrity.py")
    for relative in package.runtime_files(ROOT):
        source = ROOT.joinpath(*relative.parts)
        target = repo.joinpath(*relative.parts)
        write(target, source.read_text(encoding="utf-8"))
    write(
        repo / "docs" / "v4" / "host-smoke.json",
        (ROOT / "docs" / "v4" / "host-smoke.json").read_text(encoding="utf-8"),
    )
    package.write_manifest(repo)

    run(repo, "init")
    run(repo, "config", "user.email", "test@example.com")
    run(repo, "config", "user.name", "Native Core Test")
    no_hooks = repo / ".test-no-hooks"
    no_hooks.mkdir()
    run(repo, "config", "core.hooksPath", str(no_hooks))
    run(repo, "add", ".")
    run(repo, "commit", "-m", "test: candidate A")
    return repo


def build_final_review(
    module,
    repo: Path,
    identity: dict,
    review_request: dict,
    *,
    permission_observation: str = "effective_read_only",
    assurance_mode: str = "enforced_read_only",
    artifact_unchanged: bool = True,
    hard_isolation_required: bool = False,
    no_edit_instruction: bool = True,
    residual_risk: str = "none",
) -> dict:
    return {
        "schema_version": module.FINAL_REVIEW_SCHEMA,
        "candidate_commit": identity["candidate_commit"],
        "candidate_tree": identity["candidate_tree"],
        "review_artifact_id": module.current_review_artifact_id(repo),
        "verdict": "ship",
        "permission_observation": permission_observation,
        "assurance_mode": assurance_mode,
        "artifact_unchanged": artifact_unchanged,
        "hard_isolation_required": hard_isolation_required,
        "no_edit_instruction": no_edit_instruction,
        "review_request_sha256": module.canonical_json_sha256(review_request),
        "residual_risk": residual_risk,
        "evidence_ref": "review:fresh-advisor",
    }


def build_final_review_request(
    module,
    repo: Path,
    identity: dict,
    *,
    hard_isolation_required: bool = False,
    no_edit_instruction: bool = True,
    reviewer_agent_type: str = "subagents_dispatch_advisor",
    fork_turns: str = "none",
    fresh_context: bool = True,
) -> dict:
    return {
        "schema_version": module.FINAL_REVIEW_REQUEST_SCHEMA,
        "candidate_commit": identity["candidate_commit"],
        "candidate_tree": identity["candidate_tree"],
        "review_artifact_id": module.current_review_artifact_id(repo),
        "hard_isolation_required": hard_isolation_required,
        "no_edit_instruction": no_edit_instruction,
        "reviewer_agent_type": reviewer_agent_type,
        "fork_turns": fork_turns,
        "fresh_context": fresh_context,
        "evidence_ref": "review-request:main-prelaunch",
    }


def build_release_envelope(module, repo: Path, campaign: dict) -> dict:
    identity = module.current_candidate_identity(repo)
    review_request = build_final_review_request(module, repo, identity)
    return {
        "schema_version": module.RELEASE_EVIDENCE_SCHEMA,
        "repository": module.EXPECTED_REPOSITORY,
        **identity,
        "host_campaign_sha256": module.canonical_json_sha256(campaign),
        "host_campaign": campaign,
        "final_review_request": review_request,
        "final_review": build_final_review(module, repo, identity, review_request),
    }


def build_valid_evidence(module, repo: Path) -> dict:
    identity = module.current_candidate_identity(repo)
    environments = {
        "env-main": {
            "codex_version": "test-current",
            "host_build": "build-main",
            "platform": "linux",
            "architecture": "x86_64",
            "session_id": "session-main",
            "thread_id": "thread-main",
        }
    }
    results = {
        probe_id: {
            "status": "PASS",
            "evidence_ref": f"host:{probe_id}",
            "environment_id": "env-main",
        }
        for probe_id in module.REQUIRED_HOST_PROBES
    }
    campaign = {
        "schema_version": module.HOST_CAMPAIGN_SCHEMA,
        "repository": module.EXPECTED_REPOSITORY,
        **module.host_qualification_identity(identity),
        "contract_version": module.HOST_CAMPAIGN_CONTRACT_VERSION,
        "campaign_id": "campaign-host-qualification-basis",
        "environments": environments,
        "results": results,
    }
    return build_release_envelope(module, repo, campaign)


def test_exact_candidate_bound_release_evidence_passes(tmp_path: Path):
    module = load_module("native_release_valid", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_valid_evidence(module, repo)

    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is True
    assert result["issues"] == []
    assert result["required_host_probes"] == [f"N{index}" for index in range(8)]
    assert result["candidate_commit"] == run(repo, "rev-parse", "HEAD")
    assert result["candidate_tree"] == run(repo, "rev-parse", "HEAD^{tree}")


def test_old_release_envelope_is_rejected_after_non_runtime_source_commit(tmp_path: Path):
    module = load_module("native_release_source_drift", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_valid_evidence(module, repo)

    write(repo / "development-note.md", "updated development context only\n")
    run(repo, "add", ".")
    run(repo, "commit", "-m", "docs: update development note")

    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is False
    assert any("candidate_commit" in issue or "candidate_tree" in issue for issue in result["issues"])


def test_host_campaign_is_reusable_after_non_runtime_source_commit(tmp_path: Path):
    module = load_module("native_release_non_runtime_reuse", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    original = build_valid_evidence(module, repo)
    campaign = copy.deepcopy(original["host_campaign"])

    qualification_before = module.host_qualification_identity(module.current_candidate_identity(repo))
    write(repo / "development-note.md", "new development-session context\n")
    run(repo, "add", ".")
    run(repo, "commit", "-m", "docs: refresh development note")
    qualification_after = module.host_qualification_identity(module.current_candidate_identity(repo))

    assert qualification_after == qualification_before

    rebound = build_release_envelope(module, repo, campaign)
    result = module.verify_release_evidence(repo, rebound)
    assert result["ok"] is True
    assert result["issues"] == []


def test_host_campaign_is_rejected_after_runtime_qualification_drift(tmp_path: Path):
    module = load_module("native_release_runtime_reuse", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    original = build_valid_evidence(module, repo)
    campaign = copy.deepcopy(original["host_campaign"])

    write(repo / "skills" / "orchestrate" / "SKILL.md", "runtime changed\n")
    package = load_module("native_release_package_b", "package_integrity.py")
    package.write_manifest(repo)
    run(repo, "add", ".")
    run(repo, "commit", "-m", "test: runtime candidate B")

    rebound = build_release_envelope(module, repo, campaign)
    result = module.verify_release_evidence(repo, rebound)
    assert result["ok"] is False
    assert any("runtime_manifest_sha256" in issue for issue in result["issues"])


def test_host_campaign_reuse_rejects_unmanifested_new_runtime_file(tmp_path: Path):
    module = load_module("native_release_unmanifested_runtime", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    original = build_valid_evidence(module, repo)
    campaign = copy.deepcopy(original["host_campaign"])
    qualification_before = module.host_qualification_identity(module.current_candidate_identity(repo))

    write(repo / "contracts" / "new-runtime-contract.md", "new runtime contract\n")
    run(repo, "add", ".")
    run(repo, "commit", "-m", "test: add unmanifested runtime file")
    qualification_after = module.host_qualification_identity(module.current_candidate_identity(repo))

    assert qualification_after == qualification_before
    rebound = build_release_envelope(module, repo, campaign)
    result = module.verify_release_evidence(repo, rebound)
    assert result["ok"] is False
    assert any("runtime file set" in issue for issue in result["issues"])


def test_runtime_profile_and_host_contract_digest_drift_are_rejected(tmp_path: Path):
    module = load_module("native_release_digests", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_valid_evidence(module, repo)

    for field in (
        "runtime_manifest_sha256",
        "profile_contract_sha256",
        "host_contract_sha256",
    ):
        tampered = copy.deepcopy(evidence)
        tampered[field] = "0" * 64
        tampered["host_campaign"][field] = "0" * 64
        tampered["host_campaign_sha256"] = module.canonical_json_sha256(tampered["host_campaign"])
        result = module.verify_release_evidence(repo, tampered)
        assert result["ok"] is False
        assert any(field in issue for issue in result["issues"])


def test_host_campaign_requires_every_n0_through_n7_pass(tmp_path: Path):
    module = load_module("native_release_host", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_valid_evidence(module, repo)

    del evidence["host_campaign"]["results"]["N7"]
    evidence["host_campaign_sha256"] = module.canonical_json_sha256(evidence["host_campaign"])
    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is False
    assert any("N7" in issue for issue in result["issues"])

    evidence = build_valid_evidence(module, repo)
    evidence["host_campaign"]["results"]["N5"]["status"] = "FAIL"
    evidence["host_campaign_sha256"] = module.canonical_json_sha256(evidence["host_campaign"])
    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is False
    assert any("N5" in issue for issue in result["issues"])


def test_host_campaign_digest_binds_environment_and_results(tmp_path: Path):
    module = load_module("native_release_host_digest", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_valid_evidence(module, repo)
    original_digest = evidence["host_campaign_sha256"]

    evidence["host_campaign"]["environments"]["env-main"]["host_build"] = "changed"
    assert evidence["host_campaign_sha256"] == original_digest
    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is False
    assert any("host_campaign_sha256" in issue for issue in result["issues"])

    evidence = build_valid_evidence(module, repo)
    original_digest = evidence["host_campaign_sha256"]
    evidence["host_campaign"]["results"]["N7"]["evidence_ref"] = "host:tampered"
    assert evidence["host_campaign_sha256"] == original_digest
    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is False
    assert any("host_campaign_sha256" in issue for issue in result["issues"])


def test_host_campaign_requires_complete_environment_identity(tmp_path: Path):
    module = load_module("native_release_environment", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_valid_evidence(module, repo)

    evidence["host_campaign"]["environments"]["env-main"]["session_id"] = ""
    evidence["host_campaign_sha256"] = module.canonical_json_sha256(evidence["host_campaign"])
    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is False
    assert any("session_id" in issue for issue in result["issues"])

    evidence = build_valid_evidence(module, repo)
    evidence["host_campaign"]["results"]["N4"]["environment_id"] = "missing-env"
    evidence["host_campaign_sha256"] = module.canonical_json_sha256(evidence["host_campaign"])
    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is False
    assert any("N4" in issue and "environment_id" in issue for issue in result["issues"])


def test_host_campaign_rejects_duplicate_root_thread_identity(tmp_path: Path):
    module = load_module("native_release_thread_identity", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_valid_evidence(module, repo)
    duplicate = copy.deepcopy(evidence["host_campaign"]["environments"]["env-main"])
    duplicate["session_id"] = "session-other"
    evidence["host_campaign"]["environments"]["env-other"] = duplicate
    evidence["host_campaign_sha256"] = module.canonical_json_sha256(evidence["host_campaign"])

    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is False
    assert any("thread_id values must be unique" in issue for issue in result["issues"])


def test_final_review_must_be_ship_and_match_current_review_artifact(tmp_path: Path):
    module = load_module("native_release_review", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_valid_evidence(module, repo)

    evidence["final_review"]["verdict"] = "fix-first"
    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is False
    assert any("verdict" in issue for issue in result["issues"])

    evidence = build_valid_evidence(module, repo)
    evidence["final_review"]["review_artifact_id"] = "sha256:" + "0" * 64
    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is False
    assert any("review_artifact_id" in issue for issue in result["issues"])


def test_final_review_enforced_read_only_path_passes(tmp_path: Path):
    module = load_module("native_release_review_read_only", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_valid_evidence(module, repo)

    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is True


def test_final_review_broader_permission_artifact_fallback_passes_with_residual_risk(
    tmp_path: Path,
):
    module = load_module("native_release_review_fallback", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_valid_evidence(module, repo)
    identity = module.current_candidate_identity(repo)
    evidence["final_review"] = build_final_review(
        module,
        repo,
        identity,
        evidence["final_review_request"],
        permission_observation="broader_write_capable",
        assurance_mode="artifact_immutability_fallback",
        hard_isolation_required=False,
        residual_risk=(
            "Host allowed broader writes; exact source artifact remained unchanged, but this "
            "does not prove Host-enforced isolation or absence of ignored/external side effects."
        ),
    )

    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is True


def test_final_review_broader_permission_rejects_hard_isolation_requirement(tmp_path: Path):
    module = load_module("native_release_review_hard_isolation", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_valid_evidence(module, repo)
    identity = module.current_candidate_identity(repo)
    evidence["final_review"] = build_final_review(
        module,
        repo,
        identity,
        evidence["final_review_request"],
        permission_observation="broader_write_capable",
        assurance_mode="artifact_immutability_fallback",
        hard_isolation_required=True,
        residual_risk="broader Host permission observed",
    )

    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is False
    assert any("hard isolation" in issue for issue in result["issues"])


def test_final_review_broader_permission_rejects_changed_artifact_or_missing_no_edit_instruction(
    tmp_path: Path,
):
    module = load_module("native_release_review_fallback_guards", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    identity = module.current_candidate_identity(repo)

    for field, value, expected in (
        ("artifact_unchanged", False, "artifact_unchanged"),
        ("no_edit_instruction", False, "no_edit_instruction"),
    ):
        evidence = build_valid_evidence(module, repo)
        kwargs = {
            "permission_observation": "broader_write_capable",
            "assurance_mode": "artifact_immutability_fallback",
            "hard_isolation_required": False,
            "residual_risk": "broader Host permission observed",
        }
        kwargs[field] = value
        evidence["final_review"] = build_final_review(
            module,
            repo,
            identity,
            evidence["final_review_request"],
            **kwargs,
        )
        result = module.verify_release_evidence(repo, evidence)
        assert result["ok"] is False
        assert any(expected in issue for issue in result["issues"])


def test_final_review_unobservable_permission_fails_closed(tmp_path: Path):
    module = load_module("native_release_review_unobservable", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_valid_evidence(module, repo)
    identity = module.current_candidate_identity(repo)
    evidence["final_review"] = build_final_review(
        module,
        repo,
        identity,
        evidence["final_review_request"],
        permission_observation="unobservable",
        assurance_mode="enforced_read_only",
    )

    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is False
    assert any("permission observation is unavailable" in issue for issue in result["issues"])


def test_final_review_broader_permission_requires_residual_risk(tmp_path: Path):
    module = load_module("native_release_review_residual_risk", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_valid_evidence(module, repo)
    identity = module.current_candidate_identity(repo)
    evidence["final_review"] = build_final_review(
        module,
        repo,
        identity,
        evidence["final_review_request"],
        permission_observation="broader_write_capable",
        assurance_mode="artifact_immutability_fallback",
        residual_risk="",
    )

    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is False
    assert any("residual_risk" in issue for issue in result["issues"])


def test_final_review_permission_and_assurance_must_match(tmp_path: Path):
    module = load_module("native_release_review_assurance_match", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    identity = module.current_candidate_identity(repo)

    for permission, assurance in (
        ("effective_read_only", "artifact_immutability_fallback"),
        ("broader_write_capable", "enforced_read_only"),
    ):
        evidence = build_valid_evidence(module, repo)
        evidence["final_review"] = build_final_review(
            module,
            repo,
            identity,
            evidence["final_review_request"],
            permission_observation=permission,
            assurance_mode=assurance,
            residual_risk="broader Host permission observed" if permission == "broader_write_capable" else "none",
        )
        result = module.verify_release_evidence(repo, evidence)
        assert result["ok"] is False
        assert any("requires" in issue and "assurance" in issue for issue in result["issues"])


def test_final_review_cannot_downgrade_bound_hard_isolation_requirement(tmp_path: Path):
    module = load_module("native_release_review_bound_hard_isolation", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_valid_evidence(module, repo)
    identity = module.current_candidate_identity(repo)
    request = build_final_review_request(
        module,
        repo,
        identity,
        hard_isolation_required=True,
    )
    evidence["final_review_request"] = request
    evidence["final_review"] = build_final_review(
        module,
        repo,
        identity,
        request,
        permission_observation="broader_write_capable",
        assurance_mode="artifact_immutability_fallback",
        hard_isolation_required=False,
        residual_risk="broader Host permission observed",
    )

    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is False
    assert any("bound pre-review request" in issue for issue in result["issues"])


def test_final_review_request_requires_real_no_edit_and_fresh_advisor_route(tmp_path: Path):
    module = load_module("native_release_review_request_guards", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    identity = module.current_candidate_identity(repo)

    for field, value, expected in (
        ("no_edit_instruction", False, "no_edit_instruction"),
        ("reviewer_agent_type", "generic", "subagents_dispatch_advisor"),
        ("fork_turns", "all", "fork_turns=none"),
        ("fresh_context", False, "fresh_context=true"),
    ):
        evidence = build_valid_evidence(module, repo)
        request = build_final_review_request(module, repo, identity)
        request[field] = value
        evidence["final_review_request"] = request
        evidence["final_review"] = build_final_review(module, repo, identity, request)
        result = module.verify_release_evidence(repo, evidence)
        assert result["ok"] is False
        assert any(expected in issue for issue in result["issues"])


def test_legacy_n8_host_result_is_rejected_as_unsupported_probe(tmp_path: Path):
    module = load_module("native_release_legacy_n8", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_valid_evidence(module, repo)
    evidence["host_campaign"]["results"]["N8"] = {
        "status": "PASS",
        "evidence_ref": "legacy:n8",
        "environment_id": "env-main",
    }
    evidence["host_campaign_sha256"] = module.canonical_json_sha256(evidence["host_campaign"])

    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is False
    assert any("unsupported probes" in issue and "N8" in issue for issue in result["issues"])


def test_malformed_all_green_json_does_not_create_release_authority(tmp_path: Path):
    module = load_module("native_release_fake", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    fake = {
        "schema_version": module.RELEASE_EVIDENCE_SCHEMA,
        "repository": module.EXPECTED_REPOSITORY,
        "candidate_commit": run(repo, "rev-parse", "HEAD"),
        "candidate_tree": run(repo, "rev-parse", "HEAD^{tree}"),
        "runtime_manifest_sha256": "a" * 64,
        "profile_contract_sha256": "c" * 64,
        "host_contract_sha256": "d" * 64,
        "host_campaign_sha256": "e" * 64,
        "host_campaign": {"status": "PASS"},
        "final_review": {"verdict": "ship"},
    }
    result = module.verify_release_evidence(repo, fake)
    assert result["ok"] is False
    assert result["issues"]


def test_evidence_file_must_live_outside_candidate_repository(tmp_path: Path):
    module = load_module("native_release_external", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_valid_evidence(module, repo)
    inside = repo / "release-evidence.json"
    inside.write_text(json.dumps(evidence), encoding="utf-8")

    result = module.verify_release_evidence(repo, inside)
    assert result["ok"] is False
    assert any("outside" in issue.lower() for issue in result["issues"])
