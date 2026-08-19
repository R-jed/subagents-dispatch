from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import importlib.util
import os
import time
import pytest
ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT
_install_agents__INSTALLER = PLUGIN / 'scripts' / 'install-agents.py'
PROFILE_SOURCE = PLUGIN / 'agent-profiles'
_install_agents__POLICY = json.loads((PLUGIN / 'contracts' / 'policy.json').read_text())
CURRENT_FILES = tuple((spec['profile_file'] for spec in _install_agents__POLICY['roles'].values()))
CURRENT_MANIFEST = '.subagents-dispatch-agents.json'
CURRENT_LOCK = '.subagents-dispatch-agents.lock'

def _install_agents__run(home: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(_install_agents__INSTALLER), '--codex-home', str(home), *extra], cwd=ROOT, text=True, capture_output=True, check=False)

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def state(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob('*') if path.is_file()}

def test_fresh_install_creates_only_current_managed_profiles(tmp_path: Path):
    home = tmp_path / 'codex-home'
    result = _install_agents__run(home)
    assert result.returncode == 0, result.stderr
    assert {p.name for p in (home / 'agents').glob('*.toml')} == set(CURRENT_FILES)
    for filename in CURRENT_FILES:
        assert (home / 'agents' / filename).read_bytes() == (PROFILE_SOURCE / filename).read_bytes()
    manifest = json.loads((home / CURRENT_MANIFEST).read_text())
    assert (home / CURRENT_LOCK).read_bytes() == b'\x00'
    assert manifest['schema_version'] == 1
    assert manifest['managed_by'] == 'subagents-dispatch'
    assert set(manifest['profile_hashes']) == set(CURRENT_FILES)

def test_symlinked_codex_home_is_rejected_without_writing_target(tmp_path: Path):
    real = tmp_path / 'real'
    real.mkdir()
    link = tmp_path / 'link'
    link.symlink_to(real, target_is_directory=True)
    before = state(real)
    result = _install_agents__run(link)
    assert result.returncode != 0
    assert 'Refusing symlinked Codex home' in result.stderr
    assert state(real) == before

def test_check_is_non_mutating_and_repeat_install_is_noop(tmp_path: Path):
    home = tmp_path / 'codex-home'
    assert _install_agents__run(home).returncode == 0
    before = state(home)
    check = _install_agents__run(home, '--check')
    assert check.returncode == 0, check.stderr
    assert 'CHECK PASSED' in check.stdout
    assert state(home) == before
    repeat = _install_agents__run(home)
    assert repeat.returncode == 0, repeat.stderr
    assert 'no changes made' in repeat.stdout
    assert state(home) == before

def test_modified_current_profile_is_not_overwritten_without_current_ownership(tmp_path: Path):
    home = tmp_path / 'codex-home'
    assert _install_agents__run(home).returncode == 0
    profile = home / 'agents' / _install_agents__POLICY['roles']['solver']['profile_file']
    profile.write_bytes(profile.read_bytes() + b'\n# user change\n')
    (home / CURRENT_MANIFEST).unlink()
    before = profile.read_bytes()
    result = _install_agents__run(home)
    assert result.returncode != 0
    assert 'not proven unchanged' in result.stderr
    assert profile.read_bytes() == before

def test_previous_current_profile_can_upgrade_with_exact_current_manifest(tmp_path: Path):
    home = tmp_path / 'codex-home'
    assert _install_agents__run(home).returncode == 0
    profile = home / 'agents' / _install_agents__POLICY['roles']['worker']['profile_file']
    previous = profile.read_bytes() + b'\n# previous managed generation\n'
    profile.write_bytes(previous)
    manifest_path = home / CURRENT_MANIFEST
    manifest = json.loads(manifest_path.read_text())
    manifest['profile_hashes'][profile.name] = sha(previous)
    manifest_path.write_text(json.dumps(manifest))
    result = _install_agents__run(home)
    assert result.returncode == 0, result.stderr
    assert profile.read_bytes() == (PROFILE_SOURCE / profile.name).read_bytes()

