from __future__ import annotations
from pathlib import Path
import json
import tomllib
import subprocess
import sys
import jsonschema
import os
import pytest
import importlib.util
ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / 'contracts'

def test_explicit_skill_selection_can_cover_first_required_final_review():
    final_review = (REFERENCES / 'final-review.md').read_text(encoding='utf-8').lower()
    guardrails = (REFERENCES / 'guardrails.md').read_text(encoding='utf-8').lower()
    assert 'fresh review after explicit user selection/invocation of dispatch' in final_review
    assert 'normal bounded orchestration envelope' in final_review
    assert 'child count by itself is not a consent trigger' in guardrails
    assert 'material compute expansion' in guardrails

def test_implicit_invocation_is_disabled_while_explicit_skill_selection_is_the_entrypoint():
    openai = (ROOT / 'skills' / 'dispatch' / 'agents' / 'openai.yaml').read_text(encoding='utf-8')
    guardrails = (REFERENCES / 'guardrails.md').read_text(encoding='utf-8')
    assert 'allow_implicit_invocation: false' in openai
    assert 'supported entrypoints are explicit user selection/invocation' in guardrails
    for skill_id in ['dispatch', 'preview', 'status', 'steer', 'takeover', 'doctor']:
        assert f'`{skill_id}`' in guardrails
    assert 'Exact interaction inputs are owned by `interaction.md`' in guardrails
    assert 'Explicit invocation only' in guardrails

def test_declined_required_review_remains_incomplete():
    final_review = (REFERENCES / 'final-review.md').read_text(encoding='utf-8').lower()
    assert 'user declines' in final_review
    assert 'independent assurance remains incomplete' in final_review
    assert 'do not silently downgrade' in final_review

def test_repeated_final_review_cycles_remain_compute_consent_bounded():
    final_review = (REFERENCES / 'final-review.md').read_text(encoding='utf-8').lower()
    guardrails = (REFERENCES / 'guardrails.md').read_text(encoding='utf-8').lower()
    assert 'repeated correction/re-review loops' in final_review
    assert 'material compute expansion' in final_review
    assert 'repeated expensive solver, advisor, investigator' in guardrails
ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT
SKILL = PLUGIN / 'skills' / 'dispatch'
CONTRACTS = PLUGIN / 'contracts'
PROFILES = PLUGIN / 'agent-profiles'
POLICY = CONTRACTS / 'policy.json'

def contract():
    return json.loads(POLICY.read_text(encoding='utf-8'))

def test_final_review_is_linked_and_semantically_triggered():
    skill = (SKILL / 'SKILL.md').read_text(encoding='utf-8')
    review = (CONTRACTS / 'final-review.md').read_text(encoding='utf-8')
    assert '../../contracts/final-review.md' in skill
    assert 'Candidate Ready' in review
    assert 'requested deliverable is complete enough for acceptance' in review
    assert 'semantic coverage closure' in review
    assert 'For Git-backed deliverables' in review
    assert 'For a non-Git deliverable' in review
    assert 'deterministic SHA-256 digest' in review
    assert 'Do not hash a summary' in review
    assert 'Process history' in review
    for trigger in contract()['final_review']['trigger_codes']:
        assert trigger in review

def test_current_advisor_route_matches_policy_and_is_fresh():
    spec = contract()['roles']['advisor']
    advisor = tomllib.loads((PROFILES / spec['profile_file']).read_text(encoding='utf-8'))
    review = (CONTRACTS / 'final-review.md').read_text(encoding='utf-8')
    assert 'agent_type: subagents_dispatch_advisor' in review
    assert 'fork_turns: none' in review
    assert advisor['name'] == spec['agent_type']
    assert advisor['model'] == spec['model']
    assert advisor['model_reasoning_effort'] == spec['effort']
    assert 'sandbox_mode' not in advisor
    assert spec['mutation_authority'] == 'none'

