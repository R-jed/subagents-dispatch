---
name: orchestrate
description: Coordinate complex coding tasks with Codex Native Subagents when delegation adds value, while Main keeps dispatch judgment, integration, and acceptance.
---

# Orchestrate

Use this Skill as the single explicit orchestration entrypoint. `Doctor` is the only other public Skill.

First decide whether delegation helps the requested task. Small, tightly coupled, or already well-understood work may stay entirely in Main. Do not create children merely because capacity exists.

For plan-only requests, read `../../contracts/policy.json` and `../../contracts/routing.md`, then return a provisional WorkUnit and dependency shape without creating orchestration state, provisioning Agent profiles, acquiring WriterLease, or invoking Host lifecycle tools.

When delegation adds value, read `../../contracts/policy.json` and `../../contracts/routing.md`. Main creates one or more WorkUnits and selects one fixed managed profile explicitly for each delegated responsibility. Runtime code validates that selection. Do not dynamically change child model or reasoning effort and do not apply an automatic Luna, Terra, Sol escalation ladder.

New children use `fork_turns: none`. Delegation depth remains one. Managed children cannot create or control further Agents. The product ceiling is four concurrently active managed children. This is a safety ceiling, not a target. Known lower Host capacity may reduce available slots; unknown Host capacity is not guessed and does not require a synthetic occupancy token.

WorkGraph is the responsibility structure truth for one or many WorkUnits. Before spawning a selected responsibility, read `../../contracts/responsibility-packet.md` and serialize only the task-needed goal, constraints, interfaces, accepted evidence, ownership, and acceptance condition. Do not automatically copy the full Main history into a fresh child.

Main owns dispatch judgment. Deterministic helpers may report the ready frontier, active count, Host readiness, known capacity, WriterLease state, and available slots. They do not rank WorkUnits, impose fixed critical-path priority, apply a fixed acceptance-backlog threshold, or choose automatic launch actions.

The canonical mutable workspace has one active managed WriterLease. Independent read-only work may overlap with other work only when effective read-only behavior and responsibility isolation are verified. If that evidence is missing, use the conservative serial path. Multiple writers require Host-verifiable isolated workspaces and clear integration boundaries; file-list separation alone is insufficient.

Main always owns the user goal, scope, integration, WorkUnit acceptance, irreversible external side effects, and final response. Host completion proves candidate lifecycle completion only. Accept results after checking relevant evidence and the actual artifact. Do not duplicate an already-owned responsibility.

Before the first child spawn, require the exact selected managed profile and never substitute a generic Agent type. When a required profile is cleanly absent, use the bounded plugin-owned provisioning path and return `RESTART_REQUIRED` for that task. A fresh task must expose the exact managed `agent_type`; if the Host cannot expose or honor it, report the Host limitation and stop.

Delegated execution requires the Native Subagent lifecycle capabilities needed by the selected operation. Managed child profiles must expose no child collaboration surface. Missing required native capability stops delegated execution. Do not infer Host-enforced read-only solely from profile configuration.

Main drives lifecycle reconciliation. Before a reconciliation-sensitive Host observation, capture the current ExecutionBinding observation basis. Apply native state only while that basis remains current. Stale observations are discarded. `UNKNOWN` never authorizes conflicting replacement, writer transfer, or final acceptance. Elapsed time or wait timeout alone never converts `UNKNOWN` into `FAILED`.

Load control contracts only when relevant. Read `../../contracts/interaction.md` for status, steer, takeover, or cancel intent. Read `../../contracts/recovery.md` for interrupted, blocked, retried, reactivated, or uncertain execution. Continue and focused correction are recovery mechanics inside Orchestrate. Read `../../contracts/final-review.md` only when consequence-based review policy applies.

For user-visible deliverables, keep the artifact focused on the requested product or business outcome. Engineering process, agent planning, verification logs, and implementation narration belong in Main's chat response, code comments, repository documentation, or PR text unless the user explicitly asks for them.

A V3.x orchestration capsule is legacy evidence. Do not silently enroll unresolved V3 state into V4. Plan-only remains available because it creates no runtime state.

The canonical runtime owner map is `../../docs/v4/architecture.json#runtime_owners`. Codex Native Subagents own lifecycle truth. Do not create a second orchestration runtime, heartbeat loop, or persisted lifecycle authorization ledger inside this Skill.
