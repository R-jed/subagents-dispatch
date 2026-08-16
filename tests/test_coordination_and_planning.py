from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import importlib.util
import re
import tomllib
import jsonschema
import yaml
ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT
POLICY = PLUGIN / 'contracts' / 'policy.json'
VERIFIER = PLUGIN / 'scripts' / 'runtime-evidence.py'

def run_main(model: str | None=None, effort: str | None=None) -> dict:
    native = {}
    if model is not None:
        native['model'] = model
    if effort is not None:
        native['effort'] = effort
    payload = {'subject': 'main_session', 'native': native or None}
    result = subprocess.run([sys.executable, str(VERIFIER)], input=json.dumps(payload), text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)

def test_policy_owns_capability_dedup_reference_route_and_aliases():
    policy = json.loads(POLICY.read_text())
    dedup = policy['capability_dedup']
    role = dedup['reference_role']
    reference = policy['roles'][role]
    order = dedup['reasoning_effort_order']
    assert policy['schema_version'] == 8
    assert role == 'solver'
    assert reference['model'] == 'gpt-5.6-sol'
    assert reference['effort'] == 'high'
    assert dedup['model_aliases'] == ['gpt-5.6']
    assert order.index('medium') < order.index('high') < order.index('xhigh') < order.index('max')

def test_capability_dedup_requires_reference_model_or_declared_alias_and_sufficient_effort():
    for model in ['gpt-5.6-sol', 'gpt-5.6']:
        assert run_main(model, 'high')['main_judgment_coverage'] == 'covered'
        assert run_main(model, 'xhigh')['main_judgment_coverage'] == 'covered'
        assert run_main(model, 'max')['main_judgment_coverage'] == 'covered'
        assert run_main(model, 'medium')['main_judgment_coverage'] == 'uncovered'
    assert run_main('gpt-5.6-sol', 'low')['main_judgment_coverage'] == 'uncovered'
    assert run_main('gpt-5.6-luna', 'max')['main_judgment_coverage'] == 'uncovered'

def test_unknown_effort_on_matching_model_does_not_suppress_sol_uplift():
    data = run_main('gpt-5.6-sol', 'future-effort')
    assert data['main_judgment_coverage'] == 'unknown'
    assert data['coverage_reference_model'] == 'gpt-5.6-sol'
    assert data['coverage_reference_model_aliases'] == ['gpt-5.6']
    assert data['coverage_reference_effort'] == 'high'

def test_partial_main_route_remains_unknown():
    assert run_main('gpt-5.6-sol', None)['main_judgment_coverage'] == 'unknown'
CONTRACTS = PLUGIN / 'contracts'
ROUTER = CONTRACTS / 'routing.md'
GUARDRAILS = CONTRACTS / 'guardrails.md'
ROUTING_CASES = ROOT / 'evals' / 'routing-cases.json'

def policy() -> dict:
    return json.loads(POLICY.read_text())

def routing_cases() -> dict[str, dict]:
    payload = json.loads(ROUTING_CASES.read_text())
    assert payload['schema_version'] == '2.0'
    return {case['id']: case for case in payload['cases']}

def test_machine_contract_keeps_depth_and_semantic_writer_coordination():
    assert policy()['delegation'] == {'max_depth': 1, 'fork_turns': 'none'}
    assert policy()['write_coordination'] == {'mode': 'single_writer', 'scope': 'canonical_workspace'}

def test_static_cases_cover_adaptive_fanout_and_material_compute_consent():
    cases = routing_cases()
    parallel = cases['three-independent-readers-can-fanout']
    assert parallel['expected']['action'] == 'delegate'
    assert len(parallel['expected']['nodes']) == 3
    assert all((node['agent_type'] == 'subagents_dispatch_reader' for node in parallel['expected']['nodes']))
    consent = cases['material-compute-expansion-needs-consent']
    assert consent['expected']['action'] == 'ask_consent'
    assert consent['expected']['consent_reason'] == 'material_compute_expansion'

def test_router_and_guardrails_own_adaptive_scheduling_and_writer_safety():
    router = ROUTER.read_text().lower()
    guardrails = GUARDRAILS.read_text().lower()
    for concept in ['ready frontier', 'progressive fan-out', 'native codex capacity']:
        assert concept in router
    for concept in ['one writer per canonical checkout', 'filesystem isolation', 'semantic independence', 'child count by itself is not a consent trigger', 'delegation depth is one']:
        assert concept in guardrails

