# V4.0.0 Release Checklist

Use this checklist for the exact V4.0.0 candidate. Repository implementation may complete while Codex quota is unavailable, but publication remains blocked until the real Host lifecycle-Hook smoke is captured.

### Evidence ownership

Keep four evidence classes separate:

```text
Repository/API/CI evidence
Raw Host/rollout evidence
Direct human Codex App observation
Model self-report
```

Repository/API/CI evidence can close deterministic package, schema, test, and distribution checks. Raw Host/rollout evidence owns lifecycle and runtime truth. Direct human Codex App observation owns rendered UI labels and post-selection presentation. Model self-report is supporting context and cannot by itself close a Host/UI gate.

Every release gate must protect one concrete public capability, safety property, distribution property, or release claim. Formal role calibration and benchmark campaigns remain Experiment Plane research capabilities and are not hard release blockers unless a release claim depends on them. Runtime attestation and the V4 Host lifecycle smoke remain release-path evidence where their corresponding claims depend on observed Host behavior.

## 1. Candidate identity

Record the exact candidate commit, tree, Plugin version, Marketplace ref, Python helper identity, Codex Host version used for smoke, and operating system. `.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json`, README badges, `README_AI.md`, and the V4 changelog entry must agree on `4.0.0` before tagging.

Use a versioned semantic-version tag only after all required release gates pass. The checklist does not claim platform-enforced tag immutability. Evidence that a ref resolves to an expected commit does not by itself prove platform-enforced tag immutability. Verify that the Marketplace entry resolves the Plugin source from the same tag rather than a mutable branch.

## 2. Repository gates

The exact candidate must pass the canonical GitHub Actions matrix:

```text
Ubuntu / Python 3.11
Ubuntu / Python 3.12
macOS / Python 3.11
Windows / Python 3.11
```

Resolve one `<python-3.11+>` interpreter according to `docs/python-runtime.md`. Interpreter resolution is environment adaptation; if no supported interpreter exists, report `PYTHON_PREREQUISITE_UNMET`. A resolved `sys.executable` may be reused for deterministic helper calls.

Required deterministic checks:

```text
Plugin and Marketplace JSON validation
package-integrity regeneration check
pinned official OpenAI Plugin validator
Ruff
full pytest suite
managed Agent install/check/uninstall/reinstall lifecycle
Doctor --check
V4 state and Work Graph tests
PendingControl and Guard tests
WriterLease and same-child lifecycle tests
Orchestrate tests
migration/fail-closed tests
tag/version parity when running from a release tag
```

Production model/effort must remain fixed:

```text
Luna Max
Terra High
Sol High
```

The public Skill directories must be exactly:

```text
skills/orchestrate
skills/doctor
```

The managed role identities remain:

```text
subagents_dispatch_reader
subagents_dispatch_worker
subagents_dispatch_investigator
subagents_dispatch_solver
subagents_dispatch_advisor
```

For formal route evidence, preserve the distinction `Configured → Requested → Accepted → Observed`. Accepted route metadata must not be promoted to observed Host truth.

Supported uninstall commands may update `config.toml` only to persist removal of this Plugin and Marketplace registration. Release verification must allow only the semantic delta required by the supported Plugin and Marketplace registration removal commands. All unrelated configuration semantics must remain unchanged, and other Codex state must remain unchanged.

## 3. State and migration gates

Verify:

```text
state v4 remains bounded and thread scoped
WorkUnit acceptance is separate from Host lifecycle
Host COMPLETED advances only to RESULT_READY
dependencies unlock only from WorkUnit ACCEPTED
stale execution/control/lease observations are discarded
WriterLease.UNKNOWN never auto-releases
PendingControl.UNKNOWN remains fail closed
V3.x active or corrupt state is never silently migrated
plan-only creates no runtime state, lease, control, or Host action
```

## 4. Real Codex Host gates

