from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load_orchestrate(name: str):
    scripts = str(SCRIPTS)
    sys.path.insert(0, scripts)
    try:
        spec = importlib.util.spec_from_file_location(name, SCRIPTS / "orchestrate_v4.py")
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts)


@pytest.mark.parametrize("responsibilities", [None, {}, "U1"])
def test_plan_only_rejects_non_array_responsibilities(responsibilities):
    orchestrate = load_orchestrate("plan_only_invalid_container")
    with pytest.raises(orchestrate.OrchestrateError, match="responsibilities must be an array"):
        orchestrate.plan_only_preview(
            goal="preview a bounded plan",
            responsibilities=responsibilities,
        )


@pytest.mark.parametrize(
    "responsibility",
    [
        {"intent": None, "goal": "inspect", "role_id": "programmer", "reasoning_effort": "max"},
        {"intent": "unsupported", "goal": "inspect", "role_id": "programmer", "reasoning_effort": "max"},
        {"intent": "inspect", "goal": None, "role_id": "programmer", "reasoning_effort": "max"},
        {"intent": "inspect", "goal": "inspect", "role_id": "programmer", "reasoning_effort": "max", "depends_on": None},
        {"intent": "inspect", "goal": "inspect", "role_id": "programmer", "reasoning_effort": "max", "depends_on": "U1"},
        {"intent": "inspect", "goal": "inspect", "role_id": "programmer", "reasoning_effort": "max", "depends_on": ("U1",)},
        {"intent": "inspect", "goal": "inspect", "role_id": "programmer", "reasoning_effort": "max", "depends_on": {"U1": 1}},
        {"intent": "inspect", "goal": "inspect", "role_id": "programmer", "reasoning_effort": "max", "depends_on": [1]},
        {"intent": "inspect", "goal": "inspect", "role_id": "programmer", "reasoning_effort": "max", "depends_on": ["U9"]},
    ],
)
def test_plan_only_rejects_malformed_workunit_fields(responsibility):
    orchestrate = load_orchestrate("plan_only_invalid_fields")
    with pytest.raises(orchestrate.OrchestrateError):
        orchestrate.plan_only_preview(
            goal="preview a bounded plan",
            responsibilities=[responsibility],
        )


def test_plan_only_rejects_dependency_cycles():
    orchestrate = load_orchestrate("plan_only_cycle")
    with pytest.raises(orchestrate.OrchestrateError, match="acyclic"):
        orchestrate.plan_only_preview(
            goal="preview a dependency graph",
            responsibilities=[
                {
                    "intent": "inspect",
                    "goal": "inspect first",
                    "role_id": "programmer", "reasoning_effort": "max",
                    "depends_on": ["U2"],
                },
                {
                    "intent": "review",
                    "goal": "review second",
                    "role_id": "product_manager", "reasoning_effort": "high",
                    "depends_on": ["U1"],
                },
            ],
        )


def test_plan_only_accepts_valid_dependencies_without_runtime_side_effects(tmp_path: Path):
    orchestrate = load_orchestrate("plan_only_valid_graph")
    preview = orchestrate.plan_only_preview(
        goal="preview a dependency graph",
        responsibilities=[
            {"intent": "inspect", "goal": "inspect first", "role_id": "programmer", "reasoning_effort": "max"},
            {
                "intent": "review",
                "goal": "review second",
                "role_id": "product_manager", "reasoning_effort": "high",
                "depends_on": ["U1"],
            },
        ],
    )

    assert preview["state_created"] is False
    assert preview["writer_lease_acquired"] is False
    assert preview["host_actions"] == []
    assert preview["work_units"][1]["depends_on"] == ["U1"]
    assert orchestrate.state.load_state("plan-only-preview", temp_root=tmp_path) is None
