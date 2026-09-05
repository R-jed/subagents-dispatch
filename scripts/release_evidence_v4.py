#!/usr/bin/env python3
"""Verify exact-source release evidence without a project-owned Host campaign.

The release boundary is intentionally small:

* the candidate Git source and generated package-integrity manifest are exact;
* the pinned Host-reference contract still names the mature upstream implementations
  whose native spawn behavior this project relies on;
* one Main-owned pre-review request and one fresh Department Director / Astra High
  result bind the exact current review artifact.

Ordinary runtime availability remains a Host fact. This verifier never turns a
reference repository into proof that a particular user's Host exposes a route.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, NoReturn

import package_integrity


EXPECTED_REPOSITORY = "R-jed/subagents-dispatch"
RELEASE_EVIDENCE_SCHEMA = "4.0.0-release-evidence-10"
FINAL_REVIEW_REQUEST_SCHEMA = "4.0.0-final-review-request-2"
FINAL_REVIEW_SCHEMA = "4.0.0-final-review-4"
HOST_REFERENCE_SCHEMA = "1.0"
HOST_REFERENCE_PATH = Path("docs/v4/host-reference.json")
EXPECTED_HOST_REFERENCES = {
    "sol-advisor": (
        "https://github.com/DannyMac180/sol-advisor",
        "37b75cad535abdd46531f0227483a8842d045ab8",
    ),
    "astra-advisor": (
        "https://github.com/DannyMac180/astra-advisor",
        "c72d3280551f118eba51a5884e3971a0c0058aa6",
    ),
}
EXPECTED_HOST_REFERENCE_PATHS = {
    "sol-advisor": [
        "plugins/sol-advisor/skills/orchestration/references/operations.md",
        "plugins/sol-advisor/skills/orchestration/SKILL.md",
    ],
    "astra-advisor": [
        "plugins/astra-advisor/skills/orchestration/references/operations.md",
        "plugins/astra-advisor/skills/orchestration/SKILL.md",
    ],
}


class ReleaseEvidenceError(RuntimeError):
    """Release evidence cannot be verified safely."""


def fail(message: str) -> NoReturn:
    raise SystemExit(f"ERROR: {message}")


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", os.fspath(repo), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip()
        raise ReleaseEvidenceError(
            f"git {' '.join(args)} failed: {detail or f'exit {result.returncode}'}"
        )
    return result.stdout.strip()


def current_candidate_identity(repo: Path) -> dict[str, str]:
    root = Path(_git(repo, "rev-parse", "--show-toplevel")).resolve()
    return {
        "candidate_commit": _git(root, "rev-parse", "HEAD"),
        "candidate_tree": _git(root, "rev-parse", "HEAD^{tree}"),
    }


def require_clean_release_source(repo: Path) -> None:
    if _git(repo, "status", "--porcelain=v1", "--untracked-files=all"):
        raise ReleaseEvidenceError("release source must be a clean exact Git commit")


def _load_review_artifact_module(repo: Path):
    path = repo / "scripts" / "review-artifact.py"
    spec = importlib.util.spec_from_file_location("subagents_dispatch_review_artifact", path)
    if spec is None or spec.loader is None:
        raise ReleaseEvidenceError("could not load review-artifact helper")
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def current_review_artifact_id(repo: Path) -> str:
    module = _load_review_artifact_module(repo)
    receipt = module.build_receipt(repo)
    value = receipt.get("review_artifact_id")
    if not isinstance(value, str) or not value:
        raise ReleaseEvidenceError("review-artifact helper returned no artifact id")
    return value


def load_host_reference(repo: Path) -> dict[str, Any]:
    path = repo / HOST_REFERENCE_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReleaseEvidenceError("Host reference contract is unreadable") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != HOST_REFERENCE_SCHEMA:
        raise ReleaseEvidenceError("Host reference contract schema is unsupported")
    if payload.get("contract_kind") != "host-reference-conformance":
        raise ReleaseEvidenceError("Host reference contract kind is invalid")

    policy = payload.get("release_policy")
    if policy != {
        "live_host_campaign_required": False,
        "reference_conformance_required": True,
        "runtime_fail_closed_still_required": True,
    }:
        raise ReleaseEvidenceError("Host reference release policy drifted")

    sources = payload.get("sources")
    if not isinstance(sources, list) or len(sources) != len(EXPECTED_HOST_REFERENCES):
        raise ReleaseEvidenceError("Host reference sources are incomplete")
    seen: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            raise ReleaseEvidenceError("Host reference source must be an object")
        name = source.get("name")
        if not isinstance(name, str) or name not in EXPECTED_HOST_REFERENCES or name in seen:
            raise ReleaseEvidenceError("Host reference source identity is invalid")
        seen.add(name)
        repository, commit = EXPECTED_HOST_REFERENCES[name]
        if source.get("repository") != repository or source.get("commit") != commit:
            raise ReleaseEvidenceError(f"Host reference {name} is not pinned to the approved source")
        if source.get("evidence_paths") != EXPECTED_HOST_REFERENCE_PATHS[name]:
            raise ReleaseEvidenceError(f"Host reference {name} evidence paths drifted")
        supports = source.get("supports")
        if not isinstance(supports, list) or not supports or not all(
            isinstance(item, str) and item.strip() for item in supports
        ):
            raise ReleaseEvidenceError(f"Host reference {name} has no usable support record")

    assumptions = payload.get("required_assumptions")
    if assumptions != {
        "fresh_context": "fork_turns_none",
        "explicit_route_controls": "model_and_reasoning_effort_when_exposed_by_current_host_schema",
        "public_host_schema_is_authoritative": True,
        "requested_is_not_observed": True,
        "silent_route_fallback": False,
        "unavailable_or_conflicting_route": "fail_closed",
    }:
        raise ReleaseEvidenceError("Host reference assumptions drifted")
    boundary = payload.get("runtime_boundary")
    if not isinstance(boundary, str) or not boundary.strip():
        raise ReleaseEvidenceError("Host reference runtime boundary is missing")
    return payload


def _exact_object(
    value: Any,
    *,
    required: set[str],
    label: str,
    issues: list[str],
) -> Mapping[str, Any] | None:
    if not isinstance(value, Mapping):
        issues.append(f"{label} must be an object")
        return None
    fields = set(value)
    if fields != required:
        missing = sorted(required - fields)
        extra = sorted(fields - required)
        if missing:
            issues.append(f"{label} is missing fields: {', '.join(missing)}")
        if extra:
            issues.append(f"{label} has unsupported fields: {', '.join(extra)}")
        return None
    return value


REVIEW_ROUTE = {
    "reviewer_agent_type": "subagents_dispatch_department_director",
    "model": "gpt-6-astra",
    "reasoning_effort": "high",
}

FINAL_REVIEW_REQUEST_FIELDS = {
    "schema_version",
    "candidate_commit",
    "candidate_tree",
    "review_artifact_id",
    "hard_isolation_required",
    "no_edit_instruction",
    "reviewer_agent_type",
    "model",
    "reasoning_effort",
    "fork_turns",
    "fresh_context",
    "evidence_ref",
}

FINAL_REVIEW_FIELDS = {
    "schema_version",
    "candidate_commit",
    "candidate_tree",
    "review_artifact_id",
    "verdict",
    "reviewer_agent_type",
    "model",
    "reasoning_effort",
    "permission_observation",
    "assurance_mode",
    "artifact_unchanged",
    "hard_isolation_required",
    "no_edit_instruction",
    "review_request_sha256",
    "residual_risk",
    "evidence_ref",
}

TOP_LEVEL_FIELDS = {
    "schema_version",
    "repository",
    "candidate_commit",
    "candidate_tree",
    "host_reference_sha256",
    "final_review_request",
    "final_review",
}


def _validate_review_request(
    value: Any,
    *,
    identity: Mapping[str, str],
    review_artifact_id: str,
    issues: list[str],
) -> Mapping[str, Any] | None:
    request = _exact_object(
        value,
        required=FINAL_REVIEW_REQUEST_FIELDS,
        label="final review request",
        issues=issues,
    )
    if request is None:
        return None
    if request.get("schema_version") != FINAL_REVIEW_REQUEST_SCHEMA:
        issues.append("final review request schema is unsupported")
    for field, expected in identity.items():
        if request.get(field) != expected:
            issues.append(f"final review request {field} does not match the exact candidate")
    if request.get("review_artifact_id") != review_artifact_id:
        issues.append("final review request review_artifact_id does not match the current candidate")
    for field, expected in REVIEW_ROUTE.items():
        if request.get(field) != expected:
            issues.append(f"final review request must select {field}={expected}")
    if request.get("fork_turns") != "none":
        issues.append("final review request must require fork_turns=none")
    if request.get("fresh_context") is not True:
        issues.append("final review request must require fresh_context=true")
    if request.get("no_edit_instruction") is not True:
        issues.append("final review request must require no_edit_instruction=true")
    if not isinstance(request.get("hard_isolation_required"), bool):
        issues.append("final review request hard_isolation_required must be boolean")
    if not isinstance(request.get("evidence_ref"), str) or not request.get("evidence_ref"):
        issues.append("final review request evidence_ref is required")
    return request


def _validate_final_review(
    value: Any,
    *,
    identity: Mapping[str, str],
    review_artifact_id: str,
    request: Mapping[str, Any] | None,
    issues: list[str],
) -> None:
    review = _exact_object(
        value,
        required=FINAL_REVIEW_FIELDS,
        label="final review",
        issues=issues,
    )
    if review is None:
        return
    if review.get("schema_version") != FINAL_REVIEW_SCHEMA:
        issues.append("final review schema is unsupported")
    for field, expected in identity.items():
        if review.get(field) != expected:
            issues.append(f"final review {field} does not match the exact candidate")
    if review.get("review_artifact_id") != review_artifact_id:
        issues.append("final review review_artifact_id does not match the current candidate")
    for field, expected in REVIEW_ROUTE.items():
        if review.get(field) != expected:
            issues.append(f"final review must select {field}={expected}")
    if review.get("verdict") != "ship":
        issues.append("final review verdict must be ship")
    if review.get("artifact_unchanged") is not True:
        issues.append("final review artifact_unchanged must be true")
    if review.get("no_edit_instruction") is not True:
        issues.append("final review no_edit_instruction must be true")
    if not isinstance(review.get("hard_isolation_required"), bool):
        issues.append("final review hard_isolation_required must be boolean")
    if not isinstance(review.get("evidence_ref"), str) or not review.get("evidence_ref"):
        issues.append("final review evidence_ref is required")

    if request is not None:
        if review.get("review_request_sha256") != canonical_json_sha256(request):
            issues.append("final review review_request_sha256 does not match the bound request")
        for field in (
            "candidate_commit",
            "candidate_tree",
            "review_artifact_id",
            "hard_isolation_required",
            "no_edit_instruction",
            *REVIEW_ROUTE,
        ):
            if review.get(field) != request.get(field):
                issues.append(f"final review {field} does not match the bound request")

    assurance = review.get("assurance_mode")
    permission = review.get("permission_observation")
    hard_isolation = review.get("hard_isolation_required") is True
    residual_risk = review.get("residual_risk")
    if assurance == "enforced_read_only":
        if permission != "effective_read_only":
            issues.append("enforced_read_only review requires effective_read_only permission observation")
    elif assurance == "artifact_immutability_fallback":
        if permission != "broader_write_capable":
            issues.append("artifact_immutability_fallback requires broader_write_capable permission")
        if hard_isolation:
            issues.append("artifact_immutability_fallback cannot satisfy hard isolation")
        if not isinstance(residual_risk, str) or not residual_risk.strip() or residual_risk == "none":
            issues.append("artifact_immutability_fallback must disclose residual risk")
    else:
        issues.append("final review assurance_mode is unsupported")


def verify_release_evidence(repo: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    candidate = repo.expanduser().resolve()
    issues: list[str] = []
    try:
        identity = current_candidate_identity(candidate)
        require_clean_release_source(candidate)
    except ReleaseEvidenceError as exc:
        return {"ok": False, "issues": [str(exc)]}

    generated = package_integrity.check_generated(candidate)
    if generated.get("ok") is not True:
        issues.append("candidate package integrity manifest does not match the current runtime file set")
    integrity = package_integrity.verify_package(candidate)
    if integrity.get("ok") is not True:
        issues.append("candidate package integrity verification failed")

    try:
        host_reference = load_host_reference(candidate)
        host_reference_sha256 = canonical_json_sha256(host_reference)
    except ReleaseEvidenceError as exc:
        host_reference_sha256 = None
        issues.append(str(exc))

    try:
        review_artifact_id = current_review_artifact_id(candidate)
    except (ReleaseEvidenceError, SystemExit) as exc:
        review_artifact_id = ""
        issues.append(f"current review artifact is unavailable: {exc}")

    top = _exact_object(
        payload,
        required=TOP_LEVEL_FIELDS,
        label="release evidence",
        issues=issues,
    )
    if top is not None:
        if top.get("schema_version") != RELEASE_EVIDENCE_SCHEMA:
            issues.append("release evidence schema is unsupported")
        if top.get("repository") != EXPECTED_REPOSITORY:
            issues.append("release evidence repository is not canonical")
        for field, expected in identity.items():
            if top.get(field) != expected:
                issues.append(f"release evidence {field} does not match the exact candidate")
        if top.get("host_reference_sha256") != host_reference_sha256:
            issues.append("release evidence host_reference_sha256 does not match the pinned contract")
        request = _validate_review_request(
            top.get("final_review_request"),
            identity=identity,
            review_artifact_id=review_artifact_id,
            issues=issues,
        )
        _validate_final_review(
            top.get("final_review"),
            identity=identity,
            review_artifact_id=review_artifact_id,
            request=request,
            issues=issues,
        )

    return {
        "ok": not issues,
        "issues": issues,
        **identity,
        "review_artifact_id": review_artifact_id or None,
        "host_reference_sha256": host_reference_sha256,
        "live_host_campaign_required": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify exact-source release evidence.")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--evidence", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        payload = json.loads(args.evidence.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(f"release evidence is unreadable: {exc}")
    if not isinstance(payload, Mapping):
        fail("release evidence must be a JSON object")
    result = verify_release_evidence(args.repo, payload)
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
