from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT
SCRIPTS = PLUGIN / "scripts"
SCRIPT = SCRIPTS / "validate_team_plan.py"
POLICY = PLUGIN / "contracts" / "policy.json"


def load_validator():
    scripts_dir = str(SCRIPTS)
    sys.path.insert(0, scripts_dir)
    try:
        spec = importlib.util.spec_from_file_location("subagents_dispatch_team_plan", SCRIPT)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts_dir)


VALIDATOR = load_validator()


def plan():
    return {
        "schema_version": "1.0",
        "revision": 1,
        "supersedes_revision": None,
        "planning_source": "ad_hoc",
        "source_refs": [],
        "root_goal": "deliver the verified requested result",
        "units": [
            {
                "unit_id": "U1",
                "role": "reader",
                "goal": "trace contract",
                "output": "evidence",
                "depends_on": [],
                "ownership": {"write": [], "forbidden": []},
                "done_when": "contract evidenced",
            },
            {
                "unit_id": "U2",
                "role": "worker",
                "goal": "implement change",
                "output": "source change",
                "depends_on": ["U1"],
                "ownership": {"write": ["src/example.py"], "forbidden": []},
                "done_when": "acceptance passes",
            },
        ],
        "integration_owner": "main",
        "integration_order": ["U1", "U2"],
        "final_verification": "Main verifies the combined artifact",
        "revision_reason": "initial",
    }


def validate(payload):
    return VALIDATOR.validate_team_plan_payload(payload)


def test_validator_derives_role_and_read_only_sets_from_policy_contract():
    policy = json.loads(POLICY.read_text())
    assert VALIDATOR.ROLES == set(policy["roles"])
    assert VALIDATOR.READ_ONLY_ROLES == {
        role for role, spec in policy["roles"].items() if spec["sandbox_intent"] == "read-only"
    }


def test_valid_plan_derives_dependency_layers_without_worker_count_alias():
    result = validate(plan())
    assert result["team_plan_valid"] is True
    assert result["ready_layers"] == [["U1"], ["U2"]]
    assert result["unit_count"] == 2
    assert "worker_count" not in result


def test_team_plan_is_only_for_multi_responsibility_coordination():
    payload = plan()
    payload["units"] = payload["units"][:1]
    payload["integration_order"] = ["U1"]
    result = validate(payload)
    assert result["team_plan_valid"] is False
    assert "TeamPlan requires at least two delegated units" in result["errors"]


def test_plan_and_unit_shapes_fail_closed_on_unknown_fields():
    payload = plan()
    payload["unexpected"] = True
    assert any("unsupported fields" in error for error in validate(payload)["errors"])

    payload = plan()
    payload["units"][0]["unexpected"] = True
    assert any("unsupported fields" in error for error in validate(payload)["errors"])


def test_malformed_enum_values_fail_closed_instead_of_crashing():
    payload = plan()
    payload["planning_source"] = ["ad_hoc"]
    assert "planning_source is not supported" in validate(payload)["errors"]

    payload = plan()
    payload["units"][0]["role"] = ["reader"]
    assert "U1 has unsupported role" in validate(payload)["errors"]


def test_duplicate_unknown_self_and_cycle_dependencies_fail_closed():
    duplicate = plan()
    duplicate["units"][1]["unit_id"] = "U1"
    assert any("duplicates unit_id" in error for error in validate(duplicate)["errors"])

    unknown = plan()
    unknown["units"][1]["depends_on"] = ["U9"]
    assert "U2 depends on unknown unit U9" in validate(unknown)["errors"]

    self_dep = plan()
    self_dep["units"][1]["depends_on"] = ["U2"]
    assert "U2 cannot depend on itself" in validate(self_dep)["errors"]

    cycle = plan()
    cycle["units"][0]["depends_on"] = ["U2"]
    cycle["units"][1]["depends_on"] = ["U1"]
    assert "TeamPlan dependency graph contains a cycle" in validate(cycle)["errors"]


def test_ready_units_cannot_claim_overlapping_write_ownership():
    payload = plan()
    payload["units"][0] = {
        "unit_id": "U1",
        "role": "worker",
        "goal": "first write",
        "output": "first change",
        "depends_on": [],
        "ownership": {"write": ["src"], "forbidden": []},
        "done_when": "done",
    }
    payload["units"][1]["depends_on"] = []
    payload["units"][1]["ownership"]["write"] = ["src/example.py"]
    result = validate(payload)
    assert any("overlapping write scope" in error for error in result["errors"])


def test_policy_read_only_roles_cannot_claim_write_ownership():
    for role in VALIDATOR.READ_ONLY_ROLES:
        payload = plan()
        payload["units"][0]["role"] = role
        payload["units"][0]["ownership"]["write"] = ["src/read_only_violation.py"]
        result = validate(payload)
        assert any("read-only role must not declare write ownership" in error for error in result["errors"])


def test_ownership_paths_fail_closed_on_unsafe_or_conflicting_paths():
    for unsafe in ["../outside", "C:/outside", "C:outside"]:
        payload = plan()
        payload["units"][1]["ownership"] = {"write": [unsafe], "forbidden": []}
        assert any("safe relative path" in error for error in validate(payload)["errors"])

    payload = plan()
    payload["units"][1]["ownership"] = {"write": ["src"], "forbidden": ["src/generated"]}
    assert any("overlaps its forbidden scope" in error for error in validate(payload)["errors"])


def test_integration_order_must_cover_all_units_and_respect_dependencies():
    missing = plan()
    missing["integration_order"] = ["U1"]
    assert "integration_order must cover every delegated unit exactly once" in validate(missing)["errors"]

    reversed_order = plan()
    reversed_order["integration_order"] = ["U2", "U1"]
    assert "integration_order violates dependency order" in validate(reversed_order)["errors"]


def test_revision_chain_and_upstream_sources_are_explicit():
    revision = plan()
    revision["revision"] = 2
    revision["supersedes_revision"] = 1
    assert validate(revision)["team_plan_valid"] is True

    wrong = plan()
    wrong["revision"] = 3
    wrong["supersedes_revision"] = 1
    assert "supersedes_revision must name the direct previous revision" in validate(wrong)["errors"]

    upstream = plan()
    upstream["planning_source"] = "upstream_skill"
    assert "non-ad_hoc TeamPlan requires source_refs" in validate(upstream)["errors"]
    upstream["source_refs"] = ["upstream:stage-2"]
    assert validate(upstream)["team_plan_valid"] is True


def test_role_vocabulary_rejects_unknown_role():
    payload = plan()
    payload["units"][0]["role"] = "researcher"
    assert "U1 has unsupported role" in validate(payload)["errors"]
