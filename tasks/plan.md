# V4 Contract Truth Simplification Plan

## Objective

Reduce V4 maintenance complexity while preserving the behavior and safety semantics of PR #102 exact head `54aec5eeb0cbe2d9e44c7ba4e3a748c65d64c6ce`.

The primary failure mode to remove is semantic duplication: one product fact currently appears in several machine JSON files, human documents and string-mirror tests. N1 remediation demonstrated that this structure creates avoidable synchronization failures even when the underlying implementation is correct.

## Non-negotiable behavior boundary

Preserve:

- Main-only managed coordination and managed delegation depth 1;
- all five fixed profile model and effort routes;
- canonical managed spawn with `fork_turns=none`;
- UNKNOWN fail-closed lifecycle semantics;
- WorkGraph acceptance semantics;
- WriterLease settlement and one-writer safety;
- Host-owned lifecycle, identity, capacity and effective permission truth;
- candidate-bound real Host release evidence;
- revised N1 managed-depth oracle from PR #102;
- N8 strict read-only requirement until separately specified and reviewed.

This refactor must not silently change product behavior.

## Simplification rules

1. One semantic fact has one machine owner.
2. Human documentation explains or links owners and does not become a parallel oracle.
3. Tests verify behavior, schema, ownership or explicit references. Avoid exact prose synchronization tests unless wording itself is a public interface.
4. Temporary RC compatibility survives only with a confirmed consumer and explicit removal condition.
5. A normalized runtime field must have an actual runtime consumer or a documented evidence-boundary reason.
6. Keep facade boundaries that protect supported APIs, but remove duplicate implementations behind them.
7. Do not simplify proven safety boundaries merely to reduce line count.

## Current progress

Completed on `refactor/v4-contract-truth-simplification`:

- removed `docs/v4/host-capability-matrix.json`, `docs/v4/orchestrate.json`, `docs/v4/scheduler.json`, and `docs/v4/writer-lifecycle.json` as competing machine projections;
- removed `docs/v4/phase-status.json` because commit-bound PASS/SHA state inside the same Git history is self-staling by construction;
- migrated tests from deleted projections to canonical `docs/v4/architecture.json`, `docs/v4/host-smoke.json`, and runtime behavior;
- corrected residual Host-hard N1 language in `contracts/guardrails.md`, `skills/orchestrate/SKILL.md`, and `docs/native-subagent-runtime.md`;
- made `managed_child_containment` input-compatible diagnostic evidence only and removed it from normalized runtime snapshots;
- consolidated fresh attempt-number calculation behind one implementation while retaining facade/core safety checks;
- removed verified-dead `route_profile` and `scheduler_decision` compatibility aliases;
- retained `write_state` as an internal test/setup helper because it still has substantial active consumers;
- deferred `team_plan_revision` schema removal and Experiment Plane calibration consolidation to independent changes because their blast radius is larger than this maintenance refactor.

Intermediate CI established package-integrity, official Plugin validator, and Ruff success. A full pytest run exposed only stale test consumers of deleted projections/aliases: `527 passed, 8 failed`. Those eight consumers have been migrated. Final exact-head matrix is still required before completion.

## Batch 1: current truth-source convergence

Status: implementation complete, final matrix pending.

- Consumer proof completed for the removed current-state/projection files.
- Current candidate status is owned by GitHub branch/PR/CI evidence and Issue #91 for real-Host release evidence.
- `docs/v4/architecture.json` owns current machine architecture; `docs/v4/host-smoke.json` owns the real-Host campaign oracle.
- Tests now protect owner existence, behavior, and removal of stale projections rather than copied prose.

## Batch 2: production duplicate and compatibility cleanup

Status: bounded cleanup complete for the proven low-risk surfaces.

Completed:

- duplicate fresh attempt-number calculation consolidated;
- `route_profile` removed;
- `scheduler_decision` removed.

Deferred with explicit reason:

- `write_state`: active internal setup/test consumers remain;
- `team_plan_revision`: state-schema and migration blast radius requires a separate compatibility migration.

## Batch 3: runtime diagnostic model cleanup

Status: implementation complete, final matrix pending.

`managed_child_containment` remains accepted and validated when historical Host evidence supplies it. The normalized runtime snapshot no longer carries the field because scheduler and Doctor execution decisions do not consume it. Actual recursive Host capability remains release evidence, while ordinary runtime readiness depends on required native lifecycle capabilities and fresh-context spawn support.

Because shipped runtime bytes changed, package integrity was regenerated from the repository generator. Candidate-bound Host evidence must be rebound after the final candidate is established.

## Deferred debt

Keep Experiment Plane calibration core/adapter consolidation separate from release-critical Native Core. It is known non-runtime debt and does not justify expanding this refactor.

## N8 boundary

Do not alter N8 during behavior-preserving simplification. Its strict effective Advisor read-only requirement requires a separate original-intent review before any product-contract change.

## Final validation and completion

Before merge, the exact final head must have:

- Ruff PASS;
- full pytest PASS;
- package integrity PASS;
- managed Agent profile lifecycle PASS;
- official OpenAI Plugin validator PASS where applicable;
- Ubuntu Python 3.11 PASS;
- Ubuntu Python 3.12 PASS;
- macOS Python 3.11 PASS;
- Windows Python 3.11 PASS;
- aggregate policy-tests PASS;
- adversarial diff review confirming behavior preservation and improved one-owner boundaries.

After the final matrix passes, compare the resulting PR behavior and contract surface against PR #102 baseline before marking the remediation complete. Do not promote intermediate workflow evidence to the final head.
