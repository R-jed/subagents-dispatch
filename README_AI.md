# subagents-dispatch: AI Agent Reference

Current V4 product surface: `Orchestrate` and `Doctor`.

Before changing V4 repository content, read `docs/v4/current-state.md`, then `docs/v4/development-handoff.md`. The current-state checkpoint is the short status entrypoint for the active release branch and Host gate. The handoff provides detailed chronology and architecture background. Neither document replaces current machine contracts, GitHub state, Issue #91 evidence, or real Host observations.

## Runtime ownership

Codex Host owns child materialization, lifecycle truth, identity, actual capacity, effective permission state, and managed-child collaboration surface.

Main owns user intent, decomposition, explicit fixed-profile selection, dispatch judgment, integration, WorkUnit acceptance, irreversible external side effects, and the final response.

WorkGraph and WorkUnit state own responsibility structure, dependencies, ownership, and acceptance. ExecutionBinding owns one concrete child execution. WriterLease owns managed write responsibility.

A `team_plan_revision` field may remain temporarily as a V4 RC state-schema compatibility marker. It has no independent planning, routing, dependency, execution, or integration authority.

## Canonical machine truth

Keep one machine owner per semantic fact.

`contracts/policy.json` owns fixed profile and product policy values. `docs/v4/architecture.json` owns the complete V4 machine architecture and runtime owner map. `docs/v4/host-smoke.json` owns the candidate-bound N0-N8 real Host release oracle.

`docs/v4/phase-status.json` is process bookkeeping only. It may say that repository remediation or release gates are pending, but it must not be treated as exact-candidate CI evidence. Exact commit, workflow and Host evidence come from current GitHub and Issue #91.

Human documentation should explain or link these owners. Do not create another machine projection simply to restate routing, scheduler, writer, Host-feasibility, or release semantics already owned by the canonical contracts. Tests should target owner data, schemas and observable behavior instead of requiring copied prose to stay synchronized across documents.

## Fixed managed profiles

```text
Reader        gpt-5.6-luna   max    read-only intent
Worker        gpt-5.6-luna   max    bounded source write when granted
Investigator  gpt-5.6-terra  high   read-only intent
Solver        gpt-5.6-sol    high   bounded source write when granted
Advisor       gpt-5.6-sol    high   read-only judgment/review
```

Main selects one fixed profile explicitly for each delegated responsibility. Runtime code validates the selection. There is no automatic Luna, Terra, Sol escalation ladder.

## Orchestration invariants

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

Delegation depth 1 is a project policy. Managed profiles and responsibility packets instruct children not to create or control further Agents. The effective child collaboration surface remains a Host fact, and latent V2 recursive capability does not by itself violate the product contract. N1 judges actual managed executions: any managed child that initiates nested Agent creation/control, or materializes a descendant, fails the gate; ambiguous evidence remains UNKNOWN.

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

The canonical runtime owner map is `docs/v4/architecture.json#runtime_owners`. The candidate-bound real Host release campaign is `docs/v4/host-smoke.json`.

V3 orchestration state is legacy evidence. Unresolved live V3 state is never silently migrated into V4 execution.

Doctor owns deterministic installed-product diagnosis and explicit maintenance. Repository publication checks, N0-N8 Host evidence, Final Review, and benchmark/calibration workflows remain outside ordinary Doctor authority.

## Compatibility owners

```text
scripts/legacy_state_cleanup.py
  ownership-safe cleanup for stale terminal V3 orchestration capsules

scripts/legacy_migration.py
  explicit profile/install migration support

contracts/team-plan.md
  pre-release V4 call-shape compatibility only
```

A compatibility surface must have a current consumer and removal condition. Do not keep a compatibility alias or state field solely because an old test mentions it.

## Change discipline

Preserve proven safety boundaries such as UNKNOWN fail-closed handling, candidate identity, Host observation basis, WriterLease settlement, and materialization ambiguity. Simplification targets duplicate representation and unnecessary compatibility, not line count.

For behavior-preserving refactors, prove consumers before deletion, make one coherent change at a time, run focused tests, then run the full suite before completion. Product behavior changes require their own specification and review rather than being hidden inside cleanup.
