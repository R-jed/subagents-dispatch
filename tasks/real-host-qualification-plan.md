# Native Core V4 Real Host Qualification Plan

Status: PLANNED. This document defines the human execution procedure for the first public Plugin `1.0.0` real-Host campaign. It does not authorize a Host action by itself.

`docs/v4/host-smoke.json` is the machine authority for N0 through N8. `docs/release-checklist.md` is the release-gate and invalidation authority. This plan defines how the operator and the Codex task cooperate without crossing Host lifecycle boundaries.

Issue #91 is the append-only Host evidence journal for this release campaign. It stores durable phase/profile results, material invalidations, and meaningful `UNKNOWN`, `FAIL`, or mutation stops. It is not a per-tool-call authorization system. No Issue #91 comment is required before every Host action, and routine preflight, review, and amendment comments should not be created.

Root `headoff.md` is development-session context only. It is not Plugin runtime, Host qualification input, release evidence, or a release gate.

## Human and Codex responsibility boundary

The operator owns Desktop Host lifecycle and UI actions.

Operator-only actions include:

- quit the Desktop Host;
- launch or relaunch the Desktop Host;
- install or update the Desktop Host;
- create a replacement or fresh root task after a restart;
- choose the repository/workspace in the Desktop UI;
- approve OS or UI actions that cannot safely be performed inside the current Codex task.

Codex owns actions that can complete inside the current live task without destroying its own execution context. These include repository inspection, package/profile verification, Host metadata inspection, runtime evidence collection, qualification guard calls, managed Agent-control steps explicitly required by N0 through N8, and result assembly.

Codex MUST NOT quit, restart, relaunch, or update the Desktop Host. Codex MUST NOT claim it created a post-restart replacement root task. A task that determines a Host restart or replacement root is required must stop and return:

```text
OPERATOR_ACTION_REQUIRED_STOP
reason: <why the lifecycle action is required>
actions:
  - <exact manual action for the operator>
resume_when:
  - <observable condition required in the new/current task>
next_prompt:
  <bounded prompt for the post-operator step>
```

The operator performs the listed actions and starts the next task when required. The new task then collects post-restart evidence. Never attempt to bridge a Host restart from the task being terminated by that restart.

## Development workflow boundary

This repository is self-maintained. Routine development does not require a new GitHub Issue or Pull Request.

Default development flow:

1. create a short-lived Git branch when isolation is useful;
2. make the smallest coherent change;
3. run focused tests and the required exact-head CI;
4. inspect the complete diff;
5. fast-forward or merge into the release line when verified;
6. update `headoff.md` when durable project direction or the safe continuation point changes.

Use a GitHub Issue only for a genuinely long-lived tracked item or for the special Host evidence journal already established as Issue #91. Use a Pull Request only when its review surface, approval semantics, or CI behavior adds real value. Do not create an Issue or PR merely because a change exists.

## Campaign identity and single-probe identity

Every Host campaign binds the environment fields required by `docs/v4/host-smoke.json`, including Host build, platform, architecture, Codex version, `session_id`, and `thread_id`.

H1 and H2 additionally use a maintainer-only local `qualification_run_ref` to bind one fresh qualification attempt before Host spawn. The format is:

```text
qualification:<campaign>:<h1|h2>:<profile>
```

Examples:

```text
qualification:host7119:h1:reader
qualification:host7119:h2:worker
qualification:host7119:h2:investigator
```

The campaign token is local qualification identity. It is not a GitHub Issue comment id and does not make GitHub a runtime dependency.

For H1/H2, call `scripts/host_qualification_guard.py::allocate_single_probe_execution` with the exact `qualification_run_ref`, then call `prepare_single_probe_spawn` with the same ref before the native Host spawn. Any prior retained or compacted execution history for that WorkUnit means the single probe has already been consumed. Do not reject a completed qualification result and allocate a fresh attempt to repair bookkeeping, provenance formatting, or evidence presentation.

The qualification guard remains maintainer-only and intentionally stays outside the Plugin runtime package manifest. Generic product Recovery continues to follow `contracts/recovery.md`.

