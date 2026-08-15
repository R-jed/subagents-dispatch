from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import importlib.util
import pytest
ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT
GUARDRAILS = PLUGIN / 'contracts' / 'guardrails.md'
RUNTIME_DOC = ROOT / 'docs' / 'native-subagent-runtime.md'
ATTESTATION_DOC = ROOT / 'docs' / 'runtime-attestation.md'
_runtime_assurance__RUNTIME_VERIFIER = PLUGIN / 'scripts' / 'runtime-evidence.py'
RUNTIME_INSPECTOR = PLUGIN / 'scripts' / 'inspect-agent-runtime.py'
RUNTIME_CASES = ROOT / 'evals' / 'runtime-assurance-cases.json'

def _runtime_assurance__run_runtime_evidence(payload: dict) -> dict:
    result = subprocess.run([sys.executable, str(_runtime_assurance__RUNTIME_VERIFIER)], cwd=ROOT, input=json.dumps(payload), text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)

def test_runtime_assurance_uses_explicit_inspector_and_normalized_verifier():
    assert _runtime_assurance__RUNTIME_VERIFIER.is_file()
    assert RUNTIME_INSPECTOR.is_file()
    assert ATTESTATION_DOC.is_file()
    guardrails = GUARDRAILS.read_text(encoding='utf-8').lower()
    runtime = RUNTIME_DOC.read_text(encoding='utf-8').lower()
    attestation = ATTESTATION_DOC.read_text(encoding='utf-8').lower()
    assert 'runtime-evidence.py' in guardrails
    assert 'runtime-evidence.py' in runtime
    assert 'inspect-agent-runtime.py' in guardrails
    assert 'inspect-agent-runtime.py' in attestation
    assert 'diagnostic' in runtime
    assert 'do not run these checks as routine ceremony' in runtime
    assert 'runtime evidence is on demand' in guardrails
    assert 'ordinary dispatch does not run' in attestation

def test_exact_runtime_inspector_is_allowlisted_and_not_a_transcript_collector():
    source = RUNTIME_INSPECTOR.read_text(encoding='utf-8')
    attestation = ATTESTATION_DOC.read_text(encoding='utf-8')
    for field in ['thread_id', 'parent_thread_id', 'agent_role', 'model', 'effort', 'sandbox_policy_type', 'permission_profile_type', 'runtime_version']:
        assert field in source
        assert field in attestation
    assert 'record_type == "session_meta"' in source
    assert 'record_type == "turn_context"' in source
    assert 'record_type == "event_msg"' not in source
    assert 'record_type == "response_item"' not in source
    assert 'The inspector does not emit prompts' in attestation
    assert 'assistant messages' in attestation
    assert 'hidden reasoning' in attestation
    assert 'tool payloads' in attestation

def test_runtime_configuration_cannot_impersonate_host_observation():
    guardrails = GUARDRAILS.read_text(encoding='utf-8')
    attestation = ATTESTATION_DOC.read_text(encoding='utf-8')
    assert 'Configured/requested is not accepted. Accepted is not observed.' in guardrails
    assert 'A child describing its own model or reasoning level in prose is not runtime evidence' in guardrails
    assert 'Configured is not Observed' in attestation
    assert "A child's prose claim" in attestation
    assert 'manually copied local data cannot be relabeled as runtime observation' in guardrails

def test_local_rollout_attestation_is_not_overclaimed_as_cryptographic_proof():
    attestation = ATTESTATION_DOC.read_text(encoding='utf-8')
    assert 'not cryptographically signed by the Host' in attestation
    assert 'not tamper-proof remote attestation or cryptographic proof' in attestation
    assert 'Prefer public Host runtime metadata' in attestation
    assert 'not a cryptographic attestation claim' in attestation

