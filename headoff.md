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

This file is a human development handoff. It does not replace machine contracts or live GitHub evidence. Exact repository SHA, current CI run, synthetic merge identity, installed-candidate binding, Host qualification basis and real-Host verdict must be read from GitHub and Issue #91 because those facts can change after this file is written.

Updating this file is a development-context change. It does not by itself invalidate real-Host evidence. Host evidence reuse is governed by the Host qualification basis defined by `scripts/release_evidence_v4.py`: the package-integrity manifest, managed profile contract and Host campaign contract. Repository commit/tree still own CI, Final Review, tag and release traceability.

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
- `docs/release-checklist.md`: release gate sequence and Host evidence invalidation boundary.
- `scripts/release_evidence_v4.py`: executable release-evidence verifier and Host qualification basis calculation.
- GitHub: current branch, PR, repository revision SHA/tree and CI state.
- Issue #91: append-only real-Host evidence and `REUSE | RERUN | NOT_RUN` preflight decisions.

Do not create another tracked status projection that mirrors repository SHA, CI or Host verdict. `docs/v4/` is reserved for version-specific machine or maintenance contracts.

## Important development trajectory

The current V4 line has already completed the major repository remediation and simplification work:

1. N1 semantics were corrected so the release gate evaluates canonical managed children and descendant evidence instead of requiring Host-hard removal of recursive capability.
2. Duplicate machine truth projections for Host capability, orchestrate, scheduler, writer lifecycle and phase status were removed.
3. Runtime compatibility residue and dead aliases were reduced while preserving active consumers and safety semantics.
4. Package integrity remains generated and verified by repository tooling.
5. Human documentation was pruned so architecture and release guidance point to canonical machine owners instead of duplicating them.
6. Prose-mirror tests were replaced with structural, contract and behavior checks where wording itself was not an interface.
7. Repository qualification has passed on the required CI matrix for the current release line before the latest context-only update. Always verify the current exact repository revision again from GitHub after any repository change.
8. Real Host binding exposed an undefined generic `run_id` requirement. The Host campaign contract was corrected to use Codex-native `session_id` and `thread_id` identities with explicit authoritative evidence sources and fail-closed `UNKNOWN` handling.
9. A later review exposed a second release-process defect: Host evidence was tied directly to Git commit/tree, which made a development-only `headoff.md` update formally invalidate real-Host work. The release evidence model now separates repository revision identity from Host qualification identity. Host campaign reuse depends on an unchanged package-integrity manifest, profile contract and Host campaign contract. Pure handoff or README changes do not force a Host rerun.

The current release work is no longer repository feature development. The active blocker is real Codex Host qualification on the current Host qualification basis, followed by the remaining release gates.

## Current progress at this handoff

The release branch is `v4/rc5-native-core` and the release PR is #81. PR #81 remains Draft until every required release gate passes. Verify its live head and CI state directly from GitHub before acting.

Current qualification progress recorded in Issue #91:

- local checkout/package/profile preparation has passed for the current product basis;
- package-integrity verification passes and all five managed profiles match the Plugin version;
- `Host integration = UNKNOWN` from Doctor before explicit Host evidence is expected and is not a failure;
- the Host environment identity contract now uses root `session_id` plus root `thread_id`; generic `run_id` is retired;
- root identity binding has been established from current Codex tool execution plus the exact Host-produced rollout;
- full Host environment binding has passed for the current qualification basis, including platform, architecture, Host build, embedded Codex version, root session identity and root thread identity;
- the verified Host was macOS/arm64 with Native Subagent V2 active;
- the binding step performed no Agent-control action and no repository mutation;
- N0 has not started;
- revised N1 has not started;
- N2-N8 have not started;
- publication remains blocked.

The exact root identities, Host build values, evidence paths and ledger entry IDs belong to Issue #91. The completed environment binding is represented there by `HOST-BINDING-ENV-001` and its prerequisite identity entries.

Host evidence reuse after repository changes must now use the qualification-basis rule:

```text
Host qualification basis
= digest(
    .codex-plugin/package-integrity.json,
    contracts/policy.json,
    docs/v4/host-smoke.json
  )
```

If that basis is unchanged, development-only changes such as `headoff.md` do not invalidate the completed Host binding. Repository CI and later Final Review still bind to the exact current Git revision.

## Next development direction

The next allowed work is real Codex Host qualification. Do not start a new repository refactor or feature branch unless the Host campaign finds a real defect or the user explicitly changes direction.

Sequence:

1. Read this file, PR #81 and the newest Issue #91 ledger entries.
2. Verify the current repository revision and CI state from GitHub.
3. Recompute or otherwise verify the current Host qualification basis from the package-integrity manifest, `contracts/policy.json` and `docs/v4/host-smoke.json`.
4. If the Host qualification basis is unchanged from `HOST-BINDING-ENV-001`, record a `REUSE` preflight decision and keep the existing Host environment binding. Do not rebind solely because `headoff.md`, README prose or another development-only document changed.
5. If any Host qualification basis component changed, apply `RERUN` only to the Host evidence affected by that concrete change.
6. Apply the N0 preflight using `REUSE | RERUN | NOT_RUN` before the first child spawn.
7. Run N0 through the canonical managed route and prove exact role/model/effort plus actual `fork_turns=none` behavior from authoritative Host evidence.
8. Apply revised N1 preflight after N0. Run revised N1 through every fixed managed profile only when authorized. Include the adversarial nested-delegation request and inspect authoritative child action plus descendant identity/spawn-edge evidence.
9. Continue N2-N8 only after the required earlier gate passes.
10. After N0-N8, run exact-revision Final Review, installed-product/external evidence checks and human two-Skill App observation.
11. Keep publication blocked until every required gate is PASS.

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
12. Before rerunning any real Host action after a repository change, compare the Host qualification basis. Repository revision changes alone are not a Host invalidation reason.
13. Update Issue #91 for release evidence without mutating runtime/product state solely to record Host status.
14. Update `headoff.md` when project background, durable workflow, important development trajectory, current phase or next direction materially changes.

Never mark repository work complete before verification.

## Maintenance rules

- One semantic fact gets one machine owner.
- Human documentation explains or links canonical owners and should not become a parallel machine oracle.
- Tests protect behavior, schema, ownership, public interfaces and safety invariants. Avoid prose synchronization tests unless wording is itself an interface.
- A compatibility surface needs a real consumer and a removal condition.
- Generate package-integrity data with repository tooling. Do not hand-copy hashes.
- Historical development chronology belongs in Git history or `docs/history/`. `headoff.md` keeps only the history needed for a new development session to understand why the current direction exists.
