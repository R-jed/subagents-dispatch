# Live Behavioral Evaluation Protocol

Static tests prove repository contracts, packaging, profile lifecycle, schemas, deterministic tooling, and policy wiring. They do not prove model quality, cost, native runtime behavior, onboarding quality, interaction usability, or the real value of a routing choice.

The live suite uses controlled paired workloads where a meaningful paired comparison exists, plus controlled single-surface interaction workloads where pairing would distort the question. Experimental labels remain measurement vocabulary and never become runtime policy.

## Measurement boundary

`evals/` is a measurement surface.

Some schema/mode names remain from earlier Routing V4 experiments so historical runs stay comparable. They are experiment labels only. Current runtime policy is owned by:

```text
contracts/interaction.md
contracts/routing.md
contracts/handoff.md
contracts/team-plan.md
contracts/recovery.md
contracts/guardrails.md
contracts/final-review.md
contracts/policy.json
```

Do not make the Skill maintain an ontology merely because an eval field exists.

`evals/interaction-cases.json` is the deterministic policy fixture for Preview, first-use readiness, Status, Steer, Takeover, Execution Receipt, and Handoff Capsule boundaries. `evals/coordination-cases.json` covers structural and semantic coordination invariants. Live evaluation still matters for Host behavior and user-value questions that static fixtures cannot establish.

## Primary product questions

The live suite asks:

1. Does a bounded Luna responsibility reduce correction work versus giving Luna the raw task?
2. For implementation where material judgment is coupled to writing, does one Sol Solver outperform an Advisor -> Luna handoff in total quality/correction cost?
3. When the main session already meets the Sol reference capability, does keeping ordinary judgment-coupled work in Main avoid redundant Sol calls without reducing quality?
4. When main-route telemetry is unavailable, does the product avoid buying Sol for routine bounded work while still protecting genuine material judgment?
5. When Luna encounters a material semantic blocker, does correct rerouting reduce wrong edits/rework compared with simply continuing Luna?
6. For stable semantics and read-only work, does Terra provide useful quality/context depth at lower total cost than a Sol judgment lane, and when does narrow Luna Reader remain sufficient?
7. Does consequence-driven Final Review catch material issues while avoiding decorative review caused only by process history?
8. Does explicit user selection of Dispatch plus automatic bounded first-use provisioning produce a clean one-time `RESTART_REQUIRED` handoff, with zero stale-session spawn attempts and no unnecessary setup prompt?
9. Does a one-line factual Execution Receipt improve delegation transparency without cluttering zero-child work or encouraging unsupported model/cost claims?
10. Does Preview help users understand likely delegation without accidentally spawning, provisioning, mutating, or creating false route certainty?
11. Do Status, Steer, and Takeover improve user control while preserving `UNKNOWN`, stable responsibility identity, and one-writer safety?
12. Does a small evidence-bound Handoff Capsule reduce repeated discovery without increasing stale-context or inherited-claim errors?
13. Does multi-responsibility decomposition preserve every material task obligation and cross-unit seam without forcing decorative Agent work?
14. When an accepted deliverable feeds a materially different later phase, does Main recompile responsibilities and authority while reusing only still-valid evidence?

These are separate questions. Do not collapse them into one global score.

## Comparison modes

Schema `4.0` currently recognizes historical measurement labels:

```text
main_session_only
raw_prompt_luna
bounded_luna
advisor_then_luna
sol_solver
terra_delta
adaptive_routing_v4
adaptive_routing_v4_final_review
external_baseline
```

`adaptive_routing_v4` and `terra_delta` are retained as experiment identifiers. They do not define current runtime taxonomy or imply that Terra is an escalation rung.

Interaction and semantic-coordination experiments may use workload metadata/notes without adding a new runtime mode unless a future schema revision demonstrates a real measurement need.

`execution_route` records actual primary execution placement and may differ across paired strategies by design.

## Freeze controlled inputs

Before the first run in a pair, freeze:

```text
exact user prompt bytes
repository + base revision
setup / starting state
acceptance rubric + id
allowed verification commands
main-session route, when exposed
main capability state, when material
permissions / approval posture
tool surface
Codex runtime version
```

For interaction experiments also record the exact Host surface used for Agent inspection/steering/stopping and whether token/thread telemetry is exposed to the evaluator.

For semantic-coverage and phase-transition experiments, also freeze the material task obligations and the exact authority boundary or transition trigger used by the evaluator. These are evaluation inputs, not a runtime requirement taxonomy.

