# Recovery

Recovery owns what happens to one delegated WorkUnit after an ExecutionBinding has been created. It distinguishes confirmed execution failure from Host uncertainty, keeps correction bounded, and preserves stable responsibility identity across attempts.

`routing.md` decides which capability the unresolved work needs. `team-plan.md` owns multi-responsibility structural truth when TeamPlan is active. `interaction.md` owns user-facing control intent. `state.md` and WriterLease own project lifecycle generation and write ownership. Codex Native Subagents own native lifecycle truth.

## Identity

Every concrete managed attempt is an ExecutionBinding with:

```text
unit_id
execution_id
attempt_no
team_plan_revision: positive integer | null
native_task_name
profile_id
agent_id, when Host evidence establishes it
control_epoch
```

`unit_id` identifies the stable WorkUnit. `execution_id` identifies one materialized fresh Agent attempt. A retry preserves the WorkUnit and receives a new `execution_id` and incremented `attempt_no`.

A recognized Host rejection that is proven pre-materialization may roll back the provisional `SPAWN_PENDING` ExecutionBinding and does not consume the fresh-attempt budget. If evidence cannot establish whether a child materialized, preserve `UNKNOWN` and do not issue replacement work.

## Execution lifecycle

```text
SPAWN_PENDING
RUNNING
INTERRUPTED
COMPLETED
FAILED
UNKNOWN
CLOSED
```

A normal activation begins from `SPAWN_PENDING`, becomes `RUNNING` when Host evidence establishes an active materialized child, then reaches a settled Host state when current-generation evidence supports it.

`INTERRUPTED` is non-final. Continue resumes the same ExecutionBinding and advances `control_epoch`. It creates no fresh attempt and consumes no focused-followup budget.

`COMPLETED` means the Host produced a candidate result. The WorkUnit remains unaccepted until Main verifies the actual artifact and relevant evidence.

Use `FAILED` only for confirmed unsuccessful execution. Use `UNKNOWN` when current Host evidence cannot safely establish creation, identity, lifecycle, or settlement.

While an execution is `UNKNOWN`:

```text
no replacement Agent
no fresh retry
no duplicate semantic reroute
no conflicting writer transfer
no final acceptance
```

## Host reconciliation

Main drives native lifecycle reconciliation.

Before a reconciliation-sensitive Host observation, capture the current ExecutionBinding observation basis. The deterministic helper re-reads authoritative state and applies the observation only when the `execution_id`, `control_epoch`, and applicable WriterLease generation still match.

A stale observation is discarded. An ambiguous observation moves lifecycle to `UNKNOWN`. For a writable execution, ambiguity also keeps WriterLease blocking.

Normal recovery may use `list_agents`. Exact root rollout inspection is reserved for cases where native call materialization or identity remains ambiguous, and for release attestation. Recovery authority comes from current Host observations and bounded local state.

## Failure and blocker axes

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

Semantic blocker:

```text
none
contract
judgment
investigation
stalled
```

`runtime_ambiguous` belongs to `UNKNOWN` and does not become confirmed failure.

## Bounded correction

One unchanged WorkUnit may use at most:

```text
2 fresh Agent attempts
1 focused same-child follow-up
```

Only materialized fresh attempts consume `attempt_no`. A focused followup stays inside the same ExecutionBinding, advances `control_epoch`, preserves responsibility/profile/authority, and is appropriate only when one narrow correction can plausibly satisfy acceptance.

Continue resumes an interrupted execution and does not consume the focused-followup budget.

A second fresh attempt starts only after the previous attempt is safely settled and the WorkUnit remains unresolved. After two fresh attempts, Main takes ownership or reports the blocker instead of silently creating a third child.

## Recovery actions

```text
same-child FOLLOWUP
same-child CONTINUE
fresh retry
semantic reroute
Main takeover
```

FOLLOWUP and CONTINUE reuse the same ExecutionBinding and advance its current generation.

Fresh retry creates a new ExecutionBinding for the same WorkUnit. It cannot start while an earlier attempt, an `UNKNOWN` lifecycle, or its WriterLease remains active or ambiguous.

Semantic reroute is justified only when unresolved task truth changes the capability required by the WorkUnit. Role changes do not reset the two-attempt budget.

Failure alone never defines an automatic Luna, Terra, Sol escalation chain.

## WriterLease recovery

A writable execution reserves WriterLease before native activation.

For interrupt/takeover, WriterLease enters `REVOKING` before Main requests native interruption. The native interrupt result alone does not prove writer settlement.

Current-generation Host settlement evidence is required before release or transfer. A lifecycle ambiguity makes the lease `UNKNOWN`; `UNKNOWN` never transfers. A later clear current-generation observation may recover the same lease to a settleable state.

## Main takeover

Takeover continues the same unresolved WorkUnit in Main only after the managed owner is safely settled.

```text
resolve current WorkUnit and ExecutionBinding
-> request native interruption when needed
-> establish current-generation Host settlement evidence
-> verify usable returned evidence
-> settle WriterLease when applicable
-> transfer responsibility to Main
```

A user takeover request expresses intent to transfer ownership. It does not prove that the child has stopped. Missing or `notFound` identity evidence remains uncertainty and cannot authorize conflicting mutation.

Takeover does not create another fresh Agent attempt or erase attempt history.

## Acceptance and retry

Host `COMPLETED` supplies candidate execution evidence. Main verifies the result before WorkUnit acceptance.

If a completed candidate fails acceptance, use the one focused FOLLOWUP when the same execution remains the right owner and the correction is narrow. Otherwise reject the candidate and use the remaining fresh-attempt budget only after safe settlement.

Accepted WorkUnits are not reactivated by delayed Host evidence. A legal same-child reactivation advances `control_epoch`, so older observations cannot settle the current generation.

## TeamPlan revisions

Retry alone does not require a TeamPlan revision. A role, dependency, ownership scope, deliverable, task scope, or acceptance change may require a new revision under `team-plan.md`.

Without TeamPlan, one dependency-free WorkUnit keeps `team_plan_revision = null` throughout its bounded execution history.

## Evidence and close

Stopping, interrupting, closing, or completing an Agent does not make its claims correct. Main verifies useful returned evidence and the actual candidate artifact.

`CLOSED` is lifecycle truth, not correctness proof. Recovery uses the bounded V4 state capsule and native Host evidence. Do not create a second repository-local ledger, request/receipt protocol, scheduler database, or private Agent runtime.
