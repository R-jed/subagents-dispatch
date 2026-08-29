# V4 Real Host Qualification Handoff

Updated: 2026-08-29

## Exact candidate

- Branch: `v4/rc5-native-core`
- HEAD before this handoff commit: `880578e62667596eb7e643a012ec457de38fb57e`
- Tree before this handoff commit: `6ba888f39014240e41f430058acc9ea058eb9f32`
- Host: `26.820.60940`
- Host build: `7119`
- Embedded Codex: `0.150.0-alpha.8`
- Root session/thread: `01a048f3-5f69-7000-9325-093dd895ae4c`

Qualification basis digests:

- runtime manifest: `a6fd674675fd0b4c2184dab7b0c0a3b85dd8ec0467756876067ae9d2874432ab`
- profile contract: `9520395880612c0c40ebc992d36cdadd950fd8328904f3e8c7641042c9f03a8d`
- Host contract: `0e9677ba7a66e8ea4a49b354a141098a26d62a3ed7051c50e2cbc7c42bab2566`

Important: this handoff file is outside the three Host qualification digest inputs. Updating this file changes source HEAD/tree and therefore requires exact-source repository CI and final-source review refresh, but does not automatically erase conclusive N0-N6 Host evidence under the release invalidation rules.

## Current qualification status

- N0 PASS
- N1 PASS
- N2 PASS
- N3 PASS
- N4 PASS
- N5 PASS
- N6 PASS
- N7 next
- N8 blocked until N7/H8 completes

Phase status:

- H0 complete
- H1/H2 N0 complete
- H3/N1 complete
- H4/N2 complete
- H5/N3 complete
- H6/N4 complete after one environmental recovery attempt
- H7/N5+N6 complete
- H8/N7 next
- H9/N8 blocked
- H10 release closure blocked

## Durable evidence ledger

Issue #91 is the append-only Host evidence journal.

Current-root / current-campaign evidence:

- H0 current-root binding: `5454591201`
- Solver active-state recovery: `5455135793`
- Solver N0 attempt 1 PASS: `5455373847`
- Advisor N0 attempt 1 PASS: `5458032103`
- H3/N1 initial partial stop: `5458140539`
- H3/N1 continuation PASS: `5458327377`
- H4/N2 PASS: `5458510689`
- H5/N3 PASS: `5458750261`
- H6/N4 attempt 1 environmental Host usage-limit stop: `5459388996`
- H6/N4 recovery attempt 2 PASS: `5459646454`
- H7/N5 PASS: `5460760790`
- H7/N6 PASS: `5460904293`

Earlier reusable evidence under same Host build/version/basis where explicitly retained by the campaign:

- previous H0: `5436646587`
- Reader N0 PASS: `5437155573`
- Worker durable PASS/RCA: `5439807120`
- Worker retained rerun evidence: `5438201247`
- Investigator N0 PASS: `5454249634`

## Reusable machine-contract facts

### N0

All five fixed managed profiles have conclusive route/model/effort/fresh-context evidence under the current Host build and qualification basis.

Profiles:

- Reader: `subagents_dispatch_reader`, `gpt-5.6-luna`, `max`, read-only
- Worker: `subagents_dispatch_worker`, `gpt-5.6-luna`, `max`, bounded write capability
- Investigator: `subagents_dispatch_investigator`, `gpt-5.6-terra`, `high`, read-only
- Solver: `subagents_dispatch_solver`, `gpt-5.6-sol`, `high`, bounded write capability
- Advisor: `subagents_dispatch_advisor`, `gpt-5.6-sol`, `high`, read-only profile intent
- All managed profiles use `fork_turns=none`.

### N1

All five fixed managed profiles passed leaf/delegation-depth checks. Effective assignments included the no-further-Agent boundary and adversarial nested-Agent instructions. Authoritative Host activity/identity evidence showed no nested Agent-control and no descendant materialization.

### N2

Canonical task address and Host child-thread identity binding passed.

Representative H4 Reader:

- WorkUnit: `N2_READER_HOST7119_H4_001`
- ExecutionBinding: `exec-n2-reader-host7119-h4-001`
- attempt: 1
- canonical task: `/root/sd_n2_reader_host7119_h4_001_a1`
- child thread: `01a04a7d-adfe-7782-8c9b-237641659503`
- runtime did not fabricate/persist a Host thread identity that public V2 did not expose.

### N3

Host admission rejection materialization safety passed.

Authoritative capacity used in the probe:

- root-inclusive active V2 session slots: 4
- product managed-child ceiling: 4
- three pressure Readers plus root filled Host active capacity
- target remained within product managed-child projection and received real Host rejection: `collab spawn failed: agent thread limit reached`

Rejected target:

- WorkUnit: `N3_REJECTED_WORKER_HOST7119_H5_001`
- ExecutionBinding: `exec-n3-rejected-worker-host7119-h5-001`
- WriterLease before spawn: `RESERVED`
- no successful spawn result
- no Started activity
- no Host thread identity
- no durable child identity
- no resident child runtime
- materialization verdict: `NOT_MATERIALIZED`
- provisional execution and reserved WriterLease rolled back
- attempt 1 not consumed
- target WorkUnit finished `CANCELLED`

### N4

Same-child steering, correction, interrupt, and continuation passed on recovery attempt 2.

Attempt history:

- attempt 1: `exec-n4-reader-host7119-h6-001`, `FAILED`, environmental `HOST_USAGE_LIMIT_FAILURE`
- attempt 2: `exec-n4-reader-host7119-h6-002`, qualification execution, `COMPLETED`, accepted

Attempt 2 identity:

- WorkUnit: `N4_READER_HOST7119_H6_001`
- canonical task: `/root/sd_n4_reader_host7119_h6_001_a2`
- child thread: `01a04b34-fece-7363-9518-60d067c21be0`

State sequence:

- initial: attempt 2, control epoch 0, followup 0
- RUNNING Steer via `followup_task`: epoch 0, followup 0, same child, guidance consumption proved by post-guidance Host rollout evidence
- focused correction: epoch 0 -> 1, followup 0 -> 1, same child
- interrupt: epoch 1 -> 2, authoritative same child `INTERRUPTED`
- continuation via `followup_task`: epoch 2 -> 3, followup remains 1, same child
- final: `COMPLETED`, accepted execution `exec-n4-reader-host7119-h6-002`
- no replacement child
- no attempt 3

### N5

Interrupt and settlement reconciliation passed.

N5 Worker:

- WorkUnit: `N5_WORKER_HOST7119_H7_001`
- ExecutionBinding: `exec-n5-worker-host7119-h7-001`
- attempt: 1
- canonical task: `/root/sd_n5_worker_host7119_h7_001_a1`
- child thread: `01a04c25-e25e-7311-bb9d-71ca51962b06`

WriterLease chain:

- allocation: `RESERVED`, epoch 1
- authoritative RUNNING: `HELD`
- prepare interrupt: control epoch 0 -> 1, lease `REVOKING`
- interrupt acknowledgement did not release writer
- stale control epoch 0 observation rejected with no state mutation
- current-generation proof: `host-observation:exec-n5-worker-host7119-h7-001:1:1:INTERRUPTED`
- stale lease epoch 2 against current epoch 1 rejected
- N5 ended with execution `INTERRUPTED`, WorkUnit `EXECUTING`, execution-owned WriterLease `REVOKING`

### N6

Writer takeover settlement passed without new Host Agent-control.

Negative tests:

- replacement allocation blocked by existing WriterLease: `blocking WriterLease must settle before another canonical-workspace execution`
- premature direct Main acquire blocked: `canonical workspace already has a blocking WriterLease`
- neither negative test mutated current writer state

Atomic transfer:

- production API: `execution_lifecycle_v4.takeover_to_main`
- old lease: `lease-n5-worker-host7119-h7-001`, epoch 1, execution-owned `REVOKING`
- new lease: `lease-main-n6-host7119-h7-001`, epoch 2, Main-owned `HELD`
- current-generation settlement proof was required before transfer
- single writer before and after
- no dual-writer state observed
- no persistent writer-gap state observed

Cleanup:

- Main lease released through `writer_lease_v4.release_main_writer`
- final WriterLease: Main-owned `RELEASED`, epoch 2
- final blocking writer count: 0
- qualification WorkUnit: `CANCELLED`
- retained execution lifecycle: `INTERRUPTED`
- Host Agent-control count during N6: 0

## Current runtime handoff state

At the H7 stop:

- no blocking WriterLease remains
- N5 qualification WorkUnit is `CANCELLED`
- N5 execution remains retained as authoritative `INTERRUPTED` history
- N6 replacement probe WorkUnit is `CANCELLED`
- N4 WorkUnit is `ACCEPTED`
- no N7/N8 work has started
- repository had remained clean through the N6 Host qualification result before this handoff documentation commit

## Exact-turn V2 capability rule

For N0/N1/N2/N3/N4/N5/N6/N8 covered Agent-control steps:

- bind exact current `turn_id`
- require Host `multi_agent_version=v2`
- require same-turn callable schema
- spawn schema requires `task_name` and `message`, contains `fork_turns`, excludes `fork_context`
- capture a contemporaneous privacy-safe snapshot before each covered Agent-control
- historical snapshot reuse is forbidden
- same numeric turn id may remain valid across multiple controls when a fresh contemporaneous snapshot is independently captured before each control
- unavailable/conflicting capability means `NOT_RUN_STOP` and zero covered action

N6 used no new Host Agent-control and therefore required no new Agent schema snapshot.

## Important recovery/invalidation lessons

- `docs/v4/host-smoke.json` is machine authority for N0-N8 product PASS/FAIL.
- procedure/diagnostic rules may fail closed for trustworthy evidence but cannot invent product gates.
- Host `COMPLETED` is lifecycle truth, not correctness acceptance.
- a consumed WorkUnit must not receive another child only to repair evidence presentation.
- explicit pre-materialization Host rejection may roll back a provisional execution and reserved writer without consuming an attempt, but only after no-materialization is proved.
- a materialized failed execution is retained; a genuine retry uses the same WorkUnit, a fresh ExecutionBinding, next attempt number, and changed execution basis.
- `UNKNOWN` writer ownership blocks replacement and takeover.
- interrupt acknowledgement does not release WriterLease.
- writer settlement requires current execution lifecycle plus exact current `control_epoch + lease_epoch` Host proof.
- Main takeover uses atomic settlement-transfer, not release-then-acquire.
- source changes outside the three qualification basis digests do not automatically invalidate conclusive Host observations, but exact-source repository CI and final-source review must refresh.

## Known environmental event

H6 attempt 1 was terminated by the Host account usage limit after successful materialization. This was recorded as an environmental qualification stop, not an N4 product failure. Capacity later recovered with current account evidence and attempt 2 passed N4.

## Next phase: H8 / N7 rollout reconciliation and privacy

Machine requirements:

- authoritative root rollout evidence binds lifecycle call id, child identity, and result
- allowlisted inspection omits assignment text and reasoning content
- ambiguous or stale rollout evidence cannot authorize acceptance or writer transfer

Procedure guidance:

- reuse authoritative rollout evidence already produced by N0-N6 where sufficient
- avoid new Agents unless the machine contract truly requires separately qualified evidence
- test the allowlisted inspection path itself, not raw sensitive rollout contents
- include a stale/ambiguous evidence negative case and show it cannot authorize acceptance or writer transfer
- stop after H8/N7; do not enter H9/N8 until explicitly instructed

## After N7

H9/N8 still requires a fresh Advisor bound to the exact final candidate and effective Host-observed strict read-only sandbox/permission truth. Requested Advisor profile intent alone is insufficient. Earlier Advisor N0 evidence disclosed broader Host rollout permissions and cannot substitute for N8.
