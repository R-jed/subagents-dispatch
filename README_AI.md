# subagents-dispatch: AI Agent Reference

This file is an index to current product owners. Historical RC documents do not override the Native Core candidate.

## Project identity

```text
Product name:        subagents-dispatch
Repository:          R-jed/subagents-dispatch
Plugin id:           subagents-dispatch
Current version:     4.0.0
Distribution:        Codex Plugin
License:             MIT
```

The public V4 surface contains exactly two explicit Skills:

| Skill id | Display label | Responsibility |
| --- | --- | --- |
| `orchestrate` | Orchestrate | plan-only, execute, inspect, correct, continue, cancel, take over, review, integrate |
| `doctor` | Doctor | diagnose and explicitly maintain the installed Plugin, managed profiles, Host integration, orchestration state, legacy compatibility |

Do not invent literal App slash-command strings from repository identifiers. Rendered UI labels are Host facts.

## Current contract owners

```text
contracts/policy.json
-> fixed managed profile identities, model/effort, depth and review triggers

contracts/routing.md
-> delegation value, role selection, semantic coverage and fanout policy

contracts/responsibility-packet.md
-> the one serialized five-section child responsibility record

contracts/team-plan.md
-> optional multi-responsibility dependency and integration truth

contracts/guardrails.md
-> authority, mutation, writer, consent, prompt-injection and external-action boundaries

contracts/interaction.md
-> Orchestrate user controls

contracts/recovery.md
-> WorkUnit / ExecutionBinding lifecycle and bounded recovery

contracts/state.md
-> current V4 state schema and Host lifecycle normalization

contracts/final-review.md
-> exact-candidate independent review
```

One independent delegated responsibility may keep `team_plan_revision = null`. TeamPlan is required only when multiple unresolved responsibilities or material dependency/integration order need persistent structural truth.

## Current runtime owners

```text
scripts/orchestrate_v4.py
-> admission, fixed-profile routing and user control facade

scripts/dispatch_state_v4.py
-> bounded session-scoped state

scripts/state_storage.py
-> schema-neutral thread identity, path safety, locking and atomic persistence

scripts/work_graph_v4.py
-> WorkUnit construction, dependency and acceptance truth

scripts/scheduler_v4.py
-> wakeup-driven admission, fanout and backpressure

scripts/execution_lifecycle_v4.py
-> ExecutionBinding allocation, followup, continue, interrupt and Host reconciliation facade

scripts/writer_lease_v4.py
-> canonical managed WriterLease ownership and settlement

scripts/managed_execution_v4.py
-> exact five-section responsibility projection and managed spawn payload

scripts/host_capabilities.py
-> native Host capability normalization

scripts/inspect-collaboration-runtime.py
-> optional allowlisted rollout evidence for recovery/release validation

docs/v4/host-smoke.json
-> candidate-bound N0-N8 real Host release gate
```

Plugin Hook lifecycle authority, PendingControl, Guard receipts, Hook capacity tokens, and a replacement request/receipt control plane are retired from Native Core.

## Compatibility owners

```text
scripts/legacy_state_cleanup.py
-> minimal ownership-safe cleanup for stale terminal V3 orchestration capsules

scripts/legacy_migration.py
-> ownership-checked V3 profile migration and compatibility diagnosis
```

Compatibility code does not define current V4 routing, lifecycle, acceptance, release or Host authority.

## Evaluator-only tooling

Calibration and benchmark helpers under `scripts/calibration_*`, `scripts/validate-experiment-*`, and `scripts/score-behavioral-evals.py` are excluded from the runtime integrity set. They may preserve frozen experiment identifiers for reproducibility, but they do not define production Skill names, lifecycle authority, model routing, or release readiness.

## Fixed profiles

```text
Reader        gpt-5.6-luna   max    behavioral read-only
Worker        gpt-5.6-luna   max    bounded source write when granted
Investigator  gpt-5.6-terra  high   behavioral read-only
Solver        gpt-5.6-sol    high   bounded source write when granted
Advisor       gpt-5.6-sol    high   behavioral read-only review
```

Managed child profiles disable child multi-agent capability. Configured read-only sandbox is intent only until the Host proves the effective sandbox.

## Core invariants

```text
Main owns user intent, authorization, integration and final acceptance
Host COMPLETED creates candidate work only
WorkUnit ACCEPTED unlocks dependencies
initial managed children <= 2
normal managed children <= 3
canonical managed writer <= 1
fork_turns = none
depth = 1
UNKNOWN blocks replacement, conflicting writer transfer and final acceptance
interrupt return alone cannot release WriterLease
current-generation Host settlement is required for writer release/takeover
child self-report is never runtime or acceptance authority
```

Known Host capacity may reduce admission. Unknown Host capacity does not require a project-issued capacity token; the Host owns actual capacity and may reject a spawn before materialization.

## First-use boundary

When an exact managed role is unavailable and Plugin-owned profile files are safely absent, Orchestrate may provision only those managed files and then return `RESTART_REQUIRED`. A fresh task must expose the exact managed `agent_type` before delegated execution continues.

## Doctor and update

`scripts/doctor.py` is the current deterministic Doctor owner. Its JSON contract is `layers` plus `actions`, with five current product layers.

Update check:

```text
<python-3.11+> scripts/check-plugin-update.py --codex-home <active-codex-home>
```

Explicit update:

```text
<python-3.11+> scripts/plugin_update.py --codex-home <active-codex-home>
```

Repository publication checks, N0-N8 Host evidence, Final Review and benchmark/calibration workflows remain outside ordinary Doctor authority.