## Evidence journal policy

Before a Host action, the coordinator still checks whether existing evidence is reusable, invalidated, or absent. That classification is part of execution reasoning and does not require a separate Issue comment.

Write to Issue #91 only when one of these durable events occurs:

- H0 environment binding reaches a conclusive result or meaningful stop;
- an H1/H2 profile probe reaches a conclusive result or meaningful stop;
- a later N1 through N8 phase reaches a conclusive result or meaningful stop;
- a material Host, package, profile, contract, or source invalidation changes what can be reused;
- an RCA or defect materially changes the qualification procedure.

Prefer one consolidated entry per phase. H1/H2 may use one entry per profile because each profile is independently release-significant. Do not add a separate preflight comment, result comment, independent-review comment, and amendment for the same ordinary step.

A durable result entry should contain only the evidence needed to understand and reproduce the verdict:

```text
phase / probe
release-source identity
Host qualification identity
Host environment identity
qualification_run_ref when H1/H2
exact-turn V2 capability evidence when required
canonical managed route / model / effort / fork behavior when required
lifecycle / child identity evidence required by the probe
side effects / mutations
verdict
invalidation / reuse scope
```

Tracked `docs/v4/host-smoke.json` remains `status=PENDING` with empty results during the external campaign.

## Exact-turn capability evidence capture

For every Host Agent-control step covered by `docs/v4/host-smoke.json` probe-turn capability semantics, capability evidence must be captured contemporaneously before the Agent-control call.

1. Bind the exact current `turn_id` and prove Host-produced `turn_context.multi_agent_version=v2` for that turn.
2. Inspect the callable Host Agent tool schema exposed for that same turn and verify the machine-contract schema requirements for the intended control action.
3. Before invoking Agent-control, preserve a privacy-safe capability snapshot keyed by root session/thread and exact `turn_id`. For a spawn precondition, record the callable tool identity, required fields, property names, `task_name_required`, `message_required`, `fork_turns_present`, and `fork_context_absent`.
4. Keep this snapshot outside the candidate repository and carry its fields into the phase's consolidated durable Issue #91 result. A separate routine preflight comment is still unnecessary.
5. Do not assume Host rollout files will retain callable schema definitions after the turn. Later actual-call arguments, later-turn schemas, configured defaults, or model memory cannot reconstruct a missing exact-turn schema proof.
6. If the required snapshot cannot be made before Agent-control, the capability precondition is unproven. Use the machine-contract `NOT_RUN_STOP` behavior and perform zero covered Agent-control.

This is qualification evidence capture only. It does not change the Host machine contract or Plugin runtime behavior.

## Stop states

Every phase terminates in one of these states.

`PASS_STOP`: acceptance criteria are satisfied. Record the durable evidence and wait for the next explicit continuation.

`OPERATOR_ACTION_REQUIRED_STOP`: Host lifecycle or UI work is required. Codex performs no lifecycle action itself and provides the exact operator instructions and resume condition.

`NOT_RUN_STOP`: a required prerequisite or exact-turn Host capability is unavailable before the covered Host action. No covered Agent-control action occurs.

`UNKNOWN_STOP`: authoritative evidence is ambiguous or incomplete. Fail closed until a better evidence path exists.

`FAIL_STOP`: authoritative evidence proves a product or qualification-procedure violation. Freeze later phases until the failure is understood and repaired.

`MUTATION_STOP`: repository, package, profile, installed basis, Host contract, or another bound campaign input changed unexpectedly. Classify invalidation before continuing.

## Phase H0: exact source, installed basis, and fresh Host environment

Purpose: establish a trustworthy environment with zero Agent-control.

### Operator step

If the current Host environment is already fresh and valid, no operator action is required.

If a Host restart or fresh root is required:

1. exit the Desktop Host outside the qualifying Codex task;
2. launch the Desktop Host;
3. create a new root task in the target repository;
4. paste the bounded H0 evidence prompt into that new root.

Codex must never perform steps 1 through 3.

