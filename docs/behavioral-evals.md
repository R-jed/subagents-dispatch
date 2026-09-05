# Behavioral Evaluation

This document describes maintainer-only paired behavioral measurement for the current
three-role subagents-dispatch product. It does not define runtime policy and cannot
promote a route, authorize a release, or create a Host capability claim.

Production truth remains in `contracts/policy.json`, the Orchestrate/Doctor Skills, and
the Native Core contracts. The behavioral registry and result schema live under
`evals/`.

## Current production roles

| Role | Production route | Responsibility boundary |
| --- | --- | --- |
| Programmer | `gpt-5.6-luna / max` | bounded factual inspection or implementation after material behavior/decisions are settled |
| Product Manager | `gpt-5.6-sol / medium` or `high` | synthesis, routing checks, material decisions, judgment-coupled implementation, Standard Review |
| Department Director | `gpt-6-astra / high` | fresh highest-consequence exact-candidate acceptance review |

Model and reasoning effort are requested explicitly at managed spawn. Canonical role
profiles provide semantic instructions and leaf posture; they are not the model/effort
authority.

Main remains Main. Main model/effort is not compared with managed routes to decide
whether a required responsibility should exist. A recorded `main_session_route` is an
experiment control only.

## What behavioral evaluation is for

The current live workloads answer bounded product questions rather than trying to
derive a universal model ranking:

1. Does a bounded Programmer responsibility reduce Main context/rework versus an
   otherwise comparable direct execution arm?
2. Does Product Manager involvement improve tasks with genuine decision or synthesis
   obligations without becoming decorative delegation?
3. Does Product Manager Medium remain adequate for local/reversible judgment, while
   High is reserved for the policy-defined material triggers?
4. For judgment-coupled implementation, does one Product Manager execution outperform
   an unnecessary decision-to-Programmer handoff when judgment truly remains coupled to
   writing?
5. Does Standard Review catch material issues at an acceptable false-positive and
   correction cost?
6. Do highest-consequence candidates receive Department Director review only when a
   highest trigger is present, without stacking a redundant Standard Review underneath?
7. Does useful read-only fanout improve evidence latency without violating the four-child
   ceiling, WriterLease rules, or current workspace mutation guard?
8. Do Status, Steer, Continue, Correction, Takeover, UNKNOWN handling, and fresh-context
   handoff preserve the Native Core ownership model under realistic interruption and
   recovery conditions?

The evaluation system does not ask whether a strong Main can suppress Product Manager
or Department Director. Parent capability deduplication is not part of the current
product.

## Frozen workload registry

`evals/behavioral-workloads.json` freezes named live workload shapes. The registry is
not a result file and contains no product-performance claims.

Current workload families include:

```text
bounded implementation
material decision and judgment-coupled implementation
cross-path read synthesis
decision reclassification after new evidence
Standard Review admission and invalidation
highest-consequence review admission
independent read fanout under the product ceiling
execution stall and evidence-gated restart
duplicate-responsibility suppression
semantic-coverage planning
phase-transition recompilation
Orchestrate Preview / Status / Steer / Takeover
fresh-context Handoff evidence
compact factual execution receipts
```

Process history alone is not a review trigger. File count, task size, retry count, spare
capacity, prior Product Manager use, or Main model identity are not reasons to invoke a
stronger managed route.

## Pair construction

A primary comparison is meaningful only when the pair freezes the same executable task
and controls all non-experimental inputs that could materially affect the result.

At minimum freeze:

```text
workload_definition_hash
repository revision and starting state
exact task/prompt bytes
acceptance rubric
main_session_route as an environment control
permissions fingerprint
tool-surface fingerprint
Host/runtime version
```

The execution route or strategy may differ only when that difference is the declared
experimental variable. If another controlled input changes, create a new fixture/pair
rather than comparing unlike runs.

`evals/LOCAL_EVAL_FIXTURE_TEMPLATE.md` is the local freezing template.

## Current comparison modes

`evals/behavioral-result.schema.json` owns the accepted evaluator mode identifiers.
Some names, such as `raw_prompt_luna`, are evaluator arm labels rather than production
roles or public Skill names.

Representative current comparisons are:

```text
raw_prompt_luna
  vs bounded_programmer

product_manager_then_programmer
  vs product_manager_coupled

external_baseline
  vs product_manager_read_synthesis

managed_routing_v4
  vs managed_routing_v4_standard_review
```

