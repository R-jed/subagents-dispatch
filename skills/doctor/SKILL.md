---
name: doctor
description: Diagnose subagents-dispatch Plugin, Skill, managed-Agent, dispatch-state, Codex Host, and runtime-route health; mutate only on explicit supported repair intent.
---

# Doctor

Use this Skill for subagents-dispatch installation and runtime health. Diagnosis is read-only by default. Repair, cleanup, migration, or live route smoke requires explicit user intent.

The deterministic report has exactly six layers, in this order:

```text
Plugin
Skills
Managed Agent profiles
Dispatch state
Codex Host
Runtime route evidence
```

Normal diagnosis never spawns a child or contacts a Host control surface. Missing Host capability is `UNKNOWN` with the supported limitation stated. Runtime route integrity is `UNKNOWN` when no explicit evidence was supplied; that state does not make an ordinary Doctor run unhealthy. Only explicit route evidence may establish an observed runtime route.

Use deterministic owners instead of reproducing their logic:

- `../../contracts/policy.json`: required Skills, five configured routes, and hard invariants
- `../../contracts/state.md`: ephemeral dispatch-state meaning and safety
- `../../contracts/guardrails.md`: mutation, trust, and user-authority boundaries
- `../../docs/python-runtime.md`: Python 3.11+ helper-runtime resolution and prerequisite failure semantics
- `../../scripts/doctor.py`: package diagnostics
- `../../scripts/install-agents.py`: managed-profile verification and lifecycle
- `../../scripts/inspect-agent-runtime.py`: exact Codex child-rollout allowlist inspection for explicit live attestation
- `../../scripts/runtime-evidence.py`: configured/requested, accepted, and observed route normalization

Before invoking a bundled Python helper, resolve one Python 3.11+ interpreter from the actual task environment according to `../../docs/python-runtime.md` and keep that resolved interpreter fixed for the operation. A missing command named `python` does not by itself fail the prerequisite when another supported Python 3.11+ invocation is available.

Report Plugin, Skills, managed Agent profiles, dispatch state, Codex Host, and runtime route evidence separately as `OK`, `WARN`, `FAIL`, or `UNKNOWN`. Configuration is not runtime observation. A child saying which model it believes it is running is also not runtime evidence. Do not edit Codex config files directly, simulate missing Host controls, or delete ambiguous state. Do not invent App slash syntax or claim App-visible labels without direct observation.

Use `scripts/doctor.py --check` for the deterministic report. Its dispatch-state layer scans existing temporary capsules even without a current thread identity and reports forbidden repository-local `team-plan-*`, `ledger-*`, `receipt-*`, `recovery-*`, and dispatch `active.json` state. Use `--runtime-evidence <file>` only when route evidence is explicitly required; it delegates normalization to `scripts/runtime-evidence.py` and keeps configured/requested, accepted, and observed layers separate. `--live-route` is a formal gate: its evidence must explicitly declare `subject=child`, exact child/parent identities, `runtime_observation_required=true`, and `requires_permission_observation=true`; `UNKNOWN` does not pass `--live-route --check`. `--repair`, `--migrate-legacy`, and `--cleanup-stale` are explicit mutation intents. Preserve unresolved writers, planned work, pending takeover, and corrupt capsules for review.

## Explicit live route workflow

Run this workflow only when the user explicitly requests live route verification. The Doctor Skill, not `scripts/doctor.py`, may create five bounded native children, one for each exact configured role:

```text
subagents_dispatch_reader
subagents_dispatch_worker
subagents_dispatch_solver
subagents_dispatch_investigator
subagents_dispatch_advisor
```

Spawn each controlled child with `fork_turns = none`, delegation depth one, a no-op verification responsibility, and no authority beyond what the role check requires. Capture requested route, Host-accepted role identity, parent/root identity, child identity, and only the model, effort, and permission facts the Host actually exposes. Stop or settle every smoke child before returning.

For each child, inspect public Host/spawn/details metadata first. Public Host metadata is the preferred runtime source. If it omits a required runtime field and the exact Codex rollout is locally available, run the bundled inspector against the exact child identity and bind it to the expected parent and managed role:

```text
<python-3.11+> ../../scripts/inspect-agent-runtime.py <child-thread-id> \
  --expected-parent-thread-id <root-thread-id> \
  --expected-agent-role <exact-agent-type>
```

`<python-3.11+>` means the already resolved interpreter invocation from `../../docs/python-runtime.md`; it is not a literal command or a requirement that the shell expose a command named `python`.

The inspector is read-only and explicit. It streams exactly one rollout selected by the exact child id, parses only `session_meta` and `turn_context` records for routing metadata, rejects ambiguous identity or cross-turn route drift, and emits only an allowlisted routing object. It never emits prompts, assistant output, tool payloads, reasoning, source contents, or the rollout path. Do not hand-copy profile values, child prose, or guessed values into its output.

Build the expected route from `contracts/policy.json`, set `runtime_observation_required=true` and `requires_permission_observation=true`, place public Host runtime metadata in `native`, and place only the exact inspector output in `local`. Record the effective parent-turn or selected-environment permission separately as `effective_permission_source`. That source object must include `source_kind`, a concrete `source_id`, observed sandbox and permission profile, `evidence_source`, `evidence_ref`, and `selection_evidence_ref`. For `parent_turn`, `source_id` must equal the exact expected parent/root thread id. For `selected_environment`, `source_id` must be a concrete Host-observed environment identity. `selection_evidence_ref` must identify the Host evidence establishing that this source was the effective source after the policy-owned source precedence was applied. If source identity or source-selection provenance is unavailable, keep permission integrity `UNKNOWN`. Never copy configured route or behavioral-authority values into an observed source. Then normalize the combined record through `scripts/runtime-evidence.py`.

Report configured route, observed route, behavioral authority, and observed Host permission separately. A behaviorally read-only role inheriting `danger-full-access` from a `danger-full-access` parent is permission integrity `OK`, not an automatic warning or route failure; state clearly that behavioral read-only is not Host sandbox enforcement. A child/source mismatch or bound parent-source identity mismatch is `FAIL`, and missing permission or permission-source provenance is `UNKNOWN`. Static Doctor never spawns Agents.

`native` and `local` are two actual-runtime evidence sources. Either may supply a field that the other legitimately omits, but every overlapping field must agree. A conflict is `FAIL` and quarantines the route claim. If the inspector finds no exact rollout, more than one exact match, identity mismatch, route drift, or unavailable required metadata, do not substitute configuration; keep the affected evidence `UNKNOWN` or `FAIL` according to the observed condition.

Report configured, accepted, and observed layers separately, plus the evidence source for each observed field (`native`, `local`, or `both`). A matching accepted role is not observed runtime proof. If model, effort, ancestry, permission, or effective permission-source provenance remains unavailable, report that field and the affected verdict as `UNKNOWN`; never copy configured values into observed columns. Any observed mismatch is `FAIL` and quarantines only that route claim.