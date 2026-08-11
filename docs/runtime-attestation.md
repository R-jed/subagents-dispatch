# Runtime Attestation

This document defines how subagents-dispatch proves the actual runtime route of one managed Codex child when model, reasoning effort, sandbox, ancestry, or role identity is part of acceptance or release validation.

It is an explicit diagnostic protocol. Ordinary Dispatch does not run it, scan Codex sessions, collect transcripts, or create background telemetry.

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

## Public Host evidence first

Use public Host/spawn/details metadata first whenever it exposes the required field. Bind every observation to the exact child identity and expected parent/root thread when those identities are available.

Public acceptance of an exact `agent_type` proves role acceptance only. It does not prove the observed model, effort, sandbox, or permission profile unless the Host explicitly reports those runtime facts.

## Exact rollout fallback

If public Host metadata omits a required child-runtime field and the local Codex rollout is accessible, use the bundled inspector:

```text
python scripts/inspect-agent-runtime.py <child-thread-id> \
  --expected-parent-thread-id <root-thread-id> \
  --expected-agent-role <exact-agent-type>
```

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
model
effort
sandbox_policy_type
permission_profile_type
runtime_version
```

The inspector does not emit prompts, assistant messages, tool payloads, hidden reasoning, source contents, working-directory paths, or rollout paths.

## Normalize and compare

Build `expected` from `contracts/policy.json` and the exact child/root identities. For formal five-role live-route validation set:

```text
runtime_observation_required = true
requires_permission_observation = true
```

Put public Host runtime metadata in `native`. Put only the exact inspector output in `local`. Record the effective inherited permission separately in `effective_permission_source`, including `source_kind` (`parent_turn` or `selected_environment`), `sandbox_policy_type`, and `permission_profile_type`. Then pass the record to `scripts/runtime-evidence.py`.

A field may be proven by `native`, `local`, or both. When both runtime sources expose the same field, they must agree. Route integrity compares role, model, effort, child identity, and ancestry with the configured route. Permission integrity independently compares the actual child sandbox and permission profile with the effective inherited permission source.

Accepted permission is retained as an accepted-layer fact but is not used to decide inheritance: Codex 0.147.0 applies the runtime permission profile after role configuration. A child/source permission mismatch is `FAIL` and quarantines the permission claim. Missing child or source permission fields are `UNKNOWN`. A matching inherited permission is `OK`, including a broad sandbox inherited from a broad parent. Separately, `requires_enforced_read_only=true` still rejects a broad sandbox even when inheritance matches.

The normalizer must never fill an absent Observed field from Configured, Requested, or Accepted values.

The application order observed on Codex 0.147.0 is base child configuration, role configuration, runtime permission override, then spawn. Re-attest this Host behavior for future supported Codex versions; do not assume it is immutable.

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

observed child permission differs from effective parent/environment permission
-> FAIL / quarantine

effective permission source or either permission field is unavailable
-> UNKNOWN

public Host and exact rollout disagree
-> FAIL / quarantine

cross-turn model/effort/sandbox/permission drift
-> refuse attestation; FAIL or UNKNOWN according to the evidence available, never choose a convenient turn
```

Do not silently fall back to a different role, model, effort, or permission level merely to make the gate pass.

## Five-role release table

For a formal live-route smoke, record all five exact managed roles separately:

| Role | Configured model / effort | Behavioral authority | Host accepted identity | Observed model / effort | Observed Host permission | Permission source | Inheritance verdict | Parent / child identity | Overall |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Reader | from policy | none | actual | actual or `UNKNOWN` | actual or `UNKNOWN` | parent/environment/unknown | OK/UNKNOWN/FAIL | actual | VERIFIED/UNKNOWN/FAIL |
| Worker | from policy | assigned bounded-source-write | actual | actual or `UNKNOWN` | actual or `UNKNOWN` | parent/environment/unknown | OK/UNKNOWN/FAIL | actual | VERIFIED/UNKNOWN/FAIL |
| Solver | from policy | assigned bounded-source-write | actual | actual or `UNKNOWN` | actual or `UNKNOWN` | parent/environment/unknown | OK/UNKNOWN/FAIL | actual | VERIFIED/UNKNOWN/FAIL |
| Investigator | from policy | none | actual | actual or `UNKNOWN` | actual or `UNKNOWN` | parent/environment/unknown | OK/UNKNOWN/FAIL | actual | VERIFIED/UNKNOWN/FAIL |
| Advisor | from policy | none | actual | actual or `UNKNOWN` | actual or `UNKNOWN` | parent/environment/unknown | OK/UNKNOWN/FAIL | actual | VERIFIED/UNKNOWN/FAIL |

For a release gate that explicitly requires observed model, effort, permission, or ancestry, `UNKNOWN` does not pass that gate.

## Privacy and scope

Runtime attestation is deliberately narrower than transcript analysis. The inspector reads only the exact child rollout selected by exact identity and emits only the allowlist above. It stores no new persistent state and does not copy the rollout into the repository or dispatch state.

Do not use this mechanism to collect prompt text, assistant content, reasoning, source code, token accounting, or behavioral telemetry. Token/cost measurement has a separate evidence problem and is outside this protocol.

## Main-session distinction

This protocol closes child route attestation. Main-session capability dedup remains more conservative: local-only main-session metadata does not by itself authorize suppressing a Sol uplift under the current policy. That optimization is separate from proving which exact child route ran.
