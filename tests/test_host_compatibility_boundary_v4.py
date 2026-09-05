from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHITECTURE = ROOT / "docs" / "v4" / "architecture.json"
ORCHESTRATE_SKILL = ROOT / "skills" / "orchestrate" / "SKILL.md"
GUARDRAILS = ROOT / "contracts" / "guardrails.md"
NATIVE_RUNTIME = ROOT / "docs" / "native-subagent-runtime.md"
REMOVED_PROJECTIONS = (
    ROOT / "docs" / "v4" / "host-capability-matrix.json",
    ROOT / "docs" / "v4" / "orchestrate.json",
    ROOT / "docs" / "v4" / "phase-status.json",
    ROOT / "docs" / "v4" / "scheduler.json",
    ROOT / "docs" / "v4" / "writer-lifecycle.json",
)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_architecture_is_the_single_current_machine_owner_for_v4_projections():
    architecture = read_json(ARCHITECTURE)

    assert all(not path.exists() for path in REMOVED_PROJECTIONS)
    assert architecture["routing"]["role_selection_owner"] == "main"
    assert architecture["routing"]["exact_route_resolution_owner"] == "deterministic_policy"
    assert architecture["scheduler"]["selection_owner"] == "main"
    assert architecture["scheduler"]["product_managed_children_max"] == 4
    assert architecture["writer_lease"]["scope"] == "canonical_workspace"
    assert architecture["control_semantics"]["INTERRUPT"]["interrupt_result_releases_writer"] is False
    assert architecture["delegation"]["max_depth"] == 1
    assert architecture["delegation"]["max_depth_scope"] == "project_policy"
    assert architecture["delegation"]["max_depth_is_v2_host_containment_proof"] is False


def test_runtime_guidance_does_not_restore_host_hard_depth_requirement():
    skill = ORCHESTRATE_SKILL.read_text(encoding="utf-8")
    guardrails = GUARDRAILS.read_text(encoding="utf-8")
    runtime = NATIVE_RUNTIME.read_text(encoding="utf-8")

    assert "Managed child profiles must expose no child collaboration surface" not in skill
    assert "effective child collaboration surface remains a Host fact" in skill
    assert "latent V2 recursive capability does not by itself block ordinary managed execution" in skill
    assert "Managed children cannot create or control further Agents" in skill

    assert "Delegated execution is eligible only when the required Host containment evidence is available" not in guardrails
    assert "Ordinary delegated execution does not require Host-hard descendant isolation" in guardrails
    assert "direct current-Host evidence" in guardrails

    assert "Delegation that requires leaf containment therefore depends on observed collaboration-tool absence" not in runtime
    assert "The depth-one product rule does not require Host-hard tool removal" in runtime
    assert "current Host" in runtime


def test_machine_contract_keeps_current_phase3_semantics_without_parallel_projections():
    architecture = read_json(ARCHITECTURE)

    assert "fresh_agent_attempt_limit" not in architecture["execution"]
    assert architecture["execution"]["control_epoch_scope"] == "execution_binding"
    assert architecture["execution"]["fresh_retry_authorization"] == "new_execution_basis_and_safe_settlement"
    assert "execution_basis_ref" in architecture["entities"]["ExecutionBinding"]["fields"]
    assert architecture["scheduler"]["ready_frontier_ranking"] == "none"
    assert architecture["scheduler"]["fixed_acceptance_backpressure"] is False
    assert architecture["execution"]["same_child_followup_authorization"] == "new_correction_basis"
    assert architecture["execution"]["followup_count_is_diagnostic"] is True
    assert architecture["invariants"]["I08"].startswith("Main is the sole managed coordinator")


def test_final_review_owns_reviewer_permission_assurance_outside_host_reference():
    final_review = (ROOT / "contracts" / "final-review.md").read_text(encoding="utf-8")
    assert "enforced_read_only" in final_review
    assert "artifact_immutability_fallback" in final_review
    assert "hard_isolation_required" in final_review
    assert "INSUFFICIENT_EVIDENCE" in final_review
