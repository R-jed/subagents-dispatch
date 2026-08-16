from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
DOCTOR = ROOT / 'scripts' / 'doctor.py'
INSTALLER = ROOT / 'scripts' / 'install-agents.py'
POLICY = json.loads((ROOT / 'contracts' / 'policy.json').read_text(encoding='utf-8'))
THREAD = '11111111-1111-7111-8111-111111111111'
PARENT = '00000000-0000-7000-8000-000000000000'
WORKER = POLICY['roles']['worker']

def install(home: Path) -> None:
    result = subprocess.run([sys.executable, str(INSTALLER), '--codex-home', str(home)], cwd=ROOT, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr

def route() -> dict:
    return {'thread_id': THREAD, 'parent_thread_id': PARENT, 'agent_role': WORKER['agent_type'], 'model': WORKER['model'], 'effort': WORKER['effort'], 'sandbox_policy_type': 'danger-full-access', 'permission_profile_type': 'disabled'}

def formal_evidence(*, include_permission_provenance: bool=True, require_permission_provenance: bool=False) -> dict:
    source = {'source_kind': 'parent_turn', 'source_id': PARENT, 'sandbox_policy_type': 'danger-full-access', 'permission_profile_type': 'disabled'}
    if include_permission_provenance:
        source.update({'evidence_ref': 'rollout:parent', 'selection_evidence_ref': 'host:permission-source-selection'})
    return {'subject': 'child', 'expected': {'thread_id': THREAD, 'parent_thread_id': PARENT, 'agent_role': WORKER['agent_type'], 'model': WORKER['model'], 'effort': WORKER['effort'], 'runtime_observation_required': True, 'requires_permission_observation': True, 'requires_permission_provenance': require_permission_provenance}, 'local': route(), 'local_permission_source': source}

def run_doctor(home: Path, evidence: Path, *, live_route: bool=True) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(DOCTOR), '--codex-home', str(home), '--check', '--runtime-evidence', str(evidence)]
    if live_route:
        command.append('--live-route')
    return subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)

def test_doctor_accepts_complete_exact_rollout_attestation_without_public_route_metadata(tmp_path: Path):
    home = tmp_path / 'codex-home'
    install(home)
    evidence = tmp_path / 'runtime.json'
    evidence.write_text(json.dumps(formal_evidence()), encoding='utf-8')
    result = run_doctor(home, evidence)
    assert result.returncode == 0, result.stdout + result.stderr
    assert '[OK] Runtime route:' in result.stdout
    assert '[OK] Effective permission state:' in result.stdout
    assert '[OK] Permission-source provenance:' in result.stdout
    assert 'Overall: HEALTHY' in result.stdout

def test_doctor_live_route_rejects_missing_formal_requirement_flags(tmp_path: Path):
    home = tmp_path / 'codex-home'
    install(home)
    payload = formal_evidence()
    del payload['expected']['requires_permission_observation']
    evidence = tmp_path / 'runtime-missing-flag.json'
    evidence.write_text(json.dumps(payload), encoding='utf-8')
    result = run_doctor(home, evidence)
    assert result.returncode == 1
    assert '[FAIL] Runtime route:' in result.stdout
    assert 'requires expected.requires_permission_observation=true' in result.stdout
    assert 'Overall: UNHEALTHY' in result.stdout

def test_doctor_live_route_keeps_verified_state_separate_from_unknown_provenance(tmp_path: Path):
    home = tmp_path / 'codex-home'
    install(home)
    evidence = tmp_path / 'runtime-unbound-source.json'
    evidence.write_text(json.dumps(formal_evidence(include_permission_provenance=False)), encoding='utf-8')
    result = run_doctor(home, evidence)
    assert result.returncode == 0
    assert '[OK] Runtime route:' in result.stdout
    assert '[OK] Effective permission state:' in result.stdout
    assert '[UNKNOWN] Permission-source provenance:' in result.stdout
    assert 'Overall: HEALTHY' in result.stdout

