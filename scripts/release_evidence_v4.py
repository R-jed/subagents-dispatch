#!/usr/bin/env python3
"""Verify external release evidence for Native Core V4.

The release evidence artifact must live outside the candidate repository. This
verifier keeps two identity layers separate:

- release source identity binds the final Git commit/tree and Final Review;
- Host qualification identity snapshots the shipped runtime manifest, managed
  profile contract, and Host campaign contract for the N0-N7 real-Host campaign.
- each N0-N7 result is additionally bound to a deterministic per-probe basis so
  unchanged Host evidence can be carried forward across unrelated package changes.

Carry-forward is permitted only when the current verifier can recompute the original
probe basis from Git history, prove that it equals the current probe basis, and prove
that the stable Host environment identity is unchanged. The final release envelope
and Final Review must still bind the exact final Git source state.

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
RELEASE_EVIDENCE_SCHEMA = "4.0.0-release-evidence-8"
HOST_CAMPAIGN_SCHEMA = "4.0.0-native-host-campaign-5"
LEGACY_HOST_CAMPAIGN_SCHEMA = "4.0.0-native-host-campaign-3"
FINAL_REVIEW_REQUEST_SCHEMA = "4.0.0-final-review-request-1"
FINAL_REVIEW_SCHEMA = "4.0.0-final-review-3"
HOST_CAMPAIGN_CONTRACT_VERSION = "4.0.0-native-host-smoke-3"
LEGACY_HOST_CAMPAIGN_CONTRACT_VERSION = "4.0.0-native-host-smoke-2"
REQUIRED_HOST_PROBES = tuple(f"N{index}" for index in range(8))
HEX = frozenset("0123456789abcdef")

RUNTIME_MANIFEST = Path(".codex-plugin/package-integrity.json")
PROFILE_CONTRACT = Path("contracts/policy.json")
HOST_CAMPAIGN_CONTRACT = Path("docs/v4/host-smoke.json")

_LEGACY_CORE_ORCH = frozenset(
    {
        "scripts/dispatch_state_v4.py",
        "scripts/dispatch_state_v4_core.py",
        "scripts/execution_lifecycle_v4.py",
        "scripts/execution_lifecycle_v4_core.py",
        "scripts/host_capabilities.py",
        "scripts/managed_execution_v4.py",
        "scripts/orchestrate_v4.py",
        "scripts/policy.py",
        "scripts/scheduler_v4.py",
        "scripts/state_storage.py",
        "scripts/work_graph_v4.py",
        "scripts/writer_lease_v4.py",
    }
)
_LEGACY_LIFECYCLE = frozenset(
    {
        "scripts/dispatch_state_v4.py",
        "scripts/dispatch_state_v4_core.py",
        "scripts/execution_lifecycle_v4.py",
        "scripts/execution_lifecycle_v4_core.py",
        "scripts/managed_execution_v4.py",
        "scripts/policy.py",
        "scripts/state_storage.py",
        "scripts/writer_lease_v4.py",
    }
)
_LEGACY_RUNTIME_EVIDENCE = frozenset(
    {"scripts/runtime-evidence.py", "scripts/inspect-agent-runtime.py"}
)
_LEGACY_COLLABORATION_EVIDENCE = frozenset({"scripts/inspect-collaboration-runtime.py"})
_LEGACY_ORCHESTRATE_SURFACE = frozenset(
    {
        ".codex-plugin/plugin.json",
        "skills/orchestrate/SKILL.md",
        "skills/orchestrate/agents/openai.yaml",
    }
)
_LEGACY_PROFILES = frozenset(
    {
        "agent-profiles/subagents-dispatch-advisor.toml",
        "agent-profiles/subagents-dispatch-investigator.toml",
        "agent-profiles/subagents-dispatch-reader.toml",
        "agent-profiles/subagents-dispatch-solver.toml",
        "agent-profiles/subagents-dispatch-worker.toml",
    }
)
_LEGACY_GUARDRAILS = frozenset(
    {
        "contracts/composition.md",
        "contracts/guardrails.md",
        "contracts/policy.json",
        "contracts/state.md",
    }
)
_LEGACY_ROUTING = frozenset({"contracts/routing.md", "contracts/responsibility-packet.md"})
_LEGACY_CONTROL = frozenset({"contracts/interaction.md", "contracts/recovery.md"})
_LEGACY_EVIDENCE_ARTIFACT = frozenset({"contracts/evidence-artifact.md"})

LEGACY_V2_PROBE_RUNTIME_FILES = {
    "N0": tuple(sorted(_LEGACY_CORE_ORCH | _LEGACY_RUNTIME_EVIDENCE | _LEGACY_ORCHESTRATE_SURFACE | _LEGACY_PROFILES | _LEGACY_GUARDRAILS | _LEGACY_ROUTING)),
    "N1": tuple(sorted(_LEGACY_CORE_ORCH | _LEGACY_RUNTIME_EVIDENCE | _LEGACY_COLLABORATION_EVIDENCE | _LEGACY_ORCHESTRATE_SURFACE | _LEGACY_PROFILES | _LEGACY_GUARDRAILS | _LEGACY_ROUTING)),
    "N2": tuple(sorted(_LEGACY_CORE_ORCH | _LEGACY_RUNTIME_EVIDENCE | _LEGACY_COLLABORATION_EVIDENCE | _LEGACY_ORCHESTRATE_SURFACE | _LEGACY_PROFILES | _LEGACY_GUARDRAILS | _LEGACY_ROUTING | {"contracts/recovery.md"})),
    "N3": tuple(sorted(_LEGACY_CORE_ORCH | _LEGACY_RUNTIME_EVIDENCE | _LEGACY_COLLABORATION_EVIDENCE | _LEGACY_ORCHESTRATE_SURFACE | _LEGACY_PROFILES | _LEGACY_GUARDRAILS | _LEGACY_ROUTING | {"contracts/recovery.md"})),
    "N4": tuple(sorted(_LEGACY_CORE_ORCH | _LEGACY_RUNTIME_EVIDENCE | _LEGACY_COLLABORATION_EVIDENCE | _LEGACY_ORCHESTRATE_SURFACE | _LEGACY_PROFILES | _LEGACY_GUARDRAILS | _LEGACY_ROUTING | _LEGACY_CONTROL)),
    "N5": tuple(sorted(_LEGACY_CORE_ORCH | _LEGACY_ORCHESTRATE_SURFACE | _LEGACY_PROFILES | _LEGACY_GUARDRAILS | _LEGACY_CONTROL)),
    "N6": tuple(sorted(_LEGACY_CORE_ORCH | _LEGACY_ORCHESTRATE_SURFACE | _LEGACY_PROFILES | _LEGACY_GUARDRAILS | _LEGACY_CONTROL)),
    "N7": tuple(sorted(_LEGACY_LIFECYCLE | {"scripts/work_graph_v4.py"} | _LEGACY_COLLABORATION_EVIDENCE | _LEGACY_ORCHESTRATE_SURFACE | _LEGACY_GUARDRAILS | {"contracts/recovery.md"} | _LEGACY_EVIDENCE_ARTIFACT)),
}
LEGACY_V2_RUNTIME_JSON_FIELDS = {
    probe_id: {".codex-plugin/plugin.json": ("interface.capabilities", "skills")}
    for probe_id in REQUIRED_HOST_PROBES
}
LEGACY_V2_SCOPE_SHA256 = "10110657a0604ee62e9d33078985acd647c18911d49844b9cd762e9763f5c0f9"

SOURCE_IDENTITY_FIELDS = {
    "candidate_commit",
    "candidate_tree",
}
HOST_QUALIFICATION_FIELDS = {
    "runtime_manifest_sha256",
    "profile_contract_sha256",
    "host_contract_sha256",
}
RELEASE_IDENTITY_FIELDS = SOURCE_IDENTITY_FIELDS | HOST_QUALIFICATION_FIELDS
TOP_LEVEL_FIELDS = {
    "schema_version",
    "repository",
    *RELEASE_IDENTITY_FIELDS,
    "host_campaign_sha256",
    "host_campaign",
    "final_review_request",
    "final_review",
}
HOST_CAMPAIGN_FIELDS = {
    "schema_version",
    "repository",
    *HOST_QUALIFICATION_FIELDS,
    "contract_version",
    "campaign_id",
    "qualification_environment_id",
    "environments",
    "results",
    "source_campaign_artifacts",
}
LEGACY_HOST_CAMPAIGN_FIELDS = {
    "schema_version",
    "repository",
    *HOST_QUALIFICATION_FIELDS,
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
    "session_id",
    "thread_id",
}
HOST_STABLE_ENVIRONMENT_FIELDS = {
    "codex_version",
    "host_build",
    "platform",
    "architecture",
}
HOST_RESULT_FIELDS = {
    "status",
    "evidence_ref",
    "environment_id",
    "probe_basis_sha256",
    "provenance",
}
LEGACY_HOST_RESULT_FIELDS = {"status", "evidence_ref", "environment_id"}
FRESH_PROVENANCE_FIELDS = {"kind", "source_commit", "source_tree"}
CARRY_FORWARD_PROVENANCE_FIELDS = {
    "kind",
    "source_campaign_artifact_sha256",
    "impact_analysis_ref",
}
SOURCE_CAMPAIGN_ARTIFACT_FIELDS = {
    "source_commit",
    "source_tree",
    "host_campaign_sha256",
    "host_campaign",
}
FINAL_REVIEW_REQUEST_FIELDS = {
    "schema_version",
    "candidate_commit",
    "candidate_tree",
    "review_artifact_id",
    "hard_isolation_required",
    "no_edit_instruction",
    "reviewer_agent_type",
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
    "permission_observation",
    "assurance_mode",
    "artifact_unchanged",
    "hard_isolation_required",
    "no_edit_instruction",
    "review_request_sha256",
    "residual_risk",
    "evidence_ref",
}
SUPPORTED_PLATFORMS = {"linux", "macos", "windows"}
PERMISSION_OBSERVATIONS = {
    "effective_read_only",
    "broader_write_capable",
    "unobservable",
}
FINAL_REVIEW_ASSURANCE_MODES = {
    "enforced_read_only",
    "artifact_immutability_fallback",
}


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


def _normalized_bytes_sha256(raw: bytes) -> str:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ReleaseEvidenceError("qualification source file is not valid UTF-8") from exc
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def _git_blob(repo: Path, ref: str, path: Path) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), "show", f"{ref}:{path.as_posix()}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ReleaseEvidenceError(
            f"cannot read {path.as_posix()} at {ref}: {detail or 'git show failed'}"
        )
    return result.stdout


def _json_at_ref(repo: Path, ref: str, path: Path) -> Mapping[str, Any]:
    try:
        payload = json.loads(_git_blob(repo, ref, path).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleaseEvidenceError(
            f"{path.as_posix()} at {ref} is not valid JSON"
        ) from exc
    if not isinstance(payload, Mapping):
        raise ReleaseEvidenceError(f"{path.as_posix()} at {ref} must be an object")
    return payload


def _json_field_projection(raw: bytes, fields: list[str], *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleaseEvidenceError(f"{label} is not valid JSON") from exc
    if not isinstance(payload, Mapping):
        raise ReleaseEvidenceError(f"{label} must be a JSON object")
    projected: dict[str, Any] = {}
    for field in fields:
        current: Any = payload
        for part in field.split("."):
            if not isinstance(current, Mapping) or part not in current:
                raise ReleaseEvidenceError(f"{label} is missing projected field {field}")
            current = current[part]
        projected[field] = current
    return projected


def _probe_by_id(contract: Mapping[str, Any], probe_id: str) -> Mapping[str, Any]:
    probes = contract.get("required_probes")
    if not isinstance(probes, list):
        raise ReleaseEvidenceError("Host campaign contract required_probes must be an array")
    matches = [item for item in probes if isinstance(item, Mapping) and item.get("id") == probe_id]
    if len(matches) != 1:
        raise ReleaseEvidenceError(f"Host campaign contract must define {probe_id} exactly once")
    return matches[0]


def _probe_qualification_spec(probe: Mapping[str, Any], *, probe_id: str) -> Mapping[str, Any]:
    raw = probe.get("qualification_basis")
    if not isinstance(raw, Mapping) or set(raw) != {
        "runtime_files",
        "runtime_json_fields",
        "shared_contract_fields",
    }:
        raise ReleaseEvidenceError(f"Host campaign {probe_id} qualification_basis is malformed")
    runtime_files = raw.get("runtime_files")
    runtime_json_fields = raw.get("runtime_json_fields")
    shared_fields = raw.get("shared_contract_fields")
    if (
        not isinstance(runtime_files, list)
        or not runtime_files
        or not all(isinstance(item, str) and item.strip() for item in runtime_files)
        or runtime_files != sorted(set(runtime_files))
    ):
        raise ReleaseEvidenceError(
            f"Host campaign {probe_id} qualification_basis.runtime_files must be sorted unique paths"
        )
    if not isinstance(runtime_json_fields, Mapping):
        raise ReleaseEvidenceError(
            f"Host campaign {probe_id} qualification_basis.runtime_json_fields must be an object"
        )
    if not set(runtime_json_fields).issubset(runtime_files):
        raise ReleaseEvidenceError(
            f"Host campaign {probe_id} qualification_basis.runtime_json_fields must reference runtime_files"
        )
    for relative, fields in runtime_json_fields.items():
        if (
            not isinstance(relative, str)
            or not isinstance(fields, list)
            or not fields
            or not all(isinstance(item, str) and item.strip() for item in fields)
            or fields != sorted(set(fields))
        ):
            raise ReleaseEvidenceError(
                f"Host campaign {probe_id} qualification_basis.runtime_json_fields is malformed"
            )
    if (
        not isinstance(shared_fields, list)
        or not shared_fields
        or not all(isinstance(item, str) and item.strip() for item in shared_fields)
        or shared_fields != sorted(set(shared_fields))
    ):
        raise ReleaseEvidenceError(
            f"Host campaign {probe_id} qualification_basis.shared_contract_fields must be sorted unique names"
        )
    return raw


def _legacy_v2_probe_qualification_spec(probe_id: str) -> Mapping[str, Any]:
    if probe_id not in LEGACY_V2_PROBE_RUNTIME_FILES:
        raise ReleaseEvidenceError(f"legacy Host qualification scope has no {probe_id}")
    scope = {
        item: {
            "runtime_files": list(LEGACY_V2_PROBE_RUNTIME_FILES[item]),
            "runtime_json_fields": {
                path: list(fields)
                for path, fields in LEGACY_V2_RUNTIME_JSON_FIELDS[item].items()
            },
            "shared_contract_fields": (
                ["environment_identity_semantics"]
                if item == "N7"
                else ["environment_identity_semantics", "probe_turn_capability_semantics"]
            ),
        }
        for item in REQUIRED_HOST_PROBES
    }
    if canonical_json_sha256(scope) != LEGACY_V2_SCOPE_SHA256:
        raise ReleaseEvidenceError("legacy Host qualification scope changed without an explicit migration")
    return scope[probe_id]


def _probe_qualification_bases(
    repo: Path,
    probe_ids: tuple[str, ...],
    *,
    ref: str,
) -> dict[str, str]:
    """Digest only the Host/runtime surfaces that can affect the requested probes."""
    repo = _resolve_repo(repo)
    current_contract = _load_host_contract(repo)
    source_contract = _json_at_ref(repo, ref, HOST_CAMPAIGN_CONTRACT)
    if source_contract.get("gate_id") != current_contract.get("gate_id"):
        raise ReleaseEvidenceError(f"Host campaign gate_id drifted at {ref}")
    manifest = _json_at_ref(repo, ref, RUNTIME_MANIFEST)
    manifest_files = manifest.get("files")
    if not isinstance(manifest_files, Mapping):
        raise ReleaseEvidenceError(f"runtime manifest at {ref} has no files object")
    file_digest_cache: dict[str, str] = {}
    results: dict[str, str] = {}
    for probe_id in probe_ids:
        _probe_qualification_spec(_probe_by_id(current_contract, probe_id), probe_id=probe_id)
        source_probe_raw = _probe_by_id(source_contract, probe_id)
        source_version = source_contract.get("schema_version")
        if source_version == HOST_CAMPAIGN_CONTRACT_VERSION:
            source_dependency_spec = _probe_qualification_spec(
                source_probe_raw, probe_id=probe_id
            )
        elif source_version == LEGACY_HOST_CAMPAIGN_CONTRACT_VERSION:
            # Historical v2 evidence predates per-probe dependency declarations.
            # Use the pinned reviewed v2 baseline; never project a mutable current
            # dependency map backwards onto old evidence.
            source_dependency_spec = _legacy_v2_probe_qualification_spec(probe_id)
        else:
            raise ReleaseEvidenceError(
                f"Host campaign contract schema_version at {ref} cannot supply qualification provenance"
            )
        source_probe = dict(source_probe_raw)
        source_probe.pop("qualification_basis", None)

        shared_contract: dict[str, Any] = {}
        for field in source_dependency_spec["shared_contract_fields"]:
            if field not in source_contract:
                raise ReleaseEvidenceError(
                    f"Host campaign {probe_id} shared contract field {field} is unavailable at {ref}"
                )
            shared_contract[field] = source_contract[field]

        runtime_files: dict[str, Any] = {}
        for relative in source_dependency_spec["runtime_files"]:
            expected = manifest_files.get(relative)
            if not _valid_hex(expected, 64):
                raise ReleaseEvidenceError(
                    f"Host campaign {probe_id} dependency {relative} is absent from runtime manifest at {ref}"
                )
            actual = file_digest_cache.get(relative)
            if actual is None:
                actual = _normalized_bytes_sha256(_git_blob(repo, ref, Path(relative)))
                file_digest_cache[relative] = actual
            if actual != expected:
                raise ReleaseEvidenceError(
                    f"Host campaign {probe_id} dependency {relative} does not match runtime manifest at {ref}"
                )
            projected_fields = source_dependency_spec["runtime_json_fields"].get(relative)
            if projected_fields is None:
                runtime_files[relative] = {"kind": "full_file", "sha256": actual}
            else:
                projection = _json_field_projection(
                    _git_blob(repo, ref, Path(relative)),
                    list(projected_fields),
                    label=f"Host campaign {probe_id} dependency {relative} at {ref}",
                )
                runtime_files[relative] = {
                    "kind": "json_projection",
                    "fields": list(projected_fields),
                    "sha256": canonical_json_sha256(projection),
                }

        payload = {
            "schema_version": 1,
            "gate_id": current_contract["gate_id"],
            "probe": source_probe,
            "qualification_basis": source_dependency_spec,
            "shared_contract": shared_contract,
            "runtime_files": runtime_files,
        }
        results[probe_id] = canonical_json_sha256(payload)
    return results


def probe_qualification_basis(repo: Path, probe_id: str, *, ref: str = "HEAD") -> str:
    return _probe_qualification_bases(repo, (probe_id,), ref=ref)[probe_id]


def current_probe_qualification_bases(repo: Path) -> dict[str, str]:
    repo = _resolve_repo(repo)
    return _probe_qualification_bases(repo, REQUIRED_HOST_PROBES, ref="HEAD")


def probe_qualification_bases_at_ref(repo: Path, ref: str) -> dict[str, str]:
    repo = _resolve_repo(repo)
    return _probe_qualification_bases(repo, REQUIRED_HOST_PROBES, ref=ref)


def host_qualification_identity_at_ref(repo: Path, ref: str) -> dict[str, str]:
    repo = _resolve_repo(repo)
    return {
        "runtime_manifest_sha256": _normalized_bytes_sha256(_git_blob(repo, ref, RUNTIME_MANIFEST)),
        "profile_contract_sha256": _normalized_bytes_sha256(_git_blob(repo, ref, PROFILE_CONTRACT)),
        "host_contract_sha256": _normalized_bytes_sha256(
            _git_blob(repo, ref, HOST_CAMPAIGN_CONTRACT)
        ),
    }


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
    if payload.get("gate_id") != "v4-real-host-n0-n7":
        raise ReleaseEvidenceError("Host campaign contract gate_id is unsupported")
    if payload.get("status") != "PENDING" or payload.get("results") != {}:
        raise ReleaseEvidenceError("tracked Host campaign contract must remain PENDING with empty results")
    required = payload.get("required_probes")
    if not isinstance(required, list):
        raise ReleaseEvidenceError("Host campaign contract required_probes must be an array")
    ids = [item.get("id") for item in required if isinstance(item, Mapping)]
    if len(ids) != len(required) or tuple(ids) != REQUIRED_HOST_PROBES:
        raise ReleaseEvidenceError("Host campaign contract probes must be exactly ordered N0-N7")
    probe_runtime_files: set[str] = set()
    probe_scope: dict[str, dict[str, Any]] = {}
    for probe_id in REQUIRED_HOST_PROBES:
        probe = _probe_by_id(payload, probe_id)
        spec = _probe_qualification_spec(probe, probe_id=probe_id)
        probe_scope[probe_id] = {
            "runtime_files": list(spec["runtime_files"]),
            "runtime_json_fields": {
                path: list(fields)
                for path, fields in spec["runtime_json_fields"].items()
            },
            "shared_contract_fields": list(spec["shared_contract_fields"]),
        }
        expected_shared = (
            ["environment_identity_semantics"]
            if probe_id == "N7"
            else ["environment_identity_semantics", "probe_turn_capability_semantics"]
        )
        if spec["shared_contract_fields"] != expected_shared:
            raise ReleaseEvidenceError(
                f"Host campaign {probe_id} qualification_basis has unsupported shared contract fields"
            )
        for relative in spec["runtime_files"]:
            path = Path(relative)
            if path.is_absolute() or ".." in path.parts or "." in path.parts:
                raise ReleaseEvidenceError(
                    f"Host campaign {probe_id} qualification dependency is unsafe: {relative}"
                )
            probe_runtime_files.add(relative)
    if canonical_json_sha256(probe_scope) != LEGACY_V2_SCOPE_SHA256:
        raise ReleaseEvidenceError(
            "Host campaign v3 qualification scope changed without a contract-version migration"
        )
    non_probe = payload.get("qualification_non_probe_runtime_files")
    if (
        not isinstance(non_probe, list)
        or not all(isinstance(item, str) and item.strip() for item in non_probe)
        or non_probe != sorted(set(non_probe))
    ):
        raise ReleaseEvidenceError(
            "Host campaign qualification_non_probe_runtime_files must be sorted unique paths"
        )
    for relative in non_probe:
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or "." in path.parts:
            raise ReleaseEvidenceError(
                f"Host campaign non-probe qualification path is unsafe: {relative}"
            )
    overlap = probe_runtime_files.intersection(non_probe)
    if overlap:
        raise ReleaseEvidenceError(
            "Host campaign runtime qualification scope overlaps probe and non-probe paths: "
            + ", ".join(sorted(overlap))
        )
    try:
        manifest_files = set(package_integrity.load_manifest(repo)["files"])
    except (OSError, package_integrity.IntegrityError, KeyError, TypeError) as exc:
        raise ReleaseEvidenceError(f"runtime manifest is unavailable for qualification scope: {exc}") from exc
    classified = probe_runtime_files.union(non_probe)
    if classified != manifest_files:
        missing = sorted(manifest_files - classified)
        extra = sorted(classified - manifest_files)
        detail: list[str] = []
        if missing:
            detail.append("unclassified=" + ",".join(missing))
        if extra:
            detail.append("not-in-manifest=" + ",".join(extra))
        raise ReleaseEvidenceError(
            "Host campaign runtime qualification scope must classify every manifest file exactly once outside probe overlap: "
            + "; ".join(detail)
        )
    if payload.get("required_environment_fields") != sorted(HOST_ENVIRONMENT_FIELDS):
        raise ReleaseEvidenceError("Host campaign contract environment field set is unsupported")
    if payload.get("required_result_fields") != sorted(HOST_RESULT_FIELDS):
        raise ReleaseEvidenceError("Host campaign contract result field set is unsupported")
    return payload


def _advisor_mutation_authority(repo: Path) -> str | None:
    path = repo / PROFILE_CONTRACT
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, Mapping):
        return None
    roles = payload.get("roles")
    if not isinstance(roles, Mapping):
        return None
    advisor = roles.get("advisor")
    if not isinstance(advisor, Mapping):
        return None
    value = advisor.get("mutation_authority")
    return value if isinstance(value, str) else None


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


def host_qualification_identity(identity: Mapping[str, str]) -> dict[str, str]:
    return {field: identity[field] for field in HOST_QUALIFICATION_FIELDS}


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
    mismatch_basis: str,
    issues: list[str],
) -> None:
    for field, actual in expected.items():
        supplied = value.get(field)
        required_length = 40 if field in SOURCE_IDENTITY_FIELDS else 64
        if not _valid_hex(supplied, required_length):
            issues.append(f"{label}.{field} is malformed")
        elif supplied != actual:
            issues.append(f"{label}.{field} does not match {mismatch_basis}")


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


def _validate_host_environments(value: Any, *, issues: list[str]) -> dict[str, Mapping[str, Any]]:
    if not isinstance(value, Mapping) or not value:
        issues.append("host campaign environments must be a non-empty object")
        return {}
    valid: dict[str, Mapping[str, Any]] = {}
    seen_thread_ids: set[str] = set()
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
        thread_id = env.get("thread_id")
        if isinstance(thread_id, str) and thread_id in seen_thread_ids:
            issues.append("host campaign environment thread_id values must be unique")
        elif isinstance(thread_id, str):
            seen_thread_ids.add(thread_id)
        valid[str(environment_id)] = env
    return valid


def _same_stable_host_environment(
    source: Mapping[str, Any], current: Mapping[str, Any]
) -> bool:
    return all(source.get(field) == current.get(field) for field in HOST_STABLE_ENVIRONMENT_FIELDS)


def _validate_git_source_identity(
    repo: Path,
    *,
    commit: Any,
    tree: Any,
    label: str,
    issues: list[str],
) -> bool:
    if not _valid_hex(commit, 40):
        issues.append(f"{label}.source_commit is malformed")
        return False
    if not _valid_hex(tree, 40):
        issues.append(f"{label}.source_tree is malformed")
        return False
    try:
        actual_commit = _git(repo, "rev-parse", f"{commit}^{{commit}}")
        actual_tree = _git(repo, "rev-parse", f"{commit}^{{tree}}")
    except ReleaseEvidenceError as exc:
        issues.append(f"{label} source Git identity is unavailable: {exc}")
        return False
    if actual_commit != commit:
        issues.append(f"{label}.source_commit is not the exact referenced commit")
        return False
    if actual_tree != tree:
        issues.append(f"{label}.source_tree does not match source_commit")
        return False
    return True


def _git_is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", ancestor, descendant],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    detail = result.stderr.decode("utf-8", errors="replace").strip()
    raise ReleaseEvidenceError(
        f"cannot compare Git ancestry {ancestor} -> {descendant}: {detail or 'git merge-base failed'}"
    )


def _source_campaign_probe_truth(
    repo: Path,
    *,
    artifact: Any,
    artifact_sha256: str,
    probe_id: str,
    issues: list[str],
) -> tuple[str, str, Mapping[str, Any], Mapping[str, Any]] | None:
    """Validate one exact predecessor campaign artifact and return its probe truth."""
    label = f"host campaign {probe_id} source campaign artifact"
    wrapper = _exact_fields(
        artifact,
        SOURCE_CAMPAIGN_ARTIFACT_FIELDS,
        label=label,
        issues=issues,
    )
    if wrapper is None:
        return None
    if not _valid_hex(artifact_sha256, 64):
        issues.append(f"{label} key is malformed")
        return None
    if canonical_json_sha256(wrapper) != artifact_sha256:
        issues.append(f"{label} key does not match the exact artifact")
        return None
    source_commit = wrapper.get("source_commit")
    source_tree = wrapper.get("source_tree")
    if not _validate_git_source_identity(
        repo,
        commit=source_commit,
        tree=source_tree,
        label=label,
        issues=issues,
    ):
        return None
    source_campaign = wrapper.get("host_campaign")
    if not isinstance(source_campaign, Mapping):
        issues.append(f"{label}.host_campaign must be an object")
        return None
    supplied_campaign_sha = wrapper.get("host_campaign_sha256")
    if not _valid_hex(supplied_campaign_sha, 64):
        issues.append(f"{label}.host_campaign_sha256 is malformed")
        return None
    if canonical_json_sha256(source_campaign) != supplied_campaign_sha:
        issues.append(f"{label}.host_campaign_sha256 does not match the exact predecessor campaign")
        return None

    schema = source_campaign.get("schema_version")
    if schema == LEGACY_HOST_CAMPAIGN_SCHEMA:
        expected_fields = LEGACY_HOST_CAMPAIGN_FIELDS
        expected_contract = LEGACY_HOST_CAMPAIGN_CONTRACT_VERSION
        result_fields = LEGACY_HOST_RESULT_FIELDS
    elif schema == HOST_CAMPAIGN_SCHEMA:
        expected_fields = HOST_CAMPAIGN_FIELDS
        expected_contract = HOST_CAMPAIGN_CONTRACT_VERSION
        result_fields = HOST_RESULT_FIELDS
    else:
        issues.append(f"{label} schema_version is unsupported as an evidence origin")
        return None
    campaign = _exact_fields(
        source_campaign,
        expected_fields,
        label=f"{label}.host_campaign",
        issues=issues,
    )
    if campaign is None:
        return None
    if campaign.get("repository") != EXPECTED_REPOSITORY:
        issues.append(f"{label} repository identity is invalid")
    if campaign.get("contract_version") != expected_contract:
        issues.append(f"{label} contract_version is invalid")
    if not _nonempty(campaign.get("campaign_id")):
        issues.append(f"{label} campaign_id must be non-empty")
    try:
        source_qualification = host_qualification_identity_at_ref(repo, str(source_commit))
    except ReleaseEvidenceError as exc:
        issues.append(f"{label} source Host qualification identity is unavailable: {exc}")
        return None
    _compare_identity(
        campaign,
        source_qualification,
        label=label,
        mismatch_basis="the source Git qualification basis",
        issues=issues,
    )

    source_environments = _validate_host_environments(campaign.get("environments"), issues=issues)
    source_qualification_environment: Mapping[str, Any] | None = None
    if schema == HOST_CAMPAIGN_SCHEMA:
        source_qualification_environment_id = campaign.get("qualification_environment_id")
        if source_qualification_environment_id not in source_environments:
            issues.append(f"{label} qualification_environment_id references unknown environment")
        else:
            source_qualification_environment = source_environments[
                str(source_qualification_environment_id)
            ]
        if campaign.get("source_campaign_artifacts") != {}:
            issues.append(f"{label} must be an original fresh campaign, not another carry-forward")
    source_results = campaign.get("results")
    if not isinstance(source_results, Mapping):
        issues.append(f"{label} results must be an object")
        return None
    actual_result_ids = set(source_results)
    required_result_ids = set(REQUIRED_HOST_PROBES)
    if actual_result_ids != required_result_ids:
        missing = sorted(required_result_ids - actual_result_ids)
        extra = sorted(actual_result_ids - required_result_ids)
        if missing:
            issues.append(f"{label} missing required probes: {', '.join(missing)}")
        if extra:
            issues.append(f"{label} contains unsupported probes: {', '.join(extra)}")
        return None
    try:
        source_bases = probe_qualification_bases_at_ref(repo, str(source_commit))
    except ReleaseEvidenceError as exc:
        issues.append(f"{label} probe bases are unavailable: {exc}")
        return None
    validated_results: dict[str, Mapping[str, Any]] = {}
    result_environments: dict[str, Mapping[str, Any]] = {}
    for source_probe_id in REQUIRED_HOST_PROBES:
        source_result = _exact_fields(
            source_results[source_probe_id],
            result_fields,
            label=f"{label} {source_probe_id}",
            issues=issues,
        )
        if source_result is None:
            return None
        if source_result.get("status") != "PASS" or not _nonempty(source_result.get("evidence_ref")):
            issues.append(
                f"{label} {source_probe_id} must be a conclusive PASS with evidence_ref"
            )
        source_environment_id = source_result.get("environment_id")
        source_environment = source_environments.get(str(source_environment_id))
        if source_environment is None:
            issues.append(f"{label} {source_probe_id} references an unknown source environment")
            return None
        if (
            source_qualification_environment is not None
            and not _same_stable_host_environment(
                source_environment, source_qualification_environment
            )
        ):
            issues.append(
                f"{label} {source_probe_id} Host build/version/platform/architecture differs from its qualification environment"
            )
        if schema == HOST_CAMPAIGN_SCHEMA:
            if source_result.get("probe_basis_sha256") != source_bases[source_probe_id]:
                issues.append(
                    f"{label} {source_probe_id}.probe_basis_sha256 does not match its source Git basis"
                )
            provenance = _exact_fields(
                source_result.get("provenance"),
                FRESH_PROVENANCE_FIELDS,
                label=f"{label} {source_probe_id} provenance",
                issues=issues,
            )
            if provenance is None or provenance.get("kind") != "fresh":
                issues.append(f"{label} {source_probe_id} must be fresh origin evidence")
            elif (
                provenance.get("source_commit") != source_commit
                or provenance.get("source_tree") != source_tree
            ):
                issues.append(
                    f"{label} {source_probe_id} fresh provenance does not match source Git identity"
                )
        validated_results[source_probe_id] = source_result
        result_environments[source_probe_id] = source_environment

    source_result = validated_results[probe_id]
    source_environment = result_environments[probe_id]
    source_basis = source_bases[probe_id]
    if schema == HOST_CAMPAIGN_SCHEMA:
        if source_qualification_environment is None:
            return None
    return str(source_commit), source_basis, source_result, source_environment


def _validate_probe_provenance(
    repo: Path,
    *,
    probe_id: str,
    result: Mapping[str, Any],
    campaign_id: str,
    qualification_environment: Mapping[str, Any],
    environments: Mapping[str, Mapping[str, Any]],
    source_campaign_artifacts: Mapping[str, Any],
    identity: Mapping[str, str],
    current_basis: str,
    issues: list[str],
) -> None:
    label = f"host campaign {probe_id} provenance"
    supplied_basis = result.get("probe_basis_sha256")
    if not _valid_hex(supplied_basis, 64):
        issues.append(f"host campaign {probe_id}.probe_basis_sha256 is malformed")
    elif supplied_basis != current_basis:
        issues.append(f"host campaign {probe_id}.probe_basis_sha256 does not match current probe basis")

    environment_id = result.get("environment_id")
    source_environment = environments.get(environment_id) if isinstance(environment_id, str) else None
    if source_environment is not None and not _same_stable_host_environment(
        source_environment, qualification_environment
    ):
        issues.append(
            f"host campaign {probe_id} Host build/version/platform/architecture differs from current qualification environment"
        )

    provenance = result.get("provenance")
    if not isinstance(provenance, Mapping):
        issues.append(f"{label} must be an object")
        return
    kind = provenance.get("kind")
    if kind == "fresh":
        value = _exact_fields(provenance, FRESH_PROVENANCE_FIELDS, label=label, issues=issues)
        if value is None:
            return
        if value.get("source_commit") != identity["candidate_commit"]:
            issues.append(f"{label}.source_commit must match exact release source for fresh evidence")
        if value.get("source_tree") != identity["candidate_tree"]:
            issues.append(f"{label}.source_tree must match exact release source for fresh evidence")
        return
    if kind != "carry_forward":
        issues.append(f"{label}.kind must be fresh or carry_forward")
        return

    value = _exact_fields(
        provenance,
        CARRY_FORWARD_PROVENANCE_FIELDS,
        label=label,
        issues=issues,
    )
    if value is None:
        return
    if not _nonempty(value.get("impact_analysis_ref")):
        issues.append(f"{label}.impact_analysis_ref must be non-empty")
    artifact_sha = value.get("source_campaign_artifact_sha256")
    if not _valid_hex(artifact_sha, 64):
        issues.append(f"{label}.source_campaign_artifact_sha256 is malformed")
        return
    artifact = source_campaign_artifacts.get(str(artifact_sha))
    if artifact is None:
        issues.append(f"{label} references an unavailable source campaign artifact")
        return
    truth = _source_campaign_probe_truth(
        repo,
        artifact=artifact,
        artifact_sha256=str(artifact_sha),
        probe_id=probe_id,
        issues=issues,
    )
    if truth is None:
        return
    source_commit, recomputed_source_basis, source_result, source_environment = truth
    if source_commit == identity["candidate_commit"]:
        issues.append(f"{label} source campaign must precede the current release source")
    else:
        try:
            is_ancestor = _git_is_ancestor(repo, source_commit, identity["candidate_commit"])
        except ReleaseEvidenceError as exc:
            issues.append(f"{label} source ancestry is unavailable: {exc}")
            is_ancestor = False
        if not is_ancestor:
            issues.append(f"{label} source campaign must be an ancestor of the current release source")
    if result.get("evidence_ref") != source_result.get("evidence_ref"):
        issues.append(f"{label} must preserve the original source evidence_ref")
    current_result_environment = environments.get(str(environment_id))
    if current_result_environment != source_environment:
        issues.append(f"{label} must preserve the exact six-field source environment identity")
    if not _same_stable_host_environment(source_environment, qualification_environment):
        issues.append(
            f"host campaign {probe_id} Host build/version/platform/architecture differs from current qualification environment"
        )
    if recomputed_source_basis != current_basis:
        issues.append(f"host campaign {probe_id} carry-forward basis changed and must be rerun")


def _validate_host_campaign(
    campaign: Any,
    *,
    repo: Path,
    identity: Mapping[str, str],
    qualification_identity: Mapping[str, str],
    probe_bases: Mapping[str, str],
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
    campaign_id = value.get("campaign_id")
    if not _nonempty(campaign_id):
        issues.append("host campaign campaign_id must be non-empty")
    _compare_identity(
        value,
        qualification_identity,
        label="host campaign",
        mismatch_basis="the current Host qualification basis",
        issues=issues,
    )

    environments = value.get("environments")
    valid_environments = _validate_host_environments(environments, issues=issues)
    environment_ids = set(valid_environments)
    raw_source_artifacts = value.get("source_campaign_artifacts")
    if not isinstance(raw_source_artifacts, Mapping):
        issues.append("host campaign source_campaign_artifacts must be an object")
        source_campaign_artifacts: Mapping[str, Any] = {}
    else:
        source_campaign_artifacts = raw_source_artifacts
        for artifact_sha in source_campaign_artifacts:
            if not _valid_hex(artifact_sha, 64):
                issues.append("host campaign source_campaign_artifacts keys must be sha256 digests")
    qualification_environment_id = value.get("qualification_environment_id")
    if qualification_environment_id not in environment_ids:
        issues.append("host campaign qualification_environment_id references unknown environment")
        qualification_environment: Mapping[str, Any] = {}
    else:
        qualification_environment = valid_environments[str(qualification_environment_id)]
    results = value.get("results")
    if not isinstance(results, Mapping):
        issues.append("host campaign results must be an object")
        return
    actual_ids = set(results)
    required_ids = set(REQUIRED_HOST_PROBES)
    referenced_source_artifacts: set[str] = set()
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
            continue
        if not qualification_environment:
            continue
        provenance = result.get("provenance")
        if isinstance(provenance, Mapping) and provenance.get("kind") == "carry_forward":
            artifact_sha = provenance.get("source_campaign_artifact_sha256")
            if isinstance(artifact_sha, str):
                referenced_source_artifacts.add(artifact_sha)
        _validate_probe_provenance(
            repo,
            probe_id=probe_id,
            result=result,
            campaign_id=str(campaign_id),
            qualification_environment=qualification_environment,
            environments=valid_environments,
            source_campaign_artifacts=source_campaign_artifacts,
            identity=identity,
            current_basis=probe_bases[probe_id],
            issues=issues,
        )
    unused_source_artifacts = sorted(set(source_campaign_artifacts) - referenced_source_artifacts)
    if unused_source_artifacts:
        issues.append(
            "host campaign contains unreferenced source campaign artifacts: "
            + ", ".join(unused_source_artifacts)
        )


def _validate_final_review(
    review: Any,
    *,
    identity: Mapping[str, str],
    review_artifact_id: str,
    review_request: Mapping[str, Any] | None,
    issues: list[str],
) -> None:
    value = _exact_fields(review, FINAL_REVIEW_FIELDS, label="final review", issues=issues)
    if value is None:
        return
    if value.get("schema_version") != FINAL_REVIEW_SCHEMA:
        issues.append("final review.schema_version is unsupported")
    for field in SOURCE_IDENTITY_FIELDS:
        if value.get(field) != identity[field]:
            issues.append(f"final review.{field} does not match the exact release source")
    if value.get("review_artifact_id") != review_artifact_id:
        issues.append("final review.review_artifact_id does not match the current candidate")
    if review_request is not None:
        request_digest = canonical_json_sha256(review_request)
        supplied_request_digest = value.get("review_request_sha256")
        if supplied_request_digest != request_digest:
            issues.append("final review.review_request_sha256 does not match the bound pre-review request")
        if value.get("hard_isolation_required") != review_request.get("hard_isolation_required"):
            issues.append("final review hard_isolation_required does not match the bound pre-review request")
        if value.get("no_edit_instruction") != review_request.get("no_edit_instruction"):
            issues.append("final review no_edit_instruction does not match the bound pre-review request")
    if value.get("verdict") != "ship":
        issues.append("final review verdict must be ship")
    permission = value.get("permission_observation")
    if permission not in PERMISSION_OBSERVATIONS:
        issues.append("final review permission_observation is unsupported")
    assurance = value.get("assurance_mode")
    if assurance not in FINAL_REVIEW_ASSURANCE_MODES:
        issues.append("final review assurance_mode is unsupported")
    if value.get("artifact_unchanged") is not True:
        issues.append("final review requires artifact_unchanged=true")
    hard_isolation = value.get("hard_isolation_required")
    if not isinstance(hard_isolation, bool):
        issues.append("final review hard_isolation_required must be boolean")
    if value.get("no_edit_instruction") is not True:
        issues.append("final review requires no_edit_instruction=true")
    if not isinstance(value.get("residual_risk"), str):
        issues.append("final review residual_risk must be a string")

    if permission == "effective_read_only":
        if assurance != "enforced_read_only":
            issues.append(
                "final review effective_read_only permission requires enforced_read_only assurance"
            )
    elif permission == "broader_write_capable":
        if assurance != "artifact_immutability_fallback":
            issues.append(
                "final review broader_write_capable permission requires artifact_immutability_fallback assurance"
            )
        if hard_isolation is not False:
            issues.append(
                "final review artifact immutability fallback cannot satisfy hard isolation"
            )
        if not _nonempty(value.get("residual_risk")):
            issues.append(
                "final review broader permission fallback requires residual_risk disclosure"
            )
    elif permission == "unobservable":
        issues.append("final review permission observation is unavailable")

    if assurance == "artifact_immutability_fallback" and permission != "broader_write_capable":
        issues.append(
            "final review artifact_immutability_fallback requires broader_write_capable observation"
        )
    if assurance == "enforced_read_only" and permission != "effective_read_only":
        issues.append(
            "final review enforced_read_only assurance requires effective_read_only observation"
        )
    if not _nonempty(value.get("evidence_ref")):
        issues.append("final review ship verdict requires evidence_ref")


def _validate_final_review_request(
    request: Any,
    *,
    identity: Mapping[str, str],
    review_artifact_id: str,
    issues: list[str],
) -> Mapping[str, Any] | None:
    value = _exact_fields(
        request,
        FINAL_REVIEW_REQUEST_FIELDS,
        label="final review request",
        issues=issues,
    )
    if value is None:
        return None
    if value.get("schema_version") != FINAL_REVIEW_REQUEST_SCHEMA:
        issues.append("final review request.schema_version is unsupported")
    for field in SOURCE_IDENTITY_FIELDS:
        if value.get(field) != identity[field]:
            issues.append(f"final review request.{field} does not match the exact release source")
    if value.get("review_artifact_id") != review_artifact_id:
        issues.append("final review request.review_artifact_id does not match the current candidate")
    if not isinstance(value.get("hard_isolation_required"), bool):
        issues.append("final review request hard_isolation_required must be boolean")
    if value.get("no_edit_instruction") is not True:
        issues.append("final review request requires no_edit_instruction=true before reviewer launch")
    if value.get("reviewer_agent_type") != "subagents_dispatch_advisor":
        issues.append("final review request must select subagents_dispatch_advisor")
    if value.get("fork_turns") != "none":
        issues.append("final review request must require fork_turns=none")
    if value.get("fresh_context") is not True:
        issues.append("final review request must require fresh_context=true")
    if not _nonempty(value.get("evidence_ref")):
        issues.append("final review request requires evidence_ref")
    return value


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
    qualification_identity = host_qualification_identity(identity)
    try:
        probe_bases = current_probe_qualification_bases(candidate)
    except ReleaseEvidenceError as exc:
        return {"ok": False, "issues": issues + [str(exc)], **identity}

    status = _git(candidate, "status", "--porcelain", "--untracked-files=all")
    if status:
        issues.append("candidate repository must be clean before release evidence can be authoritative")

    package_result = package_integrity.verify_package(candidate)
    if package_result.get("ok") is not True:
        issues.append("candidate package integrity verification failed")
    generated_result = package_integrity.check_generated(candidate)
    if generated_result.get("ok") is not True:
        issues.append("candidate package integrity manifest does not match the current runtime file set")
    if _advisor_mutation_authority(candidate) != "none":
        issues.append("bound Advisor profile must retain semantic mutation_authority=none")

    top = _exact_fields(payload, TOP_LEVEL_FIELDS, label="release evidence", issues=issues)
    if top is not None:
        if top.get("schema_version") != RELEASE_EVIDENCE_SCHEMA:
            issues.append("release evidence schema_version is unsupported")
        if top.get("repository") != EXPECTED_REPOSITORY:
            issues.append("release evidence repository identity is invalid")
        _compare_identity(
            top,
            identity,
            label="release evidence",
            mismatch_basis="the exact release source and qualification basis",
            issues=issues,
        )
        _validate_host_campaign_digest(top, issues=issues)

    try:
        review_artifact_id = current_review_artifact_id(candidate)
    except ReleaseEvidenceError as exc:
        issues.append(str(exc))
        review_artifact_id = ""

    if top is not None:
        _validate_host_campaign(
            top.get("host_campaign"),
            repo=candidate,
            identity=identity,
            qualification_identity=qualification_identity,
            probe_bases=probe_bases,
            issues=issues,
        )
        review_request = _validate_final_review_request(
            top.get("final_review_request"),
            identity=identity,
            review_artifact_id=review_artifact_id,
            issues=issues,
        )
        _validate_final_review(
            top.get("final_review"),
            identity=identity,
            review_artifact_id=review_artifact_id,
            review_request=review_request,
            issues=issues,
        )

    return {
        "ok": not issues,
        "issues": issues,
        **identity,
        "review_artifact_id": review_artifact_id,
        "required_host_probes": list(REQUIRED_HOST_PROBES),
        "probe_qualification_bases": probe_bases,
    }


def compare_host_qualification(repo: Path, source_ref: str) -> dict[str, Any]:
    """Classify per-probe Git basis compatibility; this does not authorize Host reuse."""
    candidate = _resolve_repo(repo)
    status = _git(candidate, "status", "--porcelain", "--untracked-files=all")
    if status:
        return {
            "ok": False,
            "issues": ["candidate repository must be clean before Host reuse classification"],
        }
    package_result = package_integrity.verify_package(candidate)
    generated_result = package_integrity.check_generated(candidate)
    if package_result.get("ok") is not True or generated_result.get("ok") is not True:
        return {
            "ok": False,
            "issues": ["candidate package integrity must pass before Host reuse classification"],
        }
    try:
        current_identity = current_candidate_identity(candidate)
        source_commit = _git(candidate, "rev-parse", f"{source_ref}^{{commit}}")
        source_tree = _git(candidate, "rev-parse", f"{source_commit}^{{tree}}")
        if not _git_is_ancestor(candidate, source_commit, current_identity["candidate_commit"]):
            return {
                "ok": False,
                "issues": [
                    "Host qualification comparison source must be an ancestor of the current release source"
                ],
            }
        source_qualification = host_qualification_identity_at_ref(candidate, source_commit)
        source_bases = probe_qualification_bases_at_ref(candidate, source_commit)
        current_bases = current_probe_qualification_bases(candidate)
        source_manifest = _json_at_ref(candidate, source_commit, RUNTIME_MANIFEST)
        current_manifest = package_integrity.load_manifest(candidate)
    except (ReleaseEvidenceError, package_integrity.IntegrityError) as exc:
        return {"ok": False, "issues": [str(exc)]}

    source_files = source_manifest.get("files")
    current_files = current_manifest.get("files")
    if not isinstance(source_files, Mapping) or not isinstance(current_files, Mapping):
        return {"ok": False, "issues": ["runtime manifests must contain files objects"]}
    changed_runtime_files = sorted(
        path
        for path in set(source_files) | set(current_files)
        if source_files.get(path) != current_files.get(path)
    )
    affected = [
        probe_id
        for probe_id in REQUIRED_HOST_PROBES
        if source_bases[probe_id] != current_bases[probe_id]
    ]
    compatible = [probe_id for probe_id in REQUIRED_HOST_PROBES if probe_id not in affected]
    return {
        "ok": True,
        "issues": [],
        "source_commit": source_commit,
        "source_tree": source_tree,
        "current_commit": current_identity["candidate_commit"],
        "current_tree": current_identity["candidate_tree"],
        "source_host_qualification_identity": source_qualification,
        "current_host_qualification_identity": host_qualification_identity(current_identity),
        "changed_runtime_files": changed_runtime_files,
        "affected_host_probes": affected,
        "basis_compatible_host_probes": compatible,
        "reuse_authorized": False,
        "reuse_requires_verified_source_campaign_and_environment": True,
        "source_probe_qualification_bases": source_bases,
        "current_probe_qualification_bases": current_bases,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify external Native Core V4 release evidence.")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--evidence", type=Path)
    mode.add_argument("--compare-ref")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = (
        compare_host_qualification(args.repo, args.compare_ref)
        if args.compare_ref is not None
        else verify_release_evidence(args.repo, args.evidence)
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    elif result["ok"]:
        if args.compare_ref is not None:
            print("V4 HOST QUALIFICATION DELTA CLASSIFICATION PASS")
            print("affected: " + (", ".join(result["affected_host_probes"]) or "none"))
            print(
                "basis-compatible: "
                + (", ".join(result["basis_compatible_host_probes"]) or "none")
            )
            print("reuse-authorized: no (requires verified predecessor campaign and Host environment)")
        else:
            print("V4 RELEASE EVIDENCE PASS")
    else:
        print("V4 RELEASE EVIDENCE FAIL")
        for issue in result["issues"]:
            print(f"- {issue}")
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
