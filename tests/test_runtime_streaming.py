from __future__ import annotations
import ast
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
import gc
import weakref
ROOT = Path(__file__).resolve().parents[1]
INSPECTOR = ROOT / 'scripts' / 'inspect-agent-runtime.py'
DOCTOR_SKILL = ROOT / 'skills' / 'doctor' / 'SKILL.md'
RELEASE_CHECKLIST = ROOT / 'docs' / 'release-checklist.md'
REQUIREMENTS = ROOT / 'requirements-dev.txt'
THREAD = '11111111-1111-7111-8111-111111111111'
PARENT = '00000000-0000-7000-8000-000000000000'
ROLE = 'subagents_dispatch_worker'

def _post_release_hardening__load_inspector():
    spec = importlib.util.spec_from_file_location('post_release_runtime_inspector', INSPECTOR)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def write_rollout(path: Path, *, model: str='gpt-5.6-luna') -> None:
    records = [{'type': 'session_meta', 'payload': {'id': THREAD, 'parent_thread_id': PARENT, 'agent_role': ROLE, 'model_provider': 'openai'}}, {'type': 'turn_context', 'payload': {'model': model, 'effort': 'max', 'sandbox_policy': {'type': 'workspace-write'}, 'permission_profile': {'type': 'default'}, 'cwd': '/project'}}]
    path.write_text('\n'.join((json.dumps(record) for record in records)) + '\n', encoding='utf-8')

def test_release_checklist_does_not_claim_platform_enforced_tag_immutability():
    text = RELEASE_CHECKLIST.read_text(encoding='utf-8')
    assert 'immutable tagged Marketplace distribution' not in text
    assert 'matching immutable semantic-version tag' not in text
    assert 'immutable Marketplace-source gates' not in text
    assert 'create the immutable semantic-version tag' not in text
    assert 'versioned semantic-version tag' in text
    assert 'does not by itself prove platform-enforced tag immutability' in text

def test_doctor_describes_bounded_rollout_streaming():
    text = DOCTOR_SKILL.read_text(encoding='utf-8')
    assert 'streams exactly one rollout' in text
    assert 'bounded total-rollout and per-line input limits' in text
    assert 'Oversized rollout input fails closed' in text

