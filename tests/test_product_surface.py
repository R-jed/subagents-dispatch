from __future__ import annotations
import re
from pathlib import Path
import json
import tomllib
from urllib.parse import urlparse
import yaml
ROOT = Path(__file__).resolve().parents[1]
ACTIVE_FILES = [ROOT / 'README.md', ROOT / 'README_EN.md', ROOT / 'README_AI.md', *sorted((ROOT / 'docs').glob('*.md')), *sorted((ROOT / 'skills').glob('**/*.md')), *sorted((ROOT / 'skills').glob('**/*.yaml')), *sorted((ROOT / 'evals').glob('*.json')), *sorted((ROOT / 'scripts').glob('*.py'))]
FORBIDDEN_LITERAL_ENTRYPOINTS = ('$dispatch', '$doctor', '/subagents-dispatch:dispatch', '/subagents-dispatch:doctor')
FORBIDDEN_BARE_SLASH = re.compile('(?<![A-Za-z0-9_.-])/(?:dispatch|doctor)\\b')

def test_active_surfaces_do_not_publish_unverified_or_legacy_skill_entrypoints():
    violations: list[str] = []
    for path in ACTIVE_FILES:
        text = path.read_text(encoding='utf-8')
        for token in FORBIDDEN_LITERAL_ENTRYPOINTS:
            if token in text:
                violations.append(f'{path.relative_to(ROOT)} contains {token!r}')
        for match in FORBIDDEN_BARE_SLASH.finditer(text):
            violations.append(f'{path.relative_to(ROOT)} contains unverified bare App entry {match.group(0)!r}')
    assert not violations, 'Active product surfaces publish stale/unverified Skill entrypoints:\n' + '\n'.join(violations)

def test_active_surfaces_keep_explicit_skill_identity_and_human_ui_gate():
    release = (ROOT / 'docs' / 'release-checklist.md').read_text(encoding='utf-8')
    ai_reference = (ROOT / 'README_AI.md').read_text(encoding='utf-8')
    for skill_id in ['dispatch', 'preview', 'status', 'steer', 'takeover', 'doctor']:
        skill = (ROOT / 'skills' / skill_id / 'SKILL.md').read_text(encoding='utf-8')
        assert f'name: {skill_id}\n' in skill
    assert 'Direct human Codex App observation' in release
    assert 'cannot by itself close a Host/UI gate' in release
    assert 'record the exact rendered entry labels' in release
    assert 'post-selection presentation' in release
    assert 'Do not invent literal slash-command syntax' in release
    assert 'Do not invent a Codex App slash-command string' in ai_reference
ROOT = Path(__file__).resolve().parents[1]
INSTALL_DOC = ROOT / 'docs' / 'plugin-installation.md'
RELEASE = ROOT / 'docs' / 'release-checklist.md'
ARCHITECTURE = ROOT / 'docs' / 'architecture.md'
DOCTOR_SKILL = ROOT / 'skills' / 'doctor' / 'SKILL.md'
README_CN = ROOT / 'README.md'
README_EN = ROOT / 'README_EN.md'
README_AI = ROOT / 'README_AI.md'
REPO_ARCH = ROOT / 'docs' / 'repository-architecture.md'
CI = ROOT / '.github' / 'workflows' / 'ci.yml'
UNINSTALLER = ROOT / 'scripts' / 'uninstall-agents.py'
PLUGIN_REMOVE = 'codex plugin remove subagents-dispatch@subagents-dispatch'
MARKETPLACE_REMOVE = 'codex plugin marketplace remove subagents-dispatch'
DOCTOR_LAYERS = ['Plugin', 'Skills', 'Managed Agent profiles', 'Dispatch state', 'Codex Host', 'Runtime route', 'Effective permission state', 'Permission-source provenance']

