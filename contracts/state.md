# Dispatch State

This contract owns short-lived coordination continuity for an active subagents-dispatch orchestration. It does not create another scheduler, database, daemon, event bus, or Agent runtime.

## Purpose

The Main session may be interrupted while native child Agents remain inspectable or resumable. Explicit Status, Steer, Takeover, and Dispatch-resume entry points therefore need a small amount of thread-scoped coordination truth that survives a turn boundary without polluting the repository.

The state is an index over native work, not a copy of the work itself.

## Core invariant

One Main root thread has at most one active top-level subagents-dispatch orchestration.

A different user task must not silently create a second top-level orchestration in the same root thread while an existing writer, UNKNOWN owner, pending takeover, or other unresolved active state remains.

## Storage boundary

Ordinary runtime state lives under the operating-system temporary directory:

```text
<OS TEMP>/subagents-dispatch/<CODEX_THREAD_ID>/active.json
```

`CODEX_THREAD_ID` is the preferred root-thread isolation key when the Host exposes it. If a stable thread identity is unavailable, do not invent one from repository path, current working directory, user text, or a random long-lived identifier. Cross-turn controls that require durable binding must fail closed when the current root thread cannot be identified reliably.

The repository, `.codex/`, and the user's project working tree are not dispatch-state stores.

## What active.json may contain

Store only compact coordination metadata required to recover the current control surface:

```text
schema version
root thread identity
locale
created / updated timestamps
active TeamPlan revision when one exists
native unit / task / attempt / child identity bindings
single-unit responsibility snapshot when no TeamPlan exists
control / review / recovery accounting references
pending takeover or reconciliation metadata when required
```

For a single delegated responsibility without TeamPlan, the compact responsibility snapshot may contain only the semantic fields required to identify the work safely, such as unit id, outcome, intent, delegated role, bounded write scope, and acceptance.

Do not persist raw user prompts, child transcripts, private reasoning, source-file contents, web pages, full tool output, credentials, secrets, or a duplicate evidence corpus.

## TeamPlan and ledger validation

TeamPlan and recovery-ledger payloads remain canonical structured coordination representations. When a deterministic validator is required, pass the current payload through stdin where supported. Do not create one JSON file per validation merely because a validator accepts a path.

An active state capsule may embed the current validated TeamPlan and recovery ledger because they are the coordination truth required for cross-turn recovery. Do not create a second persistent requirement ledger around them.

## Lifecycle

```text
Preview
-> never creates active state

explicit Dispatch with zero child Agents
-> does not create active state

before the first real child spawn
-> create or atomically update active state with SPAWN_PENDING

Host returns an inspectable child identity
-> bind the native identity and transition the attempt to RUNNING

Status / Steer / Takeover / Dispatch resume
-> resolve the same thread-scoped active state
-> reconcile with current native Host evidence before acting

normal terminal orchestration
-> produce the final Dispatch Receipt snapshot
-> remove active.json

Main interruption / UNKNOWN / pending writer settlement / parked user decision
-> retain the capsule temporarily
```

The normal steady state after completed work is no dispatch-state file.

## Spawn crash window

Persist the prepared attempt before invoking the Host:

```text
prepare unit + unique task id + deterministic native task name
-> active state records SPAWN_PENDING
-> invoke spawn_agent
-> Host returns child identity
-> active state records RUNNING + child identity
```

Use deterministic non-sensitive native task names derived from orchestration identity, for example `sd-u2-a1-execute`. Do not place user content or repository secrets in native task names.

If Main is interrupted after native creation but before the returned child identity is persisted, a later Status may reconcile a SPAWN_PENDING record against native Agent listings and rebind only when identity is unambiguous. Ambiguity remains UNKNOWN and never authorizes a replacement Agent.

## State truth versus Host truth

The capsule owns coordination truth. Codex Native Subagents own runtime lifecycle truth.

```text
capsule
-> responsibility, dependency, ownership, attempt identity, accounting

native Host
-> current native child status and identity evidence
```