def test_review_lifecycle_remains_fail_closed_and_artifact_bound():
    review = (CONTRACTS / 'final-review.md').read_text(encoding='utf-8')
    for phrase in ['review_artifact_id', 'review-artifact.py', 'ship', 'fix-first', 'rethink', 'INSUFFICIENT_EVIDENCE', 'Any deliverable mutation after review invalidates the old verdict']:
        assert phrase in review
    final_review = contract()['final_review']
    assert final_review['ship_verdict'] == 'ship'
    assert final_review['correction_verdicts'] == ['fix-first', 'rethink']
    assert final_review['unresolved_verdict'] == 'insufficient_evidence'

def test_sol_review_is_selective_outside_required_assurance():
    router = (CONTRACTS / 'routing.md').read_text(encoding='utf-8').lower()
    review = (CONTRACTS / 'final-review.md').read_text(encoding='utf-8').lower()
    assert 'final review' in router
    assert 'candidate' in router and 'independent second judgment' in router
    assert 'process history' in review
    assert 'not a trigger by itself' in review
ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT
ADVISOR = PLUGIN / 'agent-profiles' / 'subagents-dispatch-advisor.toml'
REVIEW = PLUGIN / 'contracts' / 'final-review.md'
SCHEMA = ROOT / 'evals' / 'behavioral-result.schema.json'

def test_advisor_can_fail_closed_on_missing_evidence():
    instructions = tomllib.loads(ADVISOR.read_text())['developer_instructions']
    assert 'INSUFFICIENT_EVIDENCE' in instructions
    assert 'missing dependency' in instructions

def test_review_keeps_insufficient_evidence_unresolved():
    review = REVIEW.read_text()
    assert 'INSUFFICIENT_EVIDENCE' in review
    assert 'Keep the candidate at review-pending' in review
    assert 'This is not completion' in review
    assert 'fresh review' in review

def test_behavioral_schema_records_insufficient_evidence():
    schema = json.loads(SCHEMA.read_text())
    verdicts = schema['properties']['runs']['items']['properties']['final_review_verdict']['enum']
    assert 'insufficient_evidence' in verdicts
ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / 'evals' / 'behavioral-result.schema.json'
SCORER = ROOT / 'scripts' / 'score-behavioral-evals.py'

def run(mode: str) -> dict:
    return {'workload_id': 'bounded-implementation', 'mode': mode, 'pair_id': 'final-review-metrics-1', 'repeat_index': 1, 'repo_revision': 'candidate-sha', 'workload_definition_hash': 'sha256:workload-fixture', 'main_session_route': 'gpt-5.6-sol/high', 'main_judgment_coverage': 'covered', 'dependency_kind': 'bounded_execution', 'execution_route': 'gpt-5.6-luna/max', 'permissions_fingerprint': 'workspace-write+default-approval', 'tool_surface_fingerprint': 'spawn-agent-v2+shell+git', 'acceptance_rubric_id': 'final-review-metrics-v1', 'success': True, 'decision': 'complete', 'agent_count': 1, 'peak_active_children': 1, 'ready_dependencies': 1, 'runtime_slot_waits': 0, 'roles': ['worker'], 'policy_violations': [], 'scope_violations': 0, 'wrong_edits': 0, 'regressions': 0, 'material_judgment_violations': 0, 'correction_turns': 0, 'reclassification_events': 0, 'execution_stall_events': 0, 'clean_same_lane_restarts': 0, 'unjustified_retry_calls': 0, 'same_failure_without_new_evidence': 0, 'judgment_uplift_calls': 0, 'solver_calls': 0, 'advisor_calls': 0, 'terra_calls': 0, 'redundant_sol_calls': 0, 'review_findings': 0, 'review_false_positives': 0, 'final_review_attempts': 0, 'review_artifact_verify_failures': 0, 'post_review_mutations': 0, 'consent_prompts': 0, 'evidence_established': 1, 'evidence_invalidated': 0, 'unjustified_repeated_commands': 0, 'unjustified_repeated_discovery': 0, 'duplicate_dependency_calls': 0}

