# Architecture

subagents-dispatch V4.0.0 is a bounded orchestration layer over Codex Native Subagents. Codex remains the Agent runtime and the authoritative source for native child materialization, collaboration-call acceptance or rejection, lifecycle status, and actual Host capacity behavior.

The user-facing Main session owns user intent, authorization, decomposition, routing, scheduling policy, WriterLease, artifact verification, WorkUnit acceptance, and the final response.

The normative V4 candidate architecture is `docs/v4/architecture.json`. `docs/rc5-hookless-core-design.md` records the active Native Core decision and its implementation constraints. RC5 is not frozen until implementation and release verification complete.

## Public surface

V4 exposes two explicit Skills:

```text
Orchestrate
Doctor
```

`Orchestrate` owns plan-only routing, delegated execution, status, correction, continuation, interruption, cancellation, takeover, integration, and consequence-based independent review. `Doctor` diagnoses the installed Plugin package, managed profiles, Host capability surface, orchestration state, and legacy compatibility.

## Semantic and capability model

The semantic model stays small:

```text
main session
Work
Review
```

Managed profiles remain fixed:

| Profile | Model / effort | Ordinary authority | Semantic role |
| --- | --- | --- | --- |
| Reader | Luna Max | none | Work |
| Worker | Luna Max | bounded-source-write | Work |
| Investigator | Terra High | none | Work |
| Solver | Sol High | bounded-source-write | Work |
| Advisor | Sol High | none | Review |

V4 does not change reasoning effort dynamically. Managed child profiles disable child multi-agent capability. A release Host that unexpectedly exposes child collaboration capability fails the managed profile contract.

Configured read-only sandbox remains least-privilege intent. RC5 does not claim Host-enforced read-only unless the running Host proves it.

## Active contract owners

```text
contracts/policy.json
-> fixed profile identities, delegation invariants, review triggers

contracts/routing.md
-> delegation value, capability selection, responsibility semantics

contracts/responsibility-packet.md
-> serialized responsibility record

contracts/team-plan.md
-> optional multi-responsibility dependency and integration truth

contracts/guardrails.md
-> authority, depth, mutation, writer, consent and external-action boundaries

contracts/handoff.md
-> optional Main-accepted evidence bridge

contracts/evidence-artifact.md
-> inspectable evidence provenance

contracts/interaction.md
-> user-visible Orchestrate controls

contracts/recovery.md
-> WorkUnit / ExecutionBinding recovery behavior

contracts/receipt.md
-> user-facing factual execution summary only; no lifecycle ledger authority

contracts/final-review.md
-> exact-candidate independent review
```

Historical RC designs and Hook-era contracts do not override the active Native Core decision. Plugin Hooks are not a correctness authority in Native Core.

## Runtime owners

```text
docs/v4/architecture.json
-> candidate V4 product and safety invariants

scripts/orchestrate_v4.py
-> admission, routing and user control facade

scripts/dispatch_state_v4.py
-> bounded session-scoped V4 state and Host lifecycle reconciliation

scripts/state_storage.py
-> schema-neutral thread identity, path safety, locking and atomic persistence

scripts/legacy_state_cleanup.py
-> explicit cleanup compatibility for stale terminal V3 capsules only

scripts/work_graph_v4.py
-> WorkUnit truth, dependency and acceptance transitions

scripts/scheduler_v4.py
-> wakeup-driven product admission, fanout and backpressure

scripts/execution_lifecycle_v4.py
-> ExecutionBinding allocation, same-child lifecycle operations, and direct Host observation facade

scripts/writer_lease_v4.py
-> canonical WriterLease ownership and settlement

scripts/managed_execution_v4.py
-> responsibility projection and managed spawn payload

scripts/host_capabilities.py
-> native Host capability normalization

scripts/inspect-collaboration-runtime.py
-> optional allowlisted rollout evidence for recovery and release attestation
```

The retired V3 orchestration state engine, separate Team Ledger, Plugin Hook interception, PendingControl, Hook-specific tool-name normalization, Hook capacity tokens, Guard coverage proof, and replacement request/receipt ledgers are outside the Native Core correctness path.

## Single responsibility and coordinated work

Zero delegated responsibilities create no orchestration state.

One independent delegated responsibility may use one WorkUnit with `team_plan_revision = null`. Multiple unresolved responsibilities use TeamPlan only when dependency or integration order matters.

WorkUnit records stable responsibility and acceptance truth. ExecutionBinding records one concrete native Agent attempt and route. One unchanged WorkUnit may use at most two fresh Agent attempts. One focused same-child FOLLOWUP remains inside an ExecutionBinding and has a bounded correction budget. CONTINUE resumes the same interrupted ExecutionBinding without consuming fresh-attempt or correction budget.

Host `COMPLETED` produces candidate work and maps to `WorkUnit.RESULT_READY`. Main verifies the actual artifact and explicitly accepts the WorkUnit. Dependencies unlock only from `ACCEPTED`.

## Native lifecycle

