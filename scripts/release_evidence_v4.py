#!/usr/bin/env python3
"""Verify candidate-bound external release evidence for V4.0.0 Native Core.

The release evidence artifact must live outside the candidate repository. This
verifier recomputes exact candidate identity, runtime/profile/Host-contract
digests, requires a complete environment-bound N0-N8 Native Core Host campaign,
and binds a fresh Final Review receipt to the same candidate.

This is release-process evidence, not cryptographic Host attestation. The trusted
boundary remains the release/CI operator supplying the external evidence artifact.
Ordinary orchestration runtime data cannot create publication authority.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping

import package_integrity


EXPECTED_REPOSITORY = "R-jed/subagents-dispatch"
RELEASE_EVIDENCE_SCHEMA = "4.0.0-release-evidence-3"
HOST_CAMPAIGN_SCHEMA = "4.0.0-native-host-campaign-1"
FINAL_REVIEW_SCHEMA = "4.0.0-final-review-1"
HOST_CAMPAIGN_CONTRACT_VERSION = "4.0.0-native-host-smoke-1"
REQUIRED_HOST_PROBES = tuple(f"N{index}" for index in range(9))
HEX = frozenset("0123456789abcdef")

RUNTIME_MANIFEST = Path(".codex-plugin/package-integrity.json")
PROFILE_CONTRACT = Path("contracts/policy.json")
HOST_CAMPAIGN_CONTRACT = Path("docs/v4/host-smoke.json")

IDENTITY_FIELDS = {
    "candidate_commit",
    "candidate_tree",
    "runtime_manifest_sha256",
    "profile_contract_sha256",
    "host_contract_sha256",
}
TOP_LEVEL_FIELDS = {
    "schema_version",
    "repository",
    *IDENTITY_FIELDS,
    "host_campaign_sha256",
    "host_campaign",
    "final_review",
}
HOST_CAMPAIGN_FIELDS = {
    "schema_version",
    "repository",
    *IDENTITY_FIELDS,
    "contract_version",
    "campaign_id",
    "environments",
    "results",
}
HOST_ENVIRONMENT_FIELDS = {
    "codex_version",
    "host_build",
    "platform",
    "architecture",
    "run_id",
}
HOST_RESULT_FIELDS = {"status", "evidence_ref", "environment_id"}
FINAL_REVIEW_FIELDS = {
    "schema_version",
    "candidate_commit",
    "candidate_tree",
    "review_artifact_id",
    "verdict",
    "evidence_ref",
}
SUPPORTED_PLATFORMS = {"linux", "macos", "windows"}


class ReleaseEvidenceError(RuntimeError):
    """Candidate or evidence could not be inspected safely."""


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise ReleaseEvidenceError(
            f"git {' '.join(args)} failed: {result.stderr.strip() or result.stdout.strip()}"
        )
    return result.stdout.strip()


def _valid_hex(value: Any, length: int) -> bool:
    return isinstance(value, str) and len(value) == length and all(ch in HEX for ch in value)


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def canonical_json_sha256(value: Any) -> str:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ReleaseEvidenceError(f"value is not canonical JSON: {exc}") from exc
    return hashlib.sha256(encoded).hexdigest()


def normalized_file_sha256(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ReleaseEvidenceError(f"cannot read candidate file {path}: {exc}") from exc
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def _resolve_repo(repo: Path) -> Path:
    try:
        resolved = repo.expanduser().resolve(strict=True)
    except OSError as exc:
        raise ReleaseEvidenceError(f"candidate repository is unavailable: {exc}") from exc
    if not resolved.is_dir():
        raise ReleaseEvidenceError("candidate repository must be a directory")
    return resolved


def _load_host_contract(repo: Path) -> Mapping[str, Any]:
    path = repo / HOST_CAMPAIGN_CONTRACT
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReleaseEvidenceError(f"Host campaign contract is unreadable: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise ReleaseEvidenceError("Host campaign contract must be an object")
    if payload.get("schema_version") != HOST_CAMPAIGN_CONTRACT_VERSION:
        raise ReleaseEvidenceError("Host campaign contract schema_version is unsupported")
    if payload.get("gate_id") != "v4-real-host-n0-n8":
        raise ReleaseEvidenceError("Host campaign contract gate_id is unsupported")
    if payload.get("status") != "PENDING" or payload.get("results") != {}:
        raise ReleaseEvidenceError("tracked Host campaign contract must remain PENDING with empty results")
    required = payload.get("required_probes")
    if not isinstance(required, list):
        raise ReleaseEvidenceError("Host campaign contract required_probes must be an array")
    ids = [item.get("id") for item in required if isinstance(item, Mapping)]
    if len(ids) != len(required) or tuple(ids) != REQUIRED_HOST_PROBES:
        raise ReleaseEvidenceError("Host campaign contract probes must be exactly ordered N0-N8")
    if payload.get("required_environment_fields") != sorted(HOST_ENVIRONMENT_FIELDS):
        raise ReleaseEvidenceError("Host campaign contract environment field set is unsupported")
    if payload.get("required_result_fields") != sorted(HOST_RESULT_FIELDS):
        raise ReleaseEvidenceError("Host campaign contract result field set is unsupported")
    return payload


def current_candidate_identity(repo: Path) -> dict[str, str]:
    repo = _resolve_repo(repo)
    _load_host_contract(repo)
    commit = _git(repo, "rev-parse", "HEAD")
    tree = _git(repo, "rev-parse", "HEAD^{tree}")
    if not _valid_hex(commit, 40) or not _valid_hex(tree, 40):
        raise ReleaseEvidenceError("candidate Git identity is malformed")
    return {
        "candidate_commit": commit,
        "candidate_tree": tree,
        "runtime_manifest_sha256": normalized_file_sha256(repo / RUNTIME_MANIFEST),
        "profile_contract_sha256": normalized_file_sha256(repo / PROFILE_CONTRACT),
        "host_contract_sha256": normalized_file_sha256(repo / HOST_CAMPAIGN_CONTRACT),
    }


def _review_module():
    path = Path(__file__).with_name("review-artifact.py")
    spec = importlib.util.spec_from_file_location("release_evidence_review_artifact", path)
    if spec is None or spec.loader is None:
        raise ReleaseEvidenceError("review-artifact helper cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def current_review_artifact_id(repo: Path) -> str:
    repo = _resolve_repo(repo)
    try:
        receipt = _review_module().build_receipt(repo)
    except Exception as exc:
        raise ReleaseEvidenceError(f"current review artifact identity is unavailable: {exc}") from exc
    artifact_id = receipt.get("review_artifact_id") if isinstance(receipt, Mapping) else None
    if (
        not isinstance(artifact_id, str)
        or not artifact_id.startswith("sha256:")
        or not _valid_hex(artifact_id.removeprefix("sha256:"), 64)
    ):
        raise ReleaseEvidenceError("current review artifact identity is malformed")
    return artifact_id


def _load_evidence(value: Mapping[str, Any] | Path) -> tuple[dict[str, Any] | None, list[str]]:
    if isinstance(value, Mapping):
        return dict(value), []
    if not isinstance(value, Path):
        return None, ["release evidence must be an object or file path"]
    try:
        payload = json.loads(value.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, [f"release evidence file is invalid: {exc}"]
    if not isinstance(payload, dict):
        return None, ["release evidence file must contain a JSON object"]
    return payload, []


def _inside(candidate: Path, path: Path) -> bool:
    try:
        path.expanduser().resolve(strict=False).relative_to(candidate)
    except ValueError:
        return False
    return True


def _exact_fields(
    value: Any,
    fields: set[str],
    *,
    label: str,
    issues: list[str],
) -> Mapping[str, Any] | None:
    if not isinstance(value, Mapping):
        issues.append(f"{label} must be an object")
        return None
    actual = set(value)
    missing = fields - actual
    extra = actual - fields
    if missing:
        issues.append(f"{label} missing fields: {', '.join(sorted(missing))}")
    if extra:
        issues.append(f"{label} unsupported fields: {', '.join(sorted(extra))}")
    return value


def _compare_identity(
    value: Mapping[str, Any],
    expected: Mapping[str, str],
    *,
    label: str,
    issues: list[str],
) -> None:
    for field, actual in expected.items():
        supplied = value.get(field)
        required_length = 40 if field in {"candidate_commit", "candidate_tree"} else 64
        if not _valid_hex(supplied, required_length):
            issues.append(f"{label}.{field} is malformed")
        elif supplied != actual:
            issues.append(f"{label}.{field} does not match the exact candidate")


def _validate_host_campaign_digest(top: Mapping[str, Any], *, issues: list[str]) -> None:
    supplied = top.get("host_campaign_sha256")
    if not _valid_hex(supplied, 64):
        issues.append("release evidence.host_campaign_sha256 is malformed")
        return
    campaign = top.get("host_campaign")
    if not isinstance(campaign, Mapping):
        return
    try:
        expected = canonical_json_sha256(campaign)
    except ReleaseEvidenceError as exc:
        issues.append(f"host campaign cannot be digested: {exc}")
        return
    if supplied != expected:
        issues.append("release evidence.host_campaign_sha256 does not match exact Host campaign")


def _validate_host_environments(value: Any, *, issues: list[str]) -> set[str]:
    if not isinstance(value, Mapping) or not value:
        issues.append("host campaign environments must be a non-empty object")
        return set()
    valid_ids: set[str] = set()
    seen_run_ids: set[str] = set()
    for environment_id, raw in value.items():
        if not _nonempty(environment_id):
            issues.append("host campaign environment id must be non-empty")
            continue
        env = _exact_fields(
            raw,
            HOST_ENVIRONMENT_FIELDS,
            label=f"host campaign environment {environment_id}",
            issues=issues,
        )
        if env is None:
            continue
        for field in HOST_ENVIRONMENT_FIELDS:
            if not _nonempty(env.get(field)):
                issues.append(f"host campaign environment {environment_id}.{field} must be non-empty")
        platform = env.get("platform")
        if isinstance(platform, str) and platform.lower() not in SUPPORTED_PLATFORMS:
            issues.append(f"host campaign environment {environment_id}.platform is unsupported")
        run_id = env.get("run_id")
        if isinstance(run_id, str) and run_id in seen_run_ids:
            issues.append("host campaign environment run_id values must be unique")
        elif isinstance(run_id, str):
            seen_run_ids.add(run_id)
        valid_ids.add(str(environment_id))
    return valid_ids


def _validate_host_campaign(
    campaign: Any,
    *,
    identity: Mapping[str, str],
    issues: list[str],
) -> None:
    value = _exact_fields(campaign, HOST_CAMPAIGN_FIELDS, label="host campaign", issues=issues)
    if value is None:
        return
    if value.get("schema_version") != HOST_CAMPAIGN_SCHEMA:
        issues.append("host campaign schema_version is unsupported")
    if value.get("repository") != EXPECTED_REPOSITORY:
        issues.append("host campaign repository identity is invalid")
    if value.get("contract_version") != HOST_CAMPAIGN_CONTRACT_VERSION:
        issues.append("host campaign contract_version is unsupported")
    if not _nonempty(value.get("campaign_id")):
        issues.append("host campaign campaign_id must be non-empty")
    _compare_identity(value, identity, label="host campaign", issues=issues)

    environments = value.get("environments")
    environment_ids = _validate_host_environments(environments, issues=issues)
    results = value.get("results")
    if not isinstance(results, Mapping):
        issues.append("host campaign results must be an object")
        return
    actual_ids = set(results)
    required_ids = set(REQUIRED_HOST_PROBES)
    missing = sorted(required_ids - actual_ids)
    extra = sorted(actual_ids - required_ids)
    if missing:
        issues.append("host campaign missing required probes: " + ", ".join(missing))
    if extra:
        issues.append("host campaign contains unsupported probes: " + ", ".join(extra))
    for probe_id in REQUIRED_HOST_PROBES:
        if probe_id not in results:
            continue
        result = _exact_fields(
            results[probe_id],
            HOST_RESULT_FIELDS,
            label=f"host campaign {probe_id}",
            issues=issues,
        )
        if result is None:
            continue
        if result.get("status") != "PASS":
            issues.append(f"host campaign {probe_id} must PASS")
        if not _nonempty(result.get("evidence_ref")):
            issues.append(f"host campaign {probe_id} PASS requires evidence_ref")
        if result.get("environment_id") not in environment_ids:
            issues.append(f"host campaign {probe_id} references unknown environment_id")


def _validate_final_review(
    review: Any,
    *,
    identity: Mapping[str, str],
    review_artifact_id: str,
    issues: list[str],
) -> None:
    value = _exact_fields(review, FINAL_REVIEW_FIELDS, label="final review", issues=issues)
    if value is None:
        return
    if value.get("schema_version") != FINAL_REVIEW_SCHEMA:
        issues.append("final review.schema_version is unsupported")
    for field in ("candidate_commit", "candidate_tree"):
        if value.get(field) != identity[field]:
            issues.append(f"final review.{field} does not match the exact candidate")
    if value.get("review_artifact_id") != review_artifact_id:
        issues.append("final review.review_artifact_id does not match the current candidate")
    if value.get("verdict") != "ship":
        issues.append("final review verdict must be ship")
    if not _nonempty(value.get("evidence_ref")):
        issues.append("final review ship verdict requires evidence_ref")


def verify_release_evidence(
    repo: Path,
    evidence: Mapping[str, Any] | Path,
) -> dict[str, Any]:
    issues: list[str] = []
    try:
        candidate = _resolve_repo(repo)
    except ReleaseEvidenceError as exc:
        return {"ok": False, "issues": [str(exc)]}

    if isinstance(evidence, Path) and _inside(candidate, evidence):
        issues.append("release evidence file must live outside the candidate repository")

    payload, load_issues = _load_evidence(evidence)
    issues.extend(load_issues)
    if payload is None:
        return {"ok": False, "issues": issues}

    try:
        identity = current_candidate_identity(candidate)
    except ReleaseEvidenceError as exc:
        return {"ok": False, "issues": issues + [str(exc)]}

    status = _git(candidate, "status", "--porcelain", "--untracked-files=all")
    if status:
        issues.append("candidate repository must be clean before release evidence can be authoritative")

    package_result = package_integrity.verify_package(candidate)
    if package_result.get("ok") is not True:
        issues.append("candidate package integrity verification failed")

    top = _exact_fields(payload, TOP_LEVEL_FIELDS, label="release evidence", issues=issues)
    if top is not None:
        if top.get("schema_version") != RELEASE_EVIDENCE_SCHEMA:
            issues.append("release evidence schema_version is unsupported")
        if top.get("repository") != EXPECTED_REPOSITORY:
            issues.append("release evidence repository identity is invalid")
        _compare_identity(top, identity, label="release evidence", issues=issues)
        _validate_host_campaign_digest(top, issues=issues)

    try:
        review_artifact_id = current_review_artifact_id(candidate)
    except ReleaseEvidenceError as exc:
        issues.append(str(exc))
        review_artifact_id = ""

    if top is not None:
        _validate_host_campaign(top.get("host_campaign"), identity=identity, issues=issues)
        _validate_final_review(
            top.get("final_review"),
            identity=identity,
            review_artifact_id=review_artifact_id,
            issues=issues,
        )

    return {
        "ok": not issues,
        "issues": issues,
        **identity,
        "review_artifact_id": review_artifact_id,
        "required_host_probes": list(REQUIRED_HOST_PROBES),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify external V4.0.0 Native Core release evidence.")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = verify_release_evidence(args.repo, args.evidence)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    elif result["ok"]:
        print("V4 RELEASE EVIDENCE PASS")
    else:
        print("V4 RELEASE EVIDENCE FAIL")
        for issue in result["issues"]:
            print(f"- {issue}")
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
