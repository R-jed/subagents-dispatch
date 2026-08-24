# V4 Deep Review Remediation Tasks

This checklist tracks repository fixes identified by the independent full-repository Deep Review. Live release candidate, CI, review, and Host verdicts remain in GitHub and Issue #91 rather than being mirrored as mutable source status.

- [x] Fix plan-only WorkUnit validation
  - Acceptance: malformed intent, goal, dependency containers/elements, unknown dependencies, and cyclic dependencies fail closed through the canonical WorkUnit/state validation path.
  - Verify: focused adversarial plan-only tests plus full pytest.
  - Files: `scripts/orchestrate_v4.py`, focused tests, package-integrity manifest.

- [x] Remove `headoff.md` from Host qualification authority
  - Acceptance: phase hard stops and Issue #91 evidence remain mandatory; editing or committing `headoff.md` is never required to advance H0-H10.
  - Verify: staged Host plan contains no headoff-driven revalidation loop and explicitly classifies headoff as development-only context.
  - Files: `tasks/real-host-qualification-plan.md`, `README_AI.md`, `headoff.md`, relevant tests/docs.

- [x] Repair stale N1/task truth
  - Acceptance: no current spec points to deleted `docs/v4/current-state.md`; tracked task files do not duplicate live candidate or Host status.
  - Verify: direct spec review and truth-closure tests.
  - Files: `tasks/SPEC-n1-managed-depth.md`, this checklist.

- [x] Make PR CI verify the exact head commit
  - Acceptance: pull-request jobs checkout the PR head SHA explicitly and assert checked-out Git HEAD matches the expected commit.
  - Verify: GitHub Actions logs show exact head identity before the platform matrix runs.
  - Files: `.github/workflows/ci.yml`.

- [x] Decouple release-evidence tests from the development handoff
  - Acceptance: source-only release identity behavior is tested with generic non-runtime source changes rather than `headoff.md`.
  - Verify: focused release-evidence tests plus full pytest.

- [x] Refresh generated package integrity
  - Acceptance: `.codex-plugin/package-integrity.json` exactly matches the changed shipped runtime bytes.
  - Verify: generated package-integrity check passes on the remediation candidate.

## Merge gate

Do not add a final source checkbox whose only purpose is to record that the final source passed CI; changing that checkbox would create a new source that needs verification again.

Before merge, read the live PR head and require the complete repository matrix plus aggregate `policy-tests` to PASS on that exact head. Perform a fresh adversarial diff review and confirm no required finding remains. After merge, verify the exact release-branch head again and record Host qualification invalidation/preflight decisions in Issue #91.

Because this remediation changes the shipped runtime manifest, real Host H1 must not resume from the old H0 basis without the required qualification-basis re-evaluation.
