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

## Batch 1: current truth-source convergence

- Prove all consumers of `docs/v4/phase-status.json` and `docs/v4/host-capability-matrix.json`.
- Archive non-authoritative current-state artifacts when their current location creates a competing truth source.
- Remove tests that only require permanently stale/PENDING mirror content.
- Keep canonical release truth in `docs/v4/host-smoke.json`, `docs/v4/architecture.json`, current GitHub/Issue #91 evidence and runtime behavior.
- Replace prose mirror assertions with owner/reference assertions where a regression guard is still valuable.

Verification after batch:

- focused affected tests;
- full pytest;
- Ruff;
- no shipped package byte change expected.

## Batch 2: production duplicate and compatibility cleanup

Investigate before deletion:

- duplicate fresh attempt-number calculation in `execution_lifecycle_v4.py` and `execution_lifecycle_v4_core.py`;
- `route_profile` compatibility alias;
- `scheduler_decision` compatibility alias;
- compatibility `write_state` create-only alias;
- `team_plan_revision` RC compatibility field and `validate_team_plan.py` consumers.

Only remove a compatibility surface when repository and external release tooling have no current required consumer. Prefer one implementation behind an explicit supported facade.

Verification after each isolated change:

- focused unit tests;
- full pytest before the next semantic area;
- compare current behavior with PR #102 baseline.

## Batch 3: runtime diagnostic model cleanup

Evaluate `managed_child_containment` after consumer proof.

Preferred shape if compatibility allows:

- accept historical input field at the evidence boundary;
- validate it when supplied;
- do not carry it in the normalized runtime snapshot when no runtime decision consumes it;
- keep actual recursive Host capability and N1 managed behavior in release evidence, not ordinary readiness state.

Because `scripts/host_capabilities.py` is shipped, any byte change requires package-integrity regeneration and invalidates previously bound Host candidate evidence.

## Deferred debt

Keep Experiment Plane calibration core/adapter consolidation separate from release-critical Native Core unless a small independently verifiable patch emerges. It is known non-runtime debt and should not enlarge this refactor unnecessarily.

## N8 boundary

Do not alter N8 during behavior-preserving simplification. Its strict effective Advisor read-only requirement requires a separate original-intent review before any product-contract change.

## Validation and completion

For every batch:

1. prove the consumer and owner model before editing;
2. make the smallest coherent change;
3. run focused tests;
4. run full pytest before marking the batch complete;
5. review the diff for new duplicate truth or compatibility residue.

Before merge:

- Ruff PASS;
- full pytest PASS;
- package integrity PASS when shipped bytes change;
- managed Agent profile lifecycle PASS when relevant;
- official OpenAI Plugin validator PASS where applicable;
- Ubuntu Python 3.11 PASS;
- Ubuntu Python 3.12 PASS;
- macOS Python 3.11 PASS;
- Windows Python 3.11 PASS;
- aggregate policy-tests PASS;
- adversarial diff review confirms behavior is preserved and one-owner rules are improved.

Do not mark the remediation complete until the exact final head has passed the full repository matrix.