def score_process(tmp_path: Path, runs: list[dict]) -> subprocess.CompletedProcess[str]:
    result_path = tmp_path / 'result.json'
    result_path.write_text(json.dumps({'schema_version': '4.0', 'suite': 'subagents-dispatch-live-behavior', 'runtime': {'codex_version': 'fixture', 'date': '2026-08-05'}, 'runs': runs}), encoding='utf-8')
    return subprocess.run([sys.executable, str(SCORER), str(result_path), '--json'], cwd=ROOT, text=True, capture_output=True, check=False)

def score(tmp_path: Path, runs: list[dict]) -> dict:
    result = score_process(tmp_path, runs)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)

def test_schema_accepts_complete_final_review_telemetry():
    schema = json.loads(SCHEMA.read_text())
    candidate = run('bounded_luna')
    candidate.update({'final_review_requirement': 'required', 'final_review_trigger_reasons': ['public_contract_change'], 'final_review_attempts': 1, 'final_review_verdict': 'ship', 'final_review_gate_satisfied': True, 'review_caught_material_issue': False})
    payload = {'schema_version': '4.0', 'suite': 'subagents-dispatch-live-behavior', 'runtime': {'codex_version': 'fixture', 'date': '2026-08-05'}, 'runs': [candidate]}
    jsonschema.Draft202012Validator(schema).validate(payload)

def test_scorer_reports_final_review_cost_and_artifact_deltas(tmp_path: Path):
    baseline = run('raw_prompt_luna')
    candidate = run('bounded_luna')
    candidate.update({'final_review_requirement': 'required', 'final_review_trigger_reasons': ['public_contract_change'], 'final_review_attempts': 2, 'final_review_verdict': 'ship', 'final_review_gate_satisfied': True, 'review_findings': 1, 'review_caught_material_issue': True, 'review_artifact_verify_failures': 1, 'post_review_mutations': 1})
    summary = score(tmp_path, [baseline, candidate])
    comparison = summary['pairs']['final-review-metrics-1']['comparison']
    assert comparison['metric_deltas']['final_review_attempts'] == 2
    assert comparison['metric_deltas']['review_artifact_verify_failures'] == 1
    assert comparison['metric_deltas']['post_review_mutations'] == 1
    assert comparison['metric_deltas']['review_findings'] == 1
    mode = summary['modes']['bounded_luna']
    assert mode['final_review_required_runs'] == 1
    assert mode['final_review_satisfied_runs'] == 1
    assert mode['final_review_unsatisfied_required_runs'] == 0
    assert mode['final_review_attempts'] == 2
    assert mode['final_review_yield'] == 0.5
    assert mode['review_artifact_verify_failures'] == 1
    assert mode['post_review_mutations'] == 1

def test_scorer_rejects_satisfied_gate_without_ship_verdict(tmp_path: Path):
    baseline = run('raw_prompt_luna')
    candidate = run('bounded_luna')
    candidate.update({'final_review_requirement': 'required', 'final_review_trigger_reasons': ['public_contract_change'], 'final_review_attempts': 1, 'final_review_verdict': 'fix-first', 'final_review_gate_satisfied': True})
    result = score_process(tmp_path, [baseline, candidate])
    assert result.returncode != 0
    assert 'without the ship verdict' in result.stderr

def test_scorer_rejects_required_review_without_trigger_reason(tmp_path: Path):
    baseline = run('raw_prompt_luna')
    candidate = run('bounded_luna')
    candidate.update({'final_review_requirement': 'required', 'final_review_trigger_reasons': [], 'final_review_attempts': 1, 'final_review_verdict': 'ship', 'final_review_gate_satisfied': True})
    result = score_process(tmp_path, [baseline, candidate])
    assert result.returncode != 0
    assert 'without a trigger reason' in result.stderr

