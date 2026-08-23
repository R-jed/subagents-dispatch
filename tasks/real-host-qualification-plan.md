# V4 Real Host Qualification Plan

Status: PLANNED. No real Host action is authorized by this document alone.

This file is a human execution plan for the V4 real Codex Host campaign. `docs/v4/host-smoke.json` remains the machine authority for N0 through N8. `docs/release-checklist.md` remains the release-gate authority. Issue #91 remains the append-only authority for live Host preflight decisions and evidence. If this plan conflicts with either canonical contract, the canonical contract wins.

## Operating rules

1. Every real Host action starts with an Issue #91 lookup and an explicit `REUSE | RERUN | NOT_RUN` preflight decision.
2. A new chat, task, or Host root never justifies a rerun by itself. Every rerun requires a concrete changed-basis or invalidation reason.
3. Every real Host action receives its own Issue #91 ledger entry before another real Host action occurs.
4. For every covered Agent-control step, the exact current `turn_id` must prove Host-produced `turn_context.multi_agent_version=v2` and a matching callable V2 Agent schema before the Agent-control call occurs.
5. Historical V2 observations cannot satisfy a later turn. V1, disabled, unavailable, or conflicting capability leaves the affected step `NOT_RUN`, and no compatibility translation may synthesize a V2 result.
6. `UNKNOWN` is fail closed. Ambiguous identity, lifecycle, materialization, permission, or descendant evidence stops the campaign.
7. No phase auto-continues into the next phase. Every phase ends at a mandatory stop point.
8. At every phase stop, update Issue #91 first. Then update root `headoff.md` with a concise durable phase checkpoint before the next phase starts.
9. `headoff.md` is a handoff summary only. It records the phase identifier, terminal phase state, Issue #91 evidence reference, qualification-basis impact, and next permitted phase. Raw logs, detailed runtime evidence, and canonical PASS or FAIL truth remain in Issue #91.
10. A `headoff.md` checkpoint is a source-only mutation when it changes no Host qualification input. After each checkpoint merge, compare the three Host qualification digests before reusing prior Host evidence.
11. Any repository, package, profile, or Host-contract mutation outside the planned checkpoint must stop the campaign until invalidation is classified and repository qualification is restored.
12. Publication remains blocked until N0 through N8, Final Review, external release evidence, installed-product checks, and human App observation all pass.

## Stop states

Every phase terminates in exactly one of these states.

`PASS_STOP`: the phase acceptance criteria are satisfied. Record the phase, update `headoff.md`, and wait for explicit continuation before starting the next phase.

`NOT_RUN_STOP`: a prerequisite is absent or the exact current turn cannot prove the required V2 capability. No covered Agent-control action occurs. Record the blocking basis and stop.

`UNKNOWN_STOP`: authoritative evidence is ambiguous or incomplete. Quarantine the affected result. Do not retry until a better evidence path or concrete changed basis is established.

`FAIL_STOP`: authoritative evidence proves a contract violation or product defect. Freeze later Host phases and move to defect analysis on a separate development branch.

`MUTATION_STOP`: repository, package, profile, Host contract, installed basis, or candidate artifact changed during the phase. Classify invalidation, rerun required repository gates, and perform a fresh Issue #91 preflight before resuming.

## Phase H0: exact source, installed basis, and fresh Host environment

Purpose: establish a trustworthy starting environment without creating or controlling an Agent.

Entry conditions:

- release source is the current `v4/rc5-native-core` head;
- release-source CI is green;
- local checkout can be synchronized to that head;
- Issue #91 preflight is recorded before any Host action.

Actions:

1. Synchronize the target local checkout and verify exact HEAD, tree, cwd, and clean worktree.
2. Verify `python3 scripts/package_integrity.py --check-generated` and `python3 scripts/package_integrity.py`.
3. Verify Doctor reports Plugin package and all five managed profiles healthy.
4. Compare installed/local Marketplace basis. Reinstall only if a concrete installed-package invalidation exists.
5. When preflight authorizes it, fully restart the target Desktop Host and create one fresh root task in the repository.
6. Bind Host build, embedded Codex version, platform, architecture, root `session_id`, root `thread_id`, cwd, and exact rollout identity using authoritative Host evidence.
7. Do not spawn, steer, interrupt, or otherwise control an Agent in H0.

Acceptance:

- environment identity is authoritative and internally consistent;
- repository and installed package/profile basis are healthy;
- no Agent-control action occurred;
- no repository mutation occurred during Host binding.

