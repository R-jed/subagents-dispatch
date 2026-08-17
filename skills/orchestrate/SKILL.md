---
name: orchestrate
description: Plan, start, resume, inspect, steer, and safely take over V4 orchestration through one explicit control surface while preserving fixed profiles, one-writer safety, Host truth, and acceptance-gated dependencies.
---

# Orchestrate

Use this Skill as the V4 unified orchestration entrypoint. During the coexistence phase the legacy Dispatch, Preview, Status, Steer, and Takeover adapters may still be installed; do not mix control surfaces inside one active orchestration. The final V4 public cutover removes those legacy adapters.

The V4 engineering baseline is `docs/v4/engineering-baseline.json`. The frozen architecture is `docs/v4/architecture.json`. Runtime structure is implemented by `scripts/dispatch_state_v4.py`, `scripts/work_graph_v4.py`, `scripts/scheduler_v4.py`, `scripts/dispatch_control_v4.py`, `scripts/execution_lifecycle_v4.py`, and `scripts/writer_lease_v4.py`.

For plan-only requests, compile the goal, responsibilities, dependencies, ownership ceilings, done conditions, and fixed profile routes without creating `active.json`, acquiring WriterLease, preparing PendingControl, or invoking any Host lifecycle tool.

For execution, bind control to the exact active `orchestration_id`. An unrelated later request must not silently join an unresolved orchestration. Status, steer, takeover, cancellation, and resume operations require the current orchestration target to be unambiguous.

Use only the fixed V4 profile set. Luna Max Reader handles bounded inspection, Luna Max Worker handles bounded implementation, Terra High Investigator handles broad investigation, Sol High Solver handles stalled or high-judgment work within its authority ceiling, and Sol High Advisor handles fresh review. Do not dynamically change model or reasoning effort.

Use the wakeup-driven scheduler one reconciliation at a time. A wakeup is a reason to observe and reconcile; it is not lifecycle truth. `Host COMPLETED` produces `WorkUnit.RESULT_READY`. Dependencies unlock only after Main accepts the producing WorkUnit. Keep initial managed fanout at at most two children, product fanout at at most three, respect Host capacity, prioritize the longer downstream critical path, and stop new fresh starts while two or more results await acceptance.

A writing activation requires the canonical WriterLease before the Host call. Same-child follow-up does not consume a fresh Agent attempt and remains bounded by the recovery policy. Interrupt acknowledgement alone never settles a writer. Takeover requires fresh current-generation Host evidence, no unresolved PendingControl, proven managed lifecycle Guard coverage, and atomic WriterLease transfer to Main.

The V4 lifecycle Hook manifest remains staged until runtime validation. `docs/v4/host-smoke.json` defines the H01-H07 evidence required before V4.0.0 can be declared supported or published. Do not infer that those probes passed from offline tests.

Keep child packets self-contained because `fork_turns` is `none`. Managed children do not create or control sibling project children. Peer messages are outside correctness-critical authority, acceptance, lease transfer, and dependency unlocking.
