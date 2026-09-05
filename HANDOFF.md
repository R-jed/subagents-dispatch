# HANDOFF

Updated: 2026-09-05

This is the current development handoff for `subagents-dispatch`. It is continuity documentation only; it is not Plugin runtime, release evidence, or a release gate.

## 1. Current task

Finish the GPT-6-era refactor for the first public `1.0.0` architecture of `subagents-dispatch`, while keeping the product small, deterministic, and fail-closed.

The intended product surface remains exactly:

```text
Orchestrate
Doctor
```

The current managed team is:

```text
Programmer             gpt-5.6-luna / max
Product Manager        gpt-5.6-sol / medium | high
Department Director    gpt-6-astra / high
```

Main remains the orchestration owner: user intent, decomposition, semantic classification, integration, WorkUnit acceptance, irreversible external effects, and final response. Managed model/effort routes do not inherit from Main.

The current source task is no longer “design the refactor”; the source implementation is stabilized. The remaining work is release-readiness review and release gating, without reintroducing the retired project-owned Host campaign.

## 2. Exact current repository state

Canonical local repository:

```text
/Users/qunqing/2026-Project-Agent/subagents-dispatch
```

Do not create sibling `subagents-dispatch-*` worktree/project directories. This is the only local project folder the user wants for this project.

Current branch and HEAD:

```text
branch: feat/gpt6-routing
HEAD:   6c283f733dfff0090474ed97e4ac79de9e4688df
```

At the time this handoff was written, the worktree was clean before adding this `HANDOFF.md` file.

Remote release-line refs still point at:

```text
origin/main                dacc8253383c345fbb069b27e094facd28f112ed
origin/v4/rc5-native-core dacc8253383c345fbb069b27e094facd28f112ed
```

`feat/gpt6-routing` is seven commits ahead of `origin/main`. Nothing from this refactor has been pushed, tagged, or released.

Current relevant local commit chain:

```text
27a86db  feat: qualify Host evidence per probe
c6c663e  fix: anchor carried Host evidence externally
499d743  refactor: establish three-role routing core
91d577e  feat: guard parallel semantic reads
3801479  refactor: simplify calibration evidence plane
988c50e  fix: make plugin updates exact and transactional
6c283f7  refactor: adopt mature Host reference conformance
```

Do not rewrite or drop the earlier local commits merely because the latest architecture no longer uses their old N0-N7 release machinery; they are part of the local history and explain the evolution of the safety model.

## 3. What has been completed

### A. Three-role routing architecture

The former Reader / Worker / Investigator / Solver / Advisor production model has been replaced by three semantic roles:

- `programmer` / `subagents_dispatch_programmer`: Luna Max; ordinary bounded investigation or implementation according to WorkUnit authority.
- `product_manager` / `subagents_dispatch_product_manager`: Sol Medium or Sol High; routing check, technical judgment, judgment-coupled implementation, or Standard Review according to explicit responsibility and trigger facts.
- `department_director` / `subagents_dispatch_department_director`: Astra High; fresh, read-only, highest-consequence acceptance review only after Candidate Ready.

`contracts/policy.json` is the production route owner. The three persistent Agent TOMLs carry behavior/configuration only; they do not pin model or reasoning effort. Every managed spawn sends the exact policy-backed model and effort explicitly.

Product Manager effort is a strict two-class policy:

```text
medium  local/reversible technical judgment
high    material architecture/contract/authority/persistence/security/data/concurrency/migration judgment
```

File count, task size, retry count, or Main model do not select High.

### B. Runtime/state clean break

Native Core state moved to the three-role schema. ExecutionBinding now separates:

```text
role_id
agent_type
model
reasoning_effort
granted mutation authority
```

Old five-role/profile-based persisted state is unsupported rather than migrated. Host lifecycle completion remains candidate-only; Main acceptance unlocks dependencies. `UNKNOWN` continues to fail closed.

WorkGraph, WorkUnit, ExecutionBinding, WriterLease, current-generation lifecycle fencing, same-child controls, and single canonical-workspace writer ownership remain intact.

