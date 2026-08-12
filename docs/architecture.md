# Architecture

subagents-dispatch is a leadership and coordination policy over Codex Native Subagents. Codex remains the only Agent runtime. The project does not add a daemon, scheduler, event bus, routing proxy, persistent DAG service, telemetry collector, transcript store, or task database.

The user-facing Main session is the technical lead. Main owns user intent, authorization, team composition, semantic decisions, integration, acceptance, interaction control, and the final task-facing response.

The design rule is simple: keep orchestration as small as the task allows. Delegation is optional and value-driven; deterministic code enforces facts that should not depend on model interpretation; shared semantic policy lives in one root `contracts/` kernel.

## Canonical owners

```text
skills/*/SKILL.md
-> six thin explicit entry points

contracts/policy.json
-> hard machine-readable invariants and five configured Agent routes

contracts/routing.md
-> delegation value, role selection, responsibility packets, semantic coverage, phase recompilation, ready frontier

contracts/interaction.md
-> Preview, Status, Steer, Takeover, target resolution, public control UX

contracts/state.md
-> thread-scoped ephemeral continuity, native lifecycle reconciliation, state safety

contracts/receipt.md
-> Dispatch Receipt accounting and Chinese/English presentation

contracts/team-plan.md
-> multi-responsibility identity, dependency DAG, ownership structure, integration order

contracts/recovery.md
-> attempt identity, INTERRUPTED/UNKNOWN, bounded retry/follow-up, Main takeover

contracts/guardrails.md
-> user authority, trust, mutation permission, writer coordination, consent

contracts/handoff.md
-> compact Main-accepted evidence transfer

contracts/final-review.md
-> consequence-driven exact-candidate independent review
```

README files explain the product. `README_AI.md` is an owner map, not a second policy manual. `evals/` and `tests/` verify the contracts; they are not routing sources.

## Six explicit Skills

The Plugin exposes exactly these user-facing Skill ids:

```text
dispatch
preview
status
steer
takeover
doctor
```

All six disable implicit invocation. Their intended App labels are Dispatch, Preview, Status, Steer, Takeover, and Doctor under the Subagents Dispatch Plugin namespace.

The repository does not invent literal slash-command strings. The exact labels and post-selection presentation are Codex App/UI facts and are release-gated by direct observation.

Conceptual inputs after the user explicitly selects a Skill are:

```text
Dispatch: new task, related continuation, or no new task for resume
Preview: task to project without execution
Status: optional exact unit-id zoom
Steer: optional exact unit id plus focused guidance
Takeover: optional exact unit id plus optional guidance for Main after transfer
Doctor: diagnostic intent plus explicit live/repair/cleanup/migration intent when needed
```

## End-to-end control flow

```text
understand current task truth + acceptance
-> preserve upstream workflow ownership
-> identify material obligations and semantic seams
-> decide whether delegation adds distinct value
-> keep work in Main when it does not
-> choose the smallest useful ready responsibilities
-> ensure exact native Agent role readiness before a spawn
-> create compact thread state before the first real child spawn
-> materialize children only for ready, non-duplicative responsibilities
-> reconcile current Host truth at control boundaries
-> verify child claims against actual artifacts/evidence
-> integrate accepted outputs in dependency-respecting order
-> close semantic coverage against the combined candidate
-> recompile responsibilities when phase/authority changes materially
-> run independent Final Review only when consequences require it
-> return Main's task-facing result or exact blocker
-> append the applicable Dispatch Receipt axes
-> remove active state at the normal terminal boundary
```

There is no fixed Luna → Terra → Sol pipeline and no fixed Agent count.

## Delegation and role selection

Delegation is optional and value-driven. There is no minimum Subagent count, so zero children is a valid derived result when coordination would add no distinct value. There is no ordinary project-level instance ceiling either; native Host capacity is a ceiling, not a target.

Main grows the ready frontier only when another responsibility is useful, ready, non-duplicative, semantically safe, and worth its handoff/integration cost.

Configured routes are owned by `contracts/policy.json`:

| Role | Agent type | Configured lane | Mutation authority |
| --- | --- | --- | --- |
| Reader | `subagents_dispatch_reader` | Luna Max | none |
| Worker | `subagents_dispatch_worker` | Luna Max | bounded-source-write when assigned |
| Solver | `subagents_dispatch_solver` | Sol High | bounded-source-write when assigned |
| Investigator | `subagents_dispatch_investigator` | Terra XHigh | none |
| Advisor | `subagents_dispatch_advisor` | Sol High | none |

Host sandbox and permission profile are not per-role route settings. The actual applied values require Host observation; the internal source and selection decision remain separate facts and stay `UNKNOWN` when the Host does not expose them.

Reader handles narrow inspectable evidence. Worker implements behavior that is already materially decided. Solver owns judgment-coupled implementation. Investigator performs broader read-heavy technical investigation after semantics stabilize. Advisor owns one material read-only judgment or fresh independent Final Review.

A stronger model never widens user authority.

