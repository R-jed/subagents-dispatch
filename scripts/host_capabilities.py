#!/usr/bin/env python3
"""Normalize inspectable Codex Native Subagent capabilities for V4 Native Core."""

from __future__ import annotations

import copy
from typing import Any, Mapping


EXPECTED_SURFACE = "multi_agent_v2"
REQUIRED_CAPABILITIES = (
    "spawn",
    "observe",
    "wait_or_wakeup",
    "followup",
    "interrupt",
)
TOOL_CAPABILITY_LEAVES = {
    "spawn": {"spawn_agent"},
    "observe": {"list_agents"},
    "wait_or_wakeup": {"wait_agent"},
    "followup": {"followup_task"},
    "interrupt": {"interrupt_agent"},
}
DEFAULT_V2_NAMESPACE = "collaboration"
COLLABORATION_TOOL_SEMANTICS = frozenset(
    set().union(*TOOL_CAPABILITY_LEAVES.values()) | {"send_message"}
)
HOST_TOOL_IDENTITIES = {
    semantic: semantic for semantic in COLLABORATION_TOOL_SEMANTICS
}
HOST_TOOL_IDENTITIES.update(
    {
        f"{DEFAULT_V2_NAMESPACE}.{semantic}": semantic
        for semantic in COLLABORATION_TOOL_SEMANTICS
    }
)
SIMPLE_AGENT_STATES = {"pending_init", "running", "interrupted", "shutdown", "not_found"}
MANAGED_CHILD_CONTAINMENT_STATES = {"verified", "failed", "unknown"}
NORMALIZED_SNAPSHOT_FIELDS = {
    "surface",
    "capabilities",
    "fork_turns_none",
    "managed_child_containment",
    "max_concurrent_threads_per_session",
    "capacity_includes_primary",
    "execution_ready",
    "missing",
}


class HostCapabilityError(RuntimeError):
    """Host capability evidence is malformed or internally inconsistent."""


def _string_set(value: Any, *, label: str) -> set[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise HostCapabilityError(f"{label} must be an array of non-empty strings")
    if len(value) != len(set(value)):
        raise HostCapabilityError(f"{label} must not contain duplicates")
    return set(value)


def _semantic_tool(identity: str) -> str | None:
    return HOST_TOOL_IDENTITIES.get(identity)


def _tool_identities(tools: set[str], semantics: set[str]) -> set[str]:
    return {identity for identity in tools if _semantic_tool(identity) in semantics}


def _reject_unclassified_collaboration_tools(tools: set[str]) -> None:
    unclassified = sorted(identity for identity in tools if identity not in HOST_TOOL_IDENTITIES)
    if unclassified:
        raise HostCapabilityError(
            "unclassified collaboration tool identities require Host adaptation: "
            + ", ".join(unclassified)
        )


def _managed_child_containment(value: Any) -> str:
    if value not in MANAGED_CHILD_CONTAINMENT_STATES:
        allowed = ", ".join(sorted(MANAGED_CHILD_CONTAINMENT_STATES))
        raise HostCapabilityError(
            f"managed_child_containment must be one of: {allowed}"
        )
    return str(value)


def normalize_agent_status(status: Any) -> dict[str, Any]:
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
    """Return a deterministic Native Subagent capability snapshot."""
    if not isinstance(evidence, Mapping):
        raise HostCapabilityError("Host evidence must be an object")
    required_fields = {
        "surface",
        "tools",
        "fork_turns_none",
        "max_concurrent_threads_per_session",
    }
    optional_fields = {"managed_child_containment"}
    extra = set(evidence) - required_fields - optional_fields
    missing = required_fields - set(evidence)
    if extra:
        raise HostCapabilityError("Host evidence has unsupported fields: " + ", ".join(sorted(extra)))
    if missing:
        raise HostCapabilityError("Host evidence is missing fields: " + ", ".join(sorted(missing)))
    if evidence["surface"] != EXPECTED_SURFACE:
        raise HostCapabilityError(f"surface must be exactly {EXPECTED_SURFACE}")

    tools = _string_set(evidence["tools"], label="tools")
    _reject_unclassified_collaboration_tools(tools)
    if not isinstance(evidence["fork_turns_none"], bool):
        raise HostCapabilityError("fork_turns_none must be boolean")
    containment = _managed_child_containment(evidence.get("managed_child_containment", "unknown"))
    capacity = evidence["max_concurrent_threads_per_session"]
    if capacity is not None and (
        not isinstance(capacity, int) or isinstance(capacity, bool) or capacity < 1
    ):
        raise HostCapabilityError(
            "max_concurrent_threads_per_session must be null or a positive integer"
        )

    capabilities = {
        capability: bool(_tool_identities(tools, semantics))
        for capability, semantics in TOOL_CAPABILITY_LEAVES.items()
    }
    missing_capabilities = [
        capability for capability in REQUIRED_CAPABILITIES if capabilities[capability] is not True
    ]
    if evidence["fork_turns_none"] is not True:
        missing_capabilities.append("fresh_context_spawn")

    return {
        "surface": evidence["surface"],
        "capabilities": capabilities,
        "fork_turns_none": evidence["fork_turns_none"],
        "managed_child_containment": containment,
        "max_concurrent_threads_per_session": capacity,
        "capacity_includes_primary": True,
        "execution_ready": not missing_capabilities,
        "missing": missing_capabilities,
    }


def validate_normalized_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(snapshot, Mapping) or set(snapshot) != NORMALIZED_SNAPSHOT_FIELDS:
        raise HostCapabilityError("normalized Host snapshot has invalid fields")
    if snapshot.get("surface") != EXPECTED_SURFACE:
        raise HostCapabilityError("normalized Host snapshot has invalid surface")
    capabilities = snapshot.get("capabilities")
    if not isinstance(capabilities, Mapping) or set(capabilities) != set(REQUIRED_CAPABILITIES):
        raise HostCapabilityError("normalized Host snapshot has invalid capability set")
    if not all(isinstance(capabilities[item], bool) for item in REQUIRED_CAPABILITIES):
        raise HostCapabilityError("normalized Host snapshot capabilities must be boolean")
    fork_none = snapshot.get("fork_turns_none")
    if not isinstance(fork_none, bool):
        raise HostCapabilityError("normalized Host snapshot fork_turns_none must be boolean")
    _managed_child_containment(snapshot.get("managed_child_containment"))
    capacity = snapshot.get("max_concurrent_threads_per_session")
    if capacity is not None and (
        not isinstance(capacity, int) or isinstance(capacity, bool) or capacity < 1
    ):
        raise HostCapabilityError(
            "normalized Host snapshot has invalid max_concurrent_threads_per_session"
        )
    if snapshot.get("capacity_includes_primary") is not True:
        raise HostCapabilityError("normalized Host snapshot must count the primary agent in capacity")
    expected_missing = [
        capability for capability in REQUIRED_CAPABILITIES if capabilities[capability] is not True
    ]
    if fork_none is not True:
        expected_missing.append("fresh_context_spawn")
    if snapshot.get("missing") != expected_missing:
        raise HostCapabilityError("normalized Host snapshot missing list is inconsistent")
    if snapshot.get("execution_ready") is not (not expected_missing):
        raise HostCapabilityError("normalized Host snapshot execution_ready is inconsistent")
    return copy.deepcopy(dict(snapshot))


def capability_snapshot_copy(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return validate_normalized_snapshot(snapshot)