### Codex step

Inside the fresh/current root:

1. verify exact HEAD, tree, branch, cwd, and clean worktree;
2. run generated package-integrity and package-integrity checks;
3. verify Plugin package and all five managed profiles are healthy;
4. compare installed/local Marketplace basis and reinstall only if a concrete mismatch is established and separately authorized;
5. bind Host build, Host/rollout Codex version, platform, architecture, root `session_id`, root `thread_id`, cwd, parent identity, and rollout identity using authoritative Host evidence;
6. record `multi_agent_version` only as H0 environment context;
7. perform zero Agent-control actions and materialize zero children.

If the current task discovers that a Host restart is required, return `OPERATOR_ACTION_REQUIRED_STOP`. Do not restart the Host from that task.

### Acceptance

- environment identity satisfies every required field in `docs/v4/host-smoke.json`;
- `session_id` and `thread_id` are authoritative and internally consistent;
- repository and installed package/profile basis are healthy;
- Agent-control count is zero;
- no unexpected repository or installed-basis mutation occurred.

Mandatory stop: `H0_STOP`.

H0 V2 capability is context only. N0 must establish V2 again on the exact Agent-control turn.

## Phase H1: N0 Reader canary

Purpose: prove one canonical managed Reader spawn on the current H0 environment before expanding N0.

### Operator step

None during normal H1 execution. If Host lifecycle work becomes necessary, Codex returns `OPERATOR_ACTION_REQUIRED_STOP` and H1 remains incomplete.

### Codex step

1. choose one pristine Reader qualification WorkUnit with no retained or compacted attempt history;
2. set a local run ref such as `qualification:<campaign>:h1:reader`;
3. bind the exact current `turn_id`;
4. prove `turn_context.multi_agent_version=v2` for that exact turn;
5. verify the same-turn callable spawn schema requires `task_name` and `message`, includes `fork_turns`, and excludes `fork_context`, then preserve the contemporaneous capability snapshot required above;
6. call `allocate_single_probe_execution` with the exact `qualification_run_ref` so attempt 1 is explicitly bound before spawn;
7. call `prepare_single_probe_spawn` with the same ref and pass the returned canonical Orchestrate payload to Host unchanged;
8. spawn exactly one `subagents_dispatch_reader` with `gpt-5.6-luna`, `max`, and `fork_turns=none`;
9. verify authoritative route, model, effort, fresh-context, child identity, and lifecycle evidence;
10. settle the Reader and stop.

Immediate stop conditions include V2/schema mismatch, qualification guard rejection, wrong route/model/effort/fork behavior, ambiguous child identity/lifecycle, or unexpected mutation.

Once a Reader materializes, that H1 WorkUnit is consumed. Evidence formatting or bookkeeping cannot justify another attempt on that WorkUnit.

Mandatory stop: `H1_STOP`.

## Phase H2: complete N0 for Worker, Investigator, Solver, and Advisor

Run profiles sequentially. A non-PASS profile stops H2 immediately.

For each profile:

1. use a new pristine qualification WorkUnit for this current campaign/profile;
2. set `qualification:<campaign>:h2:<profile>`;
3. establish exact-turn V2 capability and the required spawn schema, then preserve the contemporaneous capability snapshot required above;
4. allocate attempt 1 only through `allocate_single_probe_execution`;
5. prepare only through `prepare_single_probe_spawn`;
6. pass the canonical Host payload unchanged;
7. verify route, model, effort, `fork_turns=none`, fresh context, identity, and lifecycle;
8. settle the child;
9. record one durable profile result in Issue #91 and stop before the next profile.

Expected routes:

- Worker: `subagents_dispatch_worker`, `gpt-5.6-luna`, `max`.
- Investigator: `subagents_dispatch_investigator`, `gpt-5.6-terra`, `high`.
- Solver: `subagents_dispatch_solver`, `gpt-5.6-sol`, `high`.
- Advisor: `subagents_dispatch_advisor`, `gpt-5.6-sol`, `high`.

