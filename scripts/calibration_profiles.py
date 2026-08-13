#!/usr/bin/env python3
"""Materialize one-role, two-arm calibration Agent profiles.

The hardened profile transaction implementation lives in
``calibration_profiles_core``. This adapter generalizes only campaign and
canonical-role binding so every production semantic role can use the same
profile-only materialization path without duplicating transaction logic.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import tomllib
from typing import Any

import calibration_profiles_core as _core
from calibration_profile_contract import PRODUCTION_AGENT_TYPES, materialized_agent_type, role_contract_digest

for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "contracts" / "policy.json"
CAMPAIGN_VALIDATOR = ROOT / "scripts" / "validate-experiment-campaign.py"
SUPPORTED_ROLES = ("reader", "worker", "solver", "investigator", "advisor")
_legacy_profile_records = _core._profile_records


def _load_policy() -> dict[str, Any]:
    policy = _core._load_json(POLICY, "policy contract")
    roles = policy.get("roles")
    if not isinstance(roles, dict) or set(roles) != set(SUPPORTED_ROLES):
        _core.fail("policy must define exactly the five calibration roles")
    for role in SUPPORTED_ROLES:
        spec = roles.get(role)
        if not isinstance(spec, dict):
            _core.fail(f"policy role {role!r} is incomplete")
        required = {"profile_file", "agent_type", "model", "effort", "mutation_authority"}
        if not required <= set(spec):
            _core.fail(f"policy role {role!r} is incomplete")
        if spec["profile_file"] != f"subagents-dispatch-{role}.toml" or spec["agent_type"] != f"subagents_dispatch_{role}":
            _core.fail(f"policy role {role!r} does not use its canonical production identity")
        _load_role_template(role, policy)
    return policy


def _load_role_template(role: str, policy: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    if role not in SUPPORTED_ROLES:
        _core.fail(f"unsupported calibration role: {role!r}")
    try:
        spec = policy["roles"][role]
        template_path = ROOT / "agent-profiles" / spec["profile_file"]
    except (KeyError, TypeError) as exc:
        _core.fail(f"policy does not define a complete route for role {role!r}: {exc}")
    _core._regular(template_path, f"canonical {role} profile", missing_ok=False)
    try:
        data = tomllib.loads(template_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        _core.fail(f"invalid canonical {role} profile: {exc}")
    required = {"name", "description", "model", "model_reasoning_effort", "developer_instructions"}
    if not required <= set(data):
        _core.fail(f"canonical {role} profile is missing required contract fields")
    expected = (spec["agent_type"], spec["model"], spec["effort"])
    observed = (data["name"], data["model"], data["model_reasoning_effort"])
    if observed != expected:
        _core.fail(f"canonical {role} profile does not match the current policy route")
    if "sandbox_mode" in data:
        _core.fail(f"canonical {role} profile must inherit Host permissions")
    return template_path, data


def _render_role_profile(template_path: Path, agent_type: str, model: str, effort: str) -> bytes:
    text = template_path.read_text(encoding="utf-8")
    for key, value in {"name": agent_type, "model": model, "model_reasoning_effort": effort}.items():
        pattern = rf"(?m)^{re.escape(key)}\s*=\s*\"[^\"]*\"\s*$"
        text, count = re.subn(pattern, f'{key} = "{value}"', text, count=1)
        if count != 1:
            _core.fail(f"canonical calibration profile has no unique {key!r} field")
    return text.encode("utf-8")


def _single_role(campaign: dict[str, Any]) -> str:
    if campaign.get("experiment", {}).get("type") != "role_calibration":
        _core.fail("calibration profiles require a role_calibration campaign")
    roles = campaign["experiment"].get("roles", [])
    if len(roles) != 1 or roles[0].get("role") not in SUPPORTED_ROLES:
        _core.fail("profile-only calibration requires exactly one supported semantic role")
    return str(roles[0]["role"])


def _validated_campaign(path: Path) -> tuple[dict[str, Any], dict[str, Any], str]:
    initial, raw_sha256 = _core._campaign_bytes(path)
    fd, frozen_name = tempfile.mkstemp(prefix=".frozen-campaign-", suffix=".json", dir=path.parent)
    frozen_path = Path(frozen_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(initial)
            handle.flush()
            os.fsync(handle.fileno())
        result = subprocess.run(
            [sys.executable, str(CAMPAIGN_VALIDATOR), str(frozen_path), "--json"],
            cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
    finally:
        frozen_path.unlink(missing_ok=True)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or str(result.returncode)
        _core.fail(f"campaign validation failed: {detail}")
    try:
        summary = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        _core.fail(f"campaign validator returned invalid JSON: {exc}")
    if not isinstance(summary, dict):
        _core.fail("campaign validator summary must be a JSON object")
    current, current_sha256 = _core._campaign_bytes(path)
    if current != initial or current_sha256 != raw_sha256:
        _core.fail("campaign changed while it was being validated; refusing a TOCTOU race")
    try:
        campaign = json.loads(initial)
    except (UnicodeError, json.JSONDecodeError) as exc:
        _core.fail(f"could not load frozen campaign: {exc}")
    if not isinstance(campaign, dict):
        _core.fail("frozen campaign must be a JSON object")
    _single_role(campaign)
    return campaign, summary, raw_sha256


def _profile_records(campaign: dict[str, Any], policy: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    role = _single_role(campaign)
    if role == "reader":
        return _legacy_profile_records(campaign, policy)
    template_path, template = _load_role_template(role, policy)
    spec = campaign["experiment"]["roles"][0]
    description = str(template["description"])
    instructions = str(template["developer_instructions"])
    digest = role_contract_digest(role, description, instructions, policy["roles"][role]["mutation_authority"])
    records: list[dict[str, Any]] = []
    seen_types: set[str] = set()
    for route in [spec["control"], *spec["challengers"]]:
        route_id = str(route["id"])
        agent_type = materialized_agent_type(campaign["campaign_id"], role, route_id)
        if agent_type in PRODUCTION_AGENT_TYPES or agent_type in seen_types:
            _core.fail(f"calibration Agent identity collides: {agent_type}")
        seen_types.add(agent_type)
        profile_bytes = _render_role_profile(template_path, agent_type, route["model"], route["effort"])
        try:
            parsed = tomllib.loads(profile_bytes.decode("utf-8"))
        except (UnicodeError, tomllib.TOMLDecodeError) as exc:
            _core.fail(f"generated calibration profile is invalid: {exc}")
        if parsed.get("name") != agent_type:
            _core.fail("generated calibration profile name does not match materialized_agent_type")
        if parsed.get("description") != description or parsed.get("developer_instructions") != instructions:
            _core.fail("generated calibration profile changed the canonical role contract")
        records.append({
            "campaign_id": campaign["campaign_id"],
            "candidate_sha": campaign["plugin_candidate_sha"],
            "route": route,
            "route_id": route_id,
            "semantic_role": role,
            "materialized_agent_type": agent_type,
            "role_contract_digest": digest,
            "configured_model": route["model"],
            "configured_effort": route["effort"],
            "profile_bytes": profile_bytes,
        })
    return records, {"description": description, "developer_instructions": instructions, "digest": digest}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create/check/cleanup one-role profile-only calibration Agents.")
    parser.add_argument("command", choices=("init", "create", "check", "cleanup", "recover"))
    parser.add_argument("--evaluator-root", required=True, type=Path)
    parser.add_argument("--codex-home", type=Path)
    parser.add_argument("--campaign", type=Path)
    parser.add_argument("--host-home-evidence", type=Path)
    parser.add_argument("--provisioning-task-id")
    parser.add_argument("--shared-config", type=Path)
    parser.add_argument("--marketplace-source", type=Path)
    return parser.parse_args()


_core._load_policy = _load_policy
_core._validated_campaign = _validated_campaign
_core._profile_records = _profile_records
_core.parse_args = parse_args


def main() -> None:
    # Preserve the public module's injectable Host-home resolver used by the
    # deterministic test harness and evaluator-side callers.
    _core._normal_codex_home = globals()["_normal_codex_home"]
    _core.main()


if __name__ == "__main__":
    main()
