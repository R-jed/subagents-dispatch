# subagents-dispatch: AI Agent Reference

Use this file when answering questions about this repository. It is an index to the current project, not a second copy of runtime policy.

## Project identity

```text
Product name:        subagents-dispatch
Repository:          R-jed/subagents-dispatch
Repo marketplace id: subagents-dispatch
Plugin id:           subagents-dispatch
Plugin directory:    .
Main Skill:          dispatch
User command:        /dispatch
Internal identity:   /subagents-dispatch:dispatch
Doctor Skill:        doctor
Doctor command:      /doctor
Internal identity:   /subagents-dispatch:doctor
Current version:     2.1.1
Distribution:        Codex Plugin
License:             MIT
```

Use these names exactly.

## Product model

The current Codex main session is the team leader. The user supplies the goal. Main decides what to keep, what is worth delegating, which specialist role fits, how delegated work is coordinated, and when the final result is ready.

Zero child Agents is normal. Several may run when distinct ready responsibilities genuinely benefit from parallelism or specialization. There is no fixed Luna → Terra → Sol pipeline and no project-level ordinary numeric child ceiling. Native Codex capacity is an upper bound, never a target to fill.

Version 2.1 adds explicit preview and live-control intents plus evidence-bound handoffs around the same orchestration kernel. Read `skills/dispatch/references/interaction.md` and `skills/dispatch/references/handoff-capsule.md` for the exact contract instead of reconstructing those rules here.

`doctor` is operational maintenance. It diagnoses installation/configuration/Marketplace/profile state and may repair or upgrade only when the user explicitly asks. It does not own development routing or runtime delegation policy.

## Current roles

The machine source of truth is `policy-contract.json`.

| Role | Agent type | Model | Intent |
| --- | --- | --- | --- |
| Luna Reader | `subagents_dispatch_reader` | GPT-5.6 Luna `max` | bounded read-only evidence |
| Luna Worker | `subagents_dispatch_worker` | GPT-5.6 Luna `max` | clear bounded implementation whose material behavior is already decided |
| Sol Solver | `subagents_dispatch_solver` | GPT-5.6 Sol `high` | implementation with material judgment coupled to the write |
| Terra Investigator | `subagents_dispatch_investigator` | GPT-5.6 Terra `xhigh` | broader read-only technical investigation after semantics are stable |
| Sol Advisor | `subagents_dispatch_advisor` | GPT-5.6 Sol `high` | material read-only judgment or fresh independent final review |

A stronger model does not automatically receive more authority or a wider scope.

## Runtime policy owners

Do not reconstruct runtime policy from README prose. Read the canonical owner for the question:

```text
skills/dispatch/SKILL.md
-> execution entry point, bootstrap command recognition, control loop, and pre-dispatch readiness outcome

skills/dispatch/references/interaction.md
-> preview, status, steering, user-requested takeover, execution receipt, usage/cost evidence boundary

skills/dispatch/references/router-core.md
-> delegation value, role choice, responsibility packets, adaptive scheduling

skills/dispatch/references/handoff-capsule.md
-> compact Main-accepted evidence transfer between responsibilities

skills/dispatch/references/team-plan.md
-> multi-responsibility identity, dependency DAG, ownership, revisions, integration order

skills/dispatch/references/recovery.md
-> attempt identity, UNKNOWN, failure classification, bounded recovery and Main takeover semantics

skills/dispatch/references/guardrails.md
-> authority, mutation permissions, one-writer safety, consent, trust boundaries, first-use provisioning, runtime evidence

skills/dispatch/references/final-review.md
-> consequence-driven, artifact-bound independent review

policy-contract.json
-> stable machine constants, native optimized role routes, hard delegation limits, Final Review reason codes
```

Operational ownership is separate:

```text
docs/plugin-installation.md
-> install, deterministic first delegated run, update, and uninstall instructions

skills/doctor/SKILL.md
-> host/plugin/Marketplace/profile diagnosis and supported repair or upgrade flow

scripts/install-agents.py
-> deterministic managed-profile install/check lifecycle

scripts/policy.py
-> shared top-level policy-contract JSON loading only; consumer-specific semantic validation stays with each consumer
```

`evals/` is a regression and measurement surface. It does not define runtime policy.

## Stable boundaries worth remembering

Keep only these orientation-level facts here; use the owners above for exact semantics:

- Main owns user intent, authorization, team composition, integration, acceptance, and the final response.
- Delegation depth is one, and delegation must add concrete value.
- One canonical checkout has at most one active writing actor inside one subagents-dispatch orchestration.
- Child reports remain claims until Main accepts supporting artifact evidence.
- Missing runtime evidence stays missing; `UNKNOWN` is not silently converted into failure or replacement work.
- Final Review is consequence-driven and bound to the exact candidate reviewed.
- Interaction controls operate through Main and Codex Native Subagents. They do not add another scheduler, daemon, event bus, or lifecycle service.
- Explicit `/dispatch` authorizes routine first-use provisioning only for subagents-dispatch's fixed managed profiles, ownership manifest, and installer lock when real delegation needs them. Unsafe, conflicting, or unowned state still fails closed.
- Profiles provisioned during the current live task are treated as unavailable to that task's already-loaded Agent registry. Successful first-use provisioning ends pre-dispatch readiness as `RESTART_REQUIRED`; no child is spawned until a fresh Codex task/session reruns the request.
- `RESTART_REQUIRED` is a pre-dispatch readiness outcome, not a Recovery/Agent lifecycle state.
- Doctor diagnosis is read-only by default; repair, upgrade, migration, and broader mutations require explicit mutation intent.

## Where to answer common questions

For interaction controls, receipts, or token/cost evidence boundaries, read `skills/dispatch/references/interaction.md`.

For role choice and whether delegation is worthwhile, read `skills/dispatch/references/router-core.md` plus `policy-contract.json`.

For Handoff Capsules, read `skills/dispatch/references/handoff-capsule.md`.

For `UNKNOWN`, retries, replacement attempts, or Main takeover, read `skills/dispatch/references/recovery.md` and `skills/dispatch/references/guardrails.md`.

For install, update, first-run provisioning, `RESTART_REQUIRED`, or uninstall commands, read `docs/plugin-installation.md`. For guided diagnosis or repair, read `skills/doctor/SKILL.md`.

For managed profile filenames, models, efforts, and sandbox intents, use `policy-contract.json`; inspect `scripts/install-agents.py` when lifecycle behavior matters.

Do not claim benchmark wins, token savings, speedups, quality gains, exact runtime routes, token/cost attribution, or public directory availability unless current evidence supports the claim.

For deeper technical questions, follow the owner map above rather than treating this README as normative policy.