def test_installer_lock_is_a_local_profile_lifecycle_mechanism():
    installer = (PLUGIN / 'scripts' / 'install-agents.py').read_text().lower()
    assert 'lock_name = ".subagents-dispatch-agents.lock"' in installer
    assert 'def managed_lock(' in installer
    assert 'def installation_locks(' in installer
    assert 'def installer_lock(' not in installer
    assert 'lock_file(fd)' in installer
TEAM_PLAN = CONTRACTS / 'team-plan.md'
COORDINATION_CASES = ROOT / 'evals' / 'coordination-cases.json'

def cases() -> dict[str, dict]:
    payload = json.loads(COORDINATION_CASES.read_text())
    assert payload['schema_version'] == '1.0'
    assert payload['suite'] == 'subagents-dispatch-coordination-contract'
    result = {case['id']: case for case in payload['cases']}
    assert len(result) == len(payload['cases'])
    return result

def test_upstream_workflow_truth_remains_authoritative():
    router = ROUTER.read_text().lower()
    assert 'upstream workflow' in router
    assert 'task truth' in router
    assert 'competing' in router
    expected = cases()['upstream-workflow-remains-authoritative']['expected']
    assert expected['preserve_upstream_workflow'] is True
    assert set(expected['delegate_may_assign']) == {'owner', 'role', 'concurrency', 'write_isolation', 'integration_timing'}
    assert {'goal', 'decomposition', 'stage_order', 'dependencies', 'required_outputs', 'business_acceptance', 'quality_gates'} <= set(expected['delegate_must_not_redefine'])

def test_semantic_coverage_survives_decomposition_without_fixed_taxonomy():
    router = ROUTER.read_text().lower()
    team_plan = TEAM_PLAN.read_text().lower()
    assert 'preserve semantic coverage through decomposition' in router
    assert 'material obligation' in router
    assert 'fixed domain taxonomy' in router
    assert 'structurally valid teamplan can still be semantically incomplete' in team_plan
    assert "do not relabel main's planning defect as a semantic blocker" in router
    covered = cases()['decomposition-preserves-material-obligations']['expected']
    assert covered == {'semantic_coverage_required': True, 'every_material_obligation_has_owner': True, 'main_owned_obligation_allowed': True, 'fixed_obligation_taxonomy_required': False}
    missing = cases()['structural-validity-does-not-prove-semantic-coverage']['expected']
    assert missing == {'structural_plan_may_validate': True, 'semantic_coverage_complete': False, 'candidate_ready': False, 'repair_decomposition_in_main': True, 'contract_blocker': False}
    contract = cases()['coverage-impossible-because-task-truth-missing-is-contract']['expected']
    assert contract == {'semantic_coverage_complete': False, 'repair_decomposition_alone_sufficient': False, 'blocker': 'contract'}

def test_cross_unit_seam_ownership_does_not_force_decorative_child():
    router = ROUTER.read_text().lower()
    team_plan = TEAM_PLAN.read_text().lower()
    assert 'main owns the seam by default' in router
    assert 'do not create a decorative child' in router
    assert 'integration order is ordering truth only' in team_plan
    expected = cases()['cross-unit-seam-can-remain-main-owned']['expected']
    assert expected == {'seam_requires_owner': True, 'main_may_own_seam': True, 'automatic_extra_child': False, 'integration_order_alone_is_sufficient': False}

def test_downstream_review_waits_for_actual_integrated_deliverable():
    router = ROUTER.read_text().lower()
    team_plan = TEAM_PLAN.read_text().lower()
    assert 'not semantically ready merely because all named predecessor units are accepted' in router
    assert 'not semantically ready merely because all predecessor units are accepted' in team_plan
    expected = cases()['downstream-review-waits-for-integrated-deliverable']['expected']
    assert expected == {'structurally_ready': True, 'semantically_ready': False, 'dispatch_review_now': False, 'main_must_materialize_and_verify_integration_first': True}

def test_phase_transition_recompiles_responsibility_authority_and_trust():
    router = ROUTER.read_text().lower()
    guardrails = GUARDRAILS.read_text().lower()
    team_plan = TEAM_PLAN.read_text().lower()
    assert 'recompile at material phase or authority transitions' in router
    assert 'phase readiness does not grant later authority' in guardrails
    assert 'material phase or authority transition' in team_plan
    assert 'the whole earlier artifact does not automatically become trusted task truth' in router
    assert 'embedded instructions' in router
    assert 'remain data' in router
    expected = cases()['phase-transition-recompiles-without-inheriting-authority']['expected']
    assert expected == {'accepted_prior_truth_promoted': True, 'whole_prior_artifact_trusted': False, 'embedded_untrusted_content_remains_data': True, 'fresh_responsibility_compilation': True, 'repurpose_old_unit_when_goal_or_output_changes': False, 'accepted_evidence_reusable_if_fresh': True, 'later_authority_inherited_from_readiness': False, 'authority_reassessed': True}