def test_current_manifest_can_add_missing_managed_profile_without_touching_existing_profiles(tmp_path: Path):
    home = tmp_path / 'codex-home'
    agents = home / 'agents'
    agents.mkdir(parents=True)
    missing = _install_agents__POLICY['roles']['solver']['profile_file']
    existing_files = [name for name in CURRENT_FILES if name != missing]
    hashes = {}
    for filename in existing_files:
        data = (PROFILE_SOURCE / filename).read_bytes()
        (agents / filename).write_bytes(data)
        hashes[filename] = sha(data)
    (home / CURRENT_MANIFEST).write_text(json.dumps({'schema_version': 1, 'managed_by': 'subagents-dispatch', 'profile_hashes': hashes}))
    before = {filename: (agents / filename).read_bytes() for filename in existing_files}
    result = _install_agents__run(home)
    assert result.returncode == 0, result.stderr
    assert (agents / missing).read_bytes() == (PROFILE_SOURCE / missing).read_bytes()
    assert {filename: (agents / filename).read_bytes() for filename in existing_files} == before
    assert _install_agents__run(home, '--check').returncode == 0

def test_unrelated_agent_profiles_are_preserved(tmp_path: Path):
    home = tmp_path / 'codex-home'
    agents = home / 'agents'
    agents.mkdir(parents=True)
    unrelated = agents / 'my-custom-agent.toml'
    unrelated.write_text('name = "my_custom_agent"\nmodel = "custom"\n')
    before = unrelated.read_bytes()
    result = _install_agents__run(home)
    assert result.returncode == 0, result.stderr
    assert unrelated.read_bytes() == before
    assert all(((agents / filename).is_file() for filename in CURRENT_FILES))
    assert (home / CURRENT_MANIFEST).is_file()

def test_exact_current_profiles_can_be_adopted(tmp_path: Path):
    home = tmp_path / 'codex-home'
    agents = home / 'agents'
    agents.mkdir(parents=True)
    for filename in CURRENT_FILES:
        (agents / filename).write_bytes((PROFILE_SOURCE / filename).read_bytes())
    result = _install_agents__run(home)
    assert result.returncode == 0, result.stderr
    assert (home / CURRENT_MANIFEST).exists()
    assert _install_agents__run(home, '--check').returncode == 0

def test_check_missing_home_does_not_create_it(tmp_path: Path):
    home = tmp_path / 'missing'
    result = _install_agents__run(home, '--check')
    assert result.returncode != 0
    assert not home.exists()

def test_not_installed_guidance_matches_automatic_first_use_restart_contract(tmp_path: Path):
    home = tmp_path / 'codex-home'
    home.mkdir()
    result = _install_agents__run(home, '--check')
    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert 'Not installed' in combined
    assert 'provision these plugin-owned profiles automatically' in combined
    assert 'fresh Codex task/session before spawn' in combined
    assert 'ask permission' not in combined
ROOT = Path(__file__).resolve().parents[1]
_installer_concurrency__INSTALLER = ROOT / 'scripts' / 'install-agents.py'
LEGACY_LOCK = '.codex-delegate-agents.lock'
CURRENT_LOCK = '.subagents-dispatch-agents.lock'

def load_installer():
    scripts_dir = str(_installer_concurrency__INSTALLER.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location('subagents_dispatch_installer', _installer_concurrency__INSTALLER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def _installer_concurrency__run_installer(home: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(_installer_concurrency__INSTALLER), '--codex-home', str(home), *extra], cwd=ROOT, text=True, capture_output=True, check=False)

def create_minimal_legacy_state(home: Path) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / '.codex-delegate-agents.json').write_text(json.dumps({'schema_version': 1, 'managed_by': 'codex-delegate', 'profile_hashes': {}}), encoding='utf-8')
    (home / LEGACY_LOCK).write_bytes(b'\x00')

