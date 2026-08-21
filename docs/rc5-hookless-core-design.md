# RC5 Native Core Architecture Decision

Status: IMPLEMENTATION CANDIDATE, NOT FROZEN

This decision supersedes the earlier RC5 Hookless Core freeze that proposed `OperationIntent` and `OperationReceipt` as a replacement control plane.

## Decision

V4 RC5 removes Plugin Hook interception and the Hook-shaped control protocol from the production correctness path.

The runtime core is:

```text
Main
  -> decomposes work when useful
  -> owns WorkUnit / TeamPlan decisions
  -> allocates an ExecutionBinding
  -> reserves WriterLease before writable activation
  -> invokes Codex Native Subagents directly
  -> reconciles Host lifecycle truth
  -> verifies the resulting artifact
  -> alone accepts or rejects work
```

The implementation must not introduce a second lifecycle authorization protocol to replace Hooks.

The following are not RC5 core primitives:

- `hooks/hooks.json`;
- `PreToolUse`, `PostToolUse`, or `SubagentStop` interception;
- `orchestration_guard.py` or Hook compatibility guards;
- `PendingControl`;
- Host `tool_use_id` as project authority;
- Hook capacity observation tokens;
- Guard coverage proofs;
- `OperationIntent`;
- `OperationReceipt`;
- a new persisted phase/receipt protocol whose purpose is to recreate Hook acknowledgement semantics.

## Evidence baseline

The feasibility campaign on Codex Desktop runtime `0.148.0-alpha.15`, Desktop build `26.814.41407 (6720)`, macOS `27.0 (26A5416b)`, arm64 established:

- managed Reader role routing: PASS;
- configured model and reasoning effort observation: PASS;
- `fork_turns = none`: PASS;
- managed Reader collaboration surface absent: PASS;
- managed Reader child collaboration calls absent: PASS;
- configured read-only sandbox enforcement: FAIL on the tested MultiAgentV2 path because the child observed `danger-full-access`;
- explicit Host capacity rejection before child materialization in the tested capacity path: PASS;
- exact root collaboration rollout binding and privacy-safe inspection: PASS.

These facts justify removing Hook correctness dependencies. They do not justify claiming hostile-code containment.

## Authority model

### Host-owned lifecycle truth

Codex Native Subagents own the observable facts of whether a native collaboration request is accepted or rejected, whether a child materializes, child identity, and current native lifecycle status.

Project code may cache or reconcile these facts. It must not replace them with a competing lifecycle authority.

### Main-owned orchestration truth

Main owns:

- user intent and decomposition;
- WorkUnit responsibility and acceptance;
- TeamPlan only when a real multi-responsibility dependency graph is useful;
- ExecutionBinding allocation and bounded fresh-attempt accounting;
- mutation authority and declared write scope;
- WriterLease scheduling ownership;
- final verification and acceptance.

A child result is candidate evidence. It cannot accept a WorkUnit, broaden its mutation authority, transfer WriterLease, or prove its own Host route.

## Minimal persistent runtime state

RC5 keeps the existing primitives that still carry independent product value:

- WorkUnit;
- optional TeamPlan revision;
- ExecutionBinding;
- `control_epoch` as the generation counter for same-child reactivation and stale-observation rejection;
- WriterLease for one managed writer in the canonical checkout;
- bounded accounting references that record accepted project results or Host observations where recovery needs them.

`PendingControl` is removed.

No new persisted request/receipt state machine may be added unless a later failure case demonstrates that `ExecutionBinding + control_epoch + WriterLease + Host reconciliation` cannot represent the required safety property.

## Native lifecycle rules

### Fresh spawn

1. Main validates responsibility, profile, attempt budget, authority, and writer availability.
2. Main allocates an `ExecutionBinding` in `SPAWN_PENDING`.
3. A writable execution reserves WriterLease before the native Host mutation.
4. Main invokes native `spawn_agent`.
5. Recognized success binds the materialized child and reconciles lifecycle state.
6. An explicit recognized pre-materialization rejection may remove the provisional activation and release a merely reserved writer only when evidence establishes that no child materialized.
7. Any ambiguous outcome becomes `UNKNOWN`.

An ambiguous writable spawn keeps WriterLease blocking until reconciliation proves the prior writer did not materialize or has settled.

### Same-child followup and continue

A focused followup or continuation:

- reuses the same ExecutionBinding;
- increments `control_epoch` before the new Host activation is considered current;
- keeps the existing focused-followup budget;
- reserves or retains WriterLease for writable execution;
- reconciles native Host state after the call.

Stale observations from an earlier `control_epoch` are ignored.

### Interrupt and takeover

For a writable execution:

1. WriterLease enters `REVOKING` before Main requests native interrupt.
2. The interrupt call result alone does not release write ownership.
3. Main observes or reconciles Host lifecycle state.
4. WriterLease remains blocking while lifecycle is active or `UNKNOWN`.
5. Transfer or Main takeover is allowed only after current-generation evidence proves the prior managed writer settled.