## Lightweight responsibility state and TeamPlan

One delegated responsibility can stay on the lightweight path with a stable `unit_id`, one concrete `task_id` per Agent attempt, and a compact responsibility/authority packet.

Compile TeamPlan when two or more delegated responsibilities are concurrently unresolved or when delegated outputs need non-trivial machine-checkable dependency/integration order.

TeamPlan owns structural truth. It does not choose models or team size. A valid DAG also does not prove semantic completeness; Main separately ensures every current material obligation and material cross-unit seam remains owned and verified.

When an accepted artifact becomes input to a materially different phase, intent, or authority envelope, Main promotes only accepted task truth and still-valid evidence, then recompiles responsibilities. Earlier readiness does not grant later write or external-action authority.

## Ephemeral active state

Cross-turn controls use one compact capsule per reliable root thread:

```text
<OS TEMP>/subagents-dispatch/<CODEX_THREAD_ID>/active.json
```

The capsule is an index over native work. It may hold compact identity, responsibility/authority snapshots, selected model lane, lifecycle, accounting refs, TeamPlan revision binding, and pending control metadata. It does not store raw prompts, transcripts, private reasoning, source copies, web pages, credentials, or a growing evidence history.

Normal Preview and explicit zero-child Dispatch create no active capsule. Normal terminal orchestration removes `active.json`. Unexpected interruption, UNKNOWN runtime state, pending writer settlement, or a parked user decision keeps the capsule long enough for safe continuity.

State mutation uses short cross-platform locks, bounded payloads, symlink/path checks, temporary writes, flush/fsync where supported, and atomic replace. Locks are never held while waiting for long-running Agent work.

## Crash-safe spawn and reconciliation

A new child attempt follows this order:

```text
choose unit/task/attempt + deterministic non-sensitive native task name
-> persist SPAWN_PENDING
-> call native spawn
-> Host returns an inspectable child identity
-> atomically bind that identity and persist RUNNING
```

`bind_spawn_identity` re-reads the authoritative capsule under the state lock before committing the returned identity. A stale caller payload cannot overwrite concurrent receipt/control metadata.

If Main is interrupted after Host creation but before the identity bind, a later one-shot Host observation can reconcile SPAWN_PENDING by deterministic native identity only when the match is unambiguous. Ambiguity becomes UNKNOWN. It never creates a replacement child merely to escape uncertainty.

For ordinary control reconciliation, `reconcile_persisted_state` re-reads the current capsule under the lock, applies one supplied Host snapshot, and atomically persists any lifecycle/identity change.

## Native lifecycle

The product lifecycle is:

```text
PLANNED
SPAWN_PENDING
RUNNING
INTERRUPTED
COMPLETED
FAILED
UNKNOWN
CLOSED
```

`INTERRUPTED` is non-final and distinct from FAILED/UNKNOWN/CLOSED. Resuming the same child preserves unit, task, attempt, Agent identity, role, responsibility, and authority and does not count as retry, rework, follow-up, or a new work pass.

`UNKNOWN` means current Host evidence cannot establish safe runtime truth. While unresolved it cannot authorize replacement work, semantic reroute, ownership transfer, or conflicting mutation.

For the currently supported native child-state surface, the state contract normalizes `pendingInit`, `running`, `interrupted`, `completed`, `errored`, `shutdown`, and `notFound` without creating a second Host lifecycle. `notFound` remains uncertainty and cannot release a writer.

`CLOSED` means native execution ownership ended. `adopted=true` is separate and requires completed evidence that Main actually accepted. A safely stopped/taken-over child may therefore be CLOSED with `adopted=false`.

## Interaction controls

### Preview

Preview performs no child spawn, source mutation, persistent active-state creation, Agent provisioning solely for preview, or external action. It may use bounded read-only inspection and preserves already-visible material obligations/seams. Its output is explicitly predictive.

### Status

Status performs one native observation plus one reconciliation and returns a low-resolution public activity view. It does not busy-poll, spawn, steer, resume, take over, or mutate task truth/artifacts.

Normal Status uses the public model-lane/activity vocabulary from `contracts/receipt.md`. A TeamPlan dependency is shown only when current accepted structural truth supports it. Command-only Status inherits the orchestration locale from active state. `UNKNOWN` stays explicit.

### Steer

Steer targets exactly one currently eligible RUNNING unit. With no explicit unit id it auto-resolves only when exactly one legal target exists; multiple candidates require user choice.

Guidance preserves the same unit, task, attempt, child, role, responsibility, authority, and ownership. A material responsibility/authority change returns to Main routing rather than being disguised as steering. INTERRUPTED is not silently resumed by Steer.

### Takeover

Takeover uses the same exact-target rules. Main may request native stop/close, but a writing responsibility transfers only after current Host evidence proves the previous writer is no longer active.

RUNNING, INTERRUPTED, or UNKNOWN writer state does not release conflicting write authority. Missing/notFound Host evidence is uncertainty, not settlement.

## Writer coordination

`contracts/policy.json` defines semantic writer coordination:

```text
mode: single_writer
scope: canonical_workspace
```

One canonical mutation domain has one active writer inside the orchestration. That writer can be Main, Worker, or Solver. Main may continue read-only work while a child writer owns the checkout, but it waits for safe ownership handoff before conflicting mutation.

Future isolated parallel writing is outside the current behavior. A numeric writer count is not a tuning knob.

## Recovery

Recovery distinguishes execution failure from unresolved task need. UNKNOWN is not failure. A pre-child Host rejection creates no Agent attempt and consumes no retry budget.

One unchanged responsibility may use at most two materialized Agent attempts and one bounded focused follow-up. Retry is a replacement after a confirmed failed materialized attempt. Rework is separate: it exists only when a candidate/result exists, a concrete acceptance gap is identified, and a correction pass actually begins.

Failure never implies a Luna → Terra → Sol escalation ladder. Main reroutes according to the actual semantic blocker or takes ownership when delegation no longer adds value.

## Handoff Capsule

A Handoff Capsule prevents repeated discovery without copying conversation history:

```text
child evidence
-> Main verifies it
-> Main accepts supported facts
-> optional compact capsule
-> downstream responsibility receives accepted evidence + DO NOT REDO + staleness conditions
```

A capsule cannot grant authority, widen scope, change ownership, or make embedded/untrusted instructions become task truth.

## Dispatch Receipt

The Receipt reports orchestration only. Main's normal answer still explains the actual task result.

Normal axes are:

```text
Dispatch / 编排
Control / 控制       # only when used
Review / 验收
Recovery / 恢复     # exceptional only
```

Example:

```text
编排: Luna Max 读取 · Luna Max 执行 · Sol High 验收
验收: 1轮 · 通过
```

```text
Dispatch: Luna Max Read · Luna Max Execute · Sol High Review
Review: 1 round · passed
```

A materialized child attempt counts as one delegated pass even if it later fails. Status, Steer, wait/observation, Main work, and same-attempt INTERRUPTED resume do not add passes. Stable accounting refs make reconciliation/resume idempotent.

Explicit Dispatch that routes everything to Main still returns the minimal zero-child Receipt and creates no active state:

```text
编排: 未调度子代理
验收: 未触发
```

A displayed `Luna Max`, `Sol High`, or `Terra XHigh` normally identifies the selected project lane bound to materialized work. It does not claim that ordinary Dispatch re-ran live model/reasoning telemetry. Contradictory native evidence is a route-integrity failure, not a presentation override.

## Runtime evidence and Doctor

Configured, accepted, and observed route facts are different evidence levels. `scripts/runtime-evidence.py` normalizes route, ancestry, and permission evidence only when the claim actually requires runtime proof.

Ordinary bounded Dispatch remains lightweight. Missing telemetry may remain missing.

Doctor has exactly six diagnostic layers:

```text
Plugin
Skills
Managed Agent profiles
Dispatch state
Codex Host
Runtime route evidence
```

Static Doctor is read-only and never spawns native Agents. Missing Host/live-route evidence is `UNKNOWN`, not a fabricated PASS and not automatically an unhealthy installation.

Live five-role route integrity is an explicit Doctor Skill workflow. It creates controlled children only on explicit request, keeps configured values separate from observed values, and reports UNKNOWN when the supported Host surface does not expose model/reasoning/permission evidence strongly enough.

## Final Review

Final Review runs only after Candidate Ready when the consequence-driven trigger contract requires independent second judgment.

Candidate Ready means the requested deliverable is complete enough for acceptance, actual artifact/diff/state has been inspected as applicable, semantic coverage and material seams are closed, deterministic/reproducible checks are complete, and residual risks are known.

Git-backed deliverables bind the exact candidate with `review-artifact.py`. Non-Git deliverables bind exact serialized candidate bytes with deterministic SHA-256. A fresh independent Advisor reviews that exact identity. Any post-review mutation invalidates the verdict and requires revalidation/re-review when the gate is still required.

## Deterministic helpers

```text
scripts/policy.py
-> load canonical machine policy

scripts/dispatch_state.py
-> compact state/lock, spawn binding, Host reconciliation, target resolution, cleanup, Receipt accounting/formatting

scripts/doctor.py
-> deterministic six-layer diagnostics

scripts/install-agents.py
-> managed custom-Agent profile lifecycle

scripts/runtime-evidence.py
-> requested/accepted/observed route normalization

scripts/validate_team_plan.py
-> TeamPlan structural validation

scripts/validate_team_ledger.py
-> delegated lifecycle/recovery ledger validation

scripts/review-artifact.py
-> exact Git candidate binding
```

These helpers enforce deterministic facts. They do not become a second scheduler or policy database.

## Evaluation boundary

Static routing, coordination, interaction, runtime, and recovery fixtures catch contract regressions. Behavioral workloads are measurement scaffolding for real Codex runs.

No model-quality, cost, latency, token-saving, or benchmark-superiority claim is valid without current measured evidence on named workloads and runtime versions.