def test_product_rc_has_one_ownership_aware_managed_profile_uninstaller():
    assert UNINSTALLER.is_file()
    install = INSTALL_DOC.read_text(encoding='utf-8')
    doctor = DOCTOR_SKILL.read_text(encoding='utf-8')
    ai = README_AI.read_text(encoding='utf-8')
    architecture = REPO_ARCH.read_text(encoding='utf-8')
    release = RELEASE.read_text(encoding='utf-8')
    for text in (install, doctor, ai, architecture, release):
        assert 'scripts/uninstall-agents.py' in text or '../../scripts/uninstall-agents.py' in text
    assert 'ownership-aware' in install
    assert 'ownership-aware' in doctor
    assert 'managed Agent profile removal' in ai
    assert 'managed Agent profile removal' in architecture
    assert 'ownership-aware managed Agent uninstall' in release

def test_public_uninstall_flow_removes_managed_profiles_before_plugin_registration():
    for path in (INSTALL_DOC, README_CN, README_EN):
        text = path.read_text(encoding='utf-8')
        plugin_index = text.index(PLUGIN_REMOVE)
        if path == INSTALL_DOC:
            cleanup_index = text.index('scripts/uninstall-agents.py')
        elif path == README_CN:
            cleanup_index = text.index('明确要求卸载 subagents-dispatch 的 managed profiles')
        else:
            cleanup_index = text.index('explicitly ask it to uninstall the subagents-dispatch managed profiles')
        assert cleanup_index < plugin_index
        assert MARKETPLACE_REMOVE in text

def test_public_uninstall_flow_does_not_publish_manual_managed_profile_rm():
    forbidden = ['rm ~/.codex/agents/subagents-dispatch-reader.toml', 'rm ~/.codex/agents/subagents-dispatch-worker.toml', 'rm ~/.codex/agents/subagents-dispatch-solver.toml', 'rm ~/.codex/agents/subagents-dispatch-investigator.toml', 'rm ~/.codex/agents/subagents-dispatch-advisor.toml', 'rm ~/.codex/.subagents-dispatch-agents.json']
    for path in (INSTALL_DOC, README_CN, README_EN, DOCTOR_SKILL):
        text = path.read_text(encoding='utf-8')
        for command in forbidden:
            assert command not in text

def test_doctor_product_docs_match_the_eight_layer_contract():
    for path in (INSTALL_DOC, ARCHITECTURE, REPO_ARCH):
        text = path.read_text(encoding='utf-8')
        assert 'exactly eight' in text
        assert 'exactly six' not in text
        for layer in DOCTOR_LAYERS:
            assert layer in text

def test_ci_runs_uninstall_reinstall_lifecycle_and_tag_parity_gate():
    text = CI.read_text(encoding='utf-8')
    assert 'python scripts/uninstall-agents.py --codex-home "$target"' in text
    assert 'managed Agent check unexpectedly passed after uninstall' in text
    assert text.count('python scripts/install-agents.py --codex-home "$target" --check') >= 3
    assert "startsWith(github.ref, 'refs/tags/')" in text
    assert 'test "$GITHUB_REF_NAME" = "v$version"' in text
ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT
_official_plugin_compliance__MANIFEST = PLUGIN_ROOT / '.codex-plugin' / 'plugin.json'
SKILLS_ROOT = PLUGIN_ROOT / 'skills'
_official_plugin_compliance__SKILL_IDS = ['dispatch', 'preview', 'status', 'steer', 'takeover', 'doctor']
POLICY = PLUGIN_ROOT / 'contracts' / 'policy.json'

def test_plugin_manifest_has_public_legal_links_and_stays_skills_only():
    payload = json.loads(_official_plugin_compliance__MANIFEST.read_text(encoding='utf-8'))
    interface = payload['interface']
    assert payload['name'] == 'subagents-dispatch'
    assert payload['skills'] == './skills/'
    for unsupported_component in ['mcpServers', 'apps', 'hooks']:
        assert unsupported_component not in payload
    for field, suffix in [('privacyPolicyURL', '/PRIVACY.md'), ('termsOfServiceURL', '/TERMS.md')]:
        parsed = urlparse(interface[field])
        assert parsed.scheme == 'https' and parsed.netloc
        assert parsed.path.endswith(suffix)
    assert (ROOT / 'PRIVACY.md').is_file()
    assert (ROOT / 'TERMS.md').is_file()

