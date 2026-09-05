# Experiment Protocol

This document owns maintainer-only evidence for two questions:

```text
role_calibration
-> for one fixed semantic role/responsibility, does a challenger model/effort route have enough evidence to justify a future production-policy decision?

product_benchmark
-> on the same real task and controlled environment, does Orchestrate improve enough over a single-agent baseline to justify its coordination/compute cost?
```

Experiments never edit production policy automatically and have no runtime/release authority.

## 1. Current production routes are controls, not benchmark claims

`contracts/policy.json` owns current production routing:

```text
程序员 / Programmer
  gpt-5.6-luna / max

产品经理 / Product Manager
  gpt-5.6-sol / medium | high

部门总监 / Department Director
  gpt-6-astra / high
```

Configured production routes are operational policy, not proof that they are optimal. A route promotion requires calibration evidence, explicit product/policy approval, focused verification, Host-reference conformance, and normal release gates. The current runtime must still fail an affected route closed when its actual Host controls or observations are unavailable or conflicting.

## 2. One campaign format, two experiment types

`evals/experiment-campaign.schema.json` freezes campaign identity and controlled inputs. `evals/experiment-run.schema.json` records one observed run.

Every campaign binds the exact current Git `HEAD`. Formal campaigns use at least three completed runs per arm and real repositories/tasks rather than placeholder repositories.

### Role calibration

One campaign calibrates exactly one semantic role. It freezes:

- the canonical role id and responsibility contract reference;
- one current production route as control;
- one or more explicit model/effort challenger routes;
- one fixed responsibility packet identity per workload;
- repository/revision, exact task bytes, reset procedure and oracle;
- Main-route, permission, tool-surface and project-rule fingerprints;
- Host target and model-provider control.

The control must be a currently legal production route for that role. A challenger may intentionally be outside production policy, but it must preserve the same responsibility mutation authority. Challenger authority exists only inside evaluator execution and can never be accepted by production Orchestrate.

Calibration no longer creates temporary custom-Agent TOMLs. All arms use the canonical role profile and explicitly request the campaign-frozen model and reasoning effort on spawn. There is no calibration profile staging, registry mutation, materialization manifest, provisioning nonce, temporary Agent identity, or cleanup/recovery transaction.

This is a deliberate simplification enabled by the current Codex spawn contract: production and evaluator execution can request model/effort explicitly while keeping the role profile stable.

### Product benchmark

```json
{
  "type": "product_benchmark",
  "baseline_mode": "single_agent",
  "candidate_mode": "dispatch"
}
```

`dispatch` is an evaluator arm identifier, not a public Skill id. A benchmark workload freezes a task stratum rather than pre-selecting a managed role. Orchestrate remains free to stay Main-only or materialize the roles its normal policy admits.

## 3. Requested, accepted, and observed route truth are separate

Each materialized child route records:

```text
requested
  canonical agent_type
  model
  reasoning effort
  evidence ref

accepted
  Host-accepted agent_type/model/effort when observable
  verdict + evidence ref

observed
  actual agent_type/model/effort
  permission/sandbox state
  model provider when material
  native/local/both evidence source + ref
```

For production benchmark dispatch arms, the requested route must be current production policy. For role calibration, it must equal the frozen control/challenger route while retaining the canonical role `agent_type`.

A mismatch is recorded as failed evidence; validators never rewrite Observed to match Requested. Missing evidence remains unknown. Configured values, model self-report, or copied campaign fields are not Observed evidence.

## 4. Input provenance is mandatory

A run independently attests the actual:

- Plugin candidate state;
- Host product/version/platform;
- repository URL and immutable base revision;
- task bytes;
- reset procedure;
- acceptance/oracle contract;
- calibration responsibility packet where applicable;
- Main-route, permission, tool-surface and project-rule controls.

Expected campaign values do not become observed truth merely because they are copied into the run file. Verified evidence requires a concrete evidence reference. Missing observation is `unknown`; observed drift is `failed`.

For the product `single_agent` baseline, subagents-dispatch must be independently attested absent. Route/permission assurance is then `not_applicable`, not fabricated `verified`.

## 5. Permission and provider evidence

Route, permission state and permission provenance remain separate assurance dimensions. Every campaign classifies each dimension as required or allowed unknown; route and actual permission state are always required by the current experiment types.

Model/effort calibration also freezes `model_provider_control`. Provider mismatch makes the arm ineligible for model/effort promotion. Provider evidence does not come from the deleted profile materialization mechanism; it comes from actual runtime observation.

## 6. Child materialization completeness

Observed child count must equal the number of child-route records. A calibration run requires exactly one observed materialized child. A product dispatch run may legitimately have zero children.

If the Host cannot establish the complete child set, materialization is `unavailable`, count is null, child-route coverage remains unknown, and the run is preserved rather than guessed into a conclusive result.

## 7. Execution, oracle and measurement provenance

Execution completion and acceptance are separate facts. A failed/interrupted/unknown execution cannot claim passed acceptance. Passed acceptance requires at least one oracle reference and a concrete result reference.

Measurements use:

```text
observed       exact value + source_ref
unavailable    null value/ref because Host/evaluator could not establish it
not_applicable null value/ref because the measurement does not apply
```

Observed token totals must reconcile when main/child/aggregate totals are all available. Do not estimate missing telemetry.

Failed, interrupted, input-drifted, route-failed and materialization-unknown runs remain evidence records. Do not discard them to improve an aggregate.

## 8. Promotion boundary

Calibration validation never ranks routes or modifies policy. Promotion is explicit:

```text
frozen campaign
-> sufficient claim-eligible observed runs
-> human/product judgment
-> policy change
-> focused tests
-> Host-reference conformance
-> release gates
```

A syntactically valid challenger is not proof that the Host supports it. Unsupported, rejected, conflicting, or unobservable routes remain failed/unknown; there is no fallback route.

## 9. Commands

```bash
python scripts/validate-experiment-campaign.py <campaign.json> --json
python scripts/validate-experiment-run.py <run.json> --campaign <campaign.json> --json
```

These validators do not run Codex, score quality, aggregate campaigns, install Agent profiles, or grant release readiness.
