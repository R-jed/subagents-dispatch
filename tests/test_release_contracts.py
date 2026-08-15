from __future__ import annotations
from pathlib import Path
import json
import re
ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'docs' / 'v3.0.0-post-release-final-audit.md'

def test_post_release_audit_does_not_overclaim_tag_immutability():
    text = AUDIT.read_text(encoding='utf-8')
    assert 'The immutable `v3.0.0` tag' not in text
    assert 'GitHub/API verification confirmed that `v3.0.0` resolved to the exact released commit above' in text
    assert 'does not claim platform-enforced tag immutability' in text

def test_post_release_audit_scopes_external_writer_residual_risk():
    text = AUDIT.read_text(encoding='utf-8')
    assert 'A non-cooperating external writer can create a narrow filesystem TOCTOU window' in text
    assert 'No reproducible cooperating-path data-loss defect was established during this audit' in text
    assert 'hostile or perfectly timed external writer' not in text
ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / '.codex-plugin' / 'plugin.json'
MARKETPLACE = ROOT / '.agents' / 'plugins' / 'marketplace.json'
README_CN = ROOT / 'README.md'
README_EN = ROOT / 'README_EN.md'
README_AI = ROOT / 'README_AI.md'
CHANGELOG = ROOT / 'CHANGELOG.md'
RELEASE_CHECKLIST = ROOT / 'docs' / 'release-checklist.md'
SEMVER = re.compile('^\\d+\\.\\d+\\.\\d+$')

def current_version() -> str:
    version = json.loads(PLUGIN.read_text(encoding='utf-8'))['version']
    assert isinstance(version, str) and SEMVER.fullmatch(version)
    return version

def test_public_version_markers_match_plugin_manifest():
    version = current_version()
    badge = f'version-{version}-green.svg'
    assert badge in README_CN.read_text(encoding='utf-8')
    assert badge in README_EN.read_text(encoding='utf-8')
    assert re.search(f'^Current version:\\s+{re.escape(version)}$', README_AI.read_text(encoding='utf-8'), flags=re.MULTILINE)

def test_latest_changelog_entry_matches_plugin_manifest():
    version = current_version()
    match = re.search('^## \\[([^\\]]+)\\]', CHANGELOG.read_text(encoding='utf-8'), flags=re.MULTILINE)
    assert match, 'CHANGELOG.md must contain a version heading'
    assert match.group(1) == version

def test_marketplace_plugin_source_is_bound_to_release_tag():
    version = current_version()
    market = json.loads(MARKETPLACE.read_text(encoding='utf-8'))
    plugins = market.get('plugins')
    assert isinstance(plugins, list) and len(plugins) == 1
    source = plugins[0].get('source')
    assert source == {'source': 'url', 'url': 'https://github.com/R-jed/subagents-dispatch.git', 'ref': f'v{version}'}

def test_release_checklist_separates_repository_host_human_ui_and_distribution_evidence():
    text = RELEASE_CHECKLIST.read_text(encoding='utf-8')
    for marker in ['### Evidence ownership', 'Repository/API/CI evidence', 'Raw Host/rollout evidence', 'Direct human Codex App observation', 'Model self-report', 'cannot by itself close a Host/UI gate', '## 2. Repository gates', '## 3. Real Codex Host gates', 'Human App gate', 'record the exact rendered entry labels', 'post-selection presentation', 'RESTART_REQUIRED', 'subagents_dispatch_reader', 'subagents_dispatch_worker', '## 4. Hard release blockers', '## 5. Repository governance before tagging', '## 6. Tag, distribution smoke, and GitHub Release', 'Marketplace entry resolves the Plugin source from the same tag rather than a mutable branch']:
        assert marker in text
ROOT = Path(__file__).resolve().parents[1]

def test_transient_local_agent_review_and_handoff_artifacts_are_not_packaged():
    forbidden_markers = {'deep-review-report', 'release-candidate-closure', 'local-validation', 'handoff-progress', 'headoff'}
    candidates = [ROOT, ROOT / 'docs']
    offenders: list[str] = []
    for base in candidates:
        for path in base.iterdir():
            if not path.is_file():
                continue
            lowered = path.name.lower()
            if any((marker in lowered for marker in forbidden_markers)):
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == [], f'transient local-agent artifacts must stay out of the repository: {offenders}'

def test_durable_docs_do_not_reintroduce_pre_root_move_plugin_paths():
    durable_docs = [ROOT / 'README.md', ROOT / 'README_EN.md', ROOT / 'README_AI.md']
    durable_docs.extend((ROOT / 'docs').glob('*.md'))
    durable_docs.extend((ROOT / 'skills').glob('**/*.md'))
    stale = 'plugins/subagents-dispatch'
    offenders = [str(path.relative_to(ROOT)) for path in durable_docs if stale in path.read_text(encoding='utf-8')]
    assert offenders == [], f'root Plugin docs contain stale nested-plugin paths: {offenders}'

