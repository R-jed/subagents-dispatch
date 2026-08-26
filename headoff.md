# Headoff

Updated: 2026-08-26.

## Purpose

This is the development-session handoff record for `subagents-dispatch`. It preserves durable project direction, major completed work, important decisions, lessons, current blockers, and the next safe continuation point.

It is not Plugin runtime, a product contract, Host qualification input, release evidence, or a release gate. Live branch, PR, commit/tree, CI, and review state belong in GitHub. Real Host actions, evidence, phase verdicts, and `REUSE | RERUN | NOT_RUN` decisions belong in Issue #91. Machine behavior belongs in canonical contracts.

If this file conflicts with GitHub, Issue #91, or a canonical contract, resolve live truth from the canonical owner first and then repair this record.

## Project in one minute

`subagents-dispatch` is a bounded orchestration layer over Codex Native Subagents. Main owns dispatch judgment, integration, irreversible side effects, and final acceptance. Managed children use fixed profiles, fresh context, bounded authority, WorkGraph/WorkUnit responsibility ownership, ExecutionBinding attempt identity, and WriterLease coordination.

The first public Plugin line is `1.0.0`. Native Core V4 is the internal architecture generation and is not the public release number.

The project intentionally fails closed on unsupported state and ambiguous Host truth. Pre-1.0 compatibility surfaces, TeamPlan, migration wrappers, and stale-state fallback paths are not part of the first public contract.

## Current status

Repository clean-break closure: **COMPLETE**.

Public `1.0.0` release: **BLOCKED on real Host qualification and later release closure**.

The post-clean-break real Host campaign established valid H0 environment binding, H1 Reader N0 evidence, and H2 Worker N0 evidence on the then-current qualification basis. H2 Investigator then reached **FAIL_STOP** because the qualification control flow materialized two Investigator attempts for one single-use profile probe.

The Investigator failure has been root-caused. The Host did not duplicate the child automatically. Main created attempt 1, observed it `COMPLETED`, explicitly rejected that completed WorkUnit result, and allocated attempt 2. The second execution basis contained only the existing Issue #91 qualification preflight reference and no new task-level execution evidence. The second dispatch therefore repaired qualification provenance by repeating the Host action after the one-probe authorization had already been consumed.

A focused development fix is now in progress: maintainer-only `scripts/host_qualification_guard.py` requires H1/H2 single-probe allocations to bind the exact Issue #91 `RERUN` preflight on attempt 1, refuses default `initial:<execution_id>` qualification provenance at spawn preparation, and refuses any fresh qualification allocation when that WorkUnit already has retained or compacted execution history. The guard is intentionally excluded from the Plugin runtime package manifest, so generic product Recovery semantics remain unchanged.

`tasks/real-host-qualification-plan.md` now requires the guard for H1/H2 and explicitly forbids rejecting a completed qualification probe and fresh-retrying merely to repair provenance or bookkeeping.

Because repository source changed to repair the qualification process, the Host campaign must remain stopped until the change is merged, exact-head repository qualification is green, and Issue #91 classifies which prior Host evidence can be reused on the new release-source basis. Do not assume that every prior Host result is invalid: compare the canonical Host qualification digests and environment prerequisites first.

## Recently completed milestones

### First-public 1.0.0 clean break

The first-public clean break removed retired TeamPlan and pre-1 migration/compatibility surfaces, aligned the public version to Plugin `1.0.0`, preserved Native Core V4 only as an internal architecture identifier, strengthened package-integrity and regression coverage, and kept unresolved orchestration Host uncertainty visible as `UNKNOWN`.

The durable architecture remains:

- WorkGraph and WorkUnit own responsibility, dependencies, readiness, and acceptance.
- ExecutionBinding owns one concrete managed attempt/generation.
- WriterLease owns canonical-workspace managed writer coordination.
- Main is the sole managed coordinator and final acceptance owner.
- Managed children do not create or control another managed Agent layer.
- Reader and Worker use Luna Max; Investigator uses Terra High; Solver and Advisor use Sol High.
- Fresh managed children use `fork_turns=none`.
- Product managed-child ceiling is four.
- Host `COMPLETED` means candidate lifecycle completion only.
- Codex Host owns actual materialization, lifecycle, capacity, child identity, effective permission, effective sandbox, and effective collaboration capability.

### Real Host qualification through the Investigator RCA

The staged real Host procedure and append-only Issue #91 ledger remain the operational authority. The campaign uses mandatory phase stops and exact-turn V2 capability checks before covered Agent-control actions.

Durable result of the Investigator incident:

- the original Investigator attempt was a real successful Host spawn and reached `COMPLETED`;
- Main then used the supported `reject_work_unit -> allocate_execution` path to create a second attempt;
- there was no new task-level evidence, confirmed failure cause, corrected task input, or changed external condition justifying a product-style fresh retry;
- the second basis existed only to attach qualification provenance after the first probe had already consumed the one-action authorization;
- no direct `active.json` mutation or unsupported state bypass was found;
- the defect was in qualification control flow and guardrails, not in Host automatic materialization or generic product retry automation.

## Key decisions and why

### Keep product Recovery general; narrow qualification separately

`contracts/recovery.md` intentionally permits fresh retries when the prior execution is safely settled and a concrete changed execution basis exists. Tightening that contract globally to solve one qualification bookkeeping error would break legitimate product recovery.

The fix therefore lives in maintainer-only qualification tooling. A single-use release preflight is a stricter concept than a normal unresolved product WorkUnit. H1/H2 qualification WorkUnits get exactly one fresh attempt per ledger authorization.

### Qualification provenance must be bound before spawn

For H1/H2, the exact Issue #91 `RERUN` preflight reference must be supplied as the first ExecutionBinding `execution_basis_ref`. A default `initial:<execution_id>` basis is insufficient for a release qualification probe.

If this binding is missing or wrong, stop before Host spawn. If a child already materialized, the authorization is consumed. Do not reject the result and create another child to repair metadata after the fact.

### Qualification guard stays outside shipped runtime

`host_qualification_guard.py` is maintainer tooling and is intentionally absent from `.codex-plugin/package-integrity.json`. This keeps release-testing mechanics out of the user-facing Plugin runtime and avoids turning Issue #91 concepts into product state.

### Fail closed on ambiguous or over-consumed authorization

A new chat, new root, elapsed time, cleaner provenance string, or desire to improve evidence formatting does not create a rerun basis. A real Host action requires its own current Issue #91 authorization. Once a single-probe authorization is consumed, another materialization requires a separately justified preflight and, where applicable, a new qualification WorkUnit/campaign basis rather than a silent retry.

## Canonical truth owners

Read live sources before acting:

- `.codex-plugin/plugin.json`: public Plugin version.
- `.codex-plugin/package-integrity.json`: shipped runtime byte manifest.
- `contracts/policy.json`: fixed product policy and managed profile values.
- `contracts/state.md`: current state schema and clean-break boundary.
- `contracts/recovery.md`: legitimate product retry and recovery semantics.
- `docs/v4/architecture.json`: Native Core runtime ownership.
- `docs/v4/host-smoke.json`: N0-N8 machine Host contract.
- `docs/release-checklist.md`: release gates and invalidation rules.
- `tasks/real-host-qualification-plan.md`: staged human Host qualification procedure.
- `scripts/host_qualification_guard.py`: maintainer-only H1/H2 single-probe enforcement.
- GitHub: live source, PR, CI, review, and merge state.
- Issue #91: append-only Host action/preflight/evidence history and reuse decisions.

Do not create another tracked status ledger that duplicates GitHub or Issue #91.

## Lessons already learned

