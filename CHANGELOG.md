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
- Keep initial managed fanout at most 2 and normal managed fanout at most 3, with known Host capacity able to lower the admission ceiling.
- Let the Host own actual capacity. Explicit pre-materialization spawn rejection rolls back provisional activation without consuming a fresh attempt; ambiguous materialization becomes `UNKNOWN`.
- Keep one focused same-child followup distinct from `CONTINUE` and fresh attempts.
- Require current-generation Host settlement before writer release or takeover. Interrupt return alone is insufficient.
- Keep one dependency-free delegated responsibility on the compact path with `team_plan_revision = null`; create TeamPlan only when coordination structure needs it.
- Keep the one five-section responsibility record and bounded reusable accepted evidence context.

### Complexity reduction

- Remove Plugin Hook lifecycle authority from the V4 correctness path.
- Remove PendingControl, Guard receipts, Hook-derived capacity tokens, Hook identity normalization and Hook-specific release diagnostics.
- Do not replace that machinery with OperationIntent/OperationReceipt or another persisted request/receipt control plane.
- Keep optional allowlisted rollout inspection only for recovery or validation when native Host evidence is insufficient.

### Managed child containment

- Managed child profiles disable child multi-agent capability and instruct leaf Agents not to create or manage further subagents.
- Behavioral read-only remains separate from Host-enforced sandbox truth. Configured read-only is not promoted to runtime proof without Host evidence.

### Product lifecycle

- Keep first-use managed-profile provisioning ownership-safe and return `RESTART_REQUIRED` when the current task cannot authoritatively observe newly created custom roles.
- Keep update check and explicit update as separate flows.
- Verify a newly installed package with package integrity, managed-profile reconciliation and the current Native Core Doctor contract before reporting update completion.

### Release status

- Repository and CI checks may complete before real Host evidence.
- V4.0.0 publication remains blocked until the exact candidate passes the N0-N8 Host campaign in `docs/v4/host-smoke.json`, fresh exact-candidate Final Review and candidate-bound release evidence verification.

Complete V3.x and earlier release history is preserved in [CHANGELOG_V3.md](CHANGELOG_V3.md).