def test_parallel_writers_require_semantic_independence():
    router = ROUTER.read_text().lower()
    guardrails = GUARDRAILS.read_text().lower()
    team_plan = TEAM_PLAN.read_text().lower()
    assert 'semantic independence' in router
    assert 'semantic independence' in guardrails
    assert 'different files' in team_plan
    expected = cases()['isolated-files-shared-api-are-not-independent']['expected']
    assert expected == {'parallel_writes_allowed': False, 'filesystem_isolation_sufficient': False, 'reason': 'semantic_dependency', 'required_resolution': 'explicit_dependency_or_integration_order'}

def test_intent_and_mutation_authority_stay_separate():
    router = ROUTER.read_text().lower()
    guardrails = GUARDRAILS.read_text().lower()
    assert 'intent: inspect | implement | verify | review' in router
    assert 'mutation authority: none | declared-output-only | bounded-source-write' in router
    assert 'filesystem permission is capability, not authorization' in guardrails
    verify_case = cases()['verify-child-cannot-fix-source']['expected']
    assert verify_case == {'intent': 'verify', 'mutation_authority': 'none', 'source_write_allowed': False, 'on_required_source_change': 'return_to_main_for_authority'}
    output_case = cases()['declared-output-does-not-grant-source-write']['expected']
    assert output_case['mutation_authority'] == 'declared-output-only'
    assert output_case['source_write_allowed'] is False
    assert output_case['declared_output_write_allowed'] is True

def test_execution_dependency_and_integration_order_are_distinct():
    team_plan = TEAM_PLAN.read_text().lower()
    assert 'dependency' in team_plan
    assert 'integration_order' in team_plan
    assert 'integration_owner' in team_plan
    ordered = cases()['independent-execution-ordered-integration']['expected']
    assert ordered['execution_can_overlap'] is True
    assert ordered['consumer_integration_after'] == ['producer']
    assert ordered['main_is_integration_owner'] is True
    assert ordered['integrate_by_completion_time'] is False
    blocked = cases()['unresolved-semantics-cannot-hide-behind-integration-order']['expected']
    assert blocked['ready_to_execute'] is False
    assert blocked['integration_after_is_sufficient'] is False
    assert blocked['reason'] == 'semantic_truth_not_ready'

def test_requested_accepted_and_observed_truth_layers_are_distinct():
    guardrails = GUARDRAILS.read_text().lower()
    for concept in ['requested', 'accepted', 'observed']:
        assert concept in guardrails
    expected = cases()['accepted-route-is-not-runtime-observation']['expected']
    assert expected == {'requested_status': 'declared', 'accepted_status': 'matched', 'observed_status': 'not_observed', 'may_claim_observed_route': False}
DISPATCH_SKILL = ROOT / 'skills' / 'dispatch' / 'SKILL.md'
RECOVERY = ROOT / 'contracts' / 'recovery.md'
INTERACTION = ROOT / 'contracts' / 'interaction.md'
RECEIPT = ROOT / 'contracts' / 'receipt.md'
CASES = ROOT / 'evals' / 'interaction-cases.json'
WORKLOADS = ROOT / 'evals' / 'behavioral-workloads.json'

def by_id(path: Path, key: str) -> dict[str, dict]:
    payload = json.loads(path.read_text(encoding='utf-8'))
    return {item['id']: item for item in payload[key]}

def test_project_child_spawn_requires_explicit_fresh_context_before_tool_call():
    skill = DISPATCH_SKILL.read_text(encoding='utf-8')
    guardrails = GUARDRAILS.read_text(encoding='utf-8')
    assert '../../contracts/guardrails.md' in skill
    for phrase in ['new project child + exact project agent_type -> fork_turns: none', 'Full-history (`all`) and omitted `fork_turns` are forbidden for project children', 'correct it before invoking the Host']:
        assert phrase in guardrails
    expected = by_id(CASES, 'cases')['custom-role-spawn-requires-fork-turns-none']['expected']
    assert expected == {'spawn_call_valid': False, 'required_fork_turns': 'none', 'full_history_allowed': False, 'omitted_fork_turns_allowed': False}

