# V4 Deep Review Remediation Tasks

This checklist tracks the repository fixes identified by the independent full-repository Deep Review. Live release candidate, CI, and Host verdicts remain in GitHub and Issue #91.

- [x] Fix plan-only WorkUnit validation
  - Acceptance: malformed intent, goal, dependency type, unknown dependency, and cyclic dependency fail closed through canonical WorkUnit/state validation.
  - Verify: focused adversarial plan-only tests plus full pytest.
  - Files: `scripts/orchestrate_v4.py`, focused tests, package-integrity manifest.

- [x] Remove `headoff.md` from Host qualification authority
  - Acceptance: phase hard stops and Issue #91 evidence remain mandatory; editing or committing `headoff.md` is never required to advance H0-H10.
  - Verify: staged Host plan contains no headoff-driven revalidation loop and explicitly classifies headoff as development-only context.
  - Files: `tasks/real-host-qualification-plan.md`, `README_AI.md`, relevant tests/docs.

- [x] Repair stale N1/task truth
  - Acceptance: no current spec points to deleted `docs/v4/current-state.md`; live state is not duplicated into tracked task documents.
  - Verify: direct spec review and truth-closure tests.
  - Files: `tasks/SPEC-n1-managed-depth.md`, this checklist.

- [x] Make PR CI verify the exact head commit
  - Acceptance: pull-request jobs checkout the PR head SHA explicitly and assert the checked-out Git HEAD matches the expected commit.
  - Verify: GitHub Actions logs show the exact PR head identity before the test matrix runs.
  - Files: `.github/workflows/ci.yml`.

- [x] Decouple source-only release-evidence tests from `headoff.md`
  - Acceptance: release identity tests preserve generic non-runtime source-change semantics without using the development handoff file as a release concept.
  - Verify: focused release-evidence tests.

- [ ] Refresh generated package integrity
  - Acceptance: `.codex-plugin/package-integrity.json` exactly matches the changed shipped runtime bytes.
  - Verify: `python scripts/package_integrity.py --check-generated` PASS in CI.

- [ ] Full exact-head repository verification
  - Acceptance: Ruff, full pytest, package integrity, official Plugin validator, managed Agent lifecycle, Ubuntu 3.11/3.12, macOS 3.11, Windows 3.11, and aggregate `policy-tests` all PASS on the final remediation head.

- [ ] Fresh adversarial review and merge decision
  - Acceptance: no required review finding remains, no safety invariant is weakened, Host qualification invalidation is classified from the final three qualification digests, and the remediation can be merged without hidden release-state claims.

Real Host H1 must not resume until the final remediation candidate is repository-green and its Host qualification basis has been re-evaluated under Issue #91 rules.