### C. Three production profiles and installer/Doctor

The package now has three managed behavior/configuration profiles instead of five route-pinning profiles. Installer/Doctor ownership, no-clobber, drift detection, safe provisioning, rollback, and `RESTART_REQUIRED` behavior were preserved.

Department Director requests read-only sandbox intent. Effective Host permission is still runtime truth and is not inferred from the TOML.

### D. Parallel semantic-read containment

Parallel semantic-read responsibilities remain allowed. When Host permission is broader than semantic read-only authority, a before/after artifact-immutability guard is mandatory and there must be no active canonical WriterLease.

If the workspace changes during the protected batch:

- invalidate all workspace-dependent evidence from that batch;
- do not guess which actor caused the change;
- do not auto-rollback user files;
- pause conflicting managed mutation until Main re-establishes current truth.

This is implemented in Slice 4 (`91d577e`).

### E. Calibration/evidence simplification

Temporary campaign-specific Agent TOML materialization was removed. Calibration now varies model/effort through explicit evaluator-only spawn routes while retaining campaign/run provenance, requested/accepted/observed separation, result/oracle provenance, and measurement provenance.

The old staging/locking/nonce/materialized-agent identity/cleanup/recovery obligations that existed only to safely create temporary challenger profiles were deleted.

This is Slice 5 (`3801479`).

### F. Updater correctness

The updater now treats exact installed source/package identity as authoritative rather than semantic version alone.

Fixed release blockers:

- same-semver but different exact bytes/source no longer reports `already current`;
- explicit update is transactional;
- post-switch package/profile/Doctor failure restores and verifies the exact previous Plugin plus Plugin-owned profile state;
- unrelated user Agents/configuration remain outside rollback ownership.

This is Slice 6 (`988c50e`).

### G. Host release strategy was deliberately simplified

The user explicitly changed the release strategy during implementation: do **not** run a project-owned real-Host N0-N7 campaign for the first public `1.0.0`.

Instead, release Host assumptions are pinned to mature Native Codex integrations:

```text
sol-advisor
https://github.com/DannyMac180/sol-advisor
37b75cad535abdd46531f0227483a8842d045ab8

astra-advisor
https://github.com/DannyMac180/astra-advisor
c72d3280551f118eba51a5884e3971a0c0058aa6
```

`docs/v4/host-reference.json` is now the machine release owner for the narrow Host assumptions reused from those projects. It records exact source paths supporting the assumptions.

The retired project-specific machinery was removed:

- `docs/v4/host-smoke.json`;
- N0-N7 staged qualification procedure;
- qualification single-probe guard;
- Host rollout qualification collector/root inspector;
- per-probe carry-forward/reuse release machinery;
- campaign-only tests tied to those mechanisms.

This deletion was intentional and large. Slice 7 was approximately `997 additions / 6833 deletions`.

This does **not** weaken ordinary runtime Host truth. Current callable Host schema and current Host observations remain authoritative for a concrete delegation. Required model/effort/control/realized-route facts that are missing, conflicting, unavailable, or unobservable still fail the affected delegation/review closed.

Depth one is a product semantic rule, not a claim that the Host physically removes collaboration tools from every child. If a user explicitly requires Host-hard descendant isolation, obtain direct current-Host evidence for that stronger claim.

### H. Release verifier simplification

`scripts/release_evidence_v4.py` was reduced from the old Host campaign/carry-forward verifier to an exact-source release verifier. It now binds:

```text
clean exact Git commit/tree
package integrity
pinned host-reference digest
current review_artifact_id
Main-owned pre-review request
fresh Department Director / Astra High review result
```

The verifier rejects dirty release source and rejects the retired Host-campaign envelope shape.

### I. Verification already completed

After the architecture stabilized:

```text
release/reference focused tests   PASS
affected Slice 7 tests            122/122 PASS
full pytest                       428/428 PASS
Ruff                              PASS
package integrity                 PASS
git diff --check                  PASS
managed profile lifecycle/Doctor PASS
official pinned OpenAI validator  PASS
```