def test_privacy_policy_discloses_explicit_local_rollout_attestation_boundary():
    text = (ROOT / 'PRIVACY.md').read_text(encoding='utf-8')
    for phrase in ['## Local runtime attestation', 'explicitly requests live route verification', 'exact requested child thread UUID', 'session_meta', 'turn_context', 'does not scan transcript records for task facts', 'does not emit prompts, assistant output, tool payloads, reasoning, source contents, or the rollout path', 'does not upload the rollout, extracted metadata, or session content to the project maintainer', 'ordinary plugin use does not require local rollout inspection']:
        assert phrase in text
ROOT = Path(__file__).resolve().parents[1]

def test_privacy_discloses_thread_scoped_temporary_capsule_and_retention_boundary():
    text = (ROOT / 'PRIVACY.md').read_text(encoding='utf-8')
    for phrase in ["operating system's temporary directory", 'root-thread-id', 'active.json', 'raw prompts', 'private reasoning', 'credentials', 'full source files', 'Normal terminal completion removes', 'seven days', 'unresolved active writers are retained', 'not sent to the project maintainer']:
        assert phrase in text

def test_chinese_public_examples_use_receipt_activity_vocabulary():
    text = (ROOT / 'README.md').read_text(encoding='utf-8')
    assert all((word not in text for word in ['Reader', 'Worker', 'Solver', 'Investigator', 'Advisor']))
    for word in ['Luna', 'Sol', 'Terra', 'Max', 'High', 'XHigh', 'Status', 'Steer', 'Takeover', '读取', '调研', '执行', '决策', '验收']:
        assert word in text

def test_public_receipt_examples_use_independent_axes_without_task_completion_state():
    chinese = (ROOT / 'README.md').read_text(encoding='utf-8')
    english = (ROOT / 'README_EN.md').read_text(encoding='utf-8')
    assert '编排: Luna Max 读取 · Luna Max 执行 · Sol High 验收' in chinese
    assert '验收: 1轮 · 通过' in chinese
    for obsolete in ['Dispatch: Luna Max 读取 → Luna Max 执行 · 完成 · 未重试 · 无需最终复核', '· 完成 · 未重试', '无需最终复核']:
        assert obsolete not in chinese
    assert 'Dispatch: Luna Max Read · Luna Max Execute · Sol High Review' in english
    assert 'Review: 1 round · passed' in english
    for obsolete in ['Dispatch: Luna Max Read → Luna Max Execute · complete · no retry · not required', '· complete · no retry']:
        assert obsolete not in english

def test_work_section_63_adversarial_cases_are_registered_once():
    payload = json.loads((ROOT / 'evals' / 'interaction-cases.json').read_text(encoding='utf-8'))
    ids = [case['id'] for case in payload['cases']]
    expected = {'missing-thread-id', 'spawn-pending-no-match', 'spawn-pending-single-match', 'spawn-pending-multiple-match', 'corrupt-capsule-active-writer', 'multi-targetless-steer', 'single-targetless-steer', 'interrupted-takeover', 'fix-first-without-correction', 'retry-then-rework', 'locale-persistence', 'unrelated-dispatch-with-unresolved-writer', 'repeated-status-dedupe', 'same-child-resume', 'route-mismatch'}
    assert expected <= set(ids)
    assert len(ids) == len(set(ids))

def test_ci_and_release_docs_keep_host_app_evidence_external_and_local_gates_deterministic():
    workflow = (ROOT / '.github' / 'workflows' / 'ci.yml').read_text(encoding='utf-8')
    release = (ROOT / 'docs' / 'release-checklist.md').read_text(encoding='utf-8')
    assert 'OPENAI_CODEX_PLUGIN_VALIDATOR_REF' in workflow
    for phrase in ['python -m ruff check', 'python -m pytest -q', 'install-agents.py --codex-home', 'doctor.py --codex-home']:
        assert phrase in workflow or phrase in release
    for phrase in ['short-lived feature branch', 'adversarial/deep review', 'direct merge to main', 'GitHub Actions cross-platform confirmation', 'A pull request is optional', 'all six Plugin Skills']:
        assert phrase in release
    assert 'A green branch run does not replace the pull-request merge-result run' not in release
    ai_reference = (ROOT / 'README_AI.md').read_text(encoding='utf-8')
    assert 'App labels require direct human observation' in ai_reference
    assert 'Host route/control claims require raw Host/rollout evidence from the exact candidate under validation' in ai_reference
    assert 'Evidence status belongs to the release validation record, not this reference file' in ai_reference
    assert 'never treat repository text or model self-report as proof that a Host/UI gate passed' in ai_reference
    assert 'short-lived feature branch' in ai_reference

