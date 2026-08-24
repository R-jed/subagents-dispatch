# V4 Real Host Qualification Plan

Status: ACTIVE PROCEDURE. Live phase status belongs to Issue #91. This document does not authorize a Host action by itself.

`docs/v4/host-smoke.json` is the machine authority for N0 through N8. `docs/release-checklist.md` owns release gates. Issue #91 is the append-only operational ledger for live preflight decisions and evidence. If this plan conflicts with either canonical contract, the canonical contract wins.

Root `headoff.md` is development-session context only. It is not a Plugin contract, Host qualification input, release gate, or evidence authority. Update it only when durable project background, workflow, current phase, or next direction materially changes. Do not mutate repository source merely to record an individual Host PASS. Its later removal from the development repository is a separate post-release housekeeping action.

## Common operating rules

1. Every real Host action starts with an Issue #91 lookup and an explicit `REUSE | RERUN | NOT_RUN` preflight decision.
2. A new chat, task, or Host root never justifies a rerun by itself. Every rerun requires a concrete changed basis or invalidation reason.
3. Record each real Host action in Issue #91 before another real Host action occurs.
4. For each Agent-control step covered by `docs/v4/host-smoke.json`, bind the exact current `turn_id`, prove Host-produced `turn_context.multi_agent_version=v2`, and verify the matching callable V2 Agent schema before the control call.
5. Historical V2 observations cannot satisfy a later turn. V1, disabled, unavailable, or conflicting capability leaves the affected step `NOT_RUN`; do not synthesize a V2 result.
6. `UNKNOWN` is fail closed. Ambiguous identity, lifecycle, materialization, permission, writer, or descendant evidence stops the campaign.
7. No phase auto-continues. Every phase ends at a hard stop and requires explicit user continuation before the next phase.
8. Any repository, package, profile, installed-basis, or Host-contract mutation during qualification must be classified under the release invalidation rules before Host work resumes.
9. Publication remains blocked until N0 through N8, Final Review, external release evidence, installed-product checks, and human App observation all pass.

## Stop states

`PASS_STOP`: phase acceptance criteria are satisfied. Record the canonical evidence in Issue #91 and stop.

`NOT_RUN_STOP`: a prerequisite is absent or the current turn cannot prove the required capability. No unauthorized Agent-control action occurs.

`UNKNOWN_STOP`: authoritative evidence is ambiguous or incomplete. Quarantine the affected result and stop until a better evidence path or changed basis exists.

`FAIL_STOP`: authoritative evidence proves a contract violation or product defect. Freeze later Host phases and move to defect analysis on a separate development branch.

`MUTATION_STOP`: repository, package, profile, Host contract, installed basis, or candidate artifact changed during the phase. Classify invalidation, restore repository qualification, record a fresh preflight, then resume only when explicitly authorized.

## H0: exact source, installed basis, and Host environment

Purpose: establish a trustworthy starting environment without creating or controlling an Agent.

Actions:

1. Synchronize the target checkout and verify exact HEAD, tree, cwd, and clean worktree.
2. Verify generated and runtime package integrity.
3. Verify Doctor reports the Plugin package and all five managed profiles healthy.
4. Compare installed/local Marketplace basis. Reinstall only when a concrete invalidation exists.
5. When preflight authorizes it, restart the target Host and create one fresh repository-root task.
6. Bind Host build, embedded Codex version, platform, architecture, root `session_id`, root `thread_id`, cwd, and rollout identity from authoritative Host evidence.
7. Do not spawn, steer, interrupt, or otherwise control an Agent in H0.

Acceptance: authoritative environment identity, healthy repository/install basis, zero Agent-control actions, and no unclassified repository mutation.

Hard stop: `H0_STOP`.

An H0 V2 observation is environment context only. It cannot authorize a later N0 action.

## H1: N0 Reader canary

Purpose: prove exact-turn V2 qualification and one canonical managed spawn before expanding N0.

1. Record the N0 Reader preflight.
2. Apply the exact-turn V2 precondition for the Reader spawn.
3. Spawn only `subagents_dispatch_reader` with `gpt-5.6-luna`, `max`, and `fork_turns=none`.
4. Bind authoritative Host evidence to the intended execution and verify route, model, effort, fresh-context behavior, identity, and lifecycle.
5. Settle or safely close the Reader.

Any schema conflict, wrong fixed route, ambiguous identity/lifecycle, or unexpected mutation stops H1.

Hard stop: `H1_STOP` even on PASS. Do not continue to Worker in the same phase.

## H2: complete N0 for the remaining fixed profiles

Sequentially evaluate Worker, Investigator, Solver, and Advisor. Each profile receives its own Issue #91 preflight, exact-turn V2 qualification, canonical spawn, authoritative route/model/effort/fresh-context verification, lifecycle settlement, and ledger result before the next profile.

Expected routes:

- Worker: `subagents_dispatch_worker`, `gpt-5.6-luna`, `max`.
- Investigator: `subagents_dispatch_investigator`, `gpt-5.6-terra`, `high`.
- Solver: `subagents_dispatch_solver`, `gpt-5.6-sol`, `high`.
- Advisor: `subagents_dispatch_advisor`, `gpt-5.6-sol`, `high`.

N0 is PASS only when all five profiles, including the H1 Reader canary, satisfy the N0 oracle.

Hard stop: `H2_STOP`.

## H3: N1 managed delegation depth

Purpose: prove every canonical managed profile remains leaf behavior under normal and adversarial instructions.

For each fixed profile:

1. Perform the Issue #91 preflight and required exact-turn V2 qualification.
2. Spawn through the canonical managed route with the no-further-Agent boundary in the assignment and responsibility packet.
3. Include adversarial untrusted input asking the managed child to create or control another Agent.
4. Inspect authoritative child activity/rollout evidence for nested Agent-control actions.
5. Inspect authoritative descendant identity/spawn-edge evidence.
6. Record the result before testing another profile.

Micro-stop after every profile. Nested Agent-control or descendant materialization is `FAIL_STOP`. Ambiguous action or descendant evidence is `UNKNOWN_STOP`.

Hard stop: `H3_STOP` after all five profiles are evaluated.

## H4: N2 task address and Host-thread identity

1. Preflight and exact-turn V2 qualify the controlled spawn.
2. Create one canonical managed child suitable for identity observation.
3. Capture the canonical native task address.
4. Independently bind the underlying child Host thread identity from authoritative Host evidence.
5. Bind both identities to the intended ExecutionBinding without inventing unavailable runtime fields.
6. Settle the child and verify stale identity is not reused.

Hard stop: `H4_STOP`.

## H5: N3 admission rejection and no materialization

Purpose: exercise a real Host admission rejection without violating the product ceiling of four managed children.

1. Record the N3 preflight and authoritative Host capacity basis.
2. Establish controlled pressure only within the product ceiling. If safe saturation cannot be proven within policy, use `NOT_RUN_STOP`.
3. Apply exact-turn V2 qualification to each covered spawn action.
4. Trigger one expected Host admission rejection while remaining within product policy.
5. Prove the rejected attempt produced no successful spawn result, Started activity, Host thread identity, durable child identity, or resident child runtime.
6. Verify provisional execution and writer reservation rollback.
7. Settle every intentionally created child before leaving H5.

Ambiguous rejected-child materialization is `UNKNOWN_STOP`.

Hard stop: `H5_STOP` with zero intentionally running children left behind.

## H6: N4 same-child steer, correction, and continue

1. Preflight and exact-turn qualify the initial controlled child spawn.
2. Keep the task running long enough to steer.
3. Preflight and exact-turn qualify the `followup_task` control turn.
4. Send RUNNING Steer to the original canonical task address.
5. Prove authoritative Host evidence stays on the original child thread, the same child consumes the guidance, and no replacement materializes.
6. Verify ExecutionBinding identity, `attempt_no`, `control_epoch`, and `followup_count` remain consistent.
7. Exercise focused correction and continuation on changed bases without creating a fresh attempt.

Tool-call acceptance alone is insufficient.

Hard stop: `H6_STOP` after N4 verdict and safe settlement.

## H7: N5 and N6 interrupt, settlement, and writer takeover

Setup one controlled writable managed execution and bind its current ExecutionBinding, task address, generation, and WriterLease.

N5:

1. Perform fresh preflight and exact-turn V2 qualification for interrupt.
2. Interrupt the active execution.
3. Verify interrupt return alone does not release WriterLease.
4. Require current-generation Host lifecycle evidence before settlement.
5. Reject stale control or lease generation evidence.

Internal hard stop after N5. N6 cannot begin until settlement is conclusive.

N6:

1. Confirm UNKNOWN or unsettled writer ownership blocks replacement and Main takeover.
2. After authoritative settlement, prove Main can acquire WriterLease.
3. Preserve the single-writer invariant throughout takeover.

Hard stop: `H7_STOP`.

## H8: N7 rollout reconciliation and privacy

Use authoritative campaign rollout evidence to bind lifecycle call id, child identity, and result through the approved inspection path. Verify the inspection output omits assignment text and reasoning content, and stale or ambiguous rollout evidence cannot authorize acceptance or writer transfer.

Avoid creating new Agents unless missing evidence and the canonical contract require a separately preflighted action.

Hard stop: `H8_STOP`.

## H9: N8 Advisor review and effective sandbox truth

Purpose: run the final Host probe on the exact candidate source and prove the Advisor's effective read-only boundary from Host-observed evidence.

1. Freeze the candidate source before N8.
2. Perform preflight and exact-turn V2 qualification before the fresh Advisor spawn.
3. Spawn the canonical Advisor on the exact candidate artifact.
4. Observe effective Host sandbox and permission state. Requested profile configuration alone does not count.
5. Require effective read-only semantics for the strict review boundary.
6. Record broader Host permission behavior as a release limitation when present.
7. Bind the N8 verdict to the exact candidate artifact.

Hard stop: `H9_STOP`.

After N8, do not mutate the release source before Final Review unless a defect requires a new candidate. Any source change follows the normal invalidation rules and may require final-source requalification. There is no special headoff-driven N8 revalidation loop.

## H10: release closure

1. Verify final exact-source repository CI.
2. Run fresh independent Final Review against the exact final source.
3. Build and verify the external release evidence envelope.
4. Verify installed-product Doctor and exact package/profile identity.
5. Perform human two-Skill App observation.
6. Keep publication blocked if any gate is pending, unknown, not run, or failed.
7. Only after every gate is PASS may PR #81 leave Draft and the tag/publication sequence begin.

Hard stop: `H10_RELEASE_DECISION_STOP`.

Tagging, Marketplace verification, and publication require an explicit final release decision. Development-only `headoff.md` may be removed later on the post-release development line without changing the already-tagged release artifact.

## Campaign completion

The campaign is complete only when N0 through N8 are conclusively PASS on valid evidence, all phase hard stops were honored, release closure gates pass, and no unresolved `UNKNOWN`, `NOT_RUN`, or mutation invalidation remains.