def test_plugin_starter_prompts_cover_all_skills_without_inventing_app_command_syntax():
    prompts = json.loads(_official_plugin_compliance__MANIFEST.read_text(encoding='utf-8'))['interface']['defaultPrompt']
    assert len(prompts) == len(_official_plugin_compliance__SKILL_IDS)
    for skill_id in _official_plugin_compliance__SKILL_IDS:
        assert any((skill_id.title() in prompt for prompt in prompts))
    assert all((len(prompt) <= 128 for prompt in prompts))
    for stale in ['$dispatch', '$doctor', '/dispatch', '/doctor', '/subagents-dispatch:']:
        assert all((stale not in prompt for prompt in prompts))

def test_openai_skill_metadata_uses_explicit_display_identity_and_explicit_only_policy():
    for skill_id in _official_plugin_compliance__SKILL_IDS:
        payload = yaml.safe_load((SKILLS_ROOT / skill_id / 'agents' / 'openai.yaml').read_text(encoding='utf-8'))
        action_name = skill_id.title()
        interface = payload['interface']
        assert interface['display_name'] == f'Subagents Dispatch: {action_name}'
        assert 25 <= len(interface['short_description']) <= 64
        assert action_name in interface['default_prompt']
        assert payload['policy']['allow_implicit_invocation'] is False
        for stale in ['$dispatch', '$doctor', '/dispatch', '/doctor', '/subagents-dispatch:']:
            assert stale not in interface['default_prompt']

def test_managed_agent_profiles_follow_policy_owned_native_shape():
    policy = json.loads(POLICY.read_text(encoding='utf-8'))
    profile_dir = PLUGIN_ROOT / 'agent-profiles'
    for role in policy['roles'].values():
        payload = tomllib.loads((profile_dir / role['profile_file']).read_text(encoding='utf-8'))
        assert payload['name'] == role['agent_type']
        assert isinstance(payload['description'], str) and payload['description'].strip()
        assert isinstance(payload['developer_instructions'], str) and payload['developer_instructions'].strip()
        assert payload['model'] == role['model']
        assert payload['model_reasoning_effort'] == role['effort']
        assert 'sandbox_mode' not in payload
ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT
PLUGIN = PLUGIN_ROOT / '.codex-plugin' / 'plugin.json'
MARKETPLACE = ROOT / '.agents' / 'plugins' / 'marketplace.json'
SKILLS_ROOT = PLUGIN_ROOT / 'skills'
_plugin_packaging__SKILL_IDS = {'dispatch', 'preview', 'status', 'steer', 'takeover', 'doctor'}
INSTALL_DOC = ROOT / 'docs' / 'plugin-installation.md'
PYTHON_RUNTIME_DOC = ROOT / 'docs' / 'python-runtime.md'
POLICY = PLUGIN_ROOT / 'contracts' / 'policy.json'
CANONICAL_MARKETPLACE = 'codex plugin marketplace add R-jed/subagents-dispatch'
PLUGIN_ADD = 'codex plugin add subagents-dispatch@subagents-dispatch'
UPGRADE = 'codex plugin marketplace upgrade subagents-dispatch'
PLUGIN_REMOVE = 'codex plugin remove subagents-dispatch@subagents-dispatch'
MARKETPLACE_REMOVE = 'codex plugin marketplace remove subagents-dispatch'

