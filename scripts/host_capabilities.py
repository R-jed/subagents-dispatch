#!/usr/bin/env python3
"""Normalize inspectable Codex Host evidence into the V4 capability contract.

This module does not probe the Host or simulate missing primitives. Callers supply
inspectable evidence and receive a deterministic fail-closed capability snapshot.
Real Hook coverage is validated later by Host smoke tests.
"""

from __future__ import annotations

import copy
from typing import Any, Mapping


REQUIRED_CAPABILITIES = (
    "spawn",
    "observe",
    "wait_or_wakeup",
    "followup",
    "interrupt",
    "pre_tool_use_guard",
    "post_tool_use_guard",
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


def normalize_host_capabilities(evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Return a deterministic V4 capability snapshot from explicit Host evidence.

    Expected evidence shape::

        {
          "surface": "multi_agent_v2",
          "tools": ["spawn_agent", ...],
          "hooks": {
            "PreToolUse": ["spawn_agent", ...],
            "PostToolUse": ["spawn_agent", ...],
            "SubagentStop": true
          },
          "fork_turns_none": true,
          "max_spawned_threads": 4 | null
        }

    ``max_spawned_threads`` follows the public Host meaning: spawned threads only,
    excluding the primary thread. Missing or untrusted capacity remains ``None``.
    """
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
    if not isinstance(surface, str) or not surface.strip():
        raise HostCapabilityError("surface must be a non-empty string")
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


def required_lifecycle_hook_tools() -> tuple[str, ...]:
    return LIFECYCLE_TOOLS


def effective_managed_child_limit(
    snapshot: Mapping[str, Any],
    *,
    product_limit: int = 3,
) -> int | None:
    """Cap V4 product fan-out by known Host spawned-thread capacity.

    ``None`` means Host capacity is unknown. The scheduler must then use its
    conservative runtime path instead of inventing a capacity number.
    """
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
