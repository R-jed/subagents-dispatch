# Changelog

## 1.0.0

Initial public release of subagents-dispatch.

### Product surface

- Public Skills are exactly `Orchestrate` and `Doctor`.
- Main remains the sole managed coordinator.
- Managed children are bounded to one Agent layer and use `fork_turns=none`.
- The product managed-child ceiling is four.

### Managed profiles

- Reader and Worker use Luna Max.
- Investigator uses Terra High.
- Solver and Advisor use Sol High.

### Native Core

- WorkGraph and WorkUnit own responsibility, dependency, readiness, and acceptance truth.
- ExecutionBinding owns one concrete managed attempt.
- WriterLease owns canonical-workspace writer coordination.
- Host lifecycle completion remains separate from Main acceptance.
- Ambiguous lifecycle, identity, materialization, permission, and writer evidence fails closed as `UNKNOWN`.
- Recovery is evidence-gated. Fresh retry requires a changed execution basis and same-child correction requires a new correction basis.

### Installation and maintenance

- Managed Agent installation is ownership-safe and no-clobber.
- Doctor diagnoses only the current product and supports explicit managed-profile repair or uninstall.
- Update checking and update installation require the canonical Marketplace-local Plugin source.
- Pre-1.0 product state is unsupported and rejected by the current state schema. Current installer and updater ownership metadata must match current product identities; unrelated files remain outside product ownership. No pre-1.0 discovery, migration, or cleanup path is shipped.

### Release qualification

- Repository CI, package integrity, real Codex Host qualification, Final Review, installed-product verification, and human App observation remain separate evidence gates.
- Publication is blocked until the exact release candidate satisfies all required gates.
