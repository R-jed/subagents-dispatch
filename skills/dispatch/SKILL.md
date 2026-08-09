---
name: dispatch
description: Start or resume value-driven orchestration with Codex Native Subagents while preserving user authority, runtime truth, one-writer safety, and evidence-bound completion.
---

# Dispatch

Use this Skill to start a new orchestration when none is active, or to resume the current orchestration when explicitly invoked without a new task. Resume the bound unit/task/attempt/Agent/role/responsibility/authority; do not create a duplicate child, retry, follow-up, work pass, or rework. If active unresolved ownership exists, do not silently create a second unrelated top-level orchestration in the same root thread.

Load the canonical contracts required by the task:

- `../../contracts/policy.json`: hard machine-readable invariants and five route definitions
- `../../contracts/routing.md`: delegation value, role selection, responsibility compilation, and adaptive ready work
- `../../contracts/guardrails.md`: authority, trust, mutation boundaries, and writer coordination
- `../../contracts/state.md`: ephemeral root-thread continuity and Host reconciliation
- `../../contracts/team-plan.md`: multi-responsibility identity, dependencies, ownership, and revisions
- `../../contracts/recovery.md`: attempt lifecycle, bounded recovery, `UNKNOWN`, and `INTERRUPTED`
- `../../contracts/handoff.md`: compact Main-accepted evidence transfer
- `../../contracts/final-review.md`: consequence-driven exact-candidate review
- `../../contracts/receipt.md`: terminal orchestration accounting and presentation

Delegate only when a distinct responsibility adds enough value to justify coordination cost. There is no child minimum or ordinary project-level child maximum; native Host capacity is only a ceiling. Keep delegation depth at one.

Main retains the user's goal, authorization, team composition, integration, acceptance, and final response. Before conflicting writes, preserve semantic `single_writer` coordination for the canonical workspace. Treat configured, accepted, and observed route facts as different evidence levels.

When the orchestration reaches a stable return boundary, produce the Dispatch Receipt defined by `../../contracts/receipt.md`. Do not invent App slash syntax or Host facts.
