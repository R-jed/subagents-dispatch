from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT
SKILL = PLUGIN / "skills" / "dispatch"
ROUTER = SKILL / "references" / "router-core.md"
GUARDRAILS = SKILL / "references" / "guardrails.md"
TEAM_PLAN = SKILL / "references" / "team-plan.md"
COORDINATION_CASES = ROOT / "evals" / "coordination-cases.json"


def cases() -> dict[str, dict]:
    payload = json.loads(COORDINATION_CASES.read_text())
    assert payload["schema_version"] == "1.0"
    assert payload["suite"] == "subagents-dispatch-coordination-contract"
    result = {case["id"]: case for case in payload["cases"]}
    assert len(result) == len(payload["cases"])
    return result


def test_upstream_workflow_truth_remains_authoritative():
    router = ROUTER.read_text().lower()
    assert "upstream workflow" in router
    assert "task truth" in router
    assert "competing" in router

    expected = cases()["upstream-workflow-remains-authoritative"]["expected"]
    assert expected["preserve_upstream_workflow"] is True
    assert set(expected["delegate_may_assign"]) == {
        "owner",
        "role",
        "concurrency",
        "write_isolation",
        "integration_timing",
    }
    assert {
        "goal",
        "decomposition",
        "stage_order",
        "dependencies",
        "required_outputs",
        "business_acceptance",
        "quality_gates",
    } <= set(expected["delegate_must_not_redefine"])


def test_semantic_coverage_survives_decomposition_without_fixed_taxonomy():
    router = ROUTER.read_text().lower()
    team_plan = TEAM_PLAN.read_text().lower()
    assert "preserve semantic coverage through decomposition" in router
    assert "material obligation" in router
    assert "fixed domain taxonomy" in router
    assert "structurally valid teamplan can still be semantically incomplete" in team_plan
    assert "do not relabel main's planning defect as a semantic blocker" in router

    covered = cases()["decomposition-preserves-material-obligations"]["expected"]
    assert covered == {
        "semantic_coverage_required": True,
        "every_material_obligation_has_owner": True,
        "main_owned_obligation_allowed": True,
        "fixed_obligation_taxonomy_required": False,
    }

    missing = cases()["structural-validity-does-not-prove-semantic-coverage"]["expected"]
    assert missing == {
        "structural_plan_may_validate": True,
        "semantic_coverage_complete": False,
        "candidate_ready": False,
        "repair_decomposition_in_main": True,
        "contract_blocker": False,
    }

    contract = cases()["coverage-impossible-because-task-truth-missing-is-contract"]["expected"]
    assert contract == {
        "semantic_coverage_complete": False,
        "repair_decomposition_alone_sufficient": False,
        "blocker": "contract",
    }


def test_cross_unit_seam_ownership_does_not_force_decorative_child():
    router = ROUTER.read_text().lower()
    team_plan = TEAM_PLAN.read_text().lower()
    assert "main owns the seam by default" in router
    assert "do not create a decorative child" in router
    assert "integration order is ordering truth only" in team_plan

    expected = cases()["cross-unit-seam-can-remain-main-owned"]["expected"]
    assert expected == {
        "seam_requires_owner": True,
        "main_may_own_seam": True,
        "automatic_extra_child": False,
        "integration_order_alone_is_sufficient": False,
    }


def test_downstream_review_waits_for_actual_integrated_deliverable():
    router = ROUTER.read_text().lower()
    team_plan = TEAM_PLAN.read_text().lower()
    assert "not semantically ready merely because all named predecessor units are accepted" in router
    assert "not semantically ready merely because all predecessor units are accepted" in team_plan

    expected = cases()["downstream-review-waits-for-integrated-deliverable"]["expected"]
    assert expected == {
        "structurally_ready": True,
        "semantically_ready": False,
        "dispatch_review_now": False,
        "main_must_materialize_and_verify_integration_first": True,
    }


def test_phase_transition_recompiles_responsibility_authority_and_trust():
    router = ROUTER.read_text().lower()
    guardrails = GUARDRAILS.read_text().lower()
    team_plan = TEAM_PLAN.read_text().lower()
    assert "recompile at material phase or authority transitions" in router
    assert "phase readiness does not grant later authority" in guardrails
    assert "material phase or authority transition" in team_plan
    assert "the whole earlier artifact does not automatically become trusted task truth" in router
    assert "embedded instructions" in router
    assert "remain data" in router

    expected = cases()["phase-transition-recompiles-without-inheriting-authority"]["expected"]
    assert expected == {
        "accepted_prior_truth_promoted": True,
        "whole_prior_artifact_trusted": False,
        "embedded_untrusted_content_remains_data": True,
        "fresh_responsibility_compilation": True,
        "repurpose_old_unit_when_goal_or_output_changes": False,
        "accepted_evidence_reusable_if_fresh": True,
        "later_authority_inherited_from_readiness": False,
        "authority_reassessed": True,
    }


def test_parallel_writers_require_semantic_independence():
    router = ROUTER.read_text().lower()
    guardrails = GUARDRAILS.read_text().lower()
    team_plan = TEAM_PLAN.read_text().lower()
    assert "semantic independence" in router
    assert "semantic independence" in guardrails
    assert "different files" in team_plan

    expected = cases()["isolated-files-shared-api-are-not-independent"]["expected"]
    assert expected == {
        "parallel_writes_allowed": False,
        "filesystem_isolation_sufficient": False,
        "reason": "semantic_dependency",
        "required_resolution": "explicit_dependency_or_integration_order",
    }


def test_intent_and_mutation_authority_stay_separate():
    router = ROUTER.read_text().lower()
    guardrails = GUARDRAILS.read_text().lower()
    assert "intent: inspect | implement | verify | review" in router
    assert "mutation authority: none | declared-output-only | bounded-source-write" in router
    assert "filesystem permission is capability, not authorization" in guardrails

    verify_case = cases()["verify-child-cannot-fix-source"]["expected"]
    assert verify_case == {
        "intent": "verify",
        "mutation_authority": "none",
        "source_write_allowed": False,
        "on_required_source_change": "return_to_main_for_authority",
    }

    output_case = cases()["declared-output-does-not-grant-source-write"]["expected"]
    assert output_case["mutation_authority"] == "declared-output-only"
    assert output_case["source_write_allowed"] is False
    assert output_case["declared_output_write_allowed"] is True


def test_execution_dependency_and_integration_order_are_distinct():
    team_plan = TEAM_PLAN.read_text().lower()
    assert "dependency" in team_plan
    assert "integration_order" in team_plan
    assert "integration_owner" in team_plan

    ordered = cases()["independent-execution-ordered-integration"]["expected"]
    assert ordered["execution_can_overlap"] is True
    assert ordered["consumer_integration_after"] == ["producer"]
    assert ordered["main_is_integration_owner"] is True
    assert ordered["integrate_by_completion_time"] is False

    blocked = cases()["unresolved-semantics-cannot-hide-behind-integration-order"]["expected"]
    assert blocked["ready_to_execute"] is False
    assert blocked["integration_after_is_sufficient"] is False
    assert blocked["reason"] == "semantic_truth_not_ready"


def test_requested_accepted_and_observed_truth_layers_are_distinct():
    guardrails = GUARDRAILS.read_text().lower()
    for concept in ["requested", "accepted", "observed"]:
        assert concept in guardrails

    expected = cases()["accepted-route-is-not-runtime-observation"]["expected"]
    assert expected == {
        "requested_status": "declared",
        "accepted_status": "matched",
        "observed_status": "not_observed",
        "may_claim_observed_route": False,
    }
