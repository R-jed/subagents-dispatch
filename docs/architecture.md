# Architecture

subagents-dispatch is a leadership and coordination policy over Codex Native Subagents. It does not implement a second Agent runtime, background scheduler, daemon, routing proxy, provider layer, persistent DAG service, telemetry collector, or transcript store.

The user-facing Main session is the technical lead. It owns user intent, authorization, team composition, semantic decisions, integration, acceptance, interaction control, and the final response.

## Canonical policy owners

```text
SKILL.md
-> execution control loop, Skill entry point, and pre-dispatch role readiness

interaction.md
-> Preview, Status, Steer, Takeover, Execution Receipt, usage/cost evidence boundary

router-core.md
-> delegation value, capability selection, responsibility packets, adaptive scheduling

handoff-capsule.md
-> compact Main-accepted evidence transfer between responsibilities

team-plan.md
-> multi-responsibility identity, dependency DAG, delegated role assignment, ownership scope, revisions, integration order

recovery.md
-> attempt identity, UNKNOWN, failure classification, bounded recovery, Main takeover semantics

guardrails.md
-> authority, mutation permissions, writer safety, consent, trust, first-use provisioning, runtime evidence

final-review.md
-> consequence-driven artifact-bound independent assurance

policy-contract.json
-> stable machine constants and native optimized role/model routes
```

README files explain the product; they are not runtime policy owners. `evals/` measures and regression-tests behavior; it is not a routing source.

## Entry point

The Plugin packages Skills. Explicit user invocation is:

```text
$dispatch <task>
$doctor <diagnostic or maintenance request>
```

Users may also open `/skills` and choose **Dispatch** or **Doctor**. Bare `/dispatch`, `/doctor`, and legacy namespaced slash identities are not part of the Plugin contract.

## Control flow

Normal Dispatch execution is:

```text
understand outcome + acceptance
-> preserve upstream workflow truth when another Skill/plan already owns it
-> decide whether delegation adds value
-> choose the capability actually needed
-> ensure required native role readiness
   -> exact role available: continue
   -> cleanly missing managed profiles: auto provision + --check -> RESTART_REQUIRED -> stop before spawn
   -> exact profiles present but role unavailable: RESTART_REQUIRED -> stop before spawn
   -> unsafe/conflicting/unowned state: USER_ACTION_REQUIRED
-> keep zero/one delegated responsibility on the lightweight path
-> use TeamPlan only when multi-responsibility coordination needs it
-> run the smallest useful ready set
-> verify child claims against actual artifacts/evidence
-> promote only accepted reusable facts into a Handoff Capsule when worthwhile
-> classify unresolved blockers
-> recover within the bounded attempt contract
-> integrate accepted outputs
-> verify the combined candidate
-> run independent Final Review only when the candidate requires it
-> deliver or report the exact blocker
-> append one compact factual execution receipt when a child actually spawned
```

`RESTART_REQUIRED` is a pre-dispatch readiness outcome. It is not part of the Agent attempt lifecycle because no child exists yet.

## Interaction control surface

Controls are parsed inside the explicitly selected Dispatch Skill:

```text
$dispatch preview <task>
$dispatch status
$dispatch steer <unit_id>: <guidance>
$dispatch takeover <unit_id>
$dispatch takeover <unit_id>: <guidance>
```

Preview is non-executing. Status is a one-shot observation and preserves `UNKNOWN`. Steer keeps responsibility identity, role, ownership, authority, and acceptance. Takeover transfers responsibility only after the prior owner is established as no longer active.

For a writing child, Main remains read-only until the previous writer is confirmed stopped/terminal/closed. `UNKNOWN` never authorizes a conflicting ownership transfer.

Takeover is represented as Recovery state rather than a new TeamPlan role. A pure Main takeover also does not invent `role: main` or require a revision. TeamPlan is revised only when structural truth changes.

## Execution Receipt

When real delegation occurred, the terminal response adds one compact factual receipt, for example:

```text
Dispatch: Reader → Worker · complete · no retry · not required
Dispatch: Worker · blocked · no retry · not reached · takeover pending on UNKNOWN writer
```

