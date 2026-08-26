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

Qualification duplicate-dispatch repair: **COMPLETE and merged**. Exact-head and post-merge repository qualification both passed the required platform matrix, generated package-integrity checks, Python lint, full tests, and managed profile lifecycle verification.

Public `1.0.0` release: **BLOCKED on real Host qualification and later release closure**.

The post-clean-break real Host campaign established H0 environment evidence, H1 Reader N0 evidence, and H2 Worker N0 evidence on the pre-guard qualification procedure. H2 Investigator reached **FAIL_STOP** after the qualification control flow materialized two Investigator attempts for one single-use profile probe.

The Investigator failure is root-caused. Main created attempt 1, observed it `COMPLETED`, explicitly rejected that completed WorkUnit result, and allocated attempt 2. The second execution basis contained only the existing Issue #91 qualification preflight reference and no new task-level execution evidence. The Host did not autonomously duplicate the child, and no direct `active.json` mutation or unsupported state bypass was found.

The repair adds maintainer-only `scripts/host_qualification_guard.py`. H1/H2 single-probe allocations must bind the exact Issue #91 `RERUN` preflight on attempt 1. Spawn preparation rejects a default `initial:<execution_id>` qualification basis, retry attempts, prior retained attempts, and compacted execution history. A completed qualification probe cannot be rejected and fresh-retried merely to repair provenance or bookkeeping.

The guard remains outside the Plugin runtime package manifest. Generic product Recovery semantics, shipped Plugin bytes, `contracts/policy.json`, and `docs/v4/host-smoke.json` were not changed by this repair.

Because the human qualification procedure changed, no new real Host action is allowed until Issue #91 records the source mutation and classifies prior evidence under the current procedure. The three canonical Host qualification digests remain unchanged, so prior evidence must be evaluated selectively rather than automatically discarded. In particular, H1 Reader and H2 Worker require provenance review against the new single-probe rule before `REUSE` can be claimed.

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

### Investigator duplicate-dispatch RCA and repair

The staged real Host procedure and append-only Issue #91 ledger remain the operational authority. The campaign uses mandatory phase stops and exact-turn V2 capability checks before covered Agent-control actions.

Durable RCA:

- the original Investigator attempt was a real successful Host spawn and reached `COMPLETED`;
- Main then used the supported `reject_work_unit -> allocate_execution` path to create a second attempt;
- there was no new task-level evidence, confirmed failure cause, corrected task input, or changed external condition justifying a product-style fresh retry;
- the second basis existed only to attach qualification provenance after the first probe had consumed the one-action authorization;
- no direct state-file mutation or unsupported state bypass occurred;
- the defect was in qualification control flow and guardrails, not Host automatic materialization or generic product retry automation.

Durable repair:

- first H1/H2 qualification allocation goes through `allocate_single_probe_execution`;
- the exact Issue #91 `RERUN` preflight becomes the first ExecutionBinding `execution_basis_ref`;
- qualification spawn preparation goes through `prepare_single_probe_spawn` before canonical Orchestrate preparation;
- prior retained or compacted execution history causes fail-close rather than another profile probe;
- default initial provenance is caught before Host spawn;
- regression coverage reproduces the observed completed-attempt, reject, second-allocation path;
- package-integrity coverage proves the qualification guard does not ship in the Plugin runtime package;
- `tasks/real-host-qualification-plan.md` now makes the single-use rule explicit for H1 and H2.

## Key decisions and why

### Keep product Recovery general; narrow qualification separately

`contracts/recovery.md` intentionally permits fresh retries when the prior execution is safely settled and a concrete changed execution basis exists. Tightening that contract globally to solve one qualification bookkeeping error would break legitimate product recovery.

The repair therefore lives in maintainer-only qualification tooling. A single-use release preflight is stricter than a normal unresolved product WorkUnit. H1/H2 qualification WorkUnits get one fresh attempt per ledger authorization.

### Qualification provenance must be bound before spawn

For H1/H2, the exact Issue #91 `RERUN` preflight reference must be supplied as the first ExecutionBinding `execution_basis_ref`. A default `initial:<execution_id>` basis is insufficient for a release qualification probe.

If this binding is missing or wrong, stop before Host spawn. If a child already materialized, the authorization is consumed. Do not reject the result and create another child to repair metadata after the fact.

### Qualification guard stays outside shipped runtime

`host_qualification_guard.py` is maintainer tooling and is intentionally absent from `.codex-plugin/package-integrity.json`. This keeps release-testing mechanics out of the user-facing Plugin runtime and avoids turning Issue #91 concepts into product state.

### Fail closed on ambiguous or over-consumed authorization

A new chat, new root, elapsed time, cleaner provenance string, or desire to improve evidence formatting does not create a rerun basis. A real Host action requires its own current Issue #91 authorization. Once a single-probe authorization is consumed, another materialization requires a separately justified qualification decision.

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
8. Qualification metadata that must be authoritative later should be bound before Host action and checked by deterministic code before the native call.
9. When a qualification process defect is found, distinguish product behavior from operator/control-flow behavior before changing runtime contracts.
10. A source-only qualification-procedure change can leave shipped runtime and machine-contract digests unchanged while still requiring evidence-level procedural review.

## Open work

### Host qualification re-entry

- Record the merged qualification-procedure source mutation in Issue #91.
- Compare prior H0, H1 Reader, and H2 Worker evidence against the current single-probe procedure.
- For H1/H2 evidence, determine whether attempt 1 was already bound to the exact ledger preflight. Missing authoritative provenance blocks `REUSE`.
- Preserve historical Investigator FAIL/RCA evidence; do not reinterpret the duplicate attempt as PASS.
- Create a fresh Investigator preflight only after the current evidence-reuse classification is complete.
- Run Investigator through the new qualification guard exactly once.
- Continue Solver and Advisor only after Investigator reaches conclusive PASS and the H2 stop discipline is satisfied.
- Do not begin N1 while N0 is incomplete.

### Later release work

After N0-N8 are conclusive on a valid basis, complete Final Review, external release evidence verification, installed-product checks, human App observation, and the explicit tag/publication decision required by `docs/release-checklist.md`.

## Next safe sequence

1. Query GitHub and Issue #91 to confirm the merged qualification-procedure source is the current release line and repository CI remains green.
2. Append the source-mutation/invalidation checkpoint to Issue #91 before any new Host action.
3. Confirm `.codex-plugin/package-integrity.json`, `contracts/policy.json`, and `docs/v4/host-smoke.json` still match the prior Host qualification basis.
4. Audit H1 Reader and H2 Worker attempt-1 provenance against the new requirement that the exact Issue #91 preflight was bound before spawn.
5. Record `REUSE`, `RERUN`, or `NOT_RUN` for each affected prior gate based on evidence. Do not infer provenance from a successful Host result.
6. After the reuse classification is closed, create the new H2 Investigator preflight.
7. In the local Host root, use `allocate_single_probe_execution` with the exact preflight reference and then `prepare_single_probe_spawn`. If either guard rejects, perform zero Host spawn and stop.
8. After one Investigator materializes, treat that preflight as consumed. Record and independently accept the result before touching Solver.
9. Continue later profiles and phases only through their own Issue #91 preflights and mandatory stops.

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
