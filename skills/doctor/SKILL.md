---
name: doctor
description: Diagnose the V4 package, two-Skill public surface, fixed profiles, state, Work Graph, WriterLease, PendingControl, Host capabilities, Hook evidence, and release readiness.
---

# Doctor

Diagnosis is read-only by default. Run `../../scripts/doctor.py --check` as the deterministic diagnostic owner and show its user-facing output verbatim. Do not rewrite statuses, hide `UNKNOWN`, or claim release readiness when the Host smoke gate is pending.

Before the report starts, `../../scripts/package_integrity.py` verifies the shipped runtime package against `.codex-plugin/package-integrity.json`. A bootstrap integrity failure terminates diagnosis safely.

The V4 report has exactly eleven layers, in this order:

```text
Plugin
Public Skills
Fixed execution profiles
V4 state
Legacy V3.x state
Work Graph
WriterLease
PendingControl
Host capabilities
Lifecycle Hook coverage
Release readiness
```

Public Skills must resolve to exactly `Orchestrate` and `Doctor`. Fixed execution profiles are Luna Max, Terra High, and Sol High; dynamic reasoning-effort routing is outside V4.0.0.

Treat V4 state as thread-scoped, bounded and fail-closed. A valid legacy V3.x capsule is migration evidence only. Never silently rewrite or enroll it into V4. Unresolved V3.x ownership, active writers, pending takeover, corrupt state, `WriterLease.UNKNOWN`, or unresolved `PendingControl.UNKNOWN` must remain visible.

Host capability evidence is explicit input. Missing Host evidence stays `UNKNOWN`. Packaged `docs/v4/hooks.json` proves only the staged V4 Hook configuration. It does not prove Host discovery, Hook trust, `PreToolUse`/`PostToolUse` coverage, `SubagentStop` veto behavior, or `tool_use_id` continuity.

Use `../../scripts/doctor.py --release-check` only when evaluating a V4.0.0 release candidate. This must exit non-zero while `../../docs/v4/host-smoke.json` is pending. Offline CI cannot promote the real Host gate to PASS.

Use deterministic owners rather than reproducing their logic: `../../contracts/policy.json`, `../../scripts/dispatch_state_v4.py`, `../../scripts/work_graph_v4.py`, `../../scripts/writer_lease_v4.py`, `../../scripts/dispatch_control_v4.py`, `../../scripts/host_capabilities.py`, `../../scripts/orchestration_guard.py`, `../../scripts/install-agents.py`, `../../scripts/uninstall-agents.py`, and `../../docs/v4/host-smoke.json`.

Only explicit user intent may run lifecycle mutations. `--repair` may reconcile the five managed profiles. `--migrate-legacy` applies only to proven-owned legacy managed-profile installation state. It never migrates a live V3.x orchestration capsule. `--cleanup-stale` may remove only stale terminal legacy state through the hardened compatibility helper; active or corrupt state remains fail closed.

For plugin update requests, use the existing package-integrity-protected `../../scripts/doctor.py --update` path. Never edit Hook trust or Host configuration to make Doctor green.
