# TeamPlan

TeamPlan is the lightweight coordination contract for tasks that need more than one delegated responsibility at the same time or need machine-checkable dependency and integration order.

It does not choose models, replace Main, create another planner, or impose a project-level child-count target. `routing.md` still decides whether delegation is useful and which specialist role owns each delegated responsibility. Main remains the integration and acceptance owner.

A TeamPlan makes coordination structure explicit. It does not by itself prove that decomposition preserved every material obligation from user or upstream task truth. Semantic coverage remains a Main responsibility under `routing.md`.

## 1. When TeamPlan is required

Do not create TeamPlan ceremony for zero or one delegated responsibility.

Compile TeamPlan before dispatch when either condition becomes true:

- two or more delegated responsibilities are concurrently unresolved; or
- delegated outputs have a non-trivial dependency or integration order that must remain explicit across attempts.

If the task later returns to one simple responsibility, keep the current accepted plan truth but do not create new plan machinery without value.

When an upstream Skill or accepted plan already owns decomposition, dependencies, outputs, acceptance, or quality gates, compile those responsibilities into TeamPlan without changing the upstream workflow.

## 2. Minimal contract

A TeamPlan is one JSON object:

```json
{
  "schema_version": "1.0",
  "revision": 1,
  "supersedes_revision": null,
  "planning_source": "ad_hoc",
  "source_refs": [],
  "root_goal": "deliver the verified requested result",
  "units": [
    {
      "unit_id": "U1",
      "role": "reader",
      "goal": "trace the existing API contract",
      "output": "bounded evidence for Main",
      "depends_on": [],
      "ownership": {"write": [], "forbidden": []},
      "done_when": "the relevant call path and contract are evidenced"
    },
    {
      "unit_id": "U2",
      "role": "worker",
      "goal": "implement the already-decided bounded change",
      "output": "verified source changes",
      "depends_on": ["U1"],
      "ownership": {"write": ["src/example.py"], "forbidden": []},
      "done_when": "the change satisfies its acceptance checks"
    }
  ],
  "integration_owner": "main",
  "integration_order": ["U1", "U2"],
  "final_verification": "Main verifies the combined artifact against user acceptance",
  "revision_reason": "initial"
}
```

Each unit keeps exactly these coordination fields:

```text
unit_id
role
goal
output
depends_on
ownership
done_when
```

Allowed roles come from `policy.json`. `role` records the delegated Subagent role assigned by the router for that plan revision. TeamPlan does not define a `main` role and does not independently choose a role or model.

If Recovery later performs `main_takeover`, delegated execution for that unit ends and Main continues the stable responsibility. Recovery owns that execution-state transition; TeamPlan does not rewrite the unit to an invalid `role: main`.

TeamPlan does not duplicate the full child packet. The responsibility packet still carries intent, mutation authority, decision rights, interfaces, evidence, optional Handoff Capsule, current failure, and stop conditions.

## 2A. Semantic coverage stays with Main

The TeamPlan schema intentionally remains structural. Do not add a fixed requirement taxonomy, domain-specific flow fields, or a second planning ledger merely to encode semantic coverage.

Before dispatch and again before Candidate Ready, Main must establish that current task truth remains covered by the combination of:

```text
root_goal
planned delegated responsibilities
explicit Main-owned integration or verification responsibilities
final_verification
```

Every material obligation must remain owned somewhere in that combined responsibility graph. One obligation may span several units, and a cross-unit seam may remain Main-owned when no distinct child adds value.

A structurally valid TeamPlan can still be semantically incomplete. Valid IDs, an acyclic dependency graph, disjoint ownership, and a valid integration order do not prove that decomposition preserved user acceptance or that all material seams are covered.

If current task truth is already clear and decomposition drops a material obligation or seam, Main repairs the decomposition or ownership before continuing affected dispatch or claiming completion. That planning defect is not itself a `contract` blocker. Use `contract` only when semantic coverage cannot be closed because required task truth, scope, invariants, acceptance, or another semantic fact is missing, contradictory, or underspecified.

## 3. Dependency truth

`depends_on` is the machine-checkable structural dependency graph.

A unit is structurally ready only when all units named in `depends_on` have been accepted. Main still decides whether a structurally ready unit is worth delegating, semantically safe to run now, semantically ready for its actual input, and justified under current compute and authority boundaries.

Different files do not prove semantic independence. Shared APIs, schemas, migrations, lockfiles, generated artifacts, persistent state, external systems, or other shared interfaces remain Main-level semantic checks even when the validator sees disjoint paths.

Do not use integration order to hide an unresolved execution dependency. If a unit cannot make safe progress until another unit establishes missing semantics or evidence, that dependency belongs in `depends_on`.

