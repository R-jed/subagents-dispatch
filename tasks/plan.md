# V4 Contract Truth Simplification Plan

Status: COMPLETE.

This plan records the completed repository remediation from PR #102 and PR #103. Current release-candidate identifiers, CI results and Host verdicts are intentionally not mirrored here. Read GitHub and Issue #91 for live release state.

## Objective

Reduce V4 maintenance complexity while preserving the established runtime and safety behavior.

The root failure mode was semantic duplication: one product fact appeared in several machine JSON files, human documents, compatibility surfaces and string-mirror tests. The N1 contract correction demonstrated that this structure could produce synchronization failures after the underlying implementation semantics were already correct.

## Preserved behavior boundary

The remediation preserved:

- Main-only managed coordination and managed delegation depth 1;
- all five fixed profile model and effort routes;
- canonical managed spawn with `fork_turns=none`;
- UNKNOWN fail-closed lifecycle semantics;
- WorkGraph acceptance semantics;
- WriterLease settlement and one-writer safety;
- Host-owned lifecycle, identity, capacity and effective permission truth;
- candidate-bound real Host release evidence;
- revised N1 managed-depth oracle;
- N8 strict read-only requirement.

## Completed changes

Truth-source convergence:

- removed `docs/v4/host-capability-matrix.json`;
- removed `docs/v4/orchestrate.json`;
- removed `docs/v4/scheduler.json`;
- removed `docs/v4/writer-lifecycle.json`;
- removed self-staling `docs/v4/phase-status.json`;
- retained `docs/v4/architecture.json` as the current machine architecture/runtime-owner map;
- retained `docs/v4/host-smoke.json` as the real-Host campaign oracle;
- moved current candidate/CI truth to GitHub and real-Host release truth to Issue #91.

Runtime and compatibility cleanup:

- corrected residual Host-hard N1 language in active guardrails and runtime guidance;
- removed unused normalized `managed_child_containment` output while continuing to validate historical input evidence when supplied;
- consolidated fresh attempt-number calculation behind one implementation while preserving facade/core safety checks;
- removed verified-dead `route_profile` compatibility alias;
- removed verified-dead `scheduler_decision` compatibility alias.

Test cleanup:

- migrated tests from deleted projections to canonical machine owners and observable behavior;
- migrated stale consumers from removed aliases to supported functions;
- removed newly discovered prose-mirror assertions instead of restoring copied wording;
- added structural checks preventing self-staling tracked candidate-status snapshots from returning.

## Validation result

The implementation went through repeated full repository matrices during remediation. Intermediate failures were used to locate stale test consumers and one new prose-mirror assertion. No runtime behavior regression was identified from those failures.

Before merge, the refactor passed the complete release-context matrix. After merge, the release branch passed the complete matrix again, including:

- Ubuntu Python 3.11;
- Ubuntu Python 3.12;
- macOS Python 3.11;
- Windows Python 3.11;
- generated package integrity;
- pinned official OpenAI Plugin validator where applicable;
- Ruff;
- full pytest;
- managed Agent profile lifecycle;
- aggregate `policy-tests`.

The final adversarial diff review found no unintended product behavior change.

## Deferred debt

These items were deliberately kept outside this remediation:

- `write_state`: active internal setup/test consumers remain;
- `team_plan_revision`: removal requires a separate state-schema and migration change;
- Experiment Plane calibration monkeypatch consolidation: known non-runtime debt requiring its own bounded refactor;
- N8 semantics: product-contract change requires separate intent review and specification.

## Lessons and permanent rules

1. One semantic fact gets one machine owner.
2. Human documentation explains or links canonical owners and does not become a parallel oracle.
3. Tests verify behavior, schema, ownership or public interface. Exact prose synchronization is used only when wording itself is an interface.
4. A compatibility surface survives only with a confirmed consumer and removal condition.
5. A normalized runtime field needs a real consumer or a documented evidence-boundary reason.
6. Preserve safety boundaries even when they cost lines of code.
7. Generate package-integrity data with the repository generator rather than manually copying hashes.
8. Do not promote intermediate CI evidence to a later head.
9. For stacked PRs, merge dependencies first, retarget the dependent PR to the real release branch, preserve the validated tree during history alignment when possible, then rerun the full release-context matrix.
10. Current candidate SHA, CI and Host verdict belong in GitHub and Issue #91, not a tracked self-updating status snapshot.
11. Handoff text should describe durable boundaries and next procedures so it remains useful after the commit that introduces it.

## Next work

This plan is closed. Release qualification continues through `docs/v4/current-state.md`, `docs/v4/host-smoke.json`, `docs/release-checklist.md`, GitHub PR #81 and Issue #91.

The next release work is exact installed-candidate and Host-environment binding followed by the required `REUSE | RERUN | NOT_RUN` preflight and revised canonical managed-profile N1 campaign. Publication remains blocked until all required Host and later release gates pass.
