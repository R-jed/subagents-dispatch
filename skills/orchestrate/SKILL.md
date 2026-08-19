---
name: orchestrate
description: Coordinate complex coding tasks with Codex Native Subagents when delegation adds value, while Main keeps integration and acceptance.
---

# Orchestrate

Use this Skill as the single explicit orchestration entrypoint. `Doctor` is the only other public Skill.

First decide whether delegation helps the requested task. Small, tightly coupled, or already well-understood work may stay entirely in Main. Do not create children merely because capacity exists. When a task is clearly Main-only, keep it there without eagerly loading the deeper orchestration contracts or provisioning managed profiles.

For plan-only requests, read `../../contracts/policy.json` and `../../contracts/routing.md`, then return a provisional responsibility/dependency shape without creating orchestration state, provisioning Agent profiles, acquiring WriterLease, or invoking Host lifecycle tools.

When delegation may add value, read `../../contracts/policy.json` and `../../contracts/routing.md` before selecting roles or responsibilities. Do not dynamically change model or reasoning effort. New project children use `fork_turns: none`, delegation depth remains one, initial managed fanout is at most two, and ordinary managed fanout is at most three plus any lower Host capacity.

Before spawning one selected responsibility, read `../../contracts/responsibility-packet.md` and project the canonical responsibility into its compact five-section packet. This packet is only a prompt serialization of routing truth; it does not create another task state or authority model. If two or more delegated responsibilities remain unresolved concurrently, or dependency/integration order becomes material, then also read `../../contracts/team-plan.md` and use its graph as the canonical multi-responsibility truth.

The canonical mutable workspace has at most one active managed writing actor. A writing child requires the canonical WriterLease before its Host call. `UNKNOWN`, unresolved PendingControl, or ambiguous writer settlement never authorizes a conflicting write or ownership transfer. Separate worktrees or workspaces are outside the current V4 writer domain unless a future contract explicitly proves their isolation.

Main always owns the user goal, scope, integration, WorkUnit acceptance, and final response. Host completion alone does not unlock dependencies. Accept results only after checking relevant evidence and do not duplicate an already-owned responsibility.

Before the first child spawn, require the exact selected managed profile and never substitute a generic Agent type. When a required profile is cleanly absent, use the bounded plugin-owned provisioning path and return `RESTART_REQUIRED` for that task. Current V4 has no authoritative in-task registry observation that can prove a newly written custom-Agent profile became selectable in the already-running task, so it does not probe by attempting a speculative spawn. The fresh task must use the exact managed `agent_type`; if the Host cannot expose or honor that selector, report the Host limitation and stop.

Delegated execution also requires the installed Host/Hook surface to satisfy the lifecycle capabilities needed by the selected operation. A missing or `UNKNOWN` required capability stops delegated execution. Local or staged configuration alone does not prove that the current Host discovered, trusted, or executed the required lifecycle Hook.

Load control contracts only when their state becomes relevant. Read `../../contracts/interaction.md` for status, steer, takeover, cancel, continue, or correction requests. Read `../../contracts/recovery.md` when an attempt is interrupted, blocked, retried, reactivated, or has uncertain lifecycle truth. Read `../../contracts/final-review.md` only when its trigger policy applies. Use those contracts directly rather than reproducing their state machines in this Skill.

A V3.x orchestration capsule is legacy evidence. Do not silently enroll it into V4. Surface legacy blockers through `Doctor`; plan-only remains available because it creates no runtime state.

The deterministic runtime owners are `../../scripts/orchestrate_v4.py`, `../../scripts/dispatch_state_v4.py`, `../../scripts/work_graph_v4.py`, `../../scripts/scheduler_v4.py`, `../../scripts/dispatch_control_v4.py`, `../../scripts/execution_lifecycle_v4.py`, and `../../scripts/writer_lease_v4.py`. Host lifecycle enforcement is owned by the installed Hook/Guard path. Do not create a second orchestration runtime inside this Skill.
