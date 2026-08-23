# Headoff

Updated: 2026-08-23.

## Purpose

This file is the project context transfer entrypoint for a new development chat/session. A new development session should read this file first before planning, coding, reviewing, running Host probes, or changing the release candidate.

Its job is to restore enough context to continue work without reconstructing the project from old conversations. It records:

- project background and product intent;
- current architecture and ownership boundaries;
- important workflow and design decisions already made;
- completed development milestones and why they matter;
- current release progress and blocking gate;
- the next permitted development direction;
- the repository and release workflow a new session must follow.

This file is a human development handoff. It does not replace machine contracts or live GitHub evidence. Exact candidate SHA, current CI run, synthetic merge identity, installed-candidate binding, and real-Host verdict must be read from GitHub and Issue #91 because those facts can change after this file is written.

## Project background

`subagents-dispatch` is a Codex Plugin for bounded engineering orchestration over Codex Native Subagents. The project has moved away from the earlier Hook-centered lifecycle correctness path. V4 Native Core keeps Codex Host as the Agent runtime and concentrates project logic on responsibility, routing, acceptance, recovery, writer ownership, evidence, and release safety.

The public Plugin surface is intentionally small:

```text
Orchestrate
Doctor
```

`Orchestrate` is the normal engineering/orchestration surface. `Doctor` owns deterministic installed-product diagnosis and explicitly requested ownership-safe maintenance.

## Durable product boundaries

- Main is the sole managed coordinator.
- Managed children must not create or control another Agent layer.
- Reader and Worker use Luna Max.
- Investigator uses Terra High.
- Solver and Advisor use Sol High.
- Fresh managed children use `fork_turns=none`.
- The managed-child ceiling is four.
- WorkGraph and WorkUnit own responsibility, dependency and acceptance truth.
- ExecutionBinding owns one concrete managed attempt and generation.
- WriterLease owns canonical-workspace managed writer coordination.
- Host `COMPLETED` produces candidate work only. Main acceptance is separate.
- `UNKNOWN` remains fail closed.
- Codex Host owns child materialization, lifecycle, actual capacity, native child identity, effective permission, effective sandbox state and effective collaboration capability.

The historical generic V2 recursion probe proved Host recursive capability on the tested Host. It is platform-capability evidence only. Revised N1 judges actual canonical managed-profile behavior and authoritative descendant evidence. Latent recursive capability alone does not decide the managed N1 verdict.

## Canonical truth owners

Use one owner per kind of truth:

- `contracts/policy.json`: fixed product policy and profile values.
- `docs/v4/architecture.json`: current V4 machine architecture and runtime owners.
- `docs/v4/host-smoke.json`: N0-N8 real-Host campaign contract.
- `docs/v4/technical-debt.json`: explicitly tracked V4 technical debt.
- `docs/architecture.md`: human architecture overview.
- `docs/release-checklist.md`: release gate sequence.
- GitHub: current branch, PR, candidate SHA/tree and CI state.
- Issue #91: append-only real-Host evidence and `REUSE | RERUN | NOT_RUN` preflight decisions.

Do not create another tracked status projection that mirrors candidate SHA, CI or Host verdict. `docs/v4/` is reserved for version-specific machine or maintenance contracts.

## Important development trajectory

The current V4 line has already completed the major repository remediation and simplification work:

1. N1 semantics were corrected so the release gate evaluates canonical managed children and descendant evidence instead of requiring Host-hard removal of recursive capability.
2. Duplicate machine truth projections for Host capability, orchestrate, scheduler, writer lifecycle and phase status were removed.
3. Runtime compatibility residue and dead aliases were reduced while preserving active consumers and safety semantics.
4. Package integrity remains generated and verified by repository tooling.
5. Human documentation was pruned so architecture and release guidance point to canonical machine owners instead of duplicating them.
6. Prose-mirror tests were replaced with structural, contract and behavior checks where wording itself was not an interface.
7. Repository qualification has passed on the required CI matrix for the current release line before the latest handoff-only update. Always verify the current exact head again from GitHub after any repository change.
8. Real Host binding exposed an undefined generic `run_id` requirement. The Host campaign contract was corrected to use Codex-native `session_id` and `thread_id` identities with explicit authoritative evidence sources and fail-closed `UNKNOWN` handling.

The current release work is no longer repository feature development. The active blocker is real Codex Host qualification on the exact current candidate, followed by the remaining release gates.

## Current progress at this handoff

The release branch is `v4/rc5-native-core` and the release PR is #81. PR #81 remains Draft until every required release gate passes. Verify its live head and CI state directly from GitHub before acting.

