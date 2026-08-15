# ruff: noqa: E402
from __future__ import annotations
from pathlib import Path
import sys
import pytest
from test_calibration_profiles import manifest, run, setup
import os
import hashlib
import json
import subprocess
import tomllib

def _owned_paths(evidence: Path) -> list[Path]:
    return [Path(item['path']) for item in manifest(evidence)['profiles']]

def _apply_external_environment_drift(home: Path) -> tuple[bytes, Path]:
    config = b'model = "cc-switch-updated"\nmodel_provider = "custom"\n'
    (home / 'config.toml').write_bytes(config)
    cache_entry = home / 'plugins' / 'cache' / 'external' / 'state.json'
    cache_entry.parent.mkdir(parents=True, exist_ok=True)
    cache_entry.write_text('{"state":"external"}\n', encoding='utf-8')
    return (config, cache_entry)

def test_cleanup_preserves_environment_drift_that_predates_cleanup(tmp_path: Path):
    evidence, home, campaign, _ = setup(tmp_path)
    assert run(evidence, home, campaign, 'create').returncode == 0
    owned_paths = _owned_paths(evidence)
    changed_config, cache_entry = _apply_external_environment_drift(home)
    cleanup = run(evidence, home, campaign, 'cleanup')
    assert cleanup.returncode == 0, cleanup.stderr
    assert all((not path.exists() for path in owned_paths))
    assert all((item['status'] == 'CLEANED' for item in manifest(evidence)['profiles']))
    assert (home / 'config.toml').read_bytes() == changed_config
    assert cache_entry.read_text(encoding='utf-8') == '{"state":"external"}\n'

def test_unexpected_third_calibration_profile_blocks_cleanup_before_owned_deletion(tmp_path: Path):
    evidence, home, campaign, _ = setup(tmp_path)
    assert run(evidence, home, campaign, 'create').returncode == 0
    owned_paths = _owned_paths(evidence)
    extra = home / 'agents' / 'subagents_dispatch_calibration_external.toml'
    extra.write_text('name="external-calibration"\ndescription="keep"\ndeveloper_instructions="keep"\n', encoding='utf-8')
    cleanup = run(evidence, home, campaign, 'cleanup')
    assert cleanup.returncode != 0
    assert 'unexpected third calibration profile blocks cleanup' in cleanup.stderr
    assert all((path.exists() for path in owned_paths))
    assert all((item['status'] == 'COMMITTED' for item in manifest(evidence)['profiles']))
    assert extra.exists()

def test_recover_preserves_preexisting_environment_drift_after_partial_cleanup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    evidence, home, campaign, _ = setup(tmp_path)
    assert run(evidence, home, campaign, 'create').returncode == 0
    changed_config, cache_entry = _apply_external_environment_drift(home)
    monkeypatch.setenv('SUBAGENTS_DISPATCH_CALIBRATION_CRASH_AT', 'after_profile_candidate_cleanup_unlink')
    crashed = run(evidence, home, campaign, 'cleanup')
    assert crashed.returncode == 86
    monkeypatch.delenv('SUBAGENTS_DISPATCH_CALIBRATION_CRASH_AT')
    recovered = run(evidence, home, campaign, 'recover')
    assert recovered.returncode == 0, recovered.stderr
    assert all((item['status'] == 'CLEANED' for item in manifest(evidence)['profiles']))
    assert list((home / 'agents').glob('subagents_dispatch_calibration_*.toml')) == []
    assert (home / 'config.toml').read_bytes() == changed_config
    assert cache_entry.read_text(encoding='utf-8') == '{"state":"external"}\n'

def test_cleanup_transaction_detects_environment_change_after_start(tmp_path: Path):
    evidence, home, campaign, _ = setup(tmp_path)
    assert run(evidence, home, campaign, 'create').returncode == 0
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
    try:
        import calibration_profiles as profiles
    finally:
        sys.path.pop(0)
    baseline = profiles._cleanup_transaction_baseline(home, manifest(evidence))
    (home / 'config.toml').write_text('model = "changed-during-cleanup"\nmodel_provider = "custom"\n', encoding='utf-8')
    with pytest.raises(SystemExit, match='config_sha256'):
        profiles._verify_environment_baseline(home, baseline, set())
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import calibration_profiles as profiles
sys.path.pop(0)