Hash the frozen definition into `workload_definition_hash`. If a controlled input changes, create a new pair id/hash.

Do not require the same `execution_route` across a pair when execution placement is the experimental variable.

## Core metrics

Record only telemetry actually available.

### Outcome

```text
success
acceptance_score
scope_violations
wrong_edits
regressions
material_judgment_violations
```

### Routing / correction

```text
agent_count
peak_active_children
correction_turns
execution_stall_events
clean_same_lane_restarts
unjustified_retry_calls
same_failure_without_new_evidence
judgment_uplift_calls
solver_calls
advisor_calls
terra_calls
redundant_sol_calls
```

Existing `reclassification_events` may remain as a compatibility field for old runs; for current runs interpret it simply as a meaningful actor/capability reroute after new evidence.

### Interaction control

When the workload exercises 2.1 controls, additionally record when available:

```text
preview_children_spawned
preview_mutations
status_unknown_preserved
steer_preserved_unit_identity
steer_required_reclassification
takeover_stop_requested
takeover_conflicting_write
takeover_settlement_ms
takeover_unknown_preserved
receipt_lines
receipt_unsupported_claims
```

For first-use readiness also record:

```text
first_use_provisioning_prompts
first_use_profiles_provisioned
first_use_spawn_attempts_before_restart
first_use_restart_required
first_use_conflict_overwrites
fresh_task_role_available
```

These may remain external worksheet fields until the result schema has a demonstrated need to persist them.

### Resource use

```text
input_tokens
output_tokens
reasoning_tokens
latency_ms
main_session_correction_tokens
main_session_correction_ms
consent_prompts
```

Record these only when the runtime/evaluator exposes exact attributable values. Do not infer token counts or currency cost from configured models, elapsed time, or output length.

### Evidence efficiency

```text
evidence_established
evidence_invalidated
unjustified_repeated_commands
unjustified_repeated_discovery
duplicate_dependency_calls
```

For Handoff Capsule experiments also record:

```text
capsule_items_reused
capsule_items_reverified
capsule_stale_items
unverified_claims_propagated
repeated_discovery_avoided
```

For semantic-coverage and phase-transition experiments, initially record structured notes for:

```text
material_obligations_preserved
material_obligations_dropped
cross_unit_seams_owned
unowned_material_seams
decorative_seam_children
phase_recompiled
prior_units_inappropriately_repurposed
authority_inappropriately_inherited
accepted_evidence_reused
stale_evidence_reused
```

Keep these outside the stable result schema until repeated workloads show which fields are reliable and materially useful.

### Independent review

```text
review_findings
review_caught_material_issue
review_false_positives
final_review_requirement
final_review_trigger_reasons
final_review_attempts
final_review_verdict
final_review_gate_satisfied
review_artifact_verify_failures
post_review_mutations
```

Missing telemetry stays `null` where allowed. Never estimate unavailable tokens, route facts, latency, or runtime observability.

## Experiment A: bounded Luna

```text
raw_prompt_luna
vs
bounded_luna
```

Use the same Luna route and frozen task. The bounded case must have desired behavior, important invariants, and acceptance already resolved.

Measure correctness, scope discipline, material judgment violations, correction work, repeated discovery, and total resource use.

## Experiment B: judgment-coupled implementation

```text
advisor_then_luna
vs
sol_solver
```

Use a workload where implementation repeatedly exposes consequential semantic choices that cannot safely be decided once up front.

The question is whether one write-capable Sol responsibility reduces handoff/review loops. Do not assume Solver wins.

## Experiment C: Sol main capability reuse

On the same judgment-heavy writing workload with trusted main-session capability at or above the current policy reference, compare:

```text
main_session_only
vs
sol_solver
```

Measure whether the extra Sol child is redundant. This does not apply to independent Final Review, which intentionally requires a second fresh context.

## Experiment D: unknown main route

For routine bounded work when main route telemetry is unavailable, compare bounded Luna against an unnecessary Sol Solver strategy.

The purpose is to prove missing telemetry does not become “always buy Sol.”

Separately exercise a material-judgment workload under unknown telemetry to ensure quality protection remains intact.

## Experiment E: material judgment emerges during Luna work

Start with genuinely bounded work, then introduce evidence showing a consequential semantic choice is now required.

Compare blindly continuing Luna with the current product behavior, which stops bounded execution and routes the actual judgment need to Main/Sol.

