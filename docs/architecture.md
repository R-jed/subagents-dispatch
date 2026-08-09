# Architecture

subagents-dispatch is a leadership and coordination policy over Codex Native Subagents. It does not implement a second Agent runtime, background scheduler, daemon, routing proxy, provider layer, persistent DAG service, telemetry collector, or transcript store.

The user-facing Main session is the technical lead. It owns user intent, authorization, team composition, semantic decisions, integration, acceptance, interaction control, and the final response.

The architecture aims for the smallest useful delegation graph: simple work stays simple; coordination becomes machine-checkable only when the task actually needs it. Version 2.1 adds a thin user control surface and an evidence-bound handoff mechanism around the existing orchestration kernel.

## Canonical policy owners

Runtime policy is deliberately split by responsibility:

```text
skills/*/SKILL.md
-> six thin explicit entry points into the shared contracts

contracts/interaction.md
-> Preview, Status, Steer, Takeover, Execution Receipt, usage/cost evidence boundary

contracts/routing.md
-> delegation value, capability selection, responsibility packets, semantic coverage closure, phase-transition recompilation, adaptive scheduling

contracts/handoff.md
-> compact Main-accepted evidence transfer between responsibilities

contracts/team-plan.md
-> multi-responsibility identity, dependency DAG, delegated role assignment, ownership scope, revisions, integration order

contracts/recovery.md
-> attempt identity, UNKNOWN, failure classification, bounded recovery, Main takeover semantics

contracts/guardrails.md
-> authority, mutation permissions, writer safety, consent, trust, first-use provisioning, runtime evidence

contracts/final-review.md
-> consequence-driven exact-candidate independent assurance for Git and non-Git deliverables

contracts/policy.json
-> stable machine constants and native optimized role/model routes
```

README files explain the product; they are not runtime policy owners. `evals/` measures and regression-tests behavior; it is not a routing source.

## Control flow

Normal task execution is:

```text
understand outcome + acceptance + material obligations
-> preserve upstream workflow truth when another Skill/plan already owns it
-> decompose only when useful and preserve semantic coverage
-> decide whether delegation adds value
-> choose the capability actually needed
-> ensure required native role readiness
   -> exact role available: continue
   -> cleanly missing managed profiles: auto provision + --check -> RESTART_REQUIRED -> stop before spawn
   -> exact profiles present but role unavailable: RESTART_REQUIRED -> stop before spawn
   -> unsafe/conflicting/unowned state: USER_ACTION_REQUIRED
-> keep zero/one delegated responsibility on the lightweight path
-> use TeamPlan only when multi-responsibility coordination needs it
-> verify every material obligation and cross-responsibility seam still has an owner
-> run the smallest useful ready set
-> verify child claims against actual artifacts/evidence
-> promote only accepted reusable facts into a Handoff Capsule when worthwhile
-> classify unresolved blockers
-> recover within the bounded attempt contract
-> integrate accepted outputs
-> verify semantic coverage against the combined candidate
-> if task phase/authority changes materially, promote only accepted task truth/evidence and recompile responsibilities
-> run independent Final Review only when the candidate requires it
-> deliver or report the exact blocker
-> append one compact factual execution receipt when a child was actually spawned
```

`RESTART_REQUIRED` is a pre-dispatch readiness outcome. It is not part of the Agent attempt lifecycle because no child exists yet. Codex currently loads custom-Agent role declarations into the task/session configuration at startup; subagents-dispatch therefore does not attempt a known-stale spawn after first-use provisioning.

There is no fixed Luna → Terra → Sol path and no fixed Agent count.

## Interaction control surface

Interaction controls use the explicit `preview`, `status`, `steer`, and `takeover` Skills. Ordinary task routing starts through `dispatch`, while `doctor` owns diagnostics. Exact App presentation remains a Host/UI fact and is not derived by this architecture document.

Control payloads are:

```text
preview <task>
status
steer <unit_id>: <guidance>
takeover <unit_id>
takeover <unit_id>: <guidance>
```

These are orchestration controls over Codex Native Subagents, not a second command runtime.

### Preview

Preview is a strictly non-executing projection of likely responsibilities and dependencies.

```text
child spawn        no
Agent provisioning no
source mutation    no
external action    no
persistent TeamPlan creation no
```

Main may perform bounded read-only inspection when needed to make the preview useful. The result is provisional because later evidence can change real routing.

