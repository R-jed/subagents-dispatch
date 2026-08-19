# Responsibility Packet Projection

This file defines the compact prompt shape for one selected delegated responsibility. It is a serialization projection of the responsibility semantics owned by `routing.md`; it does not create a second task state, scheduler, authority model, or acceptance model.

Use it only after Main has decided that delegation adds value and selected the role under `routing.md` and `policy.json`. A small Main-only task needs no packet.

For an ordinary single delegated responsibility, send the smallest self-contained packet that preserves all material truth:

```text
OBJECTIVE
<observable outcome and why this responsibility exists>

OWNERSHIP
scope: <exact read/write scope>
mutation_authority: none | declared-output-only | bounded-source-write
<unit/task identity only when the runtime already assigned it>

INTERFACES
<interfaces and invariants that must remain true>
decision_rights: <material choices this child may make, or none>

CONSTRAINTS
<settled constraints and excluded scope>
valid_evidence: <accepted facts/refs that remain valid, or none>
do_not_redo: <accepted discovery that must not be repeated, or none>
stop_when: <contract, judgment, investigation, stalled, scope, or safety boundary>

VERIFICATION
acceptance: <observable acceptance condition>
checks: <exact checks/evidence expected from this responsibility>
<integration_after only when dependency order materially matters>
```

Request the normal compact return defined by `routing.md`: status, summary, changed-file refs when applicable, verification, new evidence, remaining problem, blocker, and material decisions when applicable. Child output remains a claim until Main verifies the actual artifact and relevant checks.

Do not add empty ceremony. Omit optional lines that have no task meaning. Do not omit a material invariant, decision boundary, mutation boundary, accepted evidence dependency, or acceptance condition merely to shorten the packet.

When several delegated responsibilities remain unresolved concurrently, or machine-checkable dependency/integration order becomes material, use `team-plan.md` for graph truth and place the relevant TeamPlan identity/dependency facts into the same five sections. When recovery state matters, use `recovery.md`; do not invent retry semantics inside the packet.