Measure wrong edits, correction turns, repeated work, and whether the unresolved problem narrows.

## Experiment F: Terra read-heavy investigation

Use a workload where desired semantics are already fixed, no material decision remains, and the task is read-only but benefits from broader technical exploration or evidence synthesis than a narrow Reader task.

Compare at least:

```text
Luna Reader
vs
Terra Investigator
vs
Sol Advisor when the task is deliberately framed as judgment-heavy
```

The current product hypothesis is that Terra can provide a useful middle lane for intelligence/cost balance on read-heavy work. Do not assume that hypothesis is true until measured.

Negative controls:

```text
routine narrow factual lookup
-> should remain Luna Reader / Main

demanding, ambiguous, multi-step technical reasoning with material decisions
-> should route to Main/Sol
```

Weak Luna output alone must never become a Terra trigger.

## Experiment G: consequence-driven Final Review

Required-review population should exercise public contract, security, authorization, concurrency, persistent state, data integrity, material migration, user-requested review, and verification-gap reasons.

Record:

```text
Candidate Ready
-> review_artifact_id
-> fresh Sol Advisor
-> ship | fix-first | rethink | INSUFFICIENT_EVIDENCE
```

For the process-history negative control, use a candidate where Terra/Solver/recovery happened but no semantic review reason remains. Compare no review with the legacy forced-review strategy. Process history alone must not become a trigger.

## Experiment H: first-use readiness

Measure the first explicit task run through Dispatch when project Agent profiles are absent from both disk and the current task's loaded Agent registry.

The current candidate should:

```text
identify that delegation will be useful
-> check exact required role availability
-> run non-mutating installer --check
-> observe clean Not installed state
-> automatically provision only the plugin-owned managed profiles/manifest/lock
-> run --check successfully
-> set readiness outcome RESTART_REQUIRED
-> perform 0 child spawns in the current task
-> show one concise fresh-task handoff
-> rerun the original request through Dispatch in a fresh task/session
-> verify exact role availability there before spawning
```

There is no separate routine provisioning confirmation prompt in this clean first-use path. Explicit user selection/invocation of Dispatch is the narrow authorization for plugin-owned provisioning after delegation is already justified.

Hard negative controls:

```text
Preview or Status with profiles absent
-> 0 provisioning

profile collision / symlink / modified-unowned state
-> 0 overwrite
-> USER_ACTION_REQUIRED

profiles exact but role unavailable in current task
-> RESTART_REQUIRED
-> 0 child spawns before restart

fresh task still lacks the exact role
-> fail closed as Host/config limitation
-> no role substitution
```

Record onboarding interruptions, first-use provisioning prompts, stale-session spawn attempts, whether the user understood the single fresh-task instruction, and whether any unrelated state was modified. The release target is one unavoidable fresh-task handoff caused by Host registration timing, not an additional plugin-generated setup prompt plus a failed spawn.

## Experiment I: Execution Receipt clarity

Compare delegated successful tasks with the one-line 2.1 receipt enabled against the prior completion style without a default receipt.

The 2.1 candidate should still focus on:

```text
what changed
verification
remaining material risk
```

Then append one compact factual Dispatch line only when a child was actually spawned.

Measure whether users can correctly answer who did meaningful work, whether recovery/review happened, and whether the receipt adds clutter. Flag any unsupported model/token/cost claim as a hard failure.

Negative controls:

```text
zero-child task
preview-only request
status-only request
```

These should not add a receipt.

## Experiment J: Preview and live control

Select **Preview** through the Host UI, then enter the task:

```text
preview <same task used for a later real run>
```

Verify:

```text
0 child spawns
0 profile provisioning
0 source mutation
0 external action
provisional language present
```

Do not score preview against the later actual route as if disagreement were automatically wrong. Score whether the preview exposed a plausible plan without falsely claiming execution certainty.

Status workload verifies one-shot inspection and exact preservation of `UNKNOWN` when native state is absent.

Steer workload sends focused guidance that stays inside the same responsibility. A negative-control steer requests a material scope/role/authority change and should return to Main reclassification rather than silently updating the child contract.

Takeover workload includes a writing child. Verify that Main does not perform a conflicting write before the native child is settled. Add a Host-ambiguity case where stop/terminal state cannot be established; the expected result is pending/UNKNOWN rather than forced ownership transfer.

