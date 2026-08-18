# subagents-dispatch: AI Agent Reference

This file is an index to canonical project owners, not a second copy of runtime policy.

## Project identity

```text
Product name:        subagents-dispatch
Repository:          R-jed/subagents-dispatch
Repo marketplace id: subagents-dispatch
Plugin id:           subagents-dispatch
Plugin directory:    .
Current version:     4.0.0
Distribution:        Codex Plugin
License:             MIT
```

The V4 public surface contains exactly two explicit Skills:

| Skill id | Display label | Responsibility |
| --- | --- | --- |
| `orchestrate` | Orchestrate | plan-only, execute, inspect, correct, continue, cancel, take over, review, and integrate |
| `doctor` | Doctor | diagnose package, fixed profiles, V4 state, Host capabilities, Hook evidence, and release readiness |

Do not invent a Codex App slash-command string from repository identifiers. Exact App labels and presentation are Host/UI facts requiring direct observation.

## V4 runtime owners

```text
scripts/orchestrate_v4.py
-> explicit Orchestrate admission, fixed profile routing, plan-only, status surface

scripts/dispatch_state_v4.py
-> bounded thread-scoped state v4 and stale-observation protection

scripts/work_graph_v4.py
-> WorkUnit graph, acceptance-gated dependency readiness

scripts/scheduler_v4.py
-> wakeup-driven reconcile decision, fanout, critical path, backpressure

scripts/dispatch_control_v4.py
-> PendingControl prepare/consume/ack/quarantine

scripts/execution_lifecycle_v4.py
-> ExecutionBinding lifecycle, followup, continue, interrupt and takeover coordination

scripts/writer_lease_v4.py
-> canonical managed WriterLease protocol

scripts/host_capabilities.py
-> semantic Host capability normalization

scripts/orchestration_guard.py
-> staged V4 lifecycle Guard implementation

docs/v4/host-smoke.json
-> H00-H20 real Host release gate
```

## Fixed profiles

```text
Reader        gpt-5.6-luna   max   read-only
Worker        gpt-5.6-luna   max   bounded write
Investigator  gpt-5.6-terra  high  read-only
Solver        gpt-5.6-sol    high  bounded write
Advisor       gpt-5.6-sol    high  read-only review
```

Dynamic reasoning-effort routing is outside V4.0.0.

## Compatibility owners

```text
contracts/policy.json
-> fixed route identities, delegation depth and single-writer policy

scripts/dispatch_state.py
-> hardened V3.x state/storage compatibility boundary used for legacy detection and shared filesystem primitives

scripts/legacy_migration.py
-> managed-profile legacy ownership detection

contracts/final-review.md
-> exact-candidate independent review identity retained from V3.x
```

A V3.x orchestration capsule is legacy evidence. Never silently rewrite it into V4. An unresolved legacy writer, pending takeover, corrupt state, WriterLease.UNKNOWN, or unresolved PendingControl remains fail closed.

## Safety invariants

```text
Main owns user intent, integration and WorkUnit acceptance
Host COMPLETED does not unlock dependencies
WorkUnit ACCEPTED unlocks dependencies
initial managed children <= 2
normal managed children <= 3 and Host-capacity bounded
canonical managed writer <= 1
fork_turns = none
depth = 1
interrupt ACK alone cannot release WriterLease
stale execution/control/lease observations are discarded
```

The production `hooks/hooks.json` remains the hardened V3.x spawn boundary until H00-H20 pass against the exact promoted candidate. `docs/v4/hooks.json` is staged configuration only. Offline CI cannot promote `docs/v4/host-smoke.json` to PASS.

Each `skills/<id>/SKILL.md` is a thin explicit adapter. `policy.allow_implicit_invocation` is false for both public Skills.

For installation and lifecycle instructions, use `docs/plugin-installation.md`. For runtime helpers, use the named scripts above and `scripts/policy.py`. Keep Experiment Plane material under `evals/` and experiment documentation separate from production routing truth.