This gate is defined by `docs/v4/host-smoke.json`. Offline CI, source inspection, the official Plugin validator, prior V3 spawn-guard evidence, or model self-report cannot substitute for it.

All H01-H07 probes must have real Codex Host evidence:

```text
H01 spawn_agent
     PreToolUse observed
     PostToolUse observed
     same tool_use_id across both

H02 followup_task
     PreToolUse observed
     PostToolUse observed
     same tool_use_id across both

H03 interrupt_agent
     PreToolUse observed
     PostToolUse observed
     same tool_use_id across both

H04 SubagentStop
     managed stop event observed
     continue:false prevents automatic continuation

H05 managed child sibling followup
     blocked before sibling lifecycle control

H06 managed child sibling interrupt
     blocked before sibling lifecycle control

H07 missing PostToolUse
     control is not ACKED
     unresolved state remains fail closed
```

Only after H01-H07 pass may the staged `docs/v4/hooks.json` be promoted to production `hooks/hooks.json`. After promotion, rerun the entire repository matrix and repeat the relevant Host smoke against the exact promoted candidate.

A generic non-blocking Hook command failure is not a successful Guard block. Internal Guard failures must use the Host's actual blocking path. Real Host evidence must distinguish tool rejection, Hook rejection, Host lifecycle acceptance, and later settlement observation.

With production lifecycle Hooks active, verify:

```text
fresh writer activation reserves WriterLease before the Host call
second managed writer is blocked
followup for an old writer cannot bypass the current lease
interrupt ACK alone does not release WriterLease
fresh same-generation INTERRUPTED evidence may settle a writer only with proven Guard coverage
takeover transfers WriterLease atomically to Main
stale lease identity cannot release a newer lease
```

Verify representative Orchestrate flows:

```text
plan-only
zero-child task
two-child initial fanout
Host-capacity-limited fanout
progressive refill
acceptance backpressure
same-child correction
CONTINUE after interrupt
takeover
cancellation
fresh Advisor review
post-review mutation invalidation
V3.x unresolved-state block
```

No child may create or control sibling project children. Peer messaging must not grant authority, transfer WriterLease, unlock dependencies, or complete acceptance.

## 5. Doctor and human App gates

Run:

```text
<python-3.11+> scripts/doctor.py --codex-home <isolated-home> --check --thread-id release-doctor
<python-3.11+> scripts/doctor.py --codex-home <isolated-home> --release-check --thread-id release-doctor
```

The first command validates repository/package health. The second must remain non-zero while `docs/v4/host-smoke.json` is pending, and may turn green only after the production lifecycle Hook manifest and real Host evidence agree. Doctor must not edit Host Hook trust state to make the report green.

After the exact release candidate is installed in Codex, record the exact rendered entry labels for Orchestrate and Doctor through Direct human Codex App observation. Verify both entries are distinguishable, post-selection presentation is correct, and unrelated tasks do not implicitly activate either Skill. If managed profiles were newly provisioned and the Host requires rediscovery, record `RESTART_REQUIRED` and start a fresh task before the route smoke. Do not infer literal slash syntax from repository names.

## 6. Governance, tag, and distribution

Use a short-lived feature branch for candidate work, require adversarial/deep review for material safety or state changes, and require GitHub Actions cross-platform confirmation before merging. A pull request is optional when repository policy permits direct merge to main, but the same review and CI evidence is still required.

Final sequence:

```text
repository matrix PASS
real Host H01-H07 PASS
promote staged V4 Hooks
repository matrix PASS again
writer/takeover Host smoke PASS
Orchestrate representative Host smoke PASS
Doctor --release-check PASS
human two-Skill App observation PASS
merge approved candidate
create v4.0.0 versioned semantic-version tag
verify Marketplace installs exact tagged candidate
publish release notes
```

If any real Host gate remains unavailable, record the candidate as repository-complete and release-blocked. Do not relabel `PENDING`, `UNKNOWN`, or `NOT TESTED` as PASS.