The full-suite count dropped from 510 to 428 because campaign-only Host qualification tests were deleted with the retired campaign machinery. Runtime Host safety tests remain.

## 4. What is blocked or still unresolved

There is no known source-code correctness blocker on `6c283f7` from the completed local verification.

The remaining blockers are release/process gates, not an unfinished implementation feature:

1. **No final adversarial exact-head release review has been recorded after all current source is frozen.** The formal release Final Review must be a fresh `subagents_dispatch_department_director / gpt-6-astra / high`, `fork_turns=none`, exact-candidate-bound review.
2. **The canonical GitHub Actions matrix has not been established here for the final remote release source.** The checklist requires Ubuntu 3.11/3.12, macOS 3.11, and Windows 3.11 on the exact frozen source.
3. **The feature branch has not been merged/pushed into the release line.** Local HEAD is seven commits ahead of `origin/main`; publication actions require explicit user authorization.
4. **Installed-product/human App release smoke remains a release gate** for the exact shipped package after the release source is chosen.
5. **No `v1.0.0` tag or release exists.** Do not create either without explicit user authorization.

Important: Doctor may report Host integration as `UNKNOWN` when no current Host capability snapshot was supplied. Under the revised release strategy, that alone is not the old N0-N7 release blocker. It is still meaningful at runtime when a concrete delegation requires a fact the Host has not established.

## 5. Next-step plan

Proceed in this order unless the user changes release policy:

1. Re-read this `HANDOFF.md`, `docs/release-checklist.md`, `contracts/final-review.md`, `docs/v4/host-reference.json`, and the latest Git diff/history before changing code.
2. Perform a fresh adversarial review of the exact current candidate across correctness, simplicity/over-engineering, architecture/authority, security, and performance. Do not modify code merely to satisfy stale historical N0-N7 assumptions.
3. If review finds a real issue, fix the smallest scope, start with the smallest behavior-sensitive tests, then expand only for failure/cross-module/architecture effects. Any source change invalidates the prior exact-source review candidate.
4. Once source is accepted, choose/freeze the exact release commit. Do not confuse local `feat/gpt6-routing` HEAD with a published release source until the user authorizes the relevant Git operations.
5. Run/confirm the canonical final repository matrix on that exact frozen source.
6. Bind the Main-owned pre-review request and run one fresh Department Director / Astra High release Final Review under `contracts/final-review.md`.
7. Verify the release envelope with `scripts/release_evidence_v4.py`.
8. Verify the exact installed package in an isolated Codex home: package, three profiles, Doctor, update/check surface, two public Skills.
9. Perform the human two-Skill App observation required by the release checklist.
10. Only with explicit user authorization: merge/push as requested, create `v1.0.0`, verify Marketplace resolves the exact tagged source, and publish release notes.

## 6. Pitfalls already encountered

### Pitfall 1 — Rebuilding a Host qualification control plane the mature references already solved

The project accumulated a large N0-N7 campaign/carry-forward system that duplicated assumptions already exercised by `sol-advisor` and `astra-advisor`. The user explicitly rejected continuing that path.

Rule now: use the pinned mature projects as release-design references; keep current Host evidence only where the concrete runtime operation or a hard-isolation claim actually needs it. Do not recreate N0-N7 under a new name.

### Pitfall 2 — Deleting release-only Host machinery can accidentally delete real runtime safety

The Host campaign and ordinary runtime Host authority are different concerns. During Slice 7, campaign-only tests/tools were deleted while runtime tests for capacity, identity, lifecycle, permissions, requested/accepted/observed route truth, same-child steering, WriterLease, and `UNKNOWN` were deliberately retained.

Rule now: before deleting any remaining Host-related code, identify whether it is release evidence machinery or an ordinary runtime safety owner.

### Pitfall 3 — A release verifier can dirty the candidate it is verifying

The first simplified `release_evidence_v4.py` implementation imported candidate Python modules in a way that created `__pycache__`, causing its own clean-source gate to fail.

Fix: release verification must remain read-only with respect to the candidate; Python module loading used by verification must not create bytecode in the candidate tree.

### Pitfall 4 — Guessing an internal helper API

