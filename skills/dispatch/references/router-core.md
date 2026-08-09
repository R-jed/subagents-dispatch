# Router Core

This is the runtime routing contract for subagents-dispatch.

The main session is the team leader. It understands the user's goal, keeps work that belongs in Main, assigns distinct responsibilities to specialist Agents when that helps, and owns integration and acceptance.

The product goal is simple: delegate only when doing so improves the task, use Luna for clear repeatable bounded work, use Sol where demanding or material judgment belongs, use Terra for bounded read-heavy technical investigation, and avoid repeated or decorative Agent work.

Do not build a model ladder, fixed team size, or Agent pipeline before understanding the task.

`team-plan.md` owns multi-responsibility dependency and integration truth. `recovery.md` owns native attempt lifecycle and bounded recovery. `handoff-capsule.md` owns compact accepted-evidence transfer between responsibilities. This file owns delegation value, role selection, responsibility semantics, semantic coverage closure, phase-transition recompilation, and the Main-level ready frontier.

## 1. Minimal task state

Track one compact task state per genuinely distinct unresolved responsibility:

```text
WORK ITEM
outcome
owner: main | reader | worker | solver | investigator | advisor
write: yes | no
material_judgment: none | separable | coupled
acceptance
valid_evidence
current_failure
blocked_by: none | contract | judgment | investigation | stalled
```

Add another work item only when it represents a genuinely distinct unresolved responsibility. Do not duplicate work that valid evidence already satisfies or another active owner already holds.

A single delegated responsibility may remain on this compact path. When two or more delegated responsibilities are concurrently unresolved, or delegated outputs need non-trivial machine-checkable dependency/integration order, compile `team-plan.md` before further dispatch.

## 1A. Preserve upstream workflow ownership

When another active Skill, an accepted user plan, or another trusted upstream workflow already defines any of the following, treat those definitions as task truth unless the user or a real evidence-backed blocker requires them to change:

```text
goal
decomposition
stage order
dependencies
required outputs
business acceptance
quality gates
```

subagents-dispatch may assign owners, choose specialist roles, decide useful concurrency, enforce write isolation, and choose integration timing around that upstream workflow. It does not silently create a competing domain plan.

Do not skip an upstream gate, reorder an upstream dependency, widen the required output, or redefine domain semantics merely because a different decomposition would be easier to delegate. If the upstream contract is incomplete or contradictory, classify the blocker as `contract` and return the missing truth to Main instead of inventing a replacement workflow.

When the upstream workflow already maintains a useful plan or ledger, reuse it as the coordination source of truth. Do not create a second persistent state source just for subagents-dispatch.

## 1B. Preserve semantic coverage through decomposition

Before turning task truth into delegated responsibilities, identify the material obligations that must survive decomposition. A material obligation is any requirement, invariant, acceptance condition, required decision, or other task truth whose omission would materially change the requested outcome. Derive these obligations from the current task instead of maintaining a fixed domain taxonomy.

After decomposition, every material obligation must remain covered by at least one of these ownership forms:

```text
one delegated responsibility
several cooperating responsibilities
an explicit Main-owned integration or verification responsibility
```

A material obligation may span several units. When acceptance depends on a transition or relationship between their outputs, treat that seam as semantic work that still needs an owner. Main owns the seam by default unless delegating it is itself useful, distinct, and safe.

Do not create a decorative child solely to make every seam appear as a TeamPlan unit. Main-owned semantic integration is a normal responsibility.

A structurally valid TeamPlan, dependency DAG, or integration order does not by itself prove semantic coverage. If decomposition drops a material obligation or leaves a material seam ownerless, classify the problem as `contract`, repair task truth/ownership, and do not claim the affected work is ready or complete.

## 2. First question: does delegation help?

Zero children is normal.

Keep work in the main session when a child would mostly duplicate context, add handoff overhead, or provide no useful isolation, parallelism, capability uplift, read-heavy investigation, or independent judgment.

A task being large, many-file, expensive, or "complex" does not by itself justify delegation. Project policy does not map task size to a fixed child count or ordinary numeric child ceiling.

## 3. Select by capability need

### Narrow read-only factual work

If the missing result is bounded inspectable evidence such as a focused repository trace, call mapping, test mapping, or narrow factual lookup:

```text
-> Luna Reader
```

### Writing with behavior already decided

If the desired behavior, invariants, scope, and acceptance are already clear, and remaining discretion is local, clear, and repeatable implementation detail:

```text
-> Luna Worker
```

The key test is whether Luna mainly answers "how do I implement the already-decided result?"

A writable contract alone does not make work Luna-suitable. If implementation is expected to require consequential architecture, compatibility, state, or cross-module semantic choices, use the Sol path.

### Demanding or material judgment before writing