def test_environment_snapshot_hashes_regular_file_content(tmp_path: Path):
    root = tmp_path / 'cache'
    root.mkdir()
    payload = root / 'payload.txt'
    payload.write_text('alpha', encoding='utf-8')
    before = profiles._path_inventory(root)
    payload.write_text('beta', encoding='utf-8')
    after = profiles._path_inventory(root)
    assert before != after
    entry = next((item for item in before if item['path'] == 'payload.txt'))
    assert entry['type'] == 'file'
    assert len(entry['sha256']) == 64

@pytest.mark.skipif(os.name == 'nt', reason='symlink creation is not guaranteed on Windows runners')
def test_environment_snapshot_records_symlink_without_following_it(tmp_path: Path):
    root = tmp_path / 'cache'
    version = root / 'openai-bundled' / 'chrome' / '123'
    version.mkdir(parents=True)
    (version / 'payload.txt').write_text('keep', encoding='utf-8')
    latest = version.parent / 'latest'
    latest.symlink_to('123', target_is_directory=True)
    snapshot = profiles._path_inventory(root)
    link = next((item for item in snapshot if item['path'] == 'openai-bundled/chrome/latest'))
    assert link == {'path': 'openai-bundled/chrome/latest', 'type': 'symlink', 'target': '123'}
    assert all((item['path'] != 'openai-bundled/chrome/latest/payload.txt' for item in snapshot))

@pytest.mark.skipif(os.name == 'nt', reason='symlink creation is not guaranteed on Windows runners')
def test_environment_snapshot_detects_symlink_target_change(tmp_path: Path):
    root = tmp_path / 'cache'
    chrome = root / 'openai-bundled' / 'chrome'
    (chrome / '123').mkdir(parents=True)
    (chrome / '124').mkdir()
    latest = chrome / 'latest'
    latest.symlink_to('123', target_is_directory=True)
    before = profiles._path_inventory(root)
    latest.unlink()
    latest.symlink_to('124', target_is_directory=True)
    after = profiles._path_inventory(root)
    assert before != after

@pytest.mark.skipif(os.name == 'nt', reason='symlink creation is not guaranteed on Windows runners')
def test_profile_only_create_preserves_preexisting_plugin_cache_symlink(tmp_path: Path):
    sys.path.insert(0, str(ROOT / 'tests'))
    try:
        from test_calibration_profiles import manifest, run, setup
    finally:
        sys.path.pop(0)
    evidence, home, campaign_path, _ = setup(tmp_path)
    cache = home / 'plugins' / 'cache'
    version = cache / 'openai-bundled' / 'chrome' / '123'
    version.mkdir(parents=True)
    payload = version / 'payload.txt'
    payload.write_text('keep', encoding='utf-8')
    latest = version.parent / 'latest'
    latest.symlink_to('123', target_is_directory=True)
    before = profiles._path_inventory(cache)
    created = run(evidence, home, campaign_path, 'create')
    assert created.returncode == 0, created.stderr
    assert created.stdout.strip() == 'NEW TASK REQUIRED: YES'
    assert profiles._path_inventory(cache) == before
    assert os.readlink(latest) == '123'
    assert payload.read_text(encoding='utf-8') == 'keep'
    owned = manifest(evidence)
    assert owned['schema_version'] == 5
    assert len(owned['profiles']) == 2
    assert all((item['status'] == 'COMMITTED' for item in owned['profiles']))

def test_environment_snapshot_manifest_schema_is_current():
    assert profiles.MANIFEST_SCHEMA == 5
    assert profiles._core.MANIFEST_SCHEMA == 5
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import calibration_profiles_core as core
sys.path.pop(0)
TASK_ID = '019ffd2d-2c2e-7330-9c22-1e5868987b9f'
OTHER_ID = '11111111-1111-4111-8111-111111111111'

def session_meta(thread_id: str) -> dict:
    return {'type': 'session_meta', 'payload': {'id': thread_id}}

