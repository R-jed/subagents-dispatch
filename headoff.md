# Headoff

Updated: 2026-08-26.

## Purpose

This is the development-session handoff record for `subagents-dispatch`. It preserves durable project direction, major completed work, important decisions, lessons, current blockers, and the next safe continuation point.

It is not Plugin runtime, a product contract, Host qualification input, release evidence, or a release gate. Live source and CI truth belong in GitHub. Real Host evidence belongs in the external campaign evidence journal. Machine behavior belongs in canonical contracts.

## Project in one minute

`subagents-dispatch` is a bounded orchestration layer over Codex Native Subagents. Main owns dispatch judgment, integration, irreversible side effects, and final acceptance. Managed children use fixed profiles, fresh context, bounded authority, WorkGraph/WorkUnit responsibility ownership, ExecutionBinding attempt identity, and WriterLease coordination.

The first public Plugin line is `1.0.0`. Native Core V4 is an internal architecture generation, not the public version.

Public Skills are exactly `Orchestrate` and `Doctor`.

Fixed managed profiles:

- Reader: Luna Max, read-only.
- Worker: Luna Max, bounded source write.
- Investigator: Terra High, read-only.
- Solver: Sol High, bounded source write.
- Advisor: Sol High, read-only.

Fresh managed children use `fork_turns=none`. Managed children are leaf Agents and do not create/control another managed Agent layer. Product managed-child ceiling is four.

## Current status

Repository clean-break closure: **COMPLETE**.

Investigator duplicate-dispatch RCA and guard repair: **COMPLETE**.

Real Host qualification procedure correction: **IMPLEMENTED IN CURRENT DEVELOPMENT CHANGE; verify exact-head CI before resuming Host actions**.

Public `1.0.0` release: **BLOCKED on real Host qualification and later release closure**.

The previous Host campaign was bound to Desktop Host build 7019. The Host later changed to build 7119, so environment-bound H0/N0 observations from build 7019 are historical evidence and cannot qualify build 7119.

A first build-7119 H0 attempt stopped `UNKNOWN` because the qualifying Codex task was instructed to restart the Desktop Host that was executing the task. After self-host restart, the task could no longer observe the new root/session identity. This was a qualification-procedure design error, not evidence of a Host 7119 product defect.

The operator has since restarted the Desktop Host externally. The next build-7119 campaign must use the corrected operator/Codex boundary described below.

## Durable architecture

- WorkGraph and WorkUnit own responsibility, dependencies, readiness, and acceptance.
- ExecutionBinding owns one concrete managed attempt/generation.
- WriterLease owns canonical-workspace managed writer coordination.
- Main is the sole managed coordinator and final acceptance owner.
- Host `COMPLETED` means candidate lifecycle completion only.
- Codex Host owns actual materialization, lifecycle, capacity, child identity, effective permission, effective sandbox, and effective collaboration capability.
- Unsupported state and ambiguous Host truth fail closed.
- Pre-1.0 migration/compatibility surfaces and TeamPlan are not part of the first public contract.

## Qualification duplicate-dispatch RCA

The H2 Investigator incident was caused by qualification control flow:

- attempt 1 materialized and reached Host `COMPLETED`;
- Main explicitly rejected the completed WorkUnit;
- Main allocated and spawned attempt 2;
- attempt 2 had no new task-level execution evidence;
- its changed basis existed only to repair qualification provenance/bookkeeping;
- Host did not autonomously duplicate the child;
- no direct `active.json` mutation or unsupported state bypass was found.

The repair remains maintainer-only in `scripts/host_qualification_guard.py`. It prevents a single H1/H2 qualification WorkUnit from materializing more than one attempt.

## Corrected Host qualification design

### Operator owns Desktop Host lifecycle

The operator, not a Codex task, performs:

- quit Desktop Host;
- launch/relaunch Desktop Host;
- Host install/update;
- create a fresh/replacement root task after restart;
- choose the repository/workspace in the Desktop UI;
- other required UI/OS lifecycle actions.

A Codex task must not terminate or restart the Host process that is executing it. If lifecycle work is needed, the task returns `OPERATOR_ACTION_REQUIRED_STOP` with the exact manual action, resume condition, and bounded next prompt. The operator performs the action and the next/current task collects post-action evidence.

This boundary is permanent. Do not write future qualification prompts that ask Codex Desktop to restart itself.

### Codex owns in-task qualification work

Inside a live root task, Codex may:

- verify source, package integrity, Plugin and managed profiles;
- inspect Host/session/rollout metadata;
- establish exact-turn V2 capability;
- call qualification guard functions;
- perform the Agent-control actions required by N0 through N8;
- assemble evidence and verdicts;
- stop fail-closed when evidence is unavailable or ambiguous.

### Issue #91 is an evidence journal

Issue #91 remains useful because Host results must live outside the candidate repository. Its role is now narrow:

- conclusive H0 environment results;
- conclusive H1/H2 profile results;
- consolidated N1 through N8 phase results;
- meaningful `UNKNOWN`, `FAIL`, or mutation stops;
- material invalidations and RCAs.

Do not create a separate Issue #91 comment before every Host action. Do not produce routine preflight, result, review, and amendment comment chains for one ordinary step. Prefer one consolidated durable entry per phase, or one per H1/H2 profile when profile-level evidence matters.

Issue comment ids are no longer part of qualification guard semantics.

### Local qualification run identity

H1/H2 use a local maintainer run ref:

```text
qualification:<campaign>:<h1|h2>:<profile>
```