def test_plugin_manifest_and_marketplace_use_canonical_identity():
    payload = json.loads(PLUGIN.read_text(encoding='utf-8'))
    version = payload['version']
    release_ref = f'v{version}'
    assert payload['name'] == 'subagents-dispatch'
    assert payload['skills'] == './skills/'
    assert payload['repository'] == 'https://github.com/R-jed/subagents-dispatch'
    assert payload['homepage'] == 'https://github.com/R-jed/subagents-dispatch#readme'
    assert payload['interface']['displayName'] == 'subagents-dispatch'
    assert payload['interface']['websiteURL'] == 'https://github.com/R-jed/subagents-dispatch'
    assert {path.name for path in SKILLS_ROOT.iterdir() if path.is_dir()} == _plugin_packaging__SKILL_IDS
    for skill_id in _plugin_packaging__SKILL_IDS:
        assert (SKILLS_ROOT / skill_id / 'SKILL.md').is_file()
    market = json.loads(MARKETPLACE.read_text(encoding='utf-8'))
    assert market == {'name': 'subagents-dispatch', 'interface': {'displayName': 'subagents-dispatch'}, 'plugins': [{'name': 'subagents-dispatch', 'source': {'source': 'url', 'url': 'https://github.com/R-jed/subagents-dispatch.git', 'ref': release_ref}, 'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_INSTALL'}, 'category': 'Productivity'}]}

def test_skill_ids_and_ui_names_are_explicit_and_distinct():
    for skill_id in _plugin_packaging__SKILL_IDS:
        root = SKILLS_ROOT / skill_id
        skill = (root / 'SKILL.md').read_text(encoding='utf-8')
        ui = (root / 'agents' / 'openai.yaml').read_text(encoding='utf-8')
        assert f'name: {skill_id}\n' in skill
        assert f'display_name: "Subagents Dispatch: {skill_id.title()}"' in ui
        assert 'allow_implicit_invocation: false' in ui

def test_plugin_starter_prompts_do_not_invent_host_command_syntax():
    payload = json.loads(PLUGIN.read_text(encoding='utf-8'))
    prompts = '\n'.join(payload['interface']['defaultPrompt'])
    for skill_id in _plugin_packaging__SKILL_IDS:
        assert skill_id.title() in prompts
    for stale in ['$dispatch', '$doctor', '/dispatch', '/doctor', '/subagents-dispatch:dispatch', '/subagents-dispatch:doctor']:
        assert stale not in prompts

def test_root_plugin_layout_and_canonical_ci_verifier_do_not_use_removed_subdirectory():
    assert PLUGIN.is_file()
    assert (ROOT / 'skills' / 'dispatch' / 'SKILL.md').is_file()
    stale = 'plugins/subagents-dispatch'
    path = ROOT / '.github' / 'workflows' / 'ci.yml'
    text = path.read_text(encoding='utf-8')
    assert stale not in text, f'{path} still targets the removed plugin subdirectory'
    assert '.codex-plugin/plugin.json' in text
    assert 'scripts/install-agents.py' in text

def test_plugin_brand_assets_and_supported_components():
    payload = json.loads(PLUGIN.read_text(encoding='utf-8'))
    interface = payload['interface']
    assert interface['brandColor'] == '#2563EB'
    for field in ['composerIcon', 'logo']:
        asset = PLUGIN_ROOT / interface[field].removeprefix('./')
        assert asset.is_file() and '<svg' in asset.read_text(encoding='utf-8')
    for unsupported in ['agents', 'hooks', 'mcpServers', 'apps']:
        assert unsupported not in payload
    for field in ['homepage', 'repository']:
        parsed = urlparse(payload[field])
        assert parsed.scheme == 'https' and parsed.netloc

def test_policy_contract_owns_the_five_packaged_profiles():
    policy = json.loads(POLICY.read_text(encoding='utf-8'))
    assert policy['schema_version'] == 7
    assert set(policy['roles']) == {'reader', 'worker', 'solver', 'investigator', 'advisor'}
    expected = {spec['profile_file'] for spec in policy['roles'].values()}
    assert len(expected) == 5
    assert {p.name for p in (PLUGIN_ROOT / 'agent-profiles').glob('*.toml')} == expected
    assert all((name.startswith('subagents-dispatch-') for name in expected))
    assert all((spec['agent_type'].startswith('subagents_dispatch_') for spec in policy['roles'].values()))

