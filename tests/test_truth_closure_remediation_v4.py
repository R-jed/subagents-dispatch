from __future__ import annotations

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def read_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def read_text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def current_authority_text_files() -> list[Path]:
    files: set[Path] = {
        ROOT / "README.md",
        ROOT / "README_EN.md",
        ROOT / "README_AI.md",
        ROOT / "CHANGELOG.md",
    }
    for folder, suffixes in (
        (ROOT / "contracts", {".md", ".json"}),
        (ROOT / "docs", {".md"}),
        (ROOT / "docs" / "v4", {".json"}),
        (ROOT / "evals", {".md", ".json"}),
        (ROOT / "tasks", {".md"}),
    ):
        for path in folder.glob("*"):
            if path.is_file() and path.suffix in suffixes:
                files.add(path)
    for path in (ROOT / "skills").glob("*/SKILL.md"):
        files.add(path)
    return sorted(files)


def test_machine_architecture_tracks_current_host_and_capacity_truth():
    architecture = read_json("docs/v4/architecture.json")

    assert architecture["reconciliation"]["observation_basis"] == [
        "execution_id",
        "unit_id",
        "attempt_no",
        "control_epoch",
        "lease_epoch",
    ]
    scheduler = architecture["scheduler"]
    assert scheduler["selection_owner"] == "main"
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

    architecture = read_text("docs/architecture.md")
    assert "Compaction does not authorize reuse of execution or native task identities" not in architecture
    assert "Compaction never makes stale Host evidence current again" in architecture
    assert "generation-distinct canonical native task names" in architecture


def test_active_contracts_keep_workgraph_authority_and_current_profile_labels():
    composition = read_text("contracts/composition.md")
    evidence_artifact = read_text("contracts/evidence-artifact.md")
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
    assert "Dispatch:" not in receipt
    assert "Orchestrate:" in receipt
    assert "Ordinary Dispatch" not in evidence_artifact
    assert "Orchestrate responsibility" in evidence_artifact


def test_eval_oracles_follow_current_product_ceiling_and_evidence_gated_recovery():
    readme = read_text("evals/README.md").lower()
    interactions = read_json("evals/interaction-cases.json")
    workloads = read_json("evals/behavioral-workloads.json")
    routing = read_json("evals/routing-cases.json")

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
    assert by_workload["execution-stall-clean-restart"]["expected"]["unchanged_retry_forbidden"] is True

    by_routing = {item["id"]: item for item in routing["cases"]}
    local_retry = by_routing["local-defect-can-retry-same-worker"]["expected"]
    assert local_retry["recovery_action"] == "same_role_retry"
    stalled = by_routing["stalled-work-does-not-create-a-model-ladder"]["expected"]
    assert stalled["task_blocker"] == "stalled"
    assert stalled["action"] == "main_session"
    assert stalled["recovery_action"] is None
    assert stalled["nodes"] == []
    assert stalled["main_reason"] == "unchanged_retry_not_authorized"


def test_current_authority_surfaces_do_not_reintroduce_retired_product_or_budget_logic():
    retired_phrases = (
        "Ordinary Dispatch",
        "explicit Dispatch",
        "through Dispatch",
        "Dispatch Receipt",
        "Select **Preview** through the Host UI",
        "CHANGELOG_V3.md",
        "managed initial fan-out ceiling remains two",
        "frozen product ceiling of three",
        "two fresh attempts maximum per unchanged WorkUnit",
        "one focused same-child follow-up budget",
        "H00-H20",
    )

    failures: list[str] = []
    for path in current_authority_text_files():
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT).as_posix()
        for phrase in retired_phrases:
            if phrase in text:
                failures.append(f"{relative}: {phrase}")
        if re.search(r"\bDispatch\b", text):
            failures.append(f"{relative}: standalone Dispatch product term")

    assert not failures, "retired current-authority logic found:\n" + "\n".join(failures)


def test_history_documents_are_explicitly_non_authoritative():
    history = ROOT / "docs" / "history"
    readme = (history / "README.md").read_text(encoding="utf-8")
    assert "do not define current V4 product behavior" in readme
    assert "Historical documents may intentionally contain retired terms and rules" in readme

    markdown_files = sorted(path for path in history.rglob("*.md") if path.name != "README.md")
    assert markdown_files
    for path in markdown_files:
        text = path.read_text(encoding="utf-8")
        assert text.startswith("> Historical archive."), path.relative_to(ROOT).as_posix()
        assert "not a current V4 contract" in text.splitlines()[0], path.relative_to(ROOT).as_posix()

    json_files = sorted(history.rglob("*.json"))
    assert json_files
    for path in json_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload.get("historical_archive") is True, path.relative_to(ROOT).as_posix()
        assert payload.get("current_runtime_authority") is False, path.relative_to(ROOT).as_posix()

    assert not (ROOT / "docs" / "v3.0.0-post-release-final-audit.md").exists()
    assert (history / "v3.0.0-post-release-final-audit.md").is_file()


def test_candidate_status_has_no_self_stale_git_snapshot():
    assert not (ROOT / "docs" / "v4" / "phase-status.json").exists()
    assert "phase-status.json" not in read_text("README_AI.md")
    current_state = read_text("docs/v4/current-state.md")
    assert "current GitHub / real-Host evidence have higher authority" in current_state
    assert "Issue #91 remains the append-only Real Host Test Ledger" in current_state
