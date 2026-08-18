---
name: orchestrate
description: Coordinate complex coding tasks with Codex Native Subagents when delegation adds value, while Main keeps integration and acceptance.
---

# Orchestrate

Use this Skill as the single explicit orchestration entrypoint. `Doctor` is the only other public Skill.

First decide whether delegation helps the requested task. Small, tightly coupled, or already well-understood work may stay entirely in Main. Do not create children merely because capacity exists.

For plan-only requests, return a provisional responsibility/dependency shape without creating orchestration state, provisioning Agent profiles, acquiring WriterLease, or invoking Host lifecycle tools.

For delegated execution, use the fixed profiles and routing rules owned by `../../contracts/policy.json` and `../../contracts/routing.md`. Do not dynamically change model or reasoning effort. New project children use `fork_turns: none`, delegation depth remains one, initial managed fanout is at most two, and ordinary managed fanout is at most three plus any lower Host capacity.

The canonical mutable workspace has at most one active managed writing actor. A writing child requires the canonical WriterLease before its Host call. `UNKNOWN`, unresolved PendingControl, or ambiguous writer settlement never authorizes a conflicting write or ownership transfer. Separate worktrees or workspaces are outside the current V4 writer domain unless a future contract explicitly proves their isolation.

Main always owns the user goal, scope, integration, WorkUnit acceptance, and final response. Host completion alone does not unlock dependencies. Accept results only after checking relevant evidence and do not duplicate an already-owned responsibility.

Before the first child spawn, verify that the exact selected managed profile is available to the current Host task. When a required profile is cleanly absent, use the bounded plugin-owned provisioning path. If the current Host cannot expose or select the exact installed profile, report the readiness or Host limitation and stop. Do not silently substitute a generic Agent type. A fresh Codex task may be required when newly provisioned profiles are not visible to the current task.

Plan, status, steer, takeover, cancel, continue, correction, execution, review, and integration semantics are owned by `../../contracts/interaction.md`, `../../contracts/recovery.md`, `../../contracts/team-plan.md`, and `../../contracts/final-review.md`. Use those contracts rather than reproducing their state machines in the Skill prompt.

A V3.x orchestration capsule is legacy evidence. Do not silently enroll it into V4. Surface legacy blockers through `Doctor`; plan-only remains available because it creates no runtime state.

The deterministic runtime owners are `../../scripts/orchestrate_v4.py`, `../../scripts/dispatch_state_v4.py`, `../../scripts/work_graph_v4.py`, `../../scripts/scheduler_v4.py`, `../../scripts/dispatch_control_v4.py`, `../../scripts/execution_lifecycle_v4.py`, and `../../scripts/writer_lease_v4.py`. Host lifecycle enforcement is owned by the installed Hook/Guard path. Do not create a second orchestration runtime inside this Skill.