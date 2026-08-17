#!/usr/bin/env python3
"""V4 Doctor facade over the stable diagnostic core.

This module owns the active H00-H20 Host-contract boundary. The historical
runtime implementation is retained in ``doctor_runtime_core`` and receives the
RC4 contract validator through this facade, keeping release semantics in one
machine-readable Host contract.
"""

from __future__ import annotations

from typing import Any, Mapping

import doctor_runtime_core as _core
import release_evidence_v4


EXPECTED_HOST_PROBES = release_evidence_v4.REQUIRED_HOST_PROBES
HOST_CONTRACT_VERSION = release_evidence_v4.HOST_CAMPAIGN_CONTRACT_VERSION
HOST_ENVIRONMENT_FIELDS = sorted(release_evidence_v4.HOST_ENVIRONMENT_FIELDS)
HOST_RESULT_FIELDS = sorted(release_evidence_v4.HOST_RESULT_FIELDS)


def _validate_host_smoke_evidence(smoke: Mapping[str, Any]) -> tuple[bool, bool, str | None]:
    """Validate the tracked Host-smoke contract; real PASS evidence stays external."""
    if not isinstance(smoke, Mapping):
        return False, False, "Host-smoke contract must be an object"
    if smoke.get("schema_version") != HOST_CONTRACT_VERSION:
        return False, False, "Host-smoke contract schema_version is unsupported"
    if smoke.get("status") != "PENDING":
        return False, False, "tracked Host-smoke contract must remain PENDING"
    required = smoke.get("required_probes")
    if not isinstance(required, list):
        return False, False, "Host-smoke required_probes must be an array"
    ids = [item.get("id") for item in required if isinstance(item, Mapping)]
    if len(ids) != len(required) or tuple(ids) != EXPECTED_HOST_PROBES:
        return False, False, "Host-smoke required probes must be exactly ordered H00-H20"
    if smoke.get("required_environment_fields") != HOST_ENVIRONMENT_FIELDS:
        return False, False, "Host-smoke environment field contract is unsupported"
    if smoke.get("required_result_fields") != HOST_RESULT_FIELDS:
        return False, False, "Host-smoke result field contract is unsupported"
    h20 = next((item for item in required if isinstance(item, Mapping) and item.get("id") == "H20"), None)
    if not isinstance(h20, Mapping) or h20.get("platform") != "windows":
        return False, False, "Host-smoke H20 must require Windows"
    if smoke.get("results") != {}:
        return False, False, "tracked Host-smoke contract cannot contain authoritative runtime results"
    return True, False, None


_core.EXPECTED_HOST_PROBES = EXPECTED_HOST_PROBES
_core._validate_host_smoke_evidence = _validate_host_smoke_evidence


def diagnose_hook_and_release() -> tuple[dict[str, Any], dict[str, Any]]:
    """Delegate through the facade while honoring facade-bound contract paths."""
    for name in ("HOST_SMOKE", "HOOKS", "STAGED_HOOKS"):
        if name in globals():
            setattr(_core, name, globals()[name])
    return _core.diagnose_hook_and_release()


for _name in dir(_core):
    if _name.startswith("__") or _name in {"EXPECTED_HOST_PROBES", "_validate_host_smoke_evidence"}:
        continue
    if _name not in globals():
        globals()[_name] = getattr(_core, _name)


if __name__ == "__main__":
    _core.main()
