# Responsibility Record

This file owns the one serialized responsibility record sent to a managed child. `routing.md` owns delegation value, role selection, semantic coverage, and the meaning of the responsibility. This file defines how that truth is represented for one concrete ExecutionBinding.

The record has exactly five top-level sections:

```json
{
  "objective": {
    "intent": "inspect",
    "goal": "trace the current API contract",
    "output": "bounded evidence for the main session"
  },
  "ownership": {
    "unit_id": "U1",
    "execution_id": "exec-1",
    "attempt_no": 1,
    "team_plan_revision": null,
    "mutation_authority": "none",
    "write_scope": []
  },
  "interfaces": {
    "decision_boundary": "Do not widen scope, change architecture, or reinterpret acceptance without the main session."
  },
  "constraints": {
    "forbidden_scope": [],
    "evidence_boundary": "Use only supplied or independently inspected evidence for this WorkUnit; report uncertainty to the main session.",
    "delegation_boundary": "Do not create or control further subagents."
  },
  "verification": {
    "acceptance": "the relevant contract is evidenced"
  }
}
```

For one delegated responsibility with no delegated dependency, `team_plan_revision` is `null`. When TeamPlan is active, the same field carries the positive revision that already owns the multi-responsibility structural truth. A retry keeps the same stable `unit_id` and receives a new `execution_id` and `attempt_no` under the existing recovery rules.

The record does not create a second task state, authority model, scheduler, acceptance model, evidence store, or retry protocol. Runtime identity and authority facts come from persisted V4 state. `scripts/managed_execution_v4.py` implements this exact record and deterministically renders it as the managed Host `message`.

Do not maintain another child-packet template in `routing.md`, `team-plan.md`, Agent profiles, or Skills. When a responsibility needs more task meaning, first represent that meaning in the canonical WorkUnit/routing truth and then project the relevant fields through this record instead of inventing another wire format.

Child results use the compact return semantics owned by `routing.md`. A child result remains a claim until the main session verifies the actual artifact and relevant evidence.
