#!/usr/bin/env python3
"""Public V4 Native Core state facade.

All correctness-bearing schema and reconciliation logic lives in
``dispatch_state_v4_core``. This module intentionally adds no Hook receipt,
capacity-token, or PendingControl accounting layer.
"""

from __future__ import annotations

import dispatch_state_v4_core as _core


for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)
