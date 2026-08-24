# Headoff

Updated: 2026-08-24.

## Purpose

This file is temporary development-session context for `subagents-dispatch` while V4.0.0 is still being developed and qualified. It exists so a new development session can recover the project background, current engineering direction, important completed work, and the next safe step without reconstructing old chats.

`headoff.md` is not Plugin runtime, a product contract, Host qualification input, release evidence, or a release gate. Live branch/SHA/CI state belongs to GitHub. Real Host evidence and `REUSE | RERUN | NOT_RUN` decisions belong to Issue #91. Machine behavior belongs to the canonical contracts listed below.

Do not edit or commit this file merely to record an individual Host phase result. Update it only when durable development context materially changes. After V4.0.0 is released, this file is intended to be removed from the repository on the post-release development line.

## Project background

`subagents-dispatch` is a Codex Plugin for bounded engineering orchestration over Codex Native Subagents. V4 Native Core leaves Agent lifecycle truth with Codex Host and keeps project-owned logic focused on responsibility, routing, acceptance, recovery, writer ownership, evidence, and release safety.

The public Plugin surface is intentionally small:

```text
Orchestrate
Doctor
```

`Orchestrate` is the engineering/orchestration surface. `Doctor` owns deterministic installed-product diagnosis and explicitly requested ownership-safe maintenance.

## Canonical truth owners

Use one owner per semantic fact:

- `contracts/policy.json`: fixed product policy and managed profile values.
- `docs/v4/architecture.json`: V4 machine architecture and runtime ownership.
- `docs/v4/host-smoke.json`: N0-N8 real Host machine contract.
- `docs/v4/technical-debt.json`: explicitly tracked V4 technical debt.
- `docs/architecture.md`: human architecture overview.
- `docs/release-checklist.md`: release gates and identity/invalidation rules.
- `tasks/real-host-qualification-plan.md`: staged human procedure for real Host qualification. It never overrides the machine contract.
- GitHub: current branch, PR, exact source SHA/tree, and CI state.
- Issue #91: append-only real Host evidence and preflight decisions.

Do not create tracked status files that duplicate live GitHub or Host truth.

## Durable product boundaries

- Main is the sole managed coordinator.
- Managed children must not create or control another Agent layer.
- Reader and Worker use Luna Max.
- Investigator uses Terra High.
- Solver and Advisor use Sol High.
- Fresh managed children use `fork_turns=none`.
- The managed-child product ceiling is four.
- WorkGraph and WorkUnit own responsibility, dependency, and acceptance truth.
- ExecutionBinding owns one concrete managed attempt/generation.
- WriterLease owns canonical-workspace managed writer coordination.
- Host `COMPLETED` produces candidate work only. Main acceptance is separate.
- `UNKNOWN` remains fail closed.
- Codex Host owns materialization, lifecycle, actual capacity, native child identity, effective permissions, effective sandbox state, and effective collaboration capability.
- Product depth-one policy is distinct from latent Host V2 recursive capability. N1 evaluates actual canonical managed-child behavior and authoritative descendant evidence.

## Release identity model

Keep two identity layers separate.

Host qualification identity is determined by:

```text
runtime_manifest_sha256
profile_contract_sha256
host_contract_sha256
```

These derive from the current runtime package manifest, fixed profile contract, and real Host campaign contract. A changed qualification digest requires invalidation analysis before prior Host evidence can be reused.

Release source identity is the exact final Git commit/tree. Repository qualification, Final Review, and the release envelope bind this exact source.

A source-only documentation change may leave Host qualification identity unchanged, but it still changes release source identity and therefore requires the relevant exact-source repository/final-review checks to be refreshed.

## Independent Deep Review and remediation

The 2026-08-24 review was performed from the actual repository contents and current code/contracts/tests. `headoff.md` was intentionally treated only as a later cross-check. The review found several concrete issues and one important process drift.

### 1. Plan-only validation

The old `plan_only_preview()` path coerced malformed input with `str()` and `list()` and did not validate the provisional dependency graph through the canonical WorkUnit/state rules. That could make malformed plan input look valid.

The remediation now:

- requires the top-level responsibilities value to be an array;
- requires each responsibility to be an object;
- requires `depends_on` to be an array at the Orchestrate input boundary;
- constructs canonical WorkUnits with `work_graph_v4.make_work_unit()`;
- validates the in-memory WorkGraph with the existing V4 state validator;
- rejects invalid intent/goal values, invalid dependency elements, unknown dependencies, and cycles;
- creates no runtime state, WriterLease, or Host action in plan-only mode.

Focused adversarial tests cover null/non-array containers, coercible dependency containers, invalid fields, unknown dependencies, cycles, and a valid dependency graph.

### 2. `headoff.md` process drift

The prior staged Host plan made every H0-H9 stop edit and commit `headoff.md`, then rerun repository checks and qualification-digest comparison before continuing. H9 also contained a special N8 revalidation loop caused solely by the mandatory handoff edit.

That workflow made a development handoff file participate indirectly in release progression and repeatedly changed source identity for administrative recording.

The remediation keeps the safety boundaries that matter:

- Issue #91 preflight before real Host actions;
- exact-turn V2 capability proof for covered Agent-control operations;
- fail-closed `UNKNOWN` handling;
- hard stop after each Host phase;
- explicit user continuation before the next phase;
- mutation invalidation and repository requalification;
- N5/N6 writer settlement boundary;
- N8 effective read-only evidence;
- final source freeze, Final Review, release evidence, installed-product checks, and human App observation.