def start_real_lock_holder(lock_path: Path) -> subprocess.Popen[str]:
    code = '\nimport os\nfrom pathlib import Path\nimport sys\npath = Path(sys.argv[1])\npath.parent.mkdir(parents=True, exist_ok=True)\nfd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)\nif os.fstat(fd).st_size == 0:\n    os.write(fd, b"\\0")\n    os.fsync(fd)\nif os.name == "nt":\n    import msvcrt\n    os.lseek(fd, 0, os.SEEK_SET)\n    msvcrt.locking(fd, msvcrt.LK_LOCK, 1)\nelse:\n    import fcntl\n    fcntl.flock(fd, fcntl.LOCK_EX)\nprint("LOCKED", flush=True)\nsys.stdin.readline()\nif os.name == "nt":\n    os.lseek(fd, 0, os.SEEK_SET)\n    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)\nelse:\n    fcntl.flock(fd, fcntl.LOCK_UN)\nos.close(fd)\n'
    proc = subprocess.Popen([sys.executable, '-c', code, str(lock_path)], cwd=ROOT, text=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdout is not None
    assert proc.stdout.readline().strip() == 'LOCKED'
    return proc

def test_real_legacy_lock_holder_blocks_new_migrator(tmp_path: Path):
    """Old-generation lock ownership must serialize the new migrator."""
    home = tmp_path / 'codex-home'
    create_minimal_legacy_state(home)
    holder = start_real_lock_holder(home / LEGACY_LOCK)
    migrator = subprocess.Popen([sys.executable, str(_installer_concurrency__INSTALLER), '--codex-home', str(home), '--migrate-legacy'], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        time.sleep(0.4)
        assert migrator.poll() is None, 'migrator bypassed the held legacy OS lock'
        assert holder.stdin is not None
        holder.stdin.write('release\n')
        holder.stdin.flush()
        holder_out, holder_err = holder.communicate(timeout=10)
        assert holder.returncode == 0, holder_out + holder_err
        out, err = migrator.communicate(timeout=30)
        assert migrator.returncode == 0, out + err
    finally:
        if holder.poll() is None:
            holder.kill()
        if migrator.poll() is None:
            migrator.kill()

def test_both_generation_lock_files_remain_after_migration(tmp_path: Path):
    home = tmp_path / 'codex-home'
    create_minimal_legacy_state(home)
    result = _installer_concurrency__run_installer(home, '--migrate-legacy')
    assert result.returncode == 0, result.stdout + result.stderr
    assert (home / LEGACY_LOCK).exists()
    assert (home / CURRENT_LOCK).exists()
    check = _installer_concurrency__run_installer(home, '--check')
    assert check.returncode == 0, check.stdout + check.stderr

def test_profile_drift_after_manifest_publication_preserves_external_drift_and_backup(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    home = tmp_path / 'codex-home'
    installer = load_installer()
    installer.install(home, False)
    capsys.readouterr()
    profile_name = installer.PROFILE_FILES[0]
    profile = home / 'agents' / profile_name
    previous_profile = profile.read_bytes() + b'\n# previous managed generation\n'
    profile.write_bytes(previous_profile)
    manifest_path = home / installer.MANIFEST_NAME
    previous_manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    previous_manifest['profile_hashes'][profile_name] = installer.sha256_bytes(previous_profile)
    manifest_path.write_text(json.dumps(previous_manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    previous_manifest_bytes = manifest_path.read_bytes()
    original_write_manifest = installer.write_manifest
    expected_drift = (installer.PROFILE_SOURCE / profile_name).read_bytes() + b'\n# external publication-window drift\n'

    def publish_then_drift(path: Path, payload: dict) -> None:
        original_write_manifest(path, payload)
        profile.write_bytes(profile.read_bytes() + b'\n# external publication-window drift\n')
    installer.write_manifest = publish_then_drift
    with pytest.raises(SystemExit, match='ROLLBACK INCOMPLETE'):
        installer.install(home, False)
    output = capsys.readouterr().out
    assert 'Managed Agent profiles installed under:' not in output
    assert profile.read_bytes() == expected_drift
    assert manifest_path.read_bytes() == previous_manifest_bytes
    backups = list(profile.parent.glob(f'.{profile.name}.backup-*'))
    assert len(backups) == 1
    assert backups[0].read_bytes() == previous_profile
    for filename in installer.PROFILE_FILES:
        if filename == profile_name:
            continue
        assert (home / 'agents' / filename).read_bytes() == (installer.PROFILE_SOURCE / filename).read_bytes()

@pytest.mark.skipif(not hasattr(os, 'fork'), reason='fault-injection harness requires fork')
def test_failed_installer_cannot_rollback_a_successful_peer(tmp_path: Path):
    home = tmp_path / 'codex-home'
    installer = load_installer()
    ready_read, ready_write = os.pipe()
    release_read, release_write = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(ready_read)
        os.close(release_write)

        def fail_after_profile_mutation(path, payload):
            os.write(ready_write, b'1')
            os.read(release_read, 1)
            raise RuntimeError('injected failure after profile mutation')
        installer.write_manifest = fail_after_profile_mutation
        try:
            installer.install(home, False)
        except RuntimeError:
            os._exit(23)
        os._exit(24)
    os.close(ready_write)
    os.close(release_read)
    os.read(ready_read, 1)
    peer = subprocess.Popen([sys.executable, str(_installer_concurrency__INSTALLER), '--codex-home', str(home)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(0.2)
    assert peer.poll() is None
    os.write(release_write, b'1')
    _, fault_status = os.waitpid(pid, 0)
    peer_stdout, peer_stderr = peer.communicate(timeout=10)
    assert os.waitstatus_to_exitcode(fault_status) == 23
    assert peer.returncode == 0, peer_stdout + peer_stderr
    check = _installer_concurrency__run_installer(home, '--check')
    assert check.returncode == 0, check.stdout + check.stderr

def test_check_on_fresh_home_reports_not_installed_instead_of_lock_error(tmp_path: Path):
    """A --check on a never-provisioned install must diagnose "not installed", not a lock error."""
    home = tmp_path / 'codex-home'
    home.mkdir()
    result = _installer_concurrency__run_installer(home, '--check')
    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert 'Could not open installer lock' not in combined
    assert 'Not installed' in combined

def test_check_with_agents_dir_but_missing_profiles_reports_not_installed(tmp_path: Path):
    """A present agents dir without our profiles is still "not installed", not a lock error."""
    home = tmp_path / 'codex-home'
    home.mkdir()
    (home / 'agents').mkdir()
    result = _installer_concurrency__run_installer(home, '--check')
    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert 'Could not open installer lock' not in combined
    assert 'Not installed' in combined
ROOT = Path(__file__).resolve().parents[1]
_installer_safety__INSTALLER = ROOT / 'scripts' / 'install-agents.py'

def _installer_safety__run_installer(target: Path, *extra: str):
    return subprocess.run([sys.executable, str(_installer_safety__INSTALLER), '--codex-home', str(target), *extra], capture_output=True, text=True)

@pytest.mark.parametrize(
    ("filename", "expected_message"),
    [
        ("subagents-dispatch-worker.toml", "Refusing to overwrite"),
        ("my-custom-worker.toml", "reserved current role name"),
    ],
    ids=["same-filename", "reserved-role-name"],
)
def test_installer_refuses_conflicting_reserved_profile(
    tmp_path: Path, filename: str, expected_message: str
):
    target = tmp_path / "codex-home"
    agents = target / "agents"
    agents.mkdir(parents=True)
    (agents / filename).write_text(
        'name = "subagents_dispatch_worker"\n'
        'model = "gpt-5.6-terra"\n'
        'developer_instructions = "custom"\n'
    )
    result = _installer_safety__run_installer(target)
    assert result.returncode != 0
    assert expected_message in result.stdout + result.stderr


def test_installer_refuses_symlinked_lock(tmp_path):
    target = tmp_path / 'codex-home'
    target.mkdir()
    external = tmp_path / 'external-lock'
    external.write_bytes(b'\x00')
    (target / '.subagents-dispatch-agents.lock').symlink_to(external)
    result = _installer_safety__run_installer(target)
    assert result.returncode != 0
    assert 'Refusing symlinked installer lock' in result.stdout + result.stderr

def test_installer_is_idempotent_and_check_is_non_mutating(tmp_path):
    target = tmp_path / 'codex-home'
    first = _installer_safety__run_installer(target)
    assert first.returncode == 0, first.stderr
    before = {path.name: path.read_bytes() for path in target.rglob('*') if path.is_file()}
    check = _installer_safety__run_installer(target, '--check')
    second = _installer_safety__run_installer(target)
    after = {path.name: path.read_bytes() for path in target.rglob('*') if path.is_file()}
    assert check.returncode == 0, check.stderr
    assert second.returncode == 0, second.stderr
    assert before == after
ROOT = Path(__file__).resolve().parents[1]
_uninstall_agents__INSTALLER = ROOT / 'scripts' / 'install-agents.py'
UNINSTALLER = ROOT / 'scripts' / 'uninstall-agents.py'
_uninstall_agents__POLICY = json.loads((ROOT / 'contracts' / 'policy.json').read_text(encoding='utf-8'))
PROFILE_FILES = tuple((spec['profile_file'] for spec in _uninstall_agents__POLICY['roles'].values()))
MANIFEST = '.subagents-dispatch-agents.json'
LOCK = '.subagents-dispatch-agents.lock'

def _uninstall_agents__run(script: Path, home: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(script), '--codex-home', str(home), *extra], cwd=ROOT, text=True, capture_output=True, check=False)

def install(home: Path) -> None:
    result = _uninstall_agents__run(_uninstall_agents__INSTALLER, home)
    assert result.returncode == 0, result.stdout + result.stderr

def test_uninstall_removes_only_exact_owned_profiles_and_manifest(tmp_path: Path):
    home = tmp_path / 'codex-home'
    install(home)
    unrelated = home / 'agents' / 'my-agent.toml'
    unrelated.write_text('name = "my_agent"\nmodel = "custom"\n', encoding='utf-8')
    before = unrelated.read_bytes()
    result = _uninstall_agents__run(UNINSTALLER, home)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'UNINSTALL COMPLETE' in result.stdout
    assert all((not (home / 'agents' / filename).exists() for filename in PROFILE_FILES))
    assert not (home / MANIFEST).exists()
    assert (home / LOCK).is_file()
    assert unrelated.read_bytes() == before

def test_modified_owned_profile_blocks_entire_uninstall(tmp_path: Path):
    home = tmp_path / 'codex-home'
    install(home)
    modified = home / 'agents' / PROFILE_FILES[2]
    modified.write_bytes(modified.read_bytes() + b'\n# user change\n')
    before = {filename: (home / 'agents' / filename).read_bytes() for filename in PROFILE_FILES}
    manifest_before = (home / MANIFEST).read_bytes()
    result = _uninstall_agents__run(UNINSTALLER, home)
    assert result.returncode != 0
    assert 'changed after the ownership manifest was written' in result.stderr
    assert {filename: (home / 'agents' / filename).read_bytes() for filename in PROFILE_FILES} == before
    assert (home / MANIFEST).read_bytes() == manifest_before

def test_reserved_paths_without_manifest_are_not_claimed_or_deleted(tmp_path: Path):
    home = tmp_path / 'codex-home'
    agents = home / 'agents'
    agents.mkdir(parents=True)
    target = agents / PROFILE_FILES[0]
    target.write_text('name = "user_owned"\n', encoding='utf-8')
    before = target.read_bytes()
    result = _uninstall_agents__run(UNINSTALLER, home)
    assert result.returncode != 0
    assert 'ownership metadata is missing' in result.stderr
    assert target.read_bytes() == before
    assert not (home / MANIFEST).exists()

def test_symlinked_agents_directory_is_rejected_without_touching_target(tmp_path: Path):
    home = tmp_path / 'codex-home'
    home.mkdir()
    external = tmp_path / 'external-agents'
    external.mkdir()
    marker = external / PROFILE_FILES[0]
    marker.write_text('name = "outside"\n', encoding='utf-8')
    try:
        (home / 'agents').symlink_to(external, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f'symlink creation is unavailable on this runner: {exc}')
    result = _uninstall_agents__run(UNINSTALLER, home)
    assert result.returncode != 0
    assert 'Refusing symlinked agents directory' in result.stderr
    assert marker.read_text(encoding='utf-8') == 'name = "outside"\n'
    assert not (home / MANIFEST).exists()

def test_uninstall_can_finish_after_one_owned_profile_is_already_missing(tmp_path: Path):
    home = tmp_path / 'codex-home'
    install(home)
    missing = home / 'agents' / PROFILE_FILES[0]
    missing.unlink()
    result = _uninstall_agents__run(UNINSTALLER, home)
    assert result.returncode == 0, result.stdout + result.stderr
    assert all((not (home / 'agents' / filename).exists() for filename in PROFILE_FILES))
    assert not (home / MANIFEST).exists()

def test_uninstall_of_absent_install_is_non_mutating(tmp_path: Path):
    missing_home = tmp_path / 'missing'
    result = _uninstall_agents__run(UNINSTALLER, missing_home)
    assert result.returncode == 0
    assert 'not installed; no changes made' in result.stdout
    assert not missing_home.exists()
    unrelated_home = tmp_path / 'unrelated-home'
    (unrelated_home / 'agents').mkdir(parents=True)
    unrelated = unrelated_home / 'agents' / 'other.toml'
    unrelated.write_text('name = "other"\n', encoding='utf-8')
    before = unrelated.read_bytes()
    result = _uninstall_agents__run(UNINSTALLER, unrelated_home)
    assert result.returncode == 0
    assert unrelated.read_bytes() == before
    assert not (unrelated_home / LOCK).exists()
ROOT = Path(__file__).resolve().parents[1]

def test_uninstall_docs_allow_only_registration_semantic_delta_in_config():
    installation = (ROOT / 'docs' / 'plugin-installation.md').read_text(encoding='utf-8')
    release = (ROOT / 'docs' / 'release-checklist.md').read_text(encoding='utf-8')
    assert 'may update `config.toml` only to persist removal of this Plugin and Marketplace registration' in installation
    assert 'unrelated configuration semantics and other Codex state must remain unchanged' in installation
    assert 'allow only the semantic delta required by the supported Plugin and Marketplace registration removal commands' in release
    assert 'all unrelated configuration semantics must remain unchanged' in release
    assert 'Uninstall does not edit `config.toml`' not in installation
    assert 'Confirm config.toml, credentials' not in release
