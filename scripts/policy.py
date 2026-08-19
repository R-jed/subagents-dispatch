from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
POLICY_CONTRACT_PATH = ROOT / "contracts" / "policy.json"
EXPECTED_ROLES = {"reader", "worker", "investigator", "solver", "advisor"}
_REQUIRED_PROFILE_FIELDS = {
    "profile_file",
    "agent_type",
    "model",
    "effort",
    "mutation_authority",
}
_ALLOWED_PROFILE_FIELDS = _REQUIRED_PROFILE_FIELDS | {"sandbox_mode"}


def load_policy_contract(path: Path = POLICY_CONTRACT_PATH) -> dict[str, Any]:
    """Load the shared machine policy as a top-level JSON object."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"invalid policy contract {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"invalid policy contract object: {path}")
    return payload


def _nonempty_text(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"policy {label} must be non-empty text")
    return value.strip()


def profile_contracts(path: Path = POLICY_CONTRACT_PATH) -> dict[str, dict[str, str]]:
    """Return the validated canonical projection for the five managed profiles."""
    payload = load_policy_contract(path)
    roles = payload.get("roles")
    if not isinstance(roles, Mapping) or set(roles) != EXPECTED_ROLES:
        raise RuntimeError("policy roles must contain exactly the five managed profiles")

    projected: dict[str, dict[str, str]] = {}
    for role in sorted(EXPECTED_ROLES):
        raw = roles.get(role)
        if not isinstance(raw, Mapping):
            raise RuntimeError(f"policy role {role} must be an object")
        fields = set(raw)
        if not _REQUIRED_PROFILE_FIELDS.issubset(fields) or not fields.issubset(
            _ALLOWED_PROFILE_FIELDS
        ):
            raise RuntimeError(f"policy role {role} has unsupported profile fields")
        spec = {
            field: _nonempty_text(raw.get(field), label=f"roles.{role}.{field}")
            for field in _REQUIRED_PROFILE_FIELDS
        }
        authority = spec["mutation_authority"]
        sandbox = raw.get("sandbox_mode")
        if authority == "none":
            if sandbox != "read-only":
                raise RuntimeError(f"policy read-only role {role} must request read-only sandbox")
            spec["sandbox_mode"] = "read-only"
        elif sandbox is not None:
            raise RuntimeError(f"policy writable role {role} must inherit Host sandbox")
        spec["semantic_role"] = "review" if role == "advisor" else "work"
        projected[role] = spec
    return copy.deepcopy(projected)


def profile_contract_tuples(
    path: Path = POLICY_CONTRACT_PATH,
) -> dict[str, tuple[str, str, str]]:
    """Project state-compatible model, effort and mutation-authority tuples."""
    return {
        role: (spec["model"], spec["effort"], spec["mutation_authority"])
        for role, spec in profile_contracts(path).items()
    }


def profile_agent_types(path: Path = POLICY_CONTRACT_PATH) -> dict[str, str]:
    """Project the exact managed Host agent_type selector for each role."""
    return {role: spec["agent_type"] for role, spec in profile_contracts(path).items()}
