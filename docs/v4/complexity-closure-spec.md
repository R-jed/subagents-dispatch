# V4 Complexity Closure Specification

This specification freezes the bounded P0/P1 simplification pass that must complete before the real H00-H20 Host campaign.

The starting candidate is commit `7ec4b2aff380b0920078a8a5e98fe084a01212dd` on `v4/rc4-host-contract-closure`.

## Goal

Remove competing V3/V4 contract owners and unnecessary single-responsibility ceremony while preserving the V4 safety objects that already have concrete correctness value.

The pass must keep one runtime, one scheduler/admission owner, one canonical workspace writer boundary, one Host lifecycle truth path, and the five fixed managed Agent profiles.

## Non-goals

This pass must not:

- extract a new state-storage module;
- merge facade/core implementation pairs;
- reduce WriterLease identity or settlement rules;
- remove PendingControl payload, tool-use, control-epoch, lease-epoch, or writer-effect bindings;
- merge the five physical Agent profiles;
- create a second single-delegate runtime or scheduler;
- remove V3 migration/compatibility code that still has a current production consumer;
- activate staged V4 production Hooks;
- claim any H00-H20 Host result.

## P0-A: Active V4 contract closure

The current Orchestrate reasoning path may load only contracts whose current semantics agree with the V4 runtime.

Required ownership:

- `policy.json`: machine profile and review policy;
- `routing.md`: delegation value, capability selection, responsibility semantics, coverage and routing decisions;
- `responsibility-packet.md`: the only responsibility serialization contract;
- `team-plan.md`: multi-responsibility structural dependency/integration truth only;
- `interaction.md`: current Orchestrate controls;
- `recovery.md`: current WorkUnit/ExecutionBinding recovery semantics;
- `final-review.md`: current exact-candidate independent review semantics.

Supporting root contracts may remain current V4 support material when referenced by those owners. Historical V3 state/receipt material must be clearly labeled historical or removed from the active Orchestrate dependency chain.

`docs/architecture.md` and `docs/repository-architecture.md` must describe the same two-Skill product and current owner map. Public Doctor must not own release-campaign/H00-H20 readiness. `final-review.md` must refer to Orchestrate, not the retired Dispatch Skill.

## P0-B: One canonical responsibility record

There must be one responsibility schema across reasoning and Host payload construction.

`routing.md` owns semantic requirements only. It must not define a second packet template.

`responsibility-packet.md` owns one canonical structured record with five top-level sections:

- `objective`
- `ownership`
- `interfaces`
- `constraints`
- `verification`

`managed_execution_v4.py` implements that record and renders the exact JSON Host `message`. Identity fields that already exist in runtime state may be included inside the five sections; they do not create another schema.

The Host message remains deterministic JSON with stable key ordering and continues to bind exact `agent_type`, `task_name`, and `fork_turns: none` through the existing managed execution and PendingControl path.

## P0-C: Real single-delegate path

A single delegated responsibility with no delegated dependency must be executable with `team_plan_revision = null`.

The path remains inside the current V4 runtime:

1. create V4 state;
2. install exactly one WorkUnit without TeamPlan;
3. allocate one ExecutionBinding;
4. reserve WriterLease only for a writable execution;
5. prepare and consume the same PendingControl;
6. use the same managed Host payload and lifecycle acknowledgement path;
7. use the same scheduler/admission owner when admission/capacity evaluation is needed.

`work_graph_v4.py` may expose a narrow `install_single_work_unit` helper. It must reject dependencies, a second WorkUnit, an existing execution, an existing WriterLease, or an unresolved PendingControl.

`allocate_execution()` may accept `team_plan_revision = null` only when the persisted state contains exactly one dependency-free WorkUnit. Multi-responsibility execution continues to require a positive TeamPlan revision.

No second state schema, scheduler, lifecycle helper family, or writer path may be introduced.

## P1-A: Canonical profile policy projection

`contracts/policy.json` remains the machine source of truth for profile identity.

`scripts/policy.py` must validate and expose a narrow canonical projection containing, per role:

- `profile_file`
- `agent_type`
- `model`
- `effort`
- `mutation_authority`
- optional `sandbox_mode`

It must also expose the semantic lane needed by Orchestrate without owning routing behavior.

