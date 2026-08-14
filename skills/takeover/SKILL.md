---
name: takeover
description: Safely return one delegated responsibility to Main after resolving native ownership and proving any prior writer is non-active.
---

# Takeover

Use this Skill to take a delegated responsibility back into Main.

Load `../../contracts/interaction.md`, `../../contracts/state.md`, `../../contracts/recovery.md`, `../../contracts/guardrails.md`, and `../../contracts/handoff.md`.

Resolve an explicit unit exactly. Without one, auto-resolve only when exactly one unit is eligible; report none or return candidates when zero or multiple units are eligible. Observe the native owner, and settle or stop the old owner when required. Before Main performs conflicting writes, prove the old writer is non-active. `UNKNOWN` and `INTERRUPTED` are not automatically settled. Preserve only Main-accepted useful evidence.

Map the semantic takeover contract onto the native control surface actually exposed by the current Host. If a running owner can be closed directly, request that supported close/stop action and reconcile the exact same child. If the available stop control only interrupts the child and the Host reports `INTERRUPTED`, keep Main read-only and do not transfer ownership yet.

When the Host exposes a supported same-child resume/wake mechanism but no direct close that can establish a terminal state, use one bounded settlement-only resume of the exact interrupted child. On current MultiAgent V2 builds this may be an exact-child `followup_task` when that tool is exposed. The settlement instruction must narrow the child to no further mutation and immediate return. Preserve the same unit id, task id, attempt number, native child identity, delegated role, authority, and writer ownership throughout the settlement turn. Do not spawn a replacement, create a retry, reroute, or widen authority.

A settlement-only same-child resume is lifecycle settlement, not a focused correction pass or delegated work pass. It must not increment Agent-attempt, retry, focused-follow-up, semantic-rework, or Dispatch-pass accounting. Main remains read-only while that settlement turn is active. After one bounded native observation/reconciliation, transfer ownership only if the exact expected child is proven non-active by contract-accepted Host evidence such as completed, errored, shutdown, or closed. `RUNNING`, `INTERRUPTED`, `UNKNOWN`, and `notFound` remain insufficient. If the Host cannot safely settle the exact child, keep takeover pending and report the capability limitation instead of simulating success.