def turn_context() -> dict:
    return {'type': 'turn_context', 'payload': {'model': 'test'}}

def host_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, records: list[dict]) -> tuple[Path, Path]:
    codex_home = tmp_path / '.codex'
    sessions = codex_home / 'sessions' / '2026' / '08' / '14'
    sessions.mkdir(parents=True)
    rollout = sessions / f'rollout-test-{TASK_ID}.jsonl'
    raw = ''.join((json.dumps(record) + '\n' for record in records)).encode('utf-8')
    rollout.write_bytes(raw)
    evidence = tmp_path / 'host-home-evidence.json'
    evidence.write_text(json.dumps({'active_codex_home': str(codex_home), 'provisioning_rollout_path': str(rollout), 'provisioning_rollout_sha256': hashlib.sha256(raw).hexdigest()}), encoding='utf-8')
    monkeypatch.setattr(core, '_normal_codex_home', lambda: codex_home.resolve())
    return (codex_home.resolve(), evidence)

def _calibration_host_session_identity__validate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, records: list[dict]) -> dict[str, str]:
    codex_home, evidence = host_evidence(tmp_path, monkeypatch, records)
    return core._host_home_identity(codex_home, evidence, TASK_ID, require_active_task=False)

def test_duplicate_canonical_session_meta_is_valid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    result = _calibration_host_session_identity__validate(tmp_path, monkeypatch, [session_meta(TASK_ID), turn_context(), session_meta(TASK_ID), turn_context()])
    assert result['active_codex_home'].endswith('.codex')

def test_later_different_session_meta_does_not_redefine_canonical_identity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _calibration_host_session_identity__validate(tmp_path, monkeypatch, [session_meta(TASK_ID), turn_context(), session_meta(OTHER_ID), turn_context()])

def test_wrong_first_session_meta_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    with pytest.raises(SystemExit, match='does not identify the preparation task'):
        _calibration_host_session_identity__validate(tmp_path, monkeypatch, [session_meta(OTHER_ID), turn_context(), session_meta(TASK_ID)])

def test_missing_session_meta_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    with pytest.raises(SystemExit, match='does not identify the preparation task'):
        _calibration_host_session_identity__validate(tmp_path, monkeypatch, [turn_context()])

def test_missing_turn_context_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    with pytest.raises(SystemExit, match='does not identify the preparation task'):
        _calibration_host_session_identity__validate(tmp_path, monkeypatch, [session_meta(TASK_ID), session_meta(TASK_ID)])

def test_malformed_session_meta_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    with pytest.raises(SystemExit, match='session_meta is incomplete'):
        _calibration_host_session_identity__validate(tmp_path, monkeypatch, [{'type': 'session_meta', 'payload': {}}, turn_context()])
ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / 'scripts' / 'validate-experiment-campaign.py'
POLICY = json.loads((ROOT / 'contracts' / 'policy.json').read_text(encoding='utf-8'))
ROLES = ('worker', 'solver', 'investigator', 'advisor')
sys.path.insert(0, str(ROOT / 'scripts'))
from calibration_profile_contract import materialized_agent_type, role_contract_digest
from calibration_profiles import _load_policy, _profile_records
sys.path.pop(0)

def head() -> str:
    return subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip()

def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()

def profile(role: str) -> dict:
    path = ROOT / 'agent-profiles' / POLICY['roles'][role]['profile_file']
    return tomllib.loads(path.read_text(encoding='utf-8'))

def contract(role: str) -> str:
    item = profile(role)
    return role_contract_digest(role, item['description'], item['developer_instructions'], POLICY['roles'][role]['mutation_authority'])

def arm(role: str, campaign_id: str, route_id: str, challenger: bool) -> dict:
    current = POLICY['roles'][role]
    model = 'gpt-5.6-terra' if challenger else current['model']
    effort = 'high' if challenger else current['effort']
    return {'id': route_id, 'semantic_role': role, 'model': model, 'effort': effort, 'configured_model': model, 'configured_effort': effort, 'materialized_agent_type': materialized_agent_type(campaign_id, role, route_id), 'role_contract_digest': contract(role), 'mutation_authority': current['mutation_authority']}

