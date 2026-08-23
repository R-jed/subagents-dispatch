# V4 Current State Checkpoint

Updated: 2026-08-23 14:12 +08:00.

This file is the short current-state entrypoint for V4 maintenance. Read it before `docs/v4/development-handoff.md`. The long handoff remains the detailed chronology and architecture background, but status statements there that predate this checkpoint are historical. Machine-readable contracts and current GitHub/Host evidence still have higher authority.

## Current release state

Release branch: `v4/rc5-native-core`.

Release PR: #81 `RC5 Native Core: remove Hook control plane`, OPEN and Draft.

Last shipped-runtime/package candidate basis before this non-shipped documentation checkpoint:

- commit `3bc593fbae535b1d31d28f3f46dc59677ef87c52`
- tree `eadcf99c3c339428256412319da005f482df8935`
- exact-head workflow `32617888028` PASS
- Ubuntu Python 3.11 PASS, including pinned official OpenAI Plugin validator
- Ubuntu Python 3.12 PASS
- macOS Python 3.11 PASS
- Windows Python 3.11 PASS
- aggregate `policy-tests` PASS

PR #98 `Fail closed on unverified V4 child containment` is merged. Its production change requires explicit `managed_child_containment=verified` before Host execution readiness. Missing, failed, or unknown containment stays fail closed.

`docs/v4/current-state.md` and `README_AI.md` are not listed in `.codex-plugin/package-integrity.json`. Updating this checkpoint does not change shipped Plugin bytes or installed-package identity. Always verify the current release-branch commit and tree on GitHub rather than treating the commit above as this document's own immutable identity.

## Real Host gate

Issue #91 is the Real Host Test Ledger and remains operational authority for real Host actions.

Current gate state:

- N0 PASS
- N1 FAIL
- N2-N8 NOT_RUN / BLOCKED BY N1
- Final Review NOT_RUN
- publication BLOCKED

The conclusive N1 evidence is `HOST-N1-GRANDCHILD-002`: a real V2 depth-1 parent successfully created a depth-2 grandchild, which received durable Host thread identity and a `thread_spawn_edges` record.

Do not repeat that probe merely because repository documentation or fail-closed diagnosis code changes. Every real Host action still requires an Issue #91 `REUSE | RERUN | NOT_RUN` preflight.

Latest N1 upstream-analysis ledger entries:

- `HOST-N1-UPSTREAM-TRACK-001`, comment `5384469319`
- `HOST-N1-UPSTREAM-DESIGN-ROOT-001`, comment `5384499217`

## N1 root cause, current best evidence

Current evidence no longer supports treating V2 depth behavior as an accidental missing guard.

OpenAI Codex PR #20180, `Make multi-agent v2 ignore agents.max_depth`, was merged on 2026-04-29. It explicitly defines `agents.max_depth` as a V1 guard, removes the V2 depth rejection, and adds a regression test proving a depth-1 V2 child may spawn another child while `agent_max_depth=1`.

OpenAI Codex PR #36892, `Support leaf models in multi-agent v2`, was merged on 2026-08-04. It establishes the supported V2 leaf-worker mechanism: a non-root child receives collaboration tools only when its selected model metadata supports MultiAgent V2. Its tests require legacy/Luna leaf workers to omit collaboration tools.

The exact Host model metadata observed in the release campaign is:

- `gpt-5.6-luna`: `multi_agent_version=v1`
- `gpt-5.6-terra`: `multi_agent_version=v2`
- `gpt-5.6-sol`: `multi_agent_version=v2`

Reader and Worker therefore have the upstream model-metadata basis for leaf behavior, but N1 still requires exact Host evidence of their effective child collaboration surface. The frozen Investigator/Terra and Solver/Advisor/Sol profiles use V2-capable model metadata.

OpenAI Codex PR #39299 bounds role-level configuration reductions. The supported role reduction surface does not include `MultiAgentV2` or `agents_enabled`. Profile declarations such as `[agents] enabled=false` and `[features] multi_agent_v2=false` remain requested posture for this gate and cannot prove effective Host containment.

Current Codex Plugin manifest capabilities do not provide a model-catalog contribution, model-selector remapping, or per-child model-capability override that could preserve Terra/Sol backend selection while advertising those children as leaves.

No current implementation PR in `openai/codex` was found for a same-model child-specific non-delegating ceiling. `openai/codex` issue #36381 proposes a strict host-enforced delegation/capability receipt design and identifies its implementation as a default-off external reference branch rather than an implementation PR. Treat it as proposal evidence only, not as an accepted Host roadmap or available product primitive.

## Rejected remediation paths

Do not reopen these without materially new Host evidence:

- treating `max_depth=1` as V2 enforcement;
- adding stronger developer instructions;
- relying on child self-refusal;
- relying on Code Mode / `DirectModelOnly` exposure changes;
- using temporary session-capacity exhaustion as containment;
- changing every managed profile to Luna merely to obtain leaf metadata;
- inventing a model alias to Terra/Sol without a supported Host selector-to-backend mapping;
- restoring Hook/Guard interception or another Plugin-owned lifecycle control plane;
- interrupting a grandchild after materialization and calling that containment.

All of these either fail the current N1 no-descendant-materialization contract or violate the frozen V4 architecture/profile contract.

## What can reopen N1

An N1 rerun needs a material changed basis. Acceptable examples are:

- Host/Codex adds hard V2 descendant containment before thread materialization;
- Host/Codex adds a child-specific non-delegating capability that removes/rejects collaboration tools for Terra/Sol children;
- role-level capability reduction gains an effective Host-enforced `MultiAgentV2` / delegation disable surface and real Host evidence proves it;
- Terra/Sol model capability metadata changes in a way that makes the exact frozen selectors authoritative leaves;
- a formally approved product/architecture change replaces the current fixed-profile or N1 contract without weakening release safety by assumption.

A new chat, a documentation-only commit, a reinstall, or another generic V2 probe is not a changed basis.

## Current next step

Keep PR #81 Draft and publication blocked. Keep N2-N8 NOT_RUN. Do not mutate shipped runtime code merely to make the gate appear green.

Monitor OpenAI Codex for a real containment primitive or relevant Host/runtime change. When one appears, inspect source first, design the smallest Native Core adaptation, run repository validation, rebind the exact installed candidate if shipped bytes changed, then perform one fresh N1 under Issue #91 preflight discipline.

## Authority order for continuation

Use this order when status conflicts:

1. current production implementation and machine-readable contracts;
2. `contracts/`;
3. `docs/v4/architecture.json`;
4. `docs/v4/host-smoke.json`;
5. `docs/release-checklist.md`;
6. current GitHub branch/PR/CI and Issue #91 Host evidence;
7. this checkpoint;
8. `docs/v4/development-handoff.md` for detailed chronology/background;
9. ordinary README material;
10. `docs/history/` provenance.
