# Architecture

subagents-dispatch V4.0.0 is a bounded orchestration layer over Codex Native Subagents. Codex remains the Agent runtime and the authoritative source for child materialization, lifecycle status, native control results, and actual Host capacity.

The user-facing Main session owns user intent, authorization, decomposition, routing, scheduling policy, WriterLease, artifact verification, WorkUnit acceptance, integration, and the final response. The normative machine-readable contract is `docs/v4/architecture.json`.

## Public surface

V4 exposes exactly two explicit Skills:

```text
Orchestrate
Doctor
```

`Orchestrate` owns plan-only routing, delegated execution, status, correction, continuation, interruption, cancellation, takeover, integration, and consequence-based independent review. `Doctor` diagnoses the installed Plugin package, managed profiles, Host capability surface, orchestration state, and legacy compatibility.

## Fixed profiles

| Profile | Model / effort | Ordinary authority | Semantic role |
| --- | --- | --- | --- |
| Reader | Luna Max | none | Work |
| Worker | Luna Max | bounded-source-write | Work |
| Investigator | Terra High | none | Work |
| Solver | Sol High | bounded-source-write | Work |
| Advisor | Sol High | none | Review |

Reasoning effort is fixed. Managed child profiles disable child multi-agent capability. Configured read-only remains least-privilege intent until the running Host proves effective sandbox enforcement.

## Current owners

Product contract ownership remains explicit:

```text
contracts/policy.json
-> fixed profiles, delegation and review policy

contracts/routing.md
-> delegation value and role selection

contracts/responsibility-packet.md
-> child responsibility serialization

contracts/team-plan.md
-> optional dependency and integration truth

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
-> user-facing factual execution summary

contracts/final-review.md
-> exact-candidate independent review
```

The complete runtime path map lives only at `docs/v4/architecture.json#runtime_owners`.

The runtime responsibilities are orchestration admission and user controls, bounded session state, path-safe atomic storage, WorkUnit dependency and acceptance truth, wakeup-driven scheduling, ExecutionBinding lifecycle, WriterLease ownership and settlement, managed responsibility projection, Host capability normalization, and optional bounded rollout evidence for recovery or release validation.

`docs/v4/host-smoke.json` owns the candidate-bound N0-N8 real Host release gate. Compatibility helpers remain separate from current V4 runtime ownership.

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

STEER targets a currently RUNNING child through the native followup primitive without changing lifecycle generation or consuming focused-correction budget.

INTERRUPT requests native interruption. The call result alone never releases WriterLease. Current-generation Host settlement is required before writer transfer or takeover.

`UNKNOWN` blocks replacement execution, conflicting writer ownership, and final acceptance until reconciled.

## Host observations

Host observations are reconciled against a current observation basis:

```text
execution_id
control_epoch
lease_epoch when applicable
```

Stale-generation observations are discarded. Delayed evidence from an older epoch cannot reactivate or settle the current generation.

`list_agents` supports Status, recovery, takeover settlement, and ambiguity reconciliation. The allowlisted rollout inspector remains optional and is used only when exact raw collaboration evidence is required for recovery or release validation.

## Scheduling

Scheduling is wakeup-driven and enforces product policy:

```text
initial managed children <= 2
ordinary managed children <= 3
result backlog >= 2 stops fresh fanout growth
one canonical managed writer
UNKNOWN counts as blocking occupancy
```

Known Host capacity may reduce an advisory launch ceiling. Unknown Host capacity does not block a bounded spawn attempt. Codex Host owns actual capacity and may reject the call.

A writable Worker or Solver is admitted only when no other managed child is active in the canonical checkout. Read-oriented managed children may run together when independent. Final Review waits for the writer to settle. These phase rules reduce checkout interference and do not claim OS containment.

## WriterLease

V4 keeps one canonical managed writer. WriterLease is project scheduling ownership, not a filesystem or OS lock.

A writable activation acquires or retains the lease before Host activation. A writer in RUNNING, REVOKING, or UNKNOWN remains blocking. INTERRUPT return alone cannot release it. Release or transfer requires current-generation Host lifecycle settlement evidence.

## Child coordination

Main is the sole managed coordinator. Managed child profiles disable native multi-agent capability and receive behavioral instructions not to create further subagents. Peer messages have no authority semantics and are outside the managed coordination contract.

If a future Host exposes managed child collaboration despite the verified profile configuration, the Host/build fails release readiness until adapted and re-tested.

## Final Review

After Main establishes Candidate Ready, `contracts/final-review.md` decides whether consequence-based triggers require a fresh Advisor review of the exact candidate.

Git-backed deliverables use `scripts/review-artifact.py`; non-Git deliverables use deterministic SHA-256 serialization. Any material candidate mutation invalidates the previous verdict.

## Compatibility

V3.x live state remains legacy evidence and is never silently rewritten into V4 state. Unresolved legacy ownership, active execution, pending takeover, corrupt state, or uncertain writer ownership fails closed. Explicit stale cleanup understands only the minimum legacy schema needed to prove a terminal V3 capsule safe to remove.

Older pre-release V4 state from incompatible schemas requires explicit cleanup and restart. The ordinary V4 state remains bounded, temporary, session-scoped, and outside the project working tree. It stores coordination metadata, not raw prompts, child transcripts, reasoning traces, source copies, or arbitrary Host output.

## Release verification

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

Repository CI supports delivery by catching regressions. It does not define product value and cannot substitute for real Host behavior, installed-product checks, or Main acceptance semantics.

## V4.0.0 exclusions

The release excludes dynamic effort routing, nested managed delegation, autonomous peer authority transfer, daemon scheduling, persistent orchestration databases, automatic worktree management, and parallel isolated managed writers.
