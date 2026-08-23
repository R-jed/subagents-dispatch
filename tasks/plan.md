# V4 Contract Truth Simplification Plan

Status: COMPLETE.

This record summarizes the completed PR #102 and PR #103 repository remediation. Live candidate identifiers, CI results and Host verdicts belong in GitHub and Issue #91.

## Preserved behavior

The remediation kept Main-only managed coordination, delegation depth 1, the five fixed profile routes, `fork_turns=none`, UNKNOWN fail-closed behavior, WorkGraph acceptance semantics, WriterLease settlement, Host-owned lifecycle/identity/capacity/effective permission truth, revised managed N1 and the strict N8 read-only requirement.

## Completed simplification

- removed competing V4 machine projections and the self-staling phase-status snapshot;
- retained `docs/v4/architecture.json` as the machine architecture/runtime-owner map;
- retained `docs/v4/host-smoke.json` as the real-Host campaign oracle;
- moved live candidate/CI truth to GitHub and Host evidence to Issue #91;
- corrected residual Host-hard N1 wording in active contracts and guidance;
- removed unused normalized `managed_child_containment` output while preserving historical input validation;
- consolidated fresh attempt-number calculation;
- removed dead `route_profile` and `scheduler_decision` aliases;
- migrated tests from deleted projections and aliases to canonical owners and observable behavior.

## Deferred debt

- `write_state` remains because active internal test/setup consumers exist.
- `team_plan_revision` requires a separate state-schema migration.
- Experiment Plane calibration consolidation remains separate non-runtime debt.
- N8 semantics require separate product-intent review before any change.

## Permanent rules

1. One semantic fact gets one machine owner.
2. Human docs explain or link canonical owners rather than becoming a parallel oracle.
3. Tests verify behavior, schema, ownership or public interfaces instead of copied prose.
4. Compatibility surfaces require a real consumer and removal condition.
5. Preserve safety boundaries even when simplification would remove lines.
6. Generate package-integrity data with repository tooling.
7. Do not promote intermediate CI evidence to a later head.
8. Current candidate SHA, CI and Host verdict belong in GitHub and Issue #91.

## Continuation

This plan is closed. New development sessions continue from root `headoff.md`, then consult `docs/v4/host-smoke.json`, `docs/release-checklist.md`, GitHub and Issue #91 as needed.

`headoff.md` is the project context-transfer entrypoint for background, important workflow history, current progress and next direction. The next release work is exact installed-candidate and Host-environment binding, followed by the required preflight and revised canonical managed-profile N1 campaign. Publication remains blocked until all required Host and later release gates pass.
