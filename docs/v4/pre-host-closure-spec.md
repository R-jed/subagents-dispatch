# V4 Pre-Host Closure Specification

This specification freezes the final repository changes that are allowed before the first real Host feasibility probes. It follows the exact candidate `4ece78efea3e22437d72e0b85ed69e7e70627e22` and does not authorize broader state, WriterLease, PendingControl, storage, profile, or facade/core refactors.

## Goals

1. Preserve the one five-section managed responsibility record while restoring the task semantics that routing requires a child to receive.
2. Make Host capability readiness depend on exact coverage of every exposed lifecycle tool identity, including namespaced aliases.
3. Prevent managed children from using peer messaging as an unguarded sibling-context channel when the Host exposes `send_message`.
4. Strengthen H00-H20 so a campaign cannot pass while an exposed lifecycle alias or peer-message route bypasses the managed Guard.
5. Remove current-product documentation drift and move RC3 stage evidence out of the active contract directory.
6. Refresh candidate metadata and repository integrity after the code/document closure.

## Non-goals

The following remain outside this closure:

- extracting V3 storage primitives from `dispatch_state.py`;
- deleting the production compatibility `spawn_guard.py` before lifecycle Hook cutover;
- removing legacy profile/state migration;
- changing WriterLease or PendingControl authority semantics;
- solving encrypted Hook message representation before H08 provides real Host evidence;
- inferring PostToolUse success from response text before H07 provides a reliable Host contract;
- facade/core consolidation or Experiment Plane refactoring.

## Responsibility record

The record keeps exactly these five top-level sections:

`objective`, `ownership`, `interfaces`, `constraints`, `verification`.

A WorkUnit may carry one bounded responsibility-context object used only to derive that record. The context must be deterministic, JSON-serializable, bounded by the existing state limit, and must not create another scheduler, authority model, evidence store, or acceptance state.

Required semantic projection:

- `interfaces.interfaces`: concrete interfaces the child must preserve or inspect;
- `interfaces.invariants`: already-established invariants;
- `interfaces.decision_boundary`: the material decision boundary owned by the main session;
- `constraints.accepted_evidence_refs`: main-session-accepted evidence references safe to reuse;
- `constraints.do_not_redo`: already-satisfied discovery that should not be repeated while evidence remains valid;
- `constraints.stop_boundary`: explicit stop/escalation boundary for contract, judgment, investigation, stalled, scope, or safety blockers.

`make_work_unit()` owns construction defaults. Managed spawn derivation must fail closed if a persisted WorkUnit does not contain a valid responsibility context.

## Host tool identity gate

Host evidence continues to declare the exact tool identities observed on the target Host. Capability normalization classifies lifecycle meaning by the final tool-name component while preserving the complete identity for Hook coverage.

For every exposed identity whose final component is one of:

`spawn_agent`, `followup_task`, `interrupt_agent`

both PreToolUse and PostToolUse evidence must contain that exact identity. A canonical identity being covered does not cover a namespaced alias.

For every exposed identity whose final component is `list_agents`, authoritative Host observation requires paired PreToolUse and PostToolUse coverage of that exact identity.

If `send_message` is exposed, every exact identity whose final component is `send_message` must be covered by PreToolUse and the managed Guard must block calls from managed child agent types. Root/non-managed messaging remains pass-through and peer messaging never grants orchestration authority.

The staged Hook manifest should cover the canonical identities and the currently observed `collaboration.*` aliases. Any different exposed alias remains a Host-readiness failure until explicitly classified and covered.

## Host campaign contract

Before a full H00-H20 campaign:

- H00 records the exact active Hook definition and exposed collaboration tool identities.
- H01 verifies every exposed spawn lifecycle identity is intercepted, including namespace/alias forms.
- H02/H03 apply the same exact-identity rule to followup and interrupt.
- H11/H12 verify managed Sol/Terra cannot use lifecycle controls or peer messaging.
- H14 records the complete managed-child collaboration tool surface and verifies any exposed peer-message route is blocked.
- H15 verifies the delivered five-section assignment contains the material responsibility semantics, not only the five section names.

H07 and H08 remain feasibility gates for PostToolUse outcome reliability and encrypted/sanitized message representation. Repository code must not guess around either Host behavior.

## V3 and documentation closure

- Keep `scripts/dispatch_state.py`, `scripts/spawn_guard.py`, legacy migration, and their required tests until the planned post-cutover sunset.
- Move `contracts/rc3-integrity-closure.md` to `docs/history/rc3-integrity-closure.md`; it is release history, not active V4 contract truth.
- Update Privacy language from retired Dispatch/Preview/Status/Steer/Takeover identities to the two-Skill V4 product and staged lifecycle Hook model.
- Update Changelog ownership so Doctor remains product-health diagnostics while candidate-bound release authority belongs to `release_evidence_v4.py` and H00-H20.
- Expand `README_AI.md` supporting contract index to include guardrails, handoff, and evidence-artifact owners without duplicating their contents.
- Refresh PR #73 candidate metadata after the final repository candidate and CI run are known.

## Red-test matrix

| Area | Old-candidate failure required | Final assertion |
| --- | --- | --- |
| Responsibility semantics | `make_work_unit` cannot express required context | exact semantics survive WorkUnit -> assignment record |
| Incomplete persisted unit | current assignment can render without semantic context | managed assignment fails closed |
| Lifecycle alias | canonical Hook coverage can mask `collaboration.spawn_agent` | uncovered exact alias makes Host `execution_ready=false` |
| Peer messaging | exposed `send_message` is ignored by readiness | missing PreToolUse peer guard blocks execution readiness |
| Managed leaf | managed child `send_message` passes through | Guard blocks before Host messaging |
| Staged Hook manifest | no peer/namespaced matcher coverage | canonical + `collaboration.*` lifecycle/peer identities covered |
| Host contract | H01/H14 do not require exhaustive identity/peer checks | machine contract carries explicit requirements |
| Public docs | retired Dispatch/release-readiness language remains | current two-Skill and release-owner language only |
| RC3 history | stage evidence remains under active `contracts/` | historical location only |

## Acceptance

The closure is complete only when:

1. targeted red tests pass on the new implementation;
2. package-integrity generation is refreshed from the final files;
3. Ruff passes;
4. the complete pytest suite passes;
5. managed Agent install/check/uninstall/reinstall lifecycle passes;
6. the pinned official OpenAI Plugin validator passes on Ubuntu/Python 3.11;
7. Ubuntu 3.11, Ubuntu 3.12, macOS 3.11, and Windows 3.11 all pass the canonical GitHub Actions matrix;
8. an execution-after review finds no changes outside this specification;
9. `docs/v4/host-smoke.json` remains `PENDING` with empty embedded results until real Host evidence exists.