def test_scorer_rejects_verdict_without_review_attempt(tmp_path: Path):
    baseline = run('raw_prompt_luna')
    candidate = run('bounded_luna')
    candidate['final_review_verdict'] = 'ship'
    result = score_process(tmp_path, [baseline, candidate])
    assert result.returncode != 0
    assert 'without a review attempt' in result.stderr

def test_scorer_keeps_missing_final_review_telemetry_explicitly_empty(tmp_path: Path):
    baseline = run('raw_prompt_luna')
    candidate = run('bounded_luna')
    for item in [baseline, candidate]:
        for field in ['final_review_attempts', 'review_artifact_verify_failures', 'post_review_mutations']:
            item.pop(field)
    summary = score(tmp_path, [baseline, candidate])
    comparison = summary['pairs']['final-review-metrics-1']['comparison']
    assert comparison['metric_deltas']['final_review_attempts'] is None
    assert comparison['metric_deltas']['review_artifact_verify_failures'] is None
    assert comparison['metric_deltas']['post_review_mutations'] is None
    assert summary['modes']['bounded_luna']['final_review_attempts'] is None
    assert summary['modes']['bounded_luna']['final_review_yield'] is None
ROOT = Path(__file__).resolve().parents[1]
WORKLOADS = ROOT / 'evals' / 'behavioral-workloads.json'
RESULT_SCHEMA = ROOT / 'evals' / 'behavioral-result.schema.json'

def cases() -> dict[str, dict]:
    payload = json.loads(WORKLOADS.read_text(encoding='utf-8'))
    assert payload['schema_version'] == '4.0'
    return {item['id']: item for item in payload['workloads']}

def test_behavioral_suite_covers_required_final_review_and_process_history_negative_control():
    by_id = cases()
    public = by_id['public-contract-final-review-required']['expected']
    assert public['review_requirement'] == 'required'
    assert public['review_reason'] == 'public_contract_change'
    assert public['fresh_sol_required'] is True
    assert public['ship_required'] is True
    negative = by_id['process-history-does-not-force-review']['expected']
    assert negative['review_requirement'] == 'not_required'

def test_behavioral_suite_covers_verification_gap_and_sol_main_independence():
    by_id = cases()
    gap = by_id['verification-gap-final-review-required']['expected']
    sol_main = by_id['sol-main-still-needs-independent-review']['expected']
    assert gap['review_requirement'] == 'required'
    assert gap['review_reason'] == 'verification_gap'
    assert gap['fresh_sol_required'] is True
    assert sol_main['main_judgment_coverage'] == 'covered'
    assert sol_main['fresh_sol_required'] is True
    assert sol_main['independence_required'] is True

def test_behavioral_suite_covers_verdict_invalidation_lifecycle():
    by_id = cases()
    fix_first = by_id['fix-first-invalidates-old-review']['expected']
    mutation = by_id['post-review-mutation-invalidates-ship']['expected']
    assert fix_first['old_verdict_valid'] is False
    assert fix_first['fresh_rereview_required'] is True
    assert mutation['old_verdict_valid'] is False
    assert mutation['artifact_verify_must_fail'] is True
    assert mutation['fresh_rereview_required'] is True

def test_behavioral_result_schema_supports_final_review_metrics():
    schema = json.loads(RESULT_SCHEMA.read_text(encoding='utf-8'))
    jsonschema.Draft202012Validator.check_schema(schema)
    props = schema['properties']['runs']['items']['properties']
    for field in ['final_review_requirement', 'final_review_trigger_reasons', 'final_review_attempts', 'final_review_verdict', 'final_review_gate_satisfied', 'review_artifact_verify_failures', 'post_review_mutations']:
        assert field in props
    assert 'adaptive_routing_v4_final_review' in props['mode']['enum']
    assert props['final_review_requirement']['enum'] == [None, 'not_required', 'required']
    assert props['final_review_verdict']['enum'] == [None, 'ship', 'fix-first', 'rethink', 'insufficient_evidence', 'incomplete', 'declined']
ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'review-artifact.py'

