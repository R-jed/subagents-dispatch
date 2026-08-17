#!/usr/bin/env python3
"""V4 ExecutionBinding lifecycle facade for RC3 Host evidence authority.

Stable allocation and control preparation live in ``execution_lifecycle_v4_core``.
Authoritative Host lifecycle observations are intentionally absent from this
public facade and are ingested only by the production Hook path.
"""

from __future__ import annotations

import os
from pathlib import Path

import execution_lifecycle_v4_core as _core
import writer_lease_v4 as writer


ExecutionLifecycleError = _core.ExecutionLifecycleError


def takeover_to_main(
    thread_id: str,
    *,
    execution_id: str,
    old_lease_id: str,
    old_lease_epoch: int,
    main_lease_id: str,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, object]:
    """Transfer a settled writer only from authoritative current Host evidence."""
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