def test_dispatch_spawn_binds_exact_policy_agent_type_and_forbids_substitution():
    skill = DISPATCH_SKILL.read_text(encoding='utf-8')
    policy = json.loads(POLICY.read_text(encoding='utf-8'))
    for phrase in ['roles.<semantic-role>.agent_type', 'Host-discovered role names', 'built-in roles', 'unrelated installed custom Agents', 'legacy aliases', 'model-equivalent profiles', 'are never substitutions', 'A successful spawn of any different role is a routing failure']:
        assert phrase in skill
    agent_types = [spec['agent_type'] for spec in policy['roles'].values()]
    assert len(agent_types) == 5
    assert len(set(agent_types)) == 5
    assert all((agent_type.startswith('subagents_dispatch_') for agent_type in agent_types))
    expected = by_id(WORKLOADS, 'workloads')['dispatch-custom-role-fresh-context-spawn']['expected']
    assert expected['first_spawn_agent_type'] == policy['roles']['reader']['agent_type']

def test_pre_child_spawn_rejection_does_not_create_attempt_or_receipt_retry():
    recovery = RECOVERY.read_text(encoding='utf-8')
    receipt = RECEIPT.read_text(encoding='utf-8')
    guardrails = GUARDRAILS.read_text(encoding='utf-8')
    for phrase in ['an Agent attempt begins only after the Host accepts the spawn and returns an inspectable child identity', 'no attempt-budget consumption', 'no receipt retry increment', 'A pre-attempt spawn rejection is not `same_role_retry`']:
        assert phrase in recovery
    assert 'pre-attempt spawn rejection' in guardrails
    assert 'does not consume the two-attempt recovery budget' in guardrails
    assert 'Recovery retry increments only when a confirmed materialized Agent attempt is replaced' in receipt
    assert 'A pre-child spawn rejection is never a retry' in receipt
    expected = by_id(CASES, 'cases')['pre-child-spawn-rejection-does-not-count-as-retry']['expected']
    assert expected == {'materialized_agent_attempts': 1, 'retry_count': 0, 'receipt_retry': 'no_retry', 'consume_attempt_budget_on_rejection': False}

def test_live_host_workload_freezes_the_real_spawn_regression():
    workload = by_id(WORKLOADS, 'workloads')['dispatch-custom-role-fresh-context-spawn']
    expected = workload['expected']
    assert workload['category'] == 'interaction_spawn_context'
    assert expected['first_spawn_agent_type'] == 'subagents_dispatch_reader'
    assert expected['first_spawn_fork_turns'] == 'none'
    assert expected['full_history_spawn_calls'] == 0
    assert expected['omitted_fork_turns_calls'] == 0
    assert expected['pre_child_rejections_count_as_agent_attempt'] is False
    assert expected['pre_child_rejections_increment_receipt_retry'] is False
TAKEOVER = ROOT / 'skills' / 'takeover' / 'SKILL.md'

def test_takeover_maps_interrupted_v2_writer_to_bounded_same_child_settlement():
    text = TAKEOVER.read_text(encoding='utf-8')
    for phrase in ['If the available stop control only interrupts the child and the Host reports `INTERRUPTED`', 'use one bounded settlement-only resume of the exact interrupted child', 'exact-child `followup_task`', 'same unit id, task id, attempt number, native child identity, delegated role, authority, and writer ownership', 'Do not spawn a replacement, create a retry, reroute, or widen authority', 'Main remains read-only while that settlement turn is active', 'completed, errored, shutdown, or closed', '`RUNNING`, `INTERRUPTED`, `UNKNOWN`, and `notFound` remain insufficient']:
        assert phrase in text

def test_settlement_resume_reuses_existing_recovery_lifecycle_without_new_work_accounting():
    takeover = TAKEOVER.read_text(encoding='utf-8')
    recovery = RECOVERY.read_text(encoding='utf-8')
    receipt = RECEIPT.read_text(encoding='utf-8')
    assert 'A settlement-only same-child resume is lifecycle settlement' in takeover
    assert 'must not increment Agent-attempt, retry, focused-follow-up, semantic-rework, or Dispatch-pass accounting' in takeover
    assert 'RUNNING -> INTERRUPTED -> RUNNING' in recovery
    assert 'Resuming keeps the same unit, task, attempt, Agent, role, responsibility, and authority' in recovery
    assert 'It creates no child, retry, focused follow-up, work pass, or semantic rework' in recovery
    assert 'resuming an INTERRUPTED child in the same attempt' in receipt

def test_takeover_still_fails_closed_when_terminal_settlement_cannot_be_proven():
    text = TAKEOVER.read_text(encoding='utf-8')
    assert 'transfer ownership only if the exact expected child is proven non-active' in text
    assert 'keep takeover pending and report the capability limitation instead of simulating success' in text
SCRIPTS = PLUGIN / 'scripts'
SCRIPT = SCRIPTS / 'validate_team_plan.py'

