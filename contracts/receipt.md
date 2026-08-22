# Execution Receipt

This contract owns the optional user-facing summary of subagents-dispatch orchestration. It is a presentation view over current Native Core facts. It is not a lifecycle protocol, persisted event ledger, retry authority, acceptance authority, or replacement control plane.

## Source of truth

A receipt may be derived only from facts already established by current owners:

```text
WorkUnit
ExecutionBinding
current Host lifecycle observation
Main acceptance
Final Review state when applicable
explicit user control intent when the current interaction records it
```

Do not create receipt-only state to make a summary possible. `accounting_refs` remains bounded Native Core evidence such as current-generation Host observations; it is not a receipt event store.

## Language and vocabulary

Use the language of the substantive user task. Canonical model/effort labels derive from the fixed profiles in `policy.json` and stay in English:

```text
Luna Max
Terra High
Sol High
```

Normal user-facing activity labels may summarize managed work as:

| Responsibility | Chinese | English |
| --- | --- | --- |
| Reader | 读取 | Read |
| Investigator | 调研 | Investigate |
| Worker / Solver | 执行 | Execute |
| Advisor judgment | 决策 | Decide |
| Advisor Final Review | 验收 | Review |

Internal role names do not need to appear in the normal receipt.

## What may be reported

Report only facts that can be reconstructed without inventing history:

```text
materialized managed executions and their selected configured lanes
current or terminal lifecycle when Host evidence establishes it
whether Main accepted the WorkUnit
whether an independent Final Review was required and its current verdict
whether an explicit same-child followup or continuation is represented by the current ExecutionBinding state
blocking UNKNOWN or unresolved writer ownership
```

Configured route truth and observed runtime truth stay separate. Showing `Luna Max`, `Terra High`, or `Sol High` means the execution was bound to that project profile. It does not claim the Host independently re-observed model and effort unless separate Host evidence proves that fact.

A pre-materialization spawn rejection is not a materialized Agent attempt. A same-child continuation does not become a fresh attempt. Do not infer a retry or rework count from the final capsule when the current state does not retain enough history to prove it.

## Compact presentation

A successful delegated run may use a compact form such as:

```text
编排: Luna Max 读取 · Terra High 调研 · Luna Max 执行
验收: Main 已接受 3 个职责 · 独立复核未触发
```

```text
Dispatch: Luna Max Read · Terra High Investigate · Luna Max Execute
Review: Main accepted 3 responsibilities · independent review not triggered
```

When current truth is uncertain, say so explicitly:

```text
编排: U2 状态 UNKNOWN，未启动替代执行
验收: 阻塞
```

Do not convert `UNKNOWN` into failure, completion, ownership transfer, or acceptance.

## Zero-child orchestration

When the user explicitly asks Orchestrate to evaluate delegation and Main correctly keeps all work local, a minimal acknowledgement is enough:

```text
编排: 未调度子代理
验收: 由 Main 完成
```

```text
Dispatch: no Subagents dispatched
Review: completed by Main
```

Plan-only does not need a terminal execution receipt because it creates no runtime state or Host actions.

## Final Review

If `contracts/final-review.md` requires independent review, report only the current exact-candidate review state. A prior verdict invalidated by candidate mutation must not be presented as current.

Examples:

```text
验收: 独立复核待执行
验收: 独立复核 ship
验收: 独立复核 fix-first，候选尚未完成
验收: 独立复核证据不足
```

## Boundary with the task-facing response

The receipt does not replace Main's final response. Main still owns:

```text
what changed
what evidence was verified
what tests passed or failed
remaining risks
whether the user's requested outcome was achieved
```

The receipt answers only what managed orchestration materially occurred and what acceptance/review state can be proven from current Native Core truth.
