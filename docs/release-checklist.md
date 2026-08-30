# 1.0.0 Release Checklist

Use this checklist for the first public `1.0.0` release built on Native Core V4. Repository completion does not imply Host release readiness.

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

`.codex-plugin/plugin.json`, Marketplace metadata and the current changelog must agree on `1.0.0` before tagging. Use the versioned semantic-version tag `v1.0.0` only after all release gates pass, then verify Marketplace installation resolves the exact tagged source. Resolving a ref to the expected commit does not by itself prove platform-enforced tag immutability.

## 2. Repository gates

The exact release source must pass the canonical GitHub Actions matrix:

```text
Ubuntu / Python 3.11
Ubuntu / Python 3.12
macOS / Python 3.11
Windows / Python 3.11
```

Required checks include Plugin/Marketplace validation, package-integrity regeneration, official Plugin validator, Ruff, full pytest, managed profile install/check/uninstall lifecycle, Doctor, Native Core state/work graph/scheduler/lifecycle/writer tests, update lifecycle tests, unsupported pre-1.0 state rejection tests and product-surface consistency tests.

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
TeamPlan and TeamPlan revision are absent from current product state and contracts
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
unsupported pre-1.0 state is rejected; no migration or stale-state cleanup path ships
plan-only creates no runtime state, lease or Host action
```

## 4. Real Codex Host gate

`docs/v4/host-smoke.json` is the machine-readable authority. Bind each campaign environment to the exact root `session_id` and `thread_id` before any N0/N1 child spawn. Public Host/session metadata is preferred. The machine contract defines the permitted Host-produced fallback evidence and the `UNKNOWN` policy when either identity remains unavailable.

Desktop Host lifecycle is an operator boundary. A qualifying Codex task must never quit, restart, relaunch, or update the Desktop Host and must never claim it created its own post-restart replacement root. If a restart or fresh root is required, the task stops with `OPERATOR_ACTION_REQUIRED_STOP`, the operator performs the UI/lifecycle action, and a new/current root task collects the post-action evidence.

Environment identity does not prove that a later probe turn still exposes the Native Subagent V2 control surface. Before every Host Agent-control step covered by the machine contract, bind the exact probe `turn_id` to Host-produced `turn_context.multi_agent_version=v2` and verify that the callable schema for that same turn is V2-shaped. For spawn, `task_name` and `message` are required, `fork_turns` is present, and legacy `fork_context` is absent. A V2 observation from another turn in the same session is historical capability evidence only. If the current turn is V1, disabled, unobservable, or the turn context and callable schema conflict, record the affected step as `NOT_RUN` and do not invoke an Agent-control tool.

The external Host campaign must also bind the current Host qualification identity from the runtime package manifest, managed profile contract and Host campaign contract. Git commit/tree are release-source identity and do not by themselves determine whether Host evidence remains reusable.

Issue #91 is the append-only Host evidence journal for this release campaign. It should contain durable phase/profile results, meaningful stops, material invalidations, and RCAs. A separate GitHub comment is not required before every Host action. Routine preflight reasoning, independent review restatements, and amendments should not be emitted as separate ledger entries when one consolidated result record can preserve the same evidence.

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
```

For N0 H1/H2 single-profile probes, use the maintainer-only qualification guard with a local `qualification_run_ref` in the form `qualification:<campaign>:<h1|h2>:<profile>`. This local ref binds the first ExecutionBinding before Host spawn without making an Issue comment id part of runtime or qualification-tool semantics. A consumed qualification WorkUnit cannot be fresh-retried merely to repair bookkeeping or evidence presentation.

For N1, run the canonical managed route for every fixed profile. Confirm the managed assignment includes the no-further-Agent boundary, include an adversarial untrusted-input request to create or control another Agent, and inspect authoritative Host activity plus descendant identity/spawn-edge evidence. Any managed child that issues nested Agent creation/control or materializes a descendant fails N1. Ambiguous evidence is UNKNOWN. A generic V2 child that is explicitly forced to recurse demonstrates Host capability only and cannot by itself decide the managed N1 verdict.

For N4, successful `followup_task` tool-call acceptance is not sufficient by itself. Release evidence must show that the RUNNING Steer targeted the original canonical task address, stayed bound to the original Host child with no replacement materialized, and was consumed by that same child. Steer must preserve the ExecutionBinding, `attempt_no`, `control_epoch`, and `followup_count`. Correction and Continue remain same-child controls and must not create a fresh attempt.

Offline CI, source inspection, profile configuration, model self-report or evidence from another Host qualification basis cannot substitute for required real Host observations. Profile configuration and project `max_depth=1` establish product intent but do not prove Host-hard descendant isolation.