def _review_artifact__git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(['git', '-C', str(repo), *args], text=True, capture_output=True, check=True)

def init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / 'repo'
    repo.mkdir()
    _review_artifact__git(repo, 'init')
    _review_artifact__git(repo, 'config', 'user.email', 'subagents-dispatch@example.invalid')
    _review_artifact__git(repo, 'config', 'user.name', 'subagents-dispatch Test')
    (repo / '.gitignore').write_text('ignored-cache/\n', encoding='utf-8')
    (repo / 'app.py').write_text('VALUE = 1\n', encoding='utf-8')
    _review_artifact__git(repo, 'add', '.gitignore', 'app.py')
    _review_artifact__git(repo, 'commit', '-m', 'test: base')
    return repo

def init_repo_with_submodule(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / 'submodule-source'
    source.mkdir()
    _review_artifact__git(source, 'init')
    _review_artifact__git(source, 'config', 'user.email', 'subagents-dispatch@example.invalid')
    _review_artifact__git(source, 'config', 'user.name', 'subagents-dispatch Test')
    (source / 'dep.txt').write_text('VALUE = 1\n', encoding='utf-8')
    _review_artifact__git(source, 'add', 'dep.txt')
    _review_artifact__git(source, 'commit', '-m', 'test: submodule base')
    repo = init_repo(tmp_path)
    _review_artifact__git(repo, '-c', 'protocol.file.allow=always', 'submodule', 'add', str(source), 'vendor/dep')
    _review_artifact__git(repo, 'commit', '-m', 'test: add submodule')
    return (repo, repo / 'vendor' / 'dep')

def artifact(repo: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), '--repo', str(repo), *extra], text=True, capture_output=True, check=False)

def artifact_payload(repo: Path) -> dict:
    result = artifact(repo)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload['schema_version'] == 1
    assert payload['review_artifact_id'].startswith('sha256:')
    return payload

def _review_artifact__artifact_id(repo: Path) -> str:
    return artifact_payload(repo)['review_artifact_id']

def test_review_artifact_is_stable_and_verify_accepts_exact_state(tmp_path: Path):
    repo = init_repo(tmp_path)
    first = _review_artifact__artifact_id(repo)
    second = _review_artifact__artifact_id(repo)
    assert first == second
    verified = artifact(repo, '--verify', first)
    assert verified.returncode == 0
    assert json.loads(verified.stdout)['review_artifact_id'] == first

def test_tracked_mutation_invalidates_review_artifact(tmp_path: Path):
    repo = init_repo(tmp_path)
    before = _review_artifact__artifact_id(repo)
    (repo / 'app.py').write_text('VALUE = 2\n', encoding='utf-8')
    after = _review_artifact__artifact_id(repo)
    assert after != before
    verified = artifact(repo, '--verify', before)
    assert verified.returncode == 2
    assert 'review artifact changed' in verified.stderr

def test_staged_mutation_is_bound_without_requiring_commit(tmp_path: Path):
    repo = init_repo(tmp_path)
    before = _review_artifact__artifact_id(repo)
    (repo / 'app.py').write_text('VALUE = 3\n', encoding='utf-8')
    _review_artifact__git(repo, 'add', 'app.py')
    after = _review_artifact__artifact_id(repo)
    assert after != before

@pytest.mark.parametrize(('flag', 'expected_message'), [('--assume-unchanged', 'uses assume-unchanged'), ('--skip-worktree', 'uses skip-worktree')])
def test_hidden_index_flags_cannot_mask_tracked_mutation(tmp_path: Path, flag: str, expected_message: str):
    repo = init_repo(tmp_path)
    clean = _review_artifact__artifact_id(repo)
    _review_artifact__git(repo, 'update-index', flag, 'app.py')
    (repo / 'app.py').write_text("VALUE = 'hidden'\n", encoding='utf-8')
    hidden = artifact(repo)
    assert hidden.returncode != 0
    assert expected_message in hidden.stderr
    verified = artifact(repo, '--verify', clean)
    assert verified.returncode != 0
    assert expected_message in verified.stderr

