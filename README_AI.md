# subagents-dispatch: AI Agent Reference

Current product surface: `Orchestrate` and `Doctor`.

Before changing the active release branch, read root `headoff.md`. It is the development-session context transfer entrypoint for project background, important workflow history, current progress and next direction. Read GitHub and Issue #91 directly for current candidate, CI and real-Host evidence. Historical development chronology is not an active contract.

`headoff.md` is development-only context. It is not Plugin runtime, Host qualification input, release evidence, or a phase gate. Do not require a headoff edit or commit merely to record an individual Host result. Its eventual removal is repository housekeeping and does not change Plugin runtime behavior or release authority.

## Canonical truth

Keep one owner per semantic fact:

- `.codex-plugin/plugin.json`: public Plugin version and package identity.
- `contracts/policy.json`: fixed profile and product policy values.
- `contracts/state.md`: current state schema and clean-break boundary.
- `docs/v4/architecture.json`: complete Native Core V4 machine architecture and runtime owner map.
- `docs/v4/host-smoke.json`: candidate-bound N0-N7 real-Host qualification oracle.
- `docs/v4/technical-debt.json`: explicit Native Core V4 technical debt.
- GitHub: current branch, PR, candidate and CI state.
- Issue #91: real-Host evidence and `REUSE | RERUN | NOT_RUN` preflight decisions.

Do not add another tracked status JSON that copies current SHA, CI result or Host verdict. Do not create parallel machine projections of routing, scheduling, writer or Host semantics already owned by the canonical contracts.

`docs/v4/` is reserved for internal version-specific machine or maintenance contracts. Development-session continuation context lives in root `headoff.md` while the project is under active development.

## Public-version clean break

The first public Plugin line starts at `1.0.0`. Native Core V4 names are internal architecture-generation identifiers, not the public release version.

Pre-1.0 development surfaces have no compatibility entitlement. Do not keep or recreate a migration path, stale-state cleanup path, TeamPlan compatibility surface, wrapper, alias, or fallback solely because old tests, old docs, or old development state still reference it.

Unsupported current-state schema, installation source, ownership, or product identity must fail explicitly. Missing or conflicting Host evidence remains `UNKNOWN` where uncertainty is the contract. Never translate an unsupported or ambiguous condition into success merely to preserve continuity.

## Runtime ownership

Codex Host owns child materialization, lifecycle truth, child identity, actual capacity, effective permission and effective collaboration capability.

Main owns user intent, decomposition, explicit fixed-profile selection, dispatch judgment, integration, WorkUnit acceptance, irreversible external effects and the final response.

WorkGraph and WorkUnit own responsibility structure, dependencies and acceptance. ExecutionBinding owns one concrete managed attempt. WriterLease owns managed write coordination for the canonical workspace.

## Fixed profiles

```text
Reader        gpt-5.6-luna   max    no mutation
Worker        gpt-5.6-luna   max    bounded source write when granted
Investigator  gpt-5.6-terra  high   no mutation
Solver        gpt-5.6-sol    high   bounded source write when granted
Advisor       gpt-5.6-sol    high   review / no mutation
```

Main selects one fixed profile explicitly. There is no automatic model or effort escalation ladder.

## Core invariants

```text
managed children <= 4
fork_turns = none
delegation depth = 1
Host COMPLETED produces candidate work only
WorkUnit ACCEPTED unlocks dependencies
UNKNOWN blocks conflicting replacement, writer transfer and final acceptance
interrupt return alone never releases WriterLease
```

Main is the sole managed coordinator. Managed profiles and responsibility packets instruct children not to create or control further Agents. Effective child collaboration remains Host truth. Latent V2 recursive capability alone does not decide managed N1; N1 evaluates actual canonical managed execution and descendant evidence.

Independent read-only overlap requires effective read-only evidence and responsibility isolation. The canonical mutable workspace has one managed writer unless a future Host-verifiable isolated-workspace mode is explicitly designed and validated.

## Contract index

Use the smallest relevant owner:

- `contracts/routing.md`: delegation value, profile selection and dispatch judgment.
- `contracts/responsibility-packet.md`: managed child responsibility serialization.
- `contracts/guardrails.md`: authority, mutation, consent and external-action boundaries.
- `contracts/interaction.md`: user control semantics.
- `contracts/recovery.md`: ExecutionBinding recovery and UNKNOWN handling.
- `contracts/state.md`: current Native Core state schema.
- `contracts/final-review.md`: exact-candidate independent review.

Doctor owns deterministic installed-product diagnosis and explicit maintenance. Repository publication checks, N0-N7 Host evidence, the separate exact-source Final Review, and benchmark/calibration workflows stay outside ordinary Doctor authority.

## Change discipline

- Start from the current supported product boundary. Historical development surfaces do not gain support merely because they once existed.
- Keep compatibility only when a current supported consumer and explicit removal condition justify it.
- Prefer deleting an obsolete branch, alias, wrapper, or fallback over preserving it speculatively.
- Keep behavior changes separate from unrelated refactors and documentation cleanup.
- Protect behavior, schema, ownership and safety invariants in tests; avoid exact prose mirrors unless wording is an interface.
- Preserve UNKNOWN fail-closed handling, candidate identity, Host observation basis, WriterLease settlement and materialization ambiguity.
- Generate package-integrity data with repository tooling when shipped bytes change.
- Run focused checks and then the complete required repository matrix before declaring a change complete.
