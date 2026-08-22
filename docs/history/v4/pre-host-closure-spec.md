> Historical archive. This document records a superseded design/review state. It is not a current V4 contract, implementation guide, release gate, or source of runtime authority. Use current `contracts/`, current non-history `docs/`, and `docs/v4/` for present behavior.

# V4 Pre-Host Closure Specification

This specification freezes the repository changes allowed before the real H00-H20 Host campaign. The exact candidate identity is recorded by PR #73 and candidate-bound release evidence; this document does not hard-code a commit that would become stale after the next justified closure change. It does not authorize broader state, WriterLease, storage, profile, or facade/core refactors.

The initial version of this closure assumed that a managed lifecycle Hook could bind the complete plaintext assignment to the exact Host `tool_input` representation. Real H08 evidence on the target Codex Host disproved that assumption: MultiAgentV2 may replace `message` with an opaque encrypted transport representation before PreToolUse. The closure therefore now separates Host-owned message transport from Plugin-owned lifecycle authorization while preserving the existing fail-closed control generations, role selection, WriterLease effects, and Main acceptance boundary.

## Goals

1. Preserve the one five-section managed responsibility record and its deterministic plaintext construction before Host dispatch.
2. Make Host capability readiness depend on complete model-visible identity classification, exact active Hook matcher coverage, and empirical runtime interception in the behavior probe that can safely produce that evidence.
3. Prevent managed children from using peer messaging as an unguarded sibling-context channel when the Host exposes `send_message`.
4. Keep PendingControl as the single-use lifecycle authorization owner while binding only Plugin-owned control semantics.
5. Treat native V2 `message` encryption and delivery as Host transport responsibility, with the Guard requiring the expected transport field and exact control envelope without trying to decrypt or infer message content.
6. Make semantic assignment delivery a behavior-level H15 responsibility owned by Main verification.
7. Remove current-product documentation drift and move RC3 stage evidence out of the active contract directory.
8. Make the exact pre-Host candidate activate the same default lifecycle Hook artifact that would ship if every release gate passes.
9. Refresh candidate metadata and repository integrity after the code/document closure.

## Non-goals

The following remain outside this closure:

- extracting V3 storage primitives from `dispatch_state.py`;
- deleting retained `spawn_guard.py` compatibility code without a separate consumer audit;
- removing legacy profile/state migration;
- reducing WriterLease identity, epoch, effect, settlement, or UNKNOWN rules;
- removing PendingControl single-use, `tool_use_id`, control-epoch, TeamPlan-revision, lease-epoch, or target bindings;
- implementing a local decryptor, ciphertext heuristic, sidecar transport, assignment receipt protocol, or second message channel;
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

`execution_lifecycle_v4_core.prepare_spawn()` continues to compare the Main-prepared Host payload with the canonical five-section plaintext assignment before creating PendingControl. This keeps local assignment construction deterministic and prevents Main-side preparation drift.

After the Host accepts the call, `message` belongs to native Codex transport. Hook-visible ciphertext or another opaque string is not reinterpreted as local assignment truth.

## Lifecycle authorization boundary

PendingControl authorizes lifecycle control, not message transport.

The authorization projection is:

- `spawn_agent`: `task_name`, `agent_type`, `fork_turns`;
- `followup_task`: `target`;
- `interrupt_agent`: `target`.

The V2 transport fields remain mandatory where the Host tool requires them:

- `spawn_agent.message` must exist and be a non-empty string;
- `followup_task.message` must exist and be a non-empty string.

The Guard does not compare Hook-visible message bytes with the canonical plaintext assignment, does not compare PreToolUse ciphertext with PostToolUse ciphertext, and does not use ciphertext prefix, length, or format heuristics.

PendingControl continues to bind:

- one operation and one ExecutionBinding;
- exact lifecycle target;
- current TeamPlan revision;
- current control epoch and next control epoch;
- current WriterLease epoch when applicable;
- exact writer effect;
- one `tool_use_id` from PreToolUse through PostToolUse;
- single unresolved control per execution;
- ACK idempotence and UNKNOWN quarantine for ambiguous PostToolUse reconciliation.

For managed spawn, `managed_execution_v4.py` additionally validates the exact Host control envelope: `task_name`, managed `agent_type`, and `fork_turns: none`. Extra or missing fields fail closed. A missing or empty `message` also fails closed as an invalid native transport shape.

This boundary trusts the Codex Host to deliver its own native encrypted message transport. It does not trust a child result as acceptance evidence. Main still owns artifact, diff, test, evidence, and WorkUnit acceptance.

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
- H01 proves `spawn_agent` interception and successful PendingControl Pre/Post pairing on a specimen whose PreToolUse boundary also closes H08 native encrypted-message compatibility;
- H02 proves `followup_task` interception and target/control-generation binding while native message transport may remain opaque;
- H03 proves `interrupt_agent` interception;
- H14 proves managed-child `send_message` interception and pre-delivery blocking.

If a behavior probe shows that an exposed route bypasses the active Hook, the campaign stops immediately for Host adaptation even when repository-side mapping predicted coverage.