If architecture, behavior, compatibility, risk, or difficult technical reasoning requires consequential judgment before implementation:

```text
-> main session when it already has sufficient Sol capability
-> otherwise Sol Advisor
```

### Writing with judgment coupled to implementation

If demanding or material semantic decisions cannot be safely separated from implementation and must be made while inspecting or changing the artifact:

```text
-> main session when it already has sufficient Sol capability
-> otherwise Sol Solver
```

Do not create Advisor -> Luna -> Advisor loops merely to avoid the Solver lane.

### Bounded read-heavy technical investigation

If semantic intent is already stable, no material decision remains, and the task benefits from broader read-only exploration, technical synthesis, or processing a larger supporting context than a narrow Reader task:

```text
-> Terra Investigator
```

Terra is an investigation/value lane. It is not the automatic destination for hard work and it is not an escalation rung above Luna.

Demanding, ambiguous, multi-step technical reasoning that still requires material judgment belongs on the Sol path. Weak Luna output, task size, one failing test, or low confidence does not justify Terra by itself.

## 4. Main-session Sol dedup is an optimization

Main-session model identity never changes authority. It is consulted only when material judgment already requires Sol capability and trusted current-session metadata is already available or inexpensive to obtain.

The policy-owned reference role is defined in `../../../policy-contract.json`. `../../../scripts/runtime-evidence.py` can normalize exact model/effort metadata when this optimization matters.

```text
covered
-> keep ordinary judgment or judgment-coupled writing in main

uncovered
-> Advisor or Solver when delegation helps

unknown
-> do not affect routine bounded work
-> use the normal Sol path only when material judgment genuinely requires it
```

Missing telemetry is allowed to remain missing. Do not interrogate runtime metadata for a routine Luna or Terra responsibility simply to manufacture certainty.

A covered main session never replaces a required fresh independent Final Review.

## 5. Responsibility packet

A child receives one bounded responsibility, not the raw user task.

Use the smallest packet that makes the responsibility safe and self-contained:

```text
TEAM PLAN REVISION, when applicable
UNIT ID
TASK ID
OUTCOME
INTENT: inspect | implement | verify | review
READ / WRITE SCOPE
MUTATION AUTHORITY: none | declared-output-only | bounded-source-write
INTERFACES AND INVARIANTS
DECISION RIGHTS
ACCEPTANCE
VALID EVIDENCE / DO NOT REDO
HANDOFF CAPSULE, when useful
CURRENT FAILURE, if any
INTEGRATION AFTER, when needed
STOP WHEN
```

`INTENT` states what kind of responsibility the child owns. `MUTATION AUTHORITY` states why it may change artifacts and how far that permission extends. A writable filesystem or broad sandbox never creates mutation authority by itself.

Default mutation authority:

```text
inspect -> none
verify -> none
review -> none
implement -> bounded-source-write only when the packet explicitly grants bounded source ownership
```

Use `declared-output-only` when a responsibility may create or update a named report, generated output, or other explicit deliverable without gaining general source-edit authority.

A Handoff Capsule is optional. Use it only when Main has already accepted evidence that would otherwise require meaningful repeated discovery. The capsule does not grant authority or transmit raw child reasoning. Its exact semantics live in `handoff-capsule.md`.

`INTEGRATION AFTER` is optional. It expresses integration order, not permission to execute through an unresolved semantic dependency.

If a responsibility cannot make safe progress until another work item establishes missing task truth, interface semantics, or required evidence, keep it off the ready frontier instead of using `INTEGRATION AFTER` as a shortcut.

Decision boundaries:

- Reader gathers narrow evidence and does not invent semantics or mutate source.
- Worker makes local implementation choices only within granted bounded-source-write authority; material semantic judgment returns to Main/Sol.
- Solver may make implementation-coupled material choices explicitly inside granted decision rights and mutation authority.
- Investigator performs bounded read-heavy technical investigation and synthesis after semantics stabilize; material judgment returns to Main/Sol.
- Advisor resolves one demanding/material judgment or performs fresh independent review and remains read-only.

Children do not widen scope, permission, mutation authority, user intent, external impact, or their own role.

## 6. Return packet

Keep child output compact:

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

A child report is a claim. Main verifies actual artifact state and relevant checks before acceptance.

Only after that verification may Main promote supported facts/evidence into a Handoff Capsule for another responsibility. A child does not author settled inherited truth for its peers.

## 7. Blocked work means reroute, not escalation

When work is blocked, diagnose what remains:

```text
contract
-> Main repairs missing task truth, scope, invariant, acceptance, or semantic coverage

judgment
-> Main or Sol resolves the demanding/material decision

investigation
-> Terra only when semantics are stable, the work remains read-only, and no material judgment is required

stalled
-> if the same role remains correct, allow at most one clean retry with a materially improved packet
-> otherwise reroute based on the real blocker
```