def campaign(role: str) -> dict:
    campaign_id = f'{role}-calibration-fixture'
    task = f'Exercise one bounded {role} responsibility.'
    packet = f'OBJECTIVE\nBounded {role} responsibility.\nRETURN\nEvidence.'
    return {'schema_version': '2.0', 'campaign_id': campaign_id, 'stage': 'exploratory', 'materialization_mode': 'profile_only', 'model_provider_control': 'openai', 'plugin_candidate_sha': head(), 'host_target': {'product': 'Codex', 'version': 'fixture', 'platform': 'fixture'}, 'repeat_policy': {'minimum_completed_per_arm': 1, 'ordering': 'interleaved', 'fixed_order_reason': None}, 'assurance_requirements': {'claim_kind': 'model_effort', 'required': ['route', 'permission_state'], 'allow_unknown': ['permission_provenance']}, 'experiment': {'type': 'role_calibration', 'policy_promotion': False, 'promotion_criteria_ref': None, 'roles': [{'role': role, 'contract_ref': f'contracts/routing.md#{role}', 'control': arm(role, campaign_id, 'current', False), 'challengers': [arm(role, campaign_id, 'terra-high', True)]}]}, 'workloads': [{'id': f'{role}-fixture', 'calibration_role': role, 'responsibility_packet_sha256': digest(packet), 'responsibility_packet_ref': f'fixture:{role}', 'repository_url': 'https://example.invalid/repository.git', 'base_revision': 'b' * 40, 'source_task_ref': None, 'task_text': task, 'task_sha256': digest(task), 'reset_procedure': ['reset immutable fixture'], 'acceptance': {'rubric_id': 'fixture-v1', 'oracle_kind': 'deterministic', 'verification': ['inspect expected fixture']}, 'controls': {'main_session_route_fingerprint': 'main-v1', 'permissions_fingerprint': 'permissions-v1', 'tool_surface_fingerprint': 'tools-v1', 'project_rule_refs': []}}]}

def _five_role_calibration__validate(tmp_path: Path, payload: dict) -> subprocess.CompletedProcess[str]:
    path = tmp_path / 'campaign.json'
    path.write_text(json.dumps(payload), encoding='utf-8')
    return subprocess.run([sys.executable, str(VALIDATOR), str(path), '--json'], cwd=ROOT, text=True, capture_output=True)

@pytest.mark.parametrize('role', ROLES)
def test_non_reader_role_uses_exact_canonical_contract(tmp_path: Path, role: str):
    payload = campaign(role)
    result = _five_role_calibration__validate(tmp_path, payload)
    assert result.returncode == 0, result.stderr
    records, contract_data = _profile_records(payload, _load_policy())
    assert len(records) == 2
    assert contract_data['digest'] == contract(role)
    canonical = profile(role)
    for record in records:
        generated = tomllib.loads(record['profile_bytes'].decode())
        assert generated['description'] == canonical['description']
        assert generated['developer_instructions'] == canonical['developer_instructions']
        assert generated['name'] == record['materialized_agent_type']
        assert generated['model'] == record['configured_model']
        assert generated['model_reasoning_effort'] == record['configured_effort']

@pytest.mark.parametrize('role', ROLES)
def test_non_reader_challenger_cannot_change_authority(tmp_path: Path, role: str):
    payload = campaign(role)
    challenger = payload['experiment']['roles'][0]['challengers'][0]
    challenger['mutation_authority'] = 'none' if challenger['mutation_authority'] != 'none' else 'bounded-source-write'
    result = _five_role_calibration__validate(tmp_path, payload)
    assert result.returncode != 0
    assert 'changes mutation_authority' in result.stderr

def test_profile_only_campaign_is_one_role(tmp_path: Path):
    payload = campaign('worker')
    payload['experiment']['roles'].append(campaign('solver')['experiment']['roles'][0])
    result = _five_role_calibration__validate(tmp_path, payload)
    assert result.returncode != 0
    assert 'requires exactly one semantic role' in result.stderr
