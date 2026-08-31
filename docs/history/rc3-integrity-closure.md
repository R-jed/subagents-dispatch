> Historical archive. This document records a superseded design/review state. It is not a current V4 contract, implementation guide, release gate, or source of runtime authority. Use current `contracts/`, current non-history `docs/`, and `docs/v4/` for present behavior.

# Native Core V4 RC3 Integrity Closure

This contract freezes the remediation scope for `v4/rc3-integrity-closure`.

## Scope

RC3 closes five integrity boundaries without widening the public product surface:

1. Managed execution contract
2. State truth kernel
3. Scheduler and path authority
4. Host evidence authority
5. Release identity closure

The public product remains `Orchestrate` and `Doctor`. The semantic roles remain Main, Work, and Review. Fixed execution profiles remain Luna Max, Terra High, and Sol High with the existing Reader, Worker, Investigator, Solver, and Advisor mappings.

## Managed execution contract

For every managed spawn, the actual Host invocation MUST be derived from the persisted ExecutionBinding and the authoritative profile contract.

The following values are authority-bearing and MUST NOT be freely supplied by an orchestration caller:

- `task_name`
- `agent_type`
- `fork_turns`
- effective model
- effective reasoning effort

Managed spawns MUST use `fork_turns = "none"`.

The managed assignment message MUST be derived from the current WorkUnit and ExecutionBinding and carry enough fresh-context information to preserve goal, scope, authority, acceptance, evidence boundary, and no-delegation constraints.

The Guard MUST independently verify the Host input against the same authoritative contract before the lifecycle call is allowed.

## State truth kernel

For any WorkUnit, the execution with the greatest valid `attempt_no` is the current correctness-bearing execution. Older attempts lose FOLLOWUP, CONTINUE, ACCEPT, and equivalent correctness authority once a newer attempt exists.

A persisted `ACCEPTED` WorkUnit MUST resolve to one current producing execution that satisfies the acceptance lifecycle and control-epoch contract and has no unresolved PendingControl that invalidates acceptance.

Dependency readiness MUST only consume an `ACCEPTED` state that passes the full persisted invariant.

Lifecycle acknowledgement identity MUST bind the PendingControl identity to the observed Host invocation identity. Reuse of a Host tool-use identifier across distinct controls MUST NOT make an old acknowledgement authoritative for a new control.

Duplicate delivery of the exact same successful PostToolUse event MUST be idempotent at the production Guard boundary.

## Scheduler and path authority

Until confirmed accepted progress exists, the managed initial fan-out ceiling remains two children. The presence of an ExecutionBinding alone does not end the initial fan-out phase.

After accepted progress, normal managed concurrency may rise to the frozen product ceiling of three, subject to Host capacity, backpressure, WriterLease, and ready independent work.

Repository-relative write scopes MUST have one canonical lexical representation before equality, overlap, subset, or forbidden-scope checks. Platform-specific aliases that identify the same effective filesystem target MUST NOT create distinct authority scopes.

## Host evidence authority

Ordinary orchestration callers MUST NOT be able to manufacture authoritative Host evidence by supplying arbitrary lifecycle strings, boolean trust claims, digests, or evidence references.

Authoritative Host evidence MUST originate from an accepted Host/Hook observation path and bind enough identity to correlate the evidence to the current orchestration, control, execution, and candidate/runtime context.

WriterLease settlement and equivalent authority transitions MUST consume authoritative Host evidence rather than caller assertions.

Unknown or unsupported Host capability surfaces remain fail-closed.

## Release identity closure

There is one authoritative release predicate.

A Native Core V4 candidate is release-ready only when all required repository health, package integrity, production Hook identity, profile-contract identity, Host campaign evidence, candidate identity, and required Final Review conditions are simultaneously satisfied.

Host-smoke results and Final Review receipts bind an exact candidate identity. They SHOULD remain external release evidence when committing them would mutate the candidate they are intended to prove.

Any candidate mutation after required Final Review invalidates the prior verdict.

## RC3 stop conditions

RC3 MUST stop and return to architecture review if the available Host/Hook surface cannot provide enough identity and provenance to prevent ordinary orchestration code from manufacturing WriterLease settlement evidence.

RC3 does not add dynamic reasoning-effort routing, nested managed delegation, additional public Skills, speculative execution, or a background scheduler daemon.
