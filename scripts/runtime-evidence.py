#!/usr/bin/env python3
"""Normalize optional subagents-dispatch runtime evidence.

This helper is diagnostic. Ordinary routing must not depend on telemetry that the
runtime did not expose. Main-session evidence only suppresses a redundant Sol uplift
when the observed main route meets the policy reference. Child evidence verifies exact
route, ancestry, and permission claims only when those facts are material.

Route truth is kept in three layers when the host exposes them: requested, accepted,
and observed. Platform acceptance never counts as observed runtime proof. For child
attestation, observed runtime truth may come from public native metadata, an exact
Host-produced local rollout record, or both; those sources must agree where they overlap.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys
from typing import Any, NoReturn

from policy import load_policy_contract

CHILD_ROUTE_FIELDS = ("agent_role", "model", "effort")
MAIN_ROUTE_FIELDS = ("model", "effort")
IDENTITY_FIELDS = ("thread_id", "parent_thread_id")
PERMISSION_FIELDS = ("sandbox_policy_type", "permission_profile_type")
AUXILIARY_OBSERVED_FIELDS = ("agent_path", "model_provider", "cwd")
V2_AGENT_PATH = re.compile(r"^/root(?:/(?!root(?:/|$))[a-z0-9_]+)+$")
OBSERVED_FIELDS = (*CHILD_ROUTE_FIELDS, *IDENTITY_FIELDS, *PERMISSION_FIELDS, *AUXILIARY_OBSERVED_FIELDS)
PERMISSION_PROVENANCE_FIELDS = (
    "source_kind",
    "source_id",
    *PERMISSION_FIELDS,
    "evidence_ref",
    "selection_evidence_ref",
)


def fail(message: str) -> NoReturn:
    raise SystemExit(f"ERROR: {message}")


def canonical_sandbox(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower().replace("_", "-").replace(" ", "-")
    aliases = {
        "readonly": "read-only",
        "read-only": "read-only",
        "workspacewrite": "workspace-write",
        "workspace-write": "workspace-write",
    }
    return aliases.get(normalized, normalized)


def load_main_coverage_policy() -> tuple[str, str, tuple[str, ...], tuple[str, ...]]:
    try:
        payload = load_policy_contract()
        dedup = payload["capability_dedup"]
        role = dedup["reference_role"]
        order = dedup["reasoning_effort_order"]
        aliases = dedup.get("model_aliases", [])
        reference = payload["roles"][role]
        model = reference["model"]
        effort = reference["effort"]
    except (RuntimeError, KeyError, TypeError) as exc:
        fail(f"invalid policy contract for capability dedup: {exc}")
    if not isinstance(model, str) or not model.strip() or not isinstance(effort, str) or not effort.strip():
        fail("capability dedup reference route is invalid")
    if not isinstance(order, list) or not order or not all(isinstance(x, str) and x for x in order):
        fail("reasoning_effort_order must be a non-empty string list")
    if not isinstance(aliases, list) or not all(isinstance(x, str) and x.strip() for x in aliases):
        fail("model_aliases must be a string list when present")
    normalized_order = tuple(x.strip().lower() for x in order)
    normalized_aliases = tuple(x.strip().lower() for x in aliases)
    if effort.strip().lower() not in normalized_order or len(set(normalized_order)) != len(normalized_order):
        fail("reasoning_effort_order does not contain a unique reference effort")
    if len(set(normalized_aliases)) != len(normalized_aliases):
        fail("model_aliases contains duplicates")
    return model.strip().lower(), effort.strip().lower(), normalized_order, normalized_aliases


def load_permission_policy() -> tuple[frozenset[str], frozenset[str]]:
    try:
        policy = load_policy_contract()
        roles = policy["roles"]
        semantics = policy["permission_semantics"]
    except (RuntimeError, KeyError, TypeError) as exc:
        fail(f"invalid Host permission policy: {exc}")
    if not isinstance(roles, dict) or not roles:
        fail("policy roles must be a non-empty object")
    agent_types: set[str] = set()
    for role_name, route in roles.items():
        if not isinstance(route, dict):
            fail(f"policy role {role_name!r} must be an object")
        agent_type = route.get("agent_type")
        if not isinstance(agent_type, str) or not agent_type.strip():
            fail(f"policy role {role_name!r} has invalid agent_type")
        if agent_type in agent_types:
            fail(f"duplicate managed agent_type in policy: {agent_type}")
        agent_types.add(agent_type)
    if not isinstance(semantics, dict):
        fail("permission_semantics must be an object")
    sources = semantics.get("candidate_source_kinds")
    if not isinstance(sources, list):
        fail("permission_semantics must declare candidate_source_kinds")
    if not sources or not all(isinstance(item, str) and item for item in sources):
        fail("permission_semantics.candidate_source_kinds must be a non-empty string list")
    return frozenset(agent_types), frozenset(sources)


REFERENCE_MODEL, REFERENCE_EFFORT, EFFORT_ORDER, REFERENCE_MODEL_ALIASES = load_main_coverage_policy()
MANAGED_AGENT_TYPES, PERMISSION_SOURCE_KINDS = load_permission_policy()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize subagents-dispatch runtime evidence.")
    parser.add_argument("--input", type=Path, help="JSON input file; defaults to stdin.")
    return parser.parse_args()


def rollout_observation(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        fail("rollout must be an object or null")
    allowed = {"thread_id", "sessions_dir", "expected_parent_thread_id", "expected_agent_role"}
    if set(value) - allowed:
        fail("rollout contains unsupported fields")
    thread_id = text(value.get("thread_id"))
    sessions_dir = text(value.get("sessions_dir"))
    if thread_id is None or sessions_dir is None:
        fail("rollout requires exact thread_id and sessions_dir")
    inspector_path = Path(__file__).with_name("inspect-agent-runtime.py")
    spec = importlib.util.spec_from_file_location("runtime_rollout_inspector", inspector_path)
    if spec is None or spec.loader is None:
        fail("could not load rollout inspector")
    inspector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inspector)
    child = inspector.canonical_uuid(thread_id, "rollout.thread_id")
    parent = text(value.get("expected_parent_thread_id"))
    if parent is not None:
        parent = inspector.canonical_uuid(parent, "rollout.expected_parent_thread_id")
    root = Path(sessions_dir).expanduser()
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        fail("rollout sessions_dir must be an absolute regular directory")
    matched = inspector.find_exact_rollout(root.resolve(), child)
    result = inspector.inspect_rollout(
        matched,
        thread_id=child,
        expected_parent_thread_id=parent,
        expected_agent_role=text(value.get("expected_agent_role")),
    )
    missing = [field for field in CHILD_ROUTE_FIELDS if text(result.get(field)) is None]
    if missing:
        fail("exact rollout is missing required fields: " + ", ".join(missing))
    return result


def load_payload(path: Path | None) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8") if path else sys.stdin.read()
        value = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(f"invalid runtime-evidence input: {exc}")
    if not isinstance(value, dict):
        fail("runtime-evidence input must be a JSON object")
    return value


def obj(value: Any, field: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        fail(f"{field} must be an object or null")
    return value


def text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def canonical_v2_agent_path(value: Any, label: str) -> str | None:
    path = text(value)
    if path is None:
        return None
    if V2_AGENT_PATH.fullmatch(path) is None:
        fail(f"{label} must be a canonical V2 task path under /root")
    return path


def normalize(value: dict[str, Any] | None) -> dict[str, str | None] | None:
    if value is None:
        return None
    allowed = {
        "thread_id",
        "parent_thread_id",
        "agent_role",
        "model",
        "effort",
        "sandbox_policy_type",
        "permission_profile_type",
        "agent_path",
        "model_provider",
        "cwd",
        "runtime_version",
        "record_format_version",
    }
    normalized = {key: text(value.get(key)) for key in allowed}
    normalized["sandbox_policy_type"] = canonical_sandbox(normalized["sandbox_policy_type"])
    return normalized


def normalize_permission_source(
    value: dict[str, Any] | None,
    field: str,
) -> dict[str, str | None] | None:
    if value is None:
        return None
    normalized = {
        "source_kind": text(value.get("source_kind")),
        "source_id": text(value.get("source_id")),
        "sandbox_policy_type": canonical_sandbox(text(value.get("sandbox_policy_type"))),
        "permission_profile_type": text(value.get("permission_profile_type")),
        "evidence_ref": text(value.get("evidence_ref")),
        "selection_evidence_ref": text(value.get("selection_evidence_ref")),
    }
    if normalized["source_kind"] is not None and normalized["source_kind"] not in PERMISSION_SOURCE_KINDS:
        fail(f"{field}.source_kind is not allowed by policy")
    return normalized


def merged_permission_source(
    native: dict[str, str | None] | None,
    local: dict[str, str | None] | None,
) -> tuple[dict[str, str | None] | None, str]:
    if native is None and local is None:
        return None, "none"
    merged = {
        field: (
            native.get(field)
            if native is not None and native.get(field) is not None
            else local.get(field) if local is not None else None
        )
        for field in PERMISSION_PROVENANCE_FIELDS
    }
    return merged, evidence_source(native is not None, local is not None)


def seen(obs: dict[str, str | None] | None, fields: tuple[str, ...]) -> list[str]:
    return [] if obs is None else [field for field in fields if obs.get(field) is not None]


def evidence_source(native: bool, local: bool) -> str:
    if native and local:
        return "both"
    if native:
        return "native"
    if local:
        return "local"
    return "none"


def grade(native: bool, local: bool, conflict: bool) -> str:
    if conflict:
        return "X0_conflicted"
    if native and local:
        return "R2_runtime_reported_and_local_record_agree"
    if native:
        return "R1_runtime_reported"
    if local:
        return "L1_local_record_observed"
    return "C1_configuration_only"


def source_conflicts(
    native: dict[str, str | None] | None,
    local: dict[str, str | None] | None,
    fields: tuple[str, ...],
) -> list[str]:
    if native is None or local is None:
        return []
    return [
        f"source_conflict:{field}"
        for field in fields
        if native.get(field) is not None and local.get(field) is not None and native[field] != local[field]
    ]


def layer_conflicts(
    accepted: dict[str, str | None] | None,
    observed: dict[str, str | None] | None,
    fields: tuple[str, ...],
) -> list[str]:
    if accepted is None or observed is None:
        return []
    return [
        f"accepted_observed_conflict:{field}"
        for field in fields
        if accepted.get(field) is not None
        and observed.get(field) is not None
        and accepted[field] != observed[field]
    ]


def requested_layer(requested: dict[str, Any] | None, fields: tuple[str, ...]) -> dict[str, Any]:
    declared = {} if requested is None else {field: text(requested.get(field)) for field in fields}
    visible = {field: value for field, value in declared.items() if value is not None}
    return {
        "status": "declared" if visible else "not_declared",
        "fields": visible,
    }


def reported_layer(
    observation: dict[str, str | None] | None,
    fields: tuple[str, ...],
    *,
    conflict: bool,
    missing_status: str,
) -> dict[str, Any]:
    present_fields = seen(observation, fields)
    if conflict:
        status = "conflict"
    elif not present_fields:
        status = missing_status
    elif all(observation and observation.get(field) is not None for field in fields):
        status = "matched"
    else:
        status = "partial"
    return {
        "status": status,
        "fields": {field: observation[field] for field in present_fields} if observation is not None else {},
    }


def accepted_layer(
    accepted: dict[str, str | None] | None,
    fields: tuple[str, ...],
    violations: list[str],
) -> dict[str, Any]:
    conflict = any(
        item in {
            f"accepted:{field}_mismatch",
            f"accepted_observed_conflict:{field}",
        }
        for item in violations
        for field in fields
    )
    return reported_layer(
        accepted,
        fields,
        conflict=conflict,
        missing_status="not_reported",
    )


def observed_layer(
    native: dict[str, str | None] | None,
    fields: tuple[str, ...],
    violations: list[str],
) -> dict[str, Any]:
    conflict = any(
        item in {
            f"native:{field}_mismatch",
            f"accepted_observed_conflict:{field}",
            f"source_conflict:{field}",
        }
        for item in violations
        for field in fields
    )
    return reported_layer(
        native,
        fields,
        conflict=conflict,
        missing_status="not_observed",
    )


def runtime_observed_layer(
    native: dict[str, str | None] | None,
    local: dict[str, str | None] | None,
    fields: tuple[str, ...],
    violations: list[str],
) -> dict[str, Any]:
    conflict_fields = {
        field
        for field in fields
        if any(
            item in {
                f"native:{field}_mismatch",
                f"local:{field}_mismatch",
                f"accepted_observed_conflict:{field}",
                f"source_conflict:{field}",
            }
            for item in violations
        )
    }
    values: dict[str, str] = {}
    sources: dict[str, str] = {}
    for field in fields:
        if field in conflict_fields:
            continue
        native_value = native.get(field) if native is not None else None
        local_value = local.get(field) if local is not None else None
        if native_value is not None:
            values[field] = native_value
            sources[field] = "both" if local_value is not None else "native"
        elif local_value is not None:
            values[field] = local_value
            sources[field] = "local"

    if conflict_fields:
        status = "conflict"
    elif not values:
        status = "not_observed"
    elif all(field in values for field in fields):
        status = "matched"
    else:
        status = "partial"
    result: dict[str, Any] = {
        "status": status,
        "fields": values,
        "source_by_field": sources,
    }
    if conflict_fields:
        result["conflict_fields"] = sorted(conflict_fields)
    return result


def runtime_fields_complete(
    native: dict[str, str | None] | None,
    local: dict[str, str | None] | None,
    fields: tuple[str, ...],
    violations: list[str],
) -> bool:
    for field in fields:
        if any(
            item in {
                f"native:{field}_mismatch",
                f"local:{field}_mismatch",
                f"accepted_observed_conflict:{field}",
                f"source_conflict:{field}",
            }
            for item in violations
        ):
            return False
        if not (
            native is not None
            and native.get(field) is not None
            or local is not None
            and local.get(field) is not None
        ):
            return False
    return True


def model_matches(model: str) -> bool:
    normalized = model.lower()
    if normalized in REFERENCE_MODEL_ALIASES:
        return True
    return normalized == REFERENCE_MODEL or normalized.startswith(REFERENCE_MODEL + "-")


def effort_coverage(effort: str) -> str:
    normalized = effort.lower()
    if normalized not in EFFORT_ORDER:
        return "unknown"
    return "covered" if EFFORT_ORDER.index(normalized) >= EFFORT_ORDER.index(REFERENCE_EFFORT) else "uncovered"


def main_session_result(payload: dict[str, Any]) -> dict[str, Any]:
    requested = obj(payload.get("requested"), "requested")
    accepted = normalize(obj(payload.get("accepted"), "accepted"))
    native = normalize(obj(payload.get("native"), "native"))
    local = normalize(obj(payload.get("local"), "local"))
    violations = source_conflicts(native, local, MAIN_ROUTE_FIELDS)
    if requested is not None and accepted is not None:
        violations.extend(compare_expected(requested, accepted, "accepted", fields=MAIN_ROUTE_FIELDS))
    violations.extend(layer_conflicts(accepted, native, MAIN_ROUTE_FIELDS))
    native_fields, local_fields = seen(native, MAIN_ROUTE_FIELDS), seen(local, MAIN_ROUTE_FIELDS)
    observed_fields = sorted(set(native_fields + local_fields))
    native_complete = native is not None and all(native.get(field) for field in MAIN_ROUTE_FIELDS)
    local_complete = local is not None and all(local.get(field) for field in MAIN_ROUTE_FIELDS)
    conflict = bool(violations)

    if conflict:
        status = "conflict"
    elif native_complete or local_complete:
        status = "observed"
    elif observed_fields:
        status = "partial"
    else:
        status = "not_observed"

    coverage = "unknown"
    if native_complete and not conflict and native is not None:
        model = str(native.get("model") or "")
        effort = str(native.get("effort") or "")
        coverage = "uncovered" if not model_matches(model) else effort_coverage(effort)

    trusted = native_complete and not conflict
    return {
        "subject": "main_session",
        "status": status,
        "decision": "quarantine_main_route_claim" if conflict else "use_observed_coverage",
        "evidence_grade": grade(native_complete, local_complete, conflict),
        "truth_layers": {
            "requested": requested_layer(requested, MAIN_ROUTE_FIELDS),
            "accepted": accepted_layer(accepted, MAIN_ROUTE_FIELDS, violations),
            "observed": observed_layer(native, MAIN_ROUTE_FIELDS, violations),
        },
        "route_evidence": {
            "status": status,
            "source": evidence_source(native_complete, local_complete),
            "observed_fields": observed_fields,
            "native_observed_fields": native_fields,
            "local_observed_fields": local_fields,
        },
        "main_judgment_coverage": coverage,
        "coverage_source": "trusted_session_metadata" if trusted else "not_observed",
        "coverage_reference_model": REFERENCE_MODEL,
        "coverage_reference_model_aliases": list(REFERENCE_MODEL_ALIASES),
        "coverage_reference_effort": REFERENCE_EFFORT,
        "observed_main_model": native.get("model") if trusted and native is not None else None,
        "observed_main_effort": native.get("effort") if trusted and native is not None else None,
        "violations": sorted(set(violations)),
    }


def validate_expected(expected: dict[str, Any]) -> None:
    missing = [field for field in CHILD_ROUTE_FIELDS if text(expected.get(field)) is None]
    if missing:
        fail("expected exact route is incomplete; missing: " + ", ".join(missing))
    for flag in (
        "runtime_observation_required",
        "requires_enforced_read_only",
        "requires_permission_observation",
        "requires_permission_provenance",
    ):
        if not isinstance(expected.get(flag, False), bool):
            fail(f"expected.{flag} must be boolean when present")
    agent_role = text(expected.get("agent_role"))
    if agent_role not in MANAGED_AGENT_TYPES and not (
        agent_role and agent_role.startswith("subagents_dispatch_calibration_")
    ):
        fail("expected.agent_role is not a managed policy role")
    canonical_v2_agent_path(expected.get("agent_path"), "expected.agent_path")


def compare_expected(
    expected: dict[str, Any],
    observation: dict[str, str | None],
    label: str,
    fields: tuple[str, ...] = (*IDENTITY_FIELDS, *CHILD_ROUTE_FIELDS, *AUXILIARY_OBSERVED_FIELDS),
) -> list[str]:
    violations: list[str] = []
    for field in fields:
        wanted, got = text(expected.get(field)), observation.get(field)
        matches = wanted == got
        if wanted is not None and got is not None and not matches:
            violations.append(f"{label}:{field}_mismatch")
    return violations


def route_complete(
    observation: dict[str, str | None] | None,
    label: str,
    violations: list[str],
) -> bool:
    if observation is None:
        return False
    return all(observation.get(field) is not None for field in CHILD_ROUTE_FIELDS) and not any(
        f"{label}:{field}_mismatch" in violations for field in CHILD_ROUTE_FIELDS
    )


def permission_results(
    expected: dict[str, Any],
    native: dict[str, str | None] | None,
    local: dict[str, str | None] | None,
    effective_source: dict[str, str | None] | None,
    effective_source_kind: str,
    violations: list[str],
) -> tuple[dict[str, Any], dict[str, Any], bool, bool]:
    requires_read_only = expected.get("requires_enforced_read_only", False)
    state_required = bool(
        expected.get("requires_permission_observation", False) or requires_read_only
    )
    provenance_required = bool(expected.get("requires_permission_provenance", False))
    if any(f"source_conflict:{field}" in violations for field in PERMISSION_FIELDS):
        state_violations = [
            f"source_conflict:{field}"
            for field in PERMISSION_FIELDS
            if f"source_conflict:{field}" in violations
        ]
        return (
            {"status": "failed", "source": "both", "violations": state_violations},
            {"status": "unknown", "source": "none", "violations": []},
            state_required,
            provenance_required,
        )

    observed = {}
    for field in PERMISSION_FIELDS:
        native_value = native.get(field) if native else None
        observed[field] = native_value if native_value is not None else local.get(field) if local else None
    observed_source = evidence_source(
        any(native and native.get(field) is not None for field in PERMISSION_FIELDS),
        any(local and local.get(field) is not None for field in PERMISSION_FIELDS),
    )
    state = {
        "status": "verified" if all(observed[field] is not None for field in PERMISSION_FIELDS) else "unknown",
        "source": observed_source,
        "observed_sandbox": observed["sandbox_policy_type"],
        "observed_permission_profile": observed["permission_profile_type"],
        "violations": [],
    }
    if state["status"] == "verified" and requires_read_only and observed["sandbox_policy_type"] != "read-only":
        violations.append("permission:read_only_not_enforced")
        state["status"] = "failed"
        state["violations"] = ["permission:read_only_not_enforced"]

    provenance_conflicts = sorted(
        item for item in set(violations) if item.startswith("permission_source_conflict:")
    )
    if provenance_conflicts:
        return (
            state,
            {
                "status": "failed",
                "source": "both",
                "violations": provenance_conflicts,
            },
            state_required,
            provenance_required,
        )

    required_source_fields = (
        "source_kind",
        "source_id",
        "evidence_ref",
        "selection_evidence_ref",
        *PERMISSION_FIELDS,
    )
    source_complete = effective_source is not None and all(
        effective_source.get(field) is not None for field in required_source_fields
    )
    observed_complete = state["status"] != "unknown"
    if not source_complete or not observed_complete:
        return (
            state,
            {"status": "unknown", "source": "none", "violations": []},
            state_required,
            provenance_required,
        )

    assert effective_source is not None
    provenance = {
        "status": "verified",
        "source": effective_source_kind,
        "source_kind": effective_source["source_kind"],
        "source_id": effective_source["source_id"],
        "source_evidence_ref": effective_source["evidence_ref"],
        "selection_evidence_ref": effective_source["selection_evidence_ref"],
        "source_sandbox": effective_source["sandbox_policy_type"],
        "source_permission_profile": effective_source["permission_profile_type"],
        "violations": [],
    }
    if effective_source["source_kind"] == "parent_turn":
        expected_parent = text(expected.get("parent_thread_id"))
        if expected_parent is None:
            return (
                state,
                {"status": "unknown", "source": "none", "violations": []},
                state_required,
                provenance_required,
            )
        if effective_source["source_id"] != expected_parent:
            violations.append("permission:source_identity_mismatch")
            provenance["status"] = "failed"
            provenance["violations"] = ["permission:source_identity_mismatch"]
            return state, provenance, state_required, provenance_required
    if any(observed[field] != effective_source[field] for field in PERMISSION_FIELDS):
        violations.append("permission:provenance_state_mismatch")
        provenance["status"] = "failed"
        provenance["violations"] = ["permission:provenance_state_mismatch"]
    return state, provenance, state_required, provenance_required


def child_result(payload: dict[str, Any]) -> dict[str, Any]:
    if "effective_permission_source" in payload:
        fail(
            "effective_permission_source is not Host-observed evidence; use "
            "native_permission_source or local_permission_source"
        )
    expected = obj(payload.get("expected"), "expected")
    if expected is None:
        fail("expected is required for child evidence")
    validate_expected(expected)
    accepted = normalize(obj(payload.get("accepted"), "accepted"))
    native = normalize(obj(payload.get("native"), "native"))
    local = normalize(obj(payload.get("local"), "local"))
    for label, observation in (("accepted", accepted), ("native", native), ("local", local)):
        if observation is not None:
            canonical_v2_agent_path(observation.get("agent_path"), f"{label}.agent_path")
    native_permission_source = normalize_permission_source(
        obj(payload.get("native_permission_source"), "native_permission_source"),
        "native_permission_source",
    )
    local_permission_source = normalize_permission_source(
        obj(payload.get("local_permission_source"), "local_permission_source"),
        "local_permission_source",
    )
    effective_source, effective_source_kind = merged_permission_source(
        native_permission_source,
        local_permission_source,
    )

    violations: list[str] = []
    if accepted is not None:
        violations.extend(compare_expected(expected, accepted, "accepted"))
    if native is not None:
        violations.extend(compare_expected(expected, native, "native"))
    if local is not None:
        violations.extend(compare_expected(expected, local, "local"))
    violations.extend(source_conflicts(native, local, OBSERVED_FIELDS))
    violations.extend(
        item.replace("source_conflict:", "permission_source_conflict:", 1)
        for item in source_conflicts(
            native_permission_source,
            local_permission_source,
            PERMISSION_PROVENANCE_FIELDS,
        )
    )
    accepted_comparable_fields = (*IDENTITY_FIELDS, *CHILD_ROUTE_FIELDS, *AUXILIARY_OBSERVED_FIELDS)
    violations.extend(layer_conflicts(accepted, native, accepted_comparable_fields))
    violations.extend(layer_conflicts(accepted, local, accepted_comparable_fields))

    native_complete = route_complete(native, "native", violations)
    local_complete = route_complete(local, "local", violations)
    runtime_required = expected.get("runtime_observation_required", False)
    required_runtime_fields = CHILD_ROUTE_FIELDS + tuple(
        field for field in IDENTITY_FIELDS if text(expected.get(field)) is not None
    )
    runtime_required_complete = runtime_fields_complete(
        native,
        local,
        required_runtime_fields,
        violations,
    )

    native_fields, local_fields = seen(native, CHILD_ROUTE_FIELDS), seen(local, CHILD_ROUTE_FIELDS)
    route_complete_observed = runtime_fields_complete(
        native,
        local,
        CHILD_ROUTE_FIELDS,
        violations,
    )
    route_conflict = any(
        item == f"source_conflict:{field}" for item in violations for field in CHILD_ROUTE_FIELDS
    ) or any(
        f"{label}:{field}_mismatch" in violations
        for label in ("accepted", "native", "local")
        for field in CHILD_ROUTE_FIELDS
    ) or any(
        item == f"accepted_observed_conflict:{field}"
        for item in violations
        for field in CHILD_ROUTE_FIELDS
    )
    route_status = (
        "conflict"
        if route_conflict
        else "matched"
        if route_complete_observed
        else "partial"
        if native_fields or local_fields
        else "not_observed"
    )
    route = {
        "status": route_status,
        "source": evidence_source(bool(native_fields), bool(local_fields)),
        "observed_fields": sorted(set(native_fields + local_fields)),
        "native_observed_fields": native_fields,
        "local_observed_fields": local_fields,
    }

    wanted_parent = text(expected.get("parent_thread_id"))
    parent_conflict = "source_conflict:parent_thread_id" in violations or any(
        "parent_thread_id_mismatch" in item for item in violations
    )
    native_parent_observed = bool(native and native.get("parent_thread_id"))
    local_parent_observed = bool(local and local.get("parent_thread_id"))
    if parent_conflict:
        ancestry = {
            "status": "conflict",
            "source": evidence_source(native_parent_observed, local_parent_observed),
        }
    elif wanted_parent is None:
        ancestry = {"status": "not_required", "source": "none"}
    elif not (native_parent_observed or local_parent_observed):
        ancestry = {"status": "not_observed", "source": "none"}
    else:
        ancestry = {
            "status": "matched",
            "source": evidence_source(native_parent_observed, local_parent_observed),
        }

    (
        permission_state,
        permission_provenance,
        permission_state_required,
        permission_provenance_required,
    ) = permission_results(
        expected,
        native,
        local,
        effective_source,
        effective_source_kind,
        violations,
    )

    identity_conflict = any(
        item.endswith("thread_id_mismatch") or item.startswith("source_conflict:thread_id")
        for item in violations
    )
    any_source_conflict = any(
        item.startswith("source_conflict:") or item.startswith("accepted_observed_conflict:")
        for item in violations
    )
    conflict = (
        route["status"] == "conflict"
        or ancestry["status"] == "conflict"
        or permission_state["status"] == "failed"
        or permission_provenance["status"] == "failed"
        or identity_conflict
        or any_source_conflict
        or any(item.startswith("permission_source_conflict:") for item in violations)
    )
    if conflict:
        status, decision = "mismatch", "quarantine"
    elif permission_state_required and permission_state["status"] == "unknown":
        status, decision = "not_exposed", "return_to_main_session"
    elif permission_provenance_required and permission_provenance["status"] == "unknown":
        status, decision = "not_exposed", "return_to_main_session"
    elif runtime_required and not runtime_required_complete:
        status, decision = "not_exposed", "return_to_main_session"
    elif not route_complete_observed:
        status, decision = "not_exposed", "continue_configuration_only"
    else:
        status, decision = "matched", "continue"

    source_agreement = None
    if native is not None and local is not None:
        overlap = any(
            native.get(field) is not None and local.get(field) is not None
            for field in OBSERVED_FIELDS
        )
        if overlap:
            source_agreement = not any(item.startswith("source_conflict:") for item in violations)

    native_attested = route_complete_observed and bool(native_fields)
    local_attested = route_complete_observed and bool(local_fields)

    def tri(value: str, failed: set[str]) -> bool | None:
        if value == "matched":
            return True
        if value in failed:
            return False
        return None

    route_assurance = {
        "status": (
            "failed"
            if route["status"] == "conflict" or ancestry["status"] == "conflict" or identity_conflict
            else "verified"
            if runtime_required_complete
            else "unknown"
        ),
        "source": route["source"],
        "violations": sorted(
            item
            for item in set(violations)
            if item.startswith(
                (
                    "accepted:",
                    "native:",
                    "local:",
                    "source_conflict:",
                    "accepted_observed_conflict:",
                )
            )
            and not any(field in item for field in PERMISSION_FIELDS)
        ),
    }

    return {
        "subject": "child",
        "status": status,
        "decision": decision,
        "evidence_grade": grade(native_attested, local_attested, conflict),
        "truth_layers": {
            "requested": requested_layer(expected, CHILD_ROUTE_FIELDS),
            "accepted": accepted_layer(accepted, CHILD_ROUTE_FIELDS, violations),
            "observed": runtime_observed_layer(
                native,
                local,
                CHILD_ROUTE_FIELDS,
                violations,
            ),
            "observed_auxiliary": runtime_observed_layer(
                native,
                local,
                AUXILIARY_OBSERVED_FIELDS,
                violations,
            ),
        },
        "route_evidence": route,
        "ancestry_evidence": ancestry,
        "route_assurance": route_assurance,
        "task_path_observation": {
            "status": (
                "failed" if any("agent_path" in item for item in violations)
                else "verified" if runtime_fields_complete(native, local, ("agent_path",), violations)
                else "unknown"
            ),
            "observed_agent_path": (
                native.get("agent_path") if native and native.get("agent_path") is not None
                else local.get("agent_path") if local else None
            ),
        },
        "provider_control_assurance": {
            "status": (
                "failed" if any("model_provider" in item for item in violations)
                else "verified" if runtime_fields_complete(native, local, ("model_provider",), violations)
                else "unknown"
            ),
            "observed_model_provider": (
                native.get("model_provider") if native and native.get("model_provider") is not None
                else local.get("model_provider") if local else None
            ),
        },
        "permission_state_assurance": permission_state,
        "permission_provenance_assurance": permission_provenance,
        "configuration_match": tri(route["status"], {"conflict"}),
        "runtime_reported": native_complete,
        "local_record_observed": local_complete,
        "runtime_observation_complete": runtime_required_complete,
        "source_agreement": source_agreement,
        "ancestry_match": tri(ancestry["status"], {"conflict"}),
        "violations": sorted(set(violations)),
    }


def main() -> None:
    args = parse_args()
    payload = load_payload(args.input)
    if "rollout" in payload:
        if payload.get("local") is not None:
            fail("local evidence cannot be supplied together with exact rollout fallback")
        try:
            payload["local"] = rollout_observation(payload.get("rollout"))
        except SystemExit as exc:
            fail(f"rollout evidence unavailable: {str(exc).removeprefix('ERROR: ')}")
    subject = payload.get("subject", "child")
    if subject == "main_session":
        result = main_session_result(payload)
    elif subject == "child":
        result = child_result(payload)
    else:
        fail("subject must be 'main_session' or 'child'")
    json.dump(result, sys.stdout, sort_keys=True, separators=(",", ":"))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
