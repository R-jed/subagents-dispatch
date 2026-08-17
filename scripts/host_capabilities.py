#!/usr/bin/env python3
"""Normalize inspectable Codex Host evidence into the V4 capability contract.

This module does not probe the Host or simulate missing primitives. Callers supply
inspectable evidence and receive a deterministic fail-closed capability snapshot.
Real Hook coverage is validated later by Host smoke tests.
"""

from __future__ import annotations

import copy
import re
from typing import Any, Mapping


EXPECTED_SURFACE = "multi_agent_v2"
REQUIRED_CAPABILITIES = (
    "spawn",
    "observe",
    "wait_or_wakeup",
    "followup",
    "interrupt",
    "pre_tool_use_guard",
    "post_tool_use_guard",
    "host_observation_guard",
    "subagent_stop_veto",
)
LIFECYCLE_TOOLS = ("spawn_agent", "followup_task", "interrupt_agent")
TOOL_CAPABILITY_MAP = {
    "spawn": {"spawn_agent"},
    "observe": {"list_agents"},
    "wait_or_wakeup": {"wait_agent"},
    "followup": {"followup_task"},
    "interrupt": {"interrupt_agent"},
}
SIMPLE_AGENT_STATES = {"pending_init", "running", "interrupted", "shutdown", "not_found"}
GUARD_TRUST_FIELDS = {"manifest_sha256", "trusted_current_definition", "evidence_ref"}
HEX64 = re.compile(r"[0-9a-f]{64}")


class HostCapabilityError(RuntimeError):
    """Host capability evidence is malformed or internally inconsistent."""


