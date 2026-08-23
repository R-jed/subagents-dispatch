from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tomllib

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
POLICY = json.loads((CONTRACTS / "policy.json").read_text(encoding="utf-8"))
ADVISOR = ROOT / "agent-profiles" / "subagents-dispatch-advisor.toml"
SCHEMA = ROOT / "evals" / "behavioral-result.schema.json"
SCORER = ROOT / "scripts" / "score-behavioral-evals.py"


def test_advisor_route_is_fixed_containment_safe_read_only():
    spec = POLICY["roles"]["advisor"]
    profile = tomllib.loads(ADVISOR.read_text(encoding="utf-8"))
    assert spec["model"] == profile["model"] == "gpt-5.6-luna"
    assert spec["effort"] == profile["model_reasoning_effort"] == "max"
    assert spec["mutation_authority"] == "none"
    assert spec["agent_type"] == "subagents_dispatch_advisor"
    assert POLICY["delegation"]["fork_turns"] == "none"
    assert POLICY["containment"]["managed_model_multi_agent_version"] == "v1"
    assert POLICY["containment"]["v2_capable_managed_child_models_allowed"] is False


def test_review_verdict_policy_remains_fail_closed():
    final = POLICY["final_review"]
    assert final["ship_verdict"] == "ship"
    assert final["correction_verdicts"] == ["fix-first", "rethink"]
    assert final["unresolved_verdict"] == "insufficient_evidence"


def test_behavioral_schema_keeps_review_metrics_and_verdicts():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    props = schema["properties"]["runs"]["items"]["properties"]
    for field in (
        "final_review_requirement",
        "final_review_trigger_reasons",
        "final_review_attempts",
        "final_review_verdict",
        "final_review_gate_satisfied",
        "review_artifact_verify_failures",
        "post_review_mutations",
    ):
        assert field in props
    assert "insufficient_evidence" in props["final_review_verdict"]["enum"]


def _run(mode: str) -> dict:
    return {
        "workload_id": "bounded-implementation",
        "mode": mode,
        "pair_id": "final-review-metrics-1",
        "repeat_index": 1,
        "repo_revision": "candidate-sha",
        "workload_definition_hash": "sha256:workload-fixture",
        "main_session_route": "gpt-5.6-sol/high",
        "main_judgment_coverage": "covered",
        "dependency_kind": "bounded_execution",
        "execution_route": "gpt-5.6-luna/max",
        "permissions_fingerprint": "workspace-write+default-approval",
        "tool_surface_fingerprint": "spawn-agent-v2+shell+git",
        "acceptance_rubric_id": "final-review-metrics-v1",
        "success": True,
        "decision": "complete",
        "agent_count": 1,
        "peak_active_children": 1,
        "ready_dependencies": 1,
        "runtime_slot_waits": 0,
        "roles": ["worker"],
        "policy_violations": [],
        "scope_violations": 0,
        "wrong_edits": 0,
        "regressions": 0,
        "material_judgment_violations": 0,
        "correction_turns": 0,
        "reclassification_events": 0,
        "execution_stall_events": 0,
        "clean_same_lane_restarts": 0,
        "unjustified_retry_calls": 0,
        "same_failure_without_new_evidence": 0,
        "judgment_uplift_calls": 0,
        "solver_calls": 0,
        "advisor_calls": 0,
        "terra_calls": 0,
        "redundant_sol_calls": 0,
        "review_findings": 0,
        "review_false_positives": 0,
        "final_review_attempts": 0,
        "review_artifact_verify_failures": 0,
        "post_review_mutations": 0,
        "consent_prompts": 0,
        "evidence_established": 1,
        "evidence_invalidated": 0,
        "unjustified_repeated_commands": 0,
        "unjustified_repeated_discovery": 0,
        "duplicate_dependency_calls": 0,
    }


def _score(tmp_path: Path, runs: list[dict]) -> subprocess.CompletedProcess[str]:
    result_path = tmp_path / "result.json"
    result_path.write_text(
        json.dumps(
            {
                "schema_version": "4.0",
                "suite": "subagents-dispatch-live-behavior",
                "runtime": {"codex_version": "fixture", "date": "2026-08-05"},
                "runs": runs,
            }
        ),
        encoding="utf-8",
    )
    return subprocess.run(
        [sys.executable, str(SCORER), str(result_path), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_scorer_rejects_satisfied_gate_without_ship_verdict(tmp_path: Path):
    baseline = _run("raw_prompt_luna")
    candidate = _run("bounded_luna")
    candidate.update(
        {
            "final_review_requirement": "required",
            "final_review_trigger_reasons": ["public_contract_change"],
            "final_review_attempts": 1,
            "final_review_verdict": "fix-first",
            "final_review_gate_satisfied": True,
        }
    )
    result = _score(tmp_path, [baseline, candidate])
    assert result.returncode != 0
    assert "without the ship verdict" in result.stderr


def test_behavioral_workloads_cover_review_invalidation():
    workloads = json.loads((ROOT / "evals" / "behavioral-workloads.json").read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in workloads["workloads"]}
    assert by_id["public-contract-final-review-required"]["expected"]["fresh_sol_required"] is True
    assert by_id["post-review-mutation-invalidates-ship"]["expected"]["old_verdict_valid"] is False
