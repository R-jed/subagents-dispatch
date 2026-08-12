"""Canonical Reader calibration identity and contract helpers."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

ROLE_CONTRACT_SCHEMA = "subagents-dispatch-calibration-role-contract-v1"
CALIBRATION_FRESH_CONTEXT = "fork_turns:none"
CALIBRATION_DELEGATION_DEPTH = 1
CALIBRATION_PERMISSION_REQUIREMENTS = "host-inherited"
PRODUCTION_AGENT_TYPES = {
    "subagents_dispatch_reader",
    "subagents_dispatch_worker",
    "subagents_dispatch_solver",
    "subagents_dispatch_investigator",
    "subagents_dispatch_advisor",
}


def canonical_json_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def role_contract_digest(
    semantic_role: str,
    description: str,
    developer_instructions: str,
    mutation_authority: str,
) -> str:
    return canonical_json_hash(
        {
            "schema_marker": ROLE_CONTRACT_SCHEMA,
            "semantic_role": semantic_role,
            "description": description,
            "developer_instructions": developer_instructions,
            "mutation_authority": mutation_authority,
            "fresh_context": CALIBRATION_FRESH_CONTEXT,
            "delegation_depth": CALIBRATION_DELEGATION_DEPTH,
            "permission_requirements_fingerprint": CALIBRATION_PERMISSION_REQUIREMENTS,
        }
    )


def materialized_agent_type(campaign_id: str, semantic_role: str, route_id: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", semantic_role.lower()).strip("_")[:40] or "arm"
    route_slug = re.sub(r"[^a-z0-9]+", "_", route_id.lower()).strip("_")[:40] or "arm"
    identity = f"{campaign_id}\0{semantic_role}\0{route_id}".encode("utf-8")
    return f"subagents_dispatch_calibration_{slug}_{route_slug}_{hashlib.sha256(identity).hexdigest()[:16]}"
