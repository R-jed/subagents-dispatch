#!/usr/bin/env python3
"""Validate calibration campaigns with five-role profile-only support."""

from __future__ import annotations

from pathlib import Path
import tomllib
from typing import Any

import validate_experiment_campaign_core as _core
from calibration_profile_contract import materialized_agent_type, role_contract_digest

for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_ROLES = ("reader", "worker", "solver", "investigator", "advisor")
_legacy_validate_campaign = _core.validate_campaign
_legacy_validate_role_calibration = _core.validate_role_calibration


def validate_campaign(campaign: dict[str, Any]) -> dict[str, Any]:
    experiment = campaign.get("experiment")
    if isinstance(experiment, dict) and experiment.get("type") == "role_calibration":
        roles = experiment.get("roles")
        if isinstance(roles, list) and len(roles) != 1:
            _core.fail(
                "initial calibration profile materialization supports only the Reader role; "
                "five-role profile-only calibration now requires exactly one semantic role per campaign"
            )
    return _legacy_validate_campaign(campaign)


def _canonical_profile(role: str, policy: dict[str, Any]) -> dict[str, Any]:
    if role not in SUPPORTED_ROLES:
        _core.fail(f"unsupported calibration role: {role!r}")
    try:
        spec = policy["roles"][role]
        path = ROOT / "agent-profiles" / spec["profile_file"]
        profile = tomllib.loads(path.read_text(encoding="utf-8"))
    except (KeyError, TypeError, OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        _core.fail(f"could not load canonical {role} profile: {exc}")
    required = {"name", "description", "model", "model_reasoning_effort", "developer_instructions"}
    if not required <= set(profile):
        _core.fail(f"canonical {role} profile is missing required contract fields")
    if profile["name"] != spec["agent_type"] or profile["model"] != spec["model"] or profile["model_reasoning_effort"] != spec["effort"]:
        _core.fail(f"canonical {role} profile does not match the current policy route")
    if "sandbox_mode" in profile:
        _core.fail(f"canonical {role} profile must inherit Host permissions")
    return profile


def canonical_role_contract_digest(role: str) -> str:
    policy = _core.load_policy_contract()
    profile = _canonical_profile(role, policy)
    return role_contract_digest(role, str(profile["description"]), str(profile["developer_instructions"]), policy["roles"][role]["mutation_authority"])


def _require_materialization_binding(campaign: dict[str, Any], role: str, route_label: str, route: dict[str, Any], expected_digest: str) -> str:
    if route.get("semantic_role") != role:
        _core.fail(f"role {role!r} {route_label} semantic_role must equal {role!r}")
    if route.get("configured_model") != route["model"] or route.get("configured_effort") != route["effort"]:
        _core.fail(f"role {role!r} {route_label} configured route must match model/effort")
    expected_identity = materialized_agent_type(campaign["campaign_id"], role, route["id"])
    if route.get("materialized_agent_type") != expected_identity:
        _core.fail(f"role {role!r} {route_label} materialized_agent_type is not deterministic")
    if route.get("role_contract_digest") != expected_digest:
        _core.fail(f"role {role!r} {route_label} role_contract_digest does not match canonical contract")
    return expected_identity


def validate_role_calibration(campaign: dict[str, Any], experiment: dict[str, Any], policy: dict[str, Any]) -> list[str]:
    roles = experiment.get("roles", [])
    if len(roles) != 1:
        _core.fail(
            "initial calibration profile materialization supports only the Reader role; "
            "five-role profile-only calibration now requires exactly one semantic role per campaign"
        )
    role = roles[0].get("role")
    if role not in SUPPORTED_ROLES:
        _core.fail(f"unsupported calibration role: {role!r}")
    if role == "reader":
        return _legacy_validate_role_calibration(campaign, experiment, policy)
    if experiment["policy_promotion"] and campaign["stage"] != "formal":
        _core.fail("policy promotion requires a formal campaign")
    promotion_ref = experiment.get("promotion_criteria_ref")
    if promotion_ref is not None:
        _core.require_frozen_text(promotion_ref, "promotion_criteria_ref")
    spec = roles[0]
    _core.require_frozen_text(spec["contract_ref"], f"role {role!r} contract_ref")
    control = spec["control"]
    _core.require_frozen_text(control["id"], f"role {role!r} control id")
    _core.require_frozen_text(control["model"], f"role {role!r} control model")
    if _core.route_tuple(control) != _core.expected_control(policy, role):
        _core.fail(f"role {role!r} control must exactly match the current policy route; calibration cannot rewrite its baseline")
    challengers = spec["challengers"]
    if len(challengers) != 1:
        _core.fail("profile-only role calibration requires exactly one challenger arm")
    challenger = challengers[0]
    _core.require_frozen_text(challenger["id"], f"role {role!r} challenger id")
    _core.require_frozen_text(challenger["model"], f"role {role!r} challenger {challenger['id']!r} model")
    if challenger["id"] == control["id"]:
        _core.fail(f"role {role!r} duplicates route id {challenger['id']!r}")
    if _core.route_tuple(challenger) == _core.route_tuple(control):
        _core.fail(f"role {role!r} contains a challenger identical to another route")
    if challenger["mutation_authority"] != control["mutation_authority"]:
        _core.fail(f"role {role!r} challenger {challenger['id']!r} changes mutation_authority; route calibration must keep the behavioral authority contract fixed")
    if (challenger["model"], challenger["effort"]) == (control["model"], control["effort"]):
        _core.fail(f"role {role!r} challenger {challenger['id']!r} must change model and/or effort")
    expected_digest = canonical_role_contract_digest(role)
    identities: set[str] = set()
    for route_label, route in (("control", control), (f"challenger {challenger['id']!r}", challenger)):
        identity = _require_materialization_binding(campaign, role, route_label, route, expected_digest)
        if identity in identities:
            _core.fail(f"campaign duplicates materialized_agent_type {identity!r}")
        identities.add(identity)
    workload_count = 0
    for workload in campaign["workloads"]:
        workload_id = workload["id"]
        if "benchmark_stratum" in workload:
            _core.fail(f"role-calibration workload {workload_id!r} must not carry a product benchmark_stratum")
        if workload["calibration_role"] != role:
            _core.fail(f"workload {workload_id!r} targets calibration role {workload['calibration_role']!r}, which does not match the campaign role {role!r}")
        _core.require_frozen_text(workload["responsibility_packet_ref"], f"workload {workload_id!r} responsibility_packet_ref")
        workload_count += 1
    if workload_count == 0:
        _core.fail(f"role-calibration campaign has no workload for role {role!r}")
    return [role]


_core.validate_campaign = validate_campaign
_core.canonical_role_contract_digest = canonical_role_contract_digest
_core.validate_role_calibration = validate_role_calibration


def main() -> None:
    _core.main()


if __name__ == "__main__":
    main()