def load_team_plan_validator(module_name: str):
    scripts_dir = str(SCRIPTS)
    sys.path.insert(0, scripts_dir)
    try:
        spec = importlib.util.spec_from_file_location(module_name, SCRIPT)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts_dir)
VALIDATOR = load_team_plan_validator('subagents_dispatch_team_plan')

def plan():
    return {'schema_version': '1.0', 'revision': 1, 'supersedes_revision': None, 'planning_source': 'ad_hoc', 'source_refs': [], 'root_goal': 'deliver the verified requested result', 'units': [{'unit_id': 'U1', 'role': 'reader', 'goal': 'trace contract', 'output': 'evidence', 'depends_on': [], 'ownership': {'write': [], 'forbidden': []}, 'done_when': 'contract evidenced'}, {'unit_id': 'U2', 'role': 'worker', 'goal': 'implement change', 'output': 'source change', 'depends_on': ['U1'], 'ownership': {'write': ['src/example.py'], 'forbidden': []}, 'done_when': 'acceptance passes'}], 'integration_owner': 'main', 'integration_order': ['U1', 'U2'], 'final_verification': 'Main verifies the combined artifact', 'revision_reason': 'initial'}

def validate(payload):
    return VALIDATOR.validate_team_plan_payload(payload)

def test_validator_derives_role_and_read_only_sets_from_policy_contract():
    policy = json.loads(POLICY.read_text())
    assert VALIDATOR.ROLES == set(policy['roles'])
    assert VALIDATOR.READ_ONLY_ROLES == {role for role, spec in policy['roles'].items() if spec['mutation_authority'] == 'none'}

def test_valid_plan_derives_dependency_layers_without_worker_count_alias():
    result = validate(plan())
    assert result['team_plan_valid'] is True
    assert result['ready_layers'] == [['U1'], ['U2']]
    assert result['unit_count'] == 2
    assert 'worker_count' not in result

def test_team_plan_is_only_for_multi_responsibility_coordination():
    payload = plan()
    payload['units'] = payload['units'][:1]
    payload['integration_order'] = ['U1']
    result = validate(payload)
    assert result['team_plan_valid'] is False
    assert 'TeamPlan requires at least two delegated units' in result['errors']

def test_plan_and_unit_shapes_fail_closed_on_unknown_fields():
    payload = plan()
    payload['unexpected'] = True
    assert any(('unsupported fields' in error for error in validate(payload)['errors']))
    payload = plan()
    payload['units'][0]['unexpected'] = True
    assert any(('unsupported fields' in error for error in validate(payload)['errors']))

def test_malformed_enum_values_fail_closed_instead_of_crashing():
    payload = plan()
    payload['planning_source'] = ['ad_hoc']
    assert 'planning_source is not supported' in validate(payload)['errors']
    payload = plan()
    payload['units'][0]['role'] = ['reader']
    assert 'U1 has unsupported role' in validate(payload)['errors']

def test_duplicate_unknown_self_and_cycle_dependencies_fail_closed():
    duplicate = plan()
    duplicate['units'][1]['unit_id'] = 'U1'
    assert any(('duplicates unit_id' in error for error in validate(duplicate)['errors']))
    unknown = plan()
    unknown['units'][1]['depends_on'] = ['U9']
    assert 'U2 depends on unknown unit U9' in validate(unknown)['errors']
    self_dep = plan()
    self_dep['units'][1]['depends_on'] = ['U2']
    assert 'U2 cannot depend on itself' in validate(self_dep)['errors']
    cycle = plan()
    cycle['units'][0]['depends_on'] = ['U2']
    cycle['units'][1]['depends_on'] = ['U1']
    assert 'TeamPlan dependency graph contains a cycle' in validate(cycle)['errors']

def test_ready_units_cannot_claim_overlapping_write_ownership():
    payload = plan()
    payload['units'][0] = {'unit_id': 'U1', 'role': 'worker', 'goal': 'first write', 'output': 'first change', 'depends_on': [], 'ownership': {'write': ['src'], 'forbidden': []}, 'done_when': 'done'}
    payload['units'][1]['depends_on'] = []
    payload['units'][1]['ownership']['write'] = ['src/example.py']
    result = validate(payload)
    assert any(('overlapping write scope' in error for error in result['errors']))

def test_policy_read_only_roles_cannot_claim_write_ownership():
    for role in VALIDATOR.READ_ONLY_ROLES:
        payload = plan()
        payload['units'][0]['role'] = role
        payload['units'][0]['ownership']['write'] = ['src/read_only_violation.py']
        result = validate(payload)
        assert any(('read-only role must not declare write ownership' in error for error in result['errors']))

