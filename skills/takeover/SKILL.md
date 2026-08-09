---
name: takeover
description: Safely return one delegated responsibility to Main after resolving native ownership and proving any prior writer is non-active.
---

# Takeover

Use this Skill to take a delegated responsibility back into Main.

Load `../../contracts/interaction.md`, `../../contracts/state.md`, `../../contracts/recovery.md`, `../../contracts/guardrails.md`, and `../../contracts/handoff.md`.

Resolve an explicit unit exactly. Without one, auto-resolve only when exactly one unit is eligible; report none or return candidates when zero or multiple units are eligible. Observe the native owner, and settle or stop the old owner when required. Before Main performs conflicting writes, prove the old writer is non-active. `UNKNOWN` and `INTERRUPTED` are not automatically settled. Preserve only Main-accepted useful evidence.
