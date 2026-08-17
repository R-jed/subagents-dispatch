# Architecture

subagents-dispatch V4.0.0 is a bounded orchestration layer over Codex Native Subagents. Codex remains the Agent runtime. The project does not add a daemon, event bus, persistent scheduler database, private Agent runtime, automatic worktree manager, or nested managed delegation.

The user-facing Main session owns user intent, authorization, decomposition, integration, WorkUnit acceptance, lifecycle control decisions, and the final response. Native Host observations own Agent lifecycle truth.

The normative V4 architecture freeze is `docs/v4/architecture.json`. This document is the human-readable owner map for that active design.

## Public surface

V4 exposes exactly two explicit Skills:

```text
Orchestrate
Doctor
```

`Orchestrate` internalizes plan-only, execution, status, correction, continuation, interruption, cancellation, takeover, integration, and review. `Doctor` diagnoses package integrity, fixed profiles, V4 state, legacy state, Host capabilities, lifecycle Hook evidence, and release readiness.

The retired V3 public orchestration Skills remain historical compatibility material only. They are not V4 public entrypoints.

## Semantic and capability model

The semantic model is deliberately small:

```text
Main
Work
Review
```

Physical Agent profiles remain separate capability and authority boundaries:

| Profile | Model / effort | Ordinary authority | Semantic role |
| --- | --- | --- | --- |
| Reader | Luna Max | none | Work |
| Worker | Luna Max | bounded-source-write | Work |
| Investigator | Terra High | none | Work |
| Solver | Sol High | bounded-source-write | Work |
| Advisor | Sol High | none | Review |

V4.0.0 never changes reasoning effort dynamically. Routing chooses among these fixed profiles. Reader and Worker remain separate physical profiles because mutation authority is a real boundary even when both use Luna Max.

## Runtime owners

```text
docs/v4/architecture.json
-> frozen V4 product and safety invariants

scripts/orchestrate_v4.py
-> Orchestrate admission, plan-only, routing and control facade

scripts/dispatch_state_v4.py
-> bounded thread-scoped state v4, validation and Host reconciliation

scripts/work_graph_v4.py
-> WorkUnit graph and acceptance-gated dependency truth

scripts/scheduler_v4.py
-> wakeup-driven ready-frontier scheduling, critical path, fanout and backpressure

scripts/dispatch_control_v4.py
-> PendingControl authorization, PreToolUse consumption and PostToolUse acknowledgement

scripts/execution_lifecycle_v4.py
-> ExecutionBinding allocation and same-child lifecycle operations

scripts/writer_lease_v4.py
-> canonical WriterLease ownership and settlement

scripts/host_capabilities.py
-> normalized Host capability evidence

scripts/orchestration_guard.py
-> staged V4 PreToolUse, PostToolUse and SubagentStop Guard

docs/v4/host-smoke.json
-> real Host release gate
```

`contracts/policy.json` remains the machine-readable owner for the five fixed profile identities and efforts. `contracts/final-review.md` remains the exact-candidate independent review contract. Other root `contracts/` documents are hardened V3.x compatibility/reference owners and must not override the V4 runtime freeze or the two-Skill product surface.

## WorkUnit and ExecutionBinding

A WorkUnit records responsibility and acceptance truth. An ExecutionBinding records one concrete Agent attempt and route. This separation lets a stable responsibility survive retry, reroute, same-child correction, interruption, or Main takeover without making profile identity part of responsibility identity.

Host `COMPLETED` means only that an execution produced a candidate result. It maps to `WorkUnit.RESULT_READY`. Main verification and explicit WorkUnit acceptance are required before the unit becomes `ACCEPTED`. Dependencies unlock only from `ACCEPTED`.

One unchanged WorkUnit may use at most two fresh Agent attempts. A focused same-child `FOLLOWUP` stays inside one ExecutionBinding and has its own bounded correction budget. `CONTINUE` resumes the same interrupted ExecutionBinding and does not consume that correction budget.

## Scheduling

Scheduling is wakeup-driven reconciliation. A wakeup means Host or user state may have changed; it is never lifecycle truth by itself.

V4 policy is:

```text
initial managed children <= 2
normal managed children <= 3
Host capacity is an additional ceiling
longer downstream critical path wins ties before unit id
>= 2 RESULT_READY/VERIFYING units stops fresh fanout growth
empty capacity never justifies decorative work
```

Host capacity refers to spawned Agent threads still open in the Host. A completed or interrupted Agent can remain reusable and may still consume a Host thread slot until it is closed. Product scheduling therefore distinguishes active turns from open Host threads.

