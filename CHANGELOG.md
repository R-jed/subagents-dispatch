# Changelog

## 1.0.0

Initial public release of subagents-dispatch.

### Product surface

- Public Skills are exactly `Orchestrate` and `Doctor`.
- Main remains the sole managed coordinator.
- Managed children are bounded to one Agent layer and use `fork_turns=none`.
- The product managed-child ceiling is four.

### Managed profiles

- Programmer uses Luna Max.
- Product Manager uses Sol Medium by default and Sol High for explicit material-decision or Standard Review obligations.
- Department Director uses Astra High only for highest-consequence acceptance, including the formal release Final Review.
- Main model/effort does not inherit into or override managed routes.
- The three custom-Agent profiles own behavior/configuration only; exact model/effort is supplied by the policy-backed managed spawn.

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

- Repository CI, package integrity, pinned mature Host-reference conformance, exact-source Department Director Final Review, installed-product verification, and human App observation remain separate evidence gates.
- Release Host assumptions are pinned to mature `sol-advisor` and `astra-advisor` implementations instead of a project-owned N0-N7 Host campaign. Runtime Host truth still fails closed per affected delegation.
- Publication is blocked until the exact release candidate satisfies all required gates.
