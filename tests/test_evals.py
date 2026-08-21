from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import jsonschema
import pytest
ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / 'evals' / 'behavioral-result.schema.json'
WORKLOADS = ROOT / 'evals' / 'behavioral-workloads.json'
SCRIPTS = ROOT / 'scripts'
SCORER = SCRIPTS / 'score-behavioral-evals.py'

def load_scorer_module():
    scripts_dir = str(SCRIPTS)
    sys.path.insert(0, scripts_dir)
    try:
        spec = importlib.util.spec_from_file_location('subagents_dispatch_behavioral_scorer', SCORER)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts_dir)
SCORER_MODULE = load_scorer_module()

def base_run(mode: str) -> dict:
    return {'workload_id': 'bounded-implementation', 'mode': mode, 'pair_id': 'bounded-1', 'repeat_index': 1, 'repo_revision': 'abc123', 'workload_definition_hash': 'sha256:fixture', 'main_session_route': 'gpt-5.6-sol/high', 'main_judgment_coverage': 'covered', 'dependency_kind': 'bounded_execution', 'execution_route': 'gpt-5.6-luna/max', 'permissions_fingerprint': 'workspace-write+default-approval', 'tool_surface_fingerprint': 'spawn-agent-v2+shell+git', 'acceptance_rubric_id': 'bounded-v1', 'success': True, 'decision': 'complete', 'agent_count': 1, 'peak_active_children': 1, 'ready_dependencies': 1, 'runtime_slot_waits': 0, 'roles': ['worker'], 'policy_violations': [], 'scope_violations': 0, 'wrong_edits': 0, 'regressions': 0, 'material_judgment_violations': 0, 'correction_turns': 0, 'reclassification_events': 0, 'execution_stall_events': 0, 'clean_same_lane_restarts': 0, 'unjustified_retry_calls': 0, 'same_failure_without_new_evidence': 0, 'judgment_uplift_calls': 0, 'solver_calls': 0, 'advisor_calls': 0, 'terra_calls': 0, 'redundant_sol_calls': 0, 'review_findings': 0, 'review_false_positives': 0, 'final_review_attempts': 0, 'consent_prompts': 0, 'evidence_established': 1, 'evidence_invalidated': 0, 'unjustified_repeated_commands': 0, 'unjustified_repeated_discovery': 0, 'duplicate_dependency_calls': 0}

def score(tmp_path: Path, runs: list[dict]) -> subprocess.CompletedProcess[str]:
    result_file = tmp_path / 'result.json'
    result_file.write_text(json.dumps({'schema_version': '4.0', 'suite': 'subagents-dispatch-live-behavior', 'runtime': {'codex_version': 'fixture', 'date': '2026-08-05'}, 'runs': runs}), encoding='utf-8')
    return subprocess.run([sys.executable, str(SCORER), str(result_file), '--json'], cwd=ROOT, text=True, capture_output=True, check=False)

def test_behavioral_registry_and_schema_remain_valid_measurement_surfaces():
    workloads = json.loads(WORKLOADS.read_text(encoding='utf-8'))
    schema = json.loads(SCHEMA.read_text(encoding='utf-8'))
    assert workloads['schema_version'] == '4.0'
    assert workloads['suite'] == 'subagents-dispatch-live-behavior'
    jsonschema.Draft202012Validator.check_schema(schema)
    ids = {item['id'] for item in workloads['workloads']}
    assert len(ids) == len(workloads['workloads'])
    assert {'bounded-implementation', 'judgment-coupled-nonsol', 'judgment-coupled-sol-main', 'technical-delta-after-semantics', 'process-history-does-not-force-review', 'public-contract-final-review-required', 'main-route-observability', 'semantic-coverage-multi-responsibility-plan', 'phase-transition-recompile-after-authorization', 'orchestrate-first-use-restart-required', 'orchestrate-status-preserves-unknown', 'orchestrate-steer-preserves-responsibility'} <= ids

def test_schema_requires_control_fields_and_rejects_unknown_run_fields():
    schema = json.loads(SCHEMA.read_text(encoding='utf-8'))
    payload = {'schema_version': '4.0', 'suite': 'subagents-dispatch-live-behavior', 'runtime': {'codex_version': 'fixture', 'date': '2026-08-05'}, 'runs': [base_run('raw_prompt_luna'), base_run('bounded_luna')]}
    jsonschema.Draft202012Validator(schema).validate(payload)
    for field in ['main_judgment_coverage', 'dependency_kind', 'execution_route']:
        invalid_run = base_run('bounded_luna')
        invalid_run.pop(field)
        invalid = {**payload, 'runs': [base_run('raw_prompt_luna'), invalid_run]}
        assert list(jsonschema.Draft202012Validator(schema).iter_errors(invalid))
    unknown = base_run('bounded_luna')
    unknown['input_toknes'] = 100
    invalid = {**payload, 'runs': [base_run('raw_prompt_luna'), unknown]}
    assert list(jsonschema.Draft202012Validator(schema).iter_errors(invalid))