def test_doctor_live_route_blocks_when_the_claim_requires_unknown_provenance(tmp_path: Path):
    home = tmp_path / 'codex-home'
    install(home)
    evidence = tmp_path / 'runtime-unbound-source.json'
    evidence.write_text(json.dumps(formal_evidence(include_permission_provenance=False, require_permission_provenance=True)), encoding='utf-8')
    result = run_doctor(home, evidence)
    assert result.returncode == 1
    assert '[OK] Runtime route:' in result.stdout
    assert '[OK] Effective permission state:' in result.stdout
    assert '[UNKNOWN] Permission-source provenance:' in result.stdout
    assert 'Overall: ATTENTION' in result.stdout

def test_non_live_doctor_keeps_unknown_runtime_evidence_nonfatal(tmp_path: Path):
    home = tmp_path / 'codex-home'
    install(home)
    evidence = tmp_path / 'runtime-unbound-source.json'
    evidence.write_text(json.dumps(formal_evidence(include_permission_provenance=False)), encoding='utf-8')
    result = run_doctor(home, evidence, live_route=False)
    assert result.returncode == 0
    assert '[OK] Runtime route:' in result.stdout
    assert '[OK] Effective permission state:' in result.stdout
    assert '[UNKNOWN] Permission-source provenance:' in result.stdout
    assert 'Overall: HEALTHY' in result.stdout
ROOT = Path(__file__).resolve().parents[1]
NORMALIZER = ROOT / 'scripts' / 'runtime-evidence.py'
POLICY = json.loads((ROOT / 'contracts' / 'policy.json').read_text(encoding='utf-8'))
THREAD = '11111111-1111-7111-8111-111111111111'
PARENT = '00000000-0000-7000-8000-000000000000'
WORKER = POLICY['roles']['worker']

def expected() -> dict:
    return {'thread_id': THREAD, 'parent_thread_id': PARENT, 'agent_role': WORKER['agent_type'], 'model': WORKER['model'], 'effort': WORKER['effort'], 'runtime_observation_required': True, 'requires_permission_observation': True}

def full_observation() -> dict:
    return {'thread_id': THREAD, 'parent_thread_id': PARENT, 'agent_role': WORKER['agent_type'], 'model': WORKER['model'], 'effort': WORKER['effort'], 'sandbox_policy_type': 'danger-full-access', 'permission_profile_type': 'disabled', 'runtime_version': '0.999.0-test'}

def permission_source(*, kind: str='parent_turn', source_id: str | None=None) -> dict:
    return {'source_kind': kind, 'source_id': source_id or (PARENT if kind == 'parent_turn' else 'environment:test'), 'sandbox_policy_type': 'danger-full-access', 'permission_profile_type': 'disabled', 'evidence_ref': 'runtime:permission-source', 'selection_evidence_ref': 'runtime:permission-source-selection'}

def normalize(payload: dict) -> dict:
    result = subprocess.run([sys.executable, str(NORMALIZER)], cwd=ROOT, input=json.dumps(payload), text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)

def test_exact_local_rollout_can_close_formal_runtime_observation():
    data = normalize({'subject': 'child', 'expected': expected(), 'local': full_observation(), 'local_permission_source': permission_source()})
    assert data['status'] == 'matched'
    assert data['decision'] == 'continue'
    assert data['evidence_grade'] == 'L1_local_record_observed'
    assert data['route_evidence']['status'] == 'matched'
    assert data['route_evidence']['source'] == 'local'
    assert data['truth_layers']['observed']['status'] == 'matched'
    assert data['truth_layers']['observed']['fields'] == {'agent_role': WORKER['agent_type'], 'model': WORKER['model'], 'effort': WORKER['effort']}
    assert data['truth_layers']['observed']['source_by_field'] == {'agent_role': 'local', 'model': 'local', 'effort': 'local'}
    assert data['permission_state_assurance'] == {'status': 'verified', 'source': 'local', 'observed_permission_profile': 'disabled', 'observed_sandbox': 'danger-full-access', 'violations': []}
    assert data['permission_provenance_assurance'] == {'status': 'verified', 'source': 'local', 'selection_evidence_ref': 'runtime:permission-source-selection', 'source_evidence_ref': 'runtime:permission-source', 'source_id': PARENT, 'source_kind': 'parent_turn', 'source_permission_profile': 'disabled', 'source_sandbox': 'danger-full-access', 'violations': []}
    assert data['runtime_observation_complete'] is True
    assert data['runtime_reported'] is False
    assert data['local_record_observed'] is True