For the currently supported Codex native child-status surface, normalize only the observable lifecycle facts needed by this contract:

```text
pendingInit  -> RUNNING once an inspectable child identity exists
running      -> RUNNING
interrupted  -> INTERRUPTED
completed    -> COMPLETED
errored      -> FAILED
shutdown     -> CLOSED
notFound     -> UNKNOWN
```

`SPAWN_PENDING` remains the pre-identity crash-window state owned by the capsule. Do not map a materialized child with an inspectable identity back into that pre-identity state. `notFound` is missing runtime identity evidence, not proof that a previous writer stopped; it therefore cannot release write authority.

Status performs one native observation and reconciliation. A stale capsule value must not override newer explicit Host state.

When Host and capsule identity evidence conflict, quarantine the affected attempt. Do not retry, replace, transfer writer ownership, or claim successful takeover until the conflict is resolved.

## INTERRUPTED

`INTERRUPTED` is a non-final delegated-attempt state when the native Host reports an interrupted child turn.

```text
RUNNING -> INTERRUPTED
INTERRUPTED -> RUNNING
```

Resuming the same native child keeps the same unit id, task id, attempt number, Agent identity, delegated role, and authority. It is not a retry, focused follow-up, rework pass, or new delegated work pass.

An interrupted writer is not proven settled. Main may begin conflicting mutation only after native evidence establishes that the previous writer is no longer active.

## Atomicity and local safety

State operations must be deterministic and short-lived:

```text
one state lock for mutation/reconciliation critical sections
write temporary file
flush as appropriate
atomic replace
```

Receipt events use the same mutation boundary. `accounting_refs` contains unique structured events keyed by a stable `ref`; `persist_receipt_events` re-reads, merges, validates, and atomically replaces the capsule while holding the state lock. Reconciliation or resume may persist the same event again without incrementing visible totals.

`prepare_spawn` re-reads and updates authoritative state under the same lock and rejects a second active writer in the canonical workspace. State validation may still represent multiple observed writers so Doctor can expose and quarantine Host truth rather than hiding it. `remove_state` accepts terminal capsules only; planned, active, interrupted, pending-takeover, or unknown work must be settled first.

Reject unsafe symlinked state roots, thread directories, state files, or locks. Use restrictive local file permissions where the platform supports them. POSIX implementations enforce owner-only mode bits for state directories/files/locks. Windows must not treat POSIX-style `st_mode` bits as an ACL proof; it retains the user-scoped OS temporary-directory boundary plus regular-file, path, symlink, size, schema, and locking checks. Validate the thread-id path component before constructing filesystem paths.

The lock coordinates state-file updates only. It is not a scheduler lock and must not be held while waiting for long-running child execution.

## Stale cleanup

Normal completion removes state immediately. Unexpected App or process termination may leave small stale capsules in the operating-system temporary directory.

A default stale horizon of seven days is acceptable for non-current thread state. The current root thread is never removed merely because of age while it is actively being controlled. Before deleting a stale capsule that claims active native work, reconcile when reliable native identity is still available; otherwise fail closed rather than assuming a writer disappeared. Cleanup must re-read and revalidate the candidate under the state lock immediately before unlinking so concurrently refreshed state cannot be deleted from stale pre-lock evidence.

Doctor may report current, stale, corrupt, unsafe, and forbidden repository-local state. Diagnosis is read-only by default. Explicit cleanup may remove only state proven to belong to subagents-dispatch and terminal; planned work and pending takeover are unresolved, not disposable.

## Control entry points

Status, Steer, Takeover, and Dispatch resume share this state contract. None maintains a private state machine.

A control detour is interaction semantics, not a delegated lifecycle transition by itself:

```text
user opens Status
!= Agent failure
!= retry
!= semantic reroute
!= ownership transfer
```

The native child lifecycle changes only when the Host reports or accepts a corresponding runtime action.