### UNKNOWN

`UNKNOWN` is fail closed:

- no replacement execution;
- no WriterLease transfer;
- no final acceptance;
- no claim that the child did or did not materialize;
- reconciliation is required before progress that would conflict with the unresolved responsibility.

## Host observation

`list_agents` remains useful for Status, recovery, takeover settlement, and ambiguity reconciliation.

RC5 does not persist a PreToolUse preparation record merely to authorize a later PostToolUse result.

Before a Host observation, Main captures the current project observation basis for each relevant ExecutionBinding. The basis includes the execution identity and current generation information already used by state reconciliation. The returned native observation is accepted only if that basis is still current. A stale basis is discarded.

The allowlisted collaboration rollout inspector remains a recovery and release-attestation tool. It does not become a per-call mandatory receipt subsystem.

## Capacity policy

The scheduler enforces product policy, not a mirrored Host occupancy protocol.

Keep:

- bounded initial and normal fanout;
- acceptance backpressure;
- dependency readiness;
- fresh-attempt budget;
- WriterLease exclusion;
- `UNKNOWN` as blocking occupancy.

Remove:

- mandatory fresh Host-capacity observation before every spawn;
- one-shot capacity tokens;
- capacity-token invalidation after every lifecycle mutation;
- Hook-derived resident/reclaim authorization.

Known Host capacity may be used as an advisory ceiling. If capacity is unknown, RC5 may make a bounded native spawn attempt. The Host remains authoritative and may reject it.

An explicit capacity rejection is treated as pre-materialization only for a recognized path whose reconciliation establishes no child identity, activity, path, listing, or rollout materialization. Other errors remain ambiguous.

## Managed child capability containment

Managed child profiles keep child collaboration disabled:

```toml
[agents]
enabled = false

[features]
multi_agent_v2 = false
```

This is a release-tested Host capability boundary for the exact candidate. If a future Host exposes child collaboration despite the managed profile, the candidate fails its capability gate.

Reader, Investigator, and Advisor retain project mutation authority `none`. Worker and Solver may receive bounded write authority from Main.

The tested Host does not prove that a read-role process is technically unable to write when the parent runs with broader filesystem permissions. RC5 therefore does not claim OS containment from role configuration.

## Canonical writer invariant

This refactor retains WriterLease because single-writer ownership and fail-closed takeover remain independent product requirements.

This refactor does not redesign WriterLease solely for code-count reduction. After Hook removal is stable, WriterLease may be evaluated separately for simplification if the same takeover and ambiguity properties can be demonstrated with less state.

## Verification boundary

Main accepts work only after verifying the actual candidate artifact and relevant checks.

Host lifecycle completion is necessary evidence for settlement. It is not proof that the work is correct.

Read-role and review-role claims remain untrusted until Main verifies the cited evidence. Writer-reported changed files remain claims until inspected.

## Release claims

RC5 may claim, after release-candidate verification:

- fixed managed role/model/effort routing;
- fresh-context managed spawn with `fork_turns = none`;
- managed child collaboration disabled on the tested Host/build;
- bounded project fanout and fresh-attempt policy;
- Main-owned acceptance;
- one managed project writer in the canonical checkout;
- fail-closed `UNKNOWN` handling;
- native Host lifecycle reconciliation.

RC5 must not claim:

- Hook interception protects lifecycle calls;
- arbitrary native calls are technically impossible outside Main policy;
- configured `sandbox_mode = read-only` proves Host-enforced read-only;
- one managed WriterLease means only one same-user OS process can physically write;
- repository verification is a hostile-code containment boundary.

## Migration order

The production refactor is executed in reviewable stages:

1. establish this architecture decision and adversarially review it;
2. add direct native Host observation/reconciliation without Hook pairing;
3. switch lifecycle and WriterLease settlement away from PendingControl and Guard acknowledgement;
4. simplify scheduler and Host capability checks by removing Hook/capacity-token requirements;
5. remove PendingControl from the V4 state schema and delete dead Hook/control runtime;
6. remove Hook-specific Doctor, CI, package-integrity, release, and installation contracts;
7. update public documentation, remove dead compatibility surface, and run the full verification campaign.

Temporary dual paths are allowed only during the migration commit in which the production caller still requires them. Once the native path is active, the old path is deleted rather than retained as dormant compatibility code.

## Freeze rule

This document is not frozen merely because implementation has begun.

RC5 may freeze only after:

- deterministic lifecycle, recovery, writer, scheduler, state, Doctor, packaging, and public-surface tests pass;
- the complete diff against the RC4 behavior contract has been reviewed;
- the Native Core Host campaign passes on the release candidate;
- an independent final review finds no unresolved P0 or P1 issue;
- repository search shows no production correctness dependency on Hook or PendingControl semantics.

Restoring Hook to the correctness path, allowing WriterLease transfer on `UNKNOWN`, allowing child-to-child collaboration, or replacing Host lifecycle truth with a project-owned synthetic lifecycle protocol requires a new explicit architecture decision.
