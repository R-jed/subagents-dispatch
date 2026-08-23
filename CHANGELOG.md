# Changelog

## [4.0.0] - Release candidate

### Public surface

- Reduce the public Skill surface to exactly `Orchestrate` and `Doctor`.
- Keep planning, execution, status, correction, continuation, cancellation, takeover, review and integration behind Orchestrate.
- Keep Doctor as the installed-product diagnosis and ownership-safe maintenance entry.

### Fixed execution profiles

- Reader, Worker, Investigator, Solver and Advisor all use Luna Max for managed child execution in the current RC.
- Preserve separate semantic roles, exact managed selectors and mutation authority even though the child model is shared.
- Keep Main free to use other Host models.
- Dynamic reasoning-effort routing remains outside V4.0.0.

### Native Core runtime

- Use Codex Native Subagents as the only Agent runtime and lifecycle authority.
- Keep WorkUnit acceptance separate from ExecutionBinding and Host lifecycle.
- Keep `control_epoch` for stale-generation rejection without a persisted lifecycle authorization protocol.
- Keep WriterLease states `RESERVED`, `HELD`, `REVOKING`, `UNKNOWN`, and `RELEASED` for one canonical mutable workspace.
- Use one product managed-child safety ceiling of 4. Main owns dispatch judgment; fixed fanout targets, automatic ranking and acceptance-backpressure authorization are removed.
- Let the Host own actual capacity. Explicit pre-materialization spawn rejection rolls back provisional activation without consuming a fresh attempt; ambiguous materialization becomes `UNKNOWN`.
- Replace fixed fresh-attempt and focused-followup budgets with evidence-gated recovery.
- Keep WorkGraph and WorkUnit state as the responsibility/dependency structure.
- Keep optional allowlisted rollout inspection only for recovery or validation when native Host evidence is insufficient.

### Managed child containment

- Formal Real Host N1 testing on Host build 6962 / embedded Codex `0.149.0-alpha.4.1` demonstrated that a V2-capable depth-1 child can successfully materialize a depth-2 grandchild.
- Confirmed against the matching OpenAI Codex `rust-v0.149.0-alpha.4` source that the V2 spawn path does not enforce project `agent_max_depth`, while child collaboration exposure depends on the child model's `multi_agent_version` metadata.
- Current Host metadata reports Luna as V1 and Terra/Sol as V2. The RC therefore pins every managed child profile to Luna Max so the spawned child does not receive the V2 collaboration surface.
- Remove role-local `[agents] enabled=false` and `[features] multi_agent_v2=false` from managed profiles because the current Codex agent-role override layer does not apply those fields as child containment controls.
- Keep the instruction against further subagent creation as defense in depth only.
- Treat Host/model metadata drift as a containment requalification trigger. Project `max_depth`, profile settings and behavioral instructions never replace N1 Host evidence.
- Behavioral read-only remains separate from Host-enforced sandbox truth. Configured read-only is not promoted to runtime proof without Host evidence.

### Complexity reduction

- Remove the earlier lifecycle interception control plane from the active V4 runtime.
- Remove PendingControl, Guard receipts, capacity tokens, identity-normalization machinery and related release diagnostics.
- Remove semantic scheduler ranking, fixed fanout phases, fixed acceptance backpressure, and fixed recovery budgets from execution authorization.
- Do not replace that machinery with another persisted request/receipt control plane or scheduling database.
- Remove the retired V3 orchestration state engine and its receipt/recovery accounting from the active V4 runtime surface.

### Product lifecycle

- Keep first-use managed-profile provisioning ownership-safe and return `RESTART_REQUIRED` when the current task cannot authoritatively observe newly created custom roles.
- Keep update check and explicit update as separate flows.
- Verify a newly installed package with package integrity, managed-profile reconciliation and the current Native Core Doctor contract before reporting update completion.

### Release status

- Repository and CI checks may complete before real Host evidence.
- V4.0.0 publication remains blocked until the exact candidate passes the N0-N8 Host campaign in `docs/v4/host-smoke.json`, fresh exact-candidate Final Review and candidate-bound release evidence verification.
