# N1 Managed Delegation Depth Tasks

- [x] Specify the corrected product boundary
  - Acceptance: Main is the sole managed coordinator; managed children cannot create or control another Agent layer; latent Host V2 recursion is documented separately.
  - Verify: `tasks/SPEC-n1-managed-depth.md` matches current product contracts and official Codex source.
  - Files: `tasks/SPEC-n1-managed-depth.md`, `tasks/plan.md`.

- [x] Correct Host readiness semantics
  - Acceptance: `managed_child_containment` is optional diagnostic compatibility data and does not decide ordinary `execution_ready`; malformed supplied values still fail closed.
  - Verify: focused `tests/test_host_capabilities.py` plus downstream scheduler/Doctor tests.
  - Files: `scripts/host_capabilities.py`, focused tests.

- [x] Correct the N1 machine contract
  - Acceptance: N1 evaluates canonical managed profiles, their delegation boundary, adversarial untrusted-input behavior, child-issued nested Agent actions, and descendant identities/spawn edges; a generic forced V2 grandchild probe is platform evidence only.
  - Verify: `tests/test_host_contract_v4.py` assertions against `docs/v4/host-smoke.json` and architecture contract.
  - Files: `docs/v4/host-smoke.json`, `docs/v4/architecture.json`, tests.

- [x] Align current-authority documentation
  - Acceptance: architecture, release checklist, AI reference and current-state checkpoint consistently distinguish product depth policy from Host-hard isolation; N8 read-only Host evidence remains unchanged.
  - Verify: repository contract tests and direct adversarial text review.
  - Files: `docs/architecture.md`, `docs/release-checklist.md`, `README_AI.md`, `docs/v4/current-state.md`, relevant V4 evidence docs.

- [x] Refresh shipped package integrity
  - Acceptance: `.codex-plugin/package-integrity.json` contains the exact new SHA-256 for changed shipped runtime files and no unrelated payload drift.
  - Verify: generated package-integrity check in CI.

- [ ] Final exact-head candidate verification
  - Acceptance: Ruff, full pytest, managed Agent lifecycle, package integrity, official Plugin validator where applicable, all four platform jobs and aggregate policy-tests pass after the final repository-content change.
  - Verify: GitHub Actions workflow bound to the final PR head.

- [ ] Fresh adversarial review and merge decision
  - Acceptance: no current contract authorizes managed nested delegation; no stale Host-hard N1 wording remains in current-authority surfaces; no unrelated safety invariant is weakened.
  - Verify: compare final PR against `v4/rc5-native-core`, inspect exact-head CI evidence, then merge only if review is clean.

Real Host revised N1 is a later release gate, not a repository-side implementation task. It remains NOT_RUN until the corrected contract is merged, the exact installed candidate is rebound, and the canonical managed-profile campaign executes.
