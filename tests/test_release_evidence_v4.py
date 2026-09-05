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
    repo.mkdir(parents=True)
    package = load_module("release_package_builder", "package_integrity.py")
    for relative in package.runtime_files(ROOT):
        source = ROOT.joinpath(*relative.parts)
        target = repo.joinpath(*relative.parts)
        write(target, source.read_text(encoding="utf-8"))
    for relative in (
        Path("docs/v4/host-reference.json"),
        Path("scripts/release_evidence_v4.py"),
    ):
        source = ROOT / relative
        write(repo / relative, source.read_text(encoding="utf-8"))
    package.write_manifest(repo)
    run(repo, "init")
    run(repo, "config", "user.email", "test@example.com")
    run(repo, "config", "user.name", "Release Test")
    no_hooks = repo / ".test-no-hooks"
    no_hooks.mkdir()
    run(repo, "config", "core.hooksPath", str(no_hooks))
    run(repo, "add", ".")
    run(repo, "commit", "-m", "test: release candidate")
    return repo


def build_request(module, repo: Path, identity: dict, **overrides) -> dict:
    request = {
        "schema_version": module.FINAL_REVIEW_REQUEST_SCHEMA,
        **identity,
        "review_artifact_id": module.current_review_artifact_id(repo),
        "hard_isolation_required": False,
        "no_edit_instruction": True,
        "reviewer_agent_type": "subagents_dispatch_department_director",
        "model": "gpt-6-astra",
        "reasoning_effort": "high",
        "fork_turns": "none",
        "fresh_context": True,
        "evidence_ref": "review-request:prelaunch",
    }
    request.update(overrides)
    return request


def build_review(module, repo: Path, identity: dict, request: dict, **overrides) -> dict:
    review = {
        "schema_version": module.FINAL_REVIEW_SCHEMA,
        **identity,
        "review_artifact_id": module.current_review_artifact_id(repo),
        "verdict": "ship",
        "reviewer_agent_type": "subagents_dispatch_department_director",
        "model": "gpt-6-astra",
        "reasoning_effort": "high",
        "permission_observation": "effective_read_only",
        "assurance_mode": "enforced_read_only",
        "artifact_unchanged": True,
        "hard_isolation_required": False,
        "no_edit_instruction": True,
        "review_request_sha256": module.canonical_json_sha256(request),
        "residual_risk": "none",
        "evidence_ref": "review:fresh-department-director",
    }
    review.update(overrides)
    return review


def build_evidence(module, repo: Path) -> dict:
    identity = module.current_candidate_identity(repo)
    request = build_request(module, repo, identity)
    return {
        "schema_version": module.RELEASE_EVIDENCE_SCHEMA,
        "repository": module.EXPECTED_REPOSITORY,
        **identity,
        "host_reference_sha256": module.canonical_json_sha256(module.load_host_reference(repo)),
        "final_review_request": request,
        "final_review": build_review(module, repo, identity, request),
    }


