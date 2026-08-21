# Orchestration State

This contract owns short-lived project coordination state for one active V4 Native Core orchestration. It does not create another Agent runtime, Host lifecycle authority, scheduler daemon, event bus, or Hook control plane.

## Core invariant

One Main root thread has at most one active top-level subagents-dispatch orchestration.

Codex Native Subagents own native lifecycle truth. The state capsule owns project responsibility, generation, write ownership, and acceptance bookkeeping.

## Storage boundary

Runtime state lives under the operating-system temporary directory:

```text
<OS TEMP>/subagents-dispatch/<CODEX_THREAD_ID>/active.json
```

Use a stable Host-provided root thread identity. Do not invent a durable identity from repository path, user text, or another unrelated property. Reject unsafe symlinks, malformed paths, oversized payloads, invalid schema, and non-private POSIX state files. Mutations use the schema-neutral short state lock and atomic replace boundary in `scripts/state_storage.py`.

The repository and user project tree are not orchestration-state stores.

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

There is no `PendingControl`, Hook acknowledgement ledger, capacity token, `OperationIntent`, or `OperationReceipt` in the Native Core state schema.

The capsule must not persist raw prompts, child transcripts, private reasoning, source-file contents, webpages, credentials, secrets, or arbitrary Host tool output. Keep the existing 64 KiB bound.

## WorkUnit

WorkUnit owns responsibility and acceptance truth. It records intent, goal, output, dependencies, ownership/write boundaries, authority ceiling, completion condition, optional bounded responsibility context, and accepted result binding.

A dependency unlocks only when its predecessor WorkUnit reaches `ACCEPTED`. Host `COMPLETED` alone produces candidate evidence and never unlocks downstream work.

A WorkUnit may reference at most two contiguous fresh execution attempts. A safe recognized pre-materialization rejection may remove a provisional `SPAWN_PENDING` execution before it becomes an attempt.

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
```

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

## WriterLease

WriterLease is a project scheduling invariant for the canonical checkout. It is not an OS lock and does not prove that another same-user process cannot write.

A writable execution reserves WriterLease before native activation. WriterLease remains blocking in:

```text
RESERVED
HELD
REVOKING
UNKNOWN
```

Release or transfer requires current-generation Host observation proving the execution is settled. An ambiguous writer observation makes the lease `UNKNOWN`. A later clear current-generation observation may recover the lease to a settleable state. `UNKNOWN` never authorizes transfer.

## Native lifecycle flow

### Fresh spawn

```text
validate responsibility/profile/attempt/writer admission
-> persist SPAWN_PENDING ExecutionBinding
-> reserve WriterLease when writable
-> Main invokes native spawn_agent
-> reconcile recognized Host result
```

Recognized success binds the expected child identity and lifecycle.

A recognized pre-materialization rejection may roll back only the current provisional `SPAWN_PENDING` execution when there is no child identity or Host materialization evidence. An ambiguous result becomes `UNKNOWN`.

### Same-child activation

Followup and Continue reuse the same ExecutionBinding and advance `control_epoch`. They do not create a fresh attempt.

Interrupt advances the generation as well. A writing interrupt moves WriterLease to `REVOKING` before Main asks the Host to interrupt. The interrupt call result alone does not release the lease.

## Host observation basis

Main is the trusted coordinator that invokes native tools and feeds observed Host lifecycle data to deterministic project state helpers.

Before a reconciliation-sensitive observation, capture:

```text
execution_id
control_epoch
current lease_epoch or null
```

The reconciliation helper re-reads authoritative state. If the basis no longer matches, return `stale` and do not mutate the newer generation.

Normal status/recovery may use `list_agents`. Exact rollout inspection is reserved for ambiguous recovery and release attestation. No persisted PreToolUse preparation record is required.

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

`accounting_refs` contains bounded structured evidence facts with a stable unique `ref`. Native Core uses it for recovery-relevant Host observations and other compact accepted evidence that is required by state validation.

A `host_observation` record binds:

```text
ref
kind = host_observation
execution_id
control_epoch
lease_epoch
lifecycle
```

Do not add user-facing receipt counters, control history, retry/rework ledgers, or a second request/receipt protocol under `accounting_refs`.

## Acceptance truth

Only Main accepts a WorkUnit after verifying the actual candidate.

An accepted WorkUnit must reference its current producing ExecutionBinding and the exact current `control_epoch`. The producer must be `COMPLETED`, or `CLOSED` only when the same generation has a stored Host observation proving it previously completed.

Child prose, Host completion, or state transition by itself is insufficient acceptance evidence.

## Simple phase isolation

Because the tested Host did not enforce the requested read-only sandbox for managed read roles:

- managed Reader, Investigator, and Advisor executions may overlap one another when independent;
- a writable Worker or Solver starts only after managed read-oriented executions have settled;
- while WriterLease is blocking, no other managed child starts in the canonical checkout;
- Final Review starts only after the writer settles;
- `UNKNOWN` counts as active/blocking.

This is scheduler policy. It does not require persisted phase state.

## Atomicity

State-changing helpers:

1. acquire the short state lock;
2. re-read authoritative current state;
3. validate the requested transition against current generation/lease identity;
4. mutate a copy;
5. increment `state_revision`;
6. validate the complete payload;
7. atomically replace the state file.

Do not hold the state lock while waiting for child work or a Host call.

## Upgrade boundary

V3.x state is legacy compatibility evidence while V4 remains pre-release. Native Core has no compatibility promise for experimental V4 capsules created by the earlier Hook/PendingControl design.

After the V4 schema cutover, development/release validation starts with fresh V4 state. An old experimental V4 capsule containing removed fields is invalid and requires explicit cleanup/restart. V3.x profile/install ownership migration remains separately supported and tested.

## Normal completion

A terminal orchestration may remove active state after all responsibilities and writer ownership are safely settled and required acceptance/final-response work has completed. `UNKNOWN`, active execution, blocking WriterLease, or unresolved responsibility prevents silent cleanup.