## PendingControl

Managed lifecycle operations use a single-use PendingControl:

```text
PREPARED
IN_FLIGHT
ACKED
UNKNOWN
CANCELLED
```

Supported operations are `SPAWN`, `FOLLOWUP`, `CONTINUE`, and `INTERRUPT`. A PendingControl is bound to the WorkUnit/ExecutionBinding identity, TeamPlan revision, execution control epoch, optional WriterLease epoch, exact lifecycle target, canonical tool-input digest, writer effect, and one Host `tool_use_id`.

`PreToolUse` consumes exactly one matching PREPARED control. Successful `PostToolUse` acknowledges that exact IN_FLIGHT control. Ambiguous acknowledgement remains fail closed. A missing PostToolUse never becomes an inferred ACK.

## WriterLease

V4.0.0 supports one canonical managed writer at a time. `WriterLease` is an orchestration mutual-exclusion permit, not an operating-system filesystem lock.

```text
RESERVED
HELD
REVOKING
UNKNOWN
RELEASED
```

Writing SPAWN, FOLLOWUP, and CONTINUE require the matching execution-owned WriterLease before Host activation. Successful lifecycle acknowledgement applies the authorized writer effect in the same state transaction as the PendingControl ACK.

Interrupt acknowledgement alone never releases or transfers a writer. Release or transfer requires current-generation Host settlement evidence, matching lease and control epochs, no unresolved PendingControl, and current managed lifecycle Guard coverage evidence. `UNKNOWN` blocks conflicting managed mutation and never expires automatically.

Main integration writes use the same WriterLease abstraction. A user takeover cannot bypass writer settlement.

## Host observations

V4 state normalizes only lifecycle evidence needed by orchestration. Every observation is captured against an execution identity and control epoch, with WriterLease epoch when applicable. Observations captured against an older generation are discarded.

Within one control epoch, delayed Host evidence must not reactivate a previously settled execution. A legal same-child reactivation first passes through FOLLOWUP or CONTINUE, which advances the control epoch, then fresh Host evidence may establish RUNNING for that new generation.

Host uncertainty stays explicit. Missing or conflicting identity evidence produces `UNKNOWN`; it never authorizes replacement work, writer transfer, or dependency acceptance.

## Lifecycle Guard and release gate

The V4 three-sided Guard target is staged in `docs/v4/hooks.json`:

```text
PreToolUse  -> authorize managed spawn/followup/interrupt
PostToolUse -> acknowledge the exact successful Host operation
SubagentStop -> prevent autonomous continuation of managed leaf Agents
```

The production `hooks/hooks.json` remains the hardened V3.x boundary until the real Host gate passes. Repository tests can validate state machines and Hook scripts, but they cannot prove the running Codex build actually invokes the required hooks with the required identities and payload semantics.

`docs/v4/host-smoke.json` is therefore a blocking V4.0.0 release contract. Current Hook definition trust, lifecycle Pre/Post coverage, sibling-control denial, missing-Post fail-closed behavior, payload binding compatibility, open-thread capacity behavior, and WriterLease acknowledgement semantics require direct Host evidence before activation and publication.

## Final Review

Main first establishes a verified candidate. When the consequence-based trigger codes in `contracts/final-review.md` apply, the exact candidate is bound with `scripts/review-artifact.py` for Git-backed deliverables or a deterministic SHA-256 boundary for non-Git artifacts.

A fresh Sol High Advisor with `fork_turns: none` reviews that exact candidate. Any material candidate mutation invalidates the old verdict. Required review remains unresolved until the exact current artifact has a valid `ship` verdict and the final artifact identity is reverified.

## Migration

V3.x live state is legacy evidence and is never silently rewritten into V4 state. Unresolved legacy ownership, active execution, pending takeover, corrupt state, V4 `WriterLease.UNKNOWN`, or unresolved PendingControl remains fail closed. Terminal legacy state may be explicitly cleaned up through the supported lifecycle path.

The ordinary V4 state remains bounded, temporary, thread-scoped, and outside the project working tree. It stores coordination metadata only, not raw prompts, child transcripts, reasoning traces, source copies, or full Host output.

## V4.0.0 exclusions

The release intentionally excludes dynamic effort routing, nested managed delegation, autonomous peer authority transfer, daemon scheduling, persistent orchestration databases, automatic worktree management, parallel isolated managed writers, and cross-WorkUnit Agent reuse by default.

These exclusions keep the major release centered on verifiable native lifecycle control and one-writer correctness.