def test_untracked_deliverable_is_bound_and_content_changes_invalidate(tmp_path: Path):
    repo = init_repo(tmp_path)
    clean = _review_artifact__artifact_id(repo)
    untracked = repo / 'new_module.py'
    untracked.write_text("FLAG = 'a'\n", encoding='utf-8')
    first = _review_artifact__artifact_id(repo)
    assert first != clean
    untracked.write_text("FLAG = 'b'\n", encoding='utf-8')
    second = _review_artifact__artifact_id(repo)
    assert second != first
    payload = artifact_payload(repo)
    assert payload['untracked'][0]['path'] == 'new_module.py'
    assert payload['untracked'][0]['kind'] == 'file'
    assert payload['untracked'][0]['mode'] == '100644'

@pytest.mark.skipif(os.name == 'nt', reason='Windows does not expose POSIX executable mode semantics')
def test_untracked_executable_mode_is_part_of_identity(tmp_path: Path):
    repo = init_repo(tmp_path)
    tool = repo / 'tool.sh'
    tool.write_text('#!/bin/sh\necho ok\n', encoding='utf-8')
    tool.chmod(493)
    executable = artifact_payload(repo)
    entry = next((item for item in executable['untracked'] if item['path'] == 'tool.sh'))
    assert entry['mode'] == '100755'
    tool.chmod(420)
    non_executable = artifact_payload(repo)
    assert non_executable['review_artifact_id'] != executable['review_artifact_id']
    entry = next((item for item in non_executable['untracked'] if item['path'] == 'tool.sh'))
    assert entry['mode'] == '100644'

def test_untracked_symlink_target_is_bound_without_following_target(tmp_path: Path):
    repo = init_repo(tmp_path)
    link = repo / 'current-config'
    os.symlink('config-a', link)
    first = artifact_payload(repo)
    entry = next((item for item in first['untracked'] if item['path'] == 'current-config'))
    assert entry['kind'] == 'symlink'
    assert entry['mode'] == '120000'
    link.unlink()
    os.symlink('config-b', link)
    second = artifact_payload(repo)
    assert second['review_artifact_id'] != first['review_artifact_id']

def test_ignored_cache_artifacts_do_not_change_source_deliverable_identity(tmp_path: Path):
    repo = init_repo(tmp_path)
    before = _review_artifact__artifact_id(repo)
    cache = repo / 'ignored-cache'
    cache.mkdir()
    (cache / 'result.bin').write_bytes(b'not a source deliverable')
    after = _review_artifact__artifact_id(repo)
    assert after == before

def test_head_change_invalidates_artifact_even_with_clean_worktree(tmp_path: Path):
    repo = init_repo(tmp_path)
    before = _review_artifact__artifact_id(repo)
    (repo / 'app.py').write_text('VALUE = 4\n', encoding='utf-8')
    _review_artifact__git(repo, 'add', 'app.py')
    _review_artifact__git(repo, 'commit', '-m', 'test: change head')
    after = _review_artifact__artifact_id(repo)
    assert after != before