Final Review is not a Host-campaign probe. The fresh final-source Advisor review runs after N0-N7 and records the Advisor's actual permission observation. When the Host enforces read-only, use the `enforced_read_only` assurance path. When the Host positively reports broader write capability, the review may use `artifact_immutability_fallback` only when hard isolation is not required, Advisor semantic mutation authority remains `none`, the review prompt explicitly forbids edits and external side effects, the exact review artifact is unchanged before/after, and the broader permission state is disclosed as residual risk. Unobservable permission, hard-isolation mismatch, or artifact mutation is `INSUFFICIENT_EVIDENCE`/failure, not PASS.

## 5. Stability and invalidation

Classify every post-evidence change before deciding whether Host work must be repeated.

If `.codex-plugin/package-integrity.json`, `contracts/policy.json` or `docs/v4/host-smoke.json` changes in a way that changes its qualification digest, the Host qualification basis changed. The release verifier must also regenerate the runtime-file projection and reject a stale package manifest that omits a newly added runtime file. Refresh the qualification identity and repeat every affected Host probe.

If only source outside that qualification basis changes, such as `headoff.md`, ordinary documentation, or release tooling that is not part of the shipped package manifest, keep the existing Host campaign only when all three qualification digests are proven unchanged. Refresh the exact release source commit/tree, rerun the repository checks affected by the source change, and run a fresh Final Review against the final source state.

Host environment changes are separate from source identity. A Host build/version change invalidates Host observations bound to the previous environment and requires a new H0 environment binding before further Agent-control on the new environment.

Do not decide reuse from file names alone. Compare the qualification digests, Host environment identity, machine-contract requirements, and the durable evidence journal. Record a new Issue #91 entry only when the classification materially changes campaign state or when a conclusive phase/profile result is reached.

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
unsupported pre-1.0 state rejection
```

## 6. Final Review and release evidence

After deterministic checks and N0-N7 pass for the current Host qualification identity, bind a Main-owned pre-review request and then run one fresh independent Final Review against the exact final release source under `contracts/final-review.md`.

The pre-review request is created before Advisor launch and must bind the exact final commit/tree, current `review_artifact_id`, `hard_isolation_required`, the required no-edit/no-external-side-effect instruction, exact Advisor agent type, `fork_turns=none`, fresh context, and an external evidence reference. The Final Review result must reference the canonical SHA-256 of that request. The verifier checks static request/result/current-source consistency; it does not independently prove temporal ordering. The trusted release/CI operator must preserve external evidence showing the request existed before Advisor launch and the review result came afterward. Missing chronology evidence keeps the release incomplete.

The Final Review evidence must bind the exact final commit/tree and current `review_artifact_id`, and record at minimum:

```text
verdict = ship
review_request_sha256
permission_observation
assurance_mode
artifact_unchanged = true
hard_isolation_required
no_edit_instruction = true
residual_risk
evidence_ref
```

`artifact_immutability_fallback` is an exact-candidate safeguard, not a claim of Host-enforced isolation. `review-artifact.py` intentionally excludes ignored build/cache artifacts and cannot prove absence of external side effects.

Then verify the external release evidence with:

```text
<python-3.11+> scripts/release_evidence_v4.py --repo <candidate-root> --evidence <external-release-evidence>
```

The release envelope must bind the final Git commit/tree and current qualification digests. Its nested Host campaign binds only the Host qualification identity, environments and N0-N7 results. The separate Final Review object binds the exact release source and its assurance evidence. The verifier must remain non-zero for absent, stale, incomplete, permission-ambiguous, mutated, hard-isolation-incompatible, or differently bound evidence.

## 7. Installed-product gate

Install the exact shipped package basis into an isolated Codex home. Run Doctor and require no blocking product-health failure. Directly observe the two public Skill entries and verify that managed profiles become selectable after the documented fresh-session boundary when required.

Also exercise explicit update/check documentation against the shipped CLI surface so public commands cannot drift from argparse/runtime behavior.

## 8. Final sequence

```text
merge approved source into the release line and freeze the exact release commit
final release-source repository matrix PASS on that frozen commit
product-surface consistency PASS
real Host N0-N7 PASS on current Host qualification identity
fresh final-source Advisor Final Review PASS
external release evidence verifies
installed Doctor has no blocking failure
human two-Skill App observation PASS
create v1.0.0 versioned semantic-version tag
verify Marketplace resolves the exact tagged source
publish release notes
```

If a Host gate is unavailable or fails, record the qualification basis as repository-complete and release-blocked. `PENDING`, `UNKNOWN` and `NOT TESTED` are not PASS.
