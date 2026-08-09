# Interaction Control

This file owns the user-visible control surface for an active `/dispatch` workflow. It adds preview, status, steering, takeover, and a compact execution receipt without creating another Agent runtime, scheduler, ledger, or telemetry service.

`router-core.md` still decides delegation value and role suitability. `team-plan.md` still owns multi-responsibility dependency and integration truth. `recovery.md` still owns attempt lifecycle and bounded recovery. `guardrails.md` still owns authority and writer safety.

## Command intents

The normal form remains:

```text
/dispatch <task>
```

The following control intents are recognized before ordinary task routing:

```text
/dispatch preview <task>
/dispatch status
/dispatch steer <unit_id>: <guidance>
/dispatch takeover <unit_id>
/dispatch takeover <unit_id>: <guidance>
```

`status` is a control intent only when it is the complete remaining request. A task such as `status page is broken` is ordinary work. `steer` and `takeover` require a resolvable current unit id. When one lightweight delegated responsibility exists without TeamPlan, Main still gives it a stable unit id and may surface that id in status output.

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

Do not run runtime-evidence diagnostics merely to make the preview look more precise. Do not claim that a requested model will be the observed runtime model.

## Status

`/dispatch status` is a one-shot state inspection, not a polling loop.

Report the smallest useful view of current delegated responsibilities:

```text
unit id
semantic role
known lifecycle state
write ownership, when relevant
current blocker, when known
```

Prefer native host state when it is exposed. When host evidence is insufficient, report `UNKNOWN` exactly. Status must not convert `UNKNOWN` to failure, trigger a retry, create replacement work, or mutate artifacts.

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

When at least one child was actually spawned, the terminal response for that dispatch includes one compact execution receipt after the ordinary result or blocker summary. This applies whether the requested work completed successfully or ended blocked/partial.

### Unified shape

Emit the receipt as four fixed slots separated by `·`, plus an optional closing note when a blocker or `UNKNOWN` state is material. `→` connects role steps in execution order, and `×N` marks a role used N times. Keep the receipt to one line, with no free-text role descriptors.

```text
Dispatch: <role chain> · <state> · <retry> · <final review> [ · <blocker/UNKNOWN note>]
```

Slot enumerations:

```text
role chain     Reader×2 → Advisor        roles in execution order; `×N` after the role
state          complete | blocked | pending | main takeover
retry          no retry | retried N
final review   not required | ship | fix-first | rethink | INSUFFICIENT_EVIDENCE | not reached
```

The retry slot counts only replacement Agent attempts after a materialized prior attempt was confirmed `FAILED` under `recovery.md`. A `spawn_agent` call rejected before the Host returns any child identity is not an Agent retry, does not consume an attempt, and must leave the receipt at `no retry` / `未重试` unless a later real Agent attempt is actually retried.

`pending` here means takeover pending. `main takeover` is the state-slot spelling of the existing `main_takeover` recovery action. Slot coherence: a `fix-first`, `rethink`, or `INSUFFICIENT_EVIDENCE` final review must not pair with state `complete`; `not reached` pairs with `blocked`, `pending`, or `main takeover`. When a blocker or `UNKNOWN` writer is material, append a short closing note (for example `takeover pending on UNKNOWN writer`); never convert `UNKNOWN` into failure or replacement work.

### Language

Emit the receipt in the language of the user's current request/thread. Chinese requests use the localized terms below; English requests keep the native terms above. For mixed-language requests, follow the language of the main clause; when the request language is neither Chinese nor English, fall back to English. This rule applies to the receipt only, not to the rest of the terminal output. Contract keywords stay in English in both languages: `UNKNOWN`, `DO NOT REDO`, `STALE IF`. `Main` stays English when it appears as a standalone keyword (for example `Main takeover`), and is localized only as a state-slot value.

Chinese mapping:

```text
Reader → 读取               complete → 完成
Worker → 实现               blocked → 卡住
Solver → 决策               pending → 待定
Investigator → 调查         main takeover → 主会话接手
Advisor → 审核              no retry → 未重试
                            retried N → 重试 N 次

not required → 无需最终复核
ship → 最终复核通过
fix-first → 先修再验
rethink → 重新设计
INSUFFICIENT_EVIDENCE → 证据不足
not reached → 未做最终复核
```

Examples:

```text
Chinese: Dispatch: 读取×2 → 审核 · 完成 · 未重试 · 最终复核通过
English: Dispatch: Reader×2 → Advisor · complete · no retry · ship
Chinese: Dispatch: 读取 → 实现 · 完成 · 重试 1 次 · 无需最终复核
English: Dispatch: Reader → Worker · complete · retried 1 · not required
Chinese: Dispatch: 决策 → 审核 · 卡住 · 未重试 · 先修再验
English: Dispatch: Solver → Advisor · blocked · no retry · fix-first
Chinese: Dispatch: 读取 → 决策 · 主会话接手 · 未重试 · 未做最终复核 · 接管待定于 UNKNOWN 写入者
English: Dispatch: Reader → Solver · main takeover · no retry · not reached · takeover pending on UNKNOWN writer
```

Do not emit the receipt for a zero-child task, preview, or status-only request. Do not turn it into a verbose trace.

The receipt may report only inspectable orchestration facts such as semantic roles used, attempt/retry count, steering/takeover, and Final Review state. Concrete model identity or effort may appear only when current runtime evidence actually observed it and the detail is useful. Requested/configured model identity is never presented as observation.

Never expose private chain-of-thought, hidden reasoning, raw child transcripts, credentials, or unrelated tool logs.

If the user explicitly asks for delegation details, Main may expand the receipt into a short per-unit summary while preserving the same evidence rules.

## Usage and cost boundary

Current Codex App Server can expose thread token-usage updates to clients, but the Skill contract does not assume that those events are available inside this Plugin execution path.

Therefore the built-in receipt does not estimate token counts or currency cost. Exact usage may be displayed only when a supported host surface provides attributable usage for the relevant main/child threads. Missing usage remains unavailable rather than estimated from model names, elapsed time, or output length.

## No second runtime

These controls are Main-level orchestration instructions over Codex Native Subagents. They do not introduce a daemon, event bus, private Agent controller, background poller, persistent command server, or duplicate lifecycle state machine.