Highest Review is consequence-gated. Do not create an Astra comparison arm merely to
measure whether a more expensive model produces a nicer answer on an ordinary task.

## Runtime route evidence

Configured/requested/accepted/observed truth stays separate. A run may claim an observed
child route only from supported Host-produced evidence.

For every materialized managed child, record when available:

```text
role / agent_type
requested model and reasoning effort
Host-accepted model/effort when exposed
Host-observed model/effort
effective permission state
model provider when material
evidence source / ref
```

Child prose, profile filenames, configured values, or copied expected fields never count
as Observed evidence. Missing required evidence remains unknown; conflicting evidence is
failed/quarantined.

`scripts/runtime-evidence.py` is child-attestation tooling only. Main model/effort is not
a managed routing authority and has no capability-coverage result in the current design.

## Core metrics

The scorer reports paired deltas and descriptive mode aggregates. Metrics are evidence,
not automatic policy decisions.

Current coordination/quality metrics include:

```text
acceptance_score
agent_count / peak_active_children
scope_violations / wrong_edits / regressions
material_judgment_violations
correction_turns / reclassification_events
execution_stall_events
unjustified_retry_calls / same_failure_without_new_evidence
programmer_calls
product_manager_medium_calls
product_manager_high_calls
department_director_calls
redundant_product_manager_calls
review_findings / review_false_positives
final_review_attempts
review_artifact_verify_failures / post_review_mutations
consent_prompts
evidence_established / evidence_invalidated
duplicate_dependency_calls
```

When supported by the runtime, token and latency fields may also be recorded. Missing
telemetry stays null; response length, elapsed wall-clock guesses, or model self-report
must not manufacture token/cost facts.

Mode-level aggregates are descriptive only because different workload mixes are not
automatically comparable. Use frozen pairs for causal product comparisons.

## Review measurement

Standard Review is `Product Manager / Sol High`. Highest Review is
`Department Director / Astra High`.

A review run records:

```text
final_review_requirement
final_review_trigger_reasons
final_review_attempts
final_review_verdict
final_review_gate_satisfied
review_findings
review_false_positives
review_artifact_verify_failures
post_review_mutations
```

A satisfied required review must have a fresh review attempt and the `ship` verdict.
Candidate mutation invalidates the old verdict. A finding does not automatically escalate
the review tier; only new candidate truth that independently introduces a highest trigger
does so.

For the formal `1.0.0` release, the release-specific gate is always the fresh exact-source
Department Director / Astra High review defined by the release contract. Behavioral
measurement cannot substitute for it.

## Parallel-read measurement

Read-only overlap is valid only when responsibility independence and the required
workspace safety evidence are established. The product ceiling is four managed children,
not a target fanout.

The current parallel-read guard snapshots the canonical candidate workspace around
managed read-only overlap. Unexpected candidate mutation is not attributed to a child
without evidence; it is a safety stop that quarantines the affected observation and
requires Main to re-establish current workspace truth before further managed mutation.

## Recovery measurement

Recovery experiments must preserve the same rules as production:

```text
UNKNOWN never becomes permission by timeout
fresh retry requires changed execution basis and prior settlement
same-child Correction requires a new correction basis
Continue reuses the interrupted ExecutionBinding
Takeover waits for current-generation writer settlement
duplicate unchanged responsibility is not a useful second child
```

Do not use repeated failure, a weak result, or an available Host slot as a hidden model
escalation rule.

## Scoring

Validate and score a paired behavioral result with:

```bash
python scripts/score-behavioral-evals.py <result.json> --json
```

The scorer validates schema, pair controls, workload mode requirements, basic concurrency
consistency, and Final Review semantics before computing deltas. It does not run Codex,
choose production routes, change policy, or grant release readiness.

## Claim boundary

Do not claim better quality, lower cost, lower token use, lower latency, reduced rework,
better review yield, or superior routing until repeated named workloads on named runtime
versions support that claim.

One good run is not a route promotion. Promotion follows the experiment protocol:

```text
frozen evidence
-> repeated claim-eligible runs
-> product judgment
-> explicit policy change
-> focused verification
-> real Host qualification
-> release gates
```

See `experiment-protocol.md` for formal campaign/run provenance and
`runtime-attestation.md` for child runtime evidence rules.