def test_ownership_paths_fail_closed_on_unsafe_or_conflicting_paths():
    for unsafe in ['../outside', 'C:/outside', 'C:outside']:
        payload = plan()
        payload['units'][1]['ownership'] = {'write': [unsafe], 'forbidden': []}
        assert any(('safe relative path' in error for error in validate(payload)['errors']))
    payload = plan()
    payload['units'][1]['ownership'] = {'write': ['src'], 'forbidden': ['src/generated']}
    assert any(('overlaps its forbidden scope' in error for error in validate(payload)['errors']))

def test_integration_order_must_cover_all_units_and_respect_dependencies():
    missing = plan()
    missing['integration_order'] = ['U1']
    assert 'integration_order must cover every delegated unit exactly once' in validate(missing)['errors']
    reversed_order = plan()
    reversed_order['integration_order'] = ['U2', 'U1']
    assert 'integration_order violates dependency order' in validate(reversed_order)['errors']

def test_revision_chain_and_upstream_sources_are_explicit():
    revision = plan()
    revision['revision'] = 2
    revision['supersedes_revision'] = 1
    assert validate(revision)['team_plan_valid'] is True
    wrong = plan()
    wrong['revision'] = 3
    wrong['supersedes_revision'] = 1
    assert 'supersedes_revision must name the direct previous revision' in validate(wrong)['errors']
    upstream = plan()
    upstream['planning_source'] = 'upstream_skill'
    assert 'non-ad_hoc TeamPlan requires source_refs' in validate(upstream)['errors']
    upstream['source_refs'] = ['upstream:stage-2']
    assert validate(upstream)['team_plan_valid'] is True

def test_role_vocabulary_rejects_unknown_role():
    payload = plan()
    payload['units'][0]['role'] = 'researcher'
    assert 'U1 has unsupported role' in validate(payload)['errors']

VALIDATOR = load_team_plan_validator('subagents_dispatch_team_plan_takeover')

def test_teamplan_role_main_is_rejected_because_takeover_is_recovery_state():
    payload = {'schema_version': '1.0', 'revision': 1, 'supersedes_revision': None, 'planning_source': 'ad_hoc', 'source_refs': [], 'root_goal': 'deliver the verified requested result', 'units': [{'unit_id': 'U1', 'role': 'reader', 'goal': 'trace contract', 'output': 'evidence', 'depends_on': [], 'ownership': {'write': [], 'forbidden': []}, 'done_when': 'contract evidenced'}, {'unit_id': 'U2', 'role': 'main', 'goal': 'implement change', 'output': 'source change', 'depends_on': ['U1'], 'ownership': {'write': ['src/example.py'], 'forbidden': []}, 'done_when': 'acceptance passes'}], 'integration_owner': 'main', 'integration_order': ['U1', 'U2'], 'final_verification': 'Main verifies the combined artifact', 'revision_reason': 'initial'}
    result = VALIDATOR.validate_team_plan_payload(payload)
    assert result['team_plan_valid'] is False
    assert 'U2 has unsupported role' in result['errors']
DISPATCH_SKILL_DIR = PLUGIN / 'skills' / 'dispatch'
PROFILES = PLUGIN / 'agent-profiles'
MANIFEST = PLUGIN / '.codex-plugin' / 'plugin.json'
CANONICAL_BLOCKERS = {'contract', 'judgment', 'investigation', 'stalled'}
RUNTIME_OWNERS = {'policy.json', 'routing.md', 'composition.md', 'interaction.md', 'state.md', 'receipt.md', 'team-plan.md', 'recovery.md', 'guardrails.md', 'handoff.md', 'evidence-artifact.md', 'final-review.md'}
DISPATCH_DIRECT_OWNERS = {'policy.json', 'routing.md', 'state.md', 'receipt.md', 'team-plan.md', 'recovery.md', 'guardrails.md', 'handoff.md', 'final-review.md'}

def contract() -> dict:
    return json.loads(POLICY.read_text(encoding='utf-8'))

def current_version() -> str:
    return json.loads(MANIFEST.read_text(encoding='utf-8'))['version']