A failed Luna attempt never directly means "use Terra" or "use a stronger model."

`recovery.md` adds the execution-origin axis, same-Agent focused follow-up, unique task identity, UNKNOWN handling, and the two-Agent-attempt bound. Semantic reroute still follows the blocker classes above.

## 8. Adaptive scheduling

Main manages a ready frontier. Project policy does not define an ordinary numeric child ceiling or a target team size.

A responsibility belongs on the ready frontier only when it can make meaningful progress now. With TeamPlan, structural dependency readiness comes from the validated DAG; Main still decides semantic safety, semantic readiness, coverage, and delegation value.

Start a child only when all of the following are true:

```text
ready now
+ distinct ownership
+ non-duplicative
+ semantically independent from concurrently active work, or dependency order is explicit
+ delegation adds useful parallelism, isolation, capability, or independence
+ expected value exceeds handoff / compute / integration cost
+ safe under writer, permission, scope, and external-impact boundaries
```

Filesystem isolation is necessary for simultaneous writers, but it is not sufficient to prove safe parallel work. Main must also establish semantic independence or an explicit dependency and integration order.

Treat responsibilities as semantically coupled when they can invalidate each other's assumptions through a shared API or schema, migration order, lockfile, generated artifact, build output, persistent state, external service, or another shared interface. Different intended file paths do not erase these dependencies.

Use progressive fan-out. Start with the smallest useful active set, then grow it only when the task justifies another ready responsibility.

```text
understand current work
-> start useful ready responsibilities
-> consume an exposed completion
-> verify and merge valid evidence
-> create/update a compact capsule only when it prevents meaningful repeated discovery
-> update semantic coverage and the ready frontier
-> start another child only if a new responsibility is now ready and still worth delegating
```

Do not speculate ahead by spawning work that depends on unresolved decisions. Do not create multiple owners for the same unchanged responsibility unless independent cross-checking is itself an explicit requirement. Do not keep Agents busy merely because the host has spare capacity.

Native Codex capacity is the upper bound on concurrency, not a target. If the runtime exposes less capacity or only barrier-style completion, adapt to the observed host surface rather than simulating a scheduler with busy polling.

Read-only independent work is the preferred place to exploit parallelism. A canonical physical checkout has one active writing actor inside the current orchestration. Concurrent writers require genuinely isolated workspaces or worktrees plus semantic independence or explicit dependency/integration order.

For accepted outputs with `INTEGRATION AFTER`, Main remains the integration owner and applies them only after the named predecessor work items are accepted. TeamPlan integration order must respect all explicit dependencies. Do not integrate by completion time when dependency order says otherwise.

A downstream review or synthesis responsibility that depends on an integrated deliverable is not semantically ready merely because all named predecessor units are accepted. Main must first materialize and verify the integrated deliverable that responsibility is supposed to consume.

Empty capacity is never a reason to start Solver, Advisor, or Investigator. Repeated expensive parallel or serial calls that materially expand compute require consent under `guardrails.md`.

Process an exposed child completion when useful instead of imposing an artificial wave barrier. Reuse valid evidence and accepted capsules to suppress repeated discovery, but revalidate any capsule whose evidence may have become stale.

## 8A. Recompile at material phase or authority transitions

When an accepted result becomes input to a materially different phase, intent, or authority envelope, do not mechanically continue the old responsibility graph.

Treat the accepted result and still-valid evidence as upstream task truth, then reassess the current state:

```text
outcome
material obligations
scope and authorization
decision rights
mutation authority
dependencies
acceptance
valid evidence
```

Compile fresh responsibilities from that state. If an old unit's goal or output would materially change, use a new unit ID instead of repurposing the old responsibility. Preserve still-valid accepted evidence through normal packets or a Handoff Capsule when useful.

A prior phase being implementation-ready, remediation-ready, review-ready, or otherwise ready for a later action does not grant the authority required for that later action. Authority comes from current user/task truth and `guardrails.md`.

## 9. Completion

Main owns integration and final acceptance.

Normal completion requires the actual requested deliverable plus relevant deterministic or reproducible verification. When several delegated outputs are combined, Main integrates them in dependency-respecting order and verifies the resulting combined artifact, not only each isolated child result.

Before Candidate Ready, Main performs semantic coverage closure against current task truth:

```text
every material obligation is satisfied or explicitly unresolved
material cross-responsibility seams have an owner and accepted evidence
claimed completion is supported by the integrated deliverable
no obligation disappeared only because the task was decomposed or changed phase
```

Model agreement is not verification.

After Candidate Ready, apply `final-review.md` only when the final artifact's consequences require an independent second judgment.