def test_hard_read_only_requires_actual_host_runtime_evidence():
    guardrails = GUARDRAILS.read_text(encoding='utf-8')
    assert 'When hard read-only isolation is required' in guardrails
    assert 'actual Host runtime evidence proves an enforced read-only boundary' in guardrails
    assert 'Main itself is proven Host-enforced read-only' in guardrails
    assert 'otherwise the responsibility remains blocked' in guardrails
    assert 'Configured or accepted values and child self-report are insufficient' in guardrails
    assert 'configured read-only profile is intent, not proof' in guardrails

def test_runtime_evidence_keeps_route_ancestry_and_permission_typed():
    runtime = RUNTIME_DOC.read_text(encoding='utf-8')
    verifier = _runtime_assurance__RUNTIME_VERIFIER.read_text(encoding='utf-8')
    for field in ['route_assurance', 'permission_state_assurance', 'permission_provenance_assurance']:
        assert field in runtime
        assert field in verifier
    for grade in ['C1_configuration_only', 'L1_local_record_observed', 'R1_runtime_reported', 'R2_runtime_reported_and_local_record_agree', 'X0_conflicted']:
        assert grade in verifier

def test_runtime_observation_required_accepts_exact_local_identity_and_ancestry():
    expected = {'agent_role': 'subagents_dispatch_reader', 'model': 'gpt-5.6-luna', 'effort': 'max', 'thread_id': 'child-1', 'parent_thread_id': 'main-1', 'runtime_observation_required': True, 'requires_enforced_read_only': False}
    route = {'agent_role': 'subagents_dispatch_reader', 'model': 'gpt-5.6-luna', 'effort': 'max'}
    local = {**route, 'thread_id': 'child-1', 'parent_thread_id': 'main-1'}
    local_identity_fallback = _runtime_assurance__run_runtime_evidence({'subject': 'child', 'expected': expected, 'native': route, 'local': local})
    assert local_identity_fallback['status'] == 'matched'
    assert local_identity_fallback['decision'] == 'continue'
    assert local_identity_fallback['runtime_observation_complete'] is True
    assert local_identity_fallback['ancestry_evidence'] == {'status': 'matched', 'source': 'local'}
    native_identity = _runtime_assurance__run_runtime_evidence({'subject': 'child', 'expected': expected, 'native': local, 'local': local})
    assert native_identity['status'] == 'matched'
    assert native_identity['decision'] == 'continue'
    assert native_identity['ancestry_evidence'] == {'status': 'matched', 'source': 'both'}

def test_runtime_assurance_fixture_uses_current_return_target():
    payload = json.loads(RUNTIME_CASES.read_text(encoding='utf-8'))
    assert payload['schema_version'] == '2.0'
    decisions = {case['expected'].get('decision') for case in payload['cases'] if 'decision' in case['expected']}
    assert 'return_to_main_session' in decisions
    assert 'return_to_root' not in decisions
ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT
SKILL = PLUGIN / 'skills' / 'dispatch'
CONTRACTS = PLUGIN / 'contracts'
_runtime_truth_policy__POLICY = PLUGIN / 'contracts' / 'policy.json'

def test_runtime_evidence_is_diagnostic_not_default_hot_path():
    guardrails = (CONTRACTS / 'guardrails.md').read_text(encoding='utf-8')
    router = (CONTRACTS / 'routing.md').read_text(encoding='utf-8')
    assert 'Runtime evidence is on demand' in guardrails
    assert 'Do not run runtime-evidence diagnostics for every ordinary child' in guardrails
    assert 'Main-session Sol dedup is an optimization' in router
    assert 'Missing telemetry is allowed to remain missing' in router

def test_runtime_verifier_supports_main_and_child_subjects_and_policy_reference():
    verifier = (PLUGIN / 'scripts' / 'runtime-evidence.py').read_text(encoding='utf-8')
    policy = json.loads(_runtime_truth_policy__POLICY.read_text(encoding='utf-8'))
    assert 'subject == "main_session"' in verifier
    assert 'subject == "child"' in verifier
    assert 'load_main_coverage_policy' in verifier
    assert policy['capability_dedup']['reference_role'] == 'solver'
    assert 'coverage = "unknown"' in verifier
    assert 'quarantine_main_route_claim' in verifier

