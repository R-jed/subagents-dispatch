# Architecture

subagents-dispatch V4.0.0 is a bounded orchestration layer over Codex Native Subagents. Codex remains the Agent runtime and the authoritative source for child materialization, lifecycle status, native control results, actual Host capacity, effective permission state, and managed-child collaboration surface.

The user-facing Main session owns user intent, authorization, decomposition, explicit fixed-profile selection, dispatch judgment, WriterLease coordination, artifact verification, WorkUnit acceptance, integration, and the final response. The normative machine-readable contract is `docs/v4/architecture.json`.

## Public surface

V4 exposes exactly two explicit Skills:

```text
Orchestrate
Doctor
```

`Orchestrate` owns plan-only routing, delegated execution, status, correction, continuation, interruption, cancellation, takeover, integration, and consequence-based independent review. `Doctor` diagnoses the installed Plugin package, managed profiles, Host capability surface, orchestration state, and legacy compatibility.

## Fixed profiles

| Profile | Model / effort | Ordinary authority | Semantic role |
| --- | --- | --- | --- |
| Reader | Luna Max | none | Work |
| Worker | Luna Max | bounded-source-write | Work |
| Investigator | Luna Max | none | Work |
| Solver | Luna Max | bounded-source-write | Work |
| Advisor | Luna Max | none | Review |

The roles remain semantically distinct while managed child execution is currently pinned to Luna Max. This is a Host-containment constraint, not an automatic quality ranking.

Formal N1 evidence on Host build 6962 with embedded Codex `0.149.0-alpha.4.1` proved that a V2-capable depth-1 child can successfully create a depth-2 grandchild. The Host returned a canonical grandchild task address and persisted a parent/child spawn edge. The same Codex source family ignores project `agent_max_depth` on the V2 spawn path. Current Host model metadata reports Luna as `multi_agent_version=v1`, while Terra and Sol report V2. Under the Host's `collab_tools_enabled()` rule, a spawned V2-session child using Luna does not receive collaboration tools.

For that reason the current managed lanes use Luna. Main can still use other Host models for its own work. A Host/model update that changes the managed model's effective collaboration exposure invalidates the containment basis and requires requalification before delegated execution can rely on it.

The profile developer instruction against further delegation remains defense in depth. Role-local `[agents] enabled=false` and `[features] multi_agent_v2=false` are not shipped as containment controls because the current Codex agent-role override layer does not apply those settings.

Reasoning effort is fixed. Effective child collaboration capability, model, effort, sandbox, and permission state remain Host facts when material to acceptance or release.

## Current owners

Product contract ownership remains explicit:

```text
contracts/policy.json
-> fixed profiles, containment posture, delegation ceiling and review policy

contracts/routing.md
-> delegation value, profile selection and dispatch judgment

contracts/responsibility-packet.md
-> child responsibility serialization

contracts/team-plan.md
-> RC compatibility boundary only; no runtime planning authority

contracts/guardrails.md
-> authority, depth, mutation, writer, consent and external-action boundaries

contracts/handoff.md
-> optional Main-accepted evidence bridge

contracts/evidence-artifact.md
-> inspectable evidence provenance

contracts/interaction.md
-> user-visible Orchestrate controls

contracts/recovery.md
-> WorkUnit / ExecutionBinding recovery behavior

contracts/receipt.md
-> user-facing factual execution summary

contracts/final-review.md
-> exact-candidate independent review
```

The complete runtime path map lives at `docs/v4/architecture.json#runtime_owners`.

`docs/v4/host-smoke.json` owns the candidate-bound N0-N8 real Host release gate. Compatibility helpers remain separate from current V4 runtime ownership.

## Responsibility and coordinated work

Zero delegated responsibilities create no orchestration state.

WorkGraph and WorkUnit state are the responsibility structure for one or many delegated responsibilities. `team_plan_revision` may remain as an RC compatibility marker, but it does not authorize planning, routing, dependency readiness, execution, or integration.

WorkUnit records stable responsibility and acceptance truth. ExecutionBinding records one concrete native Agent attempt and route. Fresh retries have no fixed count ceiling. A retry is legal only after the prior attempt is safely settled and a changed execution basis makes repeating the same responsibility rational. A focused same-child FOLLOWUP requires a new correction basis; its count is diagnostic. CONTINUE resumes the same interrupted ExecutionBinding without creating a fresh attempt.

Host `COMPLETED` produces candidate work and maps to `WorkUnit.RESULT_READY`. Main verifies the actual artifact and explicitly accepts the WorkUnit. Dependencies unlock only from `ACCEPTED`.

Older safely settled attempts may be compacted into bounded execution history while the current ExecutionBinding remains fully represented. Compaction never makes stale Host evidence current again.

## Native lifecycle

Fresh spawn follows this order:

```text
validate responsibility / explicit profile / authority / writer admission
allocate ExecutionBinding as SPAWN_PENDING
reserve WriterLease if writable
invoke native spawn_agent
reconcile Host result
```

Recognized success binds observed child identity and lifecycle. A recognized pre-materialization rejection may roll back provisional activation only when evidence establishes that no child materialized. Ambiguous materialization becomes `UNKNOWN`. Writable ambiguity keeps WriterLease blocking.

FOLLOWUP and CONTINUE reuse the same ExecutionBinding and advance `control_epoch` before a later Host generation may become current. Writable reactivation reserves or retains WriterLease first.

STEER targets a currently RUNNING child through the current V2 `followup_task` primitive without creating a replacement child or changing the ExecutionBinding generation. Release qualification requires post-guidance evidence that the original child consumed the guidance; successful tool-call acceptance alone is insufficient proof.

INTERRUPT requests native interruption. The call result alone never releases WriterLease. Current-generation Host settlement is required before writer transfer or takeover.

`UNKNOWN` blocks replacement execution, conflicting writer ownership, and final acceptance until reconciled.

## Host observations

Host observations are reconciled against a current observation basis:

```text
execution_id
control_epoch
lease_epoch when applicable
```

Stale-generation observations are discarded. Delayed evidence from an older or compacted execution cannot reactivate or settle the current generation.

`list_agents` supports Status, recovery, takeover settlement, and ambiguity reconciliation. The allowlisted rollout inspector remains optional and is used only when exact raw collaboration evidence is required for recovery or release validation.

## Scheduling

Scheduling code is a constraint projection. It reports the ready frontier, current active count, known Host capacity, Host readiness, WriterLease state, result backlog, and available slots. It does not rank WorkUnits, apply a fixed acceptance-backlog threshold, or emit automatic launch actions.

The product has one managed-child safety ceiling:

```text
managed children <= 4
```

Four is not a target. Main chooses which ready responsibility to delegate and when. Known Host capacity may reduce available slots. Unknown Host capacity remains unknown and does not create a synthetic occupancy token.

Independent read-only responsibilities may overlap only when effective read-only behavior and responsibility isolation are verified. A blocking canonical WriterLease conservatively blocks another managed child in that workspace until Host evidence proves a safe boundary. The current release has no parallel isolated writer mode.

## WriterLease

V4 keeps one canonical managed writer. WriterLease is project scheduling ownership, not a filesystem or OS lock.

A writable activation acquires or retains the lease before Host activation. A writer in `RESERVED`, `HELD`, `REVOKING`, or `UNKNOWN` remains blocking. INTERRUPT return alone cannot release it. Release or transfer requires current-generation Host lifecycle settlement evidence.

## Child coordination

Main is the sole managed coordinator. Delegation depth one remains project policy.

Current managed profiles deliberately use a Host-qualified model whose child metadata does not expose the V2 collaboration surface. The profile-level instruction against creating further Agents is defense only. Project `max_depth`, role-local feature requests, and behavioral instructions cannot satisfy release containment by themselves.

The acceptable N1 outcome remains an absent child collaboration surface or an authoritative Host denial of descendant creation, with no descendant identity materialized. If the target Host cannot establish that boundary, the affected managed profile is unavailable for delegated execution.

## Final Review

After Main establishes Candidate Ready, `contracts/final-review.md` decides whether consequence-based triggers require a fresh Advisor review of the exact candidate.

Git-backed deliverables use `scripts/review-artifact.py`; non-Git deliverables use deterministic SHA-256 serialization. Any material candidate mutation invalidates the previous verdict.

Strict read-only Final Review also depends on effective Host evidence for the Advisor permission state. Configured `sandbox_mode = read-only` is intent and cannot substitute for that evidence.

## Compatibility

V3.x live state remains legacy evidence and is never silently rewritten into V4 state. Unresolved legacy ownership, active execution, pending takeover, corrupt state, or uncertain writer ownership fails closed.

## Release verification

The Native Core Host campaign is:

```text
N0 exact role / model / effort / fork_turns plus managed-model Host metadata
N1 managed child collaboration containment
N2 canonical task address plus Host-thread identity evidence binding
N3 Host admission rejection with no child identity or resident runtime materialization
N4 RUNNING Steer via followup_task plus same-child correction and continue
N5 interrupt and settlement observation
N6 writer takeover blocked until settlement
N7 rollout reconciliation and privacy allowlist
N8 final Advisor review and effective sandbox truth
```

Repository CI supports delivery by catching regressions. It cannot substitute for real Host behavior, installed-product checks, or Main acceptance semantics.

## V4.0.0 exclusions

The release excludes dynamic effort routing, nested managed delegation, autonomous peer authority transfer, daemon scheduling, persistent orchestration databases, automatic worktree management, and parallel isolated managed writers.
