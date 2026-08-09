from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT
POLICY = PLUGIN / "contracts" / "policy.json"
VERIFIER = PLUGIN / "scripts" / "runtime-evidence.py"


def run_main(model: str | None = None, effort: str | None = None) -> dict:
    native = {}
    if model is not None:
        native["model"] = model
    if effort is not None:
        native["effort"] = effort
    payload = {"subject": "main_session", "native": native or None}
    result = subprocess.run(
        [sys.executable, str(VERIFIER)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_policy_owns_capability_dedup_reference_route_and_aliases():
    policy = json.loads(POLICY.read_text())
    dedup = policy["capability_dedup"]
    role = dedup["reference_role"]
    reference = policy["roles"][role]
    order = dedup["reasoning_effort_order"]

    assert policy["schema_version"] == 5
    assert role == "solver"
    assert reference["model"] == "gpt-5.6-sol"
    assert reference["effort"] == "high"
    assert dedup["model_aliases"] == ["gpt-5.6"]
    assert order.index("medium") < order.index("high") < order.index("xhigh") < order.index("max")


def test_capability_dedup_requires_reference_model_or_declared_alias_and_sufficient_effort():
    for model in ["gpt-5.6-sol", "gpt-5.6"]:
        assert run_main(model, "high")["main_judgment_coverage"] == "covered"
        assert run_main(model, "xhigh")["main_judgment_coverage"] == "covered"
        assert run_main(model, "max")["main_judgment_coverage"] == "covered"
        assert run_main(model, "medium")["main_judgment_coverage"] == "uncovered"

    assert run_main("gpt-5.6-sol", "low")["main_judgment_coverage"] == "uncovered"
    assert run_main("gpt-5.6-luna", "max")["main_judgment_coverage"] == "uncovered"


def test_unknown_effort_on_matching_model_does_not_suppress_sol_uplift():
    data = run_main("gpt-5.6-sol", "future-effort")
    assert data["main_judgment_coverage"] == "unknown"
    assert data["coverage_reference_model"] == "gpt-5.6-sol"
    assert data["coverage_reference_model_aliases"] == ["gpt-5.6"]
    assert data["coverage_reference_effort"] == "high"


def test_partial_main_route_remains_unknown():
    assert run_main("gpt-5.6-sol", None)["main_judgment_coverage"] == "unknown"
