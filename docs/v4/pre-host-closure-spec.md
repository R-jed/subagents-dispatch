# V4 Pre-Host Closure Specification

This specification freezes the repository changes allowed before the first real Host feasibility probes. The exact candidate identity is recorded by PR #73 and candidate-bound release evidence; this document does not hard-code a commit that would become stale after the next justified closure change. It does not authorize broader state, WriterLease, PendingControl, storage, profile, or facade/core refactors.

## Goals

1. Preserve the one five-section managed responsibility record while restoring the task semantics that routing requires a child to receive.
2. Make Host capability readiness depend on exact coverage of every exposed collaboration identity across the model-visible and Hook-serialized identity planes.
3. Prevent managed children from using peer messaging as an unguarded sibling-context channel when the Host exposes `send_message`.
4. Strengthen H00-H20 so a campaign cannot pass while an exposed lifecycle, observation, or peer-message route bypasses the managed Guard.
5. Remove current-product documentation drift and move RC3 stage evidence out of the active contract directory.
6. Make the pre-Host candidate actually activate the exact staged lifecycle Hook definition under test without prematurely replacing the production compatibility Hook file.
7. Refresh candidate metadata and repository integrity after the code/document closure.

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

Host evidence declares the exact collaboration tool identities observed on the target Host. Model-visible identity and Hook `tool_name` identity are separate evidence fields.

The current supported V2 identity mapping is explicit:

- bare model-visible identities such as `spawn_agent` map to the same Hook identity;
- default namespace model identities such as `collaboration.spawn_agent` map to the semantic tool `spawn_agent` and the flattened Hook identity `collaborationspawn_agent`;
- the same rule applies to `followup_task`, `interrupt_agent`, `list_agents`, `send_message`, and `wait_agent` where applicable;
- an unknown namespace, unknown flattening, or otherwise unclassified collaboration identity is a Host-readiness failure requiring Host adaptation.

For every exposed lifecycle semantic tool in:

`spawn_agent`, `followup_task`, `interrupt_agent`

PreToolUse and PostToolUse evidence must contain the exact Hook-serialized identity required by the model-visible identity mapping. Coverage of the bare identity does not prove coverage of a namespaced model identity.

For every exposed `list_agents` model identity, authoritative Host observation requires paired PreToolUse and PostToolUse coverage of its exact Hook-serialized identity.

If `send_message` is exposed, every exposed model identity must map to an exact PreToolUse Hook identity, and the managed Guard must block calls from managed child agent types before peer delivery. Root/non-managed messaging remains pass-through and peer messaging never grants orchestration authority.

`host_capabilities.py` owns the identity mapping. `orchestration_guard.py` reuses that owner and may recognize additional defensive compatibility spellings for containment, but defensive recognition does not count as execution-readiness evidence.

## Staged Hook activation

`docs/v4/hooks.json` is the exact lifecycle Hook definition under test. During the pre-Host candidate phase, `.codex-plugin/plugin.json` explicitly selects `./docs/v4/hooks.json` through the Plugin `hooks` field. The physical production file `hooks/hooks.json` remains the V3 compatibility spawn Guard and is retained until lifecycle Hook cutover.

The staged Hook file is part of package-integrity scope while the Plugin manifest selects it. H00 must capture the active Hook digest and prove that the target Host discovered and trusts that exact definition. Installing the candidate without confirming active Hook identity does not close H00.

After all H00-H20 probes pass against the staged definition, lifecycle Hook cutover promotes the staged definition to `hooks/hooks.json`, removes the temporary manifest selection when the default production path is sufficient, refreshes package integrity and candidate identity, reruns the complete repository matrix, and repeats every Host probe affected by the changed candidate or Hook identity.

## Host campaign contract

Before a full H00-H20 campaign:

- H00 records the exact active Hook definition, target Host build, model-visible collaboration identities, Hook-serialized identities, and trust state.
- H01 verifies every exposed spawn model identity maps to and is intercepted through its exact Hook-serialized identity.
- H08 verifies the actual message Hook representation remains compatible with exact PendingControl binding.
- H13 verifies exact managed-profile selectors and effective profile behavior.
- H14 records the complete managed-child collaboration surface and verifies every exposed peer-message route is blocked.
- H07 verifies lifecycle success/failure discrimination is reliable enough that a failed Host operation cannot be ACKED as success.
- H15 verifies the delivered five-section assignment contains the material responsibility semantics and fresh-context isolation.

Only after that feasibility wave passes should the remaining H00-H20 probes be completed. H02/H03 apply the exact-identity rule to followup and interrupt; H11/H12 verify managed Sol/Terra cannot use lifecycle controls or peer messaging; H20 requires Windows path-alias evidence.

H07 and H08 remain Host feasibility gates. Repository code must not guess around either Host behavior.

## V3 and documentation closure

- Keep `scripts/dispatch_state.py`, `scripts/spawn_guard.py`, legacy migration, and their required tests until the planned post-cutover sunset.
- Move `contracts/rc3-integrity-closure.md` to `docs/history/rc3-integrity-closure.md`; it is release history, not active V4 contract truth.
- Keep Privacy language aligned with the two-Skill V4 product and staged lifecycle Hook model.
- Keep Doctor as product-health diagnostics while candidate-bound release authority belongs to `release_evidence_v4.py` and H00-H20.
- Keep `README_AI.md` as an owner index rather than a second policy implementation.
- Refresh PR #73 candidate metadata after the final repository candidate and CI run are known.

## Red-test matrix

| Area | Old-candidate failure required | Final assertion |
| --- | --- | --- |
| Responsibility semantics | `make_work_unit` cannot express required context | exact semantics survive WorkUnit -> assignment record |
| Incomplete persisted unit | current assignment can render without semantic context | managed assignment fails closed |
| Lifecycle identity | model-visible namespaced identity can be mistaken for Hook identity | exact model identity maps to exact flattened Hook identity or readiness fails closed |
| Peer messaging | exposed `send_message` is ignored by readiness | missing exact PreToolUse peer guard blocks execution readiness |
| Managed leaf | managed child `send_message` passes through | Guard blocks before Host messaging |
| Staged Hook activation | installed candidate loads only the V3 compatibility Hook | Plugin manifest selects `./docs/v4/hooks.json` for the pre-Host candidate |
| Staged Hook integrity | active staged Hook is outside package-integrity scope | `docs/v4/hooks.json` is hashed while selected by Plugin manifest |
| Host contract | H00/H01/H14 do not require exhaustive identity separation | machine contract carries explicit model-visible and Hook-serialized requirements |
| Public docs | retired identities or stale Host assumptions remain | current two-Skill, exact-identity, and release-owner language only |
| RC3 history | stage evidence remains under active `contracts/` | historical location only |

## Acceptance

The closure is complete only when:

1. targeted red tests pass on the new implementation;
2. the pre-Host Plugin manifest selects the exact staged Hook definition and package integrity covers that file;
3. package-integrity generation is refreshed from the final files;
4. Ruff passes;
5. the complete pytest suite passes;
6. managed Agent install/check/uninstall/reinstall lifecycle passes;
7. the pinned official OpenAI Plugin validator passes on Ubuntu/Python 3.11;
8. Ubuntu 3.11, Ubuntu 3.12, macOS 3.11, and Windows 3.11 all pass the canonical GitHub Actions matrix;
9. an execution-after review finds no changes outside this specification;
10. `docs/v4/host-smoke.json` remains `PENDING` with empty embedded results until real Host evidence exists.
