---
name: orchestrate
description: Coordinate complex coding tasks with Codex Native Subagents when delegation adds value, while Main keeps integration and acceptance.
---

# Orchestrate

Use this Skill as the single explicit orchestration entrypoint. `Doctor` is the only other public Skill.

First decide whether delegation helps the requested task. Small, tightly coupled, or already well-understood work may stay entirely in Main. Do not create children merely because capacity exists. When a task is clearly Main-only, keep it there without eagerly loading deeper orchestration contracts or provisioning managed profiles.

For plan-only requests, read `../../contracts/policy.json` and `../../contracts/routing.md`, then return a provisional responsibility/dependency shape without creating orchestration state, provisioning Agent profiles, acquiring WriterLease, or invoking Host lifecycle tools.

When delegation may add value, read `../../contracts/policy.json` and `../../contracts/routing.md` before selecting roles or responsibilities. Do not dynamically change model or reasoning effort. New project children use `fork_turns: none`, delegation depth remains one, initial managed fanout is at most two, and ordinary managed fanout is at most three. A known lower Host capacity may reduce that ceiling; unknown Host capacity does not require a synthetic occupancy token before a bounded spawn attempt.

Before spawning one selected responsibility, read `../../contracts/responsibility-packet.md` and project the canonical responsibility into its compact five-section packet. This packet is prompt serialization of routing truth and creates no additional authority model. If two or more delegated responsibilities remain unresolved concurrently, or dependency/integration order becomes material, also read `../../contracts/team-plan.md` and use its graph as canonical multi-responsibility truth.

The canonical mutable workspace has at most one active managed writing actor. A writing child requires WriterLease before its native Host activation. Because the tested Host does not reliably enforce the requested read-only sandbox for managed read roles, do not run a writable child concurrently with any managed Reader, Investigator, or Advisor. While WriterLease is blocking, do not start another managed child. Final Review starts only after the writer settles. `UNKNOWN` never authorizes a conflicting write, replacement, ownership transfer, or acceptance.

Main always owns the user goal, scope, integration, WorkUnit acceptance, and final response. Host completion proves lifecycle settlement only. Accept results after checking relevant evidence and the actual artifact. Do not duplicate an already-owned responsibility.

For user-visible UI, PDFs, presentations, reports, screenshots, or exported files, keep the deliverable focused on the product or business outcome. Unless the user explicitly requests design notes, methodology, implementation process, or a work log, do not put agent planning, implementation rationale, design narration, debugging chronology, verification mechanics, tool logs, or future-work planning inside the deliverable. Put engineering explanation, verification detail, limitations, and tradeoffs in Main's chat response, code comments, PR/MR text, documentation, or a plan file as appropriate. Product help text and empty-state copy may explain use when that explanation itself serves the product.

Before the first child spawn, require the exact selected managed profile and never substitute a generic Agent type. When a required profile is cleanly absent, use the bounded plugin-owned provisioning path and return `RESTART_REQUIRED` for that task. Current V4 has no authoritative in-task registry observation that can prove a newly written custom-Agent profile became selectable in the already-running task. The fresh task must use the exact managed `agent_type`; if the Host cannot expose or honor that selector, report the Host limitation and stop.

Delegated execution requires the Native Subagent lifecycle capabilities needed by the selected operation. Managed child profiles must expose no child collaboration surface. Missing required native capability stops delegated execution. Do not infer Host-enforced read-only from the profile setting when observed runtime permissions are broader.

Main drives lifecycle reconciliation directly. Before reconciliation-sensitive Host observation, capture the current ExecutionBinding observation basis. Feed the observed native state to the deterministic lifecycle helper only while that basis remains current. Stale observations are discarded. Use `list_agents` for status, recovery, takeover settlement, and ambiguous lifecycle truth. Use the allowlisted collaboration rollout inspector only when exact recovery or release evidence is needed; do not turn it into a mandatory receipt protocol.

Load control contracts only when their state becomes relevant. Read `../../contracts/interaction.md` for status, steer, takeover, cancel, continue, or correction requests. Read `../../contracts/recovery.md` when an attempt is interrupted, blocked, retried, reactivated, or has uncertain lifecycle truth. Read `../../contracts/final-review.md` only when its trigger policy applies.

A V3.x orchestration capsule is legacy evidence. Do not silently enroll it into V4. Older pre-release V4 capsules from incompatible schemas require explicit cleanup/restart. Plan-only remains available because it creates no runtime state.

The deterministic runtime owners are `../../scripts/orchestrate_v4.py`, `../../scripts/dispatch_state_v4.py`, `../../scripts/work_graph_v4.py`, `../../scripts/scheduler_v4.py`, `../../scripts/execution_lifecycle_v4.py`, and `../../scripts/writer_lease_v4.py`. Codex Native Subagents own lifecycle truth. Do not create a second orchestration runtime or persisted lifecycle authorization ledger inside this Skill.