def _string_set(value: Any, *, label: str) -> set[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise HostCapabilityError(f"{label} must be an array of non-empty strings")
    if len(value) != len(set(value)):
        raise HostCapabilityError(f"{label} must not contain duplicates")
    return set(value)


def _hook_tool_set(hooks: Mapping[str, Any], event: str) -> set[str]:
    value = hooks.get(event, [])
    return _string_set(value, label=f"hooks.{event}")


def normalize_agent_status(status: Any) -> dict[str, Any]:
    """Normalize the public Multi-Agent V2 status union without inventing identity."""
    if isinstance(status, str) and status in SIMPLE_AGENT_STATES:
        return {"state": status, "detail": None}
    if isinstance(status, Mapping) and set(status) == {"completed"}:
        detail = status["completed"]
        if detail is not None and not isinstance(detail, str):
            raise HostCapabilityError("completed agent status detail must be string or null")
        return {"state": "completed", "detail": detail}
    if isinstance(status, Mapping) and set(status) == {"errored"}:
        detail = status["errored"]
        if not isinstance(detail, str):
            raise HostCapabilityError("errored agent status detail must be string")
        return {"state": "errored", "detail": detail}
    raise HostCapabilityError("unsupported or malformed agent status")


def normalize_host_capabilities(evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Return a deterministic V4 capability snapshot from explicit Host evidence."""
    if not isinstance(evidence, Mapping):
        raise HostCapabilityError("Host evidence must be an object")
    required_fields = {"surface", "tools", "hooks", "fork_turns_none", "max_spawned_threads"}
    extra = set(evidence) - required_fields
    missing = required_fields - set(evidence)
    if extra:
        raise HostCapabilityError("Host evidence has unsupported fields: " + ", ".join(sorted(extra)))
    if missing:
        raise HostCapabilityError("Host evidence is missing fields: " + ", ".join(sorted(missing)))

    surface = evidence["surface"]
    if surface != EXPECTED_SURFACE:
        raise HostCapabilityError(f"surface must be exactly {EXPECTED_SURFACE}")
    tools = _string_set(evidence["tools"], label="tools")
    hooks = evidence["hooks"]
    if not isinstance(hooks, Mapping):
        raise HostCapabilityError("hooks must be an object")
    hook_fields = {"PreToolUse", "PostToolUse", "SubagentStop"}
    if set(hooks) != hook_fields:
        raise HostCapabilityError("hooks must contain exactly PreToolUse, PostToolUse, SubagentStop")
    pre_tools = _hook_tool_set(hooks, "PreToolUse")
    post_tools = _hook_tool_set(hooks, "PostToolUse")
    if not isinstance(hooks["SubagentStop"], bool):
        raise HostCapabilityError("hooks.SubagentStop must be boolean")
    if not isinstance(evidence["fork_turns_none"], bool):
        raise HostCapabilityError("fork_turns_none must be boolean")

    capacity = evidence["max_spawned_threads"]
    if capacity is not None and (
        not isinstance(capacity, int) or isinstance(capacity, bool) or capacity < 1
    ):
        raise HostCapabilityError("max_spawned_threads must be null or a positive integer")

    capabilities: dict[str, bool] = {}
    for capability, required_tools in TOOL_CAPABILITY_MAP.items():
        capabilities[capability] = required_tools.issubset(tools)
    lifecycle = set(LIFECYCLE_TOOLS)
    capabilities["pre_tool_use_guard"] = lifecycle.issubset(pre_tools)
    capabilities["post_tool_use_guard"] = lifecycle.issubset(post_tools)
    capabilities["host_observation_guard"] = (
        "list_agents" in pre_tools and "list_agents" in post_tools
    )
    capabilities["subagent_stop_veto"] = hooks["SubagentStop"] is True

    missing_capabilities = [
        capability for capability in REQUIRED_CAPABILITIES if capabilities.get(capability) is not True
    ]
    execution_ready = not missing_capabilities and evidence["fork_turns_none"] is True
    if evidence["fork_turns_none"] is not True:
        missing_capabilities.append("fresh_context_spawn")

    return {
        "surface": surface,
        "capabilities": capabilities,
        "fork_turns_none": evidence["fork_turns_none"],
        "max_spawned_threads": capacity,
        "capacity_excludes_primary": True,
        "execution_ready": execution_ready,
        "missing": missing_capabilities,
    }


def build_guard_coverage_proof(
    snapshot: Mapping[str, Any],
    *,
    session_id: str,
    trust_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a diagnostic Hook-coverage summary with no WriterLease authority."""
    if not isinstance(snapshot, Mapping) or snapshot.get("execution_ready") is not True:
        raise HostCapabilityError("Guard coverage summary requires an execution-ready Host snapshot")
    if not isinstance(session_id, str) or not session_id.strip():
        raise HostCapabilityError("Guard coverage summary requires non-empty session_id")
    capabilities = snapshot.get("capabilities")
    if not isinstance(capabilities, Mapping):
        raise HostCapabilityError("Guard coverage summary requires normalized capabilities")
    for capability in (
        "pre_tool_use_guard",
        "post_tool_use_guard",
        "host_observation_guard",
        "subagent_stop_veto",
    ):
        if capabilities.get(capability) is not True:
            raise HostCapabilityError(f"Guard coverage summary requires {capability}")
    if not isinstance(trust_evidence, Mapping) or set(trust_evidence) != GUARD_TRUST_FIELDS:
        raise HostCapabilityError("Guard trust evidence has invalid fields")
    digest = trust_evidence.get("manifest_sha256")
    if not isinstance(digest, str) or HEX64.fullmatch(digest) is None:
        raise HostCapabilityError("Guard trust evidence has invalid manifest SHA-256")
    if trust_evidence.get("trusted_current_definition") is not True:
        raise HostCapabilityError("current Hook definition is not proven trusted")
    evidence_ref = trust_evidence.get("evidence_ref")
    if not isinstance(evidence_ref, str) or not evidence_ref.strip():
        raise HostCapabilityError("Guard trust evidence requires evidence_ref")
    return {
        "schema_version": "4.0",
        "authority": "diagnostic_only",
        "session_id": session_id,
        "manifest_sha256": digest,
        "trusted_current_definition": True,
        "pre_tool_use": True,
        "post_tool_use": True,
        "host_observation_guard": True,
        "subagent_stop_veto": True,
        "evidence_ref": evidence_ref,
    }


def required_lifecycle_hook_tools() -> tuple[str, ...]:
    return LIFECYCLE_TOOLS


def effective_managed_child_limit(
    snapshot: Mapping[str, Any],
    *,
    product_limit: int = 3,
) -> int | None:
    """Cap V4 product fan-out by known Host spawned-thread capacity."""
    if not isinstance(snapshot, Mapping):
        raise HostCapabilityError("capability snapshot must be an object")
    if not isinstance(product_limit, int) or isinstance(product_limit, bool) or product_limit < 1:
        raise HostCapabilityError("product_limit must be a positive integer")
    capacity = snapshot.get("max_spawned_threads")
    if capacity is None:
        return None
    if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity < 1:
        raise HostCapabilityError("snapshot has invalid max_spawned_threads")
    return min(product_limit, capacity)


def capability_snapshot_copy(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Return a defensive copy for persistence/diagnostics without adding evidence."""
    if not isinstance(snapshot, Mapping):
        raise HostCapabilityError("capability snapshot must be an object")
    return copy.deepcopy(dict(snapshot))
