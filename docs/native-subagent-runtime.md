# Native Subagent Runtime Contract

subagents-dispatch uses Codex Native Subagents directly. It does not create another Agent runtime, daemon, background poller, thread pool, routing proxy, control server, persistent scheduler database, or telemetry collector.

## Public entry points

The Plugin exposes exactly two explicit Skills:

```text
Orchestrate
Doctor
```

Orchestrate contains plan-only, status, steer, takeover, cancel, execution, recovery, review and integration inside one public Skill. Implicit invocation is disabled.

## Ownership boundary

Codex Host owns child materialization, native lifecycle, actual capacity and native control primitives.

The main session owns user intent, decomposition, semantic classification, dispatch judgment, integration and final acceptance. Managed model/effort is resolved from product policy rather than inherited from Main.

Project state owns WorkUnit responsibility and acceptance, ExecutionBinding identity and generation, and WriterLease.

Deterministic orchestration helpers report machine-checkable constraints. They do not rank ready WorkUnits, create critical-path priority, apply a fixed backlog threshold, or choose launch actions.

## Native control boundary

```text
fresh spawn
-> Main confirms role/tier semantics
-> deterministic policy resolves exact agent_type, model and reasoning_effort
-> fork_turns = none
-> Host success binds one child identity
-> explicit pre-materialization rejection rolls back provisional activation
-> ambiguous materialization becomes UNKNOWN

same-child recovery
-> reuse the same ExecutionBinding when continuity is useful and legal
-> advance control_epoch when the Host interaction changes generation

interrupt / takeover
-> request native interruption
-> interrupt return alone does not release WriterLease
-> current-generation Host settlement must prove the old writer is non-active
```

`UNKNOWN` never authorizes conflicting replacement execution, conflicting writer transfer or final acceptance.

## First-use readiness

Managed custom-Agent profiles live under the active Codex home and may not become selectable in a task that was already running when the files were created.

When delegation is useful but the exact role is unavailable:

```text
managed profiles safely absent
-> provision only Plugin-owned managed files
-> verify them
-> return RESTART_REQUIRED

managed profiles exact but current task still lacks the role
-> return RESTART_REQUIRED

unsafe/conflicting ownership state
-> USER_ACTION_REQUIRED
```

No speculative spawn is used to probe a known-stale registry boundary.

## Current exact routes

```text
subagents_dispatch_programmer           -> gpt-5.6-luna / max
subagents_dispatch_product_manager      -> gpt-5.6-sol  / medium | high
subagents_dispatch_department_director  -> gpt-6-astra  / high
```

The profiles do not pin model or effort. Exact requested route comes from `policy.json` and is explicit in each spawn; actual realized model/effort remains Host evidence. Mutation authority comes from the WorkUnit/ExecutionBinding rather than the role label, except Department Director is always semantic read-only. Managed profiles request a leaf-style collaboration posture and instruct children not to create or control further managed Agents. The depth-one product rule does not require Host-hard tool removal. If a task specifically requires Host-hard descendant isolation, that stronger fact must be established from the current Host or reported unavailable.

## Capacity and dispatch

Delegation is value-driven. Zero children is normal when delegation adds no value.

The product has one ceiling:

```text
managed children <= 4
```

This is a safety ceiling. It is not a desired fanout. Known Host capacity may reduce the available slots. Unknown Host capacity is left unknown and does not create a synthetic capacity token.

The main session chooses which ready responsibility to delegate and when. Spare capacity never justifies decorative work. Unprocessed useful results may be integrated before further dispatch when that better serves the task.

## Concurrency and writer ownership

Independent semantic-read Programmer/Product Manager responsibilities may overlap. If Host effective permission is broader than semantic authority, the batch requires no active canonical WriterLease plus before/after artifact-immutability binding. Any drift invalidates all workspace-dependent evidence from that batch. Host-proven effective read-only is the stronger assurance path.

The canonical mutable workspace has one active managed WriterLease. A second writer requires Host-verifiable isolated workspace ownership and a clear integration boundary. Intended file separation alone is insufficient.

WriterLease is orchestration ownership, not an OS or filesystem lock. A writing execution in an active, revoking or unknown generation remains blocking until current-generation Host evidence proves safe release or transfer.

## Context transfer

Every fresh managed child receives `fork_turns = none` plus the exact responsibility record from `contracts/responsibility-packet.md`.

The main session includes only task-needed context, accepted evidence and constraints. Raw transcripts, private reasoning and unverified child claims do not become inherited task truth. When continuity with one existing child is materially valuable, use same-child interaction instead of copying the full main-session history into a new child.

## Runtime evidence

Use public Host metadata first. When required runtime facts are unavailable and an exact local Codex rollout is accessible, the allowlisted inspectors may recover only the bounded identity, routing and permission metadata defined by `docs/runtime-attestation.md`.

Configured, requested, accepted and observed facts stay separate. Child prose is not observed runtime evidence.

## Completion and acceptance

Host completion produces candidate work and moves the WorkUnit to `RESULT_READY`. Main verifies the actual artifact and relevant evidence before `ACCEPTED`. Dependencies unlock only from WorkUnit acceptance.

Missing, stale or ambiguous Host state remains explicit rather than being inferred from elapsed time.