def test_clean_submodule_is_bindable_but_dirty_or_mismatched_checkout_fails_closed(tmp_path: Path):
    repo, submodule = init_repo_with_submodule(tmp_path)
    clean = _review_artifact__artifact_id(repo)
    assert _review_artifact__artifact_id(repo) == clean
    (submodule / 'dep.txt').write_text('VALUE = 2\n', encoding='utf-8')
    dirty = artifact(repo)
    assert dirty.returncode != 0
    assert 'dirty submodule cannot be bound exactly' in dirty.stderr
    verified = artifact(repo, '--verify', clean)
    assert verified.returncode != 0
    assert 'dirty submodule cannot be bound exactly' in verified.stderr
    _review_artifact__git(submodule, 'reset', '--hard', 'HEAD')
    _review_artifact__git(submodule, 'config', 'user.email', 'subagents-dispatch@example.invalid')
    _review_artifact__git(submodule, 'config', 'user.name', 'subagents-dispatch Test')
    (submodule / 'dep.txt').write_text('VALUE = 3\n', encoding='utf-8')
    _review_artifact__git(submodule, 'add', 'dep.txt')
    _review_artifact__git(submodule, 'commit', '-m', 'test: local submodule commit')
    mismatched = artifact(repo)
    assert mismatched.returncode != 0
    assert 'submodule checkout does not match the indexed gitlink' in mismatched.stderr

@pytest.mark.parametrize(('flag', 'expected_message'), [('--assume-unchanged', 'uses assume-unchanged'), ('--skip-worktree', 'uses skip-worktree')])
def test_submodule_hidden_index_flags_fail_closed(tmp_path: Path, flag: str, expected_message: str):
    repo, submodule = init_repo_with_submodule(tmp_path)
    _review_artifact__git(submodule, 'update-index', flag, 'dep.txt')
    (submodule / 'dep.txt').write_text("VALUE = 'hidden'\n", encoding='utf-8')
    hidden = artifact(repo)
    assert hidden.returncode != 0
    assert expected_message in hidden.stderr

def test_unborn_repository_is_supported(tmp_path: Path):
    repo = tmp_path / 'unborn'
    repo.mkdir()
    _review_artifact__git(repo, 'init')
    (repo / 'staged.txt').write_text('staged\n', encoding='utf-8')
    (repo / 'untracked.txt').write_text('untracked\n', encoding='utf-8')
    _review_artifact__git(repo, 'add', 'staged.txt')
    payload = artifact_payload(repo)
    assert payload['head'] == 'UNBORN'
    assert [item['path'] for item in payload['untracked']] == ['untracked.txt']
ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'review-artifact.py'

def _review_artifact_unborn__git(repo: Path, *args: str) -> None:
    subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True)

def _review_artifact_unborn__artifact_id(repo: Path) -> str:
    result = subprocess.run([sys.executable, str(SCRIPT), '--repo', str(repo)], text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)['review_artifact_id']

def test_unborn_staged_file_then_unstaged_edit_changes_artifact(tmp_path: Path):
    repo = tmp_path / 'repo'
    repo.mkdir()
    _review_artifact_unborn__git(repo, 'init')
    tracked = repo / 'tracked.txt'
    tracked.write_text('staged-version\n', encoding='utf-8')
    _review_artifact_unborn__git(repo, 'add', 'tracked.txt')
    staged_id = _review_artifact_unborn__artifact_id(repo)
    tracked.write_text('working-tree-version\n', encoding='utf-8')
    working_id = _review_artifact_unborn__artifact_id(repo)
    assert working_id != staged_id
ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / 'scripts' / 'dispatch_state.py'

