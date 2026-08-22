# Orchestration State

This contract owns short-lived project coordination state for one active V4 Native Core orchestration. It does not create another Agent runtime, Host lifecycle authority, scheduler daemon, event bus, or Hook control plane.

## Core invariant

One Main root thread has at most one active top-level subagents-dispatch orchestration.

Codex Host owns native child lifecycle truth. The state capsule owns WorkUnit responsibility, ExecutionBinding generation, WriterLease ownership, acceptance bookkeeping, and bounded recovery evidence.

## Storage boundary

Runtime state currently lives under the operating-system temporary directory:

```text
<OS TEMP>/subagents-dispatch/<CODEX_THREAD_ID>/active.json
```

Use a stable Host-provided root thread identity. Reject unsafe symlinks, malformed paths, oversized payloads, invalid schema, and non-private POSIX state files. Mutations use the schema-neutral short state lock and atomic replace boundary in `scripts/state_storage.py`.

The repository and user project tree are not orchestration-state stores. Durable Recovery Capsule work is a separate capability and must use the official Plugin data boundary when implemented.

## Active-state lifecycle boundary

`new_state()` is a pure payload factory. Persistence starts through `create_state_if_absent()`, which acquires the state lock and rejects every existing `active.json`; initialization cannot replace a live, ambiguous, or terminal capsule in place.

A completed orchestration leaves the active capsule in place until `remove_terminal_state()` re-reads it under the same state lock and proves:

- every WorkUnit is `ACCEPTED` or `CANCELLED`;
- no ExecutionBinding is `SPAWN_PENDING`, `RUNNING`, `INTERRUPTED`, or `UNKNOWN`;
- no WriterLease is `RESERVED`, `HELD`, `REVOKING`, or `UNKNOWN`;
- an optional expected `state_revision` still matches.

Only then may the active capsule be removed.

## V4 Native Core schema

The top-level payload contains exactly:

```text
schema_version
root_session_id
state_revision
team_plan_revision
work_units
executions
writer_lease
accounting_refs
created_at
updated_at
locale
```

`team_plan_revision` is an RC compatibility marker only. It has no planning, routing, dependency, integration-order, or execution-authorization semantics.

There is no `PendingControl`, Hook acknowledgement ledger, capacity token, `OperationIntent`, or `OperationReceipt` in the Native Core state schema.

The capsule must not persist raw prompts, child transcripts, private reasoning, source-file contents, webpages, credentials, secrets, or arbitrary Host tool output. Keep the existing 64 KiB bound.

## WorkUnit

WorkUnit owns responsibility and acceptance truth. It records intent, goal, output, dependencies, ownership/write boundaries, authority ceiling, completion condition, optional bounded responsibility context, and accepted result binding.

A dependency unlocks only when its predecessor WorkUnit reaches `ACCEPTED`. Host `COMPLETED` alone produces candidate evidence and never unlocks downstream work.

One WorkGraph may contain one or many WorkUnits without an independent TeamPlan runtime object.

## ExecutionBinding

ExecutionBinding records one fresh attempt identity and its current same-child activation generation:

```text
execution_id
unit_id
team_plan_revision
attempt_no
profile_id
agent_id
native_task_name
model
effort
granted_authority
granted_write_scope
workspace_id
lifecycle
control_epoch
followup_count
failure_origin
blocker
quarantine_reason
execution_basis_ref
```

`attempt_no` is a positive diagnostic sequence number and has no fixed product ceiling. A fresh retry after attempt 1 requires a changed execution basis relative to the retained recovery evidence that still authorizes the current retry. `followup_count` is a non-negative diagnostic count and has no fixed product ceiling.

Main should allocate fresh `execution_id` and `native_task_name` values for clear diagnostics. Active retained ExecutionBindings still require exact identity uniqueness. Correctness does not depend on an unbounded orchestration-lifetime tombstone set after older settled attempts are compacted. If an opaque identity is later reused after compaction, stale Host evidence is rejected by the full generation basis described below.

`control_epoch` is the generation counter for same-child followup, continue, and interrupt. A Host observation captured against an older epoch is stale and cannot settle the current activation.

Lifecycle values are:

```text
SPAWN_PENDING
RUNNING
INTERRUPTED
COMPLETED
FAILED
UNKNOWN
CLOSED
```

`UNKNOWN` requires `runtime_ambiguous` and blocks conflicting progress.

## Bounded execution history

The active state keeps the current ExecutionBinding fully represented. Older safely settled fresh attempts may be compacted into one `execution_history` record per WorkUnit.

An `execution_history` record contains exactly:

```text
ref
kind = execution_history
unit_id
compacted_attempts
max_attempt_no
last_execution_id
last_lifecycle
last_basis_ref
last_followup_count
```

Only `COMPLETED`, `FAILED`, or `CLOSED` historical executions may be compacted. The newest retained execution is not compacted by fresh-attempt allocation. Removing a compacted execution also removes Host observation and recovery-basis records that refer only to that execution.

