# Headoff

Updated: 2026-08-25.

## Purpose

This file is the development-session handoff record for `subagents-dispatch`.

Its job is to help a new ChatGPT development session recover the project quickly without reconstructing old conversations. It should preserve durable development context: current direction, recent completed work, important decisions and their reasons, lessons already learned, current phase, open work, and the next safe continuation point.

This file is not Plugin runtime, a product contract, Host qualification input, release evidence, or a release gate. It must not become a second source of truth for facts already owned elsewhere.

Live branch, PR, exact commit/tree, CI and review state belong in GitHub. Real Host actions, evidence, phase verdicts, and `REUSE | RERUN | NOT_RUN` decisions belong in Issue #91. Machine behavior belongs in the canonical contracts.

Update this file when the development theme, durable project direction, major completed work, important decision, current phase, blocker, lesson, or next safe continuation point materially changes. Do not edit it merely to record an individual CI run, exact live SHA, one Host probe result, temporary diagnostic output, or another short-lived status value.

## Project in one minute

`subagents-dispatch` is a bounded orchestration layer over Codex Native Subagents. It helps Main decide when delegation is useful, assign bounded responsibilities to fixed managed profiles, coordinate dependency and writer safety, inspect Host evidence conservatively, and keep final acceptance with Main.

The first public Plugin line is `1.0.0`. Native Core V4 remains an internal architecture generation used by machine contracts and filenames. It is not the public release number.

The current development philosophy is deliberately strict:

- unsupported pre-1.0 state has no compatibility entitlement;
- retired TeamPlan surfaces remain removed;
- retired migration and stale-state cleanup implementations do not ship;
- unsupported state, ownership, installation source, or current schema fails explicitly;
- ambiguous Host lifecycle, identity, materialization, permission, or writer evidence remains `UNKNOWN` and blocks unsafe progress;
- old callers, tests, or documents do not justify restoring deleted APIs or compatibility paths.

## Current status

Repository clean-break closure: **COMPLETE**.

The first-public `1.0.0` clean-break work was merged through PR #115. The final PR head passed the required repository matrix and adversarial review, and the merged branch passed the post-merge repository qualification as well.

Current active release workstream: **real Codex Host qualification re-entry on the post-clean-break basis**.

Real Host qualification: **requires a fresh Issue #91 qualification-basis preflight before another Host action is treated as current release evidence**.

Final Review: **blocked until the applicable N0-N8 Host campaign is conclusive for the current qualification basis**.

Public `1.0.0` release: **not complete**.

Feature development should not quietly restart while release qualification is being closed. Any source or package change must be classified against repository and Host invalidation rules before later release evidence is reused.

## Recently completed work

### First-public 1.0.0 clean break

PR #115 completed the repository-side clean break for the first public release.

The durable outcomes are:

- WorkGraph and WorkUnit remain the current responsibility, dependency, readiness, and acceptance structure;
- retired TeamPlan contract, validator, revision fields, and current compatibility callers were removed;
- pre-1.0 migration and stale-state cleanup implementations were removed from the shipped product;
- unsupported pre-1.0 state and unsupported current inputs fail explicitly instead of being translated forward;
- public release identity was aligned to Plugin `1.0.0` while Native Core V4 stayed an internal architecture identifier;
- release and architecture documents were aligned with the current runtime schema;
- stale current-authority documentation references to deleted compatibility surfaces were removed;
- Doctor now preserves unresolved orchestration Host uncertainty as `UNKNOWN` instead of describing that state as healthy;
- package-integrity data was refreshed for changed shipped bytes;
- repository regression coverage was strengthened so retired compatibility surfaces cannot quietly return to current authority documents and tests;
- the exact reviewed PR head passed the required CI matrix and managed Agent lifecycle checks;
- the merged branch passed the post-merge repository matrix.

The clean-break repository plan in `tasks/plan.md` is now completed historical execution context. It is no longer the active development plan.

### Earlier real Host work

A staged Host qualification procedure and append-only evidence ledger were established before the final clean break. Earlier H0 work reached `PASS_STOP` on its then-current qualification basis.

That earlier H0 result is useful historical evidence, but it must not be promoted automatically to the current post-clean-break basis. PR #115 changed shipped runtime/package bytes, so the next Host step begins with the normal Issue #91 qualification-basis comparison and invalidation decision.

A new chat or maintainer session does not by itself invalidate Host evidence and does not justify repeating a Host action.

## Key decisions and why

### Clean break over speculative compatibility

The first public line starts at `1.0.0`. Pre-1.0 development artifacts are not supported product data. Keeping migration wrappers, TeamPlan aliases, stale-state cleanup paths, or compatibility translations would increase branching and ambiguity before any public compatibility promise exists.

When an old test or document depends on a deleted surface, fix the stale consumer or current contract. Do not restore the deleted surface solely to make historical assertions green.

### Fail closed on unsupported or ambiguous evidence

Host truth can be incomplete. `UNKNOWN` is therefore a real state, not a cosmetic warning to erase. Ambiguous materialization, lifecycle, identity, permission, or WriterLease evidence cannot authorize conflicting replacement, writer transfer, acceptance, or another unsafe action.

