---
name: doctor
description: Diagnose subagents-dispatch Plugin, Skill, managed-Agent, dispatch-state, Codex Host, and runtime-route health; mutate only on explicit supported lifecycle intent.
---

# Doctor

Use this Skill for subagents-dispatch installation and runtime health. Diagnosis is read-only by default. Repair, uninstall, cleanup, migration, or live route smoke requires explicit user intent.

The deterministic report has eight layers, in this order:

```text
Plugin
Skills
Managed Agent profiles
Dispatch state
Codex Host
Runtime route
Effective permission state
Permission-source provenance
```

Normal diagnosis never spawns a child or contacts a Host control surface. Missing Host capability is `UNKNOWN` with the supported limitation stated. Runtime route integrity is `UNKNOWN` when no explicit evidence was supplied; that state does not make an ordinary Doctor run unhealthy. Only explicit route evidence may establish an observed runtime route.

Use deterministic owners instead of reproducing their logic:

- `../../contracts/policy.json`: required Skills, five configured routes, and hard invariants
- `../../contracts/state.md`: ephemeral dispatch-state meaning and safety
- `../../contracts/guardrails.md`: mutation, trust, and user-authority boundaries
- `../../docs/python-runtime.md`: Python 3.11+ helper-runtime resolution and prerequisite failure semantics
- `../../scripts/doctor.py`: package diagnostics
- `../../scripts/install-agents.py`: managed-profile install/check lifecycle
- `../../scripts/uninstall-agents.py`: ownership-aware managed-profile removal
- `../../scripts/inspect-agent-runtime.py`: exact Codex child-rollout allowlist inspection for explicit live attestation
- `../../scripts/runtime-evidence.py`: configured/requested, accepted, and observed route normalization

Before invoking a bundled Python helper, resolve one Python 3.11+ interpreter from the actual task environment according to `../../docs/python-runtime.md` and keep that resolved interpreter fixed for the operation. A missing command named `python` does not by itself fail the prerequisite when another supported Python 3.11+ invocation is available.

Report Plugin, Skills, managed Agent profiles, dispatch state, Codex Host, runtime route, effective permission state, and permission-source provenance separately as `OK`, `WARN`, `FAIL`, or `UNKNOWN`. Configuration is not runtime observation. A child saying which model it believes it is running is also not runtime evidence. Do not edit Codex config files directly, simulate missing Host controls, or delete ambiguous state. Do not invent App slash syntax or claim App-visible labels without direct observation.

Use `scripts/doctor.py --check` for the deterministic report. Its dispatch-state layer scans existing temporary capsules even without a current thread identity and reports forbidden repository-local `team-plan-*`, `ledger-*`, `receipt-*`, `recovery-*`, and dispatch `active.json` state. Use `--runtime-evidence <file>` only when route evidence is explicitly required; it delegates normalization to `scripts/runtime-evidence.py` and keeps configured/requested, accepted, and observed layers separate. `--live-route` is claim-sensitive: it requires `subject=child`, exact child/parent identities, `runtime_observation_required=true`, and `requires_permission_observation=true`. Add `requires_permission_provenance=true` only for Host source or selection claims. `UNKNOWN` blocks only a dimension declared required by `--live-route --check`. `--repair`, `--migrate-legacy`, and `--cleanup-stale` are explicit mutation intents. Preserve unresolved writers, planned work, pending takeover, and corrupt capsules for review.

For explicit managed-profile uninstall intent, run the bundled ownership-aware helper while the Plugin is still installed:

```text
<python-3.11+> ../../scripts/uninstall-agents.py --codex-home <active-codex-home>
```

Do not replace an uninstall refusal with manual `rm`, wildcard deletion, or edits to the ownership manifest. The helper removes only existing profile paths whose current SHA-256 matches the existing subagents-dispatch ownership manifest, removes that manifest after the owned profile set is reconciled, and leaves the installer lock plus unrelated Codex state untouched. After that succeeds, the user may remove the Plugin registration and Marketplace source using `../../docs/plugin-installation.md`.

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

The inspector is read-only and explicit. It incrementally streams exactly one rollout selected by the exact child id within bounded total-scan and per-line limits, parses only `session_meta` and `turn_context` records for routing metadata, rejects ambiguous identity, resource-limit violations, or cross-turn route drift, and emits only an allowlisted routing object. It never emits prompts, assistant output, tool payloads, reasoning, source contents, or the rollout path. Do not hand-copy profile values, child prose, or guessed values into its output.

Build the expected route from `contracts/policy.json`, set `runtime_observation_required=true` and `requires_permission_observation=true`, place public Host runtime metadata in `native`, and place only the exact inspector output in `local`. Record source fields in `native_permission_source` or `local_permission_source` only when that corresponding Host evidence surface exposes a concrete source identity and direct source/selection evidence. `parent_turn` and `selected_environment` are candidate source kinds, not policy-owned Host precedence. Never infer a source from equal permission values, a detached object, or configured values. If source identity or selection provenance is unavailable, keep permission provenance `UNKNOWN` while preserving independently observed child sandbox/profile as permission-state evidence. Then normalize once through `scripts/runtime-evidence.py`.

Report route, behavioral authority, observed Host permission state, and permission provenance separately. A behaviorally read-only role with observed `danger-full-access` is not automatically a route failure; behavioral read-only is not Host sandbox enforcement. Hard read-only still requires observed `read-only`. A child/source mismatch or bound parent-source identity mismatch fails provenance; missing provenance does not erase verified actual permission state. Static Doctor never spawns Agents.

`native` and `local` are two actual-runtime evidence sources. Either may supply a field that the other legitimately omits, but every overlapping field must agree. A conflict is `FAIL` and quarantines the route claim. If the inspector finds no exact rollout, more than one exact match, identity mismatch, route drift, or unavailable required metadata, do not substitute configuration; keep the affected evidence `UNKNOWN` or `FAIL` according to the observed condition.

Report configured, accepted, and observed layers separately, plus the evidence source for each observed field (`native`, `local`, or `both`). A matching accepted role is not observed runtime proof. Report the three assurance verdicts independently. Any observed mismatch is `FAIL`; unavailable facts remain `UNKNOWN` only in the affected dimension.