The latest local qualification preparation established the following workflow facts:

- the Plugin may be installed from the local repository checkout;
- when the installed Plugin source resolves directly to that checkout, pulling the release branch updates the local Plugin source basis;
- in that local-source case, do not run the stable Marketplace updater merely to refresh the exact candidate, because that can change the candidate basis;
- package verification uses `python3 scripts/package_integrity.py --check-generated` and `python3 scripts/package_integrity.py`;
- `python3 scripts/doctor.py --codex-home "$HOME/.codex" --check` must report Plugin package and all five managed profiles healthy before Host probing;
- `Host integration = UNKNOWN` is expected before current Host capability evidence is supplied;
- `Orchestration state = UNKNOWN` is expected when no active task is selected;
- static checkout, Plugin source and package/profile verification are separate from fresh Host identity binding;
- Host environment binding now requires the current root `session_id` and `thread_id` from the authoritative sources defined in `docs/v4/host-smoke.json`; a generic `run_id` is not part of the release contract.

The static candidate/package/profile preparation and the real Host build/capability inspection have been recorded in Issue #91. Because the Host identity contract changed, read the latest candidate and ledger entries before deciding what evidence can be reused. Do not repeat Host actions without the required preflight decision.

## Next development direction

The next allowed work is real Codex Host qualification. Do not start a new repository refactor or feature branch unless the Host campaign finds a real defect or the user explicitly changes direction.

Sequence:

1. Read this file, PR #81 and the newest Issue #91 ledger entries.
2. Verify the current release candidate and exact repository head from GitHub.
3. Verify the local installed Plugin/package/profile basis without spawning or controlling an Agent.
4. Start a fresh Codex Host session when the current preflight requires one.
5. Before invoking `Orchestrate` or any Agent-control primitive, bind the current Host build/version, platform/architecture, root `session_id`, root `thread_id` and actually exposed Native Subagent V2 capability surface from the authoritative evidence sources defined in `docs/v4/host-smoke.json`.
6. Keep unavailable Host facts as `UNKNOWN`. Do not infer Host truth from configuration, requested profile values, repository identity, CLI assumptions or model self-report.
7. Record the fresh Host binding in Issue #91 before the first N0/N1 child spawn.
8. Apply the current N0 and revised N1 preflight using `REUSE | RERUN | NOT_RUN`.
9. Run revised N1 through every fixed managed profile only when the preflight authorizes it. Include the adversarial nested-delegation request and inspect authoritative child action plus descendant identity/spawn-edge evidence.
10. Continue N2-N8 only after the required earlier gate passes.
11. After N0-N8, run exact-candidate Final Review, installed-product/external evidence checks and human two-Skill App observation.
12. Keep publication blocked until every required gate is PASS.

Do not repeat the old generic recursion probe merely because a new chat/session starts.

## Development workflow for a new session

Follow this sequence for repository changes:

1. Read `headoff.md` first, then inspect the relevant machine contracts and live GitHub/Issue #91 state.
2. Check the user's request for missing assumptions or incorrect premises before planning.
3. Write a concrete plan for non-trivial work and verify the plan against current owners and consumers.
4. Create a short-lived branch from the exact intended base. Do not develop directly on the release branch.
5. Keep each change minimal and coherent. Separate behavior changes, refactors and documentation cleanup where possible.
6. Prove active consumers before deleting compatibility surfaces or paths.
7. Preserve UNKNOWN handling, WriterLease settlement, Host identity/materialization evidence, managed-depth checks and strict read-only evidence.
8. Run focused validation first, then the full required repository matrix before calling the work complete.
9. Review the diff adversarially. Ask whether a senior engineer would approve the change and whether a simpler design exists.
10. Merge only after validation is green and the reviewed head is fixed. Use an expected head SHA when merging where supported.
11. Re-run or inspect post-merge exact-head CI and compare candidate/synthetic tree when relevant.
12. Update Issue #91 for release evidence without mutating the candidate solely to record Host status.
13. Update `headoff.md` when project background, durable workflow, important development trajectory, current phase or next direction materially changes.

Never mark repository work complete before verification.

## Maintenance rules

- One semantic fact gets one machine owner.
- Human documentation explains or links canonical owners and should not become a parallel machine oracle.
- Tests protect behavior, schema, ownership, public interfaces and safety invariants. Avoid prose synchronization tests unless wording is itself an interface.
- A compatibility surface needs a real consumer and a removal condition.
- Generate package-integrity data with repository tooling. Do not hand-copy hashes.
- Historical development chronology belongs in Git history or `docs/history/`. `headoff.md` keeps only the history needed for a new development session to understand why the current direction exists.
