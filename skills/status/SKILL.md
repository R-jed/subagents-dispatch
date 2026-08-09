---
name: status
description: Observe and reconcile the current root-thread orchestration once without polling or changing task truth, ownership, responsibility, or native execution.
---

# Status

Use this Skill to inspect the current root-thread orchestration.

Load `../../contracts/interaction.md`, `../../contracts/state.md`, `../../contracts/recovery.md`, and `../../contracts/receipt.md`.

Perform one native observation and one reconciliation pass, then return the low-resolution summary defined by the contracts. Accept an optional exact unit-id zoom. Do not spawn, steer, resume, take over, busy-poll, or change task truth, responsibility, ownership, authority, native execution, or semantic lifecycle. Update only Status-owned ephemeral observation/accounting metadata when the state contract permits it.
