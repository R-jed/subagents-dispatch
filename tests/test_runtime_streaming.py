from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import pytest
import gc
import weakref
ROOT = Path(__file__).resolve().parents[1]
INSPECTOR = ROOT / 'scripts' / 'inspect-agent-runtime.py'
RELEASE_CHECKLIST = ROOT / 'docs' / 'release-checklist.md'
REQUIREMENTS = ROOT / 'requirements-dev.txt'
THREAD = '11111111-1111-7111-8111-111111111111'
PARENT = '00000000-0000-7000-8000-000000000000'
ROLE = 'subagents_dispatch_programmer'

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
            write_rollout(rollout, model='gpt-5.6-sol')
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

def test_experiment_plane_has_no_temporary_profile_materialization_modules():
    retired = {
        "calibration_profile_contract.py",
        "calibration_profiles.py",
        "calibration_profiles_core.py",
        "validate_experiment_campaign_core.py",
    }
    assert not any((ROOT / "scripts" / name).exists() for name in retired)
    for current in ("validate-experiment-campaign.py", "validate-experiment-run.py"):
        text = (ROOT / "scripts" / current).read_text(encoding="utf-8")
        assert "materialized_agent_type" not in text
        assert "materialization_manifest_ref" not in text
        assert "calibration_profiles" not in text


def test_dev_dependency_closure_is_exactly_pinned_for_ci_replay():
    lines = {line.strip() for line in REQUIREMENTS.read_text(encoding='utf-8').splitlines() if line.strip() and (not line.lstrip().startswith('#'))}
    required = {'jsonschema==4.26.0', 'PyYAML==6.0.3', 'pytest==9.1.1', 'ruff==0.12.12', 'attrs==26.1.0', 'jsonschema-specifications==2025.9.1', 'referencing==0.37.0', 'rpds-py==2026.6.3', 'iniconfig==2.3.0', 'packaging==26.3', 'pluggy==1.6.0', 'Pygments==2.20.0', 'typing-extensions==4.16.0', 'colorama==0.4.6; platform_system == "Windows"'}
    assert lines == required
ROOT = Path(__file__).resolve().parents[1]
INSPECTOR = ROOT / 'scripts' / 'inspect-agent-runtime.py'
THREAD = '11111111-1111-7111-8111-111111111111'
PARENT = '00000000-0000-7000-8000-000000000000'
ROLE = 'subagents_dispatch_programmer'

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
