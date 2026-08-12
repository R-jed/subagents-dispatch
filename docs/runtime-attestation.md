# Runtime Attestation

This document defines how subagents-dispatch proves the actual runtime route of one managed Codex child when model, reasoning effort, sandbox, ancestry, or role identity is part of acceptance or release validation.

It is an explicit diagnostic protocol. Ordinary Dispatch does not run it, scan Codex sessions, collect transcripts, or create background telemetry.

Bundled Python helpers used by this protocol require Python 3.11 or newer. Before invoking one, resolve a supported interpreter from the actual task environment according to `docs/python-runtime.md`, record the resolved invocation, `sys.executable`, and Python version, and keep that interpreter fixed for the attestation operation. Interpreter command-name resolution is environment adaptation; it does not authorize role, model, Agent-type, permission-evidence, or acceptance substitution. If no supported interpreter is available, stop before child spawn and report `PYTHON_PREREQUISITE_UNMET`; downstream Host gates are not tested by that failed environment precondition.

## Evidence model

Keep these facts separate:

```text
Configured route
-> contracts/policy.json and the exact managed Agent profile describe intended model, effort, and agent_type

Behavioral authority
-> role mutation_authority describes whether the responsibility may mutate source

Requested
-> the actual spawn request selects the exact managed agent_type

Accepted
-> the Host acknowledges/creates the requested role and child identity when that fact is exposed

Observed
-> the running Host records the actual child route and runtime settings
```

Configured is not Observed. Requested is not Observed. Accepted is not Observed. A child's prose claim about its own model, effort, permissions, identity, or ancestry is not Observed evidence.

For child attestation, Observed evidence may come from two Host-produced sources:

```text
native
-> public Host/spawn/details runtime metadata

local
-> one exact Codex rollout inspected by scripts/inspect-agent-runtime.py
```

`local` here means a Host-produced local runtime record. It never means profile TOML, `policy.json`, a hand-written JSON object, copied configuration, remembered values, or child output.

The normalizer reports three independent assurance dimensions:

```text
route_assurance
-> exact child and parent identity, managed role/agent_type, model, and reasoning effort

permission_state_assurance
-> the sandbox_policy_type and permission_profile_type that actually applied to the child

permission_provenance_assurance
-> the effective source kind and identity, source permission, source evidence, and Host selection evidence
```

Each dimension is `verified`, `unknown`, or `failed`. They are not collapsed into one overall attestation result. A claim passes only when every dimension declared required for that claim is verified.

## Public Host evidence first

Use public Host/spawn/details metadata first whenever it exposes the required field. Bind every observation to the exact child identity and expected parent/root thread when those identities are available.

Public acceptance of an exact `agent_type` proves role acceptance only. It does not prove the observed model, effort, sandbox, or permission profile unless the Host explicitly reports those runtime facts.

## Exact rollout fallback

If public Host metadata omits a required child-runtime field and the local Codex rollout is accessible, pass the exact child UUID and sessions directory to `runtime-evidence.py`. It loads the bundled Python inspector directly; no shell runtime is required. The standalone inspector remains available for focused diagnostics:

```text
<python-3.11+> scripts/inspect-agent-runtime.py <child-thread-id> \
  --expected-parent-thread-id <root-thread-id> \
  --expected-agent-role <exact-agent-type>
```

`<python-3.11+>` is the already resolved interpreter invocation from `docs/python-runtime.md`; it is a protocol placeholder, not a literal executable name.

By default the inspector resolves the Codex sessions directory from `$CODEX_HOME` or `~/.codex`. `--codex-home <path>` may select another Codex home explicitly.

The inspector:

- requires a canonical lowercase child UUID;
- uses `session_meta.id` as the concrete rollout/thread identity for exact child binding; `session_meta.session_id`, when present, may be a distinct canonical UUID for a broader live session and is not used as child identity;
- establishes ancestry from `parent_thread_id`; `session_id` is not copied into Observed route facts;
- selects exactly one `rollout-...-<child-id>.jsonl` file;
- rejects no match, duplicate exact matches, symlinked matched files, identity mismatch, and unexpected path escape;
- requires exactly one `session_meta` record and at least one `turn_context` record;
- can bind the rollout to an expected parent thread and exact managed role;
- rejects conflicting model, effort, sandbox-policy, or permission-profile values across child turns;
- leaves a field unobserved when any relevant turn omits it instead of inferring a stable value from partial data;
- emits only allowlisted routing metadata.

