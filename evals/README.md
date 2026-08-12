# Evaluation files

This folder contains test data used to check routing, coordination, recovery, interaction control, runtime behavior, and explicitly frozen live experiments. It is for maintainers and is not part of the normal user setup.

- `behavioral-workloads.json`: saved task shapes for repeated live behavioral tests. These are workload shapes, not benchmark claims.
- `behavioral-result.schema.json`: format used to store paired behavioral test results.
- `experiment-campaign.schema.json`: format for freezing either a fixed-role model/effort calibration or a real single-agent-versus-Dispatch product benchmark before expensive runs begin.
- `experiment-run.schema.json`: campaign-bound fact envelope for one actual experiment run. It records attested inputs, child materialization, execution/oracle refs, route evidence, and only directly attributable measurements; it does not score or aggregate a campaign.
- `LOCAL_EVAL_FIXTURE_TEMPLATE.md`: template for freezing a local test case before comparing runs.
- `routing-cases.json`: static cases that catch routing regressions, including adaptive multi-Agent fan-out.
- `coordination-cases.json`: static cases for upstream workflow ownership, semantic independence, mutation authority, integration ordering, and requested/accepted/observed route truth.
- `interaction-cases.json`: static cases for Preview, one-shot Status, steering boundaries, safe Main takeover, compact Dispatch Receipts, and evidence-bound Handoff Capsules.
- `runtime-assurance-cases.json`: fixtures used by runtime-evidence tests.

`../scripts/validate-experiment-campaign.py` validates/freeze-hashes a campaign definition against the exact current plugin candidate. It does not run Agents, score results, or mutate `contracts/policy.json`.

Reader-only route calibration profiles are evaluator-owned artifacts materialized in the confirmed active normal Codex home. Claim an empty evaluator root with `../scripts/calibration_profiles.py init`, freeze the campaign with one Reader control, one Terra XHigh challenger, and one provider control, then use `create|check|cleanup` with the marker, exact Host-home evidence, and the validated campaign. Host-home evidence binds the preparation task to its SHA-256-frozen Host rollout under `<normal-codex-home>/sessions`; a caller-authored home assertion alone is rejected. Creation never edits the frozen campaign or `config.toml`. The helper derives TOML from the canonical Reader profile, journals ownership outside Host discovery, stages each profile under `agents/` with a non-`.toml` name, and returns `NEW TASK REQUIRED: YES`. Execution requires a distinct fresh task with `fork_turns=none`; a full App restart is not required. Run evidence binds the Host-observed `agent_path` and `model_provider` to the exact committed manifest path, current profile SHA-256, and frozen provider before the model/effort claim is eligible.

`../scripts/validate-experiment-run.py` validates one run against that already-validated campaign. It checks campaign/candidate/workload/arm identity, actual input attestation, materialized-child completeness, child route evidence, oracle/result provenance, and measurement provenance. It does not run Codex, rank routes, aggregate results, or change policy.

The campaign/run boundary follows the same truth discipline as runtime attestation. Each campaign also binds a typed claim kind: role calibration is `model_effort`, product benchmark is `product_behavior`, and neither may be relabeled as a Host permission-source claim.

```text
campaign expected input
-> run observed input + evidence ref
-> verified | unknown | failed
```

A run cannot prove that it used the frozen plugin state, Host, repository revision, task bytes, reset procedure, acceptance contract, Main route, permission envelope, tool surface, or project rules merely by copying those values from the campaign. `experiment-run.schema.json` records the actual observation and a provenance ref, and `validate-experiment-run.py` derives `input_assurance`. Missing observations remain `unknown`; observed drift remains `failed`. Both stay in the evidence record rather than being discarded.

For `product_benchmark`, plugin state is part of the controlled input. The `single_agent` baseline must independently attest that subagents-dispatch is absent, while the `dispatch` arm must attest the exact campaign candidate SHA. This prevents a baseline that accidentally loaded the plugin from being treated as a clean baseline. Each run also attests canonical hashes of the frozen reset procedure and acceptance contract, so environment-reset or oracle drift cannot be silently attributed to Dispatch.

For `role_calibration`, the current route control must match project policy and challengers may change model/effort while keeping the role's sandbox/isolation contract fixed. Each workload belongs to one calibration role. The frozen workload also binds `responsibility_packet_sha256` plus an evaluator-owned packet ref, and each run attests the packet hash actually used. This prevents a packet change from being misattributed to the model/effort challenger.