def test_dispatch_skill_and_openai_metadata_keep_explicit_identity():
    skill = (DISPATCH_SKILL_DIR / 'SKILL.md').read_text(encoding='utf-8')
    match = re.match('^---\\n(.*?)\\n---\\n', skill, re.S)
    assert match
    frontmatter = yaml.safe_load(match.group(1))
    assert frontmatter['name'] == 'dispatch'
    assert frontmatter['description'].strip()
    openai = yaml.safe_load((DISPATCH_SKILL_DIR / 'agents' / 'openai.yaml').read_text(encoding='utf-8'))
    assert openai['interface']['display_name'] == 'Subagents Dispatch: Dispatch'
    assert 'Dispatch' in openai['interface']['default_prompt']
    assert openai['policy']['allow_implicit_invocation'] is False
    for stale in ['$dispatch', '/dispatch', '/subagents-dispatch:dispatch']:
        assert stale not in openai['interface']['default_prompt']

def test_policy_contract_is_the_single_machine_role_source():
    payload = contract()
    assert payload['schema_version'] == 8
    assert set(payload) == {'schema_version', 'delegation', 'write_coordination', 'permission_semantics', 'capability_dedup', 'roles', 'final_review'}
    assert payload['delegation'] == {'max_depth': 1, 'fork_turns': 'none'}
    assert payload['write_coordination'] == {'mode': 'single_writer', 'scope': 'canonical_workspace'}
    assert payload['permission_semantics'] == {'candidate_source_kinds': ['selected_environment', 'parent_turn']}
    assert set(payload['roles']) == {'reader', 'worker', 'solver', 'investigator', 'advisor'}
    profile_files = {path.name for path in PROFILES.glob('*.toml')}
    assert profile_files == {spec['profile_file'] for spec in payload['roles'].values()}
    for spec in payload['roles'].values():
        profile = tomllib.loads((PROFILES / spec['profile_file']).read_text(encoding='utf-8'))
        assert profile['name'] == spec['agent_type']
        assert profile['model'] == spec['model']
        assert profile['model_reasoning_effort'] == spec['effort']
        assert 'sandbox_mode' not in profile
        assert spec['mutation_authority'] in {'none', 'bounded-source-write'}
        assert 'sandbox_intent' not in spec

def test_agent_profiles_do_not_invent_semantic_blockers():
    found: set[str] = set()
    for path in PROFILES.glob('*.toml'):
        text = path.read_text(encoding='utf-8')
        values = set(re.findall('blocker=([a-z_]+)', text))
        assert values <= CANONICAL_BLOCKERS, f'{path.name} has unsupported blockers: {values - CANONICAL_BLOCKERS}'
        found |= values
    assert CANONICAL_BLOCKERS <= found

def test_runtime_policy_has_focused_owners():
    assert {path.name for path in CONTRACTS.iterdir() if path.is_file()} == RUNTIME_OWNERS
    skill = (DISPATCH_SKILL_DIR / 'SKILL.md').read_text(encoding='utf-8')
    for name in DISPATCH_DIRECT_OWNERS:
        assert f'../../contracts/{name}' in skill

def test_composition_and_evidence_artifact_are_progressive_disclosure_owners():
    composition = (CONTRACTS / 'composition.md').read_text(encoding='utf-8')
    evidence = (CONTRACTS / 'evidence-artifact.md').read_text(encoding='utf-8')
    assert 'constraint intersection' in composition
    assert 'Hooks are optional' in composition
    assert 'does not emulate a missing Host feature' in composition
    assert 'Use references before copies' in evidence
    assert 'Main owns artifact acceptance and sealing' in evidence
    assert 'Evidence artifacts are separate from `active.json`' in evidence

def test_team_plan_and_recovery_do_not_define_fixed_fanout_policy():
    delegation = contract()['delegation']
    assert delegation == {'max_depth': 1, 'fork_turns': 'none'}
    team_plan = (CONTRACTS / 'team-plan.md').read_text(encoding='utf-8').lower()
    recovery = (CONTRACTS / 'recovery.md').read_text(encoding='utf-8').lower()
    assert 'native codex capacity remains the concurrency ceiling' in team_plan
    assert 'two-attempt bound limits automatic delegated recovery' in recovery
    assert 'not a team-size or concurrency limit' in recovery

def test_policy_owned_final_review_contract_has_one_ship_verdict():
    review = (CONTRACTS / 'final-review.md').read_text(encoding='utf-8')
    final_review = contract()['final_review']
    triggers = set(final_review['trigger_codes'])
    assert triggers == {'user_requested', 'public_contract_change', 'persistent_state_change', 'security_boundary', 'authorization_boundary', 'data_integrity', 'concurrency_semantics', 'migration', 'verification_gap'}
    assert final_review['ship_verdict'] == 'ship'
    assert final_review['correction_verdicts'] == ['fix-first', 'rethink']
    assert final_review['unresolved_verdict'] == 'insufficient_evidence'
    for trigger in triggers:
        assert trigger in review