Doctor may diagnose uncertainty, but it must not manufacture runtime authority or silently repair an ambiguous condition.

### Keep release-source identity separate from Host qualification identity

Two identity layers exist for different purposes.

Release-source identity is the exact final Git commit/tree used for repository qualification, Final Review, release traceability, and the top-level release evidence envelope.

Host qualification identity is the tuple of digests derived from:

- `.codex-plugin/package-integrity.json`;
- `contracts/policy.json`;
- `docs/v4/host-smoke.json`.

A source-only documentation change does not automatically invalidate conclusive Host evidence when all three Host qualification digests remain unchanged and no environment or prerequisite invalidation applies. Conversely, a matching public version string alone does not prove that the installed Plugin bytes still match the tested candidate.

Every reuse decision still goes through Issue #91.

### Keep Host evidence outside tracked product state

`docs/v4/host-smoke.json` is the machine-readable N0-N8 contract and must remain `PENDING` with empty tracked results. Actual Host actions and preflight decisions go to Issue #91 so the frozen candidate does not mutate merely because qualification evidence is being collected.

The final release evidence artifact also lives outside the candidate repository and is verified against the exact release source and Host qualification identity.

### Headoff is development memory

`headoff.md` records durable development context and session continuation. It should summarize important conclusions and point to the canonical owner instead of copying complete schemas, runtime state machines, CI snapshots, Host evidence, or release verdicts.

The file should help a new ChatGPT session understand why the project is in its current shape and where to continue. It should not create new authority.

## Canonical truth owners

Use the smallest relevant owner and read live sources before acting:

- `.codex-plugin/plugin.json`: public Plugin version and package identity.
- `contracts/policy.json`: fixed product policy and managed profile values.
- `contracts/state.md`: current state schema and clean-break boundary.
- `docs/v4/architecture.json`: complete Native Core machine architecture and runtime ownership.
- `docs/v4/host-smoke.json`: N0-N8 real Host machine contract.
- `docs/release-checklist.md`: release gates, identity layers, and invalidation rules.
- `tasks/plan.md`: completed 1.0.0 clean-break repository closure plan.
- `tasks/real-host-qualification-plan.md`: current staged human Host execution procedure. It never overrides the machine contract.
- `docs/runtime-attestation.md`: runtime observation and evidence boundaries.
- GitHub: live branch, PR, exact source identity, CI, review, and merge state.
- Issue #91: append-only real Host actions, evidence, preflight decisions, invalidation history, and reusable historical Host context.

Do not create another tracked status file that duplicates GitHub or Issue #91.

## Product context a new development session should retain

Only the minimum durable architecture context belongs here:

- Public Skills are `Orchestrate` and `Doctor`.
- Main is the sole managed coordinator and owns final integration and acceptance.
- Managed children do not create or control another managed Agent layer.
- Reader and Worker use Luna Max; Investigator uses Terra High; Solver and Advisor use Sol High.
- Fresh managed children use `fork_turns=none`.
- The product managed-child ceiling is four.
- WorkGraph and WorkUnit own responsibility, dependencies, readiness, and acceptance.
- ExecutionBinding owns one concrete managed attempt/generation.
- WriterLease owns managed write coordination for the canonical mutable workspace.
- Host `COMPLETED` produces candidate work only; Main acceptance is separate.
- Codex Host owns actual materialization, lifecycle, capacity, child identity, effective permission, effective sandbox, and effective collaboration capability.
- Interrupt acknowledgement alone does not release WriterLease.

For exact behavior, read the canonical contracts rather than expanding this section into a second architecture document.

## Lessons already learned

Keep these conclusions available to future sessions so the project does not repeat solved mistakes:

1. Deleting an old architecture surface requires searching current-authority tests and documents for stale consumers. A deleted implementation can remain conceptually alive through documentation drift.
2. A stale test is not evidence that a deleted API should return. Determine which current contract owns the behavior first.
3. `UNKNOWN` must stay visible through diagnostics. Converting unresolved Host uncertainty into a healthy status weakens fail-close behavior even when runtime gates still block unsafe work.
4. Shipped documentation and scripts covered by package integrity are part of the package identity. Editing them requires the normal package-integrity update and repository qualification path.
5. Git commit changes and Host qualification changes are related but not identical. Use the three qualification digests before deciding whether Host evidence must be repeated.
6. Matching Plugin version text is insufficient proof of exact tested bytes. Exact installed package/profile basis must be verified when binding a Host campaign.
7. Starting a new ChatGPT, Codex, or maintainer session is not a rerun reason. Reuse or rerun follows evidence and invalidation rules.
8. Host configuration expresses intent. Real Host observations decide claims about actual model route, lifecycle, descendant materialization, sandbox, permissions, and control behavior.
9. A Host action that returns successfully is not automatically sufficient evidence that the intended semantic effect occurred. N4 steering, settlement, writer transfer, and similar gates require the specific observations in the Host contract.
10. Do not mutate tracked source merely to record a Host PASS. Milestone-level development context may be summarized here after the phase changes, while the evidence itself remains in Issue #91.

