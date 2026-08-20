# RC5 Hookless Core Design Freeze

Status: FROZEN FOR IMPLEMENTATION

Frozen from feasibility branch after Host campaign on Codex Desktop runtime `0.148.0-alpha.15`, Desktop build `26.814.41407 (6720)`, macOS `27.0 (26A5416b)`, arm64.

## Decision

V4 RC5 removes Hook interception from the correctness path. The product is an orchestration system over Codex Native Subagents. It does not claim to be a Host security monitor.

The required runtime shape is:

```text
Main
  -> validates responsibility and authority
  -> prepares OperationIntent
  -> invokes native collaboration tool
  -> records OperationReceipt from Host result
  -> reconciles native lifecycle evidence when needed
  -> verifies artifact/mutation outcome
  -> alone accepts or rejects work
```

`hooks/hooks.json`, `orchestration_guard.py`, PendingControl PreToolUse consumption, PostToolUse acknowledgement, and Hook-owned lifecycle authorization are not part of the RC5 core design.

## Feasibility evidence

### F1 managed child capability surface

Host campaign thread: `01a02040-93bc-7da1-8f74-2f81f05b4666`.

Reader spawn call: `call_YPEaDdIm3ls66Sp2IJ6agnIe`.

Confirmed:

- exact managed Reader role selected;
- observed model `gpt-5.6-luna`;
- observed reasoning effort `max`;
- `fork_turns = none`;
- child collaboration tools were absent;
- child made no collaboration function calls;
- child changed no repository files.

Host limitation confirmed:

- role requested `sandbox_mode = read-only`;
- actual child permission state was `danger-full-access` because MultiAgentV2 reapplies the live parent/environment permission profile after role configuration.

Therefore a configured read-only profile remains least-privilege intent and optional Host hardening. RC5 correctness does not depend on Host honoring that sandbox request.

### F2 Host capacity rejection

The same Host campaign kept five Reader children running and attempted `rc5_f2_reader_7`.

Rejected call: `call_1nrAGaV4Fp4xKg1lavfH9fqI`.

Host result: `collab spawn failed: agent thread limit reached`.

Confirmed after rejection:

- no child identity;
- no `sub_agent_activity`;
- no agent path;
- no `list_agents` entry;
- no child rollout;
- no other materialization evidence.

RC5 may treat an explicit, reconciled pre-materialization Host rejection as no child attempt. Ambiguous failure remains `UNKNOWN` and never authorizes replacement work.

### F3 collaboration receipt evidence

The exact root rollout binds:

```text
function_call
  call_id
  task_name
  agent_type
  fork_turns

sub_agent_activity
  event_id == call_id
  child thread id
  child path
  kind

function_call_output
  call_id
  recognized Host result
```

The allowlisted inspector emits no assignment body, reasoning, nickname, transcript body, or arbitrary tool output.

This is sufficient for post-call `OperationReceipt` and recovery reconciliation without Hook interception.

## Trust model

### Host-owned truth

Codex Native Subagents own:

- whether a collaboration call is accepted or rejected;
- materialized child identity and path;
- current native lifecycle status;
- runtime model/effort/permission evidence when exposed;
- Host capacity limits.

### subagents-dispatch-owned truth

Main and the bounded state capsule own:

- WorkUnit responsibility;
- TeamPlan revision;
- ExecutionBinding generation;
- mutation authority and write scope;
- WriterLease;
- OperationIntent;
- OperationReceipt and reconciliation status;
- acceptance and retry accounting.

A child result is candidate evidence. It never grants authority, transfers WriterLease, accepts a WorkUnit, or proves its own runtime route.

## Capability containment

Reader, Investigator, and Advisor have mutation authority `none`.

Worker and Solver may receive `bounded-source-write` only from Main and only inside declared scope.

All managed child profiles disable child multi-agent capability:

```toml
[agents]
enabled = false

[features]
multi_agent_v2 = false
```

This Host-visible capability boundary is required for RC5. The behavioral instruction to create no further subagents remains defense in depth.

## Phase isolation

Because current MultiAgentV2 can inherit `danger-full-access` into a role that requested read-only, RC5 does not run a behavioral read-only child concurrently with a writing child in the canonical checkout.

Canonical-checkout phases are:

```text
READ / INVESTIGATION PHASE
  Reader / Investigator / Advisor may run in parallel
  active writing child = 0

barrier
  all read-phase children settled
  repository mutation audit passes

WRITE PHASE
  at most one Worker or Solver owns WriterLease
  all other managed children = 0
  Main performs no conflicting write

barrier
  writer settled
  declared-scope mutation verification passes

FINAL REVIEW PHASE
  Advisor may run
  active writing child = 0
```

Main may perform read-only inspection while a writer owns WriterLease, but no other managed child is admitted until that writer settles.

## Mutation audit

Hard read-only sandbox is not assumed. For every behavioral read-only phase, Main records enough repository state to detect unauthorized mutation before accepting the phase or starting a writer.

Minimum checks:

- repository HEAD identity when applicable;
- tracked working-tree changes;
- untracked paths;
- protected orchestration/runtime state paths;
- any task-specific protected path hashes required by acceptance.

For a role with mutation authority `none`, unexplained mutation invalidates the child result and blocks the phase barrier.

