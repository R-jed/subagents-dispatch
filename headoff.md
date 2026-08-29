# Headoff

Updated: 2026-08-29.

## Purpose

This is the durable development-session handoff for `subagents-dispatch`.

It is a project continuity record only. It is not Plugin runtime, a product contract, a Host qualification input, release evidence, or a release gate. Canonical product and qualification truth remains in the files named below and in Issue #91.

Detailed current V4 Host campaign handoff:

- `docs/v4/host-qualification-handoff.md`

Use that file for the full N0-N6 evidence map and retained runtime identities. This root handoff keeps the current project direction, safe continuation point, and highest-value reusable facts concise.

## Project summary

`subagents-dispatch` is a bounded orchestration layer over Codex Native Subagents.

Main owns dispatch judgment, integration, irreversible effects, writer takeover, and final acceptance.

Fixed managed profiles:

- Reader: `subagents_dispatch_reader`, `gpt-5.6-luna`, `max`, read-only.
- Worker: `subagents_dispatch_worker`, `gpt-5.6-luna`, `max`, bounded source write.
- Investigator: `subagents_dispatch_investigator`, `gpt-5.6-terra`, `high`, read-only.
- Solver: `subagents_dispatch_solver`, `gpt-5.6-sol`, `high`, bounded source write.
- Advisor: `subagents_dispatch_advisor`, `gpt-5.6-sol`, `high`, read-only profile intent.

All managed children use `fork_turns=none`, are intended to remain leaf Agents, and are subject to the product managed-child ceiling of four.

Core ownership:

- WorkGraph / WorkUnit own responsibility, dependencies, readiness, and acceptance.
- ExecutionBinding owns one concrete managed attempt/generation.
- WriterLease owns canonical-workspace writer coordination.
- Codex Host owns actual materialization, lifecycle, capacity, child identity, effective permissions/sandbox, and collaboration capability.
- Host `COMPLETED` is lifecycle evidence, not correctness acceptance.
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
- H7: COMPLETE
- H8 / N7: NEXT
- H9 / N8: BLOCKED until N7 completes
- H10 release closure: BLOCKED until Host campaign and final release gates complete

Public `1.0.0` remains blocked on N7, N8, and release closure.

No N7 or N8 qualification work has started at this handoff point.

## Qualification basis and environment

Host qualification evidence through N6 was produced against shipped source:

- branch: `v4/rc5-native-core`
- qualification source HEAD: `880578e62667596eb7e643a012ec457de38fb57e`
- qualification source tree: `6ba888f39014240e41f430058acc9ea058eb9f32`
- Host: `26.820.60940`
- Host build: `7119`
- embedded Codex: `0.150.0-alpha.8`
- root session/thread: `01a048f3-5f69-7000-9325-093dd895ae4c`

Qualification basis digests:

- runtime manifest SHA256: `a6fd674675fd0b4c2184dab7b0c0a3b85dd8ec0467756876067ae9d2874432ab`
- profile contract SHA256: `9520395880612c0c40ebc992d36cdadd950fd8328904f3e8c7641042c9f03a8d`
- Host contract SHA256: `0e9677ba7a66e8ea4a49b354a141098a26d62a3ed7051c50e2cbc7c42bab2566`

Documentation-only handoff commits after `880578e...` are outside the three Host qualification digest inputs. Under the current release invalidation rules they require exact-source repository CI and final-source review refresh, but do not automatically erase conclusive N0-N6 Host evidence. Always re-check the three digests before relying on that reuse rule.

## Durable evidence ledger

Issue #91 is the append-only Host evidence journal.

Current-root/current-campaign evidence:

- H0 current-root binding: `5454591201`
- Solver active-state recovery: `5455135793`
- Solver N0 attempt 1 PASS: `5455373847`
- Advisor N0 attempt 1 PASS: `5458032103`
- H3/N1 initial partial stop: `5458140539`
- H3/N1 continuation PASS: `5458327377`
- H4/N2 PASS: `5458510689`
- H5/N3 PASS: `5458750261`
- H6/N4 attempt 1 Host usage-limit environmental stop: `5459388996`
- H6/N4 recovery attempt 2 PASS: `5459646454`
- H7/N5 PASS: `5460760790`
- H7/N6 PASS: `5460904293`

Earlier evidence explicitly reused by the current campaign:

- Reader N0 PASS: `5437155573`
- Worker durable PASS/RCA: `5439807120`
- Worker retained rerun evidence: `5438201247`
- Investigator N0 PASS: `5454249634`

Do not promote unrelated historical evidence merely because Host build/version match. Reuse must follow the current release invalidation rules and the durable campaign rationale.

## Highest-value reusable facts

### Exact-turn V2 rule

For every covered Host Agent-control step in N0/N1/N2/N3/N4/N5/N6/N8:

- bind the exact current `turn_id`;
- prove Host `multi_agent_version=v2` for that turn;
- inspect the same-turn callable schema;
- preserve a privacy-safe contemporaneous schema snapshot before Agent-control;
- do not reconstruct a missing snapshot from later rollout evidence.

The same numerical `turn_id` may remain current across multiple controls. What matters is a fresh contemporaneous snapshot before each covered control, not forcing a different turn id.

### N2 identity

Representative accepted H4 Reader:

- WorkUnit: `N2_READER_HOST7119_H4_001`
- ExecutionBinding: `exec-n2-reader-host7119-h4-001`
- canonical task: `/root/sd_n2_reader_host7119_h4_001_a1`
- Host child thread: `01a04a7d-adfe-7782-8c9b-237641659503`