Examples:

```text
qualification:host7119:h1:reader
qualification:host7119:h2:worker
qualification:host7119:h2:investigator
```

`allocate_single_probe_execution` binds this value as the first ExecutionBinding `execution_basis_ref`. `prepare_single_probe_spawn` requires the same value before Host spawn. The guard also requires a pristine WorkUnit with no retained or compacted prior attempt.

A completed qualification WorkUnit cannot be rejected and retried to improve bookkeeping or evidence presentation. A genuine later rerun caused by material invalidation uses a new campaign identity and a new pristine qualification WorkUnit.

The guard remains outside `.codex-plugin/package-integrity.json`, so this testing mechanism is not shipped to Plugin users.

## GitHub development workflow

This is a self-maintained project. Git is the default development/version-control mechanism.

Routine development does not require creating a GitHub Issue or Pull Request.

Default flow:

1. use a short-lived branch when isolation helps;
2. make the smallest coherent change;
3. run focused tests and required exact-head CI;
4. inspect the complete diff;
5. fast-forward/merge into the release line when verified;
6. update this handoff when durable direction or the safe continuation point changes.

Use a GitHub Issue for a genuinely long-lived tracked item or for the existing special Host evidence journal. Use a Pull Request only when the review surface, approval semantics, or CI behavior adds real value. Do not create an Issue or PR merely because a code change exists.

## Canonical truth owners

- `.codex-plugin/plugin.json`: public Plugin version.
- `.codex-plugin/package-integrity.json`: shipped runtime byte manifest.
- `contracts/policy.json`: fixed product policy and managed profile values.
- `contracts/state.md`: state schema and clean-break boundary.
- `contracts/recovery.md`: product retry and recovery semantics.
- `docs/v4/architecture.json`: Native Core ownership.
- `docs/v4/host-smoke.json`: N0 through N8 machine Host contract.
- `docs/release-checklist.md`: release gates and invalidation rules.
- `tasks/real-host-qualification-plan.md`: operator/Codex Host qualification procedure.
- `scripts/host_qualification_guard.py`: maintainer-only H1/H2 single-probe enforcement.
- GitHub branch/commit/CI: live source verification.
- Issue #91: external durable Host evidence journal only.

## Important lessons

1. A successful Host action is not sufficient by itself to prove the intended semantic effect.
2. `UNKNOWN` remains visible and cannot authorize acceptance, replacement, or writer transfer.
3. Host configuration expresses intent; Host observations decide runtime truth.
4. `execution_basis_ref` represents semantic basis. Changing a string is not evidence that the underlying task basis changed.
5. One qualification WorkUnit may materialize at most once under one single-probe run identity.
6. Qualification mechanics should stay outside the shipped runtime unless they are part of user-facing behavior.
7. Host lifecycle transitions are operator boundaries because a task cannot reliably observe the environment after terminating its own Host.
8. A new chat/task alone is not a rerun reason.
9. A Host build change is a material environment change and requires new H0 environment binding.
10. GitHub Issue/PR workflow is optional for this self-maintained project; use it only when it provides durable value.
11. Keep machine contract, human procedure, evidence journal, and development handoff separate. Do not let one become a duplicate control plane for the others.

## Current build-7119 recovery point

Known current facts before this procedure change:

- Desktop Host short version observed: `26.820.60940`.
- Desktop Host build observed: `7119`.
- Plugin remains `subagents-dispatch@subagents-dispatch` `1.0.0`.
- Installed package integrity and five managed profiles were healthy.
- The three Host qualification input blobs remained unchanged from the accepted post-clean-break basis.
- The operator completed an external Desktop Host restart.
- A conclusive post-restart fresh root identity has not yet been bound for build 7119.

Because this procedure/maintainer-tool change updates release-source identity, synchronize the target checkout to the final verified commit before resuming Host qualification. This source-only change does not require another Host restart by itself if Host build 7119 and the installed Plugin/profile basis remain unchanged.

## Next safe sequence

1. Verify this procedure redesign on the exact final source with focused tests, full repository CI, package integrity, and complete diff review.
2. Synchronize the target local checkout to that exact verified source.
3. Confirm Desktop Host remains build 7119 and installed Plugin/profile basis remains healthy.
4. Operator creates a fresh root task in `/Users/qunqing/2026-Project-Agent/subagents-dispatch` if no suitable post-restart root already exists.
5. Codex performs H0 post-restart environment binding only. It must establish authoritative `session_id`, `thread_id`, rollout identity, Host build/runtime, cwd, source identity, and zero Agent-control.
6. If H0 reaches `PASS_STOP`, run a fresh H1 Reader canary with `qualification:host7119:h1:reader` and a pristine Reader WorkUnit.
7. If Reader passes, run H2 Worker, Investigator, Solver, and Advisor sequentially with distinct pristine WorkUnits and matching `qualification_run_ref` values.
8. Do not begin N1 until N0 is conclusive on build 7119.

## Verification discipline

For repository changes:

1. read the smallest relevant canonical contracts and current source;
2. state acceptance conditions before editing;
3. keep behavior changes focused and avoid compatibility/fallback branches;
4. add regression coverage for the actual failure mode;
5. run focused tests and the complete exact-head repository matrix;
6. compare base and final head and inspect the complete diff;
7. verify generated/package integrity and intended shipped-file scope;
8. do not mark complete while any required check is red, skipped, stale, or bound to an older head;
9. classify Host qualification invalidation before resuming real Host actions.