For `product_benchmark`, the campaign compares ordinary `single_agent` with explicit `dispatch`. Workloads are classified by task stratum, not by a predeclared role; which project roles Dispatch actually materializes is result/runtime evidence. A valid Dispatch run may materialize zero project children. Zero-child is never inferred from an empty `child_routes` array alone: the run must carry an observed project-child count plus provenance, and that count must equal the number of route rows. A `single_agent` run must prove an observed project-child count of zero. Product-benchmark input must not freeze a delegated responsibility packet because Dispatch decomposition is part of the behavior under test.

If the Host cannot establish the complete materialized child set for a product run, `child_materialization.status` is `unavailable`, the run is retained, and `route_assurance` remains `unknown`. It cannot be relabeled as zero-child or used to claim complete route coverage. Role calibration requires an observed count of exactly one materialized project child.

Child route evidence uses only actual runtime sources accepted by the Runtime Attestation protocol (`native`, exact-rollout `local`, or `both`). Configured values and model self-report are not observed evidence. `evidence_source=none` requires all Observed route fields to remain null. A route with missing required observation stays `unknown`; a route mismatch is recorded as `failed` rather than silently substituted.

Measurements use an explicit status per field:

```text
observed       -> exact non-negative value + provenance ref
unavailable    -> null value/ref; do not estimate
not_applicable -> null value/ref because the measure does not apply
```

Reported Main and child token totals are reconciled into the aggregate only when those exact totals are actually observed. If child materialization itself is unavailable, child token usage cannot be marked `not_applicable`. Response length, configured model names, or elapsed wall time must not be converted into guessed token/cost values.

Execution and acceptance are also separate facts. A failed, interrupted, or unknown execution cannot claim `acceptance_status=passed`. A completed run may still fail its oracle, and failed/UNKNOWN runs stay in the evidence record rather than disappearing from the campaign history.

Formal campaigns require repeated real-repository workloads and actual controlled fingerprints. Exploratory fixtures may use synthetic placeholders to test the evaluator itself, but those fixtures are not benchmark evidence. Failed, interrupted, input-drifted, materialization-UNKNOWN, or route-UNKNOWN runs remain evidence records; they cannot be erased merely to improve an aggregate.

The adaptive-routing checks cover both sides of the policy: several independent ready responsibilities may run together when useful, while duplicate, speculative, or low-value work stays out of the active team. The project does not use a fixed ordinary child-Agent count as the routing target.

The coordination cases protect parallel correctness after delegation. They check that subagents-dispatch preserves upstream workflow truth, does not confuse filesystem isolation with semantic independence, does not let a verification or read-only responsibility acquire source-write authority, respects explicit integration dependencies, and never relabels an accepted/configured route as an observed runtime route.

The interaction cases protect the user control surface without creating a second runtime. Preview must not spawn or mutate. Status is one-shot and preserves `UNKNOWN`. Steering cannot smuggle in a role/scope/authority change. Takeover must settle the old owner before Main assumes the responsibility, especially for writers. Receipts remain compact and factual. Handoff Capsules carry only Main-accepted evidence, become stale after relevant drift, and never grant write authority. When complete provenance would bloat a capsule, `contracts/evidence-artifact.md` keeps that evidence references-first and outside the conversational packet.

The adversarial interaction set also covers missing thread identity; `SPAWN_PENDING` no-match, single-match, and multiple-match reconciliation; corrupt capsules with active writers; targetless Steer with one or many eligible units; `INTERRUPTED` Takeover; `fix-first` without correction; retry versus semantic rework; locale persistence; unrelated dispatch with an unresolved writer; repeated Status deduplication; same-child resume; and requested/accepted/observed route mismatch. These cases are fixtures, not a second runtime policy.

Machine-checkable TeamPlan and recovery invariants are covered directly by `tests/test_team_plan.py` and `tests/test_recovery_policy.py`. Interaction and capsule invariants are bound by `tests/test_interaction_policy.py`. Runtime attestation has its own inspector/normalizer tests. Experiment campaign and per-run evidence integrity are covered by `tests/test_experiment_campaign.py` and `tests/test_experiment_run.py`.

These files do not control how the plugin routes or coordinates work. Live behavior is defined by the explicit Skills and the canonical files under `contracts/`, including `policy.json`, `routing.md`, `composition.md`, `interaction.md`, `state.md`, `receipt.md`, `team-plan.md`, `recovery.md`, `guardrails.md`, `handoff.md`, `evidence-artifact.md`, and `final-review.md`.

See [`../docs/behavioral-evals.md`](../docs/behavioral-evals.md) for the existing paired behavioral result protocol, [`../docs/experiment-protocol.md`](../docs/experiment-protocol.md) for role calibration, real product benchmarking, policy promotion, and public claim gates, and [`../docs/runtime-attestation.md`](../docs/runtime-attestation.md) for proving which model/effort/sandbox actually ran.
