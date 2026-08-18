---
name: orchestrate
description: Plan, execute, inspect, correct, resume, cancel, review, and safely take over V4 orchestration through one explicit control surface while preserving fixed profiles, one-writer safety, Host truth, and acceptance-gated dependencies.
---

# Orchestrate

Use this Skill as the single V4 orchestration entrypoint. `Doctor` is the only other public Skill. Do not route users through retired Dispatch, Preview, Status, Steer, or Takeover adapters.

The V4 engineering baseline is `../../docs/v4/engineering-baseline.json`. The frozen architecture is `../../docs/v4/architecture.json`. Runtime structure is owned by `../../scripts/orchestrate_v4.py`, `../../scripts/dispatch_state_v4.py`, `../../scripts/work_graph_v4.py`, `../../scripts/scheduler_v4.py`, `../../scripts/dispatch_control_v4.py`, `../../scripts/execution_lifecycle_v4.py`, and `../../scripts/writer_lease_v4.py`.

For plan-only requests, compile the goal, responsibilities, dependencies, ownership ceilings, done conditions, and fixed profile routes without creating `active.json`, acquiring WriterLease, preparing PendingControl, or invoking any Host lifecycle tool.

For execution, bind control to the exact active `orchestration_id`. An unrelated later request must not silently join an unresolved orchestration. Status, correction, takeover, cancellation, and continuation operations require the current orchestration target to be unambiguous.

Use only the fixed V4 profile set. Luna Max Reader handles bounded inspection, Luna Max Worker handles bounded implementation, Terra High Investigator handles broad investigation, Sol High Solver handles stalled or high-judgment work within its authority ceiling, and Sol High Advisor handles fresh review. Do not dynamically change model or reasoning effort.

Use the wakeup-driven scheduler one reconciliation at a time. A wakeup is a reason to observe and reconcile; it is not lifecycle truth. `Host COMPLETED` produces `WorkUnit.RESULT_READY`. Dependencies unlock only after Main accepts the producing WorkUnit. Keep initial managed fanout at no more than two children, product fanout at no more than three, respect Host open-thread capacity, prioritize the longer downstream critical path, and stop new fresh starts while two or more results await acceptance. A completed or interrupted child can remain an open Host thread until it is explicitly closed, so do not treat a settled turn as automatically released capacity.

A writing activation requires the canonical WriterLease before the Host call. Same-child correction does not consume a fresh Agent attempt and remains bounded by the recovery policy. `CONTINUE` is a distinct control operation and does not consume the correction-followup budget. Interrupt acknowledgement alone never settles a writer. Takeover requires fresh current-generation Host evidence, a completed authoritative list_agents Hook receipt, no unresolved PendingControl, and atomic WriterLease transfer to Main.

Authoritative Host capacity truth is consumed during lifecycle `PreToolUse` before the lifecycle Host mutation is allowed to cross the tool boundary. A failed or ambiguous lifecycle `PostToolUse` rejects the tool result and preserves fail-closed state; do not treat PostToolUse `continue:false` as a turn-stop primitive. `SubagentStop` remains the stop/veto boundary for managed child continuation.

A V3.x `active.json` is legacy migration evidence and must not be silently enrolled into V4. If legacy state is present, stop V4 execution and surface the condition through Doctor. Plan-only remains available because it creates no runtime state.

The V4 lifecycle Hook manifest remains staged until runtime validation. `../../docs/v4/host-smoke.json` defines the real Host evidence required before V4.0.0 can be declared supported or published. Offline tests cannot satisfy this gate. Until activation is proven, any execution path that requires the staged lifecycle Hooks must fail closed rather than bypass PendingControl or WriterLease.

Keep child packets self-contained because `fork_turns` is `none`. Managed children do not create or control sibling project children. Peer messages are outside correctness-critical authority, acceptance, lease transfer, and dependency unlocking.

Before declaring the requested deliverable complete, apply the exact Final Review contract at `../../contracts/final-review.md`. Determine whether any consequence-based trigger code in `../../contracts/policy.json` applies to the current candidate. When review is required, Main must first establish Candidate Ready with deterministic or reproducible verification, then bind the exact candidate with `../../scripts/review-artifact.py` for Git-backed work or the contract's deterministic SHA-256 boundary for non-Git work. Launch a fresh `subagents_dispatch_advisor` with `fork_turns: none` against that exact candidate. A prior planning or implementation judgment never substitutes for this independent review.

A required review completes only with the current exact artifact identity, a valid `ship` verdict, relevant verification still passing, and Main acceptance still satisfied. Any deliverable mutation after review invalidates the old verdict. Re-run affected checks, bind the new candidate, launch a fresh review, and verify the artifact identity again immediately before completion. `fix-first`, `rethink`, and `INSUFFICIENT_EVIDENCE` remain unresolved completion states.