Canonical task address plus authoritative Host child-thread evidence establishes release-campaign native identity. Ordinary runtime state must not fabricate/persist a Host thread id that public V2 did not expose.

### N3 admission rejection

The accepted N3 probe established:

- Host capacity source: root-inclusive active V2 session slots = 4;
- product managed-child ceiling = 4;
- root + three running pressure Readers filled Host active capacity;
- the target remained within product managed-child projection and received actual Host rejection: `collab spawn failed: agent thread limit reached`;
- rejected target had no successful spawn result, Started activity, Host thread identity, durable child identity, or resident child runtime;
- provisional ExecutionBinding and RESERVED WriterLease rolled back;
- attempt 1 was not consumed.

Do not invent whether an undifferentiated Host thread-limit error is active-pressure or residency-pressure.

### N4 same-child control

H6 attempt 1 materialized and later failed because of Host account usage capacity. That is retained environmental failure evidence, not an N4 product defect.

Recovery attempt 2 passed N4:

- ExecutionBinding: `exec-n4-reader-host7119-h6-002`
- attempt: 2
- canonical task: `/root/sd_n4_reader_host7119_h6_001_a2`
- child thread: `01a04b34-fece-7363-9518-60d067c21be0`
- RUNNING Steer used `followup_task`, preserved epoch/followup counters, and had post-guidance same-child consumption evidence;
- focused correction advanced epoch `0 -> 1` and followup `0 -> 1`;
- interrupt advanced epoch `1 -> 2` and authoritative lifecycle became `INTERRUPTED`;
- continuation used `followup_task`, advanced epoch `2 -> 3`, retained followup count 1, and resumed the same child;
- no replacement child and no attempt 3;
- final accepted execution is attempt 2.

### N5/N6 WriterLease chain

N5 Worker:

- WorkUnit: `N5_WORKER_HOST7119_H7_001`
- ExecutionBinding: `exec-n5-worker-host7119-h7-001`
- canonical task: `/root/sd_n5_worker_host7119_h7_001_a1`
- child thread: `01a04c25-e25e-7311-bb9d-71ca51962b06`

N5 proved:

- allocation WriterLease `RESERVED`, epoch 1;
- authoritative RUNNING moved it to `HELD`;
- prepare interrupt moved control epoch `0 -> 1` and lease to `REVOKING`;
- interrupt acknowledgement alone did not release writer ownership;
- stale control-generation observation was rejected with no state mutation;
- current proof was `host-observation:exec-n5-worker-host7119-h7-001:1:1:INTERRUPTED`;
- stale lease epoch was rejected;
- N5 stopped with execution `INTERRUPTED` and execution-owned `REVOKING` lease.

N6 then proved without new Host Agent-control:

- replacement allocation was blocked by the existing WriterLease;
- premature direct Main writer acquisition was blocked;
- `execution_lifecycle_v4.takeover_to_main` atomically transferred the settled execution-owned epoch-1 lease to a Main-owned epoch-2 `HELD` lease;
- no dual-writer state and no persistent writer gap were observed;
- Main released its qualification lease through `writer_lease_v4.release_main_writer`;
- final WriterLease is Main-owned `RELEASED`, epoch 2;
- final blocking writer count is 0;
- N5 qualification WorkUnit is `CANCELLED`;
- retained N5 execution lifecycle remains `INTERRUPTED`;
- N6 replacement probe WorkUnit is `CANCELLED`.

This is the runtime state to preserve when entering H8/N7.

## Permanent operating boundaries

The operator owns Desktop Host lifecycle and UI actions. A Codex task must not terminate/restart the Host that is executing it.

If a Host restart or replacement root is required, stop with `OPERATOR_ACTION_REQUIRED_STOP`, state the exact manual operator action and resume condition, and let the operator perform it outside the qualifying task.

Issue #91 remains release evidence. This handoff remains continuity documentation. Do not turn either into a second runtime database.

A consumed qualification WorkUnit must not receive another child solely to repair diagnostics, evidence formatting, or report presentation.

Host tool acceptance alone does not prove semantic application. Use authoritative Host activity/lifecycle evidence for materialization, identity, guidance consumption, settlement, and effective permissions.

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
- `docs/v4/host-qualification-handoff.md`: detailed current campaign handoff through N6.
- GitHub branch/commit/CI: live source truth.
- Issue #91: durable external Host evidence journal.

## Next safe continuation

Next phase is `H8 / N7 rollout reconciliation and privacy`.

Before doing N7:

1. read the current exact `docs/v4/host-smoke.json`, `tasks/real-host-qualification-plan.md`, release invalidation rules, and rollout inspection tooling;
2. bind the live branch HEAD/tree and verify the three Host qualification digests remain unchanged after documentation-only handoff commits;
3. refresh exact-source repository CI requirements caused by the documentation-only HEAD change, without re-running N0-N6 solely because the handoff docs changed;
4. reuse authoritative rollout evidence already generated by the campaign where it satisfies N7;
5. avoid creating a new Agent unless the N7 machine oracle truly requires evidence absent from the existing campaign;
6. prove allowlisted inspection binds lifecycle call id, child identity, and result while omitting assignment text and reasoning content;
7. prove stale or ambiguous rollout evidence cannot authorize acceptance or writer transfer;
8. record one consolidated H8/N7 result in Issue #91;
9. hard stop after H8/N7 and await explicit H9/N8 instruction.

Do not enter N8 early. N8 requires a fresh Advisor review bound to the final exact candidate and authoritative effective Host sandbox/permission truth.