def test_public_and_local_runtime_sources_can_collectively_close_required_fields():
    native = {'thread_id': THREAD, 'agent_role': WORKER['agent_type'], 'model': WORKER['model']}
    local = full_observation()
    del local['model']
    data = normalize({'subject': 'child', 'expected': expected(), 'native': native, 'local': local, 'native_permission_source': permission_source(kind='selected_environment')})
    assert data['status'] == 'matched'
    assert data['decision'] == 'continue'
    assert data['route_evidence']['status'] == 'matched'
    assert data['route_evidence']['source'] == 'both'
    assert data['truth_layers']['observed']['source_by_field'] == {'agent_role': 'both', 'model': 'native', 'effort': 'local'}
    assert data['ancestry_evidence'] == {'status': 'matched', 'source': 'local'}
    assert data['permission_state_assurance']['source'] == 'local'
    assert data['permission_provenance_assurance']['source_id'] == 'environment:test'
    assert data['runtime_observation_complete'] is True

def test_permission_source_provenance_is_independent_from_formal_permission_observation():
    source = permission_source()
    source['selection_evidence_ref'] = None
    data = normalize({'subject': 'child', 'expected': expected(), 'local': full_observation(), 'local_permission_source': source})
    assert data['permission_state_assurance']['status'] == 'verified'
    assert data['permission_provenance_assurance'] == {'status': 'unknown', 'source': 'none', 'violations': []}
    assert data['decision'] == 'continue'

def test_parent_permission_source_must_bind_expected_parent_identity():
    data = normalize({'subject': 'child', 'expected': expected(), 'local': full_observation(), 'native_permission_source': permission_source(source_id='22222222-2222-7222-8222-222222222222')})
    assert data['permission_state_assurance']['status'] == 'verified'
    assert data['permission_provenance_assurance']['status'] == 'failed'
    assert 'permission:source_identity_mismatch' in data['violations']
    assert data['decision'] == 'quarantine'

def test_public_and_local_runtime_conflict_quarantines_the_route():
    native = full_observation()
    local = full_observation()
    local['model'] = 'gpt-5.6-terra'
    data = normalize({'subject': 'child', 'expected': expected(), 'native': native, 'local': local})
    assert data['status'] == 'mismatch'
    assert data['decision'] == 'quarantine'
    assert data['evidence_grade'] == 'X0_conflicted'
    assert data['route_evidence']['status'] == 'conflict'
    assert data['truth_layers']['observed']['status'] == 'conflict'
    assert 'model' in data['truth_layers']['observed']['conflict_fields']
    assert 'source_conflict:model' in data['violations']
    assert 'local:model_mismatch' in data['violations']

def test_host_accepted_route_without_runtime_observation_never_closes_live_gate():
    data = normalize({'subject': 'child', 'expected': expected(), 'accepted': full_observation()})
    assert data['truth_layers']['accepted']['status'] == 'matched'
    assert data['truth_layers']['observed']['status'] == 'not_observed'
    assert data['status'] == 'not_exposed'
    assert data['decision'] == 'return_to_main_session'
    assert data['runtime_observation_complete'] is False
    assert data['evidence_grade'] == 'C1_configuration_only'

def test_local_rollout_missing_effort_remains_unknown_for_formal_live_gate():
    local = full_observation()
    local['effort'] = None
    data = normalize({'subject': 'child', 'expected': expected(), 'local': local})
    assert data['route_evidence']['status'] == 'partial'
    assert data['truth_layers']['observed']['status'] == 'partial'
    assert data['status'] == 'not_exposed'
    assert data['decision'] == 'return_to_main_session'
    assert data['runtime_observation_complete'] is False
    assert data['local_record_observed'] is False

def test_accepted_and_local_conflict_is_not_hidden_when_public_metadata_is_absent():
    accepted = full_observation()
    local = full_observation()
    accepted['effort'] = 'high'
    data = normalize({'subject': 'child', 'expected': expected(), 'accepted': accepted, 'local': local})
    assert data['status'] == 'mismatch'
    assert data['decision'] == 'quarantine'
    assert data['truth_layers']['accepted']['status'] == 'conflict'
    assert data['truth_layers']['observed']['status'] == 'conflict'
    assert 'accepted:effort_mismatch' in data['violations']
    assert 'accepted_observed_conflict:effort' in data['violations']