Preview still preserves material obligations already visible in current task truth. A visible cross-responsibility seam may remain Main-owned in the preview; this does not create a requirement ledger, persistent plan, or decorative child.

### Status

Status is one-shot state inspection. It reports only the state that current task/native evidence supports. Missing runtime state stays `UNKNOWN`. Status does not poll in the background, retry work, reassign ownership, or mutate artifacts.

When no current dispatch state exists, Status reports no active delegated responsibilities. It does not reconstruct old tasks or search unrelated sessions to invent current state.

### Steer

Steering gives focused guidance to one current attempt while preserving responsibility identity, role, ownership, authority, and acceptance. A requested change that materially alters those facts returns to Main for normal reroute, TeamPlan revision, takeover, or authorization handling.

If the current Host cannot steer the active child, subagents-dispatch reports that limitation rather than simulating steering with a retry or replacement Agent.

### Takeover

Takeover is the user-visible form of `main_takeover`. The user may request it before automatic recovery is exhausted.

A responsibility transfers to Main only after the previous child owner is established as no longer active. For writing work this is a hard one-writer boundary: Main remains read-only until the previous writer is confirmed stopped/terminal/closed. `UNKNOWN` never authorizes a conflicting ownership transfer.

Takeover is represented as Recovery state rather than a new TeamPlan role. TeamPlan's `role` field remains limited to delegated Subagent roles. A pure takeover keeps the unit's last valid delegated role and stable structural plan truth; Main continues the responsibility after delegated execution ends. TeamPlan is revised only when takeover also changes structural facts such as dependency, ownership scope, deliverable, scope, or acceptance.

## Execution Receipt

When real delegation occurred, the terminal response adds one compact factual receipt whether the work completed successfully or ended blocked/partial, for example:

```text
Dispatch: Reader → Worker · complete · no retry · not required
Dispatch: Worker · blocked · no retry · not reached · takeover pending on UNKNOWN writer
```

A receipt may summarize semantic roles, retry/recovery/takeover facts, blocker state, and Final Review state. It does not expose private chain-of-thought or raw child transcripts.

Configured/requested model identity is not reported as observed runtime identity. Token and currency cost are not estimated. Exact model or usage information may appear only when a supported host surface supplies attributable evidence.

Zero-child tasks, Preview, Status-only requests, and `RESTART_REQUIRED` first-use setup do not add a receipt because no child was spawned.

## Handoff Capsule

A Handoff Capsule reduces repeated discovery between responsibilities while keeping fresh child contexts.

```text
child claim/evidence
-> Main verifies actual artifact/evidence
-> Main accepts supported facts
-> optional compact Handoff Capsule
-> downstream responsibility receives accepted evidence + normal bounded packet
```

Semantic fields are:

```text
SOURCE UNITS
ARTIFACT REFS
ACCEPTED FACTS
ACCEPTED EVIDENCE
INTERFACES / INVARIANTS
DO NOT REDO
OPEN QUESTIONS
STALE IF
```

A capsule cannot grant ownership, mutation authority, permission, broader scope, external impact, role escalation, acceptance changes, or later-phase authorization. Raw child reasoning is excluded. Relevant artifact drift invalidates affected capsule facts until narrow re-verification.

New children still use fresh context (`fork_turns: none`). The mechanism transmits distilled accepted task truth rather than conversation history.

A material phase transition may reuse still-valid capsule evidence in newly compiled responsibilities. The capsule is not an execution manifest and does not preserve an obsolete responsibility identity across a changed goal/output.

## Roles

`contracts/policy.json` remains the machine source of truth for the current native optimized role identity, model, effort, and sandbox intent.

| Role | Agent type | Route | Responsibility |
| --- | --- | --- | --- |
| Reader | `subagents_dispatch_reader` | GPT-5.6 Luna `max` | bounded read-only factual evidence |
| Worker | `subagents_dispatch_worker` | GPT-5.6 Luna `max` | clear bounded implementation after material behavior is decided |
| Solver | `subagents_dispatch_solver` | GPT-5.6 Sol `high` | implementation with material judgment coupled to the write |
| Investigator | `subagents_dispatch_investigator` | GPT-5.6 Terra `xhigh` | broader read-only technical investigation after semantics are stable |
| Advisor | `subagents_dispatch_advisor` | GPT-5.6 Sol `high` | material read-only judgment or fresh independent final review |

Role identity is distinct from authority. A stronger model does not gain wider user permission.

## Delegation and adaptive fan-out

