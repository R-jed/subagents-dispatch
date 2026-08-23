# Headoff

Updated: 2026-08-23.

## Purpose

This file is the project context transfer entrypoint for a new development chat/session. A new development session should read this file first before planning, coding, reviewing, running Host probes, or changing the release source.

Its job is to restore enough context to continue work without reconstructing the project from old conversations. It records:

- project background and product intent;
- current architecture and ownership boundaries;
- important workflow and design decisions already made;
- completed development milestones and why they matter;
- current release progress and blocking gate;
- the next permitted development direction;
- the repository and release workflow a new session must follow.

This file is a human development handoff. It does not replace machine contracts or live GitHub evidence. Exact release-source SHA/tree, current CI run, synthetic merge identity, installed-product binding, Host qualification identity and real-Host verdict must be read from GitHub and Issue #91 because those facts can change after this file is written.

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
- `docs/release-checklist.md`: release gate sequence and identity/invalidation rules.
- GitHub: current branch, PR, final release-source SHA/tree and CI state.
- Issue #91: append-only real-Host evidence and `REUSE | RERUN | NOT_RUN` preflight decisions.

Do not create another tracked status projection that mirrors live GitHub or Host verdicts. `docs/v4/` is reserved for version-specific machine or maintenance contracts.

## Release identity model

Keep two identity layers separate.

Host qualification identity is the basis that determines whether an existing real-Host campaign may be reused:

```text
runtime_manifest_sha256
profile_contract_sha256
host_contract_sha256
```

These correspond to:

```text
.codex-plugin/package-integrity.json
contracts/policy.json
docs/v4/host-smoke.json
```

If all three qualification digests remain unchanged, a source-only commit such as an update to `headoff.md`, ordinary documentation, or non-shipped release tooling does not invalidate already-conclusive Host evidence. Reuse must still be recorded in Issue #91 after comparing the digests.

Release source identity is the exact final Git commit/tree. It is used by final repository qualification, the release envelope and Final Review. Source-only changes therefore refresh the final Git identity and Final Review, while leaving Host evidence reusable when the Host qualification identity is unchanged.

Do not infer invalidation from the fact that HEAD changed. Decide it from the qualification basis for Host evidence and from the final source identity for release-source checks.

## Important development trajectory

The current V4 line has already completed the major repository remediation and simplification work:

1. N1 semantics were corrected so the release gate evaluates canonical managed children and descendant evidence instead of requiring Host-hard removal of recursive capability.
2. Duplicate machine truth projections for Host capability, orchestrate, scheduler, writer lifecycle and phase status were removed.
3. Runtime compatibility residue and dead aliases were reduced while preserving active consumers and safety semantics.
4. Package integrity remains generated and verified by repository tooling.
5. Human documentation was pruned so architecture and release guidance point to canonical machine owners instead of duplicating them.
6. Prose-mirror tests were replaced with structural, contract and behavior checks where wording itself was not an interface.
7. Repository qualification has passed on the required CI matrix for the current release line. Always verify the current exact source head again from GitHub after a repository change.
8. Real Host binding exposed an undefined generic `run_id` requirement. The Host campaign contract and release-evidence verifier were corrected to use Codex-native root `session_id` and `thread_id` identities with explicit authoritative evidence sources and fail-closed `UNKNOWN` handling.
9. The corrected Host-binding workflow was exercised on a real fresh Codex root task. The evidence chain successfully correlated exact checkout, clean worktree, Host build, embedded Codex version, platform, architecture, `CODEX_THREAD_ID`, one exact root rollout, `session_meta.id`, `session_meta.session_id`, repository cwd and Native Subagent V2 runtime.
10. The root environment binding reached PASS without spawning or controlling any Agent and without repository mutation during the binding step.
11. A later review found that the external release-evidence verifier still conflated Host qualification with Git commit/tree. That design is being corrected so handoff/documentation updates do not force needless Host reruns when the runtime/profile/Host-contract digests are unchanged.

The active release work is real Codex Host qualification followed by the remaining release gates. New product feature development is out of scope unless a Host probe finds a real defect or the user changes direction.

## Current progress at this handoff

