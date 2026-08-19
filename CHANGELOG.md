# Changelog

## [4.0.0] - Release candidate

### Public surface

- Reduce the public Skill surface to exactly `Orchestrate` and `Doctor`.
- Unify planning, execution, status, correction, continuation, cancellation, takeover, review, and integration behind Orchestrate.
- Keep Doctor as the deterministic installed-product health owner for package integrity, managed profiles, Host integration, orchestration state, and legacy compatibility. Candidate-bound publication authority remains outside Doctor.

### Fixed execution profiles

- Freeze Luna Max for Reader and Worker.
- Freeze Terra High for Investigator.
- Freeze Sol High for Solver and Advisor.
- Keep dynamic reasoning-effort routing outside V4.0.0.

### Runtime architecture

- Introduce the V4 WorkUnit state machine with acceptance-gated dependencies.
- Separate WorkUnit truth from ExecutionBinding and native Agent lifecycle.
- Add `control_epoch`, PendingControl single-use lifecycle authorization, and stale-observation rejection.
- Add WriterLease states `RESERVED`, `HELD`, `REVOKING`, `UNKNOWN`, and `RELEASED` for the canonical managed writer.
- Implement wakeup-driven reconciliation, critical-path prioritization, progressive refill, initial fanout <= 2, normal fanout <= 3, Host-capacity normalization, and acceptance backpressure.
- Keep same-child correction and `CONTINUE` distinct from fresh Agent attempts.
- Require fresh current-generation Host settlement evidence, a completed authoritative `list_agents` Hook receipt, and no unresolved PendingControl before writer release or takeover.
- Add a true single-responsibility path with `team_plan_revision = null` while retaining the same WorkUnit, ExecutionBinding, PendingControl, and WriterLease runtime.
- Keep one five-section managed responsibility record and restore concrete interfaces, invariants, decision boundary, reusable accepted evidence references, discovery-reuse hints, stop boundary, and acceptance semantics through bounded WorkUnit responsibility context.

### Safety and migration

- Fix the hardened V3.x Spawn Guard fatal path so internal failures use the Host blocking exit code.
- Add V4 `PreToolUse`, `PostToolUse`, and `SubagentStop` orchestration Guard logic with payload digest and `tool_use_id` binding.
- Activate the complete V4 lifecycle Guard at the default Plugin Hook path `hooks/hooks.json` for the exact real-Host release candidate while keeping publication blocked by H00-H20.
- Require Host readiness to cover every exposed lifecycle tool identity exactly, including namespace or alias forms; canonical matcher coverage cannot stand in for an uncovered alias.
- Distinguish model-visible collaboration identities from exact Hook-serialized `tool_name` identities, including the default `collaboration.<tool>` to `collaboration<tool>` flattening path.
- Guard managed-child peer `send_message` when that Host capability is exposed, while keeping peer messaging outside authority, acceptance, WriterLease transfer, dependency unlocking, and other correctness-bearing transitions.
- Consume authoritative Host capacity truth before lifecycle Host mutation and use Host-supported PostToolUse result rejection for failed or ambiguous acknowledgements.
- Keep `PostToolUse` result rejection separate from `SubagentStop` stop/veto semantics.
- Preserve V3.x state as explicit legacy evidence and refuse silent migration of unresolved or corrupt state.
- Retain exact candidate-artifact review binding from the hardened V3.x baseline.
- Keep `docs/v4/hooks.json` only as an integrity-protected non-runtime campaign reference whose `hooks` object is regression-locked to active `hooks/hooks.json`.

### Release status

- Repository implementation and offline validation may complete without Codex Host evidence.
- The exact active lifecycle Hook candidate is ready for repository validation, while V4.0.0 publication remains blocked until `docs/v4/host-smoke.json` H00-H20 are captured on a real Codex Host against that exact candidate.
- There is no post-campaign Hook-copy step; any material candidate mutation after Host evidence invalidates the affected evidence and requires the relevant probes to be repeated.
- `scripts/release_evidence_v4.py` is the dedicated candidate-bound publication verifier and remains non-zero while the required external Host campaign or fresh Final Review evidence is absent or invalid.
- Doctor remains an installed-product health diagnostic and does not grant release authority.

Complete V3.x and earlier release history is preserved verbatim in [CHANGELOG_V3.md](CHANGELOG_V3.md).