def load_module():
    spec = importlib.util.spec_from_file_location('dispatch_state_verification_rework', MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def materialized_worker():
    return {'unit_id': 'U1', 'attempt': 1, 'agent_id': 'agent-1', 'role': 'worker', 'model_lane': 'Luna Max'}

def followup_event():
    return {'ref': 'followup:U1:A1:F1', 'kind': 'followup', 'unit_id': 'U1', 'attempt': 1, 'agent_id': 'agent-1', 'activity': 'execute'}

def verification_gap_event(ref: str='verification-gap:pagination-test'):
    return {'ref': ref, 'kind': 'verification_gap', 'verification_artifact_id': 'sha256:' + 'a' * 64, 'oracle_ref': 'pytest:tests/test_api.py::test_pagination'}

def test_main_verification_gap_can_bind_real_semantic_rework_without_review_round():
    module = load_module()
    events = [followup_event(), verification_gap_event(), {'ref': 'rework:U1:verification-1', 'kind': 'semantic_rework', 'unit_id': 'U1', 'attempt': 1, 'agent_id': 'agent-1', 'verification_gap_ref': 'verification-gap:pagination-test'}]
    summary = module.account_receipt(events, materialized_units=[materialized_worker()])
    assert summary['semantic_reworks'] == 1
    assert summary['review'] == {'rounds': 0, 'reworks': 1, 'verdict': None}
    assert '验收: 未触发独立复核 · 返工1次' in module.format_receipt(summary, locale='zh')
    assert 'Review: independent review not triggered · rework×1' in module.format_receipt(summary, locale='en')

def test_repeated_verification_gap_observation_is_idempotent():
    module = load_module()
    gap = verification_gap_event()
    events = [followup_event(), gap, gap, {'ref': 'rework:U1:verification-1', 'kind': 'semantic_rework', 'unit_id': 'U1', 'attempt': 1, 'agent_id': 'agent-1', 'verification_gap_ref': gap['ref']}]
    summary = module.account_receipt(events, materialized_units=[materialized_worker()])
    assert summary['semantic_reworks'] == 1
    assert summary['review']['reworks'] == 1

def test_verification_gap_requires_exact_artifact_and_oracle():
    module = load_module()
    for event in [{'ref': 'gap:missing-artifact', 'kind': 'verification_gap', 'oracle_ref': 'pytest:test'}, {'ref': 'gap:bad-artifact', 'kind': 'verification_gap', 'verification_artifact_id': 'candidate', 'oracle_ref': 'pytest:test'}, {'ref': 'gap:missing-oracle', 'kind': 'verification_gap', 'verification_artifact_id': 'sha256:' + 'b' * 64}]:
        with pytest.raises(module.ReceiptAccountingError, match='exact candidate artifact and oracle_ref'):
            module.account_receipt([event], materialized_units=[materialized_worker()])

def test_semantic_rework_rejects_missing_or_multiple_gap_sources():
    module = load_module()
    artifact_id = 'sha256:' + 'c' * 64
    gap = {'ref': 'verification-gap:one', 'kind': 'verification_gap', 'verification_artifact_id': artifact_id, 'oracle_ref': 'pytest:test_one'}
    unbound = {'ref': 'rework:unbound', 'kind': 'semantic_rework', 'unit_id': 'U1', 'attempt': 1, 'agent_id': 'agent-1'}
    with pytest.raises(module.ReceiptAccountingError, match='exactly one bound review or verification gap'):
        module.account_receipt([followup_event(), gap, unbound], materialized_units=[materialized_worker()])
    advisor = {'unit_id': 'U2', 'attempt': 1, 'agent_id': 'advisor-1', 'role': 'advisor', 'model_lane': 'Sol High'}
    both = [followup_event(), gap, {'ref': 'reviewer:U2:A1', 'kind': 'reviewer_attempt', 'unit_id': 'U2', 'attempt': 1, 'agent_id': 'advisor-1', 'activity': 'review', 'review_artifact_id': artifact_id}, {'ref': 'review:U2:R1', 'kind': 'review_round', 'unit_id': 'U2', 'attempt': 1, 'agent_id': 'advisor-1', 'verdict': 'rework_required', 'review_artifact_id': artifact_id}, {'ref': 'rework:both', 'kind': 'semantic_rework', 'unit_id': 'U1', 'attempt': 1, 'agent_id': 'agent-1', 'review_artifact_id': artifact_id, 'verification_gap_ref': 'verification-gap:one'}]
    with pytest.raises(module.ReceiptAccountingError, match='exactly one bound review or verification gap'):
        module.account_receipt(both, materialized_units=[materialized_worker(), advisor])