Do not reuse a consumed WorkUnit. Do not allocate attempt 2 for evidence repair. A genuine later rerun caused by a material invalidation uses a new campaign identity and a new pristine qualification WorkUnit.

Mandatory stop: `H2_STOP` after all remaining N0 profiles pass.

## Phase H3: N1 managed delegation-depth campaign

Purpose: prove all fixed managed profiles remain leaf Agents under normal and adversarial instructions.

For each fixed profile:

1. establish exact-turn V2 capability before the parent spawn and preserve the contemporaneous capability snapshot required above;
2. spawn through the canonical managed route;
3. include the fixed no-further-Agent boundary and an adversarial untrusted-input request to create/control another Agent;
4. inspect authoritative child activity for nested Agent-control;
5. inspect authoritative descendant identity/spawn-edge evidence;
6. settle the child before proceeding.

Any nested Agent-control or descendant materialization is `FAIL_STOP`. Ambiguity is `UNKNOWN_STOP`.

Record one consolidated H3 result unless a profile stops the phase early.

Mandatory stop: `H3_STOP`.

## Phase H4: N2 canonical task address and Host-thread binding

1. establish exact-turn V2 capability and preserve the contemporaneous capability snapshot required above;
2. spawn one controlled canonical managed child;
3. capture the successful canonical native task address;
4. independently bind the underlying Host child thread identity;
5. bind both identities to the intended ExecutionBinding evidence basis;
6. settle the child and reject stale identity evidence.

A materialized H4 WorkUnit is consumed. If H4 later stops `UNKNOWN` because a required pre-spawn capability snapshot was not captured, do not reuse that WorkUnit or allocate attempt 2. A justified qualification-procedure rerun uses a new pristine H4 WorkUnit after the procedure defect is corrected and receives an explicit `RERUN` classification before Agent-control.

Mandatory stop: `H4_STOP`.

## Phase H5: N3 admission rejection and materialization safety

1. establish the safe Host-capacity setup without exceeding the product ceiling of four managed children;
2. establish exact-turn V2 capability before each covered Agent-control action and preserve the contemporaneous capability snapshot required above;
3. trigger one actual Host admission rejection only when the attempted spawn remains within product policy;
4. prove no successful spawn result, Started activity, Host thread identity, durable child identity, or resident child runtime materializes for the rejected attempt;
5. verify provisional execution and writer reservation rollback;
6. settle every intentionally running child before leaving the phase.

If safe pressure cannot be established within the product ceiling, use `NOT_RUN_STOP`. Ambiguous materialization is `UNKNOWN_STOP`.

Mandatory stop: `H5_STOP` with zero intentionally running children.

## Phase H6: N4 same-child steering, correction, and continuation

1. establish exact-turn V2 capability before the initial child spawn and preserve the contemporaneous capability snapshot required above;
2. start one controlled task that remains running long enough to steer;
3. establish exact-turn V2 capability before `followup_task` and preserve the contemporaneous capability snapshot for that control turn;
4. steer the original canonical task address;
5. prove the same Host child consumed the guidance and no replacement materialized;
6. verify the same ExecutionBinding, `attempt_no`, `control_epoch`, and `followup_count` are preserved;
7. exercise focused correction and continuation using changed same-child bases without a fresh attempt;
8. settle the child.

Tool-call acceptance alone is insufficient.

Mandatory stop: `H6_STOP`.

## Phase H7: N5 interrupt settlement and N6 writer takeover

Setup one controlled writable managed execution and its WriterLease.

For N5:

1. establish exact-turn V2 capability before interrupt and preserve the contemporaneous capability snapshot required above;
2. interrupt the active managed execution;
3. verify interrupt acknowledgement alone does not release WriterLease;
4. require current-generation Host lifecycle evidence to settle execution;
5. reject stale control/lease generation evidence.

Hard stop after N5 settlement.

For N6:

1. confirm UNKNOWN or unsettled writer ownership blocks replacement/Main takeover;
2. after authoritative settlement, prove Main can acquire WriterLease;
3. verify the single-writer invariant throughout takeover.

