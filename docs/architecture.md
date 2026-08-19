# Architecture

subagents-dispatch V4.0.0 is a bounded orchestration layer over Codex Native Subagents. Codex remains the Agent runtime. The project does not add a daemon, event bus, persistent scheduler database, private Agent runtime, automatic worktree manager, or nested managed delegation.

The user-facing main session owns user intent, authorization, decomposition, integration, WorkUnit acceptance, lifecycle control decisions, and the final response. Native Host observations own Agent lifecycle truth.

The normative V4 architecture freeze is `docs/v4/architecture.json`. This document is the human-readable owner map for that active design.

## Public surface

V4 exposes exactly two explicit Skills:

```text
Orchestrate
Doctor
```

`Orchestrate` owns plan-only routing, delegated execution, status, correction, continuation, interruption, cancellation, takeover, integration, and consequence-based independent review. `Doctor` diagnoses the installed product across Plugin package, Managed Agents, Host integration, Orchestration state, and Legacy compatibility. Repository publication, CI, H00-H20 campaigns, calibration, experiments, and release-candidate evidence remain maintainer workflows outside public Doctor.

Retired V3 public orchestration Skills are historical compatibility material only and are not V4 entrypoints.

## Semantic and capability model

The semantic model is deliberately small:

```text
main session
Work
Review
```

Physical Agent profiles remain separate capability and authority boundaries:

| Profile | Model / effort | Ordinary authority | Semantic role |
| --- | --- | --- | --- |
| Reader | Luna Max | none | Work |
| Worker | Luna Max | bounded-source-write | Work |
| Investigator | Terra High | none | Work |
| Solver | Sol High | bounded-source-write | Work |
| Advisor | Sol High | none | Review |

V4.0.0 never changes reasoning effort dynamically. Routing chooses among the five fixed profiles. Read-only and writable profiles remain physically distinct because mutation authority and sandbox behavior are real Host boundaries.

## Active contract owners

The current Orchestrate reasoning path uses one V4 contract generation:

```text
contracts/policy.json
-> five fixed managed profile identities, delegation invariants, review triggers

contracts/routing.md
-> delegation value, capability selection, responsibility semantics, semantic coverage

contracts/responsibility-packet.md
-> the one serialized five-section responsibility record

contracts/team-plan.md
-> multi-responsibility dependency and integration truth

contracts/guardrails.md
-> authority, depth, mutation, writer, consent and external-action boundaries

contracts/handoff.md
-> optional main-session-accepted evidence bridge between responsibilities

contracts/evidence-artifact.md
-> complete inspectable evidence provenance when compact references are insufficient

contracts/interaction.md
-> user-visible Orchestrate controls

contracts/recovery.md
-> current WorkUnit / ExecutionBinding lifecycle and bounded recovery

contracts/final-review.md
-> exact-candidate independent review
```

Other supporting contracts may refine current V4 boundaries when referenced by an active owner. Historical V3 state or receipt semantics do not override the V4 state machine or the two-Skill product surface. Historical RC stage specifications live under `docs/history/`.

## Runtime owners

```text
docs/v4/architecture.json
-> frozen V4 product and safety invariants

scripts/orchestrate_v4.py
-> Orchestrate admission, plan-only, routing and control facade

scripts/dispatch_state_v4.py
-> bounded session-scoped V4 state, validation and Host reconciliation

scripts/work_graph_v4.py
-> WorkUnit truth, bounded responsibility context, single-WorkUnit installation, dependency and acceptance transitions

scripts/scheduler_v4.py
-> wakeup-driven admission, ready frontier, Host capacity, fanout and backpressure

scripts/dispatch_control_v4.py
-> PendingControl authorization, PreToolUse consumption and PostToolUse acknowledgement

scripts/execution_lifecycle_v4.py
-> ExecutionBinding allocation and same-child lifecycle operations

scripts/writer_lease_v4.py
-> canonical WriterLease ownership and settlement

scripts/managed_execution_v4.py
-> exact five-section responsibility projection and managed spawn payload

scripts/host_evidence_v4.py
-> paired current Host lifecycle/capacity evidence

scripts/host_capabilities.py
-> Host capability normalization and exact exposed tool-identity Hook coverage

scripts/orchestration_guard.py
-> active V4 lifecycle, peer-message containment and Host-observation Guard

hooks/hooks.json
-> authoritative installed lifecycle Hook manifest for the exact real-Host candidate

docs/v4/host-smoke.json
-> real Host release gate
```

