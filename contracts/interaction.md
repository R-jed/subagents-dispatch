# Interaction Control

This file owns the user-visible control semantics for an active Dispatch workflow. It defines Preview, Status, Steer, Takeover, and a compact execution receipt without creating another Agent runtime, scheduler, ledger, or telemetry service.

`routing.md` still decides delegation value and role suitability. `team-plan.md` still owns multi-responsibility dependency and integration truth. `recovery.md` still owns attempt lifecycle and bounded recovery. `guardrails.md` still owns authority and writer safety.

The stable interaction Skill ids are `preview`, `status`, `steer`, and `takeover`, with corresponding display names Preview, Status, Steer, and Takeover under the subagents-dispatch Plugin. This contract defines their inputs after explicit selection/invocation; it does not invent the exact slash entry rendered by a particular Codex App build.

## Control intents

The explicit interaction Skills accept these conceptual inputs:

```text
Preview: <task>
Status: optional <unit_id> zoom
Steer: optional <unit_id> plus <guidance>
Takeover: optional <unit_id> plus optional <guidance>
```

An explicit unit id resolves by exact match only. Without an explicit id, exactly one eligible unit auto-resolves; zero eligible units reports none, and multiple eligible units return the eligible unit ids as candidates and require a user choice. Never guess from recency, prose similarity, an unrelated session, or an ineligible unit. When one lightweight delegated responsibility exists without TeamPlan, Main still gives it a stable unit id and may surface that id in Status output.

If there is no current dispatch state in the conversation, Status reports that there are no current delegated responsibilities. Steer and Takeover stop with an exact target-not-found/current-state-unavailable message. They do not reconstruct an old task from memory, invent an Agent id, or search unrelated sessions to guess the target.

Control intents never widen the original user scope, permissions, mutation authority, external-impact authorization, or quality gates.

## Preview

Preview lets the user inspect the likely delegation shape before any delegated execution.

A preview is strictly non-executing:

```text
child spawn        forbidden
Agent provisioning forbidden
source mutation    forbidden
external action    forbidden
persistent TeamPlan creation forbidden
```

Main may perform bounded read-only inspection when that evidence is needed to produce a useful preview.

A useful preview states only the likely responsibilities, role choices, important dependencies, expected writing owner, and whether Final Review is likely from facts already known. It is provisional. New evidence during real execution may change the route.

Even though Preview is provisional and runs before ordinary routing, its decomposition must preserve the material obligations already visible in current task truth. If a visible material obligation spans likely responsibilities, Preview should show the Main-owned integration/verification seam when that helps the user understand the shape. Do not create a requirement ledger, persistent TeamPlan, or decorative child merely to make preview topology complete. Unknown or evidence-dependent obligations may remain explicitly provisional rather than being guessed.

Do not run runtime-evidence diagnostics merely to make the preview look more precise. Do not claim that a requested model will be the observed runtime model.

## Status

The `status` control payload is a one-shot state inspection, not a polling loop.

Report the smallest useful view of current delegated responsibilities:

```text
unit id
semantic role
known lifecycle state
write ownership, when relevant
current blocker, when known
```

Prefer native host state when it is exposed. When host evidence is insufficient, report `UNKNOWN` exactly. Status must not convert `UNKNOWN` to failure, trigger a retry, create replacement work, or mutate artifacts.

Status performs at most one Host observation and one reconciliation pass. It defaults to the low-resolution list above and accepts an optional exact unit-id zoom. It never spawns, steers, polls, resumes, takes over, or creates semantic lifecycle transitions.

When there is no current delegated responsibility, say so directly. Absence of an active unit is different from an existing unit whose runtime state is `UNKNOWN`.

Do not busy-poll the host to manufacture certainty.

## Steer

Steering keeps the same responsibility, role, task attempt, authority, and ownership while giving a running child focused new guidance.

Use the native Codex subagent control surface when available. A valid steer may add evidence, clarify an existing instruction, narrow attention, or tell the child what not to redo.

