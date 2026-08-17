# Changelog

## [4.0.0] - Release candidate

### Public surface

- Reduce the public Skill surface to exactly `Orchestrate` and `Doctor`.
- Unify planning, execution, status, correction, continuation, cancellation, takeover, review, and integration behind Orchestrate.
- Keep Doctor as the deterministic package, runtime-state, Host-evidence, and release-readiness diagnostic owner.

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
- Require fresh current-generation Host settlement evidence before writer release or takeover.

### Safety and migration

- Fix the hardened V3.x Spawn Guard fatal path so internal failures use the Host blocking exit code.
- Add staged V4 `PreToolUse`, `PostToolUse`, and `SubagentStop` orchestration Guard logic with payload digest and `tool_use_id` binding.
- Keep peer messaging outside correctness-critical authority, acceptance, WriterLease transfer, and dependency unlocking.
- Preserve V3.x state as explicit legacy evidence and refuse silent migration of unresolved or corrupt state.
- Retain exact candidate-artifact review binding from the hardened V3.x baseline.

### Release status

- Repository implementation and offline validation may complete without Codex quota.
- Production lifecycle Hook activation and V4.0.0 publication remain blocked until `docs/v4/host-smoke.json` H01-H07 are captured on a real Codex Host.
- `Doctor --release-check` remains non-zero while that Host gate is pending.

Complete V3.x and earlier release history is preserved verbatim in [CHANGELOG_V3.md](CHANGELOG_V3.md).