For a writer, mutations outside granted write scope invalidate the result and block acceptance.

Mutation audit detects repository effects. It is not described as an OS sandbox and does not claim to prevent a malicious full-access process from altering arbitrary external user files. Tasks that require hard OS-level read-only isolation remain blocked unless the Host proves such isolation.

## WriterLease

WriterLease remains a Main-side scheduling invariant.

A writable ExecutionBinding reserves the lease before its native spawn. The lease remains blocking across `RUNNING`, `INTERRUPTED`, `UNKNOWN`, and takeover revocation until native evidence proves the prior writer settled.

`UNKNOWN` never releases or transfers write ownership.

Hook evidence is not required for WriterLease settlement. Settlement uses explicit Host lifecycle observation and, when ambiguity exists, exact rollout reconciliation.

## OperationIntent

PendingControl is replaced in RC5 by `OperationIntent`.

Required fields:

```text
operation_id
unit_id
execution_id
operation
 target
 authorization_digest
expected_team_plan_revision
expected_control_epoch
next_control_epoch
expected_lease_epoch
writer_effect
state = PREPARED | UNKNOWN
```

The authorization digest covers stable lifecycle authorization fields only:

- spawn: `task_name`, `agent_type`, `fork_turns`;
- followup: `target`;
- interrupt: `target`.

Host-owned message transport is required to be present where the native tool requires it, but message contents do not enter the digest.

There is no synthetic `IN_FLIGHT` state because the Plugin cannot reliably observe the exact instant the Host handler begins mutation.

## OperationReceipt

A successful or explicitly rejected native call creates an immutable receipt bound to its OperationIntent.

Minimum fields:

```text
operation_id
execution_id
operation
target
authorization_digest
call_id
result = accepted | rejected | reconciled
source = native_result | runtime_rollout | host_reconciliation
child_thread_id? 
child_path?
host_status?
control_epoch
```

If the process or Host result is ambiguous after mutation may have occurred:

```text
OperationIntent -> UNKNOWN
ExecutionBinding -> UNKNOWN when lifecycle truth is affected
WriterLease -> remains blocking when writer truth is affected
```

Recovery then uses `list_agents` and the allowlisted root collaboration inspector. Replacement work is forbidden until ambiguity is resolved.

## Capacity policy

subagents-dispatch enforces only its product ceilings and phase rules. It does not require a fresh authoritative Host-capacity token before every spawn.

Host capacity rejection is handled as follows:

- explicit rejection + reconciliation proving no materialized child: record rejected receipt, no fresh-attempt consumption;
- any materialization evidence or ambiguity: `UNKNOWN`, no replacement.

`list_agents` remains useful for Status, reconciliation, takeover settlement, crash recovery, and diagnostics.

## Child-to-child communication

RC5 has no child-to-child coordination protocol. Main is the sole coordinator.

Managed children do not own collaboration tools. If a future Host exposes them despite the managed profile contract, the runtime capability check fails closed for that Host/build.

## Claims RC5 may make

RC5 may claim:

- fixed managed role/model/effort configuration;
- fresh-context managed child spawn with `fork_turns = none`;
- managed child multi-agent capability disabled when verified by Host campaign;
- parent-controlled responsibility, mutation authority, WriterLease, acceptance, retry, and phase ordering;
- exact post-call Host receipt and optional rollout reconciliation;
- mutation verification before behavioral read-only phase acceptance and before writer admission;
- one active writer in the canonical checkout.

RC5 must not claim:

- arbitrary native spawn is technically impossible outside Main policy;
- Hook interception protects every lifecycle call;
- configured `sandbox_mode = read-only` proves Host-enforced read-only;
- a managed read-only child is technically incapable of filesystem mutation under a full-access parent;
- mutation audit is an OS security sandbox.

## Replacement F1 release gate

The old aggregate F1 sandbox requirement is retired.

The RC5 capability-containment gate passes only when all of the following are verified on the release Host/build:

1. exact role/model/effort route;
2. `fork_turns = none`;
3. managed child collaboration capability absent;
4. no child collaboration function calls;
5. mutation-authority contract encoded in state/role responsibility;
6. behavioral read-only phase cannot cross the writer barrier until all children settle and mutation audit passes;
7. child output cannot directly accept work or transfer WriterLease;
8. hard sandbox state, when observed, is reported separately and never inferred from configuration.

## Implementation order

1. introduce `OperationIntent` / `OperationReceipt` validation and tests beside the existing RC4 control module;
2. extend V4 state schema to store intents/receipts without Hook `tool_use_id` semantics;
3. migrate spawn/followup/interrupt lifecycle transitions;
4. add phase-isolation and mutation-audit gates;
5. move runtime collaboration inspector into recovery/release attestation paths;
6. remove Hook runtime and PendingControl production dependencies;
7. remove dead Hook contracts/tests and update package integrity;
8. run the new Native Core Host campaign before release.

## Freeze rule

This design is frozen for implementation. Material changes to these boundaries require a new explicit architecture decision:

- restoring Hook to the correctness path;
- permitting read-only and writable managed children concurrently in one canonical checkout while Host read-only is unproven;
- allowing child-to-child collaboration;
- releasing WriterLease on `UNKNOWN`;
- treating configured sandbox as observed enforcement;
- accepting ambiguous Host materialization as a safe rejection.