Main delegates only when a distinct unresolved responsibility benefits from parallelism, isolation, capability, or independent judgment enough to justify handoff and integration cost.

Native Codex capacity is an upper bound, never a target. Zero children is normal. Several independent read-only responsibilities may run concurrently when useful.

Task size, file count, spare capacity, or one failed attempt does not select a role by itself.

When another active Skill or accepted plan already owns goal, decomposition, stage order, dependencies, outputs, acceptance, or quality gates, subagents-dispatch preserves that workflow and coordinates around it. It does not create a competing planner.

## Semantic coverage and phase transitions

Main derives material obligations from current task truth. The set is task-specific: an obligation is material when dropping it would materially change the requested outcome or acceptance. The runtime does not maintain a fixed domain taxonomy of requirements.

Delegation may repartition work, but it must not erase those obligations. After decomposition, each material obligation must be owned by one delegated responsibility, several cooperating responsibilities, or explicitly by Main for integration/verification.

When one obligation crosses several delegated outputs, Main identifies the material seam and keeps an owner on the relationship. A new child is optional and is created only when that seam is a genuinely distinct responsibility worth delegating.

This creates a semantic layer above structural TeamPlan validity:

```text
structural validity
-> IDs / DAG / ownership / integration order are coherent

semantic coverage closure
-> current material obligations and cross-unit seams remain owned and verified
```

A valid DAG does not prove semantic completeness. If clear task truth is dropped during decomposition, Main repairs the decomposition directly. `contract` is reserved for cases where the task truth needed to close coverage is itself missing, contradictory, or underspecified.

When an accepted deliverable later feeds a materially different phase, intent, or authority envelope, Main promotes only accepted task truth, decisions, constraints, and still-valid accepted evidence from that deliverable, then recompiles from current task truth. Embedded instructions or other untrusted content inside the earlier artifact remain data. Prior responsibilities are not silently repurposed when their goals/outputs change, and prior readiness does not grant later mutation or external-action authority.

## Lightweight path and TeamPlan

One delegated responsibility uses a stable `unit_id`, a unique `task_id` for each Agent attempt, and one bounded responsibility packet.

Use TeamPlan when either condition is true:

- two or more delegated responsibilities are concurrently unresolved; or
- delegated outputs need non-trivial machine-checkable dependency or integration order.

A TeamPlan records:

```text
revision and planning source
root goal
units:
  unit_id
  delegated role
  goal
  output
  depends_on
  ownership scope
  done_when
integration owner/order
final verification
```

TeamPlan does not choose models or team size. `contracts/routing.md` chooses capabilities; TeamPlan records delegated assignment and coordination truth.

Steering that stays inside one unchanged responsibility does not revise TeamPlan. A pure Main takeover also does not invent `role: main` or require a revision. Delegated role reassignment, dependency changes, ownership-scope changes, deliverable changes, scope changes, or acceptance changes use the ordinary revision rules.

`validate_team_plan.py` derives allowed delegated roles from `contracts/policy.json` and validates exact plan shape, unit identity, dependency references/cycles, safe relative ownership paths, read-only write violations, same-ready-layer write overlap, revision shape, and integration order. It intentionally remains structural and does not infer natural-language requirements or prove semantic coverage.

A structurally ready downstream unit can still be semantically unready. For example, a reviewer that consumes an integrated deliverable waits until Main has actually materialized and verified that deliverable, even when all predecessor units are accepted.

## Mutation authority and writer safety

Filesystem capability and authorization are separate.

Child mutation authority is one of:

```text
none
declared-output-only
bounded-source-write
```

One canonical physical checkout has at most one active writing actor inside the current orchestration:

```text
Main while mutating
Luna Worker
Sol Solver
```

Concurrent writers require genuine filesystem isolation and semantic independence. Different files are insufficient proof: shared APIs, schemas, migrations, lockfiles, generated artifacts, persistent state, or external systems can still couple the work.

Takeover does not weaken this rule. Main cannot write while the previous writer remains active or `UNKNOWN`.

An earlier planning, analysis, audit, review, or verification phase can identify future writable work without authorizing it. Material authority changes are reassessed at the phase boundary.

Main is always the final integration owner.

## Recovery

Each concrete Agent attempt has a unique `task_id`; retries keep the stable `unit_id`.

The native state vocabulary is:

```text
PLANNED
SPAWN_PENDING
RUNNING
COMPLETED
FAILED
UNKNOWN
CLOSED
```