The allowlist is:

```text
thread_id
parent_thread_id
agent_role
agent_path
model_provider
model
effort
sandbox_policy_type
permission_profile_type
cwd
runtime_version
```

The inspector does not emit prompts, assistant messages, tool payloads, hidden reasoning, source contents, or rollout paths. `cwd` is emitted only as an allowlisted runtime field and must be unique across all `turn_context` records.

## Normalize and compare

Build `expected` from `contracts/policy.json` and the exact child/root identities. For formal five-role live-route validation set:

```text
runtime_observation_required = true
requires_permission_observation = true
```

Set `requires_permission_provenance=true` only when the intended claim is about the Host permission source or source-selection decision. Model/effort calibration and ordinary product-route checks require route plus actual permission state, not unavailable Host-internal provenance.

Put public Host runtime metadata in `native`. Put only the exact inspector output in `local`. Record permission-source fields in `native_permission_source` or `local_permission_source` only when that corresponding Host evidence surface directly exposes all of these fields:

```text
source_kind
source_id
sandbox_policy_type
permission_profile_type
evidence_ref
selection_evidence_ref
```

`source_kind` may be `parent_turn` or `selected_environment`; these are candidate source kinds in project vocabulary, not an asserted Host precedence. `source_id` binds the source claim to a concrete Host-observed identity. For `parent_turn` it must equal the exact expected parent/root thread id. The output `source` is derived from whether native, local, or agreeing native-and-local evidence supplied the fields. `evidence_ref` identifies the Host evidence that exposed the source permission. `selection_evidence_ref` identifies direct Host evidence for why that source was effective. A detached, configured, or hand-written source object is rejected; equality between child and candidate-source permission values cannot manufacture either source attribution or selection provenance.

A field may be proven by `native`, `local`, or both. When both runtime sources expose the same field, they must agree. Route assurance compares role, model, effort, child identity, and ancestry with the configured route. Permission-state assurance requires both actual child permission fields. Permission-provenance assurance separately requires a concrete source identity, source permission evidence, and source-selection evidence.

Accepted route identity/model/effort is retained as accepted-layer fact when exposed. Accepted permission is not Observed permission. Missing child permission makes permission-state assurance `unknown`. Missing source identity or selection evidence makes only permission-provenance assurance `unknown`; it does not erase independently observed child permission state. A child/source mismatch or bound `parent_turn` source-id mismatch makes provenance `failed` and quarantines the conflicting claim. `requires_enforced_read_only=true` still rejects an observed broad sandbox independently of provenance.

The normalizer must never fill an absent Observed field from Configured, Requested, or Accepted values.

Do not encode an internal Host decision model or source precedence unless a supported Host exposes direct selection evidence. Current Codex may expose the actual child sandbox and permission profile without exposing the identity of the effective source or why it was selected. In that case permission state can be verified while provenance remains unknown.

## Evidence grades

The current normalizer reports these provenance grades:

```text
C1_configuration_only
-> no actual runtime source closed the route

L1_local_record_observed
-> exact Host-produced rollout provides the required runtime evidence

R1_runtime_reported
-> public Host runtime metadata provides the required runtime evidence

R2_runtime_reported_and_local_record_agree
-> public Host and exact rollout sources jointly support the route without conflict; every overlapping field agrees

X0_conflicted
-> runtime/configuration/source evidence conflicts; quarantine
```

The grade is provenance, not a claim that local rollout evidence is configuration. `L1` is actual runtime evidence from the Host-produced record. Public Host metadata remains preferred because it avoids local rollout inspection when the Host already exposes the fact directly.

### Assurance limitation

An exact Codex rollout is Host-produced and bound by this protocol to the exact child identity, parent identity, managed role, and internally consistent turn metadata. It is still a local file and is not cryptographically signed by the Host. A user or process with sufficient local write access could alter that file after generation.

