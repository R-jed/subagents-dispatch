from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
POLICY_CONTRACT_PATH = ROOT / "contracts" / "policy.json"
EXPECTED_ROLES = {"programmer", "product_manager", "department_director"}
_REQUIRED_ROLE_FIELDS = {"profile_file", "agent_type", "model", "allowed_efforts"}
_ALLOWED_ROLE_FIELDS = _REQUIRED_ROLE_FIELDS


def load_policy_contract(path: Path = POLICY_CONTRACT_PATH) -> dict[str, Any]:
    """Load the shared machine policy as a top-level JSON object."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"invalid policy contract {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"invalid policy contract object: {path}")
    return payload


def _nonempty_text(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"policy {label} must be non-empty text")
    return value.strip()


def _nonempty_text_list(value: Any, *, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise RuntimeError(f"policy {label} must be a non-empty array")
    projected = tuple(_nonempty_text(item, label=f"{label}[]") for item in value)
    if len(set(projected)) != len(projected):
        raise RuntimeError(f"policy {label} must not contain duplicates")
    return projected


def managed_child_limit(path: Path = POLICY_CONTRACT_PATH) -> int:
    """Return the single product ceiling for concurrently active managed children."""
    payload = load_policy_contract(path)
    delegation = payload.get("delegation")
    if not isinstance(delegation, Mapping):
        raise RuntimeError("policy delegation must be an object")
    value = delegation.get("max_managed_children")
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise RuntimeError("policy delegation.max_managed_children must be a positive integer")
    return value


def role_contracts(path: Path = POLICY_CONTRACT_PATH) -> dict[str, dict[str, Any]]:
    """Return the validated canonical projection for the three managed roles."""
    payload = load_policy_contract(path)
    roles = payload.get("roles")
    if not isinstance(roles, Mapping) or set(roles) != EXPECTED_ROLES:
        raise RuntimeError("policy roles must contain exactly programmer, product_manager, and department_director")

    projected: dict[str, dict[str, Any]] = {}
    seen_files: set[str] = set()
    seen_agent_types: set[str] = set()
    for role_id in sorted(EXPECTED_ROLES):
        raw = roles.get(role_id)
        if not isinstance(raw, Mapping):
            raise RuntimeError(f"policy role {role_id} must be an object")
        fields = set(raw)
        if fields != _ALLOWED_ROLE_FIELDS:
            raise RuntimeError(f"policy role {role_id} has unsupported or missing fields")
        profile_file = _nonempty_text(raw.get("profile_file"), label=f"roles.{role_id}.profile_file")
        agent_type = _nonempty_text(raw.get("agent_type"), label=f"roles.{role_id}.agent_type")
        model = _nonempty_text(raw.get("model"), label=f"roles.{role_id}.model")
        efforts = _nonempty_text_list(raw.get("allowed_efforts"), label=f"roles.{role_id}.allowed_efforts")
        if profile_file in seen_files or agent_type in seen_agent_types:
            raise RuntimeError("policy managed roles must have unique profile_file and agent_type values")
        seen_files.add(profile_file)
        seen_agent_types.add(agent_type)
        projected[role_id] = {
            "profile_file": profile_file,
            "agent_type": agent_type,
            "model": model,
            "allowed_efforts": efforts,
        }

    _validate_routing_sections(payload, projected)
    return copy.deepcopy(projected)


def _routing_object(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise RuntimeError(f"policy {key} must be an object")
    return value


def _validate_routing_sections(
    payload: Mapping[str, Any], roles: Mapping[str, Mapping[str, Any]]
) -> None:
    decision = _routing_object(payload, "decision_routing")
    decision_role = _nonempty_text(decision.get("role_id"), label="decision_routing.role_id")
    if decision_role != "product_manager":
        raise RuntimeError("policy decision_routing.role_id must be product_manager")
    default_effort = _nonempty_text(
        decision.get("default_effort"), label="decision_routing.default_effort"
    )
    high_effort = _nonempty_text(
        decision.get("high_effort"), label="decision_routing.high_effort"
    )
    allowed = set(roles[decision_role]["allowed_efforts"])
    if {default_effort, high_effort} != {"medium", "high"} or not {
        default_effort,
        high_effort,
    } <= allowed:
        raise RuntimeError("policy Product Manager decision efforts must be exactly medium/high")
    _nonempty_text_list(decision.get("high_triggers"), label="decision_routing.high_triggers")

    review = _routing_object(payload, "review_routing")
    if set(review) != {"standard", "highest"}:
        raise RuntimeError("policy review_routing must contain exactly standard and highest")
    trigger_sets: dict[str, set[str]] = {}
    expected_roles = {"standard": "product_manager", "highest": "department_director"}
    for tier, expected_role in expected_roles.items():
        raw = review.get(tier)
        if not isinstance(raw, Mapping) or set(raw) != {"role_id", "effort", "triggers"}:
            raise RuntimeError(f"policy review_routing.{tier} is malformed")
        role_id = _nonempty_text(raw.get("role_id"), label=f"review_routing.{tier}.role_id")
        effort = _nonempty_text(raw.get("effort"), label=f"review_routing.{tier}.effort")
        if role_id != expected_role:
            raise RuntimeError(f"policy review_routing.{tier}.role_id must be {expected_role}")
        if effort not in roles[role_id]["allowed_efforts"]:
            raise RuntimeError(f"policy review_routing.{tier}.effort is outside the role route")
        trigger_sets[tier] = set(
            _nonempty_text_list(raw.get("triggers"), label=f"review_routing.{tier}.triggers")
        )
    if trigger_sets["standard"] & trigger_sets["highest"]:
        raise RuntimeError("policy standard/highest review triggers must not overlap")


def resolve_managed_route(
    *,
    role_id: str,
    reasoning_effort: str | None = None,
    path: Path = POLICY_CONTRACT_PATH,
) -> dict[str, str]:
    """Resolve one exact managed route without parent inheritance or runtime fallback."""
    roles = role_contracts(path)
    if role_id not in roles:
        raise RuntimeError(f"unknown managed role: {role_id}")
    spec = roles[role_id]
    allowed = tuple(spec["allowed_efforts"])
    if reasoning_effort is None:
        if len(allowed) != 1:
            raise RuntimeError(f"role {role_id} requires explicit reasoning_effort")
        selected = allowed[0]
    else:
        selected = _nonempty_text(reasoning_effort, label="reasoning_effort")
    if selected not in allowed:
        raise RuntimeError(f"reasoning_effort {selected!r} is outside the policy route for {role_id}")
    return {
        "role_id": role_id,
        "agent_type": str(spec["agent_type"]),
        "model": str(spec["model"]),
        "reasoning_effort": selected,
    }


def _normalized_triggers(values: Iterable[str], *, label: str) -> set[str]:
    result: set[str] = set()
    for value in values:
        item = _nonempty_text(value, label=label)
        result.add(item)
    return result


def resolve_product_manager_effort(
    confirmed_triggers: Iterable[str], *, path: Path = POLICY_CONTRACT_PATH
) -> str:
    """Resolve Product Manager Medium/High from Main-confirmed semantic triggers."""
    payload = load_policy_contract(path)
    roles = role_contracts(path)
    decision = _routing_object(payload, "decision_routing")
    high_triggers = set(
        _nonempty_text_list(decision.get("high_triggers"), label="decision_routing.high_triggers")
    )
    selected = _normalized_triggers(confirmed_triggers, label="decision trigger")
    unknown = selected - high_triggers
    if unknown:
        raise RuntimeError(f"unknown decision trigger: {sorted(unknown)!r}")
    effort = str(decision["high_effort"] if selected else decision["default_effort"])
    if effort not in roles["product_manager"]["allowed_efforts"]:
        raise RuntimeError("resolved Product Manager effort is outside the policy route")
    return effort


def resolve_review_route(
    confirmed_triggers: Iterable[str], *, path: Path = POLICY_CONTRACT_PATH
) -> dict[str, str] | None:
    """Return the highest applicable exact review route from Main-confirmed triggers."""
    payload = load_policy_contract(path)
    role_contracts(path)  # validates route sections and role references
    review = _routing_object(payload, "review_routing")
    trigger_sets = {
        tier: set(_nonempty_text_list(review[tier]["triggers"], label=f"review_routing.{tier}.triggers"))
        for tier in ("standard", "highest")
    }
    selected = _normalized_triggers(confirmed_triggers, label="review trigger")
    known = trigger_sets["standard"] | trigger_sets["highest"]
    unknown = selected - known
    if unknown:
        raise RuntimeError(f"unknown review trigger: {sorted(unknown)!r}")
    if selected & trigger_sets["highest"]:
        tier = "highest"
    elif selected & trigger_sets["standard"]:
        tier = "standard"
    else:
        return None
    route_spec = review[tier]
    resolved = resolve_managed_route(
        role_id=str(route_spec["role_id"]),
        reasoning_effort=str(route_spec["effort"]),
        path=path,
    )
    return {"tier": tier, **resolved}
