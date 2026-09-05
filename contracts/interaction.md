# Interaction Control

This file owns the user-visible control semantics for an active Orchestrate workflow. It defines plan-only Preview, Status, Steer, Takeover, cancel, continue, correction, and the Execution Receipt boundary without creating another Agent runtime, scheduler, ledger, or telemetry service.

`routing.md` still decides delegation value and role suitability. WorkGraph and WorkUnit own multi-responsibility dependency and responsibility truth. Main owns semantic decomposition, dispatch judgment, integration, and acceptance. `recovery.md` still owns attempt lifecycle and evidence-gated recovery. `guardrails.md` still owns authority and writer safety.

Orchestrate control intents include Preview, Status, Steer, Takeover, cancel, continue, and correction. Preview, Status, Steer, and Takeover are conceptual control names in this contract, not public Skill ids. `Orchestrate` is the single public orchestration Skill; `Doctor` is the only other public Skill. This contract defines conceptual control inputs after explicit Orchestrate selection/invocation and does not invent the exact slash entry rendered by a particular Codex App build.

## Control intents

The Orchestrate control intents accept these conceptual inputs:

```text
Preview: <task>
Status: optional <unit_id> zoom
Steer: optional <unit_id> plus <guidance>
Takeover: optional <unit_id> plus optional <guidance>
Cancel: optional <unit_id>
Continue: optional <unit_id> plus optional <guidance>
Correction: optional <unit_id> plus <guidance>
```

An explicit unit id resolves by exact match only. Without an explicit id, exactly one eligible unit auto-resolves; zero eligible units reports none, and multiple eligible units return the eligible unit ids as candidates and require a user choice. Never guess from recency, prose similarity, an unrelated session, or an ineligible unit. When one lightweight delegated responsibility exists, Main still gives it a stable unit id and may surface that id in Status output.

If there is no current V4 orchestration state in the conversation, Status reports that there are no current delegated responsibilities. Steer, Takeover, Cancel, Continue, and Correction stop with an exact target-not-found/current-state-unavailable message when they require an active target. They do not reconstruct an old task from memory, invent an Agent id, or search unrelated sessions to guess the target.

Control intents never widen the original user scope, permissions, mutation authority, external-impact authorization, or quality gates.

## Preview

Preview lets the user inspect the likely delegation shape before any delegated execution.

A preview is strictly non-executing:

```text
child spawn                    forbidden
Agent provisioning             forbidden
source mutation                forbidden
external action                forbidden
persistent orchestration state forbidden
```

Main may perform bounded read-only inspection when that evidence is needed to produce a useful preview.

A useful preview states only the likely responsibilities, role choices, important dependencies, expected writing owner, and whether Final Review is likely from facts already known. It is provisional. New evidence during real execution may change the route.

Even though Preview is provisional and runs before ordinary routing, its decomposition must preserve the material obligations already visible in current task truth. If a visible material obligation spans likely responsibilities, Preview should show the Main-owned integration/verification seam when that helps the user understand the shape. Do not create a requirement ledger, persistent WorkGraph, or decorative child merely to make preview topology complete. Unknown or evidence-dependent obligations may remain explicitly provisional rather than being guessed.

Do not run runtime-evidence diagnostics merely to make the preview look more precise. Do not claim that a requested model will be the observed runtime model.

## Status

The `status` control payload is a one-shot state inspection, not a polling loop.

The normal user-facing view uses the localized managed-team vocabulary from `receipt.md`: 程序员 / 产品经理 / 部门总监 in Chinese and Programmer / Product Manager / Department Director in English, together with the selected model/effort when useful. Internal machine ids remain hidden unless diagnostic detail is requested.

Group current responsibilities into the smallest useful presentation:

```text
Running / 运行中
Waiting / 等待
Needs attention / 需处理
Completed / 已完成
```

A current WorkGraph dependency may be shown as `waiting for U1` / `等待 U1` only when that dependency is part of current accepted structural truth. If dependency truth is unavailable to the current control turn, omit the dependency explanation rather than reconstructing or guessing it from prose.

Chinese example:

```text
运行中
U1 · 程序员 · Luna Max · 读取

等待
U2 · 程序员 · Luna Max · 执行 · 等待 U1

需处理
无

已完成
1 个职责
```

English example:

```text
Running
U1 · Programmer · Luna Max · Read

Waiting
U2 · Programmer · Luna Max · Execute · waiting for U1

Needs attention
None

Completed
1 responsibility
```

Prefer native Host state when it is exposed. When Host evidence is insufficient, report `UNKNOWN` exactly and place that unit under the attention/uncertain presentation rather than relabeling it as failed. Status must not convert `UNKNOWN` to failure, trigger a retry, create replacement work, or mutate artifacts.

Status performs at most one Host observation and one reconciliation pass. For persisted active state, use the state contract's locked reconciliation path so newer Host truth is written back without overwriting concurrent current state. It never spawns, steers, polls, resumes, takes over, or creates semantic lifecycle transitions.

An optional exact unit-id zoom may add only current accepted facts that help control the unit, for example:

```text
U2
职责: 程序员 · Luna Max · 执行
状态: 等待
依赖: U1
写入范围: src/...
尝试: 1
```

