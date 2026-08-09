from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
POLICY_CONTRACT_PATH = ROOT / "contracts" / "policy.json"


def load_policy_contract(path: Path = POLICY_CONTRACT_PATH) -> dict[str, Any]:
    """Load the shared machine policy as a top-level JSON object.

    Consumer-specific semantic validation intentionally stays with each consumer.
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"invalid policy contract {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"invalid policy contract object: {path}")
    return payload
