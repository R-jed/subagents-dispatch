# V4 Pre-Host Closure Specification

This specification freezes the repository changes allowed before the first real Host feasibility probes. The exact candidate identity is recorded by PR #73 and candidate-bound release evidence; this document does not hard-code a commit that would become stale after the next justified closure change. It does not authorize broader state, WriterLease, PendingControl, storage, profile, or facade/core refactors.

## Goals

1. Preserve the one five-section managed responsibility record while restoring the task semantics that routing requires a child to receive.
2. Make Host capability readiness depend on complete model-visible identity classification, exact active Hook matcher coverage, and empirical runtime interception in the behavior probe that can safely produce that evidence.
3. Prevent managed children from using peer messaging as an unguarded sibling-context channel when the Host exposes `send_message`.
4. Strengthen H00-H20 so a campaign cannot pass while an exposed lifecycle, observation, or peer-message route bypasses the managed Guard.
5. Remove current-product documentation drift and move RC3 stage evidence out of the active contract directory.
6. Make the exact pre-Host candidate activate the same default lifecycle Hook artifact that would ship if every release gate passes.
7. Refresh candidate metadata and repository integrity after the code/document closure.
8. Gate managed V2 spawn before H01 when the Host makes the delegated `message` opaque without a verifiable relation to the authorized plaintext assignment.

## Non-goals

The following remain outside this closure:

- extracting V3 storage primitives from `dispatch_state.py`;
- deleting retained `spawn_guard.py` compatibility code without a separate consumer audit;
- removing legacy profile/state migration;
- changing WriterLease or PendingControl authority semantics;
- guessing around encrypted Hook message representation when the Host does not expose a verifiable plaintext-to-dispatch binding;
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

Host evidence records the complete model-visible collaboration surface exactly. `host_capabilities.py` is the single identity owner and must classify every exposed model identity into a supported semantic tool. An unknown namespace or otherwise unclassified collaboration identity stops the campaign for Host adaptation.

The current supported V2 mapping includes:

- bare model identities such as `spawn_agent`;
- default namespace model identities such as `collaboration.spawn_agent`;
- the corresponding candidate-supported Hook matcher identities, including bare and flattened forms such as `spawn_agent` and `collaborationspawn_agent` where applicable;
- the same semantic classification for `followup_task`, `interrupt_agent`, `list_agents`, `send_message`, and `wait_agent`.

Model-visible identity, candidate matcher identity, and raw Hook stdin `tool_name` are different evidence concepts. The active Hook manifest must cover every candidate-supported matcher identity required for the exposed lifecycle, observation, and peer-message semantics. Defensive compatibility spellings recognized by `orchestration_guard.py` do not add execution-readiness authority.

Raw Hook stdin is useful diagnostic evidence when the Host exposes it, but it is not a valid prerequisite for invoking the very tool that produces it. Runtime interception is therefore proven in the behavior probe that safely exercises each semantic:

- H00 proves candidate discovery, trust, complete model-visible classification, active matcher coverage, and actual PreToolUse/PostToolUse execution through a safe non-mutating observation such as `list_agents`;
- H01 proves `spawn_agent` interception after message-binding capability is already established;
- H02 proves `followup_task` interception and exact message binding for that lifecycle operation;
- H03 proves `interrupt_agent` interception;
- H14 proves managed-child `send_message` interception and pre-delivery blocking.

If a behavior probe shows that an exposed route bypasses the active Hook, the campaign stops immediately for Host adaptation even when repository-side mapping predicted coverage.

`wait_agent` is a known `wait_or_wakeup` capability. It does not mutate lifecycle ownership and is not required to pass through the managed lifecycle Guard merely because it is part of the collaboration surface.

## Encrypted message binding gate

Managed V2 lifecycle authorization binds the prepared PendingControl to the exact delegated assignment. A Host representation that replaces the authorized plaintext `message` with opaque ciphertext is usable only when the blocking local boundary also receives a verifiable relation between that ciphertext and the authorized plaintext, such as locally available plaintext, a plaintext digest, an authenticated binding token, or an equivalent Host contract.

Seeing the same ciphertext in PreToolUse and PostToolUse is not sufficient. Rebinding a PREPARED PendingControl to whatever ciphertext appears at PreToolUse would prove only transport continuity, not that the dispatched instruction is the instruction authorized by the scheduler.

H08 is therefore a capability preflight and runs immediately after H00, before H01. It must stop before child mutation when the Host cannot provide a verifiable plaintext-to-dispatch binding. An opaque or transformed `message` with no local decryption path or binding metadata is H08 FAIL. Do not use ciphertext prefixes, length heuristics, probabilistic assumptions, or omission of message semantics to manufacture compatibility.

H02 separately proves the corresponding exact-binding property for `followup_task`. H14 does not require reading managed-child `send_message` content because the required behavior is unconditional pre-delivery blocking for managed children.

## Active Hook candidate

`hooks/hooks.json` is the authoritative installed lifecycle Hook definition under test. It is also the artifact that would ship if every V4.0.0 release gate passes. The Plugin uses the default Hook path, which keeps the candidate compatible with the pinned official OpenAI Plugin validator.

`docs/v4/hooks.json` is a non-runtime campaign reference. Tests require its `hooks` object to remain exactly equivalent to `hooks/hooks.json`, so it cannot become an independent safety authority. Package integrity covers both files during this campaign window.

H00 must capture the active `hooks/hooks.json` digest and prove that the target Host discovered, trusts, and actually executes that exact definition. Installing the candidate without runtime Hook execution evidence does not close H00.