Mandatory per-phase `headoff.md` commits and the headoff-driven N8 revalidation loop were removed. Issue #91 remains the operational evidence ledger.

### 3. Exact-head CI evidence

Pull-request CI previously ran from GitHub's synthetic merge commit while project language described the result as exact-head qualification. Tree equivalence can be useful, but it does not prove that the checked-out Git commit is the PR head.

CI now explicitly checks out `${{ github.event.pull_request.head.sha || github.sha }}` and asserts `git rev-parse HEAD` equals that expected SHA before tests run. This behavior has been exercised on Ubuntu, macOS, and Windows runners.

### 4. Stale task/spec truth

`tasks/SPEC-n1-managed-depth.md` still pointed to deleted `docs/v4/current-state.md`, and the old task checklist had been overtaken by later implementation. The current task/spec surfaces now point to canonical contracts, Issue #91, and the staged Host procedure without duplicating live release state.

### 5. Release-evidence test coupling

Source-only release-evidence tests previously used `headoff.md` as the representative source-only mutation, which unnecessarily embedded the development handoff file into release semantics. Those tests now use generic non-runtime documentation/source changes while preserving the same release-identity and Host-qualification behavior.

## Verification status for this remediation

The implementation was developed on `fix/v4-deep-review-remediation` in PR #114 against `v4/rc5-native-core`.

Before this final development-handoff update, exact-head PR CI on commit `a68420dd14768b6ba850af29e039c2369597581a` passed:

```text
Ubuntu / Python 3.11    PASS
Ubuntu / Python 3.12    PASS
macOS / Python 3.11     PASS
Windows / Python 3.11   PASS
aggregate policy-tests  PASS
```

That run also passed generated package-integrity verification, Ruff, full pytest, the pinned official OpenAI Plugin validator where applicable, and the managed Agent install/check/Doctor/uninstall lifecycle.

This handoff update changes source identity only. Final merge readiness must use the live CI result for the final PR head after this update. Do not treat the SHA above as the final candidate SHA.

## Host qualification impact

This remediation changes shipped runtime code in `scripts/orchestrate_v4.py`, and `.codex-plugin/package-integrity.json` was regenerated accordingly. Therefore the runtime-manifest component of Host qualification identity changed relative to the earlier H0 campaign basis.

`contracts/policy.json` and `docs/v4/host-smoke.json` were not changed by this remediation, but unchanged profile/Host-contract inputs do not cancel the runtime-manifest change.

Do not carry the earlier H0 exact-source/package basis forward as current qualification without a fresh Issue #91 invalidation/preflight decision. After the remediation is merged and post-merge repository CI is green:

1. read the latest Issue #91 ledger state;
2. compare the final three Host qualification digests;
3. record the required `REUSE | RERUN | NOT_RUN` classification;
4. synchronize the target local checkout to the final release head;
5. verify package integrity and Doctor against the installed/local basis;
6. refresh the affected H0/source-environment binding as required by the invalidation decision;
7. only then prepare H1 Reader canary preflight.

H1 still requires exact-turn Native Subagent V2 capability proof before any Agent-control action and explicit user authorization before the phase starts.

## Real Host staged protocol

The staged phase structure remains:

```text
H0   exact source, installed basis, fresh Host environment
H1   N0 Reader canary
H2   remaining N0 fixed profiles
H3   N1 managed delegation depth across all five profiles
H4   N2 native task-address and Host-thread identity binding
H5   N3 admission rejection and materialization safety
H6   N4 same-child steering, correction, and continuation
H7   N5/N6 interrupt, settlement, and writer takeover
H8   N7 rollout reconciliation and privacy
H9   N8 Advisor review and effective sandbox truth
H10  release closure and explicit release decision stop
```

Every phase still has a hard stop. Canonical phase evidence is written to Issue #91. A phase does not auto-continue, and a new chat/session does not justify rerunning Host work by itself.

`headoff.md` may be updated later when the durable project direction materially changes. Such an update is normal development documentation and has no special qualification privilege or phase-gate status.

## Development workflow

For repository changes:

1. Read this development context, then verify the relevant canonical contracts and live GitHub/Issue #91 state.
2. Check the request for wrong assumptions, missing requirements, and scope drift.
3. Plan non-trivial work before implementation.
4. Create a short-lived branch from the exact intended base.
5. Keep behavior changes focused and reuse canonical helpers rather than creating parallel validators or truth stores.
6. Preserve UNKNOWN handling, WriterLease settlement, Host identity/materialization evidence, managed-depth checks, and strict read-only evidence.
7. Run focused tests first, then the complete required repository matrix.
8. Review the final diff adversarially for correctness, simplicity, architecture, security, and performance.
9. Merge only when the reviewed exact head is green.
10. Verify post-merge exact-head CI before treating repository remediation as closed.
11. Record real Host evidence and invalidation decisions in Issue #91.
12. Update this file only when durable development context actually changes.

Never mark work complete before verification.

## Next development direction

Finish the Deep Review remediation merge first. After the final PR head and post-merge release head both pass repository qualification, rebind the Host qualification basis in Issue #91 because the runtime manifest changed.

Do not start H1 directly from the old H0 checkpoint. Resume real Host qualification only after the new exact source/package basis is synchronized, health checks pass, the Issue #91 preflight allows the next action, and the user explicitly authorizes continuation.

No new product feature work is planned in this handoff. If a real Host probe later exposes a concrete product defect, fix that defect on a separate short-lived branch and repeat the required invalidation/verification process.
