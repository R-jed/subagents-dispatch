from __future__ import annotations

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def read_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def read_text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_machine_architecture_tracks_generation_safe_host_basis_and_capacity_truth():
    architecture = read_json("docs/v4/architecture.json")

    assert architecture["reconciliation"]["observation_basis"] == [
        "execution_id",
        "unit_id",
        "attempt_no",
        "control_epoch",
        "lease_epoch",
    ]
    scheduler = architecture["scheduler"]
    assert scheduler["host_capacity_semantics"] == "session_concurrency_includes_primary"
    assert scheduler["missing_capability_snapshot_blocks_spawn"] is True
    assert scheduler["unknown_host_capacity_blocks_spawn"] is False


def test_scheduler_machine_contract_matches_host_session_capacity_semantics():
    scheduler = read_json("docs/v4/scheduler.json")

    assert scheduler["mode"] == "constraint_projection"
    assert scheduler["selection_owner"] == "main"
    assert scheduler["host_capacity_owner"] == "codex_host"
    assert scheduler["host_capacity_semantics"] == "session_concurrency_includes_primary"
    assert scheduler["known_host_session_capacity_is_advisory_ceiling"] is True
    assert scheduler["missing_capability_snapshot_blocks_spawn"] is True
    assert scheduler["unknown_host_capacity_blocks_spawn"] is False
    assert scheduler["product_managed_children_max"] == 4
    assert scheduler["automatic_launch_actions"] is False


def test_active_recovery_contracts_do_not_claim_unbounded_identity_or_basis_memory():
    state_text = read_text("contracts/state.md")
    recovery_text = read_text("contracts/recovery.md")

    for text in (state_text, recovery_text):
        lowered = text.lower()
        assert "unique for the lifetime of one orchestration" not in lowered
        assert "history compaction never authorizes reuse" not in lowered
        assert "generation" in lowered
        assert "retained" in lowered


def test_active_contracts_keep_workgraph_authority_and_current_profile_labels():
    composition = read_text("contracts/composition.md")
    handoff = read_text("contracts/handoff.md")
    interaction = read_text("contracts/interaction.md")
    responsibility = read_text("contracts/responsibility-packet.md")
    receipt = read_text("contracts/receipt.md")
    team_plan = read_text("contracts/team-plan.md")
    policy = read_json("contracts/policy.json")

    assert "WorkUnit and optional TeamPlan structure" not in composition
    assert "WorkGraph and WorkUnit responsibility structure" in composition

    for stale in (
        "superseding TeamPlan revision",
        "plus TeamPlan when required",
        "TeamPlan when active",
    ):
        assert stale not in handoff
    assert "WorkGraph dependencies when required" in handoff

    for stale in (
        "team-plan.md` still owns multi-responsibility dependency and integration truth",
        "尝试: 1/2",
        "focused-correction followup budget",
        "one focused same-child followup",
    ):
        assert stale not in interaction
    assert "WorkGraph and WorkUnit own multi-responsibility dependency and responsibility truth" in interaction
    assert "There is no fixed correction-count ceiling" in interaction

    assert "already owns the multi-responsibility structural truth" not in responsibility
    assert "carries no dependency, routing, integration-order, retry-budget, ownership, or acceptance authority" in responsibility
    assert "no independent TeamPlan runtime authority" in team_plan

    assert policy["roles"]["investigator"]["effort"] == "high"
    assert "Terra XHigh" not in receipt
    assert "Terra High" in receipt
    assert "derive from the fixed profiles in `policy.json`" in receipt


def test_eval_oracles_follow_current_product_ceiling_and_evidence_gated_recovery():
    readme = read_text("evals/README.md").lower()
    interactions = read_json("evals/interaction-cases.json")
    workloads = read_json("evals/behavioral-workloads.json")

    assert "xhigh" not in readme
    assert "initial managed fanout is at most 2" not in readme
    assert "ordinary managed fanout is at most 3" not in readme
    assert "managed child product ceiling is 4" in readme

    by_case = {item["id"]: item for item in interactions["cases"]}
    correction = by_case["orchestrate-correction-bounded-followup"]["expected"]
    assert "focused_followup_limit" not in correction
    assert correction["correction_basis_required"] is True
    assert correction["fixed_followup_count_ceiling"] is False

    by_workload = {item["id"]: item for item in workloads["workloads"]}
    fanout = by_workload["five-independent-readers-queued"]["expected"]
    assert "initial_managed_children_max" not in fanout
    assert fanout["product_managed_children_max"] == 4
    assert fanout["queue_remainder"] is True


def test_phase_status_records_verified_repository_basis_and_keeps_release_gates_pending():
    phase = read_json("docs/v4/phase-status.json")
    validation = phase["repository_validation"]

    assert phase["candidate_branch"] == "v4/rc5-review-remediation"
    assert set(phase["repository_phases"].values()) == {"PASS"}
    assert validation["status"] == "PASS"
    assert re.fullmatch(r"[0-9a-f]{40}", validation["candidate_sha"])
    assert isinstance(validation["workflow_run_id"], int) and validation["workflow_run_id"] > 0
    assert "final CI regression run" in validation["attestation_scope"]
    for removed in ("CHANGELOG_V3.md", "PRIVACY.md", "TERMS.md", "THIRD_PARTY_NOTICES.md"):
        assert removed in validation["attestation_scope"]
    assert phase["publication"] == "BLOCKED"
    assert phase["host_capability_feasibility"]["status"] == "PENDING"
    assert phase["host_capability_feasibility"]["release_authority"] is False
    assert phase["real_host_gate"]["status"] == "PENDING_RELEASE_GATE"
    assert phase["real_host_gate"]["required_campaign"] == "N0-N8"
    assert phase["final_review"] == "PENDING_RELEASE_GATE"
    assert phase["external_release_evidence"] == "PENDING_RELEASE_GATE"
