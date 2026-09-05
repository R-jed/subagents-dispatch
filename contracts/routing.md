# Routing

This is the current three-role Native Subagent routing contract. Main owns the user goal, decomposition, semantic classification, dispatch judgment, integration, WorkUnit acceptance, and final response. Delegation remains optional and exists only when a distinct managed responsibility is worth its coordination cost.

`policy.json` owns the three managed role identities, their exact production model/effort routes, Decision tier triggers, review tier triggers, and the single product child ceiling. `responsibility-packet.md` owns the serialized responsibility record. WorkGraph/WorkUnit own responsibility structure and acceptance. `recovery.md` owns ExecutionBinding lifecycle. `interaction.md` owns user controls. `final-review.md` owns exact-candidate independent review and highest-consequence acceptance review.

## Delegation value

Keep work in Main when delegation would mostly duplicate context, add handoff cost, or provide no useful isolation, parallelism, bounded capability, investigation, implementation, or independent judgment. Zero children is normal.

Task size, file count, one failure, low confidence, expense, a spare Host slot, or a description such as `complex` does not by itself justify delegation or a higher model tier. Use the minimum useful fanout. Multiple children may launch only when responsibilities are independently ready, non-duplicative, and safe to overlap under current writer/permission boundaries.

Delegated work substitutes for Main doing that same responsibility. Main verifies returned evidence and artifacts, integrates across responsibility boundaries, and owns acceptance; it does not redo a child responsibility merely to recreate confidence. Child output remains a claim until Main accepts the relevant evidence into canonical task truth.

Main model and Main `ReasoningEffort` do not select, weaken, inherit into, or suppress managed role routes. A strong Main does not absorb a formal managed Decision merely because it is strong; a weak Main does not itself trigger extra delegation. Routing checks are admitted only by genuine ambiguity or consequence.

## Three managed roles

The stable product vocabulary is localized for presentation but the machine role ids are fixed:

```text
程序员 / Programmer             -> programmer
产品经理 / Product Manager      -> product_manager
部门总监 / Department Director  -> department_director
```

Users invoke `Orchestrate` and `Doctor`; they do not directly select a managed role to bypass admission policy.

### Programmer

Programmer is the ordinary work role and always uses the exact production route `gpt-5.6-luna / max`.

Use Programmer for bounded factual inspection or for bounded implementation after behavior, invariants, material decisions, scope, and acceptance are settled. Read versus write is not encoded in role identity. The WorkUnit/Responsibility Record owns `intent`, `mutation_authority`, `write_scope`, interfaces, invariants, and stop conditions.

### Product Manager

Product Manager is the technical decision role and always uses `gpt-5.6-sol` with an explicitly selected `medium` or `high` effort. The profile does not supply or inherit effort.

`medium` is the default Decision tier for local, reversible technical judgment that does not alter a material architecture/contract/authority/persistence/security boundary. `high` is required when Main confirms one or more `decision_routing.high_triggers` from `policy.json`. Deterministic policy code resolves the exact effort from those confirmed triggers; it does not infer the semantic trigger from task size, file count, retries, or a numeric risk score.

Product Manager may perform read-only investigation/synthesis. It may receive bounded write authority only when all of the following remain true:

```text
an unresolved material judgment exists
AND it cannot safely be settled before implementation
AND the judgment remains coupled to the writing work
AND independent delegation has concrete value
```

A Product Manager routing check is advisory evidence only. It cannot widen itself into a formal Decision responsibility or edit WorkGraph. If a Medium check discovers a High trigger, it reports the trigger and evidence to Main; Main creates the formal High responsibility. There is no self-escalation.

### Department Director

Department Director is the highest-consequence acceptance role and always uses the exact production route `gpt-6-astra / high`.

It has one mode only: fresh, semantically read-only, exact-candidate-bound acceptance review after Candidate Ready. It does not plan, implement, perform routing checks, provide mid-task advice, or act as a general expensive expert. Complexity alone never admits Department Director. Admission comes only from the highest review triggers in `policy.json`.

If the exact Department Director route is unavailable, do not downgrade to Product Manager or another model/effort. The acceptance obligation remains pending/insufficient.

