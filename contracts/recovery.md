# Recovery

Recovery owns what happens to one delegated WorkUnit after an ExecutionBinding has been created. It separates confirmed execution failure from Host uncertainty, requires changed evidence for repeated work, and preserves stable responsibility identity across fresh attempts.

`routing.md` decides which managed role/tier the unresolved work needs. WorkGraph and WorkUnit own responsibility and dependency truth. `interaction.md` owns user-facing control intent. `state.md` and WriterLease own project lifecycle generation and write ownership. Codex Host owns native lifecycle truth.

## Identity

Every concrete managed fresh attempt is an ExecutionBinding with:

```text
unit_id
execution_id
attempt_no
native_task_name
role_id
agent_type
model
reasoning_effort
agent_id, when Host evidence establishes it
control_epoch
execution_basis_ref
```

`unit_id` identifies the stable WorkUnit. `execution_id` identifies one retained fresh Agent attempt. A fresh retry preserves the WorkUnit, receives the next `attempt_no`, and must carry a changed execution basis relative to the retained recovery evidence that still authorizes the retry.

Main supplies a fresh `execution_id` for each fresh materialized attempt. The managed runtime derives `native_task_name` deterministically as `sd_<case-folded-unit-id>_a<attempt-no>`, so canonical Host control addresses advance with the WorkUnit attempt generation and cannot be reused after settled history compaction. A recognized pre-materialization rollback removes the provisional generation entirely, so the next allocation may still use the same attempt number and derived task name. Active retained ExecutionBindings require exact identity uniqueness. Bounded history compaction intentionally removes older opaque execution-id detail, so correctness does not rely on an unbounded orchestration-lifetime tombstone set. The full observation generation binds Host evidence to `unit_id`, `attempt_no`, `control_epoch`, and applicable WriterLease generation in addition to the opaque execution id.

A recognized Host rejection that is proven pre-materialization may roll back the provisional `SPAWN_PENDING` ExecutionBinding. If evidence cannot establish whether a child materialized, preserve `UNKNOWN` and do not issue conflicting replacement work.

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

`INTERRUPTED` is non-final. Continue resumes the same ExecutionBinding and advances `control_epoch`. It creates no fresh attempt and does not count as a correction.

`COMPLETED` means the Host produced a candidate result. The WorkUnit remains unresolved until Main verifies the actual artifact and relevant evidence and records `ACCEPTED`.

Use `FAILED` only for confirmed unsuccessful execution. Use `UNKNOWN` when current Host evidence cannot safely establish creation, identity, lifecycle, or settlement.

While an execution is `UNKNOWN`:

```text
no conflicting replacement Agent
no blind fresh retry
no duplicate semantic reroute
no conflicting writer transfer
no final acceptance
```

Timeout, absence, or elapsed time never converts `UNKNOWN` into `FAILED`.

## Host reconciliation

Main drives native lifecycle reconciliation.

Before a reconciliation-sensitive Host observation, capture the current ExecutionBinding observation basis. The deterministic helper re-reads authoritative state and applies the observation only when `execution_id`, `unit_id`, `attempt_no`, `control_epoch`, and applicable WriterLease generation still match.

A stale observation is discarded. An observation for an execution already compacted out of active state is stale by definition. Reuse of an opaque execution id after compaction cannot make an older observation current because the WorkUnit and attempt generation must also match. An ambiguous observation moves lifecycle to `UNKNOWN`. For a writable execution, ambiguity also keeps WriterLease blocking.

Normal recovery may use `list_agents`. Exact rollout inspection is reserved for ambiguous identity/materialization recovery and release attestation.

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

`runtime_ambiguous` belongs to `UNKNOWN` and does not become confirmed failure without new Host evidence.

## Evidence-gated recovery

There is no fixed fresh-attempt count or same-child follow-up count.

### Fresh retry

A fresh retry is legal only when all of the following hold:

```text
current prior execution is safely settled by Host truth
current prior execution is not UNKNOWN
no blocking WriterLease conflicts with the new execution
WorkUnit responsibility is still the same
execution_basis_ref records a changed execution basis
that basis is not an exact replay of currently retained recovery evidence
```

A changed basis may represent new evidence, corrected input, changed external conditions, a confirmed failure cause with a targeted fix, or another concrete change that makes repeating the responsibility rational.

`attempt_no` is a diagnostic sequence number. It is not a product ceiling and never authorizes a retry by itself.

Older execution-basis detail may be compacted. Recovery therefore does not claim permanent replay memory for every historical basis. The safety property is that the current retry must be justified by retained evidence and that stale Host observations cannot cross WorkUnit/attempt generations.

### Same-child FOLLOWUP

FOLLOWUP reuses the same ExecutionBinding when the same child remains the right owner and one focused correction remains inside the existing WorkUnit boundary.

Each FOLLOWUP must provide a non-empty correction basis. The project stores only its SHA-256 digest for the retained correction generation and rejects an exact replay while that retained basis remains authoritative. FOLLOWUP advances `control_epoch` and increments `followup_count`; the count is diagnostic, not an authorization budget.

When `control_epoch` advances, superseded Host observation and recovery-basis records may be pruned. Recovery does not maintain an unbounded set of every correction digest ever used. A material change to goal, output, ownership, scope, authority, or acceptance meaning still requires Main to re-evaluate the WorkUnit instead of disguising the change as another correction.

### CONTINUE

CONTINUE applies only to the same `INTERRUPTED` ExecutionBinding. It advances `control_epoch`, creates no fresh attempt, and does not increment `followup_count`.

## Bounded retained history

Removing fixed recovery ceilings must not make active state grow without bound.

The current execution remains fully represented. Older safely settled fresh attempts may be compacted into one `execution_history` summary per WorkUnit. The summary preserves:

```text
number of compacted attempts
highest compacted attempt_no
last compacted execution identity and lifecycle
last compacted execution basis
last compacted followup_count
```

Host observations and follow-up basis records that refer only to compacted executions are removed with those executions. Superseded same-child generation evidence may also be pruned when `control_epoch` advances. A delayed observation for an older generation is stale and cannot mutate the current generation.

Do not persist raw prompts, child transcripts, private reasoning, source contents, webpage contents, credentials, or token logs as recovery history.

## Recovery actions

```text
same-child FOLLOWUP
same-child CONTINUE
fresh retry
semantic reroute
Main takeover
```

FOLLOWUP and CONTINUE reuse the same ExecutionBinding. Fresh retry creates a new ExecutionBinding for the same WorkUnit after the prior execution and writer ownership are safely settled.

Semantic reroute is justified only when newly accepted task truth changes the required managed role or Product Manager decision tier. Failure, file count, low confidence, or spare capacity never defines an automatic model/effort escalation chain, and a child cannot self-escalate from Product Manager Medium to High.

## WriterLease recovery

A writable execution reserves WriterLease before native activation.

For interrupt/takeover, WriterLease enters `REVOKING` before Main requests native interruption. The native interrupt return alone does not prove writer settlement.

Current-generation Host settlement evidence is required before release or transfer. A lifecycle ambiguity makes the lease `UNKNOWN`; `UNKNOWN` never transfers. A later clear current-generation observation may recover the same lease to a settleable state.

Until the Host Capability Gate proves effective read-only isolation, a blocking canonical WriterLease also blocks starting another managed child in that canonical workspace.

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

A user takeover request expresses intent to transfer ownership. It does not prove that the child stopped. Missing or `notFound` identity evidence remains uncertainty and cannot authorize conflicting mutation.

## Evidence and close

Stopping, interrupting, closing, or completing an Agent does not make its claims correct. Main verifies useful returned evidence and the actual candidate artifact.

`CLOSED` is lifecycle truth, not correctness proof. Recovery uses bounded V4 state plus native Host evidence. Do not create a second repository-local ledger, request/receipt protocol, scheduler database, or private Agent runtime.
