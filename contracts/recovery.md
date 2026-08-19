# Recovery

Recovery owns what happens to one delegated WorkUnit after an ExecutionBinding has been created. It distinguishes confirmed execution failure from Host uncertainty, keeps correction bounded, and preserves stable responsibility identity across attempts.

`routing.md` decides which capability the unresolved work needs. `team-plan.md` owns multi-responsibility structural truth when TeamPlan is active. `interaction.md` owns user-facing control intent. Writer ownership and lifecycle authorization remain enforced by the deterministic V4 state, PendingControl, WriterLease, and Host evidence paths.

## Identity

Every concrete managed attempt is an ExecutionBinding with:

```text
unit_id
execution_id
attempt_no
team_plan_revision: positive integer | null
native_task_name
profile_id
agent_id, when current Host evidence establishes it
control_epoch
```

`unit_id` identifies the stable WorkUnit responsibility. `execution_id` identifies one concrete fresh Agent attempt. A retry preserves the WorkUnit and receives a new `execution_id` and incremented `attempt_no`.

For one delegated responsibility without TeamPlan, `team_plan_revision` remains `null`. When TeamPlan is active, each ExecutionBinding stays bound to the applicable positive revision.

A Host call rejected before a child identity materializes does not consume a fresh-attempt budget. If current evidence cannot establish whether a child was created, preserve `UNKNOWN` and do not issue replacement work.

## Execution lifecycle

The current V4 ExecutionBinding lifecycle is:

```text
SPAWN_PENDING
RUNNING
INTERRUPTED
COMPLETED
FAILED
UNKNOWN
CLOSED
```

A normal fresh execution progresses from `SPAWN_PENDING` to `RUNNING`, then to a Host-settled state such as `COMPLETED`, `FAILED`, or `CLOSED` when current evidence supports that transition.

`INTERRUPTED` is non-final. `CONTINUE` resumes the same ExecutionBinding and advances the control generation through the existing PendingControl path. It does not create a fresh attempt or consume the focused follow-up budget.

`COMPLETED` means the Host reports that the Agent produced a candidate result. The WorkUnit remains unaccepted until the main session verifies the relevant artifact and evidence. Downstream dependencies unlock only after WorkUnit acceptance.

Use `FAILED` only for a confirmed unsuccessful execution. Use `UNKNOWN` when current Host evidence cannot safely establish creation, identity, current lifecycle, or settlement. UNKNOWN is not failure.

While an execution remains `UNKNOWN`:

```text
no replacement Agent
no fresh retry
no semantic reroute that duplicates the owned responsibility
no conflicting writer transfer
no acceptance claim
```

Missing or delayed Host evidence never becomes inferred success or inferred failure.

## Failure and blocker axes

A confirmed unsuccessful execution records its execution origin separately from the unresolved semantic blocker.

Execution origin:

```text
none
runtime_unavailable
permission_failure
tool_failure
timeout
quality_failure
runtime_ambiguous
```

`runtime_ambiguous` accompanies uncertainty and does not convert UNKNOWN into confirmed failure.

Semantic blocker:

```text
none
contract
judgment
investigation
stalled
```

The first axis says what happened to execution. The second says what capability or task truth is still missing. Infrastructure failure by itself is not capability evidence.

## Bounded correction

One unchanged WorkUnit may use at most:

```text
2 fresh Agent attempts
1 focused same-child follow-up
```

Only materialized fresh attempts consume `attempt_no`. A focused follow-up stays inside the same ExecutionBinding, preserves the same responsibility, profile and authority, and is appropriate only when a completed candidate is close enough that one narrow correction can satisfy acceptance.

`CONTINUE` resumes an interrupted execution and does not consume the focused follow-up budget.

A second fresh attempt is allowed only after the previous attempt is safely settled and the same WorkUnit remains unresolved. After two fresh attempts, the main session takes ownership or reports the exact blocker instead of silently creating a third attempt.

## Recovery actions

Use the existing managed operations and semantic outcomes:

```text
same-child FOLLOWUP
same-child CONTINUE
fresh retry
semantic reroute
main-session takeover
```

A focused FOLLOWUP preserves WorkUnit identity and ExecutionBinding identity.

CONTINUE preserves the same interrupted ExecutionBinding identity and requires the current lifecycle protocol to authorize reactivation.

A fresh retry creates a new ExecutionBinding for the same stable WorkUnit. It must not start while an earlier attempt or its writer/control state remains active or ambiguous.

Semantic reroute happens only when the unresolved blocker changes the capability that the WorkUnit requires. If TeamPlan is active and the delegated role changes, create the appropriate new TeamPlan revision before the replacement execution. Role changes never reset the two-attempt budget.

Failure alone never defines an automatic Luna, Terra, Sol escalation chain.

## PendingControl and WriterLease

Lifecycle operations use the current PendingControl contract. A prepared operation is bound to its exact ExecutionBinding generation, target, tool input, control epoch, applicable WriterLease epoch, and Host `tool_use_id` when the operation enters flight.

A missing or ambiguous acknowledgement stays fail closed. Do not infer an ACK from elapsed time or later conversational output.

For writable execution, WriterLease ownership remains authoritative for the canonical workspace. Interrupt acknowledgement alone does not prove that the writer is safely settled. Main-session mutation or transfer to another writer requires current-generation Host settlement evidence and all existing WriterLease conditions.

## Main-session takeover

Takeover continues the same unresolved WorkUnit in the main session only after the previous managed owner is safely settled.

A safe takeover sequence is:

```text
resolve the current WorkUnit and ExecutionBinding
request interruption when needed and supported
establish current Host settlement evidence
preserve and verify any usable returned evidence
settle writer ownership when applicable
end delegated execution for the WorkUnit
continue that same responsibility in the main session
```

A user takeover request changes intended ownership. It does not prove that the child has stopped. If Host state remains UNKNOWN, conflicting mutation remains blocked.

Takeover does not create another fresh Agent attempt and does not reset attempt history. When TeamPlan is active, a pure takeover does not invent a `main` delegated role. Revise TeamPlan only if structural truth such as dependency, ownership scope, deliverable, scope, or acceptance also changes.

## WorkUnit acceptance and retry

Host `COMPLETED` supplies candidate execution evidence. The main session verifies the result before WorkUnit acceptance.

If a completed candidate fails acceptance, use the one focused FOLLOWUP when the same execution remains the right owner and the correction is narrow. Otherwise reject the WorkUnit candidate, settle the current execution, and use the remaining fresh-attempt budget only when policy still supports another managed attempt.

Accepted WorkUnits are not reactivated by delayed Host evidence from the same control generation. A legal same-child reactivation first passes through FOLLOWUP or CONTINUE, which advances the current control generation under the deterministic lifecycle code.

## TeamPlan revisions

A retry alone does not require a TeamPlan revision. A delegated role, dependency, ownership scope, deliverable, scope, or acceptance change may require a new revision under `team-plan.md`.

Already-dispatched execution remains bound to the revision it received. A replacement execution for the same WorkUnit must never bind to a revision older than a prior attempt.

Without TeamPlan, one dependency-free WorkUnit keeps `team_plan_revision = null` throughout its bounded execution history.

## Evidence and close

Stopping, interrupting, or closing an Agent does not make its claims true. The main session verifies any useful returned evidence before reuse.

`CLOSED` is lifecycle truth, not correctness proof. WorkUnit acceptance continues to require current accepted evidence and the exact producing ExecutionBinding generation required by the V4 state contract.

Ordinary V4 recovery uses the bounded current V4 state as its coordination truth. Do not create a second repository-local ledger, scheduler database, or private Agent runtime for recovery.