There is no post-H00 Hook-copy or promotion step. Any material candidate mutation after Host evidence invalidates the affected evidence and requires the relevant repository and Host verification to be repeated.

## Host campaign contract

Before a full H00-H20 campaign:

- H00 records the exact active Hook definition, target Host build, complete model-visible collaboration surface, candidate identity-owner classification, active matcher coverage, trust state, and a safe real PreToolUse/PostToolUse execution witness. Raw Hook stdin identity is recorded when available but is not required before the behavior probe that can generate it.
- H08 runs next as the spawn-message binding capability preflight. A prepared authorized spawn may reach PreToolUse, but H08 must fail closed before Host child mutation if the Host exposes only opaque or transformed message content with no verifiable relation to the authorized plaintext assignment.
- H01 runs only after H08 PASS and verifies every exposed spawn model identity is empirically intercepted by the exact active candidate, with the same `tool_use_id`, exact PendingControl binding, successful Host mutation, and matching PostToolUse acknowledgement.
- H02 verifies every exposed followup identity is empirically intercepted and that its message representation remains exact-bindable to the authorized PendingControl before mutation.
- H13 verifies exact managed-profile selectors and effective profile behavior.
- H14 records the complete managed-child collaboration surface and verifies every exposed peer-message route is empirically intercepted and blocked before delivery.
- H07 verifies lifecycle success/failure discrimination is reliable enough that a failed Host operation cannot be ACKED as success.
- H15 verifies the delivered five-section assignment contains the material responsibility semantics and fresh-context isolation.

Only after that feasibility wave passes should the remaining H00-H20 probes be completed. H03 applies the empirical-interception rule to interrupt; H11/H12 verify managed Sol/Terra cannot use lifecycle controls or peer messaging; H20 requires Windows path-alias evidence.

The feasibility order is:

`H00 -> H08 -> H01 -> H02 -> H13 -> H14 -> H07 -> H15`.

H07 and H08 remain Host feasibility gates. Repository code must not guess around either Host behavior.

## V3 and documentation closure

- Keep `scripts/dispatch_state.py`, `scripts/spawn_guard.py`, legacy migration, and their required tests while active compatibility or migration consumers remain.
- `spawn_guard.py` is retained compatibility code and is not the active Hook implementation for the exact V4 real-Host candidate.
- Move `contracts/rc3-integrity-closure.md` to `docs/history/rc3-integrity-closure.md`; it is release history, not active V4 contract truth.
- Keep Privacy language aligned with the two-Skill V4 product and active lifecycle Hook model.
- Keep Doctor as product-health diagnostics while candidate-bound release authority belongs to `release_evidence_v4.py` and H00-H20.
- Keep `README_AI.md` as an owner index rather than a second policy implementation.
- Refresh PR #73 candidate metadata after the final repository candidate and CI run are known.

## Red-test matrix

| Area | Old-candidate failure required | Final assertion |
| --- | --- | --- |
| Responsibility semantics | `make_work_unit` cannot express required context | exact semantics survive WorkUnit -> assignment record |
| Incomplete persisted unit | current assignment can render without semantic context | managed assignment fails closed |
| Lifecycle identity | model-visible namespaced identity can be mistaken for Hook identity | candidate identity owner classifies the model identity and active matcher coverage plus behavior probes prove interception |
| Campaign ordering | H00 requires raw stdin evidence that only H01/H02/H03/H14 can produce | H00 admits safe behavior probes without weakening their empirical interception gates |
| Encrypted spawn binding | H01 is attempted before learning whether the Host can bind authorized plaintext to encrypted V2 message input | H08 runs first and stops before child mutation when no verifiable plaintext-to-dispatch binding exists |
| Followup binding | spawn-message feasibility is treated as proof for followup | H02 independently requires exact-bindable followup message representation |
| Peer messaging | exposed `send_message` is ignored by readiness | missing exact PreToolUse peer guard blocks execution readiness |
| Managed leaf | managed child `send_message` passes through | Guard blocks before Host messaging |
| Active Hook candidate | installed candidate still loads only the V3 compatibility Guard | default `hooks/hooks.json` contains the complete V4 lifecycle Guard |
| Reference duplication | `docs/v4/hooks.json` can drift into a second authority | reference `hooks` object must exactly equal active `hooks/hooks.json` |
| Hook integrity | active lifecycle Hook is outside package-integrity scope | active and reference Hook files are both hashed |
| Host contract | H00 requires unavailable raw payload before the tool can be exercised | machine contract separates admission evidence from per-semantic runtime interception evidence |
| Public docs | retired identities or stale Host assumptions remain | current two-Skill, behavior-evidence, and release-owner language only |
| RC3 history | stage evidence remains under active `contracts/` | historical location only |

## Acceptance

The closure is complete only when:

1. targeted red tests pass on the new implementation;
2. the exact pre-Host candidate uses validator-compatible default Plugin Hook discovery and `hooks/hooks.json` contains the complete V4 lifecycle Guard;
3. package-integrity generation is refreshed from the final files when runtime files change;
4. Ruff passes;
5. the complete pytest suite passes;
6. managed Agent install/check/uninstall/reinstall lifecycle passes;
7. the pinned official OpenAI Plugin validator passes on Ubuntu/Python 3.11;
8. Ubuntu 3.11, Ubuntu 3.12, macOS 3.11, and Windows 3.11 all pass the canonical GitHub Actions matrix;
9. an execution-after review finds no changes outside this specification;
10. `docs/v4/host-smoke.json` remains `PENDING` with empty embedded results until real Host evidence exists.