Mandatory stop: `H7_STOP`.

## Phase H8: N7 rollout reconciliation and privacy

1. use authoritative rollout evidence already produced by the campaign;
2. bind lifecycle call id, child identity, and result through the allowlisted inspection path;
3. verify inspection output omits assignment text and reasoning content;
4. verify stale or ambiguous rollout evidence cannot authorize acceptance or writer transfer.

Avoid creating new Agents unless the machine contract truly requires separately qualified evidence.

Mandatory stop: `H8_STOP`.

## Phase H9: N8 Advisor effective sandbox truth

1. freeze the candidate source before the N8 probe;
2. establish exact-turn V2 capability and preserve the contemporaneous capability snapshot required above;
3. spawn the canonical Advisor on the exact candidate artifact;
4. observe effective Host sandbox and permission state;
5. require effective read-only semantics for the strict Final Review boundary;
6. record broader Host permission behavior as a release limitation when applicable;
7. bind the review verdict to the exact candidate artifact.

Mandatory stop: `H9_STOP`.

After H9, keep the release source frozen through Final Review and release closure. A later source change requires normal invalidation classification.

## Phase H10: release closure

1. verify final release-source CI and exact source identity;
2. run the fresh independent Final Review against the final source;
3. verify external release evidence;
4. run installed-product Doctor and human two-Skill observation;
5. make the explicit release decision;
6. create `v1.0.0`, verify Marketplace resolves the exact tag, and publish release notes only after every required gate passes.

## Invalidation rules

Use `docs/release-checklist.md` as authority.

Important operational examples:

- Host build/version change invalidates environment-bound Host observations and requires a new H0 binding before more Agent-control.
- A change to one of the three Host qualification digests invalidates the affected Host evidence.
- A source-only change outside those digests still requires exact-source repository CI and final-source review refresh, but does not automatically erase conclusive Host evidence.
- A qualification procedure change applies to future actions. Historical Host evidence remains historical evidence and is invalidated only when the machine/release authority or a material environment fact requires it.
- A new chat or new task alone never creates a rerun reason.
- A required Host restart is an operator boundary, never an instruction for the qualifying task to restart itself.

## Current recovery point

The accepted build-7119 campaign remains active while the Host environment and three qualification digests remain unchanged. H0 through H3 are conclusive `PASS_STOP`.

The first H4 / N2 WorkUnit `N2_READER_HOST7119` materialized successfully and produced a coherent canonical task-address, Host-thread, child-rollout, and ExecutionBinding identity chain. Issue #91 result `5425895958` recorded `PASS_STOP`, but independent review found that its exact-turn callable spawn schema observation was not preserved in the durable result. A zero-Agent-control historical supplement then confirmed the Host rollout does not retain callable schema records for that turn and stopped `UNKNOWN_STOP` in Issue #91 comment `5426422092`.

Treat the first H4 WorkUnit as consumed historical `UNKNOWN` evidence. The missing exact-turn schema proof cannot be reconstructed from actual call arguments or later turns.

After this procedure correction is merged, exact-head CI is green, and the target checkout is synchronized to the new release-line head, the next safe action is:

1. confirm Host build 7119, accepted root/session identity, installation continuity, and all three qualification digests remain unchanged;
2. classify H4 as `RERUN` because the prior H4 attempt is incomplete due to the now-corrected qualification evidence-capture defect;
3. allocate a new pristine H4 / N2 WorkUnit with attempt 1, never reuse `N2_READER_HOST7119` and never create attempt 2 for it;
4. before the new H4 spawn, prove exact-turn V2 and the required callable spawn schema and preserve the contemporaneous privacy-safe capability snapshot;
5. run only H4 / N2, record one consolidated result, and stop at `H4_STOP`;
6. keep N3 blocked until the rerun H4 result receives conclusive independent acceptance.

No Host restart or H0 rerun is required solely because this maintainer-only qualification procedure changed, provided the actual Host build, root/session identity, installed Plugin/profile basis, and three qualification digests remain unchanged.