def test_third_party_mit_notice_is_packaged_without_repository_pointer():
    notice = PLUGIN_ROOT / 'THIRD_PARTY_NOTICES.md'
    assert notice.is_file()
    text = notice.read_text(encoding='utf-8')
    for phrase in ['MIT-licensed third-party material', 'Copyright (c) 2026 Zhijian AI / Dapeng', 'Permission is hereby granted', 'THE SOFTWARE IS PROVIDED "AS IS"']:
        assert phrase in text
    assert 'github.com/' not in text

def test_dispatch_skill_is_a_thin_adapter_to_canonical_contracts():
    text = (SKILLS_ROOT / 'dispatch' / 'SKILL.md').read_text(encoding='utf-8')
    for name in ['policy.json', 'routing.md', 'guardrails.md', 'state.md', 'team-plan.md', 'recovery.md', 'handoff.md', 'final-review.md', 'receipt.md']:
        assert f'../../contracts/{name}' in text
    assert '../../docs/python-runtime.md' in text
    assert 'Python 3.11+' in text

def test_doctor_reuses_supported_diagnostics_and_existing_installer():
    text = (SKILLS_ROOT / 'doctor' / 'SKILL.md').read_text(encoding='utf-8')
    for phrase in ['../../contracts/policy.json', '../../contracts/state.md', '../../contracts/guardrails.md', '../../docs/python-runtime.md', '../../scripts/doctor.py', '../../scripts/install-agents.py', '../../scripts/runtime-evidence.py']:
        assert phrase in text
    assert 'Diagnosis is read-only by default' in text
    assert 'explicit user intent' in text
    assert 'Do not edit Codex config files directly' in text
    assert '<python-3.11+> ../../scripts/inspect-agent-runtime.py' in text
    assert 'python ../../scripts/inspect-agent-runtime.py' not in text

def test_install_doc_contains_current_lifecycle_and_app_skill_menu_contract():
    text = INSTALL_DOC.read_text(encoding='utf-8')
    for phrase in [CANONICAL_MARKETPLACE, PLUGIN_ADD, '## Python helper prerequisite', 'Python 3.11 or newer', 'python-runtime.md', 'PYTHON_PREREQUISITE_UNMET', '## First delegated run', 'five managed custom-Agent profiles', 'automatically provisions', 'RESTART_REQUIRED', 'does not attempt to spawn', 'fresh Codex task/session', 'fails closed', '## Update', UPGRADE, '## Uninstall', PLUGIN_REMOVE, MARKETPLACE_REMOVE, 'six explicit Skill identities', 'Dispatch', 'Preview', 'Status', 'Steer', 'Takeover', 'Doctor', 'exact slash entry rendered by the App is a Host/UI fact']:
        assert phrase in text
    assert 'asks permission' not in text

def test_python_helper_runtime_declares_portable_resolution_and_ci_boundary():
    assert PYTHON_RUNTIME_DOC.is_file()
    text = PYTHON_RUNTIME_DOC.read_text(encoding='utf-8')
    for phrase in ['Python 3.11 or newer', 'python3', 'python', 'py -3.11', 'sys.executable', 'environment adaptation', 'PYTHON_PREREQUISITE_UNMET', 'actions/setup-python', 'real Codex App task shell']:
        assert phrase in text
    assert 'A single `command not found`' in text

def test_public_readmes_use_explicit_skill_names_without_inventing_exact_slash_entry():
    version = json.loads(PLUGIN.read_text(encoding='utf-8'))['version']
    for name in ['README.md', 'README_EN.md']:
        text = (ROOT / name).read_text(encoding='utf-8')
        assert version in text
        for skill_id in _plugin_packaging__SKILL_IDS:
            assert skill_id.title() in text
        assert CANONICAL_MARKETPLACE in text
        assert PLUGIN_ADD in text
        assert UPGRADE in text
        assert PLUGIN_REMOVE in text
        assert MARKETPLACE_REMOVE in text
        assert '$dispatch' not in text
        assert '$doctor' not in text
    ai = (ROOT / 'README_AI.md').read_text(encoding='utf-8')
    assert version in ai
    for skill_id in _plugin_packaging__SKILL_IDS:
        assert f'`{skill_id}`' in ai
    assert 'docs/plugin-installation.md' in ai
    assert 'Do not invent a Codex App slash-command string' in ai
    for command in [CANONICAL_MARKETPLACE, PLUGIN_ADD, UPGRADE, PLUGIN_REMOVE]:
        assert command not in ai
