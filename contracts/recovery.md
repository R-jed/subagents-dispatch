# Recovery

Recovery owns what happens to one delegated responsibility after dispatch. It distinguishes uncertain runtime state from confirmed failure and keeps retries bounded without turning failure into a model ladder.

`routing.md` decides which capability the unresolved work needs. `team-plan.md` owns dependency, delegated role, ownership scope, and integration truth when TeamPlan is active. `interaction.md` owns the user-facing status, steer, and takeover controls. This file owns attempt identity, lifecycle, failure classification, retry bounds, and the underlying Main takeover semantics.

## Identity

Every delegated Agent attempt has:

```text
team_plan_revision, when TeamPlan exists
unit_id
task_id
attempt
```

`unit_id` identifies the stable responsibility. `task_id` identifies one concrete Agent attempt and must be unique. A retry keeps the same `unit_id` and uses a new `task_id`.

Without TeamPlan, the single delegated responsibility still gets a stable `unit_id` and unique `task_id`; `team_plan_revision` is null/absent as required by the ledger representation.

A prepared responsibility packet may contain a candidate `TASK ID` before the Host call, but an Agent attempt begins only after the Host accepts the spawn and returns an inspectable child identity such as a child task name, Agent id, `agentThreadId`, or equivalent native handle.

If `spawn_agent` is rejected before any child identity exists, treat that as a pre-attempt spawn rejection:

```text
no Agent attempt created
no lifecycle FAILED record
no attempt-budget consumption
no receipt retry increment
```

Correct an invalid call before invoking again. A parameter correction after a pre-attempt rejection is not `same_role_retry`. If Host evidence cannot establish whether a child was created, use `UNKNOWN` rather than assuming the rejection was pre-attempt or issuing replacement work.

## Native lifecycle

Use only:

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

Normal accepted execution is:

```text
PLANNED -> SPAWN_PENDING -> RUNNING -> COMPLETED -> CLOSED
```

An interrupted native turn is non-final:

```text
RUNNING -> INTERRUPTED -> RUNNING
```

Resuming keeps the same unit, task, attempt, Agent, role, responsibility, and authority. It creates no child, retry, focused follow-up, work pass, or semantic rework. `INTERRUPTED` does not prove that a writer is settled and is not the `Resume` operation itself.

`COMPLETED` means the Agent produced a complete result. Main has not necessarily accepted it yet.

Use `FAILED` only for a confirmed unsuccessful attempt.

Use `UNKNOWN` when available host evidence cannot establish creation, identity, completion, or current Agent state. UNKNOWN is not failure.

While an attempt remains UNKNOWN:

```text
no replacement Agent
no retry
no semantic reroute
no conflicting ownership reassignment
no claim that the attempt failed
```

A user takeover request does not convert `UNKNOWN` into a settled state. Main may ask the host to stop the target, but responsibility execution transfers only after the previous owner is known to be no longer active.

Wait for useful native evidence when available. If the runtime never exposes enough evidence to resolve the ambiguity, preserve the uncertainty and avoid duplicate mutation risk. Do not build a private scheduler or busy-poll to manufacture state.

## Failure classification

For a confirmed failed attempt, record both axes.

Execution origin:

```text
none
runtime_unavailable
permission_failure
tool_failure
timeout
quality_failure
runtime_ambiguous
```

`runtime_ambiguous` is reserved for an UNKNOWN record; it does not mean a confirmed failed execution.

Semantic blocker:

```text
none
contract
judgment
investigation
stalled
```

These axes answer different questions: what is known about execution, and what unresolved task need remains. Do not invent additional blocker values in Agent profiles or local recovery logic.

Examples:

```text
runtime_unavailable + none
-> same role may still be correct

quality_failure + judgment
-> resolve the material decision through Main/Sol

quality_failure + contract
-> Main repairs missing task truth

runtime_ambiguous
-> UNKNOWN; do not replace
```

Infrastructure failure is not capability evidence.

## Bounded correction

One unchanged unit may use at most:

```text
2 Agent attempts
1 focused follow-up on an existing Agent
```

Only materialized Agent attempts count toward the two-attempt budget. A Host/tool rejection before child identity exists does not consume attempt 1 and does not make the next corrected spawn “attempt 2.”

A focused follow-up is only for a complete result that is close enough to acceptance that the same Agent, role, responsibility, and authority still fit. It carries the exact failure and preserves valid evidence and DO NOT REDO facts.

A follow-up stays inside the same attempt and does not create a new `task_id`.

A second Agent attempt is allowed only after the first materialized attempt is confirmed FAILED and Main has a concrete reason that another attempt is policy-compatible. The new attempt gets a new `task_id`.

