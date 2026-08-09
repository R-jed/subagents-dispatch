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
- `../../scripts/doctor.py`: package diagnostics
- `../../scripts/install-agents.py`: managed-profile verification and lifecycle
- `../../scripts/runtime-evidence.py`: requested, accepted, and observed route normalization

Report Plugin, Skills, managed Agent profiles, dispatch state, Codex Host, and runtime route evidence separately as `OK`, `WARN`, `FAIL`, or `UNKNOWN`. Configuration is not runtime observation. Do not edit Codex config files directly, simulate missing Host controls, or delete ambiguous state. Do not invent App slash syntax or claim App-visible labels without direct observation.

Use `scripts/doctor.py --check` for the deterministic report. Its dispatch-state layer scans existing temporary capsules even without a current thread identity and reports forbidden repository-local `team-plan-*`, `ledger-*`, `receipt-*`, `recovery-*`, and dispatch `active.json` state. Use `--runtime-evidence <file>` only when route evidence is explicitly required; it delegates normalization to `scripts/runtime-evidence.py` and keeps requested, accepted, and observed layers separate. `--repair`, `--migrate-legacy`, and `--cleanup-stale` are explicit mutation intents. Preserve unresolved writers, planned work, pending takeover, and corrupt capsules for review.

## Explicit live route workflow

Run this workflow only when the user explicitly requests live route verification. The Doctor Skill—not `scripts/doctor.py`—may create five bounded native children, one for each exact configured role:

```text
subagents_dispatch_reader
subagents_dispatch_worker
subagents_dispatch_solver
subagents_dispatch_investigator
subagents_dispatch_advisor
```

Spawn each controlled child with `fork_turns = none`, delegation depth one, a no-op verification responsibility, and no authority beyond what the role check requires. Capture requested route, Host-accepted role identity, parent/root identity, child identity, and only the model, effort, and permission facts the Host actually exposes. Stop or settle every smoke child before returning.

Normalize each role record through `scripts/runtime-evidence.py`. Report configured, accepted, and observed layers separately. A matching accepted role is not observed runtime proof. If model, effort, ancestry, or permission evidence is unavailable, report that field and the affected verdict as `UNKNOWN`; never copy configured values into observed columns. Any observed mismatch is `FAIL` and quarantines only that route claim.
