# Dispatch Receipt

This contract owns the user-facing summary of subagents-dispatch orchestration. It reports how Subagents were dispatched and controlled. It does not summarize the user's task result, implementation details, business outcome, or Main's final answer.

## Reporting axes

The normal receipt uses three independent axes. Recovery is shown only when it actually occurred.

```text
Dispatch / 编排
Control / 控制
Review / 验收
Recovery / 恢复   # exceptional only
```

Do not merge task completion state, Final Review verdicts, Agent lifecycle, retry history, and role names into one opaque line.

## Language

Choose presentation language from the substantive user task that established the active orchestration. Persist that locale in the thread-scoped active state so later command-only turns such as `Status` or `Steer` do not accidentally switch language.

Supported presentation policy:

```text
Chinese user task
-> Chinese labels, actions, lifecycle explanations, and receipt prose
-> keep model family, reasoning effort, and canonical control-skill names in English

English user task
-> native English presentation

other / unresolved language
-> English fallback unless the user explicitly requests another language
```

For a stateless Preview, infer language from the preview task itself.

## Public activity vocabulary

Internal role names are orchestration implementation details. Present the materialized work by model lane and user-understandable activity.

| Internal responsibility | Chinese | English |
| --- | --- | --- |
| Reader | 读取 | Read |
| Investigator | 调研 | Investigate |
| Worker | 执行 | Execute |
| Solver | 执行 | Execute |
| Advisor material judgment | 决策 | Decide |
| Advisor Final Review | 验收 | Review |

Keep model family and effort in their canonical English form, for example:

```text
Luna Max
Sol High
Terra XHigh
```

For Chinese users, do not leak `Reader`, `Worker`, `Solver`, `Investigator`, or `Advisor` into the normal receipt.

Canonical control entry names remain `Status`, `Steer`, and `Takeover` so the receipt matches the controls the user selected from the Skill surface.

## Dispatch axis

The Dispatch axis reports materialized delegated work passes in first-materialization order. It includes a model lane only when current native runtime evidence observed that model; otherwise it reports the public activity without a model name.

Chinese example:

```text
编排: Luna Max 读取×2 · Luna Max 执行×2 · Sol High 决策 · Sol High 验收×2
```

English example:

```text
Dispatch: Luna Max Read×2 · Luna Max Execute×2 · Sol High Decide · Sol High Review×2
```

A work pass is not a tool-call count.

Count one materialized pass when:

```text
a new native child identity is returned for a valid delegated attempt
or
a permitted same-Agent focused follow-up actually starts another bounded correction pass
```

Do not count:

```text
pre-child Host rejection
Status
Steer
wait / observation
resuming an INTERRUPTED child in the same attempt
Main reading
Main implementation
Main integration
Main decision-making
```

A failed materialized Agent attempt still counts as a real dispatched pass. Any replacement-attempt reason is reported separately under Recovery.

## Idempotent accounting

Do not rely only on mutable integer increments. Persist a small set of unique accounting references so interruption or reconciliation cannot double-count the same work.

Examples:

```text
attempt:U1:A1
followup:U1:A1:F1
attempt:U2:A1
review:U3:A1
```

The active root-thread capsule stores the structured event bound to each reference. Every materialized attempt, follow-up, or reviewer-attempt event carries its exact `unit_id`, integer `attempt`, and non-empty `agent_id`; that identity must match a materialized unit in the same capsule. One child attempt contributes at most one attempt or reviewer-attempt pass, and at most one bounded focused follow-up pass, even if a caller supplies different refs for the same identity. `persist_receipt_events` checks these bindings while holding the state lock, then merges and writes the events. Identical references are idempotent, while fabricated identities, duplicate identity bindings, or conflicting reuse of one reference fail closed. Visible totals are always derived from the persisted unique events.

A materialized event may include `model_lane` only with `model_evidence_source: native` or `both`. Requested, configured, accepted, or local-only route values must not appear as observed model facts in a receipt.

Aggregation is derived from unique materialized references plus their role/activity binding. Seeing the same Host event again after resume must not increment the visible count twice.

Use distinct stable refs for distinct accounting facts:

```text
materialized attempt    -> Dispatch pass
focused follow-up       -> Dispatch pass + focused-follow-up fact
replacement retry       -> Recovery retry; its new attempt ref reports the pass
semantic rework         -> Review rework only when a correction pass actually begins
reviewer attempt        -> Dispatch pass, even if no verdict is produced
review round            -> Review round only after an actual verdict
runtime recovery        -> Recovery fact such as unambiguous rebind
explicit control        -> Control use
```

One ref may be observed repeatedly but contributes once. Reusing one ref for conflicting facts is corrupt accounting and fails closed. Reconciliation itself is not a work pass, retry, rework, or review round.

## Control axis

Show Control only when an explicit control entry point was used against the active orchestration.

Chinese:

```text
控制: Status×3 · Steer×1
```

English:

```text
Control: Status×3 · Steer×1
```

Status is read-only with respect to user artifacts, native child execution, TeamPlan semantics, authority, and ownership. It may update only subagents-dispatch's own ephemeral receipt metadata so an observed `Status×N` remains factual.

A control action does not create a delegated work pass by itself.

## Review axis

The Review axis reports the independent Final Review loop only. It does not claim that the overall user task is complete.

A review round exists only when a materialized fresh independent reviewer produces an actual verdict against the exact candidate. The round binds the reviewer `unit_id`, `attempt`, and `agent_id` plus the candidate's `review_artifact_id`; one reviewer attempt and one artifact identity can each contribute at most one round.

Chinese states may include:

```text
验收: 未触发
验收: 1轮 · 通过
验收: 1轮 · 需返工
验收: 1轮 · 需重新设计
验收: 1轮 · 证据不足
验收: 2轮 · 返工1次 · 通过
```

English equivalents:

```text
Review: not triggered
Review: 1 round · passed
Review: 1 round · rework required
Review: 1 round · redesign required
Review: 1 round · insufficient evidence
Review: 2 rounds · rework×1 · passed
```

A reviewer attempt that crashes before producing a verdict contributes to Dispatch as a materialized Agent pass but does not increment the Review round count.

## Rework versus retry

Rework and retry are different axes.

Rework increments only when:

```text
a candidate or complete delegated result exists
-> Main verification or independent review identifies a concrete acceptance gap
-> a correction pass actually begins
```

The rework event binds that materialized focused follow-up and the `review_artifact_id` of the review round that reported the concrete gap. An unbound claim is not a rework.

Runtime failure, timeout, tool failure, or a replacement Agent attempt is not rework.

Recovery retry increments only when a confirmed materialized Agent attempt is replaced under the bounded Recovery contract: the first attempt is confirmed `FAILED`, and its replacement is the materialized second attempt. The retry event carries and matches that replacement's exact `unit_id`, `attempt=2`, and `agent_id`; duplicate refs cannot recount the same replacement. A pre-child spawn rejection is never a retry.

A runtime rebind recovery fact likewise carries the exact materialized `unit_id`, `attempt`, and `agent_id`. Unsupported, unbound, or duplicate generic recovery claims fail closed.

When retry occurred, add an exceptional line:

```text
恢复: 重试1次
Recovery: retry×1
```

If recovery did not occur, omit the line entirely.

## Zero-child explicit Dispatch

Explicit Dispatch is itself a user request to evaluate orchestration. If routing correctly keeps all work in Main and no child is spawned, acknowledge the result with a minimal receipt:

Chinese:

```text
编排: 未调度子代理
验收: 未触发
```

English:

```text
Dispatch: no Subagents dispatched
Review: not triggered
```

This does not create persistent dispatch state.

Preview and Status-only requests do not emit a terminal Dispatch Receipt.

## Preview presentation

Preview uses the same public vocabulary but must remain explicitly predictive:

```text
预计编排: Luna Max 读取×2 · Luna Max 执行 · Sol High 验收
Likely dispatch: Luna Max Read×2 · Luna Max Execute · Sol High Review
```

Preview never materializes accounting references, creates active state, spawns children, or mutates artifacts.

## Boundary with Main response

The receipt must not summarize:

```text
what code changed
what files were fixed
whether the user's business goal succeeded
full test results
the final deliverable contents
Main's own implementation or reasoning
```

Main owns the task-facing final response. The receipt answers only: what Subagent orchestration occurred, which explicit controls were used, whether independent review ran, and whether delegated recovery happened.