After the second Agent attempt fails, Main takes ownership or reports the exact blocker. Do not create a third Agent attempt for the unchanged unit.

The two-attempt bound limits automatic delegated recovery. It is not a team-size or concurrency limit and it does not prevent the user from explicitly asking Main to take the work back.

## Allowed recovery actions

Use only:

```text
same_agent_followup
same_role_retry
semantic_reroute
main_takeover
```

### same_agent_followup

Use once when the result is complete, the role remains correct, and a narrow correction can reasonably satisfy acceptance.

### same_role_retry

Use a new Agent attempt when responsibility and role remain correct and the retry packet is materially improved by new evidence, a concrete correction hypothesis, or a confirmed transient execution problem.

A pre-attempt spawn rejection is not `same_role_retry`; repair the call and make the first valid spawn attempt.

### semantic_reroute

Use only when the remaining semantic blocker changes the capability required:

```text
contract -> Main repairs task truth or acceptance
judgment -> capable Main or Sol Advisor/Solver
investigation -> Terra Investigator only when semantics are stable, the work is read-only, and broader investigation is actually useful
stalled -> same-role retry only if the role remains correct; otherwise Main takes over
```

Failure itself never means Luna -> Terra -> Sol.

If TeamPlan is active and semantic rerouting changes the unit's delegated Agent role, create a new TeamPlan revision before the replacement Agent attempt. Keep the same `unit_id` only when its goal and output remain the same. Role reassignment does not reset the attempt budget.

### main_takeover

Main may take ownership when:

- recovery is exhausted;
- the safe delegated route is unclear;
- authority would need to widen;
- continuing delegation no longer adds value; or
- the user explicitly requests takeover through `interaction.md`.

Explicit user takeover changes who should continue the responsibility; it does not prove that the previous owner has stopped.

Before transfer:

```text
resolve the current attempt
-> stop the child when it is still running and native control is available
-> establish that the previous owner is no longer active
-> inspect and preserve any valid returned evidence
-> end delegated execution for that unit
-> continue the same responsibility in Main
```

For a writing child, Main must remain read-only until the previous writing owner is confirmed stopped/terminal/closed. If state remains `UNKNOWN`, takeover remains pending and Main does not start conflicting mutation.

Takeover does not create another Agent attempt and does not reset attempt history. It ends delegated execution for the responsibility and continues the same work in Main under the same user authority.

## TeamPlan revisions

A retry by itself does not create a new TeamPlan revision.

TeamPlan's `role` vocabulary contains delegated Subagent roles only. `main_takeover` therefore does not rewrite a unit to an invented `role: main`. The unit keeps the last valid delegated role recorded in the plan revision; Recovery records that delegated execution ended and Main continued the stable responsibility.

A takeover alone does not require a TeamPlan revision when goal, output, dependencies, ownership scope, deliverable, scope, and acceptance remain unchanged. Create a new TeamPlan revision only if takeover also changes one of those structural facts. A materially redefined goal/output is a new responsibility and requires a new `unit_id`.

Already-dispatched work remains bound to the revision it received. If a structural revision affects active work, pause new dispatch until affected attempts are safely settled or invalidated.

## Adoption and close

Main inspects actual artifacts/evidence and marks an attempt adopted only when acceptance is supported.

An adopted completed native Agent should be closed when the host exposes that control. `CLOSED` is lifecycle state, not correctness proof, and may remain `adopted=false`. `adopted=true` requires completed accepted evidence; stopping or closing alone never creates acceptance.

Stopped or superseded work may still contain useful evidence. Main verifies that evidence before reuse; stopping a child does not make its claims true.

## Ledger validation

When machine-checkable recovery state is genuinely useful, validate the current logical ledger without creating another persistent state source:

```bash
python scripts/validate_team_ledger.py -
```

The validator checks exact record shape, policy-owned delegated role bindings, TeamPlan revision binding, stable unit goal/output identity, unique task and Agent identity, attempt sequence, the two-attempt bound, follow-up bound, UNKNOWN replacement suppression, and lifecycle/adoption consistency.

For ordinary runtime recovery and cross-turn controls, thread-local continuity belongs to the bounded ephemeral capsule in `state.md`. Do not create repository-local, `.codex/`, or `CODEX_HOME` TeamLedger history merely because the validator accepts serialized input.

A retained ledger file is an explicit export/eval/audit artifact only when the user or the verification workflow actually requires one. Keep that artifact outside ordinary runtime state, bind its purpose and lifetime explicitly, and never treat it as a second live scheduler or coordination database. When an upstream workflow already owns durable coordination truth, reuse that source instead of creating a competing ledger.