def test_exact_project_roles_have_no_cross_role_fallback():
    policy = json.loads(_runtime_truth_policy__POLICY.read_text(encoding='utf-8'))
    guardrails = (CONTRACTS / 'guardrails.md').read_text(encoding='utf-8')
    assert 'Host/configuration limitation and fail closed' in guardrails
    assert 'Do not substitute another role' in guardrails
    assert set((spec['agent_type'] for spec in policy['roles'].values())) == {'subagents_dispatch_reader', 'subagents_dispatch_worker', 'subagents_dispatch_solver', 'subagents_dispatch_investigator', 'subagents_dispatch_advisor'}

def test_new_project_children_use_explicit_fresh_context():
    guardrails = (CONTRACTS / 'guardrails.md').read_text(encoding='utf-8')
    runtime = (ROOT / 'docs' / 'native-subagent-runtime.md').read_text(encoding='utf-8')
    assert '`fork_turns` is present and exactly `none`' in guardrails
    assert 'omitted `fork_turns` are forbidden' in guardrails
    assert 'fork_turns=none' in runtime

def test_consent_writer_and_explicit_invocation_are_guardrail_owned():
    guardrails = (CONTRACTS / 'guardrails.md').read_text(encoding='utf-8')
    for phrase in ['Project policy does not impose an ordinary numeric child ceiling', 'Child count by itself is not a consent trigger', 'One writer per canonical checkout', 'main session when mutating the checkout', 'Explicit invocation only', 'Routine first-use provisioning is not a separate consent prompt']:
        assert phrase in guardrails
    openai = (SKILL / 'agents' / 'openai.yaml').read_text(encoding='utf-8')
    assert 'allow_implicit_invocation: false' in openai

def test_first_use_readiness_occurs_before_delegated_execution():
    guardrails = (CONTRACTS / 'guardrails.md').read_text(encoding='utf-8')
    skill = (SKILL / 'SKILL.md').read_text(encoding='utf-8')
    assert 'First-use readiness before delegated execution' in guardrails
    assert '../../contracts/guardrails.md' in skill
    assert 'RESTART_REQUIRED' in guardrails
    assert 'without attempting `spawn_agent`' in guardrails
    assert 'no child attempt has been created yet' in guardrails

def test_profile_lifecycle_comes_from_policy_and_installer_not_user_docs():
    policy = json.loads(_runtime_truth_policy__POLICY.read_text(encoding='utf-8'))
    profiles = PLUGIN / 'agent-profiles'
    installer = (PLUGIN / 'scripts' / 'install-agents.py').read_text(encoding='utf-8')
    policy_loader = (PLUGIN / 'scripts' / 'policy.py').read_text(encoding='utf-8')
    expected_files = {spec['profile_file'] for spec in policy['roles'].values()}
    assert {path.name for path in profiles.glob('*.toml')} == expected_files
    assert 'MANIFEST_NAME = ".subagents-dispatch-agents.json"' in installer
    assert 'LOCK_NAME = ".subagents-dispatch-agents.lock"' in installer
    assert 'from policy import load_policy_contract' in installer
    assert 'POLICY_CONTRACT_PATH = ROOT / "contracts" / "policy.json"' in policy_loader

def test_process_history_is_not_a_final_review_trigger():
    final_review = (CONTRACTS / 'final-review.md').read_text(encoding='utf-8')
    for phrase in ['Terra use', 'Solver use', 'recovery', 'a large diff']:
        assert phrase in final_review
    assert 'is not a trigger by itself' in final_review