ROOT = Path(__file__).resolve().parents[1]
ZH = (ROOT / 'README.md').read_text(encoding='utf-8')
EN = (ROOT / 'README_EN.md').read_text(encoding='utf-8')
AI = (ROOT / 'README_AI.md').read_text(encoding='utf-8')
EVALS = (ROOT / 'evals' / 'README.md').read_text(encoding='utf-8')
_readme_user_facing__MANIFEST = json.loads((ROOT / '.codex-plugin' / 'plugin.json').read_text(encoding='utf-8'))
VERSION = _readme_user_facing__MANIFEST['version']
CANONICAL_MARKETPLACE = 'codex plugin marketplace add R-jed/subagents-dispatch'
PLUGIN_ADD = 'codex plugin add subagents-dispatch@subagents-dispatch'
UPGRADE = 'codex plugin marketplace upgrade subagents-dispatch'
_readme_user_facing__SKILL_IDS = ['dispatch', 'preview', 'status', 'steer', 'takeover', 'doctor']
README_LOGO = 'assets/subagents-dispatch-banner.png'

def test_public_readmes_explain_the_current_repository_layout():
    assert '## 项目结构' in ZH
    assert '## Repository layout' in EN
    for text in [ZH, EN]:
        for path in ['.agents/plugins/', '.codex-plugin/', 'agent-profiles/', 'contracts/', 'skills/', 'dispatch/', 'preview/', 'status/', 'steer/', 'takeover/', 'doctor/', 'docs/', 'evals/', 'scripts/', 'tests/']:
            assert path in text
        assert '├── dispatch/' in text
        assert '└── doctor/' in text

def test_public_readmes_link_deeper_docs():
    for text in [ZH, EN]:
        for link in ['README_AI.md', 'docs/plugin-installation.md', 'docs/architecture.md', 'docs/native-subagent-runtime.md', 'docs/runtime-attestation.md', 'docs/experiment-protocol.md', 'contracts/composition.md']:
            assert link in text

def test_public_readmes_explain_v3_control_and_evidence_without_unmeasured_performance_claims():
    for text in [ZH, EN]:
        for phrase in ['Configured', 'Requested', 'Accepted', 'Observed', '0 child', 'Status', 'Steer', 'Takeover', 'Runtime Attestation', 'Experiment Protocol', 'Composition Contract']:
            assert phrase in text
    assert '本 README 不声称 subagents-dispatch 已经被证明更快、更省总 Token' in ZH
    assert 'this README does not claim that subagents-dispatch is proven faster' in EN
    assert '当前五个 model / effort 是最优配置' in ZH
    assert 'the current five model/effort routes are optimal' in EN

def test_public_readme_visual_surface_uses_canonical_plugin_assets():
    plugin_assets = ROOT / 'assets'
    assert (plugin_assets / 'subagents-dispatch-banner.png').is_file()
    assert not (ROOT / 'docs' / 'logo-light.svg').exists()
    assert not (ROOT / 'docs' / 'logo-dark.svg').exists()
    for text in [ZH, EN]:
        assert '<picture' not in text
        assert README_LOGO in text
        assert '#gh-light-mode-only' not in text
        assert '#gh-dark-mode-only' not in text
        assert 'docs/logo-' not in text
        for line in text.splitlines():
            if '<img' in line and 'subagents-dispatch-banner' not in line and ('shields.io' not in line):
                raise AssertionError(f'Unexpected README image: {line}')

