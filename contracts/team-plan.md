# TeamPlan Compatibility

V4 Native Core has no independent TeamPlan runtime authority.

WorkGraph and WorkUnit are the only responsibility-structure truth for one or many delegated responsibilities. They own dependencies, ownership boundaries, readiness, and acceptance structure. Main owns semantic decomposition, dispatch judgment, integration, and final acceptance.

The state field `team_plan_revision` may remain temporarily during the V4 RC as a compatibility marker for earlier call shapes and experimental state. It must not:

- authorize or block a fresh ExecutionBinding;
- limit a WorkGraph to one WorkUnit when null;
- gate dependencies or ready-frontier calculation;
- select a Profile or route work;
- define integration order;
- create a retry budget;
- override WorkUnit responsibility or acceptance truth.

`scripts/validate_team_plan.py` is compatibility tooling for historical inputs. Runtime code must not require a TeamPlan document or revision before executing a valid ready WorkUnit.

New V4 WorkGraphs keep `team_plan_revision = null`. Existing pre-release capsules carrying a positive compatibility value may still validate when their remaining state is otherwise legal, but the value has no planning semantics.

If a WorkUnit goal, output, ownership, scope, authority, or acceptance meaning materially changes after execution begins, Main creates or re-evaluates WorkUnit responsibility directly. Incrementing a TeamPlan revision is not a recovery mechanism.
