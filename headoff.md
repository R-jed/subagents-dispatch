# Headoff

Updated: 2026-08-27.

## Purpose

This is the durable development-session handoff for `subagents-dispatch`. Keep project direction, major completed work, current blockers, lessons, and the next safe continuation here.

It is not Plugin runtime, a product contract, Host qualification input, release evidence, or a release gate. Live source/CI truth belongs in GitHub. Real Host evidence belongs in the external evidence journal. Machine behavior belongs in canonical contracts.

## Project summary

`subagents-dispatch` is a bounded orchestration layer over Codex Native Subagents. Main owns dispatch judgment, integration, irreversible side effects, and final acceptance.

First public Plugin version: `1.0.0`.

Public Skills: `Orchestrate`, `Doctor`.

Fixed managed profiles:

- Reader: Luna Max, read-only.
- Worker: Luna Max, bounded source write.
- Investigator: Terra High, read-only.
- Solver: Sol High, bounded source write.
- Advisor: Sol High, read-only.

Fresh managed children use `fork_turns=none`. Managed children are leaf Agents. Product managed-child ceiling is four.

Core ownership:

- WorkGraph / WorkUnit own responsibility, dependencies, readiness, and acceptance.
- ExecutionBinding owns one concrete managed attempt/generation.
- WriterLease owns canonical-workspace managed writer coordination.
- Main is the sole managed coordinator and final acceptance owner.
- Host `COMPLETED` means candidate lifecycle completion only.
- Codex Host owns actual materialization, lifecycle, capacity, child identity, effective permissions/sandbox, and collaboration capability.
- Ambiguous Host truth fails closed.

## Current status

Repository clean-break closure: **COMPLETE**.

Investigator duplicate-dispatch RCA and guard repair: **COMPLETE**.

Real Host qualification procedure: **UPDATED AFTER H4 EVIDENCE-CAPTURE RCA**. Covered Agent-control probes must preserve a privacy-safe exact-turn capability/schema snapshot before the control call so later review does not depend on Host rollout retaining callable schema definitions.

Historical build-7119 campaign under runtime manifest `3e6d43aec07e493b937195ebbd05489f43dbbd36eea85671980f69fb357a0d8c`:

- H0 environment binding: `PASS_STOP`.
- H1 Reader: `PASS_STOP`, consumed.
- H2 / N0: `PASS_STOP`; durable closure Issue #91 comment `5422820011`.
- H3 / N1 managed delegation depth: `PASS_STOP`; durable result `5425708582`.
- H4 / N2 corrected rerun: `PASS_STOP`; durable result `5426789425`. The original H4 WorkUnit remains consumed historical `UNKNOWN`.
- H5 / N3 admission rejection materialization safety RERUN2: `PASS_STOP`; durable result `5435381320`.
- H6 / N4: `FAIL_STOP`; durable result `5435837898`. Running Steer succeeded on the original child, then product interrupt preparation rejected the authoritative canonical Host task address.

H6 root cause repair: **MERGED AND REPOSITORY-VERIFIED**.

- PR #121 was squash-merged as `a3f15b22c1eabc4ae5801979c1800d021cba9979`.
- Merge tree: `81ae71ddc70b3f65f8ce2b87d2e27f416d9390a2`.
- Post-merge exact-head push CI `33054478128` / policy-tests `#4937` passed Ubuntu Python 3.11, Ubuntu Python 3.12, macOS Python 3.11, and Windows Python 3.11, including package-integrity, Ruff, full pytest, and managed profile lifecycle checks.
- Supported same-child lifecycle controls now validate the canonical Host task address `/root/<native_task_name>` at the facade boundary and preserve that canonical payload for Host calls.
- `prepare_steer` now validates the same canonical Host task address.
- Bare task-name aliases are not retained as a compatibility path.
- Regression coverage includes canonical Steer, Interrupt, Continue, Correction, explicit bare-target rejection, same-attempt continuation/correction, and unchanged generation on rejected interrupt preparation.

The shipped runtime change regenerated `.codex-plugin/package-integrity.json`. Current Host qualification identity is therefore different from the historical H0-H5 campaign:

- runtime manifest SHA256 `a6fd674675fd0b4c2184dab7b0c0a3b85dd8ec0467756876067ae9d2874432ab`;
- profile contract SHA256 `9520395880612c0c40ebc992d36cdadd950fd8328904f3e8c7641042c9f03a8d`;
- Host contract SHA256 `0e9677ba7a66e8ea4a49b354a141098a26d62a3ed7051c50e2cbc7c42bab2566`.

`contracts/policy.json` and `docs/v4/host-smoke.json` remain unchanged; only the runtime-manifest qualification digest changed. Material invalidation is recorded in Issue #91 comment `5436511681`.

Consequences:

- old H0 through H5 results remain durable historical evidence for the old qualification identity;
- they are not formal PASS results for the new runtime-manifest identity;
- Host build 7119, embedded Codex `0.150.0-alpha.8`, prior root/session identity, capacity evidence, and historical probe results are continuity/context evidence only until the new campaign establishes its own required bindings;
- the new campaign must begin at H0 with zero Agent-control;
- after H0, rerun H1/H2 N0, H3/N1, H4/N2, H5/N3, then rerun H6/N4 independently against the repaired product;
- N5/N6 and later phases remain blocked until predecessor requirements pass on the new qualification identity.

Public `1.0.0` release: **BLOCKED on the new exact-qualification N0-N8 campaign and later release closure**.

## Qualification duplicate-dispatch RCA

The H2 Investigator incident was caused by qualification control flow:

- attempt 1 materialized and reached Host `COMPLETED`;
- Main explicitly rejected the completed WorkUnit;
- Main allocated and spawned attempt 2;
- attempt 2 had no new task-level execution evidence;
- the changed basis existed only to repair qualification bookkeeping/provenance;
- Host did not autonomously duplicate the child;
- no direct state-file mutation or unsupported state bypass was found.

`scripts/host_qualification_guard.py` is maintainer-only and prevents one H1/H2 qualification WorkUnit from materializing more than one attempt.

## H4 schema-evidence RCA

The first H4 / N2 execution satisfied the observable identity behavior but its qualification report omitted one required pre-spawn evidence field set: the exact-turn callable `spawn_agent` schema.

The later read-only supplement proved:

- the original spawn call is uniquely bound to probe turn `01a03e36-732f-79d0-8f3c-a0813beccb43`;
- Host-produced `turn_context.multi_agent_version=v2` is retained for that turn;
- the actual spawn call uses `task_name`, `message`, and `fork_turns=none` with no `fork_context`;
- the exact-turn rollout does not retain callable schema definitions, so actual call arguments cannot prove which fields were required or whether the legacy field was absent from the callable schema.

The root cause is qualification evidence capture, not a demonstrated product identity-binding failure. Future covered probes must preserve a contemporaneous privacy-safe capability snapshot before Agent-control. Later turns, actual call arguments, configured defaults, and model memory cannot repair a missing exact-turn schema snapshot.

The corrected H4 rerun used a new pristine WorkUnit with attempt 1 and durably recorded the contemporaneous schema fields before spawn. The old materialized H4 WorkUnit remains consumed historical `UNKNOWN`; the rerun is independently accepted as `PASS_STOP` for the historical qualification identity.

## H6 canonical-target RCA and repair

The historical H6 child successfully consumed RUNNING Steer on its canonical Host address and stayed on the same Host child and ExecutionBinding. Product interrupt preparation then compared the canonical Host target with the stored bare `native_task_name` and failed before `interrupt_agent` could be called.

The repair keeps the internal ExecutionBinding task segment unchanged while adapting the Host-facing control identity at the supported facade boundary:

- canonical Host input is required for Interrupt, Continue, and Correction;
- the facade binds that canonical address to the retained internal task segment before invoking the existing core lifecycle logic;
- the prepared Host payload is canonical again when returned to the caller;
- RUNNING Steer uses the same canonical target convention;
- no bare-target fallback or legacy alias ships.

This repair changes shipped runtime bytes, so repository correctness and Host qualification validity are separate. Repository CI is green; real Host N4 remains unqualified until the new qualification campaign reaches H6 again.

## Permanent Host lifecycle boundary

The operator owns Desktop Host lifecycle and UI actions:

- quit the Desktop Host;
- launch/relaunch/update the Desktop Host;
- create a fresh/replacement root task after restart;
- choose the repository/workspace in the Desktop UI;
- perform required OS/UI-only actions.

A Codex task must never terminate or restart the Host process executing it. If lifecycle work is required, return `OPERATOR_ACTION_REQUIRED_STOP` with the exact manual action, resume condition, and bounded next prompt. The operator performs the action, then the new/current root task collects post-action evidence.

Do not write future qualification prompts that ask Codex Desktop to restart itself.

Inside a live root task, Codex may verify source/package/profile state, inspect Host/session/rollout metadata, establish exact-turn V2 capability, call qualification guards, perform the Agent-control steps required by N0 through N8, assemble evidence, and fail closed when evidence is unavailable or ambiguous.

## Qualification run identity

H1/H2 use a local maintainer identity:

```text
qualification:<campaign>:<h1|h2>:<profile>
```

Examples:

```text
qualification:host7119:h1:reader
qualification:host7119:h2:worker
qualification:host7119:h2:investigator
```

`allocate_single_probe_execution` binds this value as the first ExecutionBinding `execution_basis_ref`. `prepare_single_probe_spawn` requires the same value before Host spawn. The WorkUnit must have no retained or compacted prior attempt.

