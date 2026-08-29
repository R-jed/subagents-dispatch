# Headoff

Updated: 2026-08-29.

## Purpose

This is the durable development-session handoff for `subagents-dispatch`.

It is a continuity document only. It is not Plugin runtime, a product contract, Host qualification input, release evidence, or a release gate. Canonical product and qualification truth remains in the files named below and in Issue #91.

Detailed historical Host evidence through N6 remains in:

- `docs/v4/host-qualification-handoff.md`

Issue #91 is the current append-only operational ledger and is authoritative for later N7/N8 Host observations and permission RCA.

## Project summary

`subagents-dispatch` is a bounded orchestration layer over Codex Native Subagents.

Main owns dispatch judgment, integration, irreversible effects, writer takeover, and final acceptance.

Fixed managed profiles:

- Reader: `subagents_dispatch_reader`, `gpt-5.6-luna`, `max`, read-only intent.
- Worker: `subagents_dispatch_worker`, `gpt-5.6-luna`, `max`, bounded source write.
- Investigator: `subagents_dispatch_investigator`, `gpt-5.6-terra`, `high`, read-only intent.
- Solver: `subagents_dispatch_solver`, `gpt-5.6-sol`, `high`, bounded source write.
- Advisor: `subagents_dispatch_advisor`, `gpt-5.6-sol`, `high`, read-only intent.

All managed children use `fork_turns=none`, are intended to remain leaf Agents, and are subject to the product managed-child ceiling of four.

Core ownership:

- WorkGraph / WorkUnit own responsibility, dependencies, readiness, and acceptance.
- ExecutionBinding owns one concrete managed attempt/generation.
- WriterLease owns canonical-workspace writer coordination.
- Codex Host owns actual materialization, lifecycle, capacity, child identity, effective permissions/sandbox, and collaboration capability.
- Host `COMPLETED` is lifecycle evidence, not correctness acceptance.
- Requested profile values are configuration intent, not authoritative Host permission proof.
- Ambiguous Host truth fails closed.

## Current V4 qualification status

Current campaign status:

- N0: PASS
- N1: PASS
- N2: PASS
- N3: PASS
- N4: PASS
- N5: PASS
- N6: PASS
- N7: PASS
- H8: COMPLETE
- N8: FAIL on effective Host read-only enforcement
- H9: INCOMPLETE / BLOCKED on Host permission remediation and RCA
- H10 release closure: NOT STARTED / BLOCKED

Public `1.0.0` remains blocked.

N8 must not be retried until a changed Host permission basis is proven. H10 must not start before N8 is recovered and the final release gates are explicitly entered.

## Qualification basis and source chronology

Host/build environment used by the current campaign:

- Host: `26.820.60940`
- Host build: `7119`
- embedded Codex: `0.150.0-alpha.8`
- platform: Darwin arm64

Qualification basis digests:

- runtime manifest SHA256: `a6fd674675fd0b4c2184dab7b0c0a3b85dd8ec0467756876067ae9d2874432ab`
- profile contract SHA256: `9520395880612c0c40ebc992d36cdadd950fd8328904f3e8c7641042c9f03a8d`
- Host contract SHA256: `0e9677ba7a66e8ea4a49b354a141098a26d62a3ed7051c50e2cbc7c42bab2566`

Source chronology:

- N0-N6 were originally qualified against HEAD `880578e62667596eb7e643a012ec457de38fb57e`, tree `6ba888f39014240e41f430058acc9ea058eb9f32`.
- Documentation-only handoff commits advanced the branch to HEAD `36952e16aa4b1502ae7397cb7c40351371b54763`, tree `49a3041af4e4f3e67c2d7fbb0121746df41960a0`.
- The three qualification digests remained unchanged, so conclusive N0-N6 evidence was retained under the release invalidation rules.
- N7 was completed against the `36952e...` candidate.
- N8 attempt 1 and subsequent permission diagnostics were also bound to `36952e...`.
- This `headoff.md` refresh is intentionally documentation-only and will create a new branch tip. Before any further Host qualification action, re-bind the exact new HEAD/tree and verify the same three qualification digests remain unchanged. Exact-source CI and final-source review will still need refresh on the eventual final source.

## Current roots and Host permission state

Original qualification root:

- session/thread: `01a048f3-5f69-7000-9325-093dd895ae4c`

Fresh permission-remediation root:

- session/thread: `01a04caf-1a3a-7b11-b820-b28f98d4ba4c`

The fresh root identity is authoritative and distinct from the original root, but its effective Host permission still resolves to:

- sandbox: `danger-full-access`
- active permission profile: `:danger-full-access`
- permission profile type: `disabled`
- approval policy: `never`

A later verification turn on the same fresh root, `01a04dc6-0350-7bd0-b41a-60598f448f85`, still observed the same effective permission tuple after an operator attempted to select Read Only.

Therefore:

- `permission_state_assurance = verified` means the effective state is reliably observed;
- it does not mean the state satisfies N8;
- `effective_root_read_only_verified = false`;
- `n8_retry_eligible = false`.

Permission provenance remains unknown because the Host evidence currently exposes the effective turn state but not an authoritative source/selection chain.

## N7 accepted result

N7 rollout reconciliation and privacy passed.

Representative accepted rollout chain reused the real N5 interrupt:

- WorkUnit: `N5_WORKER_HOST7119_H7_001`
- ExecutionBinding: `exec-n5-worker-host7119-h7-001`
- canonical task: `/root/sd_n5_worker_host7119_h7_001_a1`
- child thread: `01a04c25-e25e-7311-bb9d-71ca51962b06`
- interrupt call id: `call_c2HIB8juREnJTFw5k2GOj9XX`
- current settlement proof: `host-observation:exec-n5-worker-host7119-h7-001:1:1:INTERRUPTED`

N7 proved:

- lifecycle call id, exact target, child identity/path, recognized interrupt result, and current-generation Host settlement can be bound without exposing raw prompt/reasoning data;
- allowlisted inspection omits assignment text, prompts, assistant output, reasoning, message body, raw arguments/output, source contents, and environment values;
- stale acceptance evidence is rejected;
- ambiguous acceptance evidence is rejected;
- stale writer settlement evidence is rejected;
- ambiguous WriterLease truth fails closed.

Durable result: Issue #91 comment `5461073938`.

## N8 failure and permission RCA

N8 requires a fresh Advisor review bound to the exact candidate plus authoritative Host-observed strict read-only effective permission.

N8 attempt 1 materialized the correct Advisor route:

- WorkUnit: `N8_ADVISOR_HOST7119_H9_001`
- ExecutionBinding: `exec-n8-advisor-host7119-h9-001`
- canonical task: `/root/sd_n8_advisor_host7119_h9_001_a1`
- child thread: `01a04c85-5e68-7f51-8a1a-eae667ef4e8e`
- agent type: `subagents_dispatch_advisor`
- model: `gpt-5.6-sol`
- effort: `high`
- `fork_turns=none`

Artifact binding and mutation invalidation passed, and the Advisor caused no repository mutation or nested Agent creation.

The decisive failure was effective permission:

- configured Advisor intent: `sandbox_mode=read-only`, `mutation_authority=none`;
- Host-observed Advisor sandbox: `danger-full-access`;
- Host-observed permission profile type: `disabled`;
- `permission_state_assurance=failed` under the strict N8 read-only requirement;
- Advisor verdict: `rethink`.

Durable N8 result: Issue #91 comment `5461194287`.

Source-level RCA established:

1. The V2 managed spawn payload does not contain a per-child sandbox/permission field.
2. Codex applies the Agent role/profile, but spawned children retain the parent turn permission snapshot.
3. Agent role TOML sandbox values therefore express intent and cannot independently override the parent effective permission on this Host path.
4. A Full Access parent/root naturally yields a Full Access Advisor child.

Durable RCA: Issue #91 comment `5461253159`.

## Desktop permission-selection RCA

The remediation focus moved from `subagents-dispatch` source to Codex Desktop permission selection and persistence.

Exact embedded Codex source binding:

- tag/runtime: `rust-v0.150.0-alpha.8`
- upstream commit: `fcbdb57851be70192fd0c21faa9e529146e93ff1`

Relevant source facts:

- `thread/start` accepts a named `permissions` field and can override config-file permission defaults for a fresh root.
- `thread/settings/update.permissions` is a supported field for subsequent turns.
- built-in `Read Only` maps to `:read-only` / `PermissionProfile::read_only()` / approval `on-request`.
- built-in `Full Access` maps to `:danger-full-access` / `PermissionProfile::Disabled` / approval `never`.
- current Host observations exactly match the built-in Full Access tuple.

A fresh root was successfully created, eliminating old-root reuse as the explanation, but it still resolved to Full Access. A later task-level Read Only selection followed by a new verification turn also remained Full Access.

Current fault boundary is therefore narrower than config parsing alone, but exact provenance is still unproven.

Public OpenAI Codex issues provide corroborating evidence that Desktop permission UI, persisted per-thread state, and live effective thread state can diverge. They are supporting context only and do not replace this campaign's local Host evidence.

Durable RCA / diagnostics:

- source rebind before N7: `5461017966`
- N7 PASS: `5461073938`
- N8 FAIL: `5461194287`
- initial Host permission RCA: `5461253159`
- old-root remediation failed: `5461285040`
- fresh root created but still Full Access: `5462769724`
- Desktop permission-selection RCA: `5462833308`
- task-level Read Only rebind still Full Access: `5462897305`
- external/source corroboration RCA: `5462928458`

## N5/N6 retained WriterLease state

The retained runtime state remains important for any future campaign continuation:

N5 Worker:

- WorkUnit: `N5_WORKER_HOST7119_H7_001`
- ExecutionBinding: `exec-n5-worker-host7119-h7-001`
- canonical task: `/root/sd_n5_worker_host7119_h7_001_a1`
- child thread: `01a04c25-e25e-7311-bb9d-71ca51962b06`
- retained execution lifecycle: `INTERRUPTED`
- WorkUnit: `CANCELLED`

N6 proved:

- replacement allocation was blocked while the execution-owned WriterLease remained blocking;
- premature Main writer acquisition was blocked;
- settled execution ownership was atomically taken over by Main using `execution_lifecycle_v4.takeover_to_main`;
- the new Main lease reached epoch 2 `HELD` without dual writer ownership or a persistent writer gap;
- Main released through `writer_lease_v4.release_main_writer`;
- final WriterLease is Main-owned `RELEASED`, epoch 2;
- final blocking writer count is 0;
- N6 replacement probe WorkUnit is `CANCELLED`.

Do not alter or repair these historical qualification states merely to improve diagnostics.

## Exact-turn V2 rule

For every covered Host Agent-control step in N0/N1/N2/N3/N4/N5/N6/N8:

- bind the exact current `turn_id`;
- prove Host `multi_agent_version=v2` for that turn;
- inspect the same-turn callable schema;
- preserve a privacy-safe contemporaneous schema snapshot before Agent-control;
- do not reconstruct a missing snapshot from later rollout evidence.

N8 recovery, if it becomes eligible, requires a fresh Advisor attempt and a fresh exact-turn V2 capability proof before spawn.

## Permanent operating boundaries

The operator owns Desktop Host lifecycle and UI actions. A Codex task must not terminate, restart, or update the Host that is executing it.

Issue #91 remains release evidence. This handoff remains continuity documentation. Do not turn either into a second runtime database.

A consumed qualification WorkUnit must not receive another child solely to repair diagnostics, evidence formatting, or report presentation.

Host tool acceptance alone does not prove semantic application. Use authoritative Host activity/lifecycle evidence for materialization, identity, guidance consumption, settlement, and effective permissions.

Requested/configured permission values must never substitute for Host-observed effective permission truth.

## Canonical truth owners

- `.codex-plugin/plugin.json`: Plugin version.
- `.codex-plugin/package-integrity.json`: shipped runtime byte manifest.
- `contracts/policy.json`: fixed policy/profile values.
- `contracts/state.md`: state model.
- `contracts/recovery.md`: retry/recovery semantics.
- `contracts/final-review.md`: final review boundary.
- `docs/v4/architecture.json`: Native Core ownership.
- `docs/v4/host-smoke.json`: N0-N8 machine Host oracle.
- `docs/release-checklist.md`: release gates and invalidation rules.
- `tasks/real-host-qualification-plan.md`: real Host procedure.
- `docs/v4/host-qualification-handoff.md`: detailed historical/current Host handoff through N6.
- GitHub branch/commit/CI: live source truth.
- Issue #91: durable external Host evidence journal.

## Next safe continuation

The next phase is permission RCA, not another N8 attempt.

Because this handoff update changes the branch HEAD, first perform a docs-only source rebind:

1. bind the new exact branch HEAD/tree after this commit;
2. verify the commit changed only `headoff.md`;
3. verify `.codex-plugin/package-integrity.json`, `contracts/policy.json`, and `docs/v4/host-smoke.json` remain unchanged, preserving the three qualification digests;
4. preserve N0-N7 conclusive evidence under the existing invalidation rules;
5. keep N8 blocked and H10 not started.

Then run only the privacy-safe Desktop permission persistence / prompt-time writeback diagnostic against fresh root `01a04caf-1a3a-7b11-b820-b28f98d4ba4c`:

1. zero Agent-control and zero repository mutation;
2. read only permission-related entries for the exact thread from Desktop persisted state, including the thread heartbeat permission tuple and relevant host-scoped permission-selection / agent-mode keys when present;
3. inspect only allowlisted Desktop/app-server log metadata for `thread/settings/update`, prompt-time settings writeback, `turn/start`, and resulting active permission profile;
4. do not emit prompts, messages, reasoning, environment values, raw complete payloads, or unrelated persisted state;
5. determine whether Read Only was never applied, was applied then overwritten at prompt submission, was acknowledged but ineffective, or persisted correctly but diverged from runtime;
6. classify the fault boundary as `UI_SELECTION_NOT_APPLIED`, `PROMPT_TIME_OVERWRITE`, `THREAD_SETTINGS_UPDATE_NOT_EFFECTIVE`, `PERSISTED_RUNTIME_DIVERGENCE`, or `UNKNOWN`;
7. record the conclusive diagnostic in Issue #91;
8. keep `n8_retry_eligible=false` until authoritative Host evidence proves a changed effective permission basis.

Do not create another Advisor merely to diagnose permission state. Do not enter H10.

When N8 eventually becomes eligible and passes, release closure still requires exact-source CI on the final source plus the required fresh final-source review before any `1.0.0` release/tag decision.
