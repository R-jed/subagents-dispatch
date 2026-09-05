# Execution Receipt

This contract owns the optional user-facing summary of subagents-dispatch orchestration. It is a presentation view over current Native Core facts, not a lifecycle protocol, event ledger, retry authority, acceptance authority, or replacement control plane.

## Source of truth

A receipt may be derived only from current owner facts:

```text
WorkUnit
ExecutionBinding
current Host lifecycle observation
Main acceptance
independent review state when applicable
explicit current user control intent
```

Do not create receipt-only state. Configured/requested/accepted/observed route truth stays distinct.

## Language and vocabulary

Use the language of the substantive user task. The public managed-team names are:

| Machine role | Chinese | English | Production route |
| --- | --- | --- | --- |
| `programmer` | 程序员 | Programmer | Luna Max |
| `product_manager` | 产品经理 | Product Manager | Sol Medium / Sol High |
| `department_director` | 部门总监 | Department Director | Astra High |

These names are intentionally personified presentation. Runtime state, authority, lifecycle, and evidence fields remain technical.

Showing a configured route such as `程序员 · Luna Max` means policy selected/requested that route. It does not claim Host-observed model/effort unless separate runtime evidence proves it.

## What may be reported

Report only reconstructable facts:

```text
materialized managed executions and selected policy routes
current/terminal lifecycle when Host evidence establishes it
Main WorkUnit acceptance
standard or highest review requirement and current verdict
current same-child followup/continuation facts retained by ExecutionBinding
blocking UNKNOWN or unresolved WriterLease ownership
```

A pre-materialization rejection is not a materialized Agent attempt. Same-child continuation is not a fresh attempt. Do not invent retry/rework counts from unavailable history.

## Compact presentation

Examples:

```text
编排: 程序员 · Luna Max · 执行
决策: 产品经理 · Sol Medium
验收: 未触发独立复核
```

```text
Orchestrate: Programmer · Luna Max · Execute
Decision: Product Manager · Sol Medium
Review: independent review not required
```

For a highest-consequence candidate:

```text
验收: 部门总监 · Astra High · authorization boundary
```

When current truth is uncertain, preserve `UNKNOWN` exactly. Do not convert it into failure, completion, transfer, or acceptance.

## Zero-child orchestration

For an explicit Orchestrate decision that correctly keeps work local:

```text
编排: 未调度子代理
验收: 由 Main 完成
```

```text
Orchestrate: no Subagents dispatched
Review: completed by Main
```

Plan-only creates no runtime state or terminal execution receipt requirement.

## Independent review

`contracts/final-review.md` owns the exact-candidate review tiers. A prior verdict invalidated by candidate mutation is not current.

Possible compact states include:

```text
验收: 产品经理 · Sol High · 待独立复核
验收: 部门总监 · Astra High · ship
验收: fix-first，候选尚未完成
验收: 证据不足
```

## Boundary with Main response

The receipt does not replace Main's task-facing answer. Main still owns what changed, what evidence was verified, test results, residual risks, and whether the requested outcome was achieved.
