from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_phase0_host_feasibility_matrix_starts_fail_closed():
    matrix = json.loads(
        (ROOT / "docs" / "v4" / "host-capability-matrix.json").read_text(encoding="utf-8")
    )

    assert matrix["status"] == "PENDING"
    assert matrix["release_authority"] is False
    assert matrix["evidence_refs"] == []
    assert set(matrix["profiles"]) == {"reader", "worker", "investigator", "solver", "advisor"}
    assert set(matrix["capabilities"].values()) == {"unknown"}
    assert matrix["decision_policy"] == {
        "unknown_means_unavailable": True,
        "profile_request_is_effective_truth": False,
        "max_depth_is_v2_containment_proof": False,
        "hook_is_sufficient_hard_boundary": False,
        "release_gate_equivalent": False,
    }


def test_n1_requires_observed_or_authoritatively_denied_child_collaboration():
    contract = json.loads(
        (ROOT / "docs" / "v4" / "host-smoke.json").read_text(encoding="utf-8")
    )
    n1 = next(probe for probe in contract["required_probes"] if probe["id"] == "N1")

    assert n1["accepted_grandchild_outcomes"] == [
        "collaboration_tool_absent",
        "host_authoritative_deny",
    ]
    assert "compatibility_boundary" not in n1
    joined = " ".join(n1["requires"])
    assert "no descendant child identity materializes" in joined
    assert "cannot satisfy containment evidence" in joined


def test_machine_contracts_do_not_restore_retired_phase3_budgets_or_scheduler_policy():
    architecture = json.loads(
        (ROOT / "docs" / "v4" / "architecture.json").read_text(encoding="utf-8")
    )
    scheduler = json.loads(
        (ROOT / "docs" / "v4" / "scheduler.json").read_text(encoding="utf-8")
    )
    writer = json.loads(
        (ROOT / "docs" / "v4" / "writer-lifecycle.json").read_text(encoding="utf-8")
    )
    orchestrate = json.loads(
        (ROOT / "docs" / "v4" / "orchestrate.json").read_text(encoding="utf-8")
    )

    assert "fresh_agent_attempt_limit" not in architecture["execution"]
    assert architecture["execution"]["fresh_retry_authorization"] == "new_execution_basis_and_safe_settlement"
    assert "execution_basis_ref" in architecture["entities"]["ExecutionBinding"]["fields"]
    assert architecture["scheduler"]["selection_owner"] == "main"
    assert architecture["scheduler"]["ready_frontier_ranking"] == "none"
    assert architecture["scheduler"]["fixed_acceptance_backpressure"] is False
    assert scheduler["product_managed_children_max"] == 4
    for retired in (
        "initial_managed_children_max",
        "progressive_refill",
        "priority",
        "backpressure",
        "fresh_attempt_limit_per_work_unit",
    ):
        assert retired not in scheduler
    assert "focused_followup_limit" not in writer["same_child"]
    assert writer["same_child"]["followup_authorization"] == "new_correction_basis"
    assert orchestrate["managed_child_containment"] == "requires_host_evidence"


def test_n8_requires_effective_advisor_read_only_truth():
    contract = json.loads(
        (ROOT / "docs" / "v4" / "host-smoke.json").read_text(encoding="utf-8")
    )
    n8 = next(probe for probe in contract["required_probes"] if probe["id"] == "N8")
    joined = " ".join(n8["requires"])

    assert "effective Advisor sandbox and permission state" in joined
    assert "requested profile sandbox" in joined

    final_review = (ROOT / "contracts" / "final-review.md").read_text(encoding="utf-8")
    assert "effective sandbox and permission state satisfy the read-only boundary" in final_review
    assert "INSUFFICIENT_EVIDENCE" in final_review
