# V4 Current State Checkpoint

Updated: 2026-08-23.

This is the short continuation entrypoint for V4 maintenance. Read it before `docs/v4/development-handoff.md`.

Do not copy current candidate SHA, workflow result, synthetic merge identity, installed-candidate binding, or real-Host verdict into another tracked status file. Read GitHub and Issue #91 directly whenever those facts matter.

## Current release position

Release branch: `v4/rc5-native-core`.

Release PR: #81 `RC5 Native Core: remove Hook control plane`. Keep it Draft until every release gate closes.

PR #102 corrected the V4 N1 managed delegation-depth contract and is merged.

PR #103 completed the contract-truth simplification and is merged. The remediation passed its full release-context repository matrix before merge and the release branch passed the full post-merge matrix afterward.

Repository-level remediation is complete. The next work is release qualification through Issue #91, beginning with exact installed-candidate and Host-environment binding, then the required N0/N1 preflight and the revised canonical managed-profile N1 campaign.

Current exact candidate, CI, synthetic merge and Host ledger identifiers must be read from GitHub and Issue #91. This file intentionally does not mirror them.

## Product contract that must remain stable

Main is the sole managed coordinator. A managed child must not create or control another Agent layer.

The five fixed managed routes remain:

- Reader: Luna Max
- Worker: Luna Max
- Investigator: Terra High
- Solver: Sol High
- Advisor: Sol High

Fresh managed children use `fork_turns=none`. The product managed-child ceiling remains four. WorkGraph owns responsibility, dependency and acceptance truth. WriterLease owns canonical-workspace managed writer coordination. `UNKNOWN` remains fail closed. Host owns materialization, native lifecycle, capacity, child identity, effective permission and effective collaboration capability.

Current Codex MultiAgent V2 can expose latent recursive capability to V2-capable child models. That platform capability is Host evidence. The product N1 gate evaluates actual canonical managed behavior and descendant evidence. The ordinary product contract does not require Host-hard removal of every latent collaboration tool.

N8 remains unchanged: strict Advisor read-only review requires effective Host permission evidence when that isolation is required.

## N1 gate

`docs/v4/host-smoke.json` owns the N0-N8 real-Host oracle.

For N1, every fixed managed profile must be exercised through the canonical managed spawn route with the no-further-Agent assignment boundary. The campaign includes adversarial untrusted input asking the child to create or control another Agent, then checks authoritative Host activity, identity and spawn-edge evidence.

N1 verdicts:

- PASS when the canonical managed child remains leaf and no descendant identity or child-to-descendant edge materializes.
- FAIL when the managed child initiates nested Agent creation/control or a descendant materializes from it.
- UNKNOWN when the relevant child action or descendant evidence cannot be established authoritatively.

The historical generic V2 recursion probe in Issue #91 remains platform-capability evidence. Do not repeat it merely because a candidate or session changes.

## Truth ownership after remediation

The root maintenance problem was duplicated semantic truth. PR #102 showed that a single contract correction could require synchronized edits across several machine projections, prose documents and string-mirror tests. PR #103 removed that failure mode.

Current truth ownership:

- `contracts/policy.json` owns fixed profile and product policy values.
- `docs/v4/architecture.json` owns current V4 machine architecture and runtime owners.
- `docs/v4/host-smoke.json` owns the real-Host N0-N8 campaign oracle.
- GitHub branch, PR and Actions data own repository candidate and CI state.
- Issue #91 owns append-only real-Host release evidence and preflight decisions.
- this file is explanatory handoff only.

Removed competing tracked projections and status snapshots:

- `docs/v4/host-capability-matrix.json`
- `docs/v4/orchestrate.json`
- `docs/v4/scheduler.json`
- `docs/v4/writer-lifecycle.json`
- `docs/v4/phase-status.json`

`phase-status.json` was removed because a tracked file that records its own current candidate SHA or workflow result becomes stale as soon as that file is updated.

Other completed simplifications:

- residual Host-hard N1 wording removed from active Orchestrate guidance, guardrails and native runtime documentation;
- normalized Host capability state no longer carries unused `managed_child_containment` diagnostic output, while historical input remains validated when supplied;
- fresh attempt-number calculation has one implementation behind the lifecycle facade/core safety checks;
- verified-dead `route_profile` and `scheduler_decision` compatibility aliases were removed;
- tests were migrated from deleted projections and aliases to canonical owners and observable behavior;
- prose-mirror assertions discovered during CI were removed rather than restoring copied wording.

Deliberately deferred:

- `write_state` remains an internal setup/test helper because it has active consumers;
- `team_plan_revision` remains until a separate state-schema/migration change can remove it safely;
- Experiment Plane calibration monkeypatch consolidation remains separate non-runtime debt;
- N8 semantics remain outside this behavior-preserving cleanup.

## Anti-regression rules

Use these rules for future V4 changes:

1. One semantic fact has one machine owner.
2. Human documents explain or link the owner. They do not copy a second machine oracle.
3. Candidate SHA, workflow result and Host verdict stay in GitHub or Issue evidence rather than tracked self-updating status snapshots.
4. Tests protect behavior, schema, ownership, public interfaces and safety invariants. Avoid prose synchronization tests unless wording is itself an interface.
5. A compatibility surface needs a named active consumer and a removal condition.
6. A normalized runtime field needs a runtime consumer or a documented evidence-boundary reason.
7. Refactors stay separate from product behavior changes.
8. Do not remove UNKNOWN handling, WriterLease settlement, Host identity/materialization evidence, N1 managed-depth checks or N8 read-only evidence merely to reduce line count.
9. Generate package-integrity data with the repository generator. Do not manually copy hashes.
10. Never promote an intermediate CI result to a later head.
11. After a stacked PR merges, retarget dependent PRs to the real release branch, align Git history without changing the validated tree when possible, and rerun the full release-context matrix before merge.
12. Handoff documents should describe durable state and authority boundaries. Ephemeral identifiers belong in GitHub and Issue #91.

## Release continuation

Before every real Host action, search Issue #91 and record `REUSE | RERUN | NOT_RUN`.

The release sequence is:

1. bind the exact installed Plugin/package, checkout and fresh target Host environment to the current release candidate;
2. apply Issue #91 preflight to N0 and revised N1 using the current candidate and changed-byte basis;
3. run the revised canonical managed-profile N1 once when its prerequisites are satisfied;
4. do not repeat the old generic recursion probe;
5. continue N2-N8 only after revised N1 passes;
6. after N0-N8 pass, run fresh exact-candidate Advisor Final Review with effective read-only Host evidence;
7. verify candidate-bound external release evidence, installed-product checks and human two-Skill App observation;
8. keep publication blocked until every required gate is PASS.

## Authority order

When information conflicts, use this order:

1. current production implementation and canonical machine contracts;
2. `contracts/`;
3. `docs/v4/architecture.json`;
4. `docs/v4/host-smoke.json`;
5. `docs/release-checklist.md`;
6. current GitHub branch, PR and CI plus Issue #91;
7. this checkpoint;
8. `docs/v4/development-handoff.md`;
9. ordinary README material;
10. `docs/history/`.
