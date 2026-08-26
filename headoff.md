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

Real Host qualification procedure: **UPDATED AFTER H4 EVIDENCE-CAPTURE RCA**. Future covered Agent-control probes must preserve a privacy-safe exact-turn capability/schema snapshot before the control call so later review does not depend on Host rollout retaining callable schema definitions.

Build-7119 H0 environment binding: **PASS_STOP** and reusable while the material Host environment and three Host qualification digests remain unchanged.

H1 Reader: **PASS_STOP**, consumed.

H2 / N0 completion: **PASS_STOP**. Worker, Investigator, Solver, and Advisor each passed on one consumed attempt. Durable closure: Issue #91 comment `5422820011`.

H3 / N1 managed delegation depth: **PASS_STOP**. Reader, Worker, Investigator, Solver, and Advisor each stayed leaf-only under adversarial nested-Agent instructions, with zero child Agent-control, zero Agent-layer calls, and zero descendants. Durable result: Issue #91 comment `5425708582`.

Current installation continuity baseline: **PASS_STOP**. The active local Marketplace Plugin reports `subagents-dispatch@subagents-dispatch` `1.0.0`; the current release manifest covers 46 shipped files with zero missing, unexpected, or hash-mismatched files; all five managed profiles match the candidate; Doctor package/profile checks are healthy; the baseline used zero Agent-control and produced no repository or installed-package mutation. This routine continuity check intentionally has no separate Issue #91 PASS comment.

H4 / N2 is **UNKNOWN_STOP / INCOMPLETE**. The first WorkUnit `N2_READER_HOST7119` materialized successfully and produced a coherent identity chain in Issue #91 comment `5425895958`: one Reader ExecutionBinding maps to canonical task address `/root/sd_n2_reader_host7119_a1`, the same spawn call binds that address to Host child thread `01a03e37-a8db-7880-a8f5-6a542c1ccaab`, and the child rollout independently reports the same path/thread/session/parent/role. Independent review found that the required same-turn callable spawn schema observation was not preserved in the durable result. The zero-Agent-control supplement in Issue #91 comment `5426422092` confirmed the exact probe rollout does not retain callable schema records, so the missing proof cannot be reconstructed and correctly stopped `UNKNOWN_STOP`.

The first H4 WorkUnit is consumed historical `UNKNOWN` evidence. Do not reuse `N2_READER_HOST7119` and do not allocate attempt 2 for it. The qualification procedure has been corrected so a justified H4 rerun can use a new pristine WorkUnit after the corrected source is exact-head CI green and synchronized to the Host checkout.

N3 and later phases remain blocked until a fresh H4 / N2 rerun reaches conclusive `PASS_STOP` and receives independent acceptance.

Public `1.0.0` release: **BLOCKED on H4 rerun closure, N3 through N8, and later release closure**.

The earlier build-7019 campaign and the first failed build-7119 self-restart attempt remain historical evidence only. The current accepted build-7119 campaign is the authority for reusable H0 through H3 evidence while its environment and qualification identity remain valid.

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

A genuine H4 rerun is justified only after this procedure correction is verified. It must use a new pristine WorkUnit with attempt 1. The old materialized H4 WorkUnit remains consumed.

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
- `tasks/real-host-qualification-plan.md`: operator/Codex Host qualification procedure, including contemporaneous exact-turn capability snapshot requirements.
- `scripts/host_qualification_guard.py`: maintainer-only H1/H2 single-probe enforcement.
- `scripts/inspect-host-root-runtime.py`: maintainer-only exact-root rollout identity and latest-turn observation for H0 evidence.
- `scripts/inspect-collaboration-runtime.py`: root collaboration call/result/activity evidence, including same-call spawn task-address and Host child-thread binding.
- GitHub branch/commit/CI: live source verification.
- Issue #91: external durable Host evidence journal only.

## Host runtime evidence reuse

External real-Host reports confirmed two Codex evidence patterns that are now handled without adding a second routing stack.

For H0, use `scripts/inspect-host-root-runtime.py` against the exact current root thread. It requires one authoritative root `session_meta`, requires `session_id`, rejects child rollouts, and reads turn-scoped model, effort, capability, sandbox, permission, provider, and cwd only from the latest `turn_context`. Missing latest-turn values remain unobserved instead of being filled from an older turn.