def test_rollout_reader_detects_path_replacement_between_lstat_and_open(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    module = _post_release_hardening__load_inspector()
    sessions = tmp_path / 'sessions'
    sessions.mkdir()
    rollout = sessions / f'rollout-test-{THREAD}.jsonl'
    write_rollout(rollout)
    matched = module.find_exact_rollout(sessions, THREAD)
    original_open = module.os.open
    swapped = False

    def racing_open(path, flags, *args, **kwargs):
        nonlocal swapped
        candidate = Path(path)
        if candidate == rollout and (not swapped):
            swapped = True
            backup = rollout.with_suffix('.original')
            os.replace(rollout, backup)
            write_rollout(rollout, model='gpt-5.6-terra')
        return original_open(path, flags, *args, **kwargs)
    monkeypatch.setattr(module.os, 'open', racing_open)
    with pytest.raises(SystemExit, match='identity drifted while opening'):
        module.inspect_rollout(matched, thread_id=THREAD, expected_parent_thread_id=PARENT, expected_agent_role=ROLE)
    assert swapped is True

def test_rollout_reader_detects_in_place_mutation_after_fd_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    module = _post_release_hardening__load_inspector()
    rollout = tmp_path / f'rollout-test-{THREAD}.jsonl'
    write_rollout(rollout)
    original_lstat = module.os.lstat
    rollout_lstat_calls = 0

    def racing_lstat(path, *args, **kwargs):
        nonlocal rollout_lstat_calls
        candidate = Path(path)
        if candidate == rollout:
            rollout_lstat_calls += 1
            if rollout_lstat_calls == 2:
                with rollout.open('ab') as handle:
                    handle.write(b'\n')
                    handle.flush()
                    os.fsync(handle.fileno())
        return original_lstat(path, *args, **kwargs)
    monkeypatch.setattr(module.os, 'lstat', racing_lstat)
    with pytest.raises(SystemExit, match='changed while being read'):
        list(module.iter_stable_rollout_lines(rollout))
    assert rollout_lstat_calls == 2

def test_rollout_reader_yields_lines_before_reaching_eof(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    module = _post_release_hardening__load_inspector()
    rollout = tmp_path / f'rollout-test-{THREAD}.jsonl'
    write_rollout(rollout)
    with rollout.open('a', encoding='utf-8') as handle:
        handle.write('ignored-record\n' * 10000)
    monkeypatch.setattr(module, 'READ_CHUNK_BYTES', 128)
    original_read = module.os.read
    bytes_read = 0

    def counting_read(fd: int, size: int) -> bytes:
        nonlocal bytes_read
        chunk = original_read(fd, size)
        bytes_read += len(chunk)
        return chunk
    monkeypatch.setattr(module.os, 'read', counting_read)
    lines = module.iter_stable_rollout_lines(rollout)
    try:
        first_line = next(lines)
        assert '"type": "session_meta"' in first_line
        assert bytes_read < rollout.stat().st_size
    finally:
        lines.close()

def test_rollout_reader_rejects_oversized_rollout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    module = _post_release_hardening__load_inspector()
    rollout = tmp_path / f'rollout-test-{THREAD}.jsonl'
    write_rollout(rollout)
    monkeypatch.setattr(module, 'MAX_ROLLOUT_BYTES', 256, raising=False)
    with pytest.raises(SystemExit, match='maximum rollout size'):
        module.inspect_rollout(rollout, thread_id=THREAD, expected_parent_thread_id=PARENT, expected_agent_role=ROLE)

def test_rollout_reader_rejects_oversized_line(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    module = _post_release_hardening__load_inspector()
    rollout = tmp_path / f'rollout-test-{THREAD}.jsonl'
    write_rollout(rollout)
    with rollout.open('a', encoding='utf-8') as handle:
        handle.write('x' * 1024 + '\n')
    monkeypatch.setattr(module, 'MAX_ROLLOUT_BYTES', 8192, raising=False)
    monkeypatch.setattr(module, 'MAX_ROLLOUT_LINE_BYTES', 512, raising=False)
    with pytest.raises(SystemExit, match='maximum rollout line size'):
        module.inspect_rollout(rollout, thread_id=THREAD, expected_parent_thread_id=PARENT, expected_agent_role=ROLE)

def test_calibration_adapter_import_order_is_process_isolated_and_equivalent():
    script = '\nimport hashlib\nimport json\nimport sys\nsys.path.insert(0, sys.argv[1])\norder = sys.argv[2]\nif order == "core-first":\n    import calibration_profiles_core as core\n    import calibration_profiles as adapter\nelse:\n    import calibration_profiles as adapter\n    import calibration_profiles_core as core\nnames = [\n    "_path_inventory",\n    "_load_policy",\n    "_validated_campaign",\n    "_profile_records",\n    "_host_home_identity",\n    "parse_args",\n]\nprint(json.dumps({\n    name: {\n        "same_object": getattr(core, name) is getattr(adapter, name),\n        "adapter_code": hashlib.sha256(getattr(adapter, name).__code__.co_code).hexdigest(),\n        "core_code": hashlib.sha256(getattr(core, name).__code__.co_code).hexdigest(),\n    }\n    for name in names\n}, sort_keys=True))\n'
    outputs = []
    for order in ('core-first', 'adapter-first'):
        result = subprocess.run([sys.executable, '-c', script, str(ROOT / 'scripts'), order], cwd=ROOT, text=True, capture_output=True, check=False)
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert all((item['same_object'] for item in payload.values()))
        assert all((item['adapter_code'] == item['core_code'] for item in payload.values()))
        outputs.append(payload)
    assert outputs[0] == outputs[1]

def test_calibration_core_mutable_hooks_are_not_imported_by_value_in_production():
    mutable_hooks = {'_path_inventory', '_load_policy', '_validated_campaign', '_profile_records', '_host_home_identity', 'parse_args'}
    offenders: list[str] = []
    for path in sorted((ROOT / 'scripts').glob('*.py')):
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.module != 'calibration_profiles_core':
                continue
            bound_hooks = sorted((alias.name for alias in node.names if alias.name in mutable_hooks))
            if bound_hooks:
                offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}: {', '.join(bound_hooks)}")
    assert offenders == []

def test_dev_dependency_closure_is_exactly_pinned_for_ci_replay():
    lines = {line.strip() for line in REQUIREMENTS.read_text(encoding='utf-8').splitlines() if line.strip() and (not line.lstrip().startswith('#'))}
    required = {'jsonschema==4.26.0', 'PyYAML==6.0.3', 'pytest==9.1.1', 'ruff==0.12.12', 'attrs==26.1.0', 'jsonschema-specifications==2025.9.1', 'referencing==0.37.0', 'rpds-py==2026.6.3', 'iniconfig==2.3.0', 'packaging==26.3', 'pluggy==1.6.0', 'Pygments==2.20.0', 'typing-extensions==4.16.0', 'colorama==0.4.6; platform_system == "Windows"'}
    assert lines == required
ROOT = Path(__file__).resolve().parents[1]
INSPECTOR = ROOT / 'scripts' / 'inspect-agent-runtime.py'
THREAD = '11111111-1111-7111-8111-111111111111'
PARENT = '00000000-0000-7000-8000-000000000000'
ROLE = 'subagents_dispatch_worker'

def _rollout_streaming_followup__load_inspector():
    spec = importlib.util.spec_from_file_location('rollout_streaming_followup', INSPECTOR)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def session_meta() -> dict:
    return {'type': 'session_meta', 'payload': {'id': THREAD, 'parent_thread_id': PARENT, 'agent_role': ROLE, 'model_provider': 'openai'}}

def turn_context() -> dict:
    return {'type': 'turn_context', 'payload': {'model': 'gpt-5.6-luna', 'effort': 'max', 'sandbox_policy': {'type': 'workspace-write'}, 'permission_profile': {'type': 'default'}, 'cwd': '/project'}}

def inspect(module, rollout: Path):
    return module.inspect_rollout(rollout, thread_id=THREAD, expected_parent_thread_id=PARENT, expected_agent_role=ROLE)

def test_cr_only_rollout_preserves_text_iterator_newline_compatibility(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    module = _rollout_streaming_followup__load_inspector()
    rollout = tmp_path / f'rollout-test-{THREAD}.jsonl'
    lines = [json.dumps(session_meta()), json.dumps(turn_context())]
    rollout.write_bytes('\r'.join(lines).encode('utf-8') + b'\r')
    monkeypatch.setattr(module, 'READ_CHUNK_BYTES', 19)
    result = inspect(module, rollout)
    assert result['thread_id'] == THREAD
    assert result['model'] == 'gpt-5.6-luna'
    assert result['effort'] == 'max'

def test_crlf_split_across_read_chunks_is_one_newline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    module = _rollout_streaming_followup__load_inspector()
    rollout = tmp_path / f'rollout-test-{THREAD}.jsonl'
    first = json.dumps(session_meta()).encode('utf-8')
    second = json.dumps(turn_context()).encode('utf-8')
    rollout.write_bytes(first + b'\r\n' + second + b'\r\n')
    monkeypatch.setattr(module, 'READ_CHUNK_BYTES', len(first) + 1)
    result = inspect(module, rollout)
    assert result['thread_id'] == THREAD
    assert result['model'] == 'gpt-5.6-luna'
    assert result['effort'] == 'max'

def test_turn_context_payloads_are_aggregated_without_accumulating_all_records(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    module = _rollout_streaming_followup__load_inspector()
    rollout = tmp_path / f'rollout-test-{THREAD}.jsonl'
    records = [session_meta(), *[turn_context() for _ in range(32)]]
    rollout.write_text('\n'.join((json.dumps(record) for record in records)) + '\n', encoding='utf-8')

    class TrackedPayload(dict):
        pass
    original_loads = module.json.loads
    payload_refs: list[weakref.ReferenceType[TrackedPayload]] = []
    max_live_payloads = 0

    def tracking_loads(value: str):
        nonlocal max_live_payloads
        record = original_loads(value)
        if isinstance(record, dict) and record.get('type') == 'turn_context':
            payload = TrackedPayload(record['payload'])
            record['payload'] = payload
            payload_refs.append(weakref.ref(payload))
            gc.collect()
            max_live_payloads = max(max_live_payloads, sum((ref() is not None for ref in payload_refs)))
        return record
    monkeypatch.setattr(module.json, 'loads', tracking_loads)
    result = inspect(module, rollout)
    assert result['model'] == 'gpt-5.6-luna'
    assert result['effort'] == 'max'
    assert max_live_payloads <= 2
ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / 'scripts' / 'dispatch_state.py'

def load_module():
    spec = importlib.util.spec_from_file_location('dispatch_state_hardening', MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def unit(*, state='SPAWN_PENDING', agent_id=None):
    return {'unit_id': 'U1', 'task_id': 'task-1', 'attempt': 1, 'native_task_name': 'sd_u1_a1-execute', 'agent_id': agent_id, 'role': 'worker', 'model_lane': 'Luna Max', 'responsibility': {'outcome': 'change one file', 'acceptance': 'focused test passes'}, 'authority': {'write_scope': ['owned.py']}, 'writer': True, 'control_state': state, 'adopted': False, 'accepted': False, 'failure_origin': 'none', 'blocker': 'none', 'quarantine_reason': None}

def observation(state):
    return {'complete': True, 'children': [{'native_task_name': 'sd_u1_a1-execute', 'agent_id': 'agent-1', 'state': state}]}

def test_current_codex_native_statuses_normalize_without_inventing_new_lifecycle_states():
    module = load_module()
    capsule = module.new_state(thread_id='thread-1', locale='en')
    capsule['units'] = [unit()]
    pending = module.reconcile_state(capsule, observation('pendingInit'))
    assert pending['units'][0]['control_state'] == 'RUNNING'
    assert pending['units'][0]['agent_id'] == 'agent-1'
    completed = module.reconcile_state(pending, observation('completed'))
    assert completed['units'][0]['control_state'] == 'COMPLETED'
    shutdown_source = module.new_state(thread_id='thread-1', locale='en')
    shutdown_source['units'] = [unit(state='RUNNING', agent_id='agent-1')]
    shutdown = module.reconcile_state(shutdown_source, observation('shutdown'))
    assert shutdown['units'][0]['control_state'] == 'CLOSED'
    assert shutdown['units'][0]['adopted'] is False
    error_source = module.new_state(thread_id='thread-1', locale='en')
    error_source['units'] = [unit(state='RUNNING', agent_id='agent-1')]
    errored = module.reconcile_state(error_source, observation('errored'))
    assert errored['units'][0]['control_state'] == 'FAILED'
    assert errored['units'][0]['failure_origin'] == 'tool_failure'

def test_codex_not_found_is_uncertain_and_never_releases_writer_ownership():
    module = load_module()
    capsule = module.new_state(thread_id='thread-1', locale='en')
    capsule['units'] = [unit(state='RUNNING', agent_id='agent-1')]
    reconciled = module.reconcile_state(capsule, observation('notFound'))
    record = reconciled['units'][0]
    assert record['control_state'] == 'UNKNOWN'
    assert record['failure_origin'] == 'runtime_ambiguous'
    assert record['quarantine_reason'] == 'native_identity_not_found'
    takeover = module.takeover_target(reconciled)
    assert takeover['status'] == 'resolved'
    assert takeover['conflicting_write_allowed'] is False

def test_spawn_binding_reloads_canonical_state_and_preserves_concurrent_metadata(tmp_path: Path):
    module = load_module()
    initial = module.new_state(thread_id='thread-1', locale='en')
    prepared = module.prepare_spawn(initial, unit(), temp_root=tmp_path)
    concurrent = module.load_state('thread-1', temp_root=tmp_path)
    assert concurrent is not None
    concurrent['accounting_refs'] = [{'ref': 'control:status:concurrent', 'kind': 'control', 'action': 'Status'}]
    module.write_state(concurrent, temp_root=tmp_path)
    bound = module.bind_spawn_identity('thread-1', unit_id='U1', task_id='task-1', attempt=1, native_task_name='sd_u1_a1-execute', agent_id='agent-1', temp_root=tmp_path, now='2026-08-10T00:00:01Z')
    record = bound['units'][0]
    assert record['control_state'] == 'RUNNING'
    assert record['agent_id'] == 'agent-1'
    assert bound['accounting_refs'] == [{'ref': 'control:status:concurrent', 'kind': 'control', 'action': 'Status'}]
    assert module.load_state('thread-1', temp_root=tmp_path) == bound
    assert prepared['units'][0]['agent_id'] is None
    with pytest.raises(module.StatePayloadError, match='no longer eligible'):
        module.bind_spawn_identity('thread-1', unit_id='U1', task_id='task-1', attempt=1, native_task_name='sd_u1_a1-execute', agent_id='agent-2', temp_root=tmp_path)

def test_persisted_reconciliation_updates_same_capsule_without_losing_metadata(tmp_path: Path):
    module = load_module()
    initial = module.new_state(thread_id='thread-1', locale='zh')
    module.prepare_spawn(initial, unit(), temp_root=tmp_path)
    module.bind_spawn_identity('thread-1', unit_id='U1', task_id='task-1', attempt=1, native_task_name='sd_u1_a1-execute', agent_id='agent-1', temp_root=tmp_path)
    current = module.load_state('thread-1', temp_root=tmp_path)
    assert current is not None
    current['accounting_refs'] = [{'ref': 'control:status:metadata', 'kind': 'control', 'action': 'Status'}]
    module.write_state(current, temp_root=tmp_path)
    snapshot = module.persisted_status_snapshot('thread-1', observation('completed'), temp_root=tmp_path, now='2026-08-10T00:00:02Z')
    assert snapshot['units'][0]['control_state'] == 'COMPLETED'
    persisted = module.load_state('thread-1', temp_root=tmp_path)
    assert persisted is not None
    assert persisted['units'][0]['control_state'] == 'COMPLETED'
    assert persisted['accounting_refs'] == [{'ref': 'control:status:metadata', 'kind': 'control', 'action': 'Status'}]
    assert snapshot['reconciled_state'] == persisted

def test_receipt_uses_materialized_selected_lane_without_claiming_live_telemetry():
    module = load_module()
    materialized = [{'unit_id': 'U1', 'attempt': 1, 'agent_id': 'agent-1', 'role': 'worker', 'model_lane': 'Luna Max'}]
    event = {'ref': 'attempt:U1:A1', 'kind': 'attempt', 'unit_id': 'U1', 'attempt': 1, 'agent_id': 'agent-1', 'activity': 'execute'}
    summary = module.account_receipt([event], materialized_units=materialized)
    assert summary['dispatch'] == [{'model_lane': 'Luna Max', 'activity': 'execute', 'count': 1}]
    assert module.format_receipt(summary, locale='en').startswith('Dispatch: Luna Max Execute')
    configured = {**event, 'model_lane': 'Luna Max', 'model_evidence_source': 'configured'}
    assert module.account_receipt([configured], materialized_units=materialized)['dispatch'] == [{'model_lane': 'Luna Max', 'activity': 'execute', 'count': 1}]
    with pytest.raises(module.ReceiptAccountingError, match='conflicts with selected model lane'):
        module.account_receipt([{**event, 'model_lane': 'Sol High', 'model_evidence_source': 'native'}], materialized_units=materialized)