def test_workload_registry_duplicate_ids_fail_closed():
    duplicate = {'workloads': [{'id': 'same', 'expected': {}}, {'id': 'same', 'expected': {}}]}
    with pytest.raises(SystemExit, match='duplicates workload id'):
        SCORER_MODULE.workload_specs(duplicate)

def test_scorer_enforces_pair_controls_and_reports_primary_delta(tmp_path: Path):
    baseline = base_run('raw_prompt_luna')
    baseline.update({'acceptance_score': 7, 'correction_turns': 2, 'input_tokens': 1000})
    candidate = base_run('bounded_luna')
    candidate.update({'acceptance_score': 9, 'correction_turns': 0, 'input_tokens': 800})
    result = score(tmp_path, [baseline, candidate])
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    comparison = summary['pairs']['bounded-1']['comparison']
    assert comparison['baseline_mode'] == 'raw_prompt_luna'
    assert comparison['candidate_mode'] == 'bounded_luna'
    assert comparison['metric_deltas']['acceptance_score'] == 2
    assert comparison['metric_deltas']['correction_turns'] == -2
    assert comparison['metric_deltas']['input_tokens'] == -200
    assert summary['mode_aggregates_are_descriptive_only'] is True
    changed = base_run('bounded_luna')
    changed['main_judgment_coverage'] = 'unknown'
    result = score(tmp_path, [base_run('raw_prompt_luna'), changed])
    assert result.returncode != 0
    assert "controlled field 'main_judgment_coverage'" in result.stderr

def test_scorer_rejects_impossible_peak_concurrency(tmp_path: Path):
    baseline = base_run('raw_prompt_luna')
    candidate = base_run('bounded_luna')
    candidate['peak_active_children'] = 2
    result = score(tmp_path, [baseline, candidate])
    assert result.returncode != 0
    assert 'peak_active_children exceeds agent_count' in result.stderr

def test_execution_route_is_allowed_to_be_the_experimental_variable(tmp_path: Path):
    baseline = base_run('raw_prompt_luna')
    candidate = base_run('bounded_luna')
    candidate['execution_route'] = 'gpt-5.6-sol/high'
    result = score(tmp_path, [baseline, candidate])
    assert result.returncode == 0, result.stderr
    pair = json.loads(result.stdout)['pairs']['bounded-1']
    assert pair['execution_routes']['raw_prompt_luna'] != pair['execution_routes']['bounded_luna']

def test_scorer_does_not_invent_missing_telemetry(tmp_path: Path):
    baseline = base_run('raw_prompt_luna')
    candidate = base_run('bounded_luna')
    result = score(tmp_path, [baseline, candidate])
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    comparison = summary['pairs']['bounded-1']['comparison']
    assert comparison['metric_deltas']['input_tokens'] is None
    assert summary['modes']['bounded_luna']['mean_input_tokens'] is None

def test_live_behavior_registry_covers_current_orchestrate_interaction_and_handoff_workloads():
    payload = json.loads(WORKLOADS.read_text(encoding='utf-8'))
    by_id = {item['id']: item for item in payload['workloads']}
    required = {'orchestrate-preview-no-execution', 'orchestrate-takeover-running-writer', 'handoff-capsule-reuse', 'native-core-execution-receipt', 'five-independent-readers-queued'}
    assert required <= set(by_id)
    preview = by_id['orchestrate-preview-no-execution']['expected']
    assert preview['child_spawns'] == 0
    assert preview['profile_provisioning'] == 0
    assert preview['source_mutations'] == 0
    assert preview['external_actions'] == 0
    assert preview['provisional_plan'] is True
    takeover = by_id['orchestrate-takeover-running-writer']['expected']
    assert takeover['native_stop_before_transfer'] is True
    assert takeover['main_conflicting_writes_before_settlement'] == 0
    assert takeover['unknown_does_not_transfer'] is True
    handoff = by_id['handoff-capsule-reuse']['expected']
    assert handoff['fork_turns_none'] is True
    assert handoff['unverified_claims_propagated'] == 0
    assert handoff['stale_evidence_requires_reverification'] is True
    receipt = by_id['native-core-execution-receipt']['expected']
    assert receipt['minimum_receipt_lines'] == 2
    assert receipt['unsupported_runtime_claims'] == 0
    assert receipt['zero_child_minimal_receipt'] is True
    assert receipt['persistent_receipt_ledger'] is False
    assert receipt['current_state_facts_only'] is True
    fanout = by_id['five-independent-readers-queued']['expected']
    assert fanout['initial_managed_children_max'] == 2
    assert fanout['product_managed_children_max'] == 3
    assert fanout['queue_remainder'] is True
    assert fanout['unknown_host_capacity_blocks_bounded_spawn'] is False
