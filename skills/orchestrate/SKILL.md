---
name: orchestrate
description: Plan, execute, inspect, steer, recover, take over, verify, and review one V4 subagent orchestration with bounded concurrency and single-writer safety.
---

# Orchestrate

Use this Skill as the single V4 orchestration entrypoint. Doctor is the separate diagnostics and maintenance entrypoint.

Load `../../docs/v4/architecture.json` for the frozen V4 contract and use the V4 runtime helpers under `../../scripts/`. Keep Luna Max, Terra High, and Sol High fixed. Do not dynamically change model reasoning effort.

For plan-only requests, compile the proposed WorkUnits and routes without creating state, acquiring WriterLease, preparing PendingControl, or invoking Host lifecycle tools.

Before any managed Host lifecycle action, call the supported-execution readiness gate exposed by `../../scripts/orchestrate_v4.py`. If H01 through H07 real Host smoke evidence is not PASS, fail closed for managed execution and report that plan-only and diagnostics remain available. Offline CI, package integrity, or source inspection cannot satisfy this gate.

Main owns the user goal, TeamPlan, integration, WorkUnit acceptance, lifecycle authority, WriterLease transfers, and final response. Use semantic roles Main, Work, and Review. Physical profiles remain Reader, Worker, Investigator, Solver, and Advisor. Route to the lowest eligible fixed profile that can safely satisfy acceptance.

Use `fork_turns: none`, depth one, and self-contained child packets. A child may not create or control managed siblings. Peer messages are outside the V4.0.0 correctness path.

WorkUnit truth is independent from native Agent lifecycle. Host COMPLETED may advance a WorkUnit only to RESULT_READY. Dependencies unlock only after Main records ACCEPTED. Keep cancellation explicit.

Use wakeup-driven reconciliation. Start with at most two managed children, refill progressively, and keep normal managed child fanout at or below three and the observed Host child capacity. If Host capacity is unknown, use the conservative single-child path. Apply verification backpressure when at least two results are ready but unaccepted.

Canonical workspace mutation uses one managed WriterLease. Main also requires WriterLease before integration writes. Treat RESERVED, HELD, REVOKING, and UNKNOWN as blocking. Never release or transfer a writer from an interrupt acknowledgement alone. Require fresh current-epoch Host evidence, no unresolved lifecycle control, and verified Guard coverage.

Same-child correction remains on the same ExecutionBinding, is bounded, and does not consume a fresh Agent attempt. CONTINUE is a distinct semantic operation and does not consume the correction follow-up budget. Changes to the WorkUnit contract require revision or supersession rather than silent child reuse.

Status must surface the active orchestration identity, working and waiting units, dependency and execution blockers, WriterLease ownership/state, unresolved controls, and acceptance state. Control requests must target the active orchestration identity exactly.

Final review uses a fresh Advisor and the existing exact candidate-artifact binding. Any candidate mutation invalidates the prior review verdict.

V3.x live state is legacy state. Never silently migrate unresolved V3.x state into V4. Use Doctor for migration diagnostics and explicit safe cleanup.