Fresh spawn follows this order:

```text
validate responsibility / route / budget / authority
allocate ExecutionBinding as SPAWN_PENDING
reserve WriterLease if writable
invoke native spawn_agent
reconcile Host result
```

Recognized success binds observed child identity and lifecycle. A recognized pre-materialization rejection may roll back provisional activation only when evidence establishes that no child materialized. Ambiguous materialization becomes `UNKNOWN`. Writable ambiguity keeps WriterLease blocking.

FOLLOWUP and CONTINUE reuse the same ExecutionBinding and advance `control_epoch` before a later Host generation may become current. Writable reactivation reserves or retains WriterLease first.

INTERRUPT requests native interruption. The call result alone never releases WriterLease. Current-generation Host settlement is required before writer transfer or takeover.

`UNKNOWN` blocks replacement execution, conflicting writer ownership, and final acceptance until reconciled.

## Host observations

Host observations are reconciled against a current observation basis:

```text
execution_id
control_epoch
lease_epoch when applicable
```

The basis does not require a persisted PreToolUse record. Stale-generation observations are discarded. Delayed evidence from an older epoch cannot reactivate or settle the current generation.

`list_agents` supports Status, recovery, takeover settlement, and ambiguity reconciliation. The allowlisted rollout inspector remains optional and is used when exact raw collaboration evidence is required. It is not a mandatory per-call receipt subsystem.

## Scheduling

Scheduling is wakeup-driven and enforces product policy:

```text
initial managed children <= 2
ordinary managed children <= 3
result backlog >= 2 stops fresh fanout growth
one canonical managed writer
UNKNOWN counts as blocking occupancy
```

Known Host capacity may reduce an advisory launch ceiling. Unknown Host capacity does not require an occupancy token before a bounded spawn attempt. Codex Host owns actual capacity and may reject the call.

A writable Worker or Solver is admitted only when no other managed child is active in the canonical checkout. Read-oriented managed children may run together when independent. Final Review waits for the writer to settle. These phase rules reduce checkout interference and do not claim OS containment.

## WriterLease

V4 keeps one canonical managed writer. WriterLease is project scheduling ownership, not a filesystem or OS lock.

A writable activation acquires or retains the lease before Host activation. A writer in RUNNING, REVOKING, or UNKNOWN remains blocking. INTERRUPT return alone cannot release it. Release or transfer requires current-generation Host lifecycle settlement evidence.

WriterLease settlement does not depend on PendingControl acknowledgement or Guard coverage proof.

WriterLease schema simplification is deferred until native interrupt, takeover, UNKNOWN, and crash-recovery behavior are verified after Hook removal.

## Child coordination

Main is the sole managed coordinator. Managed child profiles disable native multi-agent capability and receive behavioral instructions not to create further subagents. Peer messages have no authority semantics and are not part of the correctness path.

If a future Host exposes managed child collaboration despite the verified profile configuration, the Host/build fails release readiness until adapted and re-tested.

## Final Review

After Main establishes Candidate Ready, `contracts/final-review.md` decides whether consequence-based triggers require a fresh Advisor review of the exact candidate.

Git-backed deliverables use `scripts/review-artifact.py`; non-Git deliverables use deterministic SHA-256 serialization. Any material candidate mutation invalidates the previous verdict.

## Migration

V3.x live state remains legacy evidence and is never silently rewritten into V4 state. Unresolved legacy ownership, active execution, pending takeover, corrupt state, or uncertain writer ownership fails closed. Explicit stale cleanup understands only the minimum legacy schema needed to prove a terminal V3 capsule safe to remove.

RC5 Native Core is pre-release and carries no compatibility promise for experimental V4 state containing PendingControl. Development and release validation use fresh Native Core state after schema cutover.

The ordinary V4 state remains bounded, temporary, session-scoped, and outside the project working tree. It stores coordination metadata, not raw prompts, child transcripts, reasoning traces, source copies, or arbitrary Host output.

## Release verification

RC5 freezes after deterministic verification, behavior comparison, Host verification, and adversarial review.

The Native Core Host campaign is:

```text
N0 exact role / model / effort / fork_turns
N1 managed child collaboration capability absent
N2 fresh spawn success and identity binding
N3 explicit capacity rejection with no materialization
N4 same-child followup and continue
N5 interrupt and settlement observation
N6 writer takeover blocked until settlement
N7 rollout reconciliation and privacy allowlist
N8 final Advisor review and truthful sandbox reporting
```

A repository search must find no active production correctness dependency on Plugin Hook, PendingControl, the retired V3 orchestration state engine, a separate Team Ledger, or a replacement persisted request/receipt control plane before freeze.

## V4.0.0 exclusions

The release excludes dynamic effort routing, nested managed delegation, autonomous peer authority transfer, daemon scheduling, persistent orchestration databases, automatic worktree management, parallel isolated managed writers, Plugin Hook lifecycle authority, PendingControl, the retired V3 orchestration engine, separate Team Ledger state, and replacement operation-receipt ledgers.
