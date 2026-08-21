# RC5 Native Core Architecture Decision

Status: IMPLEMENTATION CANDIDATE, NOT FROZEN

This decision supersedes the earlier RC5 Hookless Core freeze and its proposed `OperationIntent` / `OperationReceipt` replacement control plane.

## Decision

V4 RC5 removes Plugin Hook interception and Hook-shaped lifecycle authorization from the production correctness path.

```text
Main
  -> decides responsibility and routing
  -> allocates ExecutionBinding
  -> reserves WriterLease before writable activation
  -> invokes Codex Native Subagents directly
  -> reconciles Host lifecycle truth
  -> verifies the actual artifact
  -> alone accepts or rejects work
```

The implementation must not recreate Hook acknowledgement through another persisted request/receipt protocol.

Removed core concepts:

- `hooks/hooks.json`;
- `PreToolUse`, `PostToolUse`, `SubagentStop` interception;
- `orchestration_guard.py` and Hook compatibility guards;
- `PendingControl`;
- project authority derived from Host `tool_use_id`;
- Hook capacity tokens and their invalidation protocol;
- Guard coverage proofs;
- `OperationIntent` and `OperationReceipt`;
- persisted `PhaseContext` / `WorkspaceBaseline` machinery whose only purpose is to replace Hook control flow.

## Evidence baseline

The RC5 feasibility campaign on Codex Desktop runtime `0.148.0-alpha.15`, Desktop build `26.814.41407 (6720)`, macOS `27.0 (26A5416b)`, arm64 established:

- managed Reader role routing: PASS;
- configured model and reasoning effort observation: PASS;
- `fork_turns = none`: PASS;
- managed Reader collaboration surface absent: PASS;
- managed Reader child collaboration calls absent: PASS;
- configured read-only sandbox enforcement: FAIL on the tested MultiAgentV2 path because the child observed `danger-full-access`;
- explicit Host capacity rejection before child materialization in the tested capacity path: PASS;
- exact root collaboration rollout binding and privacy-safe inspection: PASS.

These facts support Native Core orchestration. They do not establish hostile-code containment.

## Trust boundary

### Main is the trusted coordinator

Main is already the actor that decides delegation, interprets native tool results, verifies artifacts, and accepts work. RC5 does not pretend that Python receives an automatic typed Host callback after Hooks are removed.

Normal lifecycle flow is Main-driven:

1. Main captures the current `observation_basis` when needed.
2. Main invokes the native collaboration tool.
3. Main passes the observed native lifecycle result into the deterministic state helper.
4. The helper rejects stale generation data.
5. Ambiguous cases use fresh `list_agents` observation and, where exact raw evidence is required, the allowlisted rollout inspector.

The rollout inspector remains a recovery and release-attestation tool. It does not become a mandatory per-call receipt subsystem.

### Host-owned truth

Codex Native Subagents own the observable facts of native acceptance/rejection, child materialization, child identity, and current native lifecycle status.

Project state may cache reconciled Host observations. Project code must not create a competing synthetic lifecycle authority.

### Main-owned project truth

Main owns:

- user intent;
- WorkUnit responsibility and acceptance;
- optional TeamPlan when a real multi-responsibility dependency graph is useful;
- ExecutionBinding allocation and bounded fresh-attempt accounting;
- mutation authority and declared write scope;
- WriterLease project ownership;
- artifact verification and final acceptance.

A child result is candidate evidence. It cannot accept a WorkUnit, broaden authority, transfer WriterLease, or prove its own Host route.

## Persistent runtime state

RC5 keeps only primitives with independent product value:

- WorkUnit;
- optional TeamPlan revision;
- ExecutionBinding;
- `control_epoch` as the generation counter for same-child activation and stale-observation rejection;
- WriterLease;
- bounded accounting references for accepted results or recovery-relevant Host observations.

`PendingControl` is removed.

No replacement persisted request/receipt state machine may be added unless a later demonstrated failure cannot be represented safely by `ExecutionBinding + control_epoch + WriterLease + Host reconciliation`.

## Native lifecycle rules

### Fresh spawn

1. Validate responsibility, profile, attempt budget, authority, and writer admission.
2. Allocate `ExecutionBinding` as `SPAWN_PENDING`.
3. Reserve WriterLease before a writable native activation.
4. Invoke native `spawn_agent`.
5. Recognized success binds the materialized child and reconciles lifecycle state.
6. A recognized pre-materialization rejection may roll back the provisional ExecutionBinding and a merely reserved WriterLease only when reconciliation establishes that no child materialized.
7. Any ambiguous result becomes `UNKNOWN`.

A safe pre-materialization rollback does not consume a fresh attempt. A writable ambiguous spawn keeps WriterLease blocking.

### Same-child followup and continue

A focused followup or continuation:

- reuses the same ExecutionBinding;
- increments `control_epoch` before the new activation is current;
- keeps the existing focused-followup budget;
- reserves or retains WriterLease for writable execution;
- reconciles native Host state after the call.

Earlier-generation observations are stale and cannot settle the current activation.

### Interrupt and takeover

For a writable execution:

1. WriterLease enters `REVOKING` before native interrupt.
2. An interrupt call result alone does not release write ownership.
3. Main reconciles current native lifecycle state.
4. WriterLease remains blocking while lifecycle is active or `UNKNOWN`.
5. Transfer to Main or another writer is allowed only after current-generation evidence proves settlement.

### UNKNOWN

`UNKNOWN` fails closed:

- no replacement execution;
- no WriterLease transfer;
- no final acceptance;
- no claim that a child did or did not materialize;
- reconciliation is required before conflicting progress.

## Simple phase isolation

The tested Host did not enforce the requested read-only sandbox for the managed Reader. RC5 therefore keeps one simple canonical-checkout scheduling rule without introducing persisted phase state.

- Reader, Investigator, and Advisor may run concurrently with one another when otherwise independent.
- A writable Worker or Solver starts only after every managed read-oriented child has settled.
- While WriterLease is blocking, no other managed child starts in the canonical checkout.
- Final Review starts only after the writer has settled.
- `UNKNOWN` counts as active/blocking for these admission rules.

This rule reduces accidental checkout interference. It does not create OS containment and does not prove that a same-user process cannot write.

Main may perform read-only inspection while WriterLease is blocking. Main must not perform conflicting writes until the prior managed writer is settled or ownership has safely transferred.

## Host observation

`list_agents` remains useful for Status, recovery, takeover settlement, and ambiguity reconciliation.

RC5 does not persist a PreToolUse preparation record merely to authorize a later PostToolUse result. Main captures the current project observation basis before reconciliation-sensitive observation. Returned data is accepted only while that basis remains current.

Exact raw rollout inspection remains available for ambiguous recovery and release verification.

## Capacity policy

The scheduler enforces product policy and lets the Host own actual native capacity.

Keep:

- initial and normal product fanout ceilings;
- acceptance backpressure;
- dependency readiness;
- fresh-attempt budget;
- phase isolation;
- WriterLease exclusion;
- `UNKNOWN` as blocking occupancy.

Remove:

- mandatory Host occupancy observation before every spawn;
- one-shot capacity tokens;
- capacity-token invalidation after every lifecycle mutation;
- Hook-derived resident/reclaim authorization.

Known Host capacity may be used as an advisory ceiling. Unknown capacity permits a bounded native spawn attempt. The Host may reject it.

A capacity rejection counts as pre-materialization only for a recognized path whose reconciliation establishes no child identity, activity, path, listing, or rollout evidence. Other errors remain ambiguous.

## Managed child capability containment

Managed child profiles keep child collaboration disabled:

```toml
[agents]
enabled = false

[features]
multi_agent_v2 = false
```

This is a release-tested Host capability boundary for the exact candidate. Unexpected child collaboration capability is a release failure.

Reader, Investigator, and Advisor keep project mutation authority `none`. Worker and Solver may receive bounded write authority from Main.

The tested Host does not prove that read-role processes are technically unable to write when the parent has broader filesystem permissions. RC5 does not claim that role configuration supplies an OS sandbox.

## WriterLease

WriterLease remains in this refactor because single managed writer ownership and fail-closed takeover have independent value.

This migration removes Hook and PendingControl coupling from WriterLease settlement. It does not redesign the entire lease state machine at the same time. A later simplification may reduce WriterLease state only after takeover, interrupt, crash-recovery, and `UNKNOWN` behavior are re-proven.

## Upgrade boundary

The public `main` branch is V3.x while this V4 work is pre-release. RC5 therefore has no deployed V4 `PendingControl` capsule compatibility promise.

Development and release-candidate validation must use fresh V4 state after the state-schema cutover. Native Core must not silently reinterpret an old experimental V4 capsule containing unresolved Hook controls. Such state is treated as incompatible development state and requires explicit cleanup/restart during the pre-release campaign.

The existing V3.x installation/profile migration boundary remains a separate release concern and must continue to pass its tests.

## Verification boundary

Host lifecycle completion proves settlement only. It does not prove task correctness.

Main accepts work only after inspecting the actual candidate and running relevant checks. Read-role evidence and writer-reported changed files remain claims until Main verifies them.

## Release claims

After release-candidate verification RC5 may claim:

- fixed managed role/model/effort routing;
- fresh-context spawn with `fork_turns = none`;
- managed child collaboration disabled on the tested Host/build;
- bounded project fanout and fresh-attempt policy;
- simple canonical-checkout phase isolation;
- Main-owned acceptance;
- one managed project writer;
- fail-closed `UNKNOWN` handling;
- native Host lifecycle reconciliation.

RC5 must not claim:

- Hook interception protects lifecycle calls;
- arbitrary native calls are technically impossible outside Main policy;
- configured `sandbox_mode = read-only` proves Host-enforced read-only;
- WriterLease means only one same-user OS process can physically write;
- repository verification is a hostile-code containment boundary.

## Migration order

1. establish and adversarially review this architecture decision;
2. expose direct Main-driven Host reconciliation without Hook pairing;
3. switch lifecycle and WriterLease settlement away from PendingControl and Guard acknowledgement;
4. simplify scheduler and Host capability checks by removing Hook/capacity-token requirements and enforcing simple phase isolation;
5. remove PendingControl from V4 state and delete dead Hook/control runtime;
6. remove Hook-specific Doctor, CI, package-integrity, release, and installation contracts;
7. update public documentation, remove dead compatibility surface, and run the complete verification campaign.

Temporary dual paths are permitted only inside the migration step that still needs them. After production callers use Native Core, dead control paths are deleted.

## Freeze rule

This decision is not frozen merely because implementation has begun.

RC5 freezes only after:

- deterministic lifecycle, recovery, writer, scheduler, state, Doctor, packaging, and public-surface tests pass;
- the complete behavior diff against RC4 is reviewed;
- the Native Core Host campaign passes on the release candidate;
- an independent final review finds no unresolved P0 or P1 issue;
- repository search finds no production correctness dependency on Hook or PendingControl semantics.

Restoring Hook to the correctness path, allowing WriterLease transfer on `UNKNOWN`, allowing child-to-child collaboration, or replacing Host lifecycle truth with a project-owned synthetic lifecycle protocol requires a new explicit architecture decision.