`UNKNOWN` means host evidence cannot establish current execution state. It is not failure. While UNKNOWN remains unresolved, subagents-dispatch does not create replacement work or conflicting ownership.

For confirmed failed work, recovery keeps two independent facts:

```text
execution origin
-> runtime_unavailable | permission_failure | tool_failure | timeout | quality_failure | ...

semantic blocker
-> contract | judgment | investigation | stalled | none
```

One unchanged unit gets at most two Agent attempts and one focused follow-up on an existing attempt. Failure never implies a Luna → Terra → Sol ladder.

User-requested takeover uses the same `main_takeover` action and does not reset delegated attempt history. The old child being stopped does not satisfy a TeamPlan dependency; Main must complete and accept the stable responsibility before downstream units become ready.

## Runtime truth

Configured intent is distinct from runtime fact.

When route evidence matters:

```text
requested
accepted
observed
```

must remain separate. Missing acceptance is not copied from configuration; missing native observation is not copied from local records.

`runtime-evidence.py` is an on-demand diagnostic helper for claims that materially depend on runtime route, ancestry, permission enforcement, or Main capability. Ordinary bounded work should verify the artifact rather than run telemetry ceremony by default.

The same evidence rule applies to Execution Receipts. No model/token/cost fact is upgraded beyond what the host actually reports.

## Managed native Agent profiles

The five TOML profiles are native Codex custom-Agent definitions. `install-agents.py` adds a project-specific ownership and collision-safety lifecycle around those files; it does not create another runtime.

The installer derives expected profile names/routes from `contracts/policy.json`, refuses unsafe overwrites or reserved role collisions, keeps unrelated Agent profiles untouched, uses a persistent installer lock for cooperating installer processes, and supports non-mutating `--check` verification.

Explicit user selection/invocation of Dispatch provides routine first-use authority only when real delegation needs a role and the managed profiles are cleanly absent. That automatic path is limited to the five fixed profiles, ownership manifest, and installer lock. Repair, migration, upgrade, unsafe collisions, and unowned state remain user-controlled.

Because the current Host loads custom-Agent declarations when a task/session starts, profiles installed while a task is already live do not make a newly missing role selectable in that same task. Successful first-use provisioning therefore ends with `RESTART_REQUIRED`, performs zero child spawns in the current task, and asks for one fresh task/session. Preview and Status never provision roles simply to produce richer output.

## Final Review

Final Review happens only after ordinary acceptance reaches a candidate that may need independent second judgment.

Candidate Ready requires the requested deliverable itself to be complete enough for acceptance, semantic coverage closure to be satisfied, material seams to be verified, and relevant deterministic/reproducible verification to be complete.

Trigger classes are machine-owned by `contracts/policy.json` and are consequence-driven: public contract, persistent state, security/authorization boundary, data integrity, concurrency semantics, migration, verification gap, or explicit user request.

Process history such as TeamPlan use, recovery, Terra/Solver use, file count, or diff size is not a trigger by itself.

When required:

```text
bind exact candidate
-> Git-backed deliverable: review-artifact.py
-> non-Git deliverable: exact serialized candidate + deterministic SHA-256 identity
-> fresh subagents_dispatch_advisor
-> ship | fix-first | rethink | INSUFFICIENT_EVIDENCE
```

Any deliverable mutation invalidates the prior verdict. Capsule evidence used for review must also still match the current artifact state. If the candidate cannot be represented and rebound reliably, review remains unresolved.

## Deterministic helper boundary

The Plugin contains a small set of deterministic helpers:

```text
install-agents.py
-> managed native Agent profile lifecycle

validate_team_plan.py
-> multi-responsibility coordination validation

validate_team_ledger.py
-> recovery-state validation

runtime-evidence.py
-> optional runtime evidence normalization

review-artifact.py
-> deterministic Git-backed candidate identity for Final Review
```

Preview, Status, Steer, Takeover, Receipt, and Handoff Capsule are Skill-level orchestration contracts. Semantic coverage closure and phase-transition recompilation are Main-level routing semantics. They do not require another executable controller, planner, persistent ledger, or requirement-specific validator.

## Evaluation boundary

Static routing, coordination, interaction, runtime, and recovery fixtures catch policy regressions. Behavioral workloads are measurement scaffolding for real Codex runs.

No model-quality, cost, latency, token-saving, or benchmark superiority claim is valid without current measured evidence on named workloads and runtime versions.