1. A Host action that succeeds is not automatically sufficient evidence that the intended semantic effect occurred.
2. `UNKNOWN` must remain visible and must not authorize conflicting replacement, writer transfer, or acceptance.
3. New chats or sessions are not rerun reasons. Reuse and rerun follow evidence and invalidation rules.
4. Host configuration expresses intent; actual Host observations decide materialization, route, lifecycle, sandbox, permissions, and descendant behavior.
5. Shipped files covered by package integrity are package identity. Maintainer-only qualification tooling should stay outside that manifest unless it truly belongs in the product.
6. `execution_basis_ref` is semantic recovery evidence. A different string is insufficient when the underlying task-level basis did not change.
7. A single-use qualification preflight must be consumed by at most one materialized profile probe. Provenance repair after materialization is not a valid fresh-retry basis.
8. Qualification metadata that must be authoritative later should be bound before Host action, then checked by deterministic code before the native call.
9. When a qualification process defect is found, distinguish product behavior from operator/control-flow behavior before changing runtime contracts.
10. Source changes during Host qualification require an explicit invalidation/reuse classification before the campaign resumes, even when shipped runtime digests remain unchanged.

## Open work

### Immediate repository work

- Finish review and exact-head CI for the qualification single-probe guard change.
- Confirm `scripts/host_qualification_guard.py` remains excluded from the generated Plugin package manifest.
- Review the final diff for accidental changes to generic Recovery, Orchestrate runtime behavior, package identity, and Host machine contract.

### Host qualification after the fix lands

- Record the source mutation and new qualification-process basis in Issue #91.
- Compare the current package-integrity, policy, and host-smoke qualification digests with the prior accepted H0/H1/Worker evidence.
- Reuse only evidence that survives the canonical invalidation rules.
- Perform a fresh Investigator preflight under the corrected single-probe procedure.
- Re-run Investigator only after that preflight explicitly authorizes the action.
- Continue Solver and Advisor only after Investigator reaches conclusive PASS and the H2 stop discipline is satisfied.
- Do not begin N1 while N0 is incomplete.

### Later release work

After N0-N8 are conclusive on a valid basis, complete Final Review, external release evidence verification, installed-product checks, human App observation, and the explicit tag/publication decision required by `docs/release-checklist.md`.

## Next safe sequence

1. Query GitHub for the live fix PR/head and exact CI state.
2. Require focused qualification-guard tests, the complete repository matrix, package-integrity generation check, and relevant lifecycle tests to pass on the exact final head.
3. Review the final diff against the base release branch and confirm the fix does not modify generic product Recovery or shipped Plugin bytes.
4. Merge only after final-head CI and review are green.
5. After merge, stop the Host campaign and record the repository-source mutation/invalidation classification in Issue #91 before any new Host action.
6. Compare the three Host qualification digests and environment prerequisites. Do not repeat H0/H1/Worker solely because the source SHA changed if canonical reuse rules allow them to survive.
7. Create the next Investigator preflight on the corrected procedure.
8. In the local Host root, use `allocate_single_probe_execution` with the exact preflight reference and `prepare_single_probe_spawn`; if either guard rejects, perform zero Host spawn and stop.
9. After one Investigator materializes, treat that preflight as consumed. Record and independently accept the result before touching Solver.
10. Continue later phases only through their own Issue #91 preflights and mandatory stops.

## Verification discipline

For repository changes:

1. read the smallest relevant canonical contracts and current source;
2. state concrete acceptance conditions before editing;
3. keep behavior changes focused and avoid compatibility or fallback branches;
4. add regression coverage that reproduces the actual failure mode;
5. run focused tests and the complete exact-head repository matrix;
6. compare base versus final head and inspect the complete diff;
7. verify generated/package integrity and confirm intended shipped-file scope;
8. do not mark work complete while any required check is red, skipped, stale, or bound to an older head;
9. classify Host qualification invalidation before resuming real Host actions.

Before ending a development session, verify that a new session can read this file, query the linked live sources, understand the Investigator duplicate-dispatch RCA, know why the guard is maintainer-only, and identify the exact next safe continuation without repeating already-conclusive work.