def test_ai_reference_is_an_index_to_canonical_policy_owners():
    for phrase in ['R-jed/subagents-dispatch', 'Repo marketplace id: subagents-dispatch', f'Current version:     {VERSION}', 'Distribution:        Codex Plugin', 'contracts/interaction.md', 'contracts/routing.md', 'contracts/handoff.md', 'contracts/team-plan.md', 'contracts/recovery.md', 'contracts/guardrails.md', 'contracts/final-review.md', 'contracts/policy.json', 'skills/<id>/SKILL.md', 'docs/plugin-installation.md', 'scripts/policy.py', 'Do not invent a Codex App slash-command string']:
        assert phrase in AI
    for skill_id in _readme_user_facing__SKILL_IDS:
        assert f'`{skill_id}`' in AI
    assert 'not a second copy of runtime policy' in AI
    for command in [CANONICAL_MARKETPLACE, PLUGIN_ADD, UPGRADE, '/subagents-dispatch:dispatch', '$dispatch']:
        assert command not in AI

def test_evals_readme_identifies_measurement_boundary_and_canonical_owners():
    for phrase in ['not part of the normal user setup', 'behavioral-workloads.json', 'behavioral-result.schema.json', 'routing-cases.json', 'coordination-cases.json', 'interaction-cases.json', 'runtime-assurance-cases.json', 'do not control how the plugin routes or coordinates work', '`interaction.md`', '`routing.md`', '`handoff.md`', '`team-plan.md`', '`recovery.md`', '`guardrails.md`', '`final-review.md`', '`policy.json`']:
        assert phrase in EVALS
ROOT = Path(__file__).resolve().parents[1]

def active_surface_files() -> list[Path]:
    paths = [ROOT / 'README.md', ROOT / 'README_EN.md', ROOT / 'README_AI.md', ROOT / 'PRIVACY.md', ROOT / '.codex-plugin' / 'plugin.json', ROOT / '.agents' / 'plugins' / 'marketplace.json']
    paths.extend(sorted((ROOT / 'docs').glob('*.md')))
    paths.extend(sorted((ROOT / 'contracts').glob('*.md')))
    paths.extend(sorted((ROOT / 'skills').glob('*/SKILL.md')))
    return paths

def test_active_v3_surfaces_have_no_obsolete_paths_control_grammar_or_policy_phrases():
    forbidden = {'skills/dispatch/references': 'obsolete Skill-owned shared contract path', 'policy-contract.json': 'obsolete root policy path', 'Zero children is normal': 'numeric zero-child framing', 'max_active_writers_per_workspace': 'numeric writer-capacity policy', '/dispatch preview': 'obsolete payload control grammar', '/dispatch status': 'obsolete payload control grammar', '/dispatch steer': 'obsolete payload control grammar', '/dispatch takeover': 'obsolete payload control grammar', '$dispatch': 'obsolete command identity', 'A green branch run does not replace the pull-request merge-result run': 'obsolete PR-only governance', 'Require pull requests': 'obsolete PR-only governance', 'Execution Receipt': 'obsolete receipt name', '· complete · no retry': 'obsolete English receipt state axis', '· 完成 · 未重试': 'obsolete Chinese receipt state axis', '无需最终复核': 'obsolete negative review wording'}
    defects: list[str] = []
    for path in active_surface_files():
        text = path.read_text(encoding='utf-8')
        for phrase, reason in forbidden.items():
            if phrase in text:
                defects.append(f'{path.relative_to(ROOT)}: {reason}: {phrase}')
    assert defects == []

def test_active_v3_surfaces_do_not_publish_unverified_namespaced_slash_syntax():
    defects: list[str] = []
    for path in active_surface_files():
        text = path.read_text(encoding='utf-8')
        if '/subagents-dispatch:' in text:
            defects.append(str(path.relative_to(ROOT)))
    assert defects == []
ROOT = Path(__file__).resolve().parents[1]
INTERACTION = ROOT / 'contracts' / 'interaction.md'
STATUS_SKILL = ROOT / 'skills' / 'status' / 'SKILL.md'