def test_exact_candidate_bound_release_evidence_passes(tmp_path: Path):
    module = load_module("release_valid", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    result = module.verify_release_evidence(repo, build_evidence(module, repo))
    assert result["ok"] is True
    assert result["issues"] == []
    assert result["live_host_campaign_required"] is False


def test_source_mutation_invalidates_old_release_evidence(tmp_path: Path):
    module = load_module("release_source_drift", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_evidence(module, repo)
    write(repo / "note.txt", "changed\n")
    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is False
    assert result["issues"] == ["release source must be a clean exact Git commit"]


def test_tracked_dirty_source_is_not_a_release_candidate(tmp_path: Path):
    module = load_module("release_tracked_dirty", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_evidence(module, repo)
    runtime = repo / "contracts" / "policy.json"
    runtime.write_text(runtime.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is False
    assert result["issues"] == ["release source must be a clean exact Git commit"]


def test_host_reference_drift_fails_closed(tmp_path: Path):
    module = load_module("release_host_reference", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_evidence(module, repo)
    host = json.loads((repo / module.HOST_REFERENCE_PATH).read_text(encoding="utf-8"))
    host["sources"][0]["commit"] = "0" * 40
    (repo / module.HOST_REFERENCE_PATH).write_text(json.dumps(host), encoding="utf-8")
    run(repo, "add", ".")
    run(repo, "commit", "-m", "test: drift Host reference")
    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is False
    assert any("approved source" in issue for issue in result["issues"])


def test_release_review_route_cannot_downgrade_to_product_manager(tmp_path: Path):
    module = load_module("release_route", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_evidence(module, repo)
    evidence["final_review"]["reviewer_agent_type"] = "subagents_dispatch_product_manager"
    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is False
    assert any("reviewer_agent_type" in issue for issue in result["issues"])


def test_release_review_request_must_bind_exact_astra_high_route(tmp_path: Path):
    module = load_module("release_request_route", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_evidence(module, repo)
    evidence["final_review_request"]["reasoning_effort"] = "medium"
    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is False
    assert any("reasoning_effort=high" in issue for issue in result["issues"])


def test_review_result_must_bind_prelaunch_request_digest(tmp_path: Path):
    module = load_module("release_request_digest", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_evidence(module, repo)
    evidence["final_review"]["review_request_sha256"] = "0" * 64
    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is False
    assert any("review_request_sha256" in issue for issue in result["issues"])


def test_broader_permission_fallback_requires_disclosed_residual_risk(tmp_path: Path):
    module = load_module("release_fallback", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_evidence(module, repo)
    review = evidence["final_review"]
    review.update(
        {
            "permission_observation": "broader_write_capable",
            "assurance_mode": "artifact_immutability_fallback",
            "residual_risk": "none",
        }
    )
    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is False
    assert any("residual risk" in issue for issue in result["issues"])


def test_broader_permission_fallback_passes_when_bound_and_disclosed(tmp_path: Path):
    module = load_module("release_fallback_ok", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_evidence(module, repo)
    evidence["final_review"].update(
        {
            "permission_observation": "broader_write_capable",
            "assurance_mode": "artifact_immutability_fallback",
            "residual_risk": "Host permission was broader than semantic authority",
        }
    )
    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is True


def test_hard_isolation_cannot_use_artifact_fallback(tmp_path: Path):
    module = load_module("release_hard_isolation", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_evidence(module, repo)
    evidence["final_review_request"]["hard_isolation_required"] = True
    evidence["final_review"] = build_review(
        module,
        repo,
        module.current_candidate_identity(repo),
        evidence["final_review_request"],
        hard_isolation_required=True,
        permission_observation="broader_write_capable",
        assurance_mode="artifact_immutability_fallback",
        residual_risk="broader Host permission",
    )
    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is False
    assert any("hard isolation" in issue for issue in result["issues"])


def test_package_integrity_drift_blocks_release(tmp_path: Path):
    module = load_module("release_package_drift", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    runtime = repo / "scripts" / "policy.py"
    runtime.write_text(runtime.read_text(encoding="utf-8") + "\n# drift\n", encoding="utf-8")
    run(repo, "add", ".")
    run(repo, "commit", "-m", "test: runtime drift without manifest refresh")
    identity = module.current_candidate_identity(repo)
    request = build_request(module, repo, identity)
    evidence = {
        "schema_version": module.RELEASE_EVIDENCE_SCHEMA,
        "repository": module.EXPECTED_REPOSITORY,
        **identity,
        "host_reference_sha256": module.canonical_json_sha256(module.load_host_reference(repo)),
        "final_review_request": request,
        "final_review": build_review(module, repo, identity, request),
    }
    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is False
    assert any("package integrity" in issue for issue in result["issues"])


def test_release_evidence_rejects_unknown_top_level_fields(tmp_path: Path):
    module = load_module("release_extra", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_evidence(module, repo)
    evidence["legacy_host_campaign"] = {}
    result = module.verify_release_evidence(repo, evidence)
    assert result["ok"] is False
    assert any("unsupported fields" in issue for issue in result["issues"])


def test_host_reference_contract_names_both_mature_sources():
    module = load_module("release_reference_contract", "release_evidence_v4.py")
    payload = module.load_host_reference(ROOT)
    observed = {
        source["name"]: (source["repository"], source["commit"])
        for source in payload["sources"]
    }
    assert observed == module.EXPECTED_HOST_REFERENCES
    assert {
        source["name"]: source["evidence_paths"] for source in payload["sources"]
    } == module.EXPECTED_HOST_REFERENCE_PATHS
    assert payload["release_policy"]["live_host_campaign_required"] is False


def test_release_evidence_old_host_campaign_shape_is_not_accepted(tmp_path: Path):
    module = load_module("release_old_host_shape", "release_evidence_v4.py")
    repo = make_candidate(tmp_path)
    evidence = build_evidence(module, repo)
    old = copy.deepcopy(evidence)
    old.pop("host_reference_sha256")
    old["host_campaign"] = {"results": {}}
    result = module.verify_release_evidence(repo, old)
    assert result["ok"] is False
    assert any("missing fields" in issue or "unsupported fields" in issue for issue in result["issues"])