`wait_agent` is a known `wait_or_wakeup` capability. It does not mutate lifecycle ownership and is not required to pass through the managed lifecycle Guard merely because it is part of the collaboration surface.

## Native encrypted-message compatibility gate

H08 verifies that the exact candidate can safely coexist with the target Host's native encrypted V2 transport.

The H08 assertion is evaluated at the PreToolUse boundary of the same authorized managed spawn specimen used by H01. It occurs before Host child mutation. Passing H08 requires all of the following:

- the canonical five-section plaintext assignment was constructed and validated before PendingControl preparation;
- Hook `tool_input` has the expected managed spawn shape;
- `message` is present and non-empty even when opaque or transformed by the Host;
- `task_name`, `agent_type`, and `fork_turns` match the authorized control envelope exactly;
- PendingControl consumes exactly one current authorization and binds the Host `tool_use_id`;
- mutation of any authorization-relevant field is rejected before child creation.

H08 does not require plaintext recovery, ciphertext equality across phases, a plaintext digest from the Host, or an authenticated plaintext-to-ciphertext token. Those would extend the Plugin into the Host's transport layer without improving control-plane ownership.

H08 also does not prove that a child semantically received the intended assignment. H15 owns that evidence through observable child behavior, Main verification, and sibling-isolation probes using distinct non-sensitive markers or equivalent observable assignments.

H02 applies the same transport boundary to `followup_task`: the target and lifecycle authorization remain exact while Host-owned message representation may vary.

H14 does not inspect managed-child `send_message` content because required behavior is unconditional pre-delivery blocking for managed children.

## Active Hook candidate

`hooks/hooks.json` is the authoritative installed lifecycle Hook definition under test. It is also the artifact that would ship if every V4.0.0 release gate passes. The Plugin uses the default Hook path, which keeps the candidate compatible with the pinned official OpenAI Plugin validator.

`docs/v4/hooks.json` is a non-runtime campaign reference. Tests require its `hooks` object to remain exactly equivalent to `hooks/hooks.json`, so it cannot become an independent safety authority. Package integrity covers both files during this campaign window.

H00 must capture the active `hooks/hooks.json` digest and prove that the target Host discovered, trusts, and actually executes that exact definition. Installing the candidate without runtime Hook execution evidence does not close H00.

There is no post-H00 Hook-copy or promotion step. Any material candidate mutation after Host evidence invalidates the affected evidence and requires the relevant repository and Host verification to be repeated.

## Host campaign contract

Before a full H00-H20 campaign:

- H00 records the exact active Hook definition, target Host build, complete model-visible collaboration surface, candidate identity-owner classification, active matcher coverage, trust state, and a safe real PreToolUse/PostToolUse execution witness. Raw Hook stdin identity is recorded when available but is not required before the behavior probe that can generate it.
- H08 is evaluated at the PreToolUse boundary of the same authorized spawn specimen that continues into H01. It verifies native encrypted-message compatibility and exact authorization-envelope enforcement before child mutation.
- H01 continues that specimen through successful Host spawn and matching PostToolUse acknowledgement with the same `tool_use_id`.
- H02 verifies every exposed followup identity is empirically intercepted and that target/control-generation binding survives Host-owned opaque message transport.
- H13 verifies exact managed-profile selectors and effective profile behavior.
- H14 records the complete managed-child collaboration surface and verifies every exposed peer-message route is empirically intercepted and blocked before delivery.
- H07 verifies lifecycle success/failure discrimination is reliable enough that a failed Host operation cannot be ACKED as success.
- H15 verifies the delivered five-section assignment through observable behavior and fresh-context sibling isolation without inspecting encrypted transport content.

Only after that feasibility wave passes should the remaining H00-H20 probes be completed. H03 applies the empirical-interception rule to interrupt; H11/H12 verify managed Sol/Terra cannot use lifecycle controls or peer messaging; H20 requires Windows path-alias evidence.

The feasibility order is:

`H00 -> H08/H01 shared spawn specimen -> H02 -> H13 -> H14 -> H07 -> H15`.

H07 and H08 remain Host feasibility gates. Repository code must not invent Host behavior around either boundary.

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
| Encrypted spawn transport | complete plaintext payload equality rejects the target Host's native encrypted `message` | H08 accepts a non-empty opaque Host message while exact task/profile/fresh-context authorization remains bound and mutable control fields fail closed |
| Followup transport | complete followup payload equality treats Host message representation as control identity | H02 binds target and lifecycle generation while opaque message representation may vary |
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
3. package-integrity generation is refreshed from the final runtime files when runtime files change;
4. Ruff passes;
5. the complete pytest suite passes;
6. managed Agent install/check/uninstall/reinstall lifecycle passes;
7. the pinned official OpenAI Plugin validator passes on Ubuntu/Python 3.11;
8. Ubuntu 3.11, Ubuntu 3.12, macOS 3.11, and Windows 3.11 all pass the canonical GitHub Actions matrix;
9. an execution-after review finds no changes outside this specification;
10. `docs/v4/host-smoke.json` remains `PENDING` with empty embedded results until real Host evidence exists.