## Single responsibility and coordinated work

Zero delegated responsibilities create no orchestration state.

One dependency-free delegated responsibility may use one WorkUnit with `team_plan_revision = null`. It still uses the same ExecutionBinding, PendingControl, WriterLease when writable, Host evidence, and scheduler/admission owner. This is a smaller shape inside the V4 runtime, not a second runtime.

When two or more delegated responsibilities remain concurrently unresolved, or dependency/integration order becomes materially important, TeamPlan supplies the positive revision and Work Graph structural truth. The same scheduler remains the sole admission owner.

## WorkUnit and responsibility context

A WorkUnit records stable responsibility and acceptance truth. An ExecutionBinding records one concrete Agent attempt and route. This separation lets one responsibility survive retry, reroute, same-child correction, interruption, or main-session takeover without making profile identity part of responsibility identity.

Current WorkUnits created for managed delegation carry one bounded `responsibility_context` containing concrete interfaces, invariants, the main-session decision boundary, accepted evidence references, valid discovery that should not be repeated, and the stop boundary. The persisted schema keeps this field optional so pre-closure V4 state can still be diagnosed, but any managed spawn requires a complete valid context and fails closed without it.

`managed_execution_v4.py` projects that state into exactly five top-level sections: `objective`, `ownership`, `interfaces`, `constraints`, and `verification`. This is the only child wire representation. Handoff Capsules and Evidence Artifacts remain main-session-owned provenance mechanisms and are referenced narrowly when useful; they do not create another assignment schema.

Host `COMPLETED` means an execution produced a candidate result. It maps to `WorkUnit.RESULT_READY`. Main-session verification and explicit WorkUnit acceptance are required before the unit becomes `ACCEPTED`. Dependencies unlock only from `ACCEPTED`.

One unchanged WorkUnit may use at most two fresh Agent attempts. A focused same-child `FOLLOWUP` stays inside one ExecutionBinding and has its own bounded correction budget. `CONTINUE` resumes the same interrupted ExecutionBinding and does not consume that correction budget.

## Scheduling

Scheduling is wakeup-driven reconciliation. A wakeup means Host or user state may have changed; it is never lifecycle truth by itself.

V4 policy remains:

```text
initial managed children <= 2
normal managed children <= 3
Host capacity is an additional ceiling
longer downstream critical path wins coordinated ties before unit id
>= 2 RESULT_READY/VERIFYING units stops fresh fanout growth
empty capacity never justifies decorative work
```

For one WorkUnit, the same scheduler naturally degenerates to one ready candidate without DAG ceremony. Host capacity still limits admission.

## PendingControl

Managed lifecycle operations use a single-use PendingControl. The correctness-bearing unresolved states remain `PREPARED`, `IN_FLIGHT`, and `UNKNOWN`; the current schema also retains existing terminal vocabulary until real Host evidence and a later consumer audit justify simplification.

Supported operations are `SPAWN`, `FOLLOWUP`, `CONTINUE`, and `INTERRUPT`. A PendingControl binds the WorkUnit/ExecutionBinding identity, applicable TeamPlan revision, execution control epoch, optional WriterLease epoch, exact lifecycle target, canonical tool-input digest, writer effect, and one Host `tool_use_id`.

`PreToolUse` consumes exactly one matching prepared control. PostToolUse may acknowledge that exact in-flight control only when the real Host event semantics prove the required success/failure distinction. Ambiguous acknowledgement remains fail closed. Missing PostToolUse never becomes an inferred acknowledgement. H07 and H08 are explicit feasibility gates for outcome reliability and message representation before managed delegated execution can be trusted on the target Host.

## WriterLease

V4.0.0 supports one canonical managed writer at a time. `WriterLease` is an orchestration mutual-exclusion permit, not an operating-system filesystem lock.

Writing SPAWN, FOLLOWUP, and CONTINUE require the matching execution-owned WriterLease before Host activation. A valid lifecycle acknowledgement applies the authorized writer effect in the same state transaction as the PendingControl acknowledgement.

Interrupt acknowledgement alone never releases or transfers a writer. Release or transfer requires current-generation Host settlement evidence, matching lease and control epochs, no unresolved PendingControl, and current managed lifecycle Guard coverage evidence. `UNKNOWN` blocks conflicting managed mutation and never expires automatically.

Main-session integration writes use the same WriterLease abstraction. User takeover cannot bypass writer settlement.

