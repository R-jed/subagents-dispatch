# V4.0.0 Release Checklist

Use this checklist for the Native Core V4.0.0 release. Repository completion does not imply Host release readiness.

## 1. Release identity

Keep two identity layers separate.

Release source identity records the exact final Git commit/tree. It is used by repository qualification, the final release envelope and Final Review.

Host qualification identity records the exact values that can change the meaning or behavior of the real-Host campaign:

```text
runtime_manifest_sha256
profile_contract_sha256
host_contract_sha256
```

The Host campaign binds these three qualification digests plus its exact environment identities and results. A source-only change that leaves all three qualification digests unchanged does not invalidate an already-conclusive Host campaign. The final Git commit/tree, repository checks and Final Review must still be refreshed for the final source state.

Also record Plugin version, Marketplace identity, Codex Host version/build and operating systems used for validation.

For real Host environment binding, use the Codex-native identities defined by `docs/v4/host-smoke.json`: `session_id` is the Host-reported session-tree identity shared by the root thread and its descendants, and `thread_id` is the Host-reported identity of the current root thread. Use only the authoritative sources listed in that machine contract. Do not invent or substitute a generic `run_id`. If either required identity cannot be established for the current root Host session, the environment binding remains `UNKNOWN`.

`.codex-plugin/plugin.json`, Marketplace metadata and the V4 changelog must agree on `4.0.0` before tagging. Use a versioned semantic-version tag only after all release gates pass, then verify Marketplace installation resolves the exact tagged source. Resolving a ref to the expected commit does not by itself prove platform-enforced tag immutability.

## 2. Repository gates

The exact release source must pass the canonical GitHub Actions matrix:

```text
Ubuntu / Python 3.11
Ubuntu / Python 3.12
macOS / Python 3.11
Windows / Python 3.11
```

Required checks include Plugin/Marketplace validation, package-integrity regeneration, official Plugin validator, Ruff, full pytest, managed profile install/check/uninstall lifecycle, Doctor, V4 state/work graph/scheduler/lifecycle/writer tests, update lifecycle tests, migration fail-closed tests and product-surface consistency tests.

Public Skill directories must be exactly:

```text
skills/orchestrate
skills/doctor
```

Production model/effort remains fixed:

```text
Reader / Worker        Luna Max
Investigator           Terra High
Solver / Advisor       Sol High
```

Supported removal commands may update `config.toml` only to persist removal of this Plugin and Marketplace registration. Release verification must allow only the semantic delta required by the supported Plugin and Marketplace registration removal commands; all unrelated configuration semantics must remain unchanged, and other Codex state must remain unchanged.

Repository tests should validate current product behavior and safety invariants. They should not preserve dead architecture solely to keep historical assertions green.

## 3. Native Core state and recovery gates

Verify at minimum:

```text
state is bounded and root-session scoped
WorkUnit acceptance is separate from Host lifecycle
Host COMPLETED advances to RESULT_READY only
dependencies unlock only from ACCEPTED
WorkGraph owns one-or-many responsibility structure
team_plan_revision has compatibility-marker semantics only
managed spawn requires complete responsibility context
fresh child uses exact managed agent_type and fork_turns = none
stale control/lease observations are rejected
explicit pre-materialization spawn rejection consumes no fresh attempt
ambiguous materialization becomes UNKNOWN
WriterLease.UNKNOWN never auto-releases
interrupt return alone never releases WriterLease
fresh retry requires changed execution basis and settled prior execution
same-child correction requires a new correction basis
attempt_no and followup_count are diagnostic, not fixed authorization budgets
CONTINUE preserves the same interrupted ExecutionBinding
older safely settled attempts compact without invalidating current identity or lease references
V3 active/corrupt state is never silently migrated
V4 state depends only on schema-neutral state_storage primitives
legacy stale cleanup does not load the retired V3 orchestration engine
plan-only creates no runtime state, lease or Host action
```

## 4. Real Codex Host gate

`docs/v4/host-smoke.json` is the machine-readable authority. Bind each campaign environment to the exact root `session_id` and `thread_id` before any N0/N1 child spawn. Public Host/session metadata is preferred. The machine contract defines the permitted Host-produced fallback evidence and the `UNKNOWN` policy when either identity remains unavailable.

The external Host campaign must also bind the current Host qualification identity from the runtime package manifest, managed profile contract and Host campaign contract. Git commit/tree are release-source identity and do not by themselves determine whether Host evidence remains reusable.

The required campaign is exactly:

```text
N0 exact role / model / effort / fork_turns
N1 managed delegation depth
N2 canonical task address plus Host-thread identity evidence binding
N3 Host admission rejection with no child identity or resident runtime materialization
N4 RUNNING Steer via followup_task plus same-child correction and continue
N5 interrupt and settlement observation
N6 writer takeover blocked until settlement
N7 rollout reconciliation and privacy allowlist
N8 final Advisor review and effective sandbox truth
```

For N1, run the canonical managed route for every fixed profile. Confirm the managed assignment includes the no-further-Agent boundary, include an adversarial untrusted-input request to create or control another Agent, and inspect authoritative Host activity plus descendant identity/spawn-edge evidence. Any managed child that issues nested Agent creation/control or materializes a descendant fails N1. Ambiguous evidence is UNKNOWN. A generic V2 child that is explicitly forced to recurse demonstrates Host capability only and cannot by itself decide the managed N1 verdict.

For N4, successful `followup_task` tool-call acceptance is not sufficient by itself. Release evidence must show that the RUNNING Steer targeted the original canonical task address, stayed bound to the original Host child with no replacement materialized, and was consumed by that same child. Steer must preserve the ExecutionBinding, `attempt_no`, `control_epoch`, and `followup_count`. Correction and Continue remain same-child controls and must not create a fresh attempt.

Offline CI, source inspection, profile configuration, model self-report or evidence from another Host qualification basis cannot substitute for required real Host observations. Profile configuration and project `max_depth=1` establish product intent but do not prove Host-hard descendant isolation.

Configured read-only profiles do not by themselves prove Host-enforced read-only. N8 must establish the Advisor's actual effective permission state before strict read-only Final Review can pass.

## 5. Stability and invalidation

Classify every post-evidence change before deciding whether Host work must be repeated.

If `.codex-plugin/package-integrity.json`, `contracts/policy.json` or `docs/v4/host-smoke.json` changes in a way that changes its qualification digest, the Host qualification basis changed. Refresh the qualification identity and repeat every affected Host probe.

If only source outside that qualification basis changes, such as `headoff.md`, ordinary documentation, or release tooling that is not part of the shipped package manifest, keep the existing Host campaign only when all three qualification digests are proven unchanged. Refresh the exact release source commit/tree, rerun the repository checks affected by the source change, and run a fresh Final Review against the final source state.

Do not decide reuse from file names alone. Compare the qualification digests and use the Issue #91 `REUSE | RERUN | NOT_RUN` preflight record.

Representative flows must remain covered by repository or Host evidence as applicable:

```text
plan-only
zero-child task
single delegated responsibility
value-driven multi-child read investigation under the four-child ceiling
known-capacity-limited admission
evidence-gated fresh retry
RUNNING Steer consumed by the same child
same-child correction with changed basis
CONTINUE after interrupt
takeover
cancellation
managed-child adversarial no-descendant behavior
fresh Advisor review
post-review mutation invalidation
legacy unresolved-state block
```

## 6. Final Review and release evidence

After deterministic checks and N0-N8 pass for the current Host qualification identity, run a fresh independent Final Review against the exact final release source under `contracts/final-review.md`.

Then verify the external release evidence with:

```text
<python-3.11+> scripts/release_evidence_v4.py --repo <candidate-root> --evidence <external-release-evidence>
```

The release envelope must bind the final Git commit/tree and current qualification digests. Its nested Host campaign binds only the Host qualification identity, environments and N0-N8 results. The verifier must remain non-zero for absent, stale, incomplete or differently bound evidence.

## 7. Installed-product gate

Install the exact shipped package basis into an isolated Codex home. Run Doctor and require no blocking product-health failure. Directly observe the two public Skill entries and verify that managed profiles become selectable after the documented fresh-session boundary when required.

Also exercise explicit update/check documentation against the shipped CLI surface so public commands cannot drift from argparse/runtime behavior.

## 8. Final sequence

```text
final release-source repository matrix PASS
product-surface consistency PASS
real Host N0-N8 PASS on current Host qualification identity
fresh final-source Advisor Final Review PASS
external release evidence verifies
installed Doctor has no blocking failure
human two-Skill App observation PASS
merge approved source
create v4.0.0 versioned semantic-version tag
verify Marketplace resolves the exact tagged source
publish release notes
```

If a Host gate is unavailable or fails, record the qualification basis as repository-complete and release-blocked. `PENDING`, `UNKNOWN` and `NOT TESTED` are not PASS.
