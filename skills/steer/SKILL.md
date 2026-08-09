---
name: steer
description: Give focused guidance to one existing delegated attempt without changing its responsibility, role, authority, ownership, or native identity.
---

# Steer

Use this Skill to guide an existing delegated unit.

Load `../../contracts/interaction.md`, `../../contracts/state.md`, `../../contracts/recovery.md`, and `../../contracts/guardrails.md`.

Resolve an explicit unit exactly. Without one, auto-resolve only when exactly one unit is eligible; report none or return candidates when zero or multiple units are eligible. Keep the same unit, attempt, native child, semantic responsibility, role, authority, and ownership. `INTERRUPTED` is not Resume and is not eligible Steering. If guidance materially changes responsibility or authority, stop and return it to Main for routing/recompilation; do not silently transform the active attempt.
