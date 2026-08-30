# 1.0.0 Clean-Break Closure Plan

This plan covers the repository closure required for the first public `1.0.0` line. Live branch, commit, CI, review, and Host verdicts belong in GitHub and Issue #91 rather than in this file.

## Objective

Finish the clean break from pre-1.0 development architecture without adding compatibility machinery to preserve retired internal designs.

The current product keeps Native Core V4 as an internal architecture generation. Public product identity starts at Plugin `1.0.0`.

## Acceptance conditions

- Plugin, changelog, release checklist, and publication tag all identify the first public release as `1.0.0`.
- WorkGraph and WorkUnit are the only current responsibility/dependency structure. Retired TeamPlan files, fields, validators, and compatibility callers are absent.
- Pre-1.0 migration and stale-state cleanup implementations are absent from the shipped product.
- Unsupported or unrecognized state, ownership, installation source, Host evidence, and runtime identity fail explicitly or remain `UNKNOWN` where uncertainty is the contract.
- Machine architecture state/entity fields match the runtime schema instead of carrying deleted compatibility fields.
- Current tests exercise current interfaces. Historical tests do not keep deleted APIs alive.
- The exact PR head passes the complete GitHub Actions matrix, package-integrity verification, Ruff, full pytest, official Plugin validation where applicable, and managed Agent install/check/Doctor/uninstall lifecycle.
- Real Host qualification remains a separate release gate and is rebound only after the final merged runtime basis is frozen and Issue #91 preflight permits the next action.

## Implementation order

1. Repair stale tests that still call deleted TeamPlan compatibility surfaces.
2. Close machine-contract and release-document drift created by the clean break.
3. Add repository assertions that prevent retired pre-1.0 compatibility artifacts and fields from returning to current authority surfaces.
4. Align development handoff and Host procedure with the current `1.0.0` release boundary without copying live SHA or CI state into source files.
5. Run the exact-head repository matrix and use failures as evidence of any remaining consumer or contract drift.
6. Perform a fresh adversarial five-axis review of the final diff before leaving Draft.

## Boundaries

Always:

- fail closed on unsupported state, unsafe ownership, stale generation, ambiguous writer ownership, and unverifiable installed source;
- preserve `UNKNOWN` when Host truth is genuinely unavailable;
- use current canonical helpers and truth owners;
- regenerate package integrity only when shipped bytes change;
- verify the exact final head.

Do not:

- reintroduce a migration path, cleanup path, compatibility marker, wrapper, or fallback solely because an old test or document still references it;
- silently translate unsupported pre-1.0 data into current state;
- turn missing or conflicting Host evidence into success;
- add a tracked checkbox or status snapshot whose only purpose is to record the final CI result and thereby create a new unverified source head.

## Verification

Repository completion requires the live GitHub exact-head matrix to pass. Tests are necessary but the final review must also check correctness, simplicity, architecture, security, and performance. Host N0-N7, the separate exact-source Final Review, installed-product verification, and human App observation remain later release gates under `docs/release-checklist.md`.
