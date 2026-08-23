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

The main session owns user intent, decomposition, explicit fixed-profile selection, dispatch judgment, integration and final acceptance.

Project state owns WorkUnit responsibility and acceptance, ExecutionBinding identity and generation, and WriterLease.

Deterministic orchestration helpers report machine-checkable constraints. They do not rank ready WorkUnits, create critical-path priority, apply a fixed backlog threshold, or choose launch actions.

## Native control boundary

```text
fresh spawn
-> exact managed agent_type chosen by Main
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

## Current exact roles

```text
subagents_dispatch_reader        -> gpt-5.6-luna  / max  / mutation none
subagents_dispatch_worker        -> gpt-5.6-luna  / max  / bounded source write when granted
subagents_dispatch_investigator  -> gpt-5.6-terra / high / mutation none
subagents_dispatch_solver        -> gpt-5.6-sol   / high / bounded source write when granted
subagents_dispatch_advisor       -> gpt-5.6-sol   / high / mutation none
```

Managed child profiles request a leaf-style collaboration posture and instruct children not to create or control further managed Agents. Profile configuration records intent only. Effective child collaboration surface, model, effort and sandbox are Host facts when those facts are material. The depth-one product rule does not require Host-hard tool removal. N1 verifies actual canonical managed execution and fails on child-issued nested Agent creation/control or descendant materialization. Only a requirement for Host-hard isolation depends on direct evidence such as collaboration-tool absence or authoritative Host denial.

## Capacity and dispatch

Delegation is value-driven. Zero children is normal when delegation adds no value.

The product has one ceiling:

```text
managed children <= 4
```

This is a safety ceiling. It is not a desired fanout. Known Host capacity may reduce the available slots. Unknown Host capacity is left unknown and does not create a synthetic capacity token.

The main session chooses which ready responsibility to delegate and when. Spare capacity never justifies decorative work. Unprocessed useful results may be integrated before further dispatch when that better serves the task.

## Concurrency and writer ownership

Independent read-only responsibilities may overlap when effective read-only behavior and responsibility independence are verifiable. If either cannot be established, use the conservative serial path.

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
