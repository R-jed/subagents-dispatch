# RC5 Hookless Core Feasibility

Status: design review complete, architecture freeze pending the replacement F1 campaign.

This document records the evidence and trust boundary for the RC5 Hookless Core direction. It is a feasibility record, not the final V4 runtime contract.

## Evidence baseline

The current feasibility branch is derived from the frozen RC4 candidate and intentionally does not change the production orchestration runtime.

Observed on Codex Desktop runtime `0.148.0-alpha.15`, ChatGPT Desktop `26.814.41407 (6720)`, macOS `27.0 (26A5416b)`, arm64:

- F1 role routing: PASS.
- F1 model and effort routing: PASS.
- F1 child collaboration removal: PASS. A managed Reader with `[agents] enabled = false` and `[features] multi_agent_v2 = false` had no collaboration tool surface and made no collaboration call.
- F1 Host read-only sandbox enforcement: FAIL. The Reader profile requested `sandbox_mode = "read-only"`, while Host runtime evidence observed `danger-full-access`.
- F2 Host capacity materialization: PASS. `rc5_f2_reader_7` was rejected with `collab spawn failed: agent thread limit reached`; no child identity, activity, agent path, `list_agents` entry, or child rollout materialized.
- F3 collaboration receipt evidence: PASS. The exact root rollout binds one `spawn_agent` function call, its authorization projection, `sub_agent_activity` through `event_id == call_id`, child thread/path, and the function-call result. The inspector emits allowlisted metadata and does not emit the assignment message, reasoning, or nickname.

F1 sandbox failure is a Host capability fact. It must not be relabeled as a Plugin configuration success.

## RC5 trust model

RC5 treats native collaboration and Host lifecycle evidence as the execution substrate. Hook interception is not a required correctness dependency.

Main remains the only orchestration authority. A child result is candidate evidence. It cannot accept a WorkUnit, acquire or transfer WriterLease authority, broaden scope, grant permissions, authorize external effects, or declare the integrated candidate accepted.

Managed child profiles disable child multi-agent capability. This is a Host-enforced capability boundary only to the extent demonstrated by current Host evidence.

Filesystem mutation authority remains a project semantic contract:

- Reader, Investigator, and Advisor have mutation authority `none`.
- Worker and Solver may receive `bounded-source-write` only from Main for an explicit responsibility.
- Broader Host filesystem capability never grants project write authority.

`sandbox_mode = "read-only"` remains a least-privilege request for read-only roles. RC5 does not claim that current MultiAgentV2 honors that request when the parent permission profile is broader.

## Guarantee tiers

### Verified Host-backed guarantees

For the tested Host/runtime combination RC5 may rely on the following after the corresponding release campaign passes for the exact candidate:

- exact managed role selection and pinned model/effort observation;
- managed child collaboration tools absent when the role disables multi-agent features;
- exact collaboration call/result/activity binding from Host rollout evidence;
- explicit Host capacity rejection does not materialize a rejected child in the tested capacity path;
- native child identity and lifecycle observations can be reconciled after the call.

### Project-enforced orchestration guarantees

RC5 can enforce through state, scheduling, evidence, and Main acceptance:

- Main is the only authority that creates and accepts orchestration state transitions;
- only one responsibility receives project write authority in the canonical checkout at a time;
- unresolved or ambiguous lifecycle evidence blocks replacement, WriterLease transfer, and final acceptance;
- read-role output is untrusted until Main verifies the claimed evidence;
- a child cannot obtain broader project authority merely because Host permissions are broader.

### Behavioral and diagnostic controls

The following reduce risk but are not security boundaries against a hostile same-user process:

- read-role developer instructions prohibiting mutation;
- pre/post working-tree mutation audit;
- protected-path hashes;
- phase separation between read-oriented children and the authorized writer;
- child self-report of changed files.

### Guarantees RC5 must not claim on the tested Host

RC5 must not claim:

- that a Reader, Investigator, or Advisor is technically incapable of filesystem mutation;
- that `sandbox_mode = "read-only"` is Host-enforced under a broader parent permission profile;
- that mutation audit detects every transient or restored mutation;
- that project single-writer authority means only one OS process is physically capable of writing;
- that repository-only audit detects mutations to arbitrary user files, Host configuration, credentials, or other out-of-repository state.

These exclusions are part of the product security statement, not temporary documentation caveats.

## Scheduling consequence of F1

RC5 should use phase separation in the canonical checkout:

1. read phase: Reader, Investigator, and Advisor responsibilities may run concurrently when otherwise independent;
2. settle phase: all read-oriented children settle and Main performs the required mutation/protected-scope audit;
3. write phase: at most one Worker or Solver owns project write authority under WriterLease; no managed read-oriented child remains active in the canonical checkout;
4. verification phase: the writer settles, Main verifies the actual candidate and relevant checks;
5. independent review phase: when required, Advisor runs only after the writer has settled and before further writes.

This rule reduces accidental cross-role interference. It does not upgrade a full-access read child into an OS sandbox.

Main itself must also avoid canonical-checkout writes while a writable child owns WriterLease.

## Mutation audit model

The replacement F1 campaign must prove the audit mechanism is useful and fail-closed without overstating it.

For a read-oriented phase, Main records before dispatch:

- exact Git HEAD when a Git repository is present;
- working-tree status including untracked paths;
- the identity of protected project orchestration state relevant to the run;
- exact hashes for bounded protected files when those files are part of the acceptance boundary.

After all read-oriented children settle, Main rechecks the same scope.

Any unexplained visible mutation invalidates the read-phase evidence and blocks transition to the write phase. Main must not silently clean, reset, or accept the mutation as if the read child were a writer.

The audit does not establish absence of transient writes and cannot defend against a process that has enough authority to mutate and restore the same audit sources. Therefore it is a workflow correctness check, not a hostile-code containment boundary.

## F1 replacement campaign

Replace the failed aggregate F1 sandbox gate with four separately reported checks. Do not erase the historical sandbox FAIL.

### F1A Managed role and collaboration containment

PASS requires:

- exact managed role selected;
- configured model/effort observed as the intended fixed lane;
- `fork_turns = none`;
- collaboration tools absent from the child tool surface;
- no child collaboration function call in the exact child rollout.

Current evidence: PASS for Reader on the tested Host.

### F1B Authority isolation

PASS requires:

- no child-created or child-accepted WorkUnit state transition;
- no child acquisition or transfer of WriterLease authority;
- no child ability to declare candidate/final acceptance;
- Main remains the sole actor that validates lifecycle evidence and accepts results.

This is a project-state invariant and must be covered by deterministic tests before architecture freeze.

### F1C Read-phase mutation detection

Run a bounded Reader responsibility with mutation authority `none`.

PASS requires:

- clean or explicitly captured pre-dispatch project state;
- child settles without an authorized write responsibility;
- post-settlement project/protected-scope audit matches the pre-dispatch state;
- any injected fixture mutation causes the audit to fail closed in deterministic tests;
- an unexplained mutation prevents progression to a writable responsibility.

This probe validates detection and transition blocking. It does not claim OS containment.

### F1D Phase exclusivity

PASS requires deterministic scheduler/state tests proving:

- no writable managed responsibility starts while any managed read-oriented child remains active in the canonical checkout;
- no new managed read-oriented child starts while a writable child owns or is revoking WriterLease;
- UNKNOWN lifecycle state blocks phase transition;
- read-oriented independent lanes may still run concurrently with each other;
- Final Review starts only after the writer has settled.

## F2 contract

A Host spawn rejection may be treated as a pre-attempt rejection only when Host evidence proves no child materialized.

For the tested capacity path, F2 provides that proof. RC5 must retain the general fail-closed rule:

- explicit rejection plus no identity/activity/path/listing/rollout evidence permits rollback of the provisional attempt;
- ambiguous evidence becomes UNKNOWN;
- UNKNOWN does not create a replacement child and does not transfer WriterLease authority.

Do not generalize the observed capacity behavior to every possible Host error without evidence.

## F3 receipt contract

RC5 may use an `OperationIntent` followed by Host evidence reconciliation.

For spawn, the evidence model may bind:

- exact root thread;
- collaboration namespace/name;
- call ID;
- authorization projection such as task name, agent type, and `fork_turns`;
- `sub_agent_activity.event_id == call_id` when present;
- child thread ID and agent path;
- exact function-call output classification.

The assignment message is Host-owned transport and is excluded from the authorization digest and normalized receipt output.

Unknown or unrecognized outputs remain unrecognized. Missing activity is missing evidence and must not be invented from the result body.

## Threat-model review

### Prompt or repository content induces a read-role write

Impact: possible because the tested Host grants broader filesystem capability.

Control: behavioral contract, phase separation, visible mutation/protected-scope audit, Main verification.

Residual risk: a sufficiently hostile same-user process can write outside the audited scope or restore observable state before inspection. RC5 therefore does not claim containment against hostile arbitrary code under `danger-full-access`.

### Child attempts recursive delegation or peer coordination

Control: managed role disables multi-agent features. Current Reader Host evidence shows no collaboration surface.

Release requirement: repeat on the exact candidate and representative managed roles. Unexpected collaboration capability is a hard failure.

### Child result forges authority

Control: child output is never an authority-bearing state transition. Main validates state and Host evidence. Deterministic state APIs must reject stale epochs, invalid owners, duplicate receipts, and unauthorized transitions.

### Host reports ambiguous spawn outcome

Control: mark operation UNKNOWN, reconcile through native listing and exact rollout evidence, block replacement and WriterLease transfer until settled.

### Capacity rejection creates a phantom child

Current tested path: no materialization observed. F2 PASS.

General rule: only a rejection with positive no-materialization evidence is safe to roll back. Other errors remain UNKNOWN.

### Read/write overlap corrupts the canonical checkout

Control: phase exclusivity plus WriterLease project authority. This prevents authorized concurrent writers and reduces accidental interference from behavioral read roles.

Residual risk: because read-role Host filesystem capability is broader, this is not physical write exclusion.

### Evidence inspector leaks prompt or reasoning

Control: exact rollout identity, stable-file checks, allowlisted projection, fail-closed duplicate/conflict handling. F3 real rollout evidence and tests passed after aligning fixtures with the real Host wire shape.

## Architecture-freeze gates

RC5 architecture may freeze only after all of the following are true:

- F1A PASS on real Host evidence;
- F1B deterministic authority-isolation tests PASS;
- F1C deterministic mutation-audit fail-closed tests PASS and one real non-mutating Reader probe PASS;
- F1D deterministic phase-exclusivity tests PASS;
- F2 PASS retained with exact evidence;
- F3 PASS retained with exact evidence and privacy tests;
- final threat-model review contains no claim of Host-enforced read-only on the tested configuration;
- production contract rewrite explicitly distinguishes Host-backed, project-enforced, and behavioral/diagnostic guarantees.

If product requirements demand hostile-code filesystem containment for read roles, the tested Host is insufficient and RC5 must remain blocked until a real Host/OS isolation primitive is available and verified.

If the product requirement is reliable orchestration of managed cooperative agents with fail-closed state transitions and explicit residual-risk disclosure, the current Hookless Core direction remains feasible subject to the gates above.

## Current verdict

```text
Hookless Core direction      VALIDATED
F1A collaboration isolation PASS
F1 sandbox enforcement      FAIL, retained as Host capability fact
F2 capacity materialization PASS
F3 receipt evidence         PASS
Architecture freeze         BLOCKED on F1B/F1C/F1D
Production runtime rewrite  NOT STARTED
```