def test_release_checklist_requires_all_five_live_routes_without_promoting_accepted_to_observed():
    release = (ROOT / 'docs' / 'release-checklist.md').read_text(encoding='utf-8')
    for agent_type in ['subagents_dispatch_reader', 'subagents_dispatch_worker', 'subagents_dispatch_solver', 'subagents_dispatch_investigator', 'subagents_dispatch_advisor']:
        assert agent_type in release
    assert 'accepted exact `agent_type` proves role acceptance only' in release
    assert 'Missing source provenance makes only that dimension `UNKNOWN`' in release
    assert 'Observed mismatches and public/local conflicts fail closed' in release

def test_formal_validation_resolves_python_311_without_bare_python_assumption():
    release = (ROOT / 'docs' / 'release-checklist.md').read_text(encoding='utf-8')
    runtime = (ROOT / 'docs' / 'runtime-attestation.md').read_text(encoding='utf-8')
    helper_runtime = (ROOT / 'docs' / 'python-runtime.md').read_text(encoding='utf-8')
    for text in [release, runtime, helper_runtime]:
        assert 'Python 3.11' in text
    for phrase in ['PYTHON_PREREQUISITE_UNMET', 'environment adaptation', 'sys.executable']:
        assert phrase in helper_runtime
        assert phrase in release or phrase in runtime
    assert '<python-3.11+>' in release
    assert '<python-3.11+>' in runtime
    assert 'python scripts/inspect-agent-runtime.py' not in release
    assert 'python scripts/inspect-agent-runtime.py' not in runtime
    assert 'A missing command named `python` is not a failed prerequisite' in release
    assert 'downstream Host acceptance, runtime route, inspector, and behavioral gates are `NOT TESTED` or `INVALIDATED`' in release
ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / 'docs' / 'release-checklist.md'
AI_REFERENCE = ROOT / 'README_AI.md'
REPOSITORY_ARCHITECTURE = ROOT / 'docs' / 'repository-architecture.md'

def test_v3_release_path_excludes_formal_experiment_materialization():
    release = RELEASE.read_text(encoding='utf-8')
    for phrase in ['role calibration', 'formal model/effort comparison campaigns', 'formal single-agent versus Dispatch product benchmark campaigns', 'not v3.0.0 hard release blockers', 'Runtime attestation remains part of the release path']:
        assert phrase in release
    for obsolete_release_gate in ['scripts/calibration_profiles.py create', 'scripts/calibration_profiles.py check', '--calibration-evidence-root', 'freeze `materialization_mode=profile_only` for the formal model/effort campaign']:
        assert obsolete_release_gate not in release

def test_release_gate_requires_a_public_product_or_claim_boundary():
    release = RELEASE.read_text(encoding='utf-8')
    assert 'must protect one concrete public capability, safety property, distribution property, or release claim' in release
    assert 'If a proposed gate cannot name that protected claim, keep it out of the release path.' in release

def test_ai_owner_map_marks_experiments_as_research_not_default_release_work():
    text = AI_REFERENCE.read_text(encoding='utf-8')
    for phrase in ['The Experiment Plane is development/research infrastructure.', 'do not block v3.0.0 unless the release publishes a claim', 'Runtime attestation remains a product release gate', 'small real-task product canary']:
        assert phrase in text

def test_unreleased_shared_config_transaction_shell_is_removed():
    assert not (ROOT / 'scripts' / 'calibration_config_transaction.py').exists()
    assert not (ROOT / 'tests' / 'test_calibration_config_transaction.py').exists()
    architecture = REPOSITORY_ARCHITECTURE.read_text(encoding='utf-8')
    assert 'semantic shared-config transaction module remains isolated infrastructure' not in architecture
    assert 'Formal model/effort calibration has no shared `config.toml` mutation path.' in architecture
ROOT = Path(__file__).resolve().parents[1]
ARCHITECTURE = ROOT / 'docs' / 'architecture.md'

