#!/usr/bin/env python3
"""Production V4 state facade with a quarantined V3.x storage backend."""

from __future__ import annotations

import dispatch_state_v3_legacy as _storage

# Preserve hardened storage primitives and legacy-only maintenance helpers while
# V4 imports this module as its storage backend. V4 public names are overlaid below.
for _name in dir(_storage):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_storage, _name)

for _name in (
    "_reject_forbidden_persisted_fields",
    "_parse_timestamp",
    "_utc_text",
    "_paths",
    "_write_unlocked",
    "_reject_symlink",
    "_temporary_root",
):
    globals()[_name] = getattr(_storage, _name)

import dispatch_state_v4 as _v4  # noqa: E402
from dispatch_control_v4 import prepare_control  # noqa: E402

for _name in dir(_v4):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_v4, _name)

globals()["prepare_control"] = prepare_control

__all__ = sorted(
    {name for name in dir(_v4) if not name.startswith("_")} | {"prepare_control"}
)