A Handoff Capsule may carry already-accepted evidence across a dependency boundary, but it does not make an unresolved predecessor accepted and it does not replace `depends_on`.

A downstream responsibility that consumes an integrated artifact is not semantically ready merely because all predecessor units are accepted. Main must first materialize and verify that integrated artifact before dispatching a reviewer, verifier, or other consumer whose acceptance depends on it.

A taken-over unit becomes dependency-satisfied only after Main completes and accepts that same responsibility. The old child being stopped does not satisfy downstream dependencies by itself.

## 4. Ownership

`ownership.write` lists the relative paths the unit may own for source mutation when its responsibility packet separately grants `bounded-source-write` mutation authority.

`ownership.forbidden` lists relative paths the unit must not mutate.

Filesystem ownership does not create mutation authority. The responsibility packet remains the authorization source.

Read-only roles, as defined by `policy.json`, must not declare write ownership.

Units that are structurally ready at the same time must not declare overlapping write paths. If they would collide, add a real dependency, repartition ownership, or serialize the work.

During `main_takeover`, the unit's existing ownership scope can remain the scope of the stable responsibility. Main may act inside that scope only after Recovery has safely settled the old owner. If takeover also changes ownership paths or another structural fact, revise TeamPlan.

## 5. Integration

`integration_owner` is always `main`.

`integration_order` must contain every unit exactly once and must respect `depends_on`.

Completion order does not decide integration order. Main integrates accepted outputs in dependency-respecting order and verifies the resulting combined artifact.

Integration order is ordering truth only. It does not prove that a cross-unit semantic seam is complete or that an acceptance obligation spanning several outputs has been satisfied. Main verifies those relationships as part of semantic coverage closure.

## 6. Revision

Create a new TeamPlan revision only when coordination structure changes materially, including:

```text
delegated role assignment
dependency
ownership scope
deliverable
scope
acceptance
```

New evidence, a Handoff Capsule refresh, steering that stays within the same responsibility, a pure `main_takeover`, or an implementation detail does not require a revision by itself.

A delegated Agent role change requires a revision when TeamPlan is active; the router remains the authority that decides the new Agent role. `main_takeover` is a Recovery transition out of delegated execution and is not encoded as a new TeamPlan role.

Revision 1 uses `supersedes_revision: null`. Every later revision must point to the direct previous revision.

Keep the same `unit_id` across revisions only when the responsibility identity remains the same. `goal` and `output` therefore stay stable for that unit. A delegated role may change after blocker-driven rerouting, and ownership, dependencies, scope, or acceptance may be revised, without resetting responsibility identity. If the goal or output is materially split, replaced, or redefined, use a new unit ID. This keeps the recovery attempt budget bound to one stable responsibility instead of resetting it through plan revision.

Already-dispatched work remains bound to the plan truth it received. Do not silently rewrite a running responsibility. When a structural change affects active work, pause new dispatch, settle or safely invalidate the affected responsibility, then dispatch against the new revision.

### Material phase or authority transition

When an accepted deliverable contributes to a materially different later phase, promote only the Main-accepted task truth, decisions, constraints, and still-valid accepted evidence from that deliverable. The whole artifact does not automatically become trusted instructions.

Compile the later phase from current task truth instead of mutating the old TeamPlan into a different kind of work. If prior units would need materially different goals or outputs, they are new responsibilities and receive new unit IDs under the ordinary routing rules.

Choose the existing `planning_source` value that truthfully describes how the new TeamPlan itself was produced. Use `source_refs` to point at the accepted upstream artifact when a stable reference exists and that artifact materially informs the new phase. Do not invent a new planning-source taxonomy merely to label every prior deliverable type.

Still-valid evidence may be reused through normal packets or a Handoff Capsule. Prior readiness does not grant mutation authority, external-impact authorization, or broader scope to the later phase.

## 7. Validation

Before multi-responsibility dispatch, validate the plan:

```bash
python scripts/validate_team_plan.py /path/to/team-plan.json
```

The validator checks the exact schema shape, unit identity, delegated roles from `policy.json`, dependency validity and cycles, safe ownership paths, ready-layer write collisions, revision shape, and integration order.

When TeamPlan revisions are recorded in a recovery ledger, the ledger validator also rejects reuse of one `unit_id` for a changed goal or output.

The validator is intentionally structural. It does not infer natural-language user requirements, decide which obligations are material, prove end-to-end semantic coverage, or decide whether an integrated artifact is actually ready for a downstream responsibility. Those remain Main-level semantic checks under `routing.md`.

It intentionally does not impose standard/expanded team sizes, fixed waves, model routing, Provider routing, a `main` pseudo-role, or a private scheduler. Native Codex capacity remains the concurrency ceiling; Main still chooses the smallest useful active set.
