# Repository Architecture

This document describes the current V4 Native Core repository organization. The normative candidate architecture and canonical runtime owner map are in `docs/v4/architecture.json`.

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
-> docs/v4/architecture.json#runtime_owners

Installed-product lifecycle
-> skills/doctor/
-> scripts/doctor.py
-> scripts/install-agents.py
-> scripts/uninstall-agents.py
-> scripts/check-plugin-update.py
-> scripts/plugin_update.py

Maintainer evidence and experiments
-> docs/v4/host-smoke.json
-> scripts/release_evidence_v4.py
-> evals/
-> experiment/calibration tooling
```

Codex Native Subagents are the Agent runtime and lifecycle authority.

## Runtime ownership

`docs/v4/architecture.json#runtime_owners` is the only complete machine-readable path map. Human documentation describes responsibility boundaries without maintaining another path inventory.

The owned concerns are orchestration admission and control, bounded state, storage, WorkUnit dependency and acceptance truth, constraint projection, ExecutionBinding lifecycle, writer ownership, managed child responsibility projection, Host capability normalization, and optional bounded runtime evidence.

WorkGraph and WorkUnit state own the responsibility structure for one or many delegated responsibilities. `team_plan_revision` remains only as an RC compatibility marker and has no runtime planning, routing, dependency, execution, or integration authority.

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
