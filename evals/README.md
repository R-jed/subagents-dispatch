# Evaluation files

This folder contains maintainer-only data for routing, coordination, interaction safety, runtime evidence, calibration, and controlled product experiments. It does not define the installed product runtime.

Current product behavior is owned by the two public Skills, `Orchestrate` and `Doctor`, plus the canonical files under `contracts/`. Conceptual controls such as Preview, Status, Steer, Takeover, Continue, and Correction are intents inside Orchestrate.

## Static and live-behavior fixtures

- `routing-cases.json` checks the fixed production profile contract and routing/reclassification decisions.
- `coordination-cases.json` checks semantic independence, mutation authority, integration ordering, and requested/configured/observed truth separation.
- `interaction-cases.json` checks the current Orchestrate/Doctor surface, one-shot Status, exact control targeting, WriterLease takeover settlement, fresh-context spawn, UNKNOWN handling, Handoff evidence, and optional factual execution receipts.
- `behavioral-workloads.json` contains frozen workload shapes for repeated live behavioral tests. It contains no benchmark results.
- `behavioral-result.schema.json` defines paired behavioral-result records.
- `runtime-assurance-cases.json` contains runtime-evidence fixtures.
- `LOCAL_EVAL_FIXTURE_TEMPLATE.md` is a template for freezing a local evaluation case.

Interaction fixtures must not recreate retired runtime machinery. In particular they do not require PendingControl, Hook receipts, Host-capacity tokens, a Team Ledger, or persisted receipt counters for retry/rework/control history.

The managed child product ceiling is 4. Main may choose a smaller batch when responsibility structure, WriterLease safety, acceptance work, or available Host evidence makes that appropriate. There is no fixed initial-vs-ordinary fanout budget in Native Core. Codex V2 session concurrency includes the primary agent, so a known Host session capacity may reduce the available child slots. A missing capability snapshot fails closed. An otherwise valid snapshot with unknown numeric Host capacity does not by itself invent a smaller ceiling.

## Experiment schemas

`experiment-campaign.schema.json` and `experiment-run.schema.json` are evaluator formats. They freeze inputs and provenance before expensive runs begin and keep unavailable evidence explicit.

Some schema values retain historical experiment identifiers such as `dispatch`, `raw_prompt_luna`, or `bounded_luna`. Those strings are frozen evaluator arm/mode identifiers. They are not public Skill ids and do not override the current Orchestrate/Doctor product surface.

`validate-experiment-campaign.py` validates and freeze-hashes a campaign against the exact candidate. It does not run Agents, score results, mutate production policy, or grant release readiness.

`validate-experiment-run.py` validates one observed run against its frozen campaign. It checks campaign/candidate/workload/arm identity, actual input attestation, materialized-child completeness, route evidence, oracle/result provenance, and measurement provenance. It does not run Codex, rank production routes, aggregate a campaign, or change policy.

The evidence boundary is:

```text
campaign expected input
-> run observed input + provenance
-> verified | unknown | failed
```

A run cannot prove candidate identity, Host version, repository revision, task bytes, reset procedure, acceptance contract, Main route, permission envelope, tool surface, or project rules merely by copying expected values from the campaign. Missing observation remains `unknown`; observed drift remains `failed`.

## Role calibration

Calibration is evaluator-only. The production route used as a control is read from `contracts/policy.json`; challengers may intentionally vary model or effort for measurement without changing production policy.

The current production controls are:

```text
Reader        gpt-5.6-luna   max
Worker        gpt-5.6-luna   max
Investigator  gpt-5.6-terra  high
Solver        gpt-5.6-sol    high
Advisor       gpt-5.6-sol    high
```

`calibration_profiles.py` can materialize one semantic role at a time under an evaluator-owned Codex home. It preserves the canonical role contract while changing only campaign-approved route fields. Generated calibration Agent identities cannot collide with production Agent identities.

Calibration helpers are excluded from the runtime package-integrity set. Their profile transaction implementation is evaluator infrastructure and has no authority over production routing, lifecycle, Doctor, release readiness, or the five packaged profiles.

Each workload binds an evaluator-owned responsibility packet hash. Each run must attest the packet actually used. Configured route values and model self-report do not count as observed runtime evidence.

## Product benchmark

For `product_benchmark`, plugin state is a controlled input. A `single_agent` baseline must independently attest that subagents-dispatch is absent. The evaluator arm historically named `dispatch` must attest the exact candidate and exercise the current product through Orchestrate.

Which managed roles Orchestrate materializes is observed result data. A valid run may use zero managed children. Zero-child cannot be inferred only from an empty route array; it requires observed project-child count provenance.

If the Host cannot establish the complete materialized child set, materialization stays unavailable and route assurance remains unknown. It cannot be relabeled as zero-child or complete route coverage.

## Measurement discipline

Measurements use explicit status:

```text
observed       -> exact value + provenance
unavailable    -> null value/ref; do not estimate
not_applicable -> null value/ref because the measure does not apply
```

Token totals, model/effort, sandbox, permission source, and child materialization are reported only from supported evidence. Response length, configured names, elapsed time, or child prose do not substitute for observation.

Execution and acceptance remain separate facts. A failed, interrupted, or UNKNOWN execution cannot claim acceptance passed. A completed execution can still fail its acceptance oracle.

Failed, interrupted, input-drifted, materialization-UNKNOWN, and route-UNKNOWN runs remain evidence records. They are not dropped to improve an aggregate.

## Current interaction invariants

The interaction set protects these current facts:

```text
Preview creates no child, profile mutation, source mutation, external action, or persistent orchestration state
first-use profile provisioning returns RESTART_REQUIRED before delegated execution
managed fresh spawn uses exact agent_type and fork_turns = none
Status is one-shot and preserves UNKNOWN
control targets resolve exactly and never guess across sessions
Steer preserves WorkUnit, ExecutionBinding, scope, and authority
Continue reuses an interrupted ExecutionBinding
Correction is an evidence-gated same-child followup with no fixed count ceiling
Takeover does not transfer a writer until current-generation Host settlement
ambiguous spawn materialization becomes UNKNOWN
UNKNOWN blocks replacement and conflicting writer transfer
Handoff carries only Main-accepted evidence into fresh context
optional execution receipts use current inspectable facts and no persistent receipt ledger
Doctor diagnoses product health but does not own release publication authority
```

Machine-checkable current state, lifecycle, scheduler, WriterLease, Orchestrate, model/effort, release, and product-surface invariants live in the current `tests/test_*_v4.py` and product-contract tests. Historical deleted V3/RC recovery-ledger tests are not current authorities.

See `../docs/behavioral-evals.md` for paired behavioral measurement, `../docs/experiment-protocol.md` for experiment methodology and claim gates, and `../docs/runtime-attestation.md` for runtime evidence rules.