## Exact route enforcement

`policy.json` is the single production owner of model/effort. Every managed spawn carries the exact model and reasoning effort explicitly. Custom-Agent profiles own stable role instructions/configuration intent, not production route truth. Parent defaults and role-profile model/effort values are not fallback sources.

The current production routes are:

```text
programmer           gpt-5.6-luna / max
product_manager      gpt-5.6-sol  / medium | high (explicit every spawn)
department_director  gpt-6-astra  / high
```

Unavailable or unsupported exact routes fail closed. There is no Luna -> Sol -> Astra failure escalation ladder.

## Responsibility semantics

Every delegated child owns one stable WorkUnit responsibility, not the raw user request. Before creating an ExecutionBinding, Main must establish enough truth to define:

```text
observable goal and output
intent: inspect | implement | verify | review
scope and forbidden scope
mutation-authority ceiling
interfaces and invariants
material decision boundary
acceptance condition
valid evidence safe to reuse
stop boundary
```

A child cannot widen scope, permission, mutation authority, user intent, external impact, acceptance, or its own role. Every fresh child uses `fork_turns = none` and receives only task-needed accepted context. All managed roles are leaf roles and may not create or control further Agents.

## Ready frontier and dispatch

A responsibility is structurally ready when its dependencies are accepted. Semantic readiness remains Main judgment.

The product has one safety ceiling:

```text
managed children <= 4
```

Known Host capacity may reduce available slots. Unknown capacity is not guessed. Spare capacity never authorizes decorative work. Deterministic helpers may report ready frontier, active managed children, Host readiness, known capacity, WriterLease state, and conservative slots; they do not rank work, choose responsibilities, or create automatic launch actions.

Before execution, give the user a brief route rationale when useful. Presentation may show the localized role plus route, for example `程序员 · Luna Max`, `产品经理 · Sol High`, or `部门总监 · Astra High`. This presentation creates no scheduler or state authority.

## Concurrency and writer ownership

Semantic mutation authority is owned by the WorkUnit/Responsibility Record. Host effective permission is separate runtime evidence and never expands semantic authority.

Independent semantic-read responsibilities may overlap. When Host positively proves effective read-only/isolation, that is the strongest path. When Host exposes broader write-capable permission, read/read overlap is still allowed only with no active canonical-workspace WriterLease and a before/after artifact-immutability guard covering the relevant workspace baseline. If the artifact changes, invalidate all workspace-dependent evidence from that batch, quarantine affected executions, pause new managed mutation, and let Main re-establish current workspace truth. Do not guess who changed it and do not auto-rollback user files.

Semantic-read work does not overlap an active canonical-workspace managed writer by default unless a future Host provides a separately verified immutable/isolated workspace boundary.

The canonical mutable workspace has one active managed WriterLease. WriterLease belongs to an exact ExecutionBinding, not to a role. Programmer or Product Manager may hold it when their responsibility grants bounded write authority. Department Director never holds it. Parallel writers still require Host-verifiable isolated workspaces and explicit integration boundaries.

`UNKNOWN` writer ownership blocks conflicting mutation or replacement.

## Blockers and recovery

Use the blocker vocabulary:

```text
contract
judgment
investigation
stalled
```

`contract` means required task truth is missing or contradictory. `judgment` means a material decision remains. `investigation` means broader evidence/synthesis is useful. `stalled` means the same responsibility is not progressing without one of those substantive blockers.

Failure does not define a model ladder. Recovery, evidence-gated retry, UNKNOWN handling, same-child continuity, and Main takeover remain owned by `recovery.md`. If responsibility meaning materially changes, create a new WorkUnit identity rather than rewriting the old one.

## Completion and review

Host completion creates candidate evidence and never accepts a WorkUnit by itself. Main verifies artifacts and relevant evidence before `ACCEPTED`; dependencies unlock only from accepted WorkUnits.

Before Candidate Ready, Main closes material obligations, integration seams, the actual deliverable, and required deterministic/reproducible verification. Then apply `final-review.md`.

Review is consequence-driven and independent of implementation history. Prior Product Manager use, model strength, diff size, file count, retries, or recovery do not trigger review by themselves.