Compaction intentionally removes old detail to keep the 64 KiB state bound. It therefore does not promise permanent memory of every historical opaque execution id, native task name, execution basis, or correction basis. Safety across compaction comes from WorkUnit and attempt generation plus the current full Host observation basis. Delayed Host evidence for an older generation is stale and cannot mutate the current generation even if an opaque id later appears again.

## WriterLease

WriterLease is a project scheduling invariant for the canonical checkout. It is not an OS lock and does not prove that another same-user process cannot write.

A writable execution reserves WriterLease before native activation. WriterLease remains blocking in:

```text
RESERVED
HELD
REVOKING
UNKNOWN
```

Release or transfer requires current-generation Host observation proving the execution is settled. An ambiguous writer observation makes the lease `UNKNOWN`. `UNKNOWN` never authorizes transfer.

Until effective read-only isolation is proven by Host evidence, a blocking canonical WriterLease also blocks starting another managed child in that canonical workspace.

## Native lifecycle flow

### Fresh spawn

```text
validate WorkUnit readiness/profile/authority/writer admission
-> require a changed execution basis for every retry relative to retained recovery evidence
-> compact only older safely settled attempts when needed
-> persist SPAWN_PENDING ExecutionBinding
-> reserve WriterLease when writable
-> Main invokes native spawn_agent
-> reconcile recognized Host result
```

A recognized pre-materialization rejection may roll back only the current provisional `SPAWN_PENDING` execution when there is no child identity or Host materialization evidence. An ambiguous result becomes `UNKNOWN`.

### Same-child activation

FOLLOWUP and CONTINUE reuse the same ExecutionBinding and advance `control_epoch`.

FOLLOWUP requires a non-empty correction basis. State persists only the SHA-256 basis digest for the retained correction generation in a `recovery_basis` record and rejects an exact replay while that retained basis is authoritative. Older correction-basis detail may be pruned when the control generation advances. FOLLOWUP increments `followup_count`.

CONTINUE applies only to an `INTERRUPTED` execution and does not increment `followup_count`.

Interrupt advances the generation as well. A writing interrupt moves WriterLease to `REVOKING` before Main asks the Host to interrupt. The interrupt call return alone does not release the lease.

## Host observation basis

Main is the trusted coordinator that invokes native tools and feeds observed Host lifecycle data to deterministic project state helpers.

Before reconciliation, capture:

```text
execution_id
unit_id
attempt_no
control_epoch
current lease_epoch or null
```

The helper re-reads authoritative state. If the basis no longer matches, or the referenced execution has already been compacted, return `stale` and do not mutate the newer generation. `unit_id` and `attempt_no` prevent an old observation from binding to a later ExecutionBinding merely because an opaque `execution_id` value was reused after compaction.

Normalize current Host status only into the lifecycle facts the project needs:

```text
pending_init / pendingInit -> RUNNING
running                    -> RUNNING
interrupted                -> INTERRUPTED
completed                  -> COMPLETED
errored                    -> FAILED
shutdown                   -> CLOSED
not_found / notFound       -> UNKNOWN
```

Missing identity is uncertainty. It does not prove that a prior writer stopped.

## Accounting references

`accounting_refs` contains bounded structured evidence facts with stable unique `ref` values among retained records.

Native Core currently recognizes compact forms for:

```text
host_observation
execution_history
recovery_basis
```

A `host_observation` binds an active execution generation to observed Host lifecycle. A `recovery_basis` stores only the SHA-256 digest needed for the retained same-child correction generation. `execution_history` summarizes safely compacted fresh attempts.

When `control_epoch` advances, Host observation and recovery-basis records from superseded generations may be removed before final state validation. This keeps same-child recovery bounded without adding an unbounded replay ledger.

Do not add raw user-facing receipt histories, raw prompts, control transcripts, or another request/receipt protocol under `accounting_refs`.

## Acceptance truth

Only Main accepts a WorkUnit after verifying the actual candidate.

An accepted WorkUnit must reference its current producing ExecutionBinding and exact current `control_epoch`. The producer must be `COMPLETED`, or `CLOSED` only when the same generation has stored Host evidence proving it previously completed.

Child prose, Host completion, or state transition by itself is insufficient acceptance evidence.

## Atomicity

State-changing helpers:

1. acquire the short state lock;
2. re-read authoritative current state;
3. validate the requested transition against current generation and lease identity;
4. mutate a copy;
5. prune superseded generation evidence when applicable;
6. increment `state_revision` only when the persisted state actually changes;
7. validate the complete payload;
8. atomically replace the state file.

A semantically duplicate Host observation that changes no persisted fact is a true no-op. It does not advance `state_revision` or `updated_at`.

Do not hold the state lock while waiting for child work or a Host call.

## Upgrade boundary

V3.x state is legacy compatibility evidence while V4 remains pre-release. Native Core has no compatibility promise for experimental V4 capsules created by the earlier Hook/PendingControl design.

After the V4 schema cutover, development and release validation start with fresh V4 state. V3.x profile/install ownership migration remains separately supported and tested.

## Normal completion

A terminal orchestration may remove active state after all responsibilities and writer ownership are safely settled and required acceptance/final-response work has completed. `UNKNOWN`, active execution, blocking WriterLease, or unresolved responsibility prevents silent cleanup.