## Host observations and exact tool identity

V4 state normalizes only lifecycle evidence needed by orchestration. Every observation is captured against an execution identity and control epoch, with WriterLease epoch when applicable. Observations captured against an older generation are discarded.

Within one control epoch, delayed Host evidence must not reactivate a settled execution. Legal same-child reactivation first passes through FOLLOWUP or CONTINUE, which advances the control epoch, then fresh Host evidence may establish RUNNING for that new generation.

Host uncertainty stays explicit. Missing or conflicting identity evidence produces `UNKNOWN`; it never authorizes replacement work, writer transfer, or dependency acceptance.

Host capability normalization keeps three distinct facts: the model-visible collaboration identity, the semantic collaboration tool, and the exact Hook-serialized `tool_name`. Bare V2 identities map to themselves. A default namespace model identity such as `collaboration.spawn_agent` maps to semantic `spawn_agent` and the flattened Hook identity `collaborationspawn_agent`. Unknown namespace or flattening is unclassified and fails execution readiness until Host adaptation. Coverage of one identity never proves coverage of another mapping.

If the Host exposes `send_message`, every model-visible peer-message identity must map to an exact PreToolUse Hook identity. Managed children are blocked before peer delivery. Root/non-managed messaging remains outside PendingControl. Peer messages never grant authority, transfer WriterLease, satisfy acceptance, or unlock dependencies.

## Lifecycle Guard and release gate

The exact V4 real-Host candidate uses the default Plugin Hook path `hooks/hooks.json`:

```text
PreToolUse   -> authorize managed lifecycle calls, bind Host observation, block managed-child peer messaging
PostToolUse  -> bind exact lifecycle/Host observation results without inventing missing Host truth
SubagentStop -> prevent autonomous continuation of managed leaf Agents
```

`docs/v4/hooks.json` is a non-runtime campaign reference copy. Tests require its `hooks` object to stay exactly equivalent to the active manifest, and package integrity protects both files during this campaign window. Runtime discovery, Doctor diagnostics, H00 evidence, and release authority bind to `hooks/hooks.json`.

Repository tests can validate state machines and Hook scripts, but cannot prove the target Codex Host build loads the active Hook source, trusts it, invokes every exposed identity with the expected serialized `tool_name`, or supplies reliable outcome semantics.

`docs/v4/host-smoke.json` therefore remains a blocking V4.0.0 release contract. H00-H20 must bind direct Host evidence to the exact candidate before publication. H00 first proves the active `hooks/hooks.json` digest and trust state. The first feasibility wave then settles identity coverage, PostToolUse outcome reliability, message representation, profile selectors/tool surface, peer-message containment, and assignment completeness before spending the full campaign budget.

There is no post-campaign Hook-copy or promotion step. Any material candidate mutation after Host evidence invalidates the affected evidence and requires the relevant probes to be repeated.

## Final Review

After the main session establishes Candidate Ready, `contracts/final-review.md` decides whether consequence-based triggers require a fresh independent Advisor review of the exact candidate.

Git-backed deliverables use `scripts/review-artifact.py`; non-Git deliverables use a deterministic SHA-256 serialization boundary. Any material candidate mutation invalidates the previous verdict.

## Migration

V3.x live state is legacy evidence and is never silently rewritten into V4 state. Unresolved legacy ownership, active execution, pending takeover, corrupt state, V4 `WriterLease.UNKNOWN`, or unresolved PendingControl remains fail closed. Terminal proven-owned legacy state may be explicitly cleaned through supported maintenance paths.

The ordinary V4 state remains bounded, temporary, session-scoped, and outside the project working tree. It stores coordination metadata only, not raw prompts, child transcripts, reasoning traces, source copies, or full Host output.

`dispatch_state.py`, `spawn_guard.py`, and legacy migration remain compatibility owners while proven consumers remain. `spawn_guard.py` is retained compatibility code and is not the active Hook implementation for the exact V4 real-Host candidate. The shared storage primitives are not extracted from the V3 module before the Host feasibility gate because doing so would widen the state-storage regression surface.

## V4.0.0 exclusions

The release intentionally excludes dynamic effort routing, nested managed delegation, autonomous peer authority transfer, daemon scheduling, persistent orchestration databases, automatic worktree management, parallel isolated managed writers, and cross-WorkUnit Agent reuse by default.

These exclusions keep V4 centered on verifiable native lifecycle control, bounded delegation, and one-writer correctness.
