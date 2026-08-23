# subagents-dispatch: AI Agent Reference

Current V4 product surface: `Orchestrate` and `Doctor`.

Before changing V4 repository content, read `docs/v4/development-handoff.md`. It is the live development-continuity record for the current candidate, remediation history, upstream Codex MultiAgent V2 assumptions, validation state, known risks, and strict next-step ordering. Every repository content change must keep that handoff synchronized. The handoff does not replace machine-readable contracts or external real-Host evidence.

## Runtime ownership

Codex Host owns child materialization, lifecycle truth, identity, actual capacity, effective permission state, and managed-child collaboration surface.

Main owns user intent, decomposition, explicit fixed-profile selection, dispatch judgment, integration, WorkUnit acceptance, irreversible external side effects, and the final response.

WorkGraph and WorkUnit state own responsibility structure, dependencies, ownership, and acceptance. ExecutionBinding owns one concrete child execution. WriterLease owns managed write responsibility.

A `team_plan_revision` field may remain temporarily as a V4 RC state-schema compatibility marker. It is not a separate planning, routing, or integration authority.

## Fixed managed profiles

```text
Reader        gpt-5.6-luna   max    read-only intent
Worker        gpt-5.6-luna   max    bounded source write when granted
Investigator  gpt-5.6-luna   max    read-only investigation
Solver        gpt-5.6-luna   max    bounded source write with granted judgment
Advisor       gpt-5.6-luna   max    read-only judgment/review
```

The semantic profiles remain distinct, but all managed child routes are currently pinned to Luna Max for Host containment. Exact-host N1 evidence on Codex `0.149.0-alpha.4.1` proved that a V2-capable child can materialize a grandchild even with project `max_depth=1`. The qualified Host model metadata reports Luna as V1, which makes `collab_tools_enabled()` false for a spawned V2-session child using Luna.

Main may use other Host models. Managed Terra or Sol child routing is unavailable in this RC until Host-enforced descendant containment exists and passes the same N1 contract. Profile developer instructions against further delegation are defense only. Role-local `[agents] enabled=false` and `[features] multi_agent_v2=false` are not used as containment controls because the current Codex role override layer does not apply those settings.

## Orchestration invariants

```text
managed children <= 4
fork_turns = none
delegation depth = 1
managed child model metadata must remain containment-qualified
Host COMPLETED produces candidate work only
WorkUnit ACCEPTED unlocks dependencies
UNKNOWN blocks conflicting replacement, writer transfer, and final acceptance
interrupt return alone never releases WriterLease
```

Four children is a safety ceiling, not a target. Known Host capacity may reduce available slots. Unknown capacity stays unknown. Deterministic helpers report constraints and status; they do not rank WorkUnits, apply a fixed backlog threshold, or choose automatic launch actions.

Delegation depth 1 is project policy. It does not prove V2 Host containment. Effective child collaboration surface remains a Host fact. A Host/model update that changes the qualified managed model to a V2-capable child surface invalidates the containment basis and requires requalification.

Independent read-only work may overlap only when effective read-only behavior and responsibility isolation are verified. The canonical mutable workspace has one active managed WriterLease. Parallel writers require Host-verifiable isolated workspaces and clear integration boundaries.

Fresh children use `fork_turns = none` and receive task-needed responsibility context rather than automatic full Main history.

## Contract index

```text
contracts/policy.json
  fixed profiles, containment posture and product child ceiling

contracts/routing.md
  delegation, profile selection, dispatch and concurrency

contracts/responsibility-packet.md
  child responsibility serialization

contracts/team-plan.md
  RC compatibility boundary only; no runtime planning authority

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

The canonical runtime owner map is `docs/v4/architecture.json#runtime_owners`. The candidate-bound real Host release campaign is `docs/v4/host-smoke.json`. `docs/v4/host-capability-matrix.json` is pre-release feasibility evidence only and has no release authority.

V3 orchestration state is legacy evidence. Unresolved live V3 state is never silently migrated into V4 execution.

Doctor owns deterministic installed-product diagnosis and explicit maintenance. Repository publication checks, N0-N8 Host evidence, Final Review, and benchmark/calibration workflows remain outside ordinary Doctor authority.

## Compatibility owners

```text
scripts/legacy_state_cleanup.py
  ownership-safe cleanup for stale terminal V3 orchestration capsules

scripts/legacy_migration.py
  ownership-checked V3 profile migration and compatibility diagnosis
```

Compatibility code and the TeamPlan compatibility marker do not define current V4 routing, lifecycle, acceptance, release, or Host authority.