The release branch is `v4/rc5-native-core` and the release PR is #81. PR #81 remains Draft until every required release gate passes. Verify its live head and CI state directly from GitHub before acting.

The latest qualification work established these workflow facts:

- the Plugin may be installed from the local repository checkout;
- when the installed Plugin source resolves directly to that checkout, pulling the release branch updates the local Plugin source basis;
- in that local-source case, do not run the stable Marketplace updater merely to refresh the exact source, because that can change the installation basis;
- package verification uses `python3 scripts/package_integrity.py --check-generated` and `python3 scripts/package_integrity.py`;
- `python3 scripts/doctor.py --codex-home "$HOME/.codex" --check` must report Plugin package and all five managed profiles healthy before Host probing;
- `Host integration = UNKNOWN` is expected before current Host capability evidence is supplied;
- `Orchestration state = UNKNOWN` is expected when no active task is selected;
- static checkout, Plugin source and package/profile verification are separate from fresh Host identity binding;
- Host environment binding requires the current root `session_id` and `thread_id` from the authoritative sources defined in `docs/v4/host-smoke.json`; generic `run_id` is not part of the release contract;
- `thread_id` may be bound from current root tool-execution `CODEX_THREAD_ID` and must agree with the exact root rollout `session_meta.id` when both are used;
- `session_id` may be bound from `session_meta.session_id`; equality between root `session_id` and `thread_id` is valid when that is what the Host reports;
- the verified Host environment used macOS 27.0 build 26A5416b on arm64, ChatGPT/Codex Desktop bundle `com.openai.codex`, Host short version `26.818.41509`, bundle build `6962`, embedded rollout Codex `0.149.0-alpha.4.1`, and Native Subagent V2;
- the complete root Host environment binding was recorded as PASS in Issue #91 before N0;
- N0 and N1 had not started at the time this handoff was refreshed.

For exact IDs, source SHA/tree, ledger comment IDs and live PASS/UNKNOWN state, use Issue #91. Do not copy those volatile values from this document into a new decision without checking the ledger.

## Next development direction

Finish the Host-qualification identity separation first. This is release tooling and handoff correctness work. It must not change the shipped runtime manifest, managed profile contract or Host campaign contract.

After that source-only fix is merged and repository CI is green:

1. Compare the three Host qualification digests with the basis used by the already-PASS root Host environment binding.
2. If all three are unchanged, record `REUSE` in Issue #91 for the Host environment binding. Do not restart or repeat the binding merely because the Git commit changed.
3. Confirm the local installed Plugin/package/profile basis remains healthy.
4. Apply the N0 preflight using `REUSE | RERUN | NOT_RUN`.
5. Run N0 only when that preflight authorizes the first managed spawn.
6. Run revised N1 through every fixed managed profile only when N0 and the N1 preflight permit it. Include the adversarial nested-delegation request and inspect authoritative child action plus descendant identity/spawn-edge evidence.
7. Continue N2-N8 only after the required earlier gates pass.
8. After N0-N8, run final-source repository checks, a fresh Final Review, installed-product/external evidence checks and human two-Skill App observation.
9. Keep publication blocked until every required gate is PASS.

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
11. Re-run or inspect post-merge exact-head CI and compare source/synthetic tree when relevant.
12. Update Issue #91 for release evidence without using tracked repository files as the live Host ledger.
13. Update `headoff.md` when project background, durable workflow, important development trajectory, current phase or next direction materially changes.

Never mark repository work complete before verification.

## Maintenance rules

- One semantic fact gets one machine owner.
- Human documentation explains or links canonical owners and should not become a parallel machine oracle.
- Tests protect behavior, schema, ownership, public interfaces and safety invariants. Avoid prose synchronization tests unless wording is itself an interface.
- A compatibility surface needs a real consumer and a removal condition.
- Generate package-integrity data with repository tooling. Do not hand-copy hashes.
- Host evidence invalidation is determined by the Host qualification identity, not by Git HEAD alone.
- Final Review invalidation is determined by the exact final release source and review artifact identity.
- Historical development chronology belongs in Git history or `docs/history/`. `headoff.md` keeps only the history needed for a new development session to understand why the current direction exists.