## Active workstream: real Host qualification

The repository clean-break work is closed. The next active release work is to determine the post-clean-break Host qualification basis and resume the staged campaign only from the point authorized by current evidence.

Before any new real Host action:

1. read the latest Issue #91 ledger;
2. read `docs/v4/host-smoke.json`, `tasks/real-host-qualification-plan.md`, and the relevant release-checklist section;
3. compare the current runtime-manifest, profile-contract, and Host-contract qualification digests with the basis of the evidence being considered for reuse;
4. record an explicit `REUSE | RERUN | NOT_RUN` preflight decision in Issue #91;
5. if a rerun is required, synchronize and verify the exact local checkout, Marketplace source, installed Plugin bytes, managed profile basis, package integrity, and Doctor before binding a fresh Host environment;
6. do not perform an Agent-control action until the exact covered turn independently proves the required V2 Host capability and callable schema;
7. stop at the mandatory phase stop defined by the Host qualification plan.

No Host phase auto-continues merely because the previous phase passed.

## Open work and unresolved questions

These are active engineering/release concerns. They should remain clearly separated from confirmed product requirements until adopted into a canonical contract.

### Required release work

- Re-evaluate the post-clean-break Host qualification basis in Issue #91.
- Rebind H0/source-environment evidence when the invalidation decision requires it.
- Complete the applicable H1 through H9 staged Host campaign with mandatory stop points.
- Run H10 release closure only after the Host campaign is conclusive.
- Complete the fresh final-source Final Review, external release evidence verification, installed-product gate, human App observation, and release/tag closure required by `docs/release-checklist.md`.

### Engineering improvements to evaluate

- Consider a read-only Host test-basis verifier that can compare the intended candidate with the installed Plugin and managed profile basis at phase entry. The goal would be earlier detection of test-basis drift and immediate `MUTATION_STOP`, without automatic update, repair, reinstall, or fallback.
- Finalize the post-release retention policy for external Host/release evidence. Issue #91 already preserves the operational ledger, while long-term immutable storage for release evidence and required raw Host artifacts still needs an explicit release-time decision.

Do not treat these two improvement ideas as implemented requirements until the project adopts them in the proper canonical owner.

## Next safe sequence

For the next development session working on release qualification:

1. Read this file for durable context.
2. Query GitHub for the current live branch, exact source state, open PRs, and current repository qualification status. Do not trust a historical SHA copied from an old chat.
3. Read the latest Issue #91 entries and identify the most recent applicable Host qualification basis and stop state.
4. Compare the current three Host qualification digests with the evidence basis under consideration.
5. Record the next `REUSE | RERUN | NOT_RUN` preflight in Issue #91 before a real Host action.
6. Verify the target checkout and installed Plugin/profile basis when the preflight requires current binding.
7. Rebind H0 if required by invalidation. Stop at `PASS_STOP`, `NOT_RUN_STOP`, `UNKNOWN_STOP`, `FAIL_STOP`, or `MUTATION_STOP` as applicable.
8. Proceed to H1 Reader canary only after H0 is valid for the current basis and the user explicitly authorizes continuation.
9. Continue later phases only through the staged Host plan and its mandatory stop points.
10. After N0-N8 are conclusive for the current qualification identity, continue with Final Review and release closure under `docs/release-checklist.md`.

If repository or package source changes during Host qualification, stop and classify invalidation before reusing later evidence.

## Verification discipline for future repository changes

For any new repository mutation:

1. read the smallest relevant canonical contracts and current source;
2. state concrete acceptance conditions before editing;
3. keep changes focused and avoid compatibility branches for unsupported pre-1.0 surfaces;
4. run focused checks when available;
5. run the complete exact-head repository matrix when the change requires repository qualification;
6. review the final diff across correctness, simplicity, architecture, security, and performance;
7. do not mark the work complete while a required check is red, skipped, or bound to an older source state;
8. classify the effect of the source change on Host qualification evidence before resuming Host work.

## Handoff maintenance protocol

A development session should update this file before handoff when at least one of these durable facts changed:

- the project or release theme changed;
- a major implementation or cleanup milestone completed;
- an important design decision changed or was newly settled;
- the active phase or release gate changed;
- a blocker or unresolved engineering question materially changed;
- a reusable lesson was learned that should prevent future repeated work;
- the next safe continuation point changed.

When updating it:

1. refresh `Current status` first;
2. add or revise the durable entry under `Recently completed work`;
3. record new decision reasoning under `Key decisions and why` only when it will matter to future sessions;
4. move solved issues out of `Open work and unresolved questions`;
5. add meaningful recurring lessons under `Lessons already learned`;
6. make `Next safe sequence` match the real current phase;
7. verify links and canonical ownership statements against the current repository;
8. avoid copying volatile SHA, CI run numbers, transient Host session ids, terminal output, or individual probe verdicts into this file.

Before ending a development session, ask one practical question: if another ChatGPT session opened only this file and then queried the linked live sources, would it know what was completed, why the project is in its current shape, what remains open, and exactly where to continue without repeating already-conclusive work?
