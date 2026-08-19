# Routing

This is the current V4 routing contract. The main session owns the user goal, decomposition, integration, WorkUnit acceptance, and final response. Delegation is optional and exists only when a distinct child responsibility is worth its coordination cost.

`policy.json` owns the five fixed managed profile identities. `responsibility-packet.md` owns the one serialized responsibility record. `team-plan.md` owns multi-responsibility dependency and integration truth. `recovery.md` owns ExecutionBinding lifecycle and bounded recovery. `interaction.md` owns user controls. `final-review.md` owns exact-candidate independent review.

## Delegation value

Keep work in the main session when a child would mostly duplicate context, add handoff cost, or provide no useful isolation, parallelism, capability uplift, read-heavy investigation, or independent judgment. There is no minimum child count. Zero children is a normal outcome.

A task being large, many-file, expensive, or described as complex does not by itself justify delegation. Start with the smallest useful active set and grow only when another distinct responsibility becomes ready and remains worth delegating.

A single delegated responsibility may remain on the compact path. Compile `team-plan.md` only when two or more delegated responsibilities are concurrently unresolved, or delegated outputs need non-trivial dependency or integration order that must remain explicit across attempts.

## Preserve task truth

When an accepted user plan, another trusted Skill, or an upstream workflow already defines goal, decomposition, dependencies, outputs, business acceptance, or quality gates, preserve that truth. Orchestrate may assign owners, select specialist profiles, control useful concurrency, and enforce its writer/lifecycle boundaries. It must not silently replace the upstream domain plan.

Before delegation, identify the material obligations that must survive decomposition. Each obligation must remain covered by a delegated responsibility or an explicit main-session integration or verification responsibility. Cross-responsibility seams remain real work even when no child owns them.

A structurally valid graph does not prove semantic coverage. If decomposition loses an already-known requirement, repair the decomposition in the main session. Use the `contract` blocker only when required task truth is genuinely missing, contradictory, or underspecified.

## Select capability by the unresolved need

Use Reader for narrow read-only factual work such as bounded repository traces, call mapping, test mapping, or focused evidence collection.

Use Worker when behavior, invariants, scope, acceptance, and material decisions are already settled and the remaining work is bounded implementation inside explicit write authority.

Use Investigator for broader read-only technical exploration and synthesis when semantics are already stable and no material decision remains unresolved.

Use Solver when material judgment is coupled to implementation and cannot be separated safely from the writing work.

Use Advisor for a demanding read-only judgment or the fresh independent review required by `final-review.md`.

When the current main session already has sufficient Sol capability, it may keep ordinary material judgment or judgment-coupled writing instead of creating a redundant Sol child. This optimization never replaces a required fresh independent Final Review.

Failure does not define a model ladder. A weak Luna result, one failed test, low confidence, or task size does not automatically route work to Terra or Sol. Diagnose the unresolved blocker and route by the capability still needed.

## Responsibility semantics

Every delegated child owns one stable WorkUnit responsibility, not the raw user request. Before creating an ExecutionBinding, the main session must have enough truth to establish:

```text
observable goal and output
intent: inspect | implement | verify | review
scope and forbidden scope
mutation-authority ceiling
interfaces and invariants that must remain true
material decision boundary
acceptance condition
valid evidence that should be reused
stop boundary for contract, judgment, investigation, stalled, scope, or safety blockers
```

Those semantics are serialized only through `responsibility-packet.md`. Do not maintain another packet schema here.

A child cannot widen scope, permission, mutation authority, user intent, external impact, acceptance, or its own role. Writable Host permissions do not create mutation authority. Read-only roles never gain write authority from the filesystem environment.

Accepted prior evidence may be reused when still valid. `handoff.md` may carry compact main-session-accepted facts and references when this prevents meaningful repeated discovery. Raw child reasoning, unverified claims, or artifact-shaped output never becomes inherited task truth automatically.

## Child return

Keep the child return compact:

```text
status: complete | blocked
summary
files_changed, if any
verification
new_evidence
remaining_problem
blocker: none | contract | judgment | investigation | stalled
material_decisions, if any
```

A child result is a claim. The main session verifies actual artifacts and relevant checks before accepting the WorkUnit or reusing its evidence elsewhere.

## Ready frontier and concurrency

A responsibility is ready only when it can make meaningful progress now and delegation still adds value. With TeamPlan, structural dependency readiness comes from the validated graph; semantic readiness remains a main-session judgment.

Start a child only when the work has distinct ownership, does not duplicate an active owner, is semantically safe to run now, and fits current writer, permission, scope, compute, and Host-capacity boundaries.

Use progressive fan-out. Current V4 ceilings remain:

```text
initial managed children <= 2
normal managed children <= 3
Host capacity is an additional ceiling
```

These are ceilings, not targets. Spare capacity never justifies decorative work. Read-only independent work is the preferred place to use parallelism.

The canonical mutable workspace has one active managed writing actor. Different intended file paths alone do not prove safe parallel writes because shared APIs, schemas, migrations, lockfiles, generated outputs, build artifacts, persistent state, and other interfaces can couple the work. Writer authority is enforced by the current WriterLease contract.

Do not busy-poll or create a private scheduler. The deterministic V4 scheduler owns capacity, backpressure, ready-frontier admission, and coordinated critical-path ordering.

## Blockers and rerouting

Use the current blocker vocabulary:

```text
contract
judgment
investigation
stalled
```

`contract` means required task truth is missing or contradictory. `judgment` means a material decision remains. `investigation` means broader read-only evidence gathering is useful after semantics stabilize. `stalled` means the same responsibility is not progressing without one of the preceding blocker types.

Recovery mechanics, same-child correction, fresh-attempt limits, UNKNOWN handling, and main-session takeover belong to `recovery.md`. Routing decides only which capability the unresolved responsibility now needs.

## Phase changes

When an accepted result becomes input to a materially different phase, promote only main-session-accepted task truth, decisions, constraints, and still-valid evidence. Reassess goal, obligations, scope, authority, dependencies, acceptance, and useful delegation for the new phase.

If a WorkUnit's goal or output materially changes, create a new WorkUnit identity. Do not repurpose the old identity merely to preserve history or bypass recovery limits.

## Completion

The main session owns integration and final acceptance. Host completion creates candidate evidence; it does not accept a WorkUnit or unlock dependencies by itself.

Before Candidate Ready, verify that every material obligation is satisfied or explicitly unresolved, cross-responsibility seams are covered, the integrated deliverable supports the completion claim, and relevant deterministic or reproducible checks have run.

After Candidate Ready, apply `final-review.md` when its consequence-based triggers require a fresh independent second judgment. Model agreement alone is not verification.