def test_behavioral_evals_remain_measurement_not_runtime_policy():
    docs = (ROOT / 'docs' / 'behavioral-evals.md').read_text(encoding='utf-8').lower()
    for phrase in ['controlled paired workloads', 'measurement surface', 'experiment labels only']:
        assert phrase in docs
ROOT = Path(__file__).resolve().parents[1]
_v3_permission_route_integrity__RUNTIME_VERIFIER = ROOT / 'scripts' / 'runtime-evidence.py'
DOCTOR = ROOT / 'scripts' / 'doctor.py'
_v3_permission_route_integrity__POLICY = ROOT / 'contracts' / 'policy.json'
RUNTIME_CASES = ROOT / 'evals' / 'runtime-assurance-cases.json'
THREAD = '11111111-1111-7111-8111-111111111111'
PARENT = '00000000-0000-7000-8000-000000000000'

def _v3_permission_route_integrity__run_runtime_evidence(payload: dict) -> dict:
    result = subprocess.run([sys.executable, str(_v3_permission_route_integrity__RUNTIME_VERIFIER)], cwd=ROOT, input=json.dumps(payload), text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)

def load_doctor_module():
    scripts = str(ROOT / 'scripts')
    sys.path.insert(0, scripts)
    try:
        spec = importlib.util.spec_from_file_location('doctor_permission_under_test', DOCTOR)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts)

def managed_routes() -> list[dict]:
    payload = json.loads(_v3_permission_route_integrity__POLICY.read_text(encoding='utf-8'))
    return list(payload['roles'].values())

def expected_for(route: dict) -> dict:
    return {'thread_id': THREAD, 'parent_thread_id': PARENT, 'agent_role': route['agent_type'], 'model': route['model'], 'effort': route['effort'], 'runtime_observation_required': True, 'requires_enforced_read_only': False, 'requires_permission_observation': True}

def native_for(route: dict, *, sandbox: str='danger-full-access', profile: str='disabled') -> dict:
    value = {'thread_id': THREAD, 'parent_thread_id': PARENT, 'agent_role': route['agent_type'], 'model': route['model'], 'effort': route['effort'], 'sandbox_policy_type': sandbox, 'permission_profile_type': profile}
    return value

def host_permission_source(*, source_kind: str='parent_turn', source_id: str | None=None, sandbox: str='danger-full-access', profile: str='disabled') -> dict:
    return {'source_kind': source_kind, 'source_id': source_id or (PARENT if source_kind == 'parent_turn' else 'environment:test'), 'sandbox_policy_type': sandbox, 'permission_profile_type': profile, 'evidence_ref': 'host:effective-permission-source', 'selection_evidence_ref': 'host:permission-source-selection'}

@pytest.mark.parametrize('route', managed_routes(), ids=lambda route: route['agent_type'])
def test_live_route_permission_matches_host_observed_source_for_all_managed_roles(route: dict):
    data = _v3_permission_route_integrity__run_runtime_evidence({'subject': 'child', 'expected': expected_for(route), 'native': native_for(route), 'native_permission_source': host_permission_source()})
    assert data['status'] == 'matched'
    assert data['decision'] == 'continue'
    assert data['permission_state_assurance']['status'] == 'verified'
    assert data['permission_state_assurance']['observed_sandbox'] == 'danger-full-access'
    assert data['permission_provenance_assurance']['status'] == 'verified'
    assert data['permission_provenance_assurance']['source_kind'] == 'parent_turn'
    assert data['permission_provenance_assurance']['source_id'] == PARENT

@pytest.mark.parametrize('route', managed_routes(), ids=lambda route: route['agent_type'])
def test_read_only_environment_source_is_host_observed_for_all_managed_roles(route: dict):
    data = _v3_permission_route_integrity__run_runtime_evidence({'subject': 'child', 'expected': expected_for(route), 'native': native_for(route, sandbox='read-only', profile='default'), 'native_permission_source': host_permission_source(source_kind='selected_environment', sandbox='read-only', profile='default')})
    assert data['permission_state_assurance']['status'] == 'verified'
    assert data['permission_provenance_assurance']['status'] == 'verified'
    assert data['permission_provenance_assurance']['source_id'] == 'environment:test'
    assert data['decision'] == 'continue'