Use the orchestration locale stored in active state for command-only Status turns. When there is no current delegated responsibility, say so directly. Absence of an active unit is different from an existing unit whose runtime state is `UNKNOWN`.

Do not dump the full active-state JSON by default. Do not busy-poll the Host to manufacture certainty.

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

If the requested guidance would materially change one of those facts, do not label it steering. Return the change to Main and use WorkUnit recompilation, reroute, takeover, correction, or user authorization as appropriate.

If the target cannot be resolved to one current child, report the ambiguity or missing target instead of guessing.

`INTERRUPTED` is not eligible Steering and must not be described as Resume. Resuming the same interrupted child uses the Orchestrate continue/resume path and preserves its existing identity and ExecutionBinding generation.

## Takeover

Takeover is an explicit user-requested form of the existing `main_takeover` recovery action. The user may request it before ordinary recovery would otherwise choose another execution action.

Takeover transfers the unresolved responsibility to Main only after the previous child owner is safely settled.

```text
user requests takeover
-> resolve unit and current attempt
-> ask Codex to stop/close the running child when needed
-> establish from current Host evidence that the previous owner is no longer active
-> collect and verify any usable returned evidence
-> close or mark the old attempt no longer active
-> transfer responsibility to Main
-> continue inside the original user authority
```

For the current native lifecycle, `shutdown` is explicit closed Host evidence; `completed` or `errored` are also non-active execution states when the observed child identity is the expected one. Product state `CLOSED` remains the normalized lifecycle term. A missing or `notFound` observation is uncertainty, not proof of settlement.

For a writing child, Main must not begin mutation until the previous writer is confirmed no longer active. This preserves one-writer safety.

`UNKNOWN` does not authorize forced ownership transfer. If the Host cannot establish that the old owner has stopped, keep the same responsibility blocked for conflicting mutation and report the exact uncertainty. Main may continue unrelated safe work, but it must not duplicate the unresolved owned responsibility under a false takeover claim.

If the current Host cannot stop or otherwise establish a safe non-active state for an active child, report takeover as pending/unavailable rather than fabricating settlement.

If the unit/current attempt cannot be resolved at all, takeover does not proceed. Missing identity and uncertain runtime state are reported separately.

When takeover includes `: <guidance>`, treat that suffix as guidance for Main after safe transfer. Do not send it to the old child unless the user explicitly requested Steering instead.

A takeover does not reset the WorkUnit history or erase valid evidence. Pure takeover keeps the same unresolved WorkUnit responsibility. Recompile the WorkUnit only when takeover also changes structural truth such as dependency, ownership scope, deliverable, scope, authority, or acceptance.

## Cancel, Continue, and Correction

Cancel targets an existing orchestration responsibility and preserves all safety and ownership boundaries while stopping further managed work for that target. It does not erase accepted evidence or fabricate Host settlement.

Continue resumes the same interrupted child only through the current managed lifecycle protocol. It preserves native identity, ExecutionBinding, authority ceiling, and WriterLease semantics, advances the control generation, creates no fresh attempt, and does not consume a correction count budget.

Correction sends an evidence-gated same-child FOLLOWUP when the responsibility remains the same and `recovery.md` authorizes the current correction basis. There is no fixed correction-count ceiling. Each correction requires a non-empty changed basis relative to the currently retained authoritative recovery evidence. A material change to goal, output, scope, authority, ownership, or acceptance requires Main to re-evaluate or recompile the WorkUnit rather than disguising that change as correction.

## Execution Receipt

`receipt.md` owns the optional factual presentation of current orchestration state. It must derive from current WorkUnit, ExecutionBinding, Host observation, Main acceptance, explicit current control intent, and Final Review facts that are actually available. It does not create a persistent receipt ledger or reconstruct unavailable retry/rework/control history.

An ordinary delegated terminal response may include a compact execution receipt after Main's result or blocker summary. `UNKNOWN` and takeover-pending outcomes must remain explicitly uncertain.

Explicit Orchestrate with zero materialized children may emit the minimal acknowledgement defined by `receipt.md` and creates no persistent state. Plan-only Preview and Status-only Orchestrate intents do not require a terminal execution receipt.

The public role vocabulary is personified but bounded: Chinese uses `程序员`, `产品经理`, `部门总监`; English uses `Programmer`, `Product Manager`, `Department Director`. Activity words such as 读取/执行/决策/验收 (Read/Execute/Decide/Review) may be appended. Machine role ids and Host agent_type values are diagnostic implementation details.

The receipt may report only inspectable orchestration facts. Never expose private reasoning, raw child transcripts, credentials, source contents, or unrelated tool logs.

## Usage and cost boundary

Current Codex App Server can expose thread token-usage updates to clients, but the Skill contract does not assume that those events are available inside this Plugin execution path.

Therefore the built-in receipt does not estimate token counts or currency cost. Exact usage may be displayed only when a supported Host surface provides attributable usage for the relevant main/child threads. Missing usage remains unavailable rather than estimated from model names, elapsed time, or output length.

## No second runtime

These controls are Main-level orchestration instructions over Codex Native Subagents. They do not introduce a daemon, event bus, private Agent controller, background poller, persistent command server, or duplicate lifecycle state machine.