For N2 and other child-identity checks, prefer the existing `scripts/inspect-collaboration-runtime.py` path. One exact root `spawn_agent` `call_id` can bind the recognized spawn task address to Host `SubAgentActivity` `agent_path` and `agent_thread_id`. Do not add a separate task-path scan when the stronger same-call Host activity binding is available.

Callable Host schema is a different evidence class. Current rollout inspection can prove the exact turn and actual call, but the build-7119 rollout does not retain callable schema definitions. Therefore future exact-turn schema acceptance must preserve a contemporaneous privacy-safe snapshot before Agent-control and carry it into the consolidated durable result.

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

## Build-7119 qualification point

Known facts:

- Desktop Host short version observed: `26.820.60940`.
- Desktop Host build observed: `7119`.
- Plugin remains `subagents-dispatch@subagents-dispatch` `1.0.0`.
- Current release manifest covers 46 shipped files.
- Current active installation is a local Marketplace source and passed the installation continuity baseline with 46/46 files matching, all five profiles matching, Doctor package/profile health PASS, zero Agent-control, and zero mutation.
- Accepted Host qualification identity:
  - runtime manifest SHA256 `3e6d43aec07e493b937195ebbd05489f43dbbd36eea85671980f69fb357a0d8c`;
  - profile contract SHA256 `9520395880612c0c40ebc992d36cdadd950fd8328904f3e8c7641042c9f03a8d`;
  - Host contract SHA256 `0e9677ba7a66e8ea4a49b354a141098a26d62a3ed7051c50e2cbc7c42bab2566`.
- Accepted root/session identity: `01a03ca1-5ece-7561-afee-9d824171d220`.
- Embedded Codex observed: `0.150.0-alpha.8`.
- H0 environment binding is conclusive `PASS_STOP`.
- H1 Reader is conclusive `PASS_STOP` and consumed.
- H2 Worker, Investigator, Solver, and Advisor are each conclusive `PASS_STOP` and consumed.
- H2 overall / N0 is complete. Durable closure: Issue #91 comment `5422820011`.
- H3 / N1 is conclusive `PASS_STOP`. Durable result: Issue #91 comment `5425708582`.
- First H4 / N2 execution: core identity evidence coherent, but final qualification status is `UNKNOWN_STOP` because required exact-turn callable schema evidence was not preserved. Original result: Issue #91 comment `5425895958`. Evidence-gap supplement: Issue #91 comment `5426422092`.

Before any new Host action, require the target local checkout to match the current release-line HEAD and require exact-head repository CI to be green. A source-only change outside the three Host qualification inputs does not erase conclusive Host evidence, but repository source identity and CI must still be refreshed before continuing.

## Next safe sequence

1. Verify the final release-line HEAD containing the qualification procedure correction and this handoff update reaches exact-head CI green.
2. Confirm `.codex-plugin/package-integrity.json`, `contracts/policy.json`, and `docs/v4/host-smoke.json` remain unchanged from the accepted qualification basis.
3. Synchronize the target Host checkout to that exact verified HEAD and require a clean worktree.
4. Confirm Desktop Host remains build 7119, embedded Codex remains `0.150.0-alpha.8`, root/session identity remains `01a03ca1-5ece-7561-afee-9d824171d220`, and the installation continuity basis remains healthy. If any material fact changed, classify invalidation before Agent-control.
5. Reuse accepted H0 through H3 evidence while their reuse conditions hold. Keep the first H4 WorkUnit `N2_READER_HOST7119` consumed as historical `UNKNOWN` evidence.
6. Classify the next H4 action as `RERUN` with the concrete reason: the prior H4 attempt cannot satisfy the exact-turn schema evidence requirement because the previous qualification procedure failed to preserve a contemporaneous callable-schema snapshot and the Host rollout does not retain it.
7. Allocate a new pristine H4 / N2 WorkUnit with attempt 1. Do not reuse the old WorkUnit and do not create attempt 2 for it.
8. Before the new H4 spawn, bind the exact turn, prove `multi_agent_version=v2`, verify the callable spawn schema, and preserve the privacy-safe contemporaneous snapshot required by `tasks/real-host-qualification-plan.md`.
9. Execute only H4 / N2, verify the same canonical task-address to Host-thread to child-rollout to ExecutionBinding chain, record one consolidated H4 result, and stop at `H4_STOP`.
10. Keep N3 blocked until the fresh H4 result receives conclusive independent acceptance. Do not automatically execute N3.

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
