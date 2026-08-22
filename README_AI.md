# subagents-dispatch: AI Agent Reference

Current V4 product surface: `Orchestrate` and `Doctor`.

## Runtime ownership

Codex Host owns child materialization, lifecycle truth, identity, and actual capacity.

Main owns user intent, decomposition, explicit fixed-profile selection, dispatch judgment, integration, WorkUnit acceptance, irreversible external side effects, and the final response.

WorkGraph and WorkUnit state own responsibility structure, dependencies, ownership, and acceptance. ExecutionBinding owns one concrete child execution. WriterLease owns managed write responsibility.

A `team_plan_revision` field may remain temporarily as a V4 RC state-schema compatibility marker. It is not a separate planning, routing, or integration authority.

## Fixed managed profiles

```text
Reader        gpt-5.6-luna   max    read-only intent
Worker        gpt-5.6-luna   max    bounded source write when granted
Investigator  gpt-5.6-terra  high   read-only intent
Solver        gpt-5.6-sol    high   bounded source write when granted
Advisor       gpt-5.6-sol    high   read-only judgment/review
```

Main selects one fixed profile explicitly for each delegated responsibility. Runtime code validates the selection. There is no automatic Luna, Terra, Sol escalation ladder.

## Dispatch invariants

```text
managed children <= 4
fork_turns = none
delegation depth = 1
Host COMPLETED produces candidate work only
WorkUnit ACCEPTED unlocks dependencies
UNKNOWN blocks conflicting replacement, writer transfer, and final acceptance
interrupt return alone never releases WriterLease
```

Four children is a safety ceiling, not a target. Known Host capacity may reduce available slots. Unknown capacity stays unknown. Deterministic helpers report constraints and status; they do not rank WorkUnits, apply a fixed backlog threshold, or choose automatic launch actions.

Independent read-only work may overlap only when effective read-only behavior and responsibility isolation are verified. The canonical mutable workspace has one active managed WriterLease. Parallel writers require Host-verifiable isolated workspaces and clear integration boundaries.

Fresh children use `fork_turns = none` and receive task-needed responsibility context rather than automatic full Main history.

## Contract index

```text
contracts/policy.json
  fixed profiles and product child ceiling

contracts/routing.md
  delegation, profile selection, dispatch and concurrency

contracts/responsibility-packet.md
  child responsibility serialization

contracts/guardrails.md
  authority, mutation, consent and external-action boundaries

contracts/interaction.md
  user control semantics

contracts/recovery.md
  ExecutionBinding recovery and UNKNOWN handling

contracts/state.md
  V4 state schema and Host normalization

contracts/final-review.md
  exact-candidate independent review
```

The canonical runtime owner map is `docs/v4/architecture.json#runtime_owners`. The candidate-bound real Host release campaign is `docs/v4/host-smoke.json`.

V3 orchestration state is legacy evidence. Unresolved live V3 state is never silently migrated into V4 execution.

Doctor owns deterministic installed-product diagnosis and explicit maintenance. Repository publication checks, N0-N8 Host evidence, Final Review, and benchmark/calibration workflows remain outside ordinary Doctor authority.