def test_architecture_document_matches_v3_control_and_receipt_contracts():
    text = ARCHITECTURE.read_text(encoding='utf-8')
    for phrase in ['six thin explicit entry points', 'There is no minimum Subagent count', 'INTERRUPTED', '## Dispatch Receipt', 'scripts/dispatch_state.py', 'Doctor has exactly eight diagnostic layers', 'Effective permission state', 'Permission-source provenance', 'scripts/uninstall-agents.py', 'selected project lane bound to materialized work', 'Explicit Dispatch that routes everything to Main still returns the minimal zero-child Receipt']:
        assert phrase in text
    for obsolete in ['Version 2.1 adds', '## Execution Receipt', 'Dispatch: Reader → Worker', '· complete · no retry', 'Zero children is normal', 'preview <task>', 'steer <unit_id>: <guidance>', 'Doctor has exactly six diagnostic layers', 'Zero-child tasks, Preview, Status-only requests, and `RESTART_REQUIRED` first-use setup do not add a receipt']:
        assert obsolete not in text

def test_architecture_keeps_codex_native_subagents_as_the_only_runtime():
    text = ARCHITECTURE.read_text(encoding='utf-8')
    assert 'Codex remains the only Agent runtime' in text
    for forbidden in ['background scheduler is introduced', 'persistent task database', 'private Agent runtime']:
        assert forbidden not in text
ROOT = Path(__file__).resolve().parents[1]
EVAL_DOC = ROOT / 'docs' / 'behavioral-evals.md'

def test_behavioral_eval_protocol_uses_current_dispatch_receipt_semantics():
    text = EVAL_DOC.read_text(encoding='utf-8')
    for phrase in ['Dispatch Receipt, and Handoff Capsule boundaries', '## Experiment I: Dispatch Receipt clarity', 'explicit Dispatch with zero materialized children', 'minimal zero-child Dispatch + Review receipt', 'Preview-only request', 'no terminal Dispatch Receipt']:
        assert phrase in text
    for obsolete in ['Execution Receipt', 'one-line 2.1 receipt', 'When the workload exercises 2.1 controls', 'preview <same task used for a later real run>', 'These should not add a receipt.']:
        assert obsolete not in text

def test_behavioral_eval_protocol_keeps_ui_syntax_observation_gated():
    text = EVAL_DOC.read_text(encoding='utf-8')
    assert 'Do not assume or record a literal slash string unless the App directly renders one' in text
    assert 'contracts/receipt.md' in text
    assert 'contracts/state.md' in text
ROOT = Path(__file__).resolve().parents[1]
DOCTOR = ROOT / 'scripts' / 'doctor.py'

def test_doctor_reuses_dispatch_state_temp_boundary_for_state_scanning():
    text = DOCTOR.read_text(encoding='utf-8')
    assert '_temporary_root,' in text
    assert '_reject_symlink,' in text
    assert 'root_base = _temporary_root(temp_root)' in text
    start = text.index('def _state_entries')
    end = text.index('\ndef _unexpected_repository_state', start)
    helper = text[start:end]
    assert 'tempfile.gettempdir()' not in helper
    assert 'candidate.is_absolute()' not in helper
    assert 'system_temp' not in helper
ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'docs' / 'native-subagent-runtime.md'

def test_native_runtime_document_keeps_selected_and_observed_route_truth_separate():
    text = RUNTIME.read_text(encoding='utf-8')
    for phrase in ['Configured or selected values never become observed values by assumption', 'ordinary Dispatch Receipt may display the selected project lane', 'not an independent live telemetry measurement', 'Contradictory native evidence is a route-integrity failure', 'The current Plugin does not add a private App Server client']:
        assert phrase in text
    assert 'Execution Receipts follow this same rule' not in text
    assert 'subagents-dispatch 2.1 does not add' not in text

def test_native_runtime_document_uses_explicit_skill_semantics_not_guessed_slash_grammar():
    text = RUNTIME.read_text(encoding='utf-8')
    assert 'The Plugin packages six explicit Skill ids' in text
    assert 'These are semantic inputs after selection, not guessed literal App slash strings' in text
    for obsolete in ['preview <task>', 'steer <unit_id>: <guidance>', 'takeover <unit_id>']:
        assert obsolete not in text
    assert 'pendingInit  -> RUNNING' in text
    assert 'notFound     -> UNKNOWN' in text
    assert 'no minimum Subagent count' in text
ROOT = Path(__file__).resolve().parents[1]
ROUTING = ROOT / 'contracts' / 'routing.md'

def test_delegation_quantity_is_value_driven_not_zero_child_numeric_policy():
    text = ROUTING.read_text(encoding='utf-8')
    assert 'Delegation is optional and value-driven' in text
    assert 'There is no minimum Subagent count' in text
    assert 'zero children is a valid derived outcome' in text
    assert 'Zero children is normal' not in text
    assert 'Native Codex capacity is the upper bound on concurrency, not a target' in text
    assert 'Do not keep Agents busy merely because the host has spare capacity' in text