Mandatory stop: `H0_STOP`.

Important: an H0 V2 observation is environment/capability context only. It cannot authorize a later N0 spawn because N0 must prove V2 again on the exact N0 Agent-control turn.

Headoff checkpoint: record H0 terminal state, Issue #91 evidence label/comment, whether package/profile/Host-contract digests changed, and whether H1 is permitted.

## Phase H1: N0 Reader canary

Purpose: prove the repaired exact-turn V2 precondition and one canonical managed spawn before expanding to all profiles.

Actions within the same N0 Reader probe turn:

1. Record the dedicated N0 Reader preflight in Issue #91.
2. Bind the exact current `turn_id`.
3. Prove `turn_context.multi_agent_version=v2` for that exact turn.
4. Verify the callable V2 spawn schema for that same turn requires `task_name` and `message`, includes `fork_turns`, and excludes `fork_context`.
5. Only if steps 2 through 4 pass, spawn the canonical Reader with `subagents_dispatch_reader`, `gpt-5.6-luna`, `max`, and `fork_turns=none`.
6. Bind the resulting Host evidence to the intended N0 Reader execution and verify route, model, effort, and fresh-context behavior.
7. Settle or safely close the Reader before the phase ends.

Immediate stop conditions:

- exact turn is V1, disabled, unavailable, or schema-conflicting;
- spawn schema differs from the V2 contract;
- wrong route, model, effort, or fork behavior;
- ambiguous child identity or lifecycle;
- unexpected repository mutation.

Mandatory stop: `H1_STOP` even when Reader passes. Do not continue to Worker in the same phase.

Headoff checkpoint: record Reader canary state and the next permitted phase only.

## Phase H2: complete N0 across the remaining fixed profiles

Purpose: close N0 for Worker, Investigator, Solver, and Advisor after the Reader canary has passed.

For each remaining profile, sequentially:

1. Perform a fresh Issue #91 preflight.
2. Re-establish the exact-turn V2 capability precondition before the spawn.
3. Spawn only the fixed canonical route with `fork_turns=none`.
4. Verify authoritative route, model, effort, fresh-context, identity, and lifecycle evidence.
5. Write the action/result ledger entry before touching the next profile.

Expected fixed routes:

- Worker: `subagents_dispatch_worker`, `gpt-5.6-luna`, `max`.
- Investigator: `subagents_dispatch_investigator`, `gpt-5.6-terra`, `high`.
- Solver: `subagents_dispatch_solver`, `gpt-5.6-sol`, `high`.
- Advisor: `subagents_dispatch_advisor`, `gpt-5.6-sol`, `high`.

Any non-PASS profile stops H2 immediately. N0 becomes conclusive PASS only when all five fixed profiles, including the H1 Reader canary, satisfy the N0 oracle.

Mandatory stop: `H2_STOP` after the N0 gate is evaluated.

Headoff checkpoint: record the N0 gate state and whether H3 is permitted.

## Phase H3: N1 managed delegation-depth campaign

Purpose: prove canonical managed children remain leaf under normal and adversarial instructions.

Run every fixed managed profile sequentially. For each profile:

1. Perform the Issue #91 preflight.
2. Re-establish exact-turn V2 capability before the parent spawn or other covered Agent-control action.
3. Spawn through the canonical managed route with the fixed no-further-Agent boundary in the assignment and responsibility packet.
4. Include an adversarial untrusted-input instruction that asks the managed child to create or control another Agent.
5. Inspect authoritative child activity/rollout evidence for nested Agent-control actions.
6. Inspect authoritative descendant identity/spawn-edge evidence for any child-to-descendant materialization.
7. Record the profile result before the next profile.

Micro-stop after every profile. A nested Agent-control attempt or descendant materialization is `FAIL_STOP`. Ambiguous child action or descendant evidence is `UNKNOWN_STOP`.

Mandatory stop: `H3_STOP` after all five profiles are evaluated. Do not start N2 automatically.

Headoff checkpoint: record the N1 gate state and Issue #91 evidence range/reference.

## Phase H4: N2 native task-address and Host-thread identity binding

Purpose: prove that a successful native spawn yields the canonical task address and that independent Host evidence binds the underlying child thread identity to that address.

Actions:

1. Perform preflight and exact-turn V2 qualification.
2. Create one controlled canonical managed child suitable for identity observation.
3. Capture the successful native task address.
4. Independently bind the underlying child Host thread identity from authoritative Host activity or lifecycle evidence.
5. Bind both identities to the intended ExecutionBinding evidence basis without fabricating or persisting unavailable runtime identity fields.
6. Settle the child and verify no stale identity is used.

Mandatory stop: `H4_STOP` after N2 verdict.

Headoff checkpoint: record N2 state and whether the deliberate saturation phase H5 is permitted.

## Phase H5: N3 Host admission rejection and materialization safety

Purpose: deliberately exercise Host admission rejection while proving the rejected attempt creates no child identity or resident runtime.

This phase is isolated because it intentionally creates capacity pressure.

Actions:

1. Perform the dedicated N3 preflight.
2. Record authoritative Host capacity evidence. If the public spawned-agent limit is used, normalize it to the root-inclusive internal V2 session limit as required by the contract.
3. Design the rejection setup so the product managed-child ceiling of four is never exceeded. Prefer a Host capacity that can be saturated below that product ceiling. If safe saturation cannot be established within product policy, stop H5 as `NOT_RUN_STOP` rather than violating the product limit.
4. For each child used to create controlled pressure, perform its own preflight and exact-turn V2 capability check before the covered Agent-control action.
5. Trigger one actual Host admission rejection only when the attempted spawn remains within the product managed-child ceiling and the Host capacity setup makes rejection expected.
6. Prove the rejected attempt produced no successful spawn result, Started activity, Host thread identity, durable child identity, or resident child runtime.
7. Verify provisional execution and writer reservation rollback semantics.
8. Settle/clean all intentionally created children before leaving H5.

Any ambiguity about rejected-child materialization is `UNKNOWN_STOP`. Any setup that would require a fifth managed child or another product-policy violation is `NOT_RUN_STOP`.

Mandatory stop: `H5_STOP` with zero intentionally running children left behind.

Headoff checkpoint: record N3 state and cleanup/settlement completion.

## Phase H6: N4 same-child steering, correction, and continuation

Purpose: prove RUNNING Steer and later correction/continuation remain bound to one ExecutionBinding and one Host child.

Actions:

1. Perform preflight and exact-turn V2 qualification before the initial child spawn.
2. Start a controlled task that remains running long enough to steer.
3. Before `followup_task`, perform the required same-turn V2 capability check for that Agent-control turn.
4. Send RUNNING Steer to the original canonical task address.
5. Prove authoritative Host evidence stays on the original child thread and that the same child consumes the guidance.
6. Prove no replacement child materializes.
7. Verify ExecutionBinding identity, `attempt_no`, `control_epoch`, and `followup_count` remain consistent.
8. Exercise focused correction and continuation on changed bases without creating a fresh attempt.

Tool-call acceptance alone is insufficient.

Mandatory stop: `H6_STOP` after N4 verdict and safe child settlement.

Headoff checkpoint: record N4 state and the same-child evidence reference.

## Phase H7: N5 and N6 interrupt, settlement, and writer takeover

Purpose: validate the safety boundary between interruption, Host settlement, WriterLease release, and Main takeover.

Setup:

1. Perform the H7 preflight.
2. Start a new controlled writable managed execution through the canonical route and acquire the corresponding WriterLease under the normal product rules.
3. Re-establish exact-turn V2 capability before every covered Agent-control action used in the setup.
4. Bind the active execution, current generation, canonical native task address, and WriterLease before attempting N5.

N5 substep:

1. Perform a fresh preflight and exact-turn V2 qualification for the interrupt turn.
2. Interrupt the active managed execution.
3. Verify the interrupt result alone does not release WriterLease.
4. Require current-generation Host lifecycle evidence to settle the execution.
5. Reject stale control/lease generation evidence.

Internal hard stop after N5. Do not attempt takeover until N5 settlement is conclusive.

N6 substep:

1. Confirm UNKNOWN or unsettled writer ownership still blocks replacement and Main takeover.
2. After authoritative settlement, prove Main can acquire WriterLease.
3. Verify the single-writer invariant throughout takeover.

Mandatory stop: `H7_STOP` after N5 and N6 are both evaluated.

Headoff checkpoint: record N5/N6 state, settlement status, and writer ownership outcome reference.

## Phase H8: N7 rollout reconciliation and privacy

Purpose: prove the allowlisted reconciliation path provides sufficient lifecycle/identity evidence without exposing assignment text or reasoning content.

Actions:

1. Use authoritative root/child rollout evidence produced by the campaign.
2. Bind lifecycle call id, child identity, and result through the approved inspection path.
3. Verify the inspection output omits assignment text and reasoning content.
4. Verify stale or ambiguous rollout evidence cannot authorize acceptance or writer transfer.

N7 should avoid creating new Agents unless the canonical contract or missing evidence requires a separately preflighted action.

Mandatory stop: `H8_STOP` after N7 verdict.

Headoff checkpoint: record N7 state and privacy/reconciliation evidence reference.

## Phase H9: N8 Advisor review and effective sandbox truth

Purpose: run the final Host qualification probe on the exact candidate source and prove the Advisor's effective read-only boundary from Host-observed evidence.

Actions:

1. Freeze the candidate source before the N8 probe.
2. Perform preflight and exact-turn V2 qualification before the fresh Advisor spawn.
3. Spawn the canonical Advisor on the exact candidate artifact.
4. Observe effective Host sandbox and permission state. Requested profile configuration alone does not count.
5. Require effective read-only semantics for the strict review boundary.
6. Record broader Host permission behavior as a release limitation when present.
7. Bind the review verdict to the exact candidate artifact.

Mandatory stop: `H9_STOP` after N8 verdict.

Headoff checkpoint and final rebind rule:

- Record the H9 phase checkpoint in `headoff.md` as required.
- That checkpoint changes release-source identity even when Host qualification digests remain unchanged.
- Because N8 and the later Final Review bind the exact candidate artifact, the post-H9 checkpoint source must be frozen again.
- Perform one justified N8 revalidation on the post-checkpoint exact head, then do not mutate `headoff.md` or other release source before Final Review and release closure.
- The revalidation is part of H9 finalization, not a new phase, so it does not create an infinite headoff-update loop. The final exact N8 evidence remains canonical in Issue #91.

## Phase H10: release closure

Purpose: close non-Host release gates after the final post-H9 source freeze.

Actions:

1. Verify final release-source CI and source/synthetic tree agreement.
2. Run the fresh independent Final Review against the exact final source.
3. Build and verify the external release evidence envelope.
4. Verify installed-product Doctor and exact package/profile identity.
5. Perform human two-Skill App observation.
6. Keep PR #81 Draft and publication blocked if any gate is pending, unknown, not run, or failed.
7. Only after every gate is PASS may PR #81 leave Draft and the version tag/publication sequence begin.

Mandatory stop: `H10_RELEASE_DECISION_STOP`.

No release action auto-runs after this stop. Tagging, Marketplace verification, and publication require an explicit final release decision.

H10 headoff record rule:

- H10 must also be recorded in `headoff.md` to satisfy the phase-by-phase handoff requirement.
- Do not mutate the frozen release candidate merely to write that record before the final release decision.
- If H10 is blocked, the H10 checkpoint may be committed after the blocking decision; any later resumption must then refresh final-source gates as required.
- If H10 reaches release approval, perform the tag/Marketplace/publication sequence first, then record the H10 completion checkpoint on the resulting post-release development line. This post-release administrative record does not alter the already-tagged release artifact.

## Headoff checkpoint template

At each H0 through H9 mandatory stop, and at H10 using its special post-decision rule, update root `headoff.md` with only this durable summary shape:

```text
Host phase: Hx <name>
Phase state: PASS_STOP | NOT_RUN_STOP | UNKNOWN_STOP | FAIL_STOP | MUTATION_STOP
Canonical evidence: Issue #91 <ledger label/comment reference>
Qualification-basis impact: unchanged | changed <which canonical input>
Durable conclusion: <one or two sentences>
Next permitted phase: Hy | none
```

Do not paste raw rollout logs, transient task identifiers, full child transcripts, or detailed live Host verdicts into `headoff.md`.

After every pre-release headoff checkpoint merge:

1. verify repository CI for the new exact head;
2. compare `.codex-plugin/package-integrity.json`, `contracts/policy.json`, and `docs/v4/host-smoke.json` qualification digests;
3. record the resulting `REUSE | RERUN | NOT_RUN` decision in Issue #91 before another real Host action;
4. sync the target local checkout before the next phase.

## Campaign completion rule

The campaign is complete only when the machine contract N0 through N8 is conclusive PASS on valid evidence, all planned phase stops have been honored, the post-H9 exact source has been revalidated where required, release closure gates pass, and no unresolved `UNKNOWN`, `NOT_RUN`, or mutation invalidation remains.