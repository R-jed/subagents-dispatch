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
| `doctor` | Doctor | diagnose and explicitly maintain the installed Plugin, managed profiles, Host integration, orchestration state, and legacy compatibility |

Do not invent a Codex App slash-command string from repository identifiers. Exact App labels and presentation are Host/UI facts requiring direct observation.

## Active V4 contract owners

```text
contracts/policy.json
-> fixed managed profile identities, delegation invariants and review triggers

contracts/routing.md
-> delegation value, capability selection, responsibility semantics and semantic coverage

contracts/responsibility-packet.md
-> the one serialized five-section responsibility record

contracts/team-plan.md
-> multi-responsibility dependency and integration truth

contracts/interaction.md
-> Orchestrate user-control semantics

contracts/recovery.md
-> WorkUnit / ExecutionBinding lifecycle and bounded recovery

contracts/final-review.md
-> exact-candidate independent review
```

One dependency-free delegated responsibility may keep `team_plan_revision = null`. TeamPlan becomes structural truth only when multiple unresolved delegated responsibilities or material dependency/integration order require it. Do not invent another responsibility packet, task state, or scheduler for the compact path.

## V4 runtime owners

```text
scripts/orchestrate_v4.py
-> explicit Orchestrate admission, policy-backed fixed profile routing, plan-only, status surface

scripts/dispatch_state_v4.py
-> bounded session-scoped state v4 and stale-observation protection

scripts/work_graph_v4.py
-> WorkUnit installation, dependency and acceptance truth

scripts/scheduler_v4.py
-> sole wakeup-driven admission, Host capacity, fanout, critical path and backpressure owner

scripts/dispatch_control_v4.py
-> PendingControl prepare/consume/ack/quarantine

scripts/execution_lifecycle_v4.py
-> ExecutionBinding lifecycle, followup, continue, interrupt and takeover coordination

scripts/writer_lease_v4.py
-> canonical managed WriterLease protocol

scripts/host_evidence_v4.py
-> paired current Host lifecycle and capacity evidence

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

`contracts/policy.json` is the machine source of truth. `scripts/policy.py` provides the validated runtime projection. Dynamic reasoning-effort routing is outside V4.0.0.

## Compatibility owners

```text
scripts/dispatch_state.py
-> hardened V3.x storage compatibility boundary still reused for legacy detection and shared filesystem primitives

scripts/legacy_migration.py
-> proven-owned legacy profile/state migration and cleanup support

scripts/spawn_guard.py
-> current production compatibility spawn boundary until lifecycle Hook cutover
```

A V3.x orchestration capsule is legacy evidence. Never silently rewrite it into V4. An unresolved legacy writer, pending takeover, corrupt legacy state, WriterLease.UNKNOWN, or unresolved PendingControl remains fail closed.

## Safety invariants

```text
main session owns user intent, integration and WorkUnit acceptance
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

The production `hooks/hooks.json` remains the hardened V3.x compatibility boundary until H00-H20 pass against the exact promoted candidate. `docs/v4/hooks.json` is staged configuration only. Offline CI cannot promote `docs/v4/host-smoke.json` to PASS.

Each `skills/<id>/SKILL.md` is a thin explicit adapter. `policy.allow_implicit_invocation` is false for both public Skills.

For installation and lifecycle instructions, use `docs/plugin-installation.md`. For runtime helpers, use the named scripts above and `scripts/policy.py`. Maintainer calibration, experiment validation/scoring and release evidence remain outside the ordinary product integrity path even when the repository retains those tools for development and publication workflows.
