#!/usr/bin/env python3
"""V4 supported-execution release gate.

Repository/offline development may proceed while the real Codex Host smoke gate
is pending. Managed Host lifecycle execution stays unsupported until every
required real-Host probe has been recorded as PASS in the canonical gate file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HOST_SMOKE = ROOT / "docs" / "v4" / "host-smoke.json"
REQUIRED_PROBES = {"H01", "H02", "H03", "H04", "H05", "H06", "H07"}


class ReleaseGateError(RuntimeError):
    """Managed execution is unavailable because release evidence is incomplete."""


def load_host_smoke() -> dict[str, Any]:
    try:
        payload = json.loads(HOST_SMOKE.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReleaseGateError(f"Host smoke gate is unreadable: {exc}") from exc
    if not isinstance(payload, dict):
        raise ReleaseGateError("Host smoke gate must be an object")
    return payload


def managed_execution_readiness() -> dict[str, Any]:
    try:
        payload = load_host_smoke()
    except ReleaseGateError as exc:
        return {"ready": False, "status": "UNKNOWN", "reason": str(exc)}
    probes = payload.get("probe_results")
    passed = {
        str(item.get("id"))
        for item in probes
        if isinstance(probes, list) and isinstance(item, dict) and item.get("status") == "PASS"
    } if isinstance(probes, list) else set()
    ready = payload.get("status") == "PASS" and REQUIRED_PROBES.issubset(passed)
    return {
        "ready": ready,
        "status": payload.get("status", "UNKNOWN"),
        "passed_probes": sorted(passed),
        "missing_probes": sorted(REQUIRED_PROBES - passed),
        "gate_id": payload.get("gate_id"),
    }


def require_managed_execution_ready() -> dict[str, Any]:
    readiness = managed_execution_readiness()
    if readiness["ready"] is not True:
        raise ReleaseGateError(
            "managed execution is blocked until the real Codex Host smoke gate H01-H07 is PASS"
        )
    return readiness
