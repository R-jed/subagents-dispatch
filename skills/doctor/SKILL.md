---
name: doctor
description: Diagnose and explicitly maintain the installed subagents-dispatch Plugin, managed Agent profiles, Host integration, orchestration state, and legacy compatibility.
---

# Doctor

Use `../../scripts/doctor.py --check` as the deterministic diagnostic owner and display its user-facing output verbatim. Do not reinterpret statuses or hide `UNKNOWN`.

Normal diagnosis is read-only and offline. It must not refresh the Marketplace, install or remove profiles, change Hook trust, mutate orchestration state, spawn children, or modify unrelated Codex configuration.

Before diagnostics start, `../../scripts/doctor.py` verifies the shipped runtime package against `.codex-plugin/package-integrity.json`. An integrity failure stops safely.

The user-facing report has five layers:

```text
Plugin package
Managed Agents
Host integration
Orchestration state
Legacy compatibility
```

`Plugin package` verifies the executing package identity and the exact two-Skill public surface. `Managed Agents` verifies the five fixed Reader, Worker, Investigator, Solver, and Advisor profiles and whether the active Codex home has the owned profiles installed exactly.

`Host integration` checks the installed production lifecycle Hook configuration. When explicit Host capability evidence is available it may verify the current Host surface through `../../scripts/host_capabilities.py`. Missing live Host evidence remains `UNKNOWN`. Local Hook configuration never impersonates observed Host behavior.

`Orchestration state` diagnoses the current thread-scoped V4 state. `WriterLease.UNKNOWN`, `PendingControl.UNKNOWN`, unknown execution lifecycle, corrupt state, or unresolved legacy active ownership remain fail closed. Ordinary in-flight controls may be reported as `WARN` without being rewritten.

`Legacy compatibility` reports legacy managed-profile and V3 orchestration state separately. Doctor never silently migrates active or ambiguous legacy state into V4.

Use explicit maintenance actions only when the user asks for them:

- repair owned managed Agent profiles;
- migrate only proven-owned legacy managed-profile installation state;
- clean only stale terminal legacy orchestration state;
- uninstall only profiles proven owned by the Plugin;
- check for Plugin updates through `../../scripts/check-plugin-update.py`;
- update the Plugin through the package-integrity-protected `../../scripts/doctor.py --update` path.

A maintenance action must use the existing ownership-aware helper and then rerun the same deterministic Doctor diagnostics. Do not replace a refused ownership check with manual deletion, wildcard cleanup, or unrelated configuration edits.

Runtime attestation remains a separate compatibility tool outside Doctor. Its dedicated verifier streams exactly one rollout, enforces bounded total-rollout and per-line input limits, and Oversized rollout input fails closed. Doctor does not expose or execute that workflow.

Repository publication checks, candidate evidence, CI state, benchmark/calibration campaigns, and other maintainer workflows are outside the Doctor Skill. Use their dedicated repository tools instead.