def test_status_contract_uses_low_resolution_public_activity_presentation():
    text = INTERACTION.read_text(encoding='utf-8')
    for phrase in ['Running / 运行中', 'Waiting / 等待', 'Needs attention / 需处理', 'Completed / 已完成', 'U1 · Luna Max 读取', 'U2 · Luna Max 执行 · 等待 U1', 'U1 · Luna Max Read', 'waiting for U1', 'Do not dump the full active-state JSON by default', 'Use the orchestration locale stored in active state']:
        assert phrase in text
    assert '## Dispatch Receipt' in text
    assert '## Execution Receipt' not in text

def test_status_dependency_explanation_is_evidence_bound_and_skill_loads_public_vocabulary():
    interaction = INTERACTION.read_text(encoding='utf-8')
    skill = STATUS_SKILL.read_text(encoding='utf-8')
    assert 'only when that dependency is part of current accepted structural truth' in interaction
    assert 'omit the dependency explanation rather than reconstructing or guessing it' in interaction
    assert '../../contracts/receipt.md' in skill
ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / 'contracts'
SKILLS = ROOT / 'skills'
_v3_structural_contract__SKILL_IDS = {'dispatch', 'preview', 'status', 'steer', 'takeover', 'doctor'}
CONTRACT_FILES = {'policy.json', 'routing.md', 'composition.md', 'interaction.md', 'state.md', 'receipt.md', 'team-plan.md', 'recovery.md', 'guardrails.md', 'handoff.md', 'evidence-artifact.md', 'final-review.md'}

def test_root_contracts_are_the_only_active_canonical_owners():
    assert {path.name for path in CONTRACTS.iterdir() if path.is_file()} == CONTRACT_FILES
    assert not (ROOT / 'policy-contract.json').exists()
    assert not (SKILLS / 'dispatch' / 'references').exists()

def test_six_explicit_thin_skills_have_exact_ids_and_metadata():
    assert {path.name for path in SKILLS.iterdir() if path.is_dir()} == _v3_structural_contract__SKILL_IDS
    for skill_id in _v3_structural_contract__SKILL_IDS:
        skill = SKILLS / skill_id
        text = (skill / 'SKILL.md').read_text(encoding='utf-8')
        match = re.match('^---\\n(.*?)\\n---\\n', text, re.S)
        assert match
        assert yaml.safe_load(match.group(1))['name'] == skill_id
        metadata = yaml.safe_load((skill / 'agents' / 'openai.yaml').read_text(encoding='utf-8'))
        assert metadata['policy']['allow_implicit_invocation'] is False

def test_machine_policy_uses_semantic_writer_coordination():
    policy = json.loads((CONTRACTS / 'policy.json').read_text(encoding='utf-8'))
    assert policy['delegation'] == {'max_depth': 1}
    assert policy['write_coordination'] == {'mode': 'single_writer', 'scope': 'canonical_workspace'}
    assert 'max_active_writers_per_workspace' not in json.dumps(policy)
    assert set(policy['roles']) == {'reader', 'worker', 'solver', 'investigator', 'advisor'}

def test_plugin_starter_prompts_cover_all_skills_without_guessed_slash_syntax():
    manifest = json.loads((ROOT / '.codex-plugin' / 'plugin.json').read_text(encoding='utf-8'))
    prompts = '\n'.join(manifest['interface']['defaultPrompt'])
    for label in ['Dispatch', 'Preview', 'Status', 'Steer', 'Takeover', 'Doctor']:
        assert label in prompts
    assert not re.search('(?<![A-Za-z0-9_.-])/(?:dispatch|preview|status|steer|takeover|doctor)\\b', prompts, re.I)

def test_doctor_skill_defines_explicit_five_role_live_route_workflow():
    skill = (SKILLS / 'doctor' / 'SKILL.md').read_text(encoding='utf-8')
    for role in ['subagents_dispatch_reader', 'subagents_dispatch_worker', 'subagents_dispatch_solver', 'subagents_dispatch_investigator', 'subagents_dispatch_advisor']:
        assert role in skill
    assert 'fork_turns = none' in skill
    assert 'scripts/runtime-evidence.py' in skill
    assert 'UNKNOWN' in skill