Issue comment ids are not part of qualification guard semantics.

A completed qualification WorkUnit cannot be rejected and retried to improve bookkeeping or evidence presentation. A genuine rerun after material invalidation uses a new campaign identity and a new pristine qualification WorkUnit.

The guard stays outside `.codex-plugin/package-integrity.json`, so it is not shipped to Plugin users.

## Issue #91 role

Issue #91 remains the external append-only Host evidence journal because real Host results should not mutate the candidate repository.

Write durable entries for:

- conclusive H0 results;
- conclusive H1/H2 profile results;
- consolidated N1 through N8 phase results;
- meaningful `UNKNOWN`, `FAIL`, or mutation stops;
- material invalidations and RCAs.

Do not create a separate comment before every Host action. Do not create routine preflight/result/review/amendment chains for one ordinary step. Prefer one consolidated entry per phase, or one per H1/H2 profile when profile-level evidence matters.

## GitHub development workflow

This is a self-maintained project. Git is the default development/version-control mechanism.

Routine development does not require a new GitHub Issue or Pull Request.

Default flow:

1. use a short-lived branch when isolation helps;
2. make the smallest coherent change;
3. run focused tests and required exact-head CI;
4. inspect the complete diff;
5. fast-forward/merge into the release line when verified;
6. update this handoff only when durable direction or the safe continuation point changes.

Use an Issue for a genuinely long-lived tracked item or the existing Host evidence journal. Use a Pull Request only when its review, approval, or CI surface adds real value.

## Canonical truth owners

- `.codex-plugin/plugin.json`: public Plugin version.
- `.codex-plugin/package-integrity.json`: shipped runtime byte manifest.
- `contracts/policy.json`: fixed product policy/profile values.
- `contracts/state.md`: state schema and clean-break boundary.
- `contracts/recovery.md`: product retry/recovery semantics.
- `docs/v4/architecture.json`: Native Core ownership.
- `docs/v4/host-smoke.json`: N0 through N8 machine Host contract.
- `docs/release-checklist.md`: release gates and invalidation rules.
- `tasks/real-host-qualification-plan.md`: operator/Codex Host qualification procedure, including contemporaneous exact-turn capability snapshot requirements.
- `scripts/host_qualification_guard.py`: maintainer-only H1/H2 single-probe enforcement.
- `scripts/inspect-host-root-runtime.py`: maintainer-only exact-root rollout identity and latest-turn observation for H0 evidence.
- `scripts/inspect-collaboration-runtime.py`: root collaboration call/result/activity evidence, including same-call spawn task-address and Host child-thread binding.
- GitHub branch/commit/CI: live source verification.
- Issue #91: external durable Host evidence journal only.

## Host runtime evidence reuse

External real-Host reports confirmed two Codex evidence patterns that are handled without adding a second routing stack.

For H0, use `scripts/inspect-host-root-runtime.py` against the exact current root thread. It requires one authoritative root `session_meta`, requires `session_id`, rejects child rollouts, and reads turn-scoped model, effort, capability, sandbox, permission, provider, and cwd only from the latest `turn_context`. Missing latest-turn values remain unobserved instead of being filled from an older turn.

For N2 and other child-identity checks, prefer the existing `scripts/inspect-collaboration-runtime.py` path. One exact root `spawn_agent` `call_id` can bind the recognized spawn task address to Host `SubAgentActivity` `agent_path` and `agent_thread_id`. Do not add a separate task-path scan when the stronger same-call Host activity binding is available.

Callable Host schema is a different evidence class. Current rollout inspection can prove the exact turn and actual call, but the build-7119 rollout does not retain callable schema definitions. Future exact-turn schema acceptance therefore preserves a contemporaneous privacy-safe snapshot before Agent-control and carries it into the consolidated durable result.

Both helpers are maintainer evidence tooling. The root helper remains outside `.codex-plugin/package-integrity.json` and does not change shipped Plugin behavior or the N0 through N8 machine contract.

## Lessons