def test_permission_profile_mismatch_quarantines_even_when_sandbox_matches():
    route = managed_routes()[0]
    data = _v3_permission_route_integrity__run_runtime_evidence({'subject': 'child', 'expected': expected_for(route), 'native': native_for(route), 'native_permission_source': host_permission_source(profile='default')})
    assert data['permission_state_assurance']['status'] == 'verified'
    assert data['permission_provenance_assurance']['status'] == 'failed'
    assert data['decision'] == 'quarantine'

def test_incomplete_host_permission_source_remains_unknown():
    route = managed_routes()[0]
    source = host_permission_source()
    del source['permission_profile_type']
    data = _v3_permission_route_integrity__run_runtime_evidence({'subject': 'child', 'expected': expected_for(route), 'native': native_for(route), 'native_permission_source': source})
    assert data['permission_state_assurance']['status'] == 'verified'
    assert data['permission_provenance_assurance']['status'] == 'unknown'
    assert data['decision'] == 'continue'

def test_permission_source_without_provenance_cannot_close_a_provenance_gate():
    route = managed_routes()[0]
    source = host_permission_source()
    del source['evidence_ref']
    data = _v3_permission_route_integrity__run_runtime_evidence({'subject': 'child', 'expected': expected_for(route), 'native': native_for(route), 'native_permission_source': source})
    assert data['permission_state_assurance']['status'] == 'verified'
    assert data['permission_provenance_assurance']['status'] == 'unknown'
    assert data['decision'] == 'continue'

def test_parent_permission_source_identity_mismatch_quarantines():
    route = managed_routes()[0]
    data = _v3_permission_route_integrity__run_runtime_evidence({'subject': 'child', 'expected': expected_for(route), 'native': native_for(route), 'native_permission_source': host_permission_source(source_id='22222222-2222-7222-8222-222222222222')})
    assert data['permission_state_assurance']['status'] == 'verified'
    assert data['permission_provenance_assurance']['status'] == 'failed'
    assert data['decision'] == 'quarantine'
    assert 'permission:source_identity_mismatch' in data['violations']

@pytest.mark.parametrize(('agent_type', 'wrong_sandbox'), [('subagents_dispatch_reader', 'read-only'), ('subagents_dispatch_worker', 'read-only')])
def test_routes_quarantine_observed_provenance_state_mismatch(agent_type: str, wrong_sandbox: str):
    route = next((item for item in managed_routes() if item['agent_type'] == agent_type))
    data = _v3_permission_route_integrity__run_runtime_evidence({'subject': 'child', 'expected': expected_for(route), 'native': native_for(route, sandbox=wrong_sandbox), 'native_permission_source': host_permission_source()})
    assert data['route_evidence']['status'] == 'matched'
    assert data['permission_state_assurance']['status'] == 'verified'
    assert data['permission_state_assurance']['observed_sandbox'] == wrong_sandbox
    assert data['permission_provenance_assurance']['status'] == 'failed'
    assert data['permission_provenance_assurance']['source_sandbox'] == 'danger-full-access'
    assert data['status'] == 'mismatch'
    assert data['decision'] == 'quarantine'
    assert data['evidence_grade'] == 'X0_conflicted'
    assert 'permission:provenance_state_mismatch' in data['violations']

def test_observed_permission_state_stays_verified_when_provenance_is_absent():
    route = next((item for item in managed_routes() if item['agent_type'] == 'subagents_dispatch_worker'))
    data = _v3_permission_route_integrity__run_runtime_evidence({'subject': 'child', 'expected': expected_for(route), 'native': native_for(route)})
    assert data['route_evidence']['status'] == 'matched'
    assert data['permission_state_assurance']['status'] == 'verified'
    assert data['permission_provenance_assurance']['status'] == 'unknown'
    assert data['decision'] == 'continue'
    assert data['violations'] == []
    doctor = load_doctor_module()
    status, _ = doctor._runtime_status(data)
    assert status == 'OK'

