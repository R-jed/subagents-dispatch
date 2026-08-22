from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


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


def test_active_recovery_contracts_do_not_claim_unbounded_identity_or_basis_memory():
    state_text = (ROOT / "contracts/state.md").read_text(encoding="utf-8")
    recovery_text = (ROOT / "contracts/recovery.md").read_text(encoding="utf-8")

    for text in (state_text, recovery_text):
        lowered = text.lower()
        assert "unique for the lifetime of one orchestration" not in lowered
        assert "history compaction never authorizes reuse" not in lowered
        assert "generation" in lowered
        assert "retained" in lowered


def test_eval_oracles_follow_current_product_ceiling_and_evidence_gated_recovery():
    readme = (ROOT / "evals/README.md").read_text(encoding="utf-8").lower()
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


def test_phase_status_is_evidence_based_while_remediation_head_is_unverified():
    phase = read_json("docs/v4/phase-status.json")

    assert phase["candidate_branch"] == "v4/rc5-review-remediation"
    assert set(phase["repository_phases"].values()) == {"PENDING_REVALIDATION"}
    assert phase["publication"] == "BLOCKED"
    assert phase["host_capability_feasibility"]["status"] == "PENDING"
