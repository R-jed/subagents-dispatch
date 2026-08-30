# Headoff

Updated: 2026-08-30.

## Purpose

This is the development-session handoff for `subagents-dispatch`. It is continuity context only. It is not Plugin runtime, a product contract, Host qualification input, release evidence, or a release gate.

## Current 1.0.0 closure

The active 1.0.0 contract-close work is isolated on:

```text
worktree: isolated 1.0 contract-close worktree
branch: feat/1.0-contract-close
base: 92cc7e8766021f2c1962c849ef34b34a81708a7e
```

The release architecture is being simplified without changing the Native Core runtime engine, fixed profiles, WorkGraph, WriterLease, Doctor, or `contracts/policy.json`.

Current intended release flow:

```text
finish contract-close verification
-> merge approved source into the release line and freeze the exact release commit
-> final release-source repository / CI verification on that frozen commit
-> freeze Host qualification identity
-> real Host N0-N7
-> bind Main-owned pre-review request
-> one fresh exact-release-source Advisor Final Review
-> external release evidence verification
-> installed-product verification
-> human product smoke
-> v1.0.0
```

## Contract decisions

Routing uses minimum useful fanout:

- Main-only is preferred when delegation adds no value.
- One child is the common delegated shape when one distinct responsibility benefits from delegation.
- Multiple children may start immediately only for independently ready, non-duplicative responsibilities that are safe to overlap and materially benefit from concurrency.
- Spare capacity never creates work.
- A delegated responsibility substitutes for Main doing the same investigation or implementation. Main verifies, integrates, and accepts instead of duplicating it.
- A short user-visible route rationale may be shown, but no persistent `solo`, `delegate`, `audit`, `full`, or other route-mode state is added.

Host qualification and Final Review are separate:

- `docs/v4/host-smoke.json` owns N0-N7 Host qualification.
- `contracts/final-review.md` owns the one exact-source Final Review.
- `scripts/release_evidence_v4.py` binds the two independent evidence lifecycles.
- The Final Review result must bind a Main-owned pre-review request so the reviewer cannot downgrade `hard_isolation_required` or invent a missing no-edit instruction after launch.

Final Review assurance has three outcomes:

```text
A  effective Host read-only
   -> enforced_read_only

B  broader Host write capability + hard isolation not required
   + Advisor semantic mutation authority remains none
   + explicit no-edit/no-external-side-effect instruction
   + exact review artifact unchanged before/after
   -> artifact_immutability_fallback with residual risk disclosure

C  permission unobservable/ambiguous, hard isolation required without enforced read-only,
   artifact mutation, or reviewer boundary violation
   -> INSUFFICIENT_EVIDENCE / fail closed
```

The fallback is not Host-hard isolation. `review-artifact.py` does not cover ignored build/cache artifacts or prove absence of external side effects.

## Historical Host evidence

The build7119 N0-N8 campaign and permission RCA are preserved as historical evidence in:

- `docs/history/v4/host-qualification-handoff-build7119.md`
- `docs/history/v4/headoff-pre-1.0-contract-close-build7119.md`
- Issue #91

That evidence does not qualify the new contract because `docs/v4/host-smoke.json` changes the Host contract digest from the old N0-N8 basis to the new N0-N7 basis. Do not rewrite historical N8 observations as if they had been collected under the new contract.

No formal Host N0-N7 campaign has started for the new contract-close candidate.

## Current boundaries

Do not:

- modify `scripts/orchestrate_v4.py`, scheduler, WorkGraph, WriterLease, managed profiles, Doctor logic, or `contracts/policy.json` merely for this simplification;
- hard-code one-child-first;
- add a dynamic Luna/Terra/Sol escalation ladder;
- start formal Host qualification before the source, package manifest, Host contract, and tests are finalized;
- treat a development code review as the release Final Review.

## Next safe continuation

Finish the isolated contract-close diff, regenerate package integrity, run focused and full repository verification, official Plugin validation, and isolated managed-profile lifecycle checks. Then perform a fresh adversarial development review of the complete diff.

Only after the verified change is merged/frozen should the new Host N0-N7 campaign begin. The one release Final Review runs after Host qualification against the exact final release source.
