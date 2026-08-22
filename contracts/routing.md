# Routing

This is the current V4 routing contract. The main session owns the user goal, decomposition, profile choice, dispatch judgment, integration, WorkUnit acceptance, and final response. Delegation is optional and exists only when a distinct child responsibility is worth its coordination cost.

`policy.json` owns the five fixed managed profile identities and the single product child ceiling. `responsibility-packet.md` owns the serialized child responsibility record. The WorkGraph and WorkUnit state own responsibility structure, dependencies, ownership, and acceptance. `recovery.md` owns ExecutionBinding lifecycle and recovery. `interaction.md` owns user controls. `final-review.md` owns exact-candidate independent review.

## Delegation value

Keep work in the main session when a child would mostly duplicate context, add handoff cost, or provide no useful isolation, parallelism, capability uplift, read-heavy investigation, or independent judgment. Zero children is a normal outcome.

Task size, file count, expense, or a description such as complex does not by itself justify delegation. The main session creates only responsibilities that can make useful progress and may add more WorkUnits later when new independent work becomes clear.

There is no separate TeamPlan planning authority. WorkGraph is the structural source of truth for one or many WorkUnits. A persisted `team_plan_revision` value may remain temporarily as a state-schema compatibility marker during the V4 RC; it carries no planning, routing, revision, or integration-order authority.

## Preserve task truth

When an accepted user plan, another trusted Skill, or an upstream workflow already defines goal, decomposition, dependencies, outputs, business acceptance, or quality gates, preserve that truth. Orchestrate may assign owners, select specialist profiles, control useful concurrency, and enforce writer and lifecycle boundaries. It must not silently replace the upstream domain plan.

Before delegation, identify the material obligations that must survive decomposition. Each obligation must remain covered by a delegated responsibility or an explicit main-session integration or verification responsibility. Cross-responsibility seams remain real work even when no child owns them.

A structurally valid graph does not prove semantic coverage. If decomposition loses an already-known requirement, repair the decomposition in the main session. Use the `contract` blocker only when required task truth is genuinely missing, contradictory, or underspecified.

## Select one fixed profile explicitly

Profile choice is a main-session judgment. Deterministic runtime code validates the chosen fixed profile; it does not infer a profile from task size, failure, file count, or a numeric routing score.

Use Reader for narrow read-only factual work such as bounded repository traces, call mapping, test mapping, or focused evidence collection.

Use Worker when behavior, invariants, scope, acceptance, and material decisions are settled and the remaining work is bounded implementation inside explicit write authority.

Use Investigator for broader read-only technical exploration and synthesis when semantics are stable and no material decision remains unresolved.

Use Solver when material judgment is coupled to implementation and cannot be separated safely from the writing work.

Use Advisor for a demanding read-only second judgment or the fresh independent review required by `final-review.md`.

Failure does not define a model ladder. A weak Luna result, one failed test, low confidence, or task size does not automatically route work to Terra or Sol. The main session reassesses the unresolved responsibility and selects the fixed profile that fits the remaining need.

## Responsibility semantics

Every delegated child owns one stable WorkUnit responsibility, not the raw user request. Before creating an ExecutionBinding, the main session must establish enough truth to define:

```text
observable goal and output
intent: inspect | implement | verify | review
scope and forbidden scope
mutation-authority ceiling
interfaces and invariants
material decision boundary
acceptance condition
valid evidence that should be reused
stop boundary
```

Those semantics are serialized through `responsibility-packet.md`. A child cannot widen scope, permission, mutation authority, user intent, external impact, acceptance, or its own role.

Every fresh child receives fresh context with `fork_turns = none`. The main session places only task-needed context in the responsibility packet. Reuse the same child when continuity with that child's existing context is materially useful.

## Ready frontier and dispatch

A responsibility is structurally ready when its dependencies are accepted. Semantic readiness remains a main-session judgment.

The product has one managed-child ceiling:

```text
managed children <= 4
```

The ceiling is a safety limit, not a target. Host capacity may reduce it. Unknown Host capacity is not guessed and does not create a synthetic project capacity token. The Host remains authoritative and may reject a spawn before materialization.

Deterministic code may report the ready frontier, current active count, Host readiness, known Host capacity, WriterLease state, and available slots. It does not rank the frontier, choose a WorkUnit, create critical-path priority, apply a fixed acceptance-backlog threshold, or emit automatic launch actions. The main session owns those decisions.

Spare capacity never justifies decorative work. If unprocessed results make further delegation counterproductive, integrate and accept the useful results first.

## Concurrency and writer ownership

Independent read-only work may overlap when read-only behavior and responsibility independence are verifiable. A read-only role label alone is insufficient proof. If effective read-only or isolation cannot be established, use the conservative serial path.

The canonical mutable workspace has one active managed WriterLease. Intended file separation alone does not prove safe parallel writes. Parallel writers require Host-verifiable isolated workspaces and explicit integration boundaries; without that evidence, keep one writer.

`UNKNOWN` writer ownership blocks conflicting mutation or replacement. Nonconflicting work may continue only when isolation from the unknown execution is deterministically established.

## Blockers and recovery

Use the blocker vocabulary:

```text
contract
judgment
investigation
stalled
```

`contract` means required task truth is missing or contradictory. `judgment` means a material decision remains. `investigation` means broader read-only evidence gathering is useful. `stalled` means the same responsibility is not progressing without one of the preceding blocker types.

Recovery mechanics, evidence-gated follow-up or fresh retry, UNKNOWN handling, and main-session takeover belong to `recovery.md`. Routing chooses no automatic escalation ladder.

If a WorkUnit goal, output, ownership, or acceptance meaning materially changes after execution begins, create a new WorkUnit identity instead of rewriting the old responsibility.

## Completion

Host completion creates candidate evidence and never accepts a WorkUnit by itself. The main session verifies actual artifacts and relevant evidence before `ACCEPTED`. Dependencies unlock only from accepted WorkUnits.

Before Candidate Ready, verify material obligations, integration seams, the actual deliverable, and required deterministic or reproducible evidence. Apply `final-review.md` when consequence-based review policy requires an independent second judgment.
