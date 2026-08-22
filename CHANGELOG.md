# Changelog

## [4.0.0] - Release candidate

### Public surface

- Reduce the public Skill surface to exactly `Orchestrate` and `Doctor`.
- Keep planning, execution, status, correction, continuation, cancellation, takeover, review and integration behind Orchestrate.
- Keep Doctor as the installed-product diagnosis and ownership-safe maintenance entry.

### Fixed execution profiles

- Reader and Worker: Luna Max.
- Investigator: Terra High.
- Solver and Advisor: Sol High.
- Dynamic reasoning-effort routing remains outside V4.0.0.

### Native Core runtime

- Use Codex Native Subagents as the only Agent runtime and lifecycle authority.
- Keep WorkUnit acceptance separate from ExecutionBinding and Host lifecycle.
- Keep `control_epoch` for stale-generation rejection without a persisted lifecycle authorization protocol.
- Keep WriterLease states `RESERVED`, `HELD`, `REVOKING`, `UNKNOWN`, and `RELEASED` for one canonical mutable workspace.
- Use one product managed-child safety ceiling of 4. Main owns dispatch judgment; fixed initial/normal fanout targets, automatic ranking and acceptance-backpressure authorization are removed.
- Let the Host own actual capacity. Explicit pre-materialization spawn rejection rolls back provisional activation without consuming a fresh attempt; ambiguous materialization becomes `UNKNOWN`.
- Replace fixed fresh-attempt and focused-followup budgets with evidence-gated recovery. Fresh retry requires a changed execution basis; same-child correction requires a new correction basis. Attempt and followup counts are diagnostic.
- Compact older safely settled execution attempts while retaining the current execution and any execution identity still required by a RELEASED WriterLease.
- Keep WorkGraph and WorkUnit state as the one responsibility/dependency structure for one or many units. `team_plan_revision` remains compatibility-only during the RC.
- Keep the one five-section responsibility record and bounded reusable accepted evidence context.
- Extract schema-neutral private state storage into `state_storage.py`; V4 state no longer imports the retired V3 orchestration engine.
- Isolate stale terminal V3 capsule cleanup in `legacy_state_cleanup.py` and remove the old Team Ledger from the V4 runtime package.

### Complexity reduction

- Remove the earlier lifecycle interception control plane from the active V4 runtime.
- Remove PendingControl, Guard receipts, capacity tokens, identity-normalization machinery and related release diagnostics.
- Remove semantic scheduler ranking, fixed fanout phases, fixed acceptance backpressure, and fixed recovery budgets from execution authorization.
- Do not replace that machinery with another persisted request/receipt control plane or scheduling database.
- Keep optional allowlisted rollout inspection only for recovery or validation when native Host evidence is insufficient.
- Remove the retired V3 orchestration state engine and its receipt/recovery accounting from the active V4 runtime surface.

### Managed child containment

- Managed child profiles request a leaf-style capability posture and instruct children not to create or manage further subagents.
- Treat profile settings as configured intent. Effective child collaboration containment and effective read-only permission are Host facts when release or concurrency depends on them.
- Behavioral read-only remains separate from Host-enforced sandbox truth. Configured read-only is not promoted to runtime proof without Host evidence.

### Product lifecycle

- Keep first-use managed-profile provisioning ownership-safe and return `RESTART_REQUIRED` when the current task cannot authoritatively observe newly created custom roles.
- Keep update check and explicit update as separate flows.
- Verify a newly installed package with package integrity, managed-profile reconciliation and the current Native Core Doctor contract before reporting update completion.

### Release status

- Repository and CI checks may complete before real Host evidence.
- V4.0.0 publication remains blocked until the exact candidate passes the N0-N8 Host campaign in `docs/v4/host-smoke.json`, fresh exact-candidate Final Review and candidate-bound release evidence verification.

Complete V3.x and earlier release history is preserved in [CHANGELOG_V3.md](CHANGELOG_V3.md).