def test_doctor_live_route_contract_keeps_permission_state_and_provenance_separate():
    skill = (ROOT / 'skills' / 'doctor' / 'SKILL.md').read_text(encoding='utf-8')
    assert 'requires_permission_observation=true' in skill
    assert 'requires_permission_provenance=true' in skill
    assert 'native_permission_source' in skill
    assert 'candidate source kinds' in skill
    assert 'Never infer a source from equal permission values' in skill
    assert 'contracts/policy.json' in skill

def test_runtime_assurance_cases_cover_permission_provenance_fail_closed():
    payload = json.loads(RUNTIME_CASES.read_text(encoding='utf-8'))
    cases = {case['id']: case for case in payload['cases']}
    required_ids = {'required-permission-provenance-unobserved', 'required-permission-provenance-unbound', 'required-permission-provenance-identity-mismatch', 'required-permission-provenance-state-mismatch'}
    assert required_ids <= cases.keys()
    assert all((cases[case_id]['input']['requires_permission_provenance'] is True for case_id in required_ids))

def test_accepted_permission_override_is_non_blocking_and_does_not_relabel_route_truth_layers():
    route = next((item for item in managed_routes() if item['agent_type'] == 'subagents_dispatch_worker'))
    accepted = native_for(route, sandbox='read-only')
    native = native_for(route)
    data = _v3_permission_route_integrity__run_runtime_evidence({'subject': 'child', 'expected': expected_for(route), 'accepted': accepted, 'native': native, 'native_permission_source': host_permission_source()})
    assert data['route_evidence']['status'] == 'matched'
    assert data['truth_layers']['accepted']['status'] == 'matched'
    assert data['truth_layers']['observed']['status'] == 'matched'
    assert data['permission_state_assurance']['status'] == 'verified'
    assert data['permission_provenance_assurance']['status'] == 'verified'
    assert data['status'] == 'matched'
    assert data['decision'] == 'continue'

def test_permission_observation_requires_both_child_permission_fields():
    route = next((item for item in managed_routes() if item['agent_type'] == 'subagents_dispatch_worker'))
    native = native_for(route)
    del native['permission_profile_type']
    data = _v3_permission_route_integrity__run_runtime_evidence({'subject': 'child', 'expected': expected_for(route), 'native': native, 'native_permission_source': host_permission_source()})
    assert data['route_evidence']['status'] == 'matched'
    assert data['permission_state_assurance']['status'] == 'unknown'
    assert data['permission_provenance_assurance']['status'] == 'unknown'
    assert data['status'] == 'not_exposed'
    assert data['decision'] == 'return_to_main_session'

def test_enforced_read_only_remains_an_independent_security_gate():
    route = next((item for item in managed_routes() if item['agent_type'] == 'subagents_dispatch_reader'))
    expected = expected_for(route)
    expected['requires_enforced_read_only'] = True
    data = _v3_permission_route_integrity__run_runtime_evidence({'subject': 'child', 'expected': expected, 'native': native_for(route), 'native_permission_source': host_permission_source()})
    assert data['permission_state_assurance']['status'] == 'failed'
    assert data['permission_provenance_assurance']['status'] == 'verified'
    assert data['status'] == 'mismatch'
    assert data['decision'] == 'quarantine'

def test_hard_read_only_documentation_blocks_when_main_is_not_host_enforced_read_only():
    guardrails = (ROOT / 'contracts' / 'guardrails.md').read_text(encoding='utf-8')
    assert 'Main itself is proven Host-enforced read-only' in guardrails
    assert 'otherwise the responsibility remains blocked' in guardrails
