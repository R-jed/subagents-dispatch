#!/usr/bin/env python3
"""V4 ExecutionBinding lifecycle facade for Native Core orchestration.

Main owns orchestration decisions. Codex Native Subagents own lifecycle truth.
This facade exposes deterministic state transitions and direct Host observation
reconciliation without requiring Plugin Hook callbacks.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

import execution_lifecycle_v4_core as _core
import writer_lease_v4 as writer


ExecutionLifecycleError = _core.ExecutionLifecycleError


def persist_host_observation(
    thread_id: str,
    *,
    basis: Mapping[str, Any],
    host_state: str,
    agent_id: str | None = None,
    failure_origin: str = "tool_failure",
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Reconcile one Main-observed native lifecycle state against a fresh basis."""
    return writer.persist_host_observation(
        thread_id,
        basis=basis,
        host_state=host_state,
        agent_id=agent_id,
        failure_origin=failure_origin,
        temp_root=temp_root,
    )


def takeover_to_main(
    thread_id: str,
    *,
    execution_id: str,
    old_lease_id: str,
    old_lease_epoch: int,
    main_lease_id: str,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, object]:
    """Transfer a settled writer only from current Host lifecycle evidence."""
    return writer.transfer_settled_execution_writer_to_main(
        thread_id,
        execution_id=execution_id,
        lease_id=old_lease_id,
        lease_epoch=old_lease_epoch,
        main_lease_id=main_lease_id,
        temp_root=temp_root,
    )


def runtime_temp_root() -> Path | None:
    raw = os.environ.get("SUBAGENTS_DISPATCH_TEMP_ROOT")
    if raw is None or not raw.strip():
        return None
    return Path(raw)


_EXCLUDED = {
    "persist_host_observation",
    "takeover_to_main",
    "runtime_temp_root",
}
for _name in dir(_core):
    if not _name.startswith("__") and _name not in _EXCLUDED and _name not in globals():
        globals()[_name] = getattr(_core, _name)