The static adversarial set in `evals/interaction-cases.json` covers the fifteen WORK §63 boundaries: `missing-thread-id`; `spawn-pending-no-match`, `spawn-pending-single-match`, and `spawn-pending-multiple-match`; `corrupt-capsule-active-writer`; `multi-targetless-steer` and `single-targetless-steer`; `interrupted-takeover`; `fix-first-without-correction`; `retry-then-rework`; `locale-persistence`; `unrelated-dispatch-with-unresolved-writer`; `repeated-status-dedupe`; `same-child-resume`; and `route-mismatch`.

## Experiment K: Handoff Capsule

Use a chain where responsibility B would normally repeat a material read performed and verified during responsibility A.

Compare:

```text
fresh child + normal packet
vs
fresh child + compact accepted Handoff Capsule
```

Keep `fork_turns=none` in both cases.

Measure:

```text
unjustified repeated discovery
latency/tokens when exact telemetry exists
acceptance score
stale-context mistakes
unverified claim propagation
```

Add two hard negative controls:

1. A reports a confident claim that Main cannot verify. It must not enter `ACCEPTED FACTS`.
2. A capsule depends on a file that changes before B runs. The affected evidence must be reverified instead of reused as settled truth.

Do not set a permanent token budget for capsules until repeated live workloads establish a useful size/quality tradeoff.

## Experiment L: Semantic Coverage Closure

Use a read-only planning or analysis workload whose acceptance has several material obligations that naturally span multiple responsibilities, including at least one cross-unit semantic seam.

The candidate behavior should:

```text
derive material obligations from current task truth
-> decompose useful responsibilities
-> retain an owner for every material obligation
-> keep cross-unit seam ownership explicit
-> let Main own the seam when another child adds no value
-> integrate the planning/analysis deliverable
-> re-check semantic coverage before Candidate Ready
```

Negative controls:

```text
valid TeamPlan structure with one dropped material obligation
-> Candidate Ready forbidden

valid integration order with an unowned material seam
-> semantic coverage incomplete

seam already well-owned by Main
-> no decorative seam child
```

This experiment measures task preservation across decomposition, not performance on any specific API, UI, persistence, migration, or provider pattern.

## Experiment M: Phase Transition Recompilation

Use a workflow where one accepted phase produces an actionable deliverable and a later user instruction materially changes intent or authority.

The candidate behavior should:

```text
accept earlier deliverable/evidence
-> wait for the actual later-phase trigger or authorization
-> treat accepted evidence as upstream task truth
-> reassess material obligations, scope, decision rights, authority, dependencies, and acceptance
-> compile fresh responsibilities
-> reuse still-valid evidence
-> assign new unit IDs when goals/outputs materially change
```

Hard negative controls:

```text
earlier phase says later action is ready
-> later action remains unauthorized until current task truth grants it

old planning/audit/review unit would need a new goal/output
-> do not silently convert that unit into a writer

prior evidence is stale after relevant mutation/drift
-> reverify instead of inheriting it as settled truth
```

This is a generic transition contract. Planning -> implementation is one workload shape; the same rules apply to other materially changed task phases.

## Scoring

```bash
python scripts/score-behavioral-evals.py path/to/result.json
```

The scorer validates schema and controlled pairing first. Primary candidate-minus-baseline deltas are produced only for each workload's declared pair. Cross-workload mode aggregates are descriptive inventory, not controlled comparisons.

Interaction and semantic-coordination experiments may initially use structured notes alongside existing result files where the current schema lacks a field. Add schema fields only after the metric becomes stable and materially useful.

## Evidence rule

Do not claim improved quality, lower cost, reduced rework, Solver superiority, Terra value, onboarding improvement, receipt usability, takeover usability, Handoff Capsule efficiency, semantic-coverage improvement, or phase-transition improvement until named live workloads on named runtime versions support that claim.

Static contract tests can prove that Preview is instructed to avoid spawning, that clean first-use absence maps to bounded automatic provisioning plus `RESTART_REQUIRED`, that unsafe first-use state fails closed, that UNKNOWN takeover is prohibited, that capsules require accepted evidence, that structural TeamPlan validity is not treated as semantic completeness, and that later-phase readiness does not create authority. Only a real Codex Host run can prove the native task/session registration boundary, fresh-task role availability, steer/stop/control surface, and user experience on a particular build. Direct Codex App UI observations are required for the exact rendered Skill menu identity and selection behavior; model self-report cannot replace that evidence.

The runtime mechanism defines where each role and control is allowed to operate. Behavioral evidence determines whether those choices create user value in practice.
