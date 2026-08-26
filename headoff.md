# Headoff

Updated: 2026-08-26.

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

Real Host qualification procedure correction: **IMPLEMENTED AND TESTED**. Host actions may resume only from an exact release-line head whose required repository CI is green.

Public `1.0.0` release: **BLOCKED on real Host qualification and later release closure**.

The previous Host campaign was bound to Desktop Host build 7019. The Host later changed to build 7119, so environment-bound build-7019 H0/N0 observations are historical evidence.

The first build-7119 H0 attempt stopped `UNKNOWN` because the qualifying Codex task was instructed to restart the Desktop Host executing that same task. Post-restart root/session identity could no longer be observed. This established a qualification-procedure design error. It did not establish a Host 7119 product defect.

The operator has since restarted the Desktop Host externally. Build 7119 still requires a conclusive post-restart H0 root/environment binding before N0 resumes.

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

Routine development does not require a GitHub Issue or Pull Request.

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
- `tasks/real-host-qualification-plan.md`: operator/Codex Host qualification procedure.
- `scripts/host_qualification_guard.py`: maintainer-only H1/H2 single-probe enforcement.
- `scripts/inspect-host-root-runtime.py`: maintainer-only exact-root rollout identity and latest-turn observation for H0 evidence.
- `scripts/inspect-collaboration-runtime.py`: root collaboration call/result/activity evidence, including same-call spawn task-address and Host child-thread binding.
- GitHub branch/commit/CI: live source verification.
- Issue #91: external durable Host evidence journal only.

## Host runtime evidence reuse

External real-Host reports confirmed two Codex evidence patterns that are now handled without adding a second routing stack.

For H0, use `scripts/inspect-host-root-runtime.py` against the exact current root thread. It requires one authoritative root `session_meta`, requires `session_id`, rejects child rollouts, and reads turn-scoped model, effort, capability, sandbox, permission, provider, and cwd only from the latest `turn_context`. Missing latest-turn values remain unobserved instead of being filled from an older turn.

For N2 and other child-identity checks, prefer the existing `scripts/inspect-collaboration-runtime.py` path. One exact root `spawn_agent` `call_id` can bind the recognized spawn task address to Host `SubAgentActivity` `agent_path` and `agent_thread_id`. Do not add a separate task-path scan when the stronger same-call Host activity binding is available.

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

## Build-7119 recovery point

Known facts:

- Desktop Host short version observed: `26.820.60940`.
- Desktop Host build observed: `7119`.
- Plugin remains `subagents-dispatch@subagents-dispatch` `1.0.0`.
- Installed package integrity and five managed profiles were healthy at the last check.
- The three Host qualification input blobs were unchanged from the accepted post-clean-break basis at the last check.
- The operator completed an external Desktop Host restart.
- A conclusive post-restart fresh root identity has not yet been bound for build 7119.

Before any new Host action, require the target local checkout to match the current release-line HEAD and require exact-head repository CI to be green. This maintainer-only procedure/source change does not itself require another Host restart when the actual Host build and installed Plugin/profile basis remain unchanged.

## Next safe sequence

1. Synchronize the target local checkout to the current verified release-line HEAD and confirm a clean worktree.
2. Confirm Desktop Host remains build 7119 and installed Plugin/profile basis remains healthy.
3. Operator creates a fresh root task in `/Users/qunqing/2026-Project-Agent/subagents-dispatch` if no suitable post-restart root already exists.
4. Codex performs H0 post-restart environment binding only. Use the exact current `CODEX_THREAD_ID` with `scripts/inspect-host-root-runtime.py` to bind authoritative root `session_id`, `thread_id`, latest-turn runtime context, cwd, and rollout runtime version, then combine that with Host build/platform/source identity and confirm zero Agent-control. Missing or ambiguous required H0 identity remains `UNKNOWN_STOP`.
5. If H0 reaches `PASS_STOP`, run a fresh H1 Reader canary with `qualification:host7119:h1:reader` and a pristine Reader WorkUnit.
6. If Reader passes, run H2 Worker, Investigator, Solver, and Advisor sequentially with distinct pristine WorkUnits and matching `qualification_run_ref` values.
7. Do not begin N1 until N0 is conclusive on build 7119.

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
