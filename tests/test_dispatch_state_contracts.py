from __future__ import annotations
import importlib.util
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / 'scripts' / 'dispatch_state.py'

def _dispatch_state_compact_schema__load_module():
    spec = importlib.util.spec_from_file_location('dispatch_state_compact_schema', MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def _dispatch_state_compact_schema__unit():
    return {'unit_id': 'U1', 'task_id': 'task-1', 'attempt': 1, 'native_task_name': 'sd_u1_a1-execute', 'agent_id': None, 'role': 'worker', 'model_lane': 'Luna Max', 'responsibility': {'outcome': 'change one owned file', 'intent': 'implement', 'acceptance': 'focused test passes'}, 'authority': {'write_scope': ['owned.py'], 'mutation_authority': 'bounded-source-write', 'decision_rights': ['local implementation mechanics']}, 'writer': True, 'control_state': 'SPAWN_PENDING', 'adopted': False, 'accepted': False, 'failure_origin': 'none', 'blocker': 'none', 'quarantine_reason': None}

def state_with_unit(module):
    state = module.new_state(thread_id='thread-1', locale='en')
    state['units'] = [_dispatch_state_compact_schema__unit()]
    return state

def test_compact_snapshot_accepts_only_existing_router_and_authority_shape():
    module = _dispatch_state_compact_schema__load_module()
    state = state_with_unit(module)
    state['team_plan_revision'] = 2
    state['pending_takeover'] = {'unit_id': 'U1', 'status': 'pending'}
    assert module.validate_state_payload(state) == state

@pytest.mark.parametrize('field,value,message', [('team_plan_revision', 0, 'positive integer'), ('team_plan_revision', True, 'positive integer'), ('controls', [{'action': 'Status'}], 'must remain empty'), ('pending_takeover', {'unit_id': 'U9', 'status': 'pending'}, 'existing unit'), ('pending_takeover', {'unit_id': 'U1', 'status': 'done'}, 'status=pending'), ('pending_takeover', {'unit_id': 'U1', 'status': 'pending', 'note': 'free-form'}, 'exactly unit_id and status')])
def test_top_level_compact_metadata_rejects_unowned_or_malformed_state(field, value, message):
    module = _dispatch_state_compact_schema__load_module()
    state = state_with_unit(module)
    state[field] = value
    with pytest.raises(module.StatePayloadError, match=message):
        module.validate_state_payload(state)

def test_responsibility_rejects_free_form_or_invalid_intent():
    module = _dispatch_state_compact_schema__load_module()
    state = state_with_unit(module)
    state['units'][0]['responsibility']['task_description'] = 'copy arbitrary task text'
    with pytest.raises(module.StatePayloadError, match='responsibility has unsupported fields'):
        module.validate_state_payload(state)
    state = state_with_unit(module)
    state['units'][0]['responsibility']['intent'] = 'deploy'
    with pytest.raises(module.StatePayloadError, match='invalid intent'):
        module.validate_state_payload(state)

def test_authority_rejects_free_form_fields_and_invalid_values():
    module = _dispatch_state_compact_schema__load_module()
    state = state_with_unit(module)
    state['units'][0]['authority']['notes'] = 'arbitrary authority prose'
    with pytest.raises(module.StatePayloadError, match='authority has unsupported fields'):
        module.validate_state_payload(state)
    state = state_with_unit(module)
    state['units'][0]['authority']['mutation_authority'] = 'unbounded'
    with pytest.raises(module.StatePayloadError, match='invalid mutation_authority'):
        module.validate_state_payload(state)
    state = state_with_unit(module)
    state['units'][0]['authority']['write_scope'] = ['']
    with pytest.raises(module.StatePayloadError, match='array of non-empty strings'):
        module.validate_state_payload(state)

def test_receipt_summary_has_no_unreachable_generic_recovery_channel():
    module = _dispatch_state_compact_schema__load_module()
    summary = module.account_receipt([])
    assert 'recoveries' not in summary
    forged = {**summary, 'zero_child': False, 'dispatch': [{'model_lane': None, 'activity': 'read', 'count': 1}], 'recoveries': 3}
    rendered = module.format_receipt(forged, locale='en')
    assert 'recovery×' not in rendered
ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / 'scripts' / 'dispatch_state.py'

def _dispatch_state_hardening__load_module():
    spec = importlib.util.spec_from_file_location('dispatch_state_hardening', MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def _dispatch_state_hardening__unit(module, *, state='UNKNOWN', blocker='investigation'):
    return {'unit_id': 'U1', 'task_id': 'task-1', 'attempt': 1, 'native_task_name': 'sd_u1_a1-execute', 'agent_id': 'agent-1', 'role': 'worker', 'model_lane': 'Luna Max', 'responsibility': {'outcome': 'change one file', 'acceptance': 'focused test passes'}, 'authority': {'write_scope': ['owned.py']}, 'writer': True, 'control_state': state, 'adopted': False, 'accepted': False, 'failure_origin': 'runtime_ambiguous' if state == 'UNKNOWN' else 'none', 'blocker': blocker, 'quarantine_reason': 'native_identity_not_found' if state == 'UNKNOWN' else None}

def errored_observation(*, failure_origin: str):
    return {'complete': True, 'children': [{'native_task_name': 'sd_u1_a1-execute', 'agent_id': 'agent-1', 'state': 'errored', 'failure_origin': failure_origin}]}

def test_reconcile_real_failure_clears_quarantine_blocker_and_normalizes_origin(tmp_path: Path):
    module = _dispatch_state_hardening__load_module()
    state = module.new_state(thread_id='thread-1', locale='zh')
    state['units'] = [_dispatch_state_hardening__unit(module)]
    reconciled = module.reconcile_state(state, errored_observation(failure_origin='runtime_ambiguous'))
    record = reconciled['units'][0]
    assert record['control_state'] == 'FAILED'
    assert record['failure_origin'] == 'tool_failure'
    assert record['blocker'] == 'none'
    assert record['quarantine_reason'] is None

def test_reconcile_real_failure_preserves_supported_failure_origin():
    module = _dispatch_state_hardening__load_module()
    state = module.new_state(thread_id='thread-1', locale='en')
    state['units'] = [_dispatch_state_hardening__unit(module)]
    reconciled = module.reconcile_state(state, errored_observation(failure_origin='timeout'))
    record = reconciled['units'][0]
    assert record['control_state'] == 'FAILED'
    assert record['failure_origin'] == 'timeout'
    assert record['blocker'] == 'none'
    assert record['quarantine_reason'] is None

def test_remove_missing_state_does_not_create_thread_or_lock(tmp_path: Path):
    module = _dispatch_state_hardening__load_module()
    thread_root = tmp_path / 'subagents-dispatch' / 'missing-thread'
    assert module.remove_state('missing-thread', temp_root=tmp_path) is False
    assert not thread_root.exists()