Therefore `L1_local_record_observed` means inspectable Host-produced local runtime evidence. It is not tamper-proof remote attestation or cryptographic proof of model execution. `R2_runtime_reported_and_local_record_agree` adds cross-source consistency when public Host metadata and the exact local record are both available; it also is not a cryptographic attestation claim. Prefer public Host runtime metadata whenever the Host exposes the required facts, and treat any disagreement between public and local runtime evidence as `FAIL`.

Permission-source `evidence_ref` values are provenance bindings, not cryptographic signatures. They make the source claim inspectable and tie `parent_turn` claims to the exact expected parent identity; they do not turn a local Host record into remote attestation.

Do not describe any evidence grade as proving model weights, server-side model identity beyond the Host's own reported/recorded identity, or an independently signed execution receipt.

## Missing evidence and failure semantics

Use these outcomes:

```text
required field absent from both runtime sources
-> UNKNOWN / not_exposed

no exact rollout available when public metadata is incomplete
-> UNKNOWN

multiple exact rollout matches
-> refuse inspection; UNKNOWN until provenance is resolved

observed route differs from policy/configured route
-> FAIL / quarantine

observed child permission differs from a directly evidenced source permission
-> permission provenance FAIL / quarantine; observed permission state remains separately reported

parent-turn permission source id differs from the expected parent/root thread id
-> FAIL / quarantine

either actual child permission field is unavailable
-> permission state UNKNOWN

effective permission source identity or source-selection evidence is unavailable
-> permission provenance UNKNOWN; route and actual permission state keep their independent verdicts

public Host and exact rollout disagree
-> FAIL / quarantine

cross-turn model/effort/sandbox/permission drift
-> refuse attestation; FAIL or UNKNOWN according to the evidence available, never choose a convenient turn
```

Do not silently fall back to a different role, model, effort, or permission level merely to make the gate pass.

## Five-role release table

For a formal live-route smoke, record all five exact managed roles separately:

| Role | Configured model / effort | Behavioral authority | Host accepted identity | Route assurance | Effective permission state | Permission provenance |
| --- | --- | --- | --- | --- | --- | --- |
| Reader | from policy | none | actual | VERIFIED/UNKNOWN/FAIL | VERIFIED/UNKNOWN/FAIL | VERIFIED/UNKNOWN/FAIL |
| Worker | from policy | assigned bounded-source-write | actual | VERIFIED/UNKNOWN/FAIL | VERIFIED/UNKNOWN/FAIL | VERIFIED/UNKNOWN/FAIL |
| Solver | from policy | assigned bounded-source-write | actual | VERIFIED/UNKNOWN/FAIL | VERIFIED/UNKNOWN/FAIL | VERIFIED/UNKNOWN/FAIL |
| Investigator | from policy | none | actual | VERIFIED/UNKNOWN/FAIL | VERIFIED/UNKNOWN/FAIL | VERIFIED/UNKNOWN/FAIL |
| Advisor | from policy | none | actual | VERIFIED/UNKNOWN/FAIL | VERIFIED/UNKNOWN/FAIL | VERIFIED/UNKNOWN/FAIL |

For Reader, Investigator, and Advisor, also record a narrow pre/post workspace mutation check appropriate to the smoke responsibility and require no project-file mutation. That check verifies the behavioral contract only. It is not Host sandbox proof and cannot replace permission attestation.

For a release gate that explicitly requires observed model, effort, actual permission state, ancestry, or permission provenance, `UNKNOWN` does not pass that specific gate. Provenance `UNKNOWN` cannot support a source/precedence claim, but does not downgrade verified route or permission-state facts.

## Privacy and scope

Runtime attestation is deliberately narrower than transcript analysis. The inspector reads only the exact child rollout selected by exact identity and emits only the allowlist above. It stores no new persistent state and does not copy the rollout into the repository or dispatch state.

Do not use this mechanism to collect prompt text, assistant content, reasoning, source code, token accounting, or behavioral telemetry. Token/cost measurement has a separate evidence problem and is outside this protocol.

## Main-session distinction

This protocol closes child route attestation. Main-session capability dedup remains more conservative: local-only main-session metadata does not by itself authorize suppressing a Sol uplift under the current policy. That optimization is separate from proving which exact child route ran.