If the current Host cannot steer that active child, report the capability limitation. Do not simulate steering by spawning a replacement Agent, converting the request into a retry, or pretending a post-completion follow-up changed the running attempt.

Steering must not silently change:

```text
responsibility goal or output
assigned semantic role
write ownership
mutation authority
user scope
permissions
acceptance
external impact
```

If the requested guidance would materially change one of those facts, do not label it steering. Return the change to Main and use the ordinary TeamPlan revision, reroute, takeover, or user-authorization path as appropriate.

If the target cannot be resolved to one current child, report the ambiguity or missing target instead of guessing.

`INTERRUPTED` is not eligible Steering and must not be described as Resume. Resuming the same interrupted child uses the Dispatch-resume path and preserves its existing identity and accounting.

## Takeover

Takeover is an explicit user-requested form of the existing `main_takeover` recovery action. The user may request it before ordinary retry exhaustion.

Takeover transfers the unresolved responsibility to Main only after the previous child owner is safely settled.

```text
user requests takeover
-> resolve unit and current attempt
-> ask Codex to stop the running child when needed
-> establish terminal/stopped/closed host state
-> collect and verify any usable returned evidence
-> close or mark the old attempt no longer active
-> transfer responsibility to Main
-> continue inside the original user authority
```

For a writing child, Main must not begin mutation until the previous writer is confirmed no longer active. This preserves one-writer safety.

`UNKNOWN` does not authorize forced ownership transfer. If the host cannot establish that the old owner has stopped, keep the same responsibility blocked for conflicting mutation and report the exact uncertainty. Main may continue unrelated safe work, but it must not duplicate the unresolved owned responsibility under a false takeover claim.

If the current Host cannot stop or otherwise establish a safe terminal state for an active child, report takeover as pending/unavailable rather than fabricating settlement.

If the unit/current attempt cannot be resolved at all, takeover does not proceed. Missing identity and uncertain runtime state are reported separately.

When takeover includes `: <guidance>`, treat that suffix as guidance for Main after safe transfer. Do not send it to the old child unless the user explicitly requested Steering instead.

A takeover does not reset the unit's history or erase valid evidence. With TeamPlan, a pure takeover stays in Recovery state: TeamPlan keeps the last valid delegated role and does not create an invalid `role: main`. Revise TeamPlan only when takeover also changes structural truth such as dependency, ownership scope, deliverable, scope, or acceptance.

## Execution Receipt

`receipt.md` is the single source of truth for receipt accounting and presentation. Derive every axis from unique stable event references; repeated Status or reconciliation of the same event is idempotent. Keep materialized passes, focused follow-ups, retries, semantic rework, reviewer attempts, review rounds, and recovery as distinct facts.

An ordinary delegated terminal response emits the applicable Dispatch, Control, Review, and exceptional Recovery axes after Main's result or blocker summary, whether the requested work completed successfully or ended blocked/partial. This also applies to `UNKNOWN` and takeover-pending outcomes.

Explicit Dispatch with zero materialized children emits the minimal receipt defined by `receipt.md` and creates no persistent state. Preview and Status-only requests emit no terminal Dispatch Receipt.

The public vocabulary is activity-based. Chinese uses `读取`, `调研`, `执行`, `决策`, and `验收` and never exposes the internal Reader, Worker, Solver, Investigator, or Advisor names. English uses Read, Investigate, Execute, Decide, and Review.

The receipt may report only inspectable orchestration facts. Never expose private reasoning, raw child transcripts, credentials, source contents, or unrelated tool logs.

## Usage and cost boundary

Current Codex App Server can expose thread token-usage updates to clients, but the Skill contract does not assume that those events are available inside this Plugin execution path.

Therefore the built-in receipt does not estimate token counts or currency cost. Exact usage may be displayed only when a supported host surface provides attributable usage for the relevant main/child threads. Missing usage remains unavailable rather than estimated from model names, elapsed time, or output length.

## No second runtime

These controls are Main-level orchestration instructions over Codex Native Subagents. They do not introduce a daemon, event bus, private Agent controller, background poller, persistent command server, or duplicate lifecycle state machine.