The first simplified verifier called a nonexistent `package_integrity.check_integrity()`. The actual supported function is `verify_package()` (plus `check_generated()`).

Rule now: inspect the current local API before wiring a caller; do not infer helper names from intent.

### Pitfall 5 — Rewriting a checklist can silently drop unrelated safety requirements

When the release checklist was simplified, two valid old requirements were accidentally removed and caught by tests:

- uninstall/removal may change only the Plugin/Marketplace registration semantics in `config.toml`; unrelated config/state must remain unchanged;
- resolving a Marketplace tag to the expected commit does not prove platform-enforced tag immutability.

Rule now: simplify obsolete Host release machinery surgically; preserve independent release safety invariants.

### Pitfall 6 — Test-count reduction can look like lost coverage

The suite went from 510 to 428 because the retired Host campaign implementation and its campaign-only tests were deleted. This is expected, not evidence of a regression by itself.

Rule now: evaluate what obligations remain covered, not raw test count. Runtime Host safety still has dedicated tests.

### Pitfall 7 — Semantic version is not installed-product identity

Updater logic previously treated equal semver as “already current” even when bytes/source differed.

Rule now: exact installed package/source identity is authoritative; same-semver drift is still drift.

### Pitfall 8 — Update rollback must cover the Plugin-owned compatibility unit

Switching package source and then failing verification could leave a mixed new/old installation.

Rule now: package plus Plugin-owned managed profiles are one transaction. On post-switch failure, restore and verify the exact previous state; do not touch unrelated user Agents/configuration.

### Pitfall 9 — Broader Host permission does not expand semantic authority

Programmer/Product Manager semantic-read work may run under a Host that technically permits writes. That does not make writes legitimate.

Rule now: WorkUnit/Responsibility authority is the semantic ceiling. Parallel read/read under broader permission needs artifact-immutability guarding; any drift invalidates the whole workspace-dependent batch.

### Pitfall 10 — Model/effort truth must have one owner

Earlier designs duplicated model/effort across profile files, policy, parent inheritance, and calibration materialization.

Rule now: production policy owns the legal route; managed spawn sends it explicitly; profile TOMLs do not pin it; requested/accepted/observed values remain separate.

### Pitfall 11 — Historical design text can be stale even when useful

`tasks/gpt6-refactor-design.md` contains the complete grilling history and later implementation amendments, but its top-level status text still describes the earlier grilling phase. Do not treat that header as current repository status. Use Git HEAD, the `Implementation progress` section near the end of that file, this `HANDOFF.md`, and current machine contracts as current truth.

## 7. Files to read first when resuming

Use this order:

```text
HANDOFF.md
docs/release-checklist.md
contracts/policy.json
contracts/routing.md
contracts/final-review.md
docs/v4/architecture.json
docs/v4/host-reference.json
docs/native-subagent-runtime.md
tasks/gpt6-refactor-design.md        # history + implementation record, not current status authority
git log / git diff / git status      # exact source truth
```

For Host behavior reference, use the exact pinned commits in `docs/v4/host-reference.json`, not a floating `main` branch.

## 8. Non-negotiable user/process constraints

- Prefer the smallest test range that proves the changed behavior. Expand only on failure, cross-module impact, architecture changes, or final integration gates.
- Review current source/callers/contracts before editing; do not patch blindly.
- Do not add speculative abstractions, a second scheduler/runtime, hidden occupancy state, or another Host qualification control plane.
- Keep one semantic truth owner; do not duplicate model/effort, acceptance, lifecycle, or writer authority.
- Preserve `UNKNOWN` fail-closed handling.
- Keep the local project under `/Users/qunqing/2026-Project-Agent/subagents-dispatch`; do not proliferate sibling project/worktree folders.
- Do not push, tag, publish, or create a release without explicit user authorization.

## 9. Current stopping point

Source implementation through Slice 7 is locally verified and committed at `6c283f7`. There is no known source-code blocker from the completed local gates. The next meaningful work is exact-head adversarial release review and, when authorized, release-line/CI/final-review/installed-product gating.