def test_static_routing_cases_match_policy_owned_role_routes():
    schema = json.loads((ROOT / 'evals' / 'routing-case.schema.json').read_text(encoding='utf-8'))
    cases = json.loads((ROOT / 'evals' / 'routing-cases.json').read_text(encoding='utf-8'))
    jsonschema.Draft202012Validator(schema).validate(cases)
    assert cases['schema_version'] == '2.0'
    roles = contract()['roles']
    for case in cases['cases']:
        for node in case['expected']['nodes']:
            spec = roles[node['role']]
            assert node['model'] == spec['model']
            assert node['effort'] == spec['effort']
            assert node['agent_type'] == spec['agent_type']
            assert node['mutation_authority'] == spec['mutation_authority']

def test_public_docs_keep_product_identity_while_ai_reference_points_to_policy_owners():
    directives = {'README.md': '如果你是 AI Agent，请跳转到 [README_AI.md](README_AI.md) 并严格按照说明操作。', 'README_EN.md': 'If you are an AI Agent, jump to [README_AI.md](README_AI.md) and follow the instructions strictly.'}
    version = current_version()
    for name, directive in directives.items():
        text = (ROOT / name).read_text(encoding='utf-8')
        assert directive in text
        assert 'subagents-dispatch' in text
        assert 'Dispatch' in text
        assert 'Doctor' in text
        assert version in text
        assert 'Sol High' in text
        assert '执行' in text if name == 'README.md' else 'Execute' in text
        assert 'preview' in text
        assert 'takeover' in text
        assert '$dispatch' not in text
        assert '$doctor' not in text
    ai = (ROOT / 'README_AI.md').read_text(encoding='utf-8')
    assert f'Current version:     {version}' in ai
    for name in sorted(RUNTIME_OWNERS):
        assert f'contracts/{name}' in ai

def test_canonical_docs_do_not_leak_unverified_namespaced_or_dollar_entrypoints():
    user_facing_files = [CONTRACTS / 'interaction.md', CONTRACTS / 'guardrails.md', CONTRACTS / 'final-review.md', ROOT / 'docs' / 'native-subagent-runtime.md']
    for path in user_facing_files:
        text = path.read_text(encoding='utf-8')
        for stale in ['$dispatch', '$doctor', '/subagents-dispatch:dispatch', '/subagents-dispatch:doctor']:
            assert stale not in text, f'{path.name} leaks unverified user entrypoint {stale!r}'

def test_readme_ai_distinguishes_skill_ids_from_host_rendered_commands():
    ai = (ROOT / 'README_AI.md').read_text(encoding='utf-8')
    for skill_id in ['dispatch', 'preview', 'status', 'steer', 'takeover', 'doctor']:
        assert f'`{skill_id}`' in ai
    assert 'Do not invent a Codex App slash-command string' in ai
    assert 'Plugin directory:    .' in ai
    assert 'plugins/subagents-dispatch' not in ai

def test_missing_current_dispatch_and_missing_target_never_create_fake_control_state():
    text = INTERACTION.read_text(encoding='utf-8')
    assert 'there are no current delegated responsibilities' in text
    assert 'do not reconstruct an old task from memory' in text
    assert 'takeover does not proceed' in text
    payload = json.loads(CASES.read_text(encoding='utf-8'))
    by_id = {case['id']: case for case in payload['cases']}
    empty = by_id['status-with-no-current-dispatch-does-not-invent-state']['expected']
    assert empty['active_responsibilities'] == 0
    assert empty['reported_unknown_unit'] is False
    assert empty['search_other_sessions'] is False
    missing = by_id['control-target-missing-fails-closed']['expected']
    assert missing['target_resolved'] is False
    assert missing['ownership_transferred'] is False
    assert missing['invent_agent_id'] is False
    assert missing['search_other_sessions'] is False

def test_blocked_delegated_terminal_response_keeps_compact_receipt():
    interaction = INTERACTION.read_text(encoding='utf-8')
    receipt = RECEIPT.read_text(encoding='utf-8')
    assert 'whether the requested work completed successfully or ended blocked/partial' in interaction
    assert 'Main owns the task-facing final response' in receipt
    assert '../../contracts/receipt.md' in DISPATCH_SKILL.read_text(encoding='utf-8')
    payload = json.loads(CASES.read_text(encoding='utf-8'))
    by_id = {case['id']: case for case in payload['cases']}
    expected = by_id['blocked-delegated-outcome-still-has-receipt']['expected']
    assert expected['receipt'] is True
    assert expected['axes'] == ['Dispatch', 'Review']
    assert expected['may_report_blocker'] is True
    assert expected['must_preserve_unknown'] is True