Runtime consumers must stop maintaining independent model/effort/agent-type copies when the same value already exists in policy. Consumer-specific behavior, Host observations, scheduler decisions and recovery semantics remain outside `policy.py`.

## P1-B: Runtime integrity boundary

Package integrity must stop treating every file under `scripts/` as an installed runtime requirement.

The integrity generator must use an explicit allowlist for product/runtime scripts. Confirmed maintainer-only files must be excluded from the full runtime integrity profile:

- `scripts/calibration_profile_contract.py`
- `scripts/calibration_profiles.py`
- `scripts/calibration_profiles_core.py`
- `scripts/release_evidence_v4.py`
- `scripts/score-behavioral-evals.py`
- `scripts/validate-experiment-campaign.py`
- `scripts/validate-experiment-run.py`
- `scripts/validate_experiment_campaign_core.py`

This change narrows the integrity, Doctor and update-verification surface. It does not by itself claim that Codex physically omits those files from the installed Plugin directory.

All scripts with a current product, Hook, Doctor, update, migration, review, routing, lifecycle or runtime-evidence consumer remain covered until separate consumer proof supports removal.

## Red-test matrix

| ID | Old candidate must fail because | Required test | Passing condition after change |
| --- | --- | --- | --- |
| R1 | `allocate_execution()` rejects `team_plan_revision=None` | create one dependency-free WorkUnit without TeamPlan and allocate Reader execution | allocation succeeds and persisted ExecutionBinding keeps `team_plan_revision=None` |
| R2 | same rejection blocks writer fast path | create one writable WorkUnit without TeamPlan and allocate Worker execution | WriterLease is atomically `RESERVED` and execution keeps null TeamPlan revision |
| R3 | no deterministic helper installs one WorkUnit without TeamPlan | call `install_single_work_unit` on empty state | one READY unit is installed and top-level revision remains null |
| R4 | a dependency could accidentally masquerade as single path if only allocator check is removed | attempt single installation with `depends_on` | fail closed |
| R5 | responsibility docs and Host JSON are independent representations | inspect `assignment_packet()` | exact five top-level section keys are emitted and contain runtime identity/authority/acceptance facts |
| R6 | `routing.md` still publishes a second long packet template | contract text check | routing delegates serialization ownership exclusively to `responsibility-packet.md` and does not contain the old packet field list |
| R7 | runtime keeps independent profile maps | compare policy projection with state/orchestrate/managed execution | model, effort, authority and agent type all derive from validated policy projection |
| R8 | whole `scripts/` directory is integrity-scoped | inspect `runtime_files()` | listed maintainer-only tools are absent while required runtime/Hook/Doctor/update scripts remain present |
| R9 | stale product vocabulary remains in active contracts | contract scan | no retired `Dispatch` Skill consent wording in final-review; architecture and Doctor ownership agree |
| R10 | stale recovery vocabulary can guide current Orchestrate | recovery contract scan | current recovery uses WorkUnit/ExecutionBinding, `execution_id`, `attempt_no`, current V4 lifecycle set, and no V3 state capsule owner claim |

## Regression requirements

The change is acceptable only if all existing safety behavior remains covered, including:

- two fresh attempts maximum per unchanged WorkUnit;
- one focused same-child follow-up budget;
- exact managed `agent_type` and `fork_turns: none`;
- WriterLease single-writer blocking and UNKNOWN fail-closed behavior;
- PendingControl Pre/Post exact binding;
- dependency unlock only after WorkUnit acceptance;
- current five-profile model/effort/sandbox contract;
- production compatibility Hook remains unchanged before Host cutover;
- Doctor remains five product layers;
- V3 migration remains explicit and fail closed.

## Verification order

1. Add the red tests and confirm their failures are explained by the frozen old candidate behavior.
2. Implement P0 contract ownership and single-delegate changes.
3. Run targeted P0 tests.
4. Implement P1 policy projection and runtime integrity allowlist.
5. Run targeted P1 tests.
6. Refresh package integrity only after runtime-file identity is final.
7. Run Ruff, full pytest, managed Agent lifecycle checks and official Plugin validation through the repository CI matrix.
8. Review the final diff against this specification and verify that no non-goal was introduced.
9. Freeze the resulting exact candidate for the real H00-H20 campaign.
