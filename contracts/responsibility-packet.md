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
    "interfaces": ["public API users.list"],
    "invariants": ["existing pagination behavior remains stable"],
    "decision_boundary": "Escalate any public API behavior change to the main session."
  },
  "constraints": {
    "forbidden_scope": [],
    "accepted_evidence_refs": ["src/api/users.py:list_users"],
    "do_not_redo": ["baseline pagination call mapping"],
    "evidence_boundary": "Use only supplied or independently inspected evidence for this WorkUnit; report uncertainty to the main session.",
    "delegation_boundary": "Do not create or control further subagents.",
    "stop_boundary": "Stop and report contract, judgment, investigation, stalled, scope, or safety blockers to the main session."
  },
  "verification": {
    "acceptance": "the relevant contract is evidenced"
  }
}
```

`team_plan_revision` is retained only as a V4 RC compatibility field described by `team-plan.md`. New WorkGraphs normally keep it `null`. A positive value from compatible pre-release state carries no dependency, routing, integration-order, retry-budget, ownership, or acceptance authority. WorkGraph and WorkUnit remain the responsibility-structure truth. A retry keeps the same stable `unit_id` and receives a new `execution_id` and `attempt_no` under the existing recovery rules.

The WorkUnit may persist a bounded `responsibility_context` containing the concrete interfaces, invariants, decision boundary, accepted evidence references, discovery that should not be repeated while still valid, and the stop boundary. `scripts/work_graph_v4.py` constructs this context for current V4 WorkUnits. Any managed spawn requires a complete validated context and fails closed if it is missing or malformed.

`accepted_evidence_refs` contain only main-session-accepted references safe for the assigned child to reuse. When complete evidence provenance would be too large for the responsibility record, use the Evidence Artifact and Handoff Capsule owners and carry only the narrow accepted refs needed by this responsibility. The record never promotes raw child claims, transcripts, or unverified output into task truth.

`do_not_redo` suppresses repeated discovery only while the referenced evidence remains valid. It never prevents verification required by the current responsibility or reuse after relevant evidence has become stale.

The record does not create a second task state, authority model, scheduler, acceptance model, evidence store, or retry protocol. Runtime identity and authority facts come from persisted V4 state. `scripts/managed_execution_v4.py` implements this exact record and deterministically renders it as the managed Host `message`.

Do not maintain another child-packet template in `routing.md`, `team-plan.md`, Agent profiles, or Skills. When a responsibility needs more task meaning, first represent that meaning in canonical WorkUnit/routing truth and then project the relevant fields through this record instead of inventing another wire format.

Child results use the compact return semantics owned by `routing.md`. A child result remains a claim until the main session verifies the actual artifact and relevant evidence.