A receipt may summarize semantic roles, retry/recovery/takeover facts, blocker state, and Final Review state. It does not expose private chain-of-thought or raw child transcripts. Configured/requested model identity is not reported as observed runtime identity, and token/currency cost is not estimated.

Zero-child tasks, Preview, Status-only requests, and `RESTART_REQUIRED` first-use setup do not add a receipt because no child was spawned.

## Handoff Capsule

A Handoff Capsule transfers only Main-verified facts and evidence to a later fresh child:

```text
child claim/evidence
-> Main verifies actual artifact/evidence
-> Main accepts supported facts
-> optional compact Handoff Capsule
-> downstream responsibility receives accepted evidence + normal bounded packet
```

It may carry `ACCEPTED FACTS`, `ACCEPTED EVIDENCE`, `DO NOT REDO`, `OPEN QUESTIONS`, and `STALE IF`. It cannot grant broader scope, ownership, permissions, mutation authority, or acceptance changes. New children still use `fork_turns: none`.

## Roles

`policy-contract.json` is the machine source of truth.

| Role | Agent type | Route | Responsibility |
| --- | --- | --- | --- |
| Reader | `subagents_dispatch_reader` | GPT-5.6 Luna `max` | bounded read-only factual evidence |
| Worker | `subagents_dispatch_worker` | GPT-5.6 Luna `max` | clear bounded implementation after behavior is decided |
| Solver | `subagents_dispatch_solver` | GPT-5.6 Sol `high` | implementation with material judgment coupled to the write |
| Investigator | `subagents_dispatch_investigator` | GPT-5.6 Terra `xhigh` | broader read-only technical investigation after semantics are stable |
| Advisor | `subagents_dispatch_advisor` | GPT-5.6 Sol `high` | material read-only judgment or fresh independent final review |

Role identity is distinct from authority. There is no fixed Agent count and no Luna → Terra → Sol escalation ladder.

## Lightweight path and TeamPlan

One delegated responsibility uses a stable `unit_id`, a unique `task_id` for each materialized Agent attempt, and one bounded responsibility packet.

Use TeamPlan when two or more delegated responsibilities are concurrently unresolved or delegated outputs need non-trivial machine-checkable dependency/integration order. TeamPlan records coordination truth; it does not choose models or team size.

## Mutation authority and writer safety

Filesystem capability and authorization are separate. Child mutation authority is one of:

```text
none
declared-output-only
bounded-source-write
```

One canonical physical checkout has at most one active writing actor inside the current orchestration: Main while mutating, Luna Worker, or Sol Solver. Concurrent writers require genuine filesystem isolation plus semantic independence or explicit dependency/integration order.

## Recovery

Each materialized Agent attempt has a unique `task_id`; retries keep the stable `unit_id`. `UNKNOWN` is not failure and does not authorize replacement work.

A Host rejection before child identity exists is a pre-attempt rejection, not an Agent attempt or retry. One unchanged unit gets at most two materialized Agent attempts and one focused follow-up on an existing attempt.

## Runtime truth

Keep runtime claims separated as:

```text
requested
accepted
observed
```

Missing acceptance or observation stays missing. `runtime-evidence.py` is diagnostic and used only when a claim materially depends on runtime proof.

## Managed native Agent profiles

The five TOML profiles are native Codex custom-Agent definitions. `install-agents.py` adds project-specific ownership, collision safety, rollback, and deterministic verification around those files; it does not create another runtime.

Explicit `$dispatch` provides routine first-use authority only when real delegation needs a role and the managed profiles are cleanly absent. Successful provisioning in an already-running task ends with `RESTART_REQUIRED`, performs zero child spawns, and asks for one fresh task/session.

## Final Review

Final Review is consequence-driven. Process history such as TeamPlan use, recovery, Terra/Solver use, file count, or diff size is not a trigger by itself. When required, bind the exact candidate with `review-artifact.py` and use a fresh `subagents_dispatch_advisor`. Any deliverable mutation invalidates the prior verdict.

## Deterministic helper boundary

```text
install-agents.py
validate_team_plan.py
validate_team_ledger.py
runtime-evidence.py
review-artifact.py
```

These helpers provide deterministic lifecycle/validation/evidence support. Preview, Status, Steer, Takeover, Receipt, and Handoff Capsule remain Skill-level orchestration contracts.
