# Native Subagent Runtime Contract

subagents-dispatch uses Codex Native Subagents directly. It does not create another Agent runtime, daemon, background poller, thread pool, routing proxy, control server, persistent scheduler database, or telemetry collector.

## Public entry points

The Plugin exposes exactly two explicit Skills:

```text
Orchestrate
Doctor
```

Orchestrate contains plan-only, status, steer, takeover, cancel, continue, correction, execution, review and integration as control intents inside one public Skill. Implicit invocation is disabled.

## Native control boundary

Codex Host owns child materialization, lifecycle execution, actual capacity and native control primitives. subagents-dispatch adds product semantics around those facts:

```text
fresh spawn
-> exact managed agent_type
-> fork_turns = none
-> Host success binds one child identity
-> explicit pre-materialization rejection rolls back provisional activation
-> ambiguous materialization becomes UNKNOWN

same-child followup
-> same ExecutionBinding
-> one bounded focused correction budget
-> control_epoch advances

continue
-> same interrupted ExecutionBinding
-> no fresh-attempt or correction-budget consumption

interrupt / takeover
-> request native interruption
-> interrupt return alone does not release WriterLease
-> current-generation Host settlement must prove the old writer is non-active
```

`UNKNOWN` never authorizes replacement execution, conflicting writer transfer or final acceptance.

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

No speculative spawn is used to probe a known-stale registry boundary. A fresh task must expose the exact role before delegated execution proceeds.

## Current exact roles

```text
subagents_dispatch_reader        -> gpt-5.6-luna  / max   / mutation none
subagents_dispatch_worker        -> gpt-5.6-luna  / max   / bounded source write when granted
subagents_dispatch_investigator  -> gpt-5.6-terra / xhigh / mutation none
subagents_dispatch_solver        -> gpt-5.6-sol   / high  / bounded source write when granted
subagents_dispatch_advisor       -> gpt-5.6-sol   / high  / mutation none
```

Managed child profiles disable child multi-agent capability. Profile configuration proves intent only; observed model, effort and sandbox require Host evidence when those facts are material.

## Capacity and fanout

Delegation is value-driven. Zero children is normal when delegation adds no value.

Current product ceilings are:

```text
initial managed children <= 2
normal managed children <= 3
known Host capacity may reduce the ceiling
```

Unknown Host capacity does not block a bounded spawn attempt. The Host owns actual capacity and may reject the call. Spare capacity never justifies decorative work.

## Writer ownership

The current product manages one canonical mutable workspace. One active managed writer may own it at a time:

```text
Main while mutating
Luna Worker when granted bounded-source-write
Sol Solver when granted bounded-source-write
```

WriterLease is scheduling ownership, not an OS or filesystem lock. A writing execution in RUNNING, REVOKING or UNKNOWN remains blocking until current-generation Host settlement proves safe release or transfer.

## Context transfer

Every new managed child receives fresh context with `fork_turns = none` plus the exact five-section responsibility record from `contracts/responsibility-packet.md`.

Accepted evidence may be distilled into bounded responsibility context or a Handoff Capsule. Raw transcripts, private reasoning and unverified child claims do not become inherited task truth.

## Runtime evidence

Use public Host metadata first. When required runtime facts are unavailable and an exact local Codex rollout is accessible, the allowlisted inspectors may recover only the bounded identity/routing/permission metadata defined by `docs/runtime-attestation.md`.

Configured, requested, accepted and observed facts stay separate. Child prose is not observed runtime evidence.

## Completion and acceptance

Host completion produces candidate work and moves the WorkUnit to `RESULT_READY`. Main verifies the actual artifact and relevant evidence before `ACCEPTED`. Dependencies unlock only from WorkUnit acceptance.

Process no-longer-needed child work promptly when the native surface supports it. Missing, stale or ambiguous Host state remains explicit rather than being guessed.
