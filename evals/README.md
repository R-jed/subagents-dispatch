# Evaluation files

This folder contains test data used to check routing, coordination, recovery, interaction control, runtime behavior, and explicitly frozen live experiments. It is for maintainers and is not part of the normal user setup.

- `behavioral-workloads.json`: saved task shapes for repeated live behavioral tests. These are workload shapes, not benchmark claims.
- `behavioral-result.schema.json`: format used to store paired behavioral test results.
- `experiment-campaign.schema.json`: format for freezing either a fixed-role model/effort calibration or a real single-agent-versus-Dispatch product benchmark before expensive runs begin.
- `LOCAL_EVAL_FIXTURE_TEMPLATE.md`: template for freezing a local test case before comparing runs.
- `routing-cases.json`: static cases that catch routing regressions, including adaptive multi-Agent fan-out.
- `coordination-cases.json`: static cases for upstream workflow ownership, semantic independence, mutation authority, integration ordering, and requested/accepted/observed route truth.
- `interaction-cases.json`: static cases for Preview, one-shot Status, steering boundaries, safe Main takeover, compact Dispatch Receipts, and evidence-bound Handoff Capsules.
- `runtime-assurance-cases.json`: fixtures used by runtime-evidence tests.

`../scripts/validate-experiment-campaign.py` validates/freeze-hashes a campaign definition against the exact current plugin candidate. It does not run Agents, score results, or mutate `contracts/policy.json`.

For `role_calibration`, the current route control must match project policy and challengers may change model/effort while keeping the role's sandbox/isolation contract fixed. Each workload belongs to one calibration role.

For `product_benchmark`, the campaign compares ordinary `single_agent` with explicit `dispatch`. Workloads are classified by task stratum, not by a predeclared role; which project roles Dispatch actually materializes is result/runtime evidence.

Formal campaigns require repeated real-repository workloads and actual controlled fingerprints. Exploratory fixtures may use synthetic placeholders to test the evaluator itself, but those fixtures are not benchmark evidence.

The adaptive-routing checks cover both sides of the policy: several independent ready responsibilities may run together when useful, while duplicate, speculative, or low-value work stays out of the active team. The project does not use a fixed ordinary child-Agent count as the routing target.

The coordination cases protect parallel correctness after delegation. They check that subagents-dispatch preserves upstream workflow truth, does not confuse filesystem isolation with semantic independence, does not let a verification or read-only responsibility acquire source-write authority, respects explicit integration dependencies, and never relabels an accepted/configured route as an observed runtime route.

The interaction cases protect the user control surface without creating a second runtime. Preview must not spawn or mutate. Status is one-shot and preserves `UNKNOWN`. Steering cannot smuggle in a role/scope/authority change. Takeover must settle the old owner before Main assumes the responsibility, especially for writers. Receipts remain compact and factual. Handoff Capsules carry only Main-accepted evidence, become stale after relevant drift, and never grant write authority. When complete provenance would bloat a capsule, `contracts/evidence-artifact.md` keeps that evidence references-first and outside the conversational packet.

The adversarial interaction set also covers missing thread identity; `SPAWN_PENDING` no-match, single-match, and multiple-match reconciliation; corrupt capsules with active writers; targetless Steer with one or many eligible units; `INTERRUPTED` Takeover; `fix-first` without correction; retry versus semantic rework; locale persistence; unrelated dispatch with an unresolved writer; repeated Status deduplication; same-child resume; and requested/accepted/observed route mismatch. These cases are fixtures, not a second runtime policy.

Machine-checkable TeamPlan and recovery invariants are covered directly by `tests/test_team_plan.py` and `tests/test_recovery_policy.py`. Interaction and capsule invariants are bound by `tests/test_interaction_policy.py`. Runtime attestation has its own inspector/normalizer tests, and Experiment Plane campaign integrity is covered by `tests/test_experiment_campaign.py`.

These files do not control how the plugin routes or coordinates work. Live behavior is defined by the explicit Skills and the canonical files under `contracts/`, including `policy.json`, `routing.md`, `composition.md`, `interaction.md`, `state.md`, `receipt.md`, `team-plan.md`, `recovery.md`, `guardrails.md`, `handoff.md`, `evidence-artifact.md`, and `final-review.md`.

See [`../docs/behavioral-evals.md`](../docs/behavioral-evals.md) for the existing paired behavioral result protocol, [`../docs/experiment-protocol.md`](../docs/experiment-protocol.md) for role calibration, real product benchmarking, policy promotion, and public claim gates, and [`../docs/runtime-attestation.md`](../docs/runtime-attestation.md) for proving which model/effort/sandbox actually ran.
