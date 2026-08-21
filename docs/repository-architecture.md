# Repository Architecture

This document describes the current V4 Native Core repository organization. The normative candidate architecture is `docs/v4/architecture.json`; `docs/architecture.md` owns the detailed runtime map.

## Product surface

The Plugin exposes exactly two explicit Skills:

```text
Orchestrate
Doctor
```

Orchestrate is the single user-facing orchestration entry. Doctor owns installed-product diagnosis and explicitly requested ownership-safe maintenance.

## Current planes

```text
Product contracts
-> contracts/

Deterministic Native Core runtime
-> scripts/orchestrate_v4.py
-> scripts/dispatch_state_v4.py
-> scripts/work_graph_v4.py
-> scripts/scheduler_v4.py
-> scripts/execution_lifecycle_v4.py
-> scripts/writer_lease_v4.py
-> scripts/managed_execution_v4.py
-> scripts/host_capabilities.py

Installed-product lifecycle
-> skills/doctor/
-> scripts/doctor.py
-> scripts/install-agents.py
-> scripts/uninstall-agents.py
-> scripts/check-plugin-update.py
-> scripts/plugin_update.py

Optional runtime evidence
-> scripts/inspect-agent-runtime.py
-> scripts/inspect-collaboration-runtime.py
-> scripts/runtime-evidence.py

Maintainer evidence and experiments
-> docs/v4/host-smoke.json
-> scripts/release_evidence_v4.py
-> evals/
-> experiment/calibration tooling
```

Codex Native Subagents are the Agent runtime and lifecycle authority.

## Runtime ownership

One concern has one current owner:

```text
Orchestrate admission/routing/control      scripts/orchestrate_v4.py
bounded current state                     scripts/dispatch_state_v4.py
WorkUnit/dependency/acceptance truth      scripts/work_graph_v4.py
admission/fanout/backpressure             scripts/scheduler_v4.py
ExecutionBinding lifecycle                scripts/execution_lifecycle_v4.py
workspace writer ownership                scripts/writer_lease_v4.py
child responsibility projection           scripts/managed_execution_v4.py
Host capability normalization             scripts/host_capabilities.py
```

A single independent delegated responsibility may avoid TeamPlan. Coordinated work adds TeamPlan only when multiple unresolved responsibilities or material dependency/integration order need persistent structural truth.

## Package integrity

`.codex-plugin/package-integrity.json` covers the explicit installed-product runtime allowlist discovered by `scripts/package_integrity.py`. It detects partial or stale packages but is not a cryptographic signature or remote provenance proof.

Maintainer-only experiment and release-evidence tools do not automatically become ordinary product-health dependencies merely because they live in the repository.

## Compatibility

V3 storage and migration helpers remain only where current Doctor or migration behavior consumes them. Older pre-release V4 state from incompatible schemas requires explicit cleanup and restart.

Historical design records remain in Git history and release notes. They do not define current runtime ownership.

## Release boundary

Repository tests prove deterministic implementation contracts. `docs/v4/host-smoke.json` owns the exact N0-N8 real Host campaign. Final Review and release evidence bind to the exact candidate after deterministic and Host verification.

The release process should prefer evidence that protects user-facing behavior, lifecycle safety, installation health and candidate identity. Tests that only preserve knowledge of deleted implementation names add maintenance cost without improving the product.

## Design rule

Prefer deleting competing representations and stale ceremony before adding abstractions. Add a new component only when a concrete product or safety requirement cannot be expressed safely through an existing owner. CI should validate these product contracts without becoming a reason to retain dead architecture.