1. Successful Host tool acceptance does not by itself prove the intended semantic effect.
2. `UNKNOWN` cannot authorize acceptance, replacement, or writer transfer.
3. Host configuration expresses intent; Host observations decide runtime truth.
4. `execution_basis_ref` represents semantic basis. Changing a string does not create new task evidence.
5. One qualification WorkUnit may materialize at most once under one single-probe run identity.
6. Qualification mechanics should remain outside shipped runtime unless they are user-facing behavior.
7. Host lifecycle transitions are operator boundaries because a task cannot reliably observe the environment after terminating its own Host.
8. A new chat/task alone is not a rerun reason.
9. A Host build change is a material environment change and requires new H0 binding.
10. Issue/PR workflow is optional for this self-maintained project.
11. Machine contract, human procedure, evidence journal, and development handoff must remain separate control surfaces.
12. Current-session runtime truth must come from current Host evidence. Configured defaults, remembered confirmations, and older turn values do not close a live gate.
13. Prefer same-call Host activity identity binding over heuristic rollout discovery when both are available.
14. A phase closure that changes the next safe continuation belongs in this handoff, while the underlying Host proof remains in Issue #91.
15. Exact-turn Host capability acceptance requires both the bound `multi_agent_version=v2` observation and the same-turn callable schema required by the machine contract.
16. Host rollout retention cannot be assumed to preserve callable schema definitions. Capture required schema evidence contemporaneously before Agent-control.
17. Actual call arguments can cross-check a schema observation but cannot prove required fields or prove that an unused legacy field was absent from the callable schema.
18. A materialized qualification WorkUnit with an unrepairable evidence gap remains consumed. A justified rerun uses a new pristine WorkUnit after the procedure defect is corrected.
19. Host admission capacity and product child ceiling are distinct gates. N3 may only pressure the Host with a projected active managed-child count at or below the product ceiling; inability to reach Host rejection safely is `NOT_RUN_STOP`.
20. A shipped runtime-manifest digest change is a qualification-basis change. Historical probe PASS results remain useful evidence, but they cannot be promoted across the changed identity without the rerun/reuse decision required by the release contract.
21. Canonical Host task addresses belong at the supported Host-facing lifecycle boundary while internal ExecutionBinding identity can retain its deterministic task segment.

## Current qualification point

Repository source immediately before this handoff-only update:

- release branch: `v4/rc5-native-core`;
- verified repair commit: `a3f15b22c1eabc4ae5801979c1800d021cba9979`;
- tree: `81ae71ddc70b3f65f8ce2b87d2e27f416d9390a2`;
- exact-head push CI `33054478128` / `#4937`: `PASS`.

Current Host qualification identity:

- runtime manifest SHA256 `a6fd674675fd0b4c2184dab7b0c0a3b85dd8ec0467756876067ae9d2874432ab`;
- profile contract SHA256 `9520395880612c0c40ebc992d36cdadd950fd8328904f3e8c7641042c9f03a8d`;
- Host contract SHA256 `0e9677ba7a66e8ea4a49b354a141098a26d62a3ed7051c50e2cbc7c42bab2566`.

Historical environment observations, pending new H0 confirmation:

- Desktop Host short version `26.820.60940`;
- Desktop Host build `7119`;
- accepted historical root/session identity `01a03ca1-5ece-7561-afee-9d824171d220`;
- embedded Codex `0.150.0-alpha.8`.

These environment values must be re-observed or otherwise accepted by the current H0 procedure before they are used as current campaign truth.

Material invalidation: Issue #91 comment `5436511681`.

Before any new Host Agent-control, require the target local checkout to match the final handoff-updated release-line HEAD, require exact-head repository CI green, and establish H0 for the new qualification identity.

## Next safe sequence

1. Finish this handoff-only source update and require exact-head repository CI green. Confirm the three Host qualification digests remain unchanged from `a6fd674... / 952039... / 0e9677...`.
2. Synchronize the target Host checkout to that exact verified release-line HEAD and require a clean worktree.
3. Execute H0 only. Perform zero Agent-control. Verify exact source/tree, generated package integrity, installed package/profile continuity, Host build/version/platform/architecture, authoritative root `session_id` and `thread_id`, and current environment binding.
4. If Host lifecycle work is actually required, return `OPERATOR_ACTION_REQUIRED_STOP`. Codex must not restart, relaunch, or replace its own Desktop Host/root task.
5. Record one conclusive H0 result or meaningful stop in Issue #91 under the new runtime-manifest identity.
6. After explicit continuation and accepted H0, use a new campaign identity and pristine WorkUnits as required to rerun H1/H2 N0, H3/N1, H4/N2, and H5/N3 sequentially with mandatory phase stops.
7. Only after H5 is independently accepted on the new identity, rerun H6/N4 against the canonical-target repair. Require same-child Steer consumption, canonical Interrupt, Continue, Correction, generation invariants, and no fresh attempt.
8. Keep N5/N6 and later phases blocked until the new H6/N4 predecessor state is accepted.

## Verification discipline

For repository changes:

1. read the smallest relevant canonical contracts/current source;
2. state acceptance conditions before editing;
3. keep changes focused and avoid compatibility/fallback branches;
4. add regression coverage for the actual failure mode;
5. run focused tests and the complete exact-head repository matrix;
6. compare base/final head and inspect the complete diff;
7. verify package integrity and intended shipped-file scope;
8. do not mark complete while required checks are red, stale, or bound to an older head;
9. classify Host qualification invalidation before resuming real Host actions.