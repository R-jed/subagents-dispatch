---
name: dispatch
description: Lead Codex Native Subagents with adaptive delegation, preview and live control, evidence-bound handoffs, one-writer safety, bounded recovery, and fresh independent review only when the final artifact requires it.
---

# dispatch

subagents-dispatch is a thin leadership layer over Codex Native Subagents. The current user-facing main session is the team leader and always owns the user's goal, authorization, team composition, integration, acceptance, and final response.

The user does not choose an Agent count, model ladder, Luna/Terra/Sol sequence, or recovery strategy. The user can preview the likely dispatch, inspect active work, steer one responsibility, or explicitly take a responsibility back into Main.

## Runtime policy owners

Keep one owner for each kind of runtime truth:

- `references/interaction.md`: preview, status, steering, user-requested takeover, execution receipt
- `references/router-core.md`: whether delegation helps, role selection, responsibility packets, adaptive scheduling
- `references/handoff-capsule.md`: compact accepted-evidence transfer between responsibilities
- `references/team-plan.md`: multi-responsibility identity, dependency DAG, ownership, revisions, integration order
- `references/recovery.md`: attempt identity, native lifecycle, UNKNOWN, failure classification, bounded recovery
- `references/guardrails.md`: authority, mutation permissions, writer safety, consent, trust boundaries, provisioning, runtime evidence
- `references/final-review.md`: consequence-driven, artifact-bound independent review
- `../../policy-contract.json`: stable role/model constants and hard delegation limits

Do not recreate these rules in another ledger or local taxonomy.

## Hard invariants

1. Delegation must add concrete value. Zero child Agents is normal.
2. There is no project-level ordinary numeric child ceiling or target team size. Native Codex capacity is only a ceiling.
3. Every child owns one distinct responsibility. Duplicate, speculative, and decorative fan-out is prohibited.
4. Preserve an active upstream Skill or accepted plan that already owns workflow truth.
5. One canonical physical checkout has at most one active writing actor inside this orchestration.
6. Filesystem isolation alone does not prove semantic independence, and filesystem permission does not grant mutation authority.
7. Child output is a claim until actual artifact state and relevant verification support it.
8. Requested, accepted, and runtime-observed route facts stay separate. Missing evidence stays missing.
9. Failure does not imply model escalation. Canonical semantic blockers are `contract | judgment | investigation | stalled`.
10. `UNKNOWN` is not `FAILED`; ambiguous execution does not authorize replacement work or an unsafe takeover.
11. Final Review is consequence-driven and bound to the exact candidate reviewed.
12. Children do not create project Subagents. Delegation depth is one.
13. Preview, status, steer, and takeover never widen user scope, permissions, mutation authority, or external-impact authorization.
14. Handoff Capsules carry only Main-accepted facts/evidence; raw child claims never become inherited task truth automatically.
15. Every new project child is a fresh-context spawn: `fork_turns` is present and exactly `none` before `spawn_agent` is invoked.

## Control loop

### 0. Handle an explicit control intent before ordinary routing

Use `references/interaction.md`.

Recognize these forms:

```text
/dispatch preview <task>
/dispatch status
/dispatch steer <unit_id>: <guidance>
/dispatch takeover <unit_id>
/dispatch takeover <unit_id>: <guidance>
```

Preview performs no delegated execution or mutation. Status is one-shot inspection. Steering keeps the same responsibility and authority. Takeover settles the old owner before Main assumes that responsibility.

If the request is not one of those exact control shapes, run the ordinary task loop below.

### 1. Understand the task before choosing Agents

Establish:

```text
observable outcome
scope and authorization
important invariants
acceptance conditions
known reliable evidence
```

If another active Skill or accepted user plan already defines goal, stage order, dependencies, outputs, acceptance, or quality gates, preserve that workflow as task truth. subagents-dispatch may coordinate owners and execution around it; it does not replace the domain workflow.

### 2. Ask whether delegation helps

Use `references/router-core.md`.

Keep work in Main when delegation mainly duplicates context or adds handoff/integration cost. Delegate only a responsibility that is ready, distinct, non-duplicative, safe under current authority, and worth the additional coordination.

Role choice follows the work:

```text
bounded read-only factual evidence
-> Main or subagents_dispatch_reader

clear bounded implementation whose material behavior is already decided
-> Main or subagents_dispatch_worker

material judgment before writing
-> capable Main or subagents_dispatch_advisor

implementation with material judgment coupled to the write
-> capable Main or subagents_dispatch_solver

broader read-heavy technical investigation after semantics are stable
-> Main or subagents_dispatch_investigator
```

Terra is not an escalation rung, and one failed Luna attempt does not imply Terra or Sol.

### 3. Ensure required native roles are ready before delegated execution

Only do this after the task actually justifies delegation. Preview, Status, and other non-spawning control operations never provision roles.

The bundled installer is:

```text
installer = skill_dir/../../scripts/install-agents.py
```

First inspect whether the exact required project role is available to the current Codex task. If it is available, continue normally.

If the exact role is unavailable, run the non-mutating managed-profile check:

```bash
python "$installer" --check
```

Handle the result conservatively:

```text
--check passes, but the role is unavailable
-> the on-disk profiles are exact while the current task cannot use that role
-> readiness outcome: RESTART_REQUIRED
-> do not attempt spawn_agent in this task
-> ask for one fresh Codex task/session and rerun the original /dispatch request

--check reports a clean Not installed state
-> explicit /dispatch already authorizes routine first-use provisioning of only the plugin-owned managed paths
-> run the installer, then --check
-> if both succeed: RESTART_REQUIRED
-> do not attempt spawn_agent in this task
-> ask for one fresh Codex task/session and rerun the original /dispatch request

--check reports collision, unsafe path, modified/unowned state, invalid ownership metadata, or another non-clean failure
-> USER_ACTION_REQUIRED
-> do not overwrite, repair, substitute a role, or spawn a child
-> report the exact failure and direct the user to /doctor when useful
```

Routine provisioning may manage only subagents-dispatch's five fixed native custom-Agent profiles plus its ownership manifest and installer lock. It does not authorize `config.toml`, credentials, MCP configuration, repositories, unrelated Agent profiles, broader repair, migration, or upgrade mutation. Those boundaries live in `references/guardrails.md`.

`RESTART_REQUIRED` is a pre-dispatch readiness outcome, not a Recovery/Agent lifecycle state. No Agent attempt exists yet, and no execution receipt is emitted because no child was spawned.

On the fresh task, inspect exact role availability again. If the role remains unavailable despite exact installed profiles, fail closed as a Host/configuration limitation; do not substitute another role merely to keep moving.

### 4. Coordinate only when coordination complexity is real

A single delegated responsibility stays on the lightweight path with a stable `UNIT ID` and unique `TASK ID`.

Before two or more delegated responsibilities are concurrently unresolved, or when delegated outputs need non-trivial machine-checkable dependency/integration order, use `references/team-plan.md` and validate the TeamPlan.

Main still decides semantic independence, delegation value, role suitability, user authority, and final acceptance. The TeamPlan only makes coordination truth explicit.

Use progressive fan-out from the ready work. Do not create fixed waves, poll to simulate a scheduler, or fill spare native capacity for appearance.

### 5. Dispatch bounded responsibilities and verify returned claims

Responsibility packet shape, mutation authority, decision rights, evidence reuse, and stop conditions are owned by `references/router-core.md` and `references/guardrails.md`.

Before every `spawn_agent` call for a new project child, inspect the call itself and require all of the following:

```text
agent_type = the exact required subagents-dispatch project role
fork_turns is present
fork_turns = none
the bounded responsibility packet is the child's task context
```

If any item is false, correct the call before invoking the Host. Never send `fork_turns: all` for a project child and never omit `fork_turns`. Do not use a rejected full-history spawn as a capability probe.

A Host rejection before child identity exists is not an Agent attempt and does not increment the retry count. Correct a pre-attempt call error without relabeling it as delegated recovery; exact attempt and retry semantics live in `references/recovery.md`.

When a downstream responsibility would otherwise repeat material discovery that Main has already verified, add one compact Handoff Capsule under `references/handoff-capsule.md`. Keep fresh child context; do not forward the previous child's transcript or full Main history.

When a child returns:

1. inspect the actual artifact or evidence;
2. inspect relevant verification results;
3. merge only supported new evidence;
4. check acceptance;
5. mark only verified facts as eligible for a future Handoff Capsule;
6. if unresolved, classify the actual blocker before choosing another action.

Do not accept “done” as proof.

### 6. Recover only through the bounded recovery contract

Use `references/recovery.md`.

The recovery contract owns attempt identity, host-state ambiguity, follow-up/retry limits, and Main takeover. Never invent a new blocker class or model-escalation rule locally.

An explicit user takeover request is handled through `references/interaction.md` and the same `main_takeover` recovery semantics. User intent may request an earlier takeover, but it does not bypass lifecycle settlement or one-writer safety.

If TeamPlan is active and blocker-driven rerouting changes the assigned delegated role, create a new TeamPlan revision while keeping the same `UNIT ID` only when the responsibility goal/output remain the same. A pure Main takeover is Recovery state and does not create a `role: main`. A materially redefined responsibility gets a new unit ID.

Use `../../scripts/runtime-evidence.py` only when exact runtime route, ancestry, permission enforcement, or Main capability evidence materially affects acceptance or routing. It is diagnostic, not an every-child hot-path dependency.

### 7. Apply Final Review only when the candidate requires independent assurance

After ordinary acceptance reaches Candidate Ready, use `references/final-review.md`.

Prior Terra/Solver use, recovery, TeamPlan use, file count, or diff size is not a review trigger by itself. The current artifact's consequences and any material verification gap decide the gate.

When review is required, bind the exact candidate and use a fresh `subagents_dispatch_advisor`. Only a valid `ship` verdict for the unchanged candidate satisfies required independent review.

### 8. Report the result or blocker

The terminal response focuses on:

```text
what changed or what remains blocked
verification performed
remaining material risk, if any
```

If at least one child was actually spawned, append one compact execution receipt using `references/interaction.md`, even when the dispatch ends blocked or partial. Keep it factual and short. Do not emit a receipt for zero-child completion, preview, or status-only requests.

Do not expose hidden reasoning or guess model/token/cost telemetry that the host did not report.
