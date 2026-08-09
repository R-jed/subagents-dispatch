# Live Behavioral Evaluation Protocol

Static tests prove repository contracts, packaging, profile lifecycle, schemas, deterministic tooling, and policy wiring. They do not prove model quality, cost, native runtime behavior, onboarding quality, interaction usability, or the real value of a routing choice.

The live suite uses controlled paired workloads where a meaningful paired comparison exists, plus controlled single-surface interaction workloads where pairing would distort the question. Experimental labels remain measurement vocabulary and never become runtime policy.

## Measurement boundary

`evals/` is a measurement surface. Historical labels such as `adaptive_routing_v4` remain experiment labels only. Historical runs stay comparable because recorded experiment labels remain frozen with the result data. Do not make the Skill maintain an ontology of experiment labels; runtime behavior still comes from the canonical policy owners.

`evals/interaction-cases.json` is the deterministic fixture for Preview, first-use readiness, Status, Steer, Takeover, Execution Receipt, and Handoff Capsule boundaries. `evals/behavioral-workloads.json` contains frozen real-Host workload shapes and no claimed benchmark results.

## Freeze controlled inputs

Before a paired run, freeze the exact user prompt bytes, repository/base revision, starting state, acceptance rubric, verification commands, permission posture, tool surface, Codex runtime version, and any route evidence that materially affects the experiment. Record the `workload_definition_hash` for that frozen definition; changed controlled inputs require a new pair id/hash.

Keep `execution_route` explicit. It is the experimental variable only when the workload's declared comparison allows route strategy to differ; otherwise it stays a controlled field along with the other causal inputs.

## Core evidence rules

Record only telemetry actually available. Missing model, token, latency, cost, ancestry, or permission evidence stays missing. Do not infer runtime facts from configured profiles.

Outcome, correction, interaction, resource-use, evidence-efficiency, and Final Review metrics remain separate. Do not collapse unrelated workloads into one global score.

## Dispatch Skill invocation in live workloads

Live Plugin runs use the actual Host Skill surface:

```text
$dispatch <task>
$dispatch preview <task>
$dispatch status
$dispatch steer <unit_id>: <guidance>
$dispatch takeover <unit_id>
$doctor <diagnostic request>
```

`/skills` may be used to select **Dispatch** or **Doctor**. Bare `/dispatch`, `/doctor`, and legacy namespaced slash identities are not Skill-discovery requirements and must not be used as the release oracle.

## Key experiments

### Bounded execution

Compare raw Luna prompting with a bounded Luna responsibility when desired behavior, invariants, scope, and deterministic acceptance are already explicit. Measure correctness, scope discipline, correction work, repeated discovery, and exact resource use when available.

### Judgment-coupled implementation

Compare Advisor→Luna handoff with one Sol Solver on work where implementation repeatedly exposes material semantic choices. Do not assume either strategy wins.

### Main capability reuse

When trusted Main-session evidence already meets the Sol reference capability, compare keeping ordinary judgment-coupled work in Main with spawning an extra Sol Solver. This optimization never substitutes for fresh independent Final Review.

### Terra read-heavy investigation

Use stable-semantics, read-only work that may benefit from broader technical synthesis. Compare narrow Luna Reader, Terra Investigator, and deliberately judgment-heavy Sol Advisor cases. Weak Luna output alone is never a Terra trigger.

### Consequence-driven Final Review

Exercise public contract, persistent state, security/authorization, data integrity, concurrency, migration, verification-gap, and user-requested review reasons. Process history such as Terra/Solver use, recovery, or diff size is a negative control rather than an automatic trigger.

### First-use readiness

Run an explicit `$dispatch` task from clean managed-profile absence. The candidate should:

```text
identify worthwhile delegation
-> inspect exact role availability
-> installer --check
-> clean Not installed
-> provision only plugin-owned managed state
-> installer --check succeeds
-> RESTART_REQUIRED
-> 0 current-task child spawns
-> fresh task/session
-> rerun the original $dispatch
-> exact role available before spawn
```

Preview or Status with missing profiles must not provision. Unsafe/unowned conflicts must not be overwritten. Exact profiles that remain unavailable in the current task produce `RESTART_REQUIRED`, not a substitute role.

### Preview and live control

Preview verifies zero child spawn, provisioning, source mutation, and external action. Status is one-shot and preserves `UNKNOWN`. Steer preserves the same unit/attempt/role/authority; material scope change returns to Main classification. Takeover of a writer must establish settlement before Main writes.

### Execution Receipt

Delegated tasks append one factual receipt. Zero-child, Preview-only, and Status-only cases do not. Any guessed runtime model, token usage, or currency cost is a hard failure.

### Handoff Capsule

Compare fresh children with and without compact Main-accepted evidence. Keep `fork_turns=none` in both cases. Measure repeated discovery, stale-context mistakes, and unverified-claim propagation. Relevant artifact drift invalidates affected capsule facts.

### Plugin Skill registry and tagged distribution

For a release candidate, install the Plugin from the exact immutable tag, start a fresh Host session, and confirm:

```text
Dispatch present in Skill registry
Doctor present in Skill registry
$dispatch accepted
$doctor accepted
source/path resolves to the tagged installed Plugin when observable
ordinary task implicit activation = none
```

Do not treat absence of bare slash commands as a packaging failure.

## Scoring

```bash
python scripts/score-behavioral-evals.py path/to/result.json
```

The scorer validates schema and controlled pairing first. Primary candidate-minus-baseline deltas are produced only for each workload's declared pair. Cross-workload aggregates are descriptive inventory, not controlled comparisons.

## Evidence rule

Do not claim improved quality, lower cost, reduced rework, Solver superiority, Terra value, onboarding improvement, receipt usability, takeover usability, Handoff Capsule efficiency, or Skill-discovery compatibility until named live workloads on named runtime versions support the claim.

Static contract tests prove intended policy. Only a real Codex Host run proves session registration, Skill registry discovery, custom-Agent availability, child-control surfaces, and release distribution behavior on a particular build.
