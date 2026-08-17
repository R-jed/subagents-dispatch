#!/usr/bin/env python3
"""Production V4 state facade with a quarantined V3.x storage backend.

The legacy module remains available only to supply hardened filesystem primitives
and explicit legacy-state diagnostics. Public state semantics are V4.
"""

from __future__ import annotations

import dispatch_state_v3_legacy as _storage

# dispatch_state_v4 reuses these hardened storage primitives during import.
StateError = _storage.StateError
StateIdentityError = _storage.StateIdentityError
StatePathError = _storage.StatePathError
StatePayloadError = _storage.StatePayloadError
StateCorruptError = _storage.StateCorruptError
StateLockError = _storage.StateLockError
resolve_thread_id = _storage.resolve_thread_id
state_path = _storage.state_path
state_lock = _storage.state_lock
_reject_forbidden_persisted_fields = _storage._reject_forbidden_persisted_fields
_parse_timestamp = _storage._parse_timestamp
_utc_text = _storage._utc_text
_paths = _storage._paths
_write_unlocked = _storage._write_unlocked

import dispatch_state_v4 as _v4  # noqa: E402
from dispatch_control_v4 import prepare_control  # noqa: E402

for _name in dir(_v4):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_v4, _name)

# V4 control preparation is intentionally surfaced from the production state API.
globals()["prepare_control"] = prepare_control

__all__ = sorted(
    {name for name in dir(_v4) if not name.startswith("_")} | {"prepare_control"}
)
