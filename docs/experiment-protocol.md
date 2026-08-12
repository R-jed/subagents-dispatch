# Experiment Protocol

This document owns the evidence process for two different questions:

```text
role_calibration
-> for a fixed role contract, which actual model / effort route is the best supported choice?

product_benchmark
-> on the same real task and controlled environment, does explicit Dispatch improve enough over a single-agent baseline to justify its coordination and compute cost?
```

They share one Experiment Plane because both need frozen inputs, real repositories, repeat discipline, route evidence, task oracles, exact telemetry, and provenance. They do not share the same independent variable.

`contracts/routing.md` owns role semantics. `contracts/policy.json` owns the currently active five-role routes. `docs/runtime-attestation.md` owns actual child route proof. `contracts/evidence-artifact.md` owns large accepted evidence bundles. `scripts/score-behavioral-evals.py` remains the existing paired behavioral regression summarizer where its fixed workload/result schema applies.

Experiments never change runtime policy automatically.

## 1. Current routes are operational defaults, not benchmark claims

The current five-role model/effort settings are working policy:

```text
Reader        -> current configured route
Worker        -> current configured route
Solver        -> current configured route
Investigator  -> current configured route
Advisor       -> current configured route
```

Do not describe a current route as optimal, faster, cheaper, or higher quality merely because it is configured or because another project uses a similar route.

External/community configurations are useful sources of challenger hypotheses. They are not evidence about this plugin's role contracts, workload distribution, Host runtime, or user experience.

## 2. One campaign format, two experiment specs

`evals/experiment-campaign.schema.json` defines common campaign identity plus one typed `experiment` object.

### Role calibration

```json
{
  "type": "role_calibration",
  "policy_promotion": false,
  "roles": []
}
```

A role-calibration workload names exactly one `calibration_role`. The campaign declares the current-policy control route and one or more model/effort challengers for that same role. Every role declared in `experiment.roles` must be backed by at least one workload in the same frozen campaign; unused route arms are invalid campaign input.

For `claim_kind=model_effort`, the campaign freezes top-level `materialization_mode=profile_only` and `model_provider_control`; both participate in the canonical campaign hash. The helper supports one Reader control and one exact Terra XHigh challenger. Run `scripts/calibration_profiles.py init` on an empty evaluator-owned evidence root, freeze the campaign, then create the profiles only after read-only evidence confirms that the requested path is the active normal `~/.codex`. That evidence binds the provisioning task to a SHA-256-frozen Host rollout under the requested home's `sessions/` tree; an ordinary JSON assertion is insufficient. `create|check|cleanup|recover` never edit the campaign or `config.toml` and reject Marketplace, Plugin, shared-config, or alternate-home preparation.

Profile intent and ownership remain durable in the evaluator root. Each profile is staged in the destination `agents/` directory under a unique non-`.toml` filename, then published with no-clobber same-filesystem semantics. After preparation, execution occurs in a distinct fresh task with `fork_turns=none`; no full App restart evidence is required. Before cleanup, formal run evidence must bind the Host-observed canonical `agent_path` to the exact committed manifest path and current SHA-256, and bind the Host-observed `model_provider` to the frozen provider control. Missing origin or provider evidence is `UNKNOWN` and claim-ineligible; mismatch fails closed.

The only Host-visible temporary objects are the two exact Agent TOMLs under the normal `<codex-home>/agents/` directory. The evidence root owns the manifest, lock, and staging files. Each profile transaction durably records campaign/candidate/route identity, exact path, staging path, inode identity, expected SHA256, and `PREPARED` status before the profile can appear at its Host path. Cleanup removes only the exact owned inode when its SHA256 still matches; external changes are preserved as conflicts. Environment readiness proves `config.toml`, Marketplace, Plugin, Plugin-cache, production-profile, and unrelated-profile inventories are unchanged. Successful creation returns `NEW TASK REQUIRED: YES`; it never spawns, requires no full App restart, and the later proof uses `fork_turns=none` with no per-spawn route override.

### Product benchmark

```json
{
  "type": "product_benchmark",
  "baseline_mode": "single_agent",
  "candidate_mode": "dispatch"
}
```

A product-benchmark workload names a task `benchmark_stratum`, not a role. Dispatch is free to keep the task in Main or materialize whichever roles its normal routing contract selects. Actual role use belongs in run/runtime evidence. The input definition must not pre-script a fake role lane merely to make the benchmark easy to analyze.

This separation prevents route calibration from being confused with orchestration-product evaluation.

## 3. Freeze the exact candidate before running

Every campaign binds `plugin_candidate_sha` to the exact Git `HEAD` validated by `scripts/validate-experiment-campaign.py`.

This is deliberate. The validator also reads the current `contracts/policy.json`; allowing the campaign to name a different plugin commit would let the campaign identity and its control route silently refer to different candidates.

A formal campaign definition is evaluator-owned input. Keep it outside the candidate commit it identifies, for example in an evaluator workspace or another explicit experiment artifact location. Do not commit a campaign containing `plugin_candidate_sha=<current candidate>` into that same candidate and then pretend the old SHA still identifies the changed tree. Committing the campaign changes `HEAD` and therefore creates a self-reference error. If the plugin candidate changes, freeze a new campaign revision/hash.

The campaign hash identifies the frozen experiment definition. It is separate from the plugin candidate SHA and from any later run artifact identity.

## 4. Keep the role contract fixed while calibrating the route

Role calibration changes model/effort for a fixed responsibility contract.

For each calibration workload freeze:

```text
role semantic contract
exact responsibility packet shape
repository and immutable starting revision
exact task/prompt bytes
project rules and upstream Skill/workflow inputs
permissions and tool surface
verification/oracle
Main-session route when material
Host/runtime version
```

Then compare route candidates for that same responsibility.

The current-policy route is the control. The experiment validator rejects a control that differs from current `policy.json`.

A model/effort challenger must keep the role mutation authority unchanged. Do not change task decomposition, acceptance, allowed tools, write scope, role decision rights, or behavioral authority between route arms. Observed Host sandbox and permission profile are runtime evidence, not configured route fields. If those controls change, it is a different experiment.

The binding failure that motivated this helper is concrete: the campaign requested a Terra XHigh challenger, but the spawn used the production Reader `agent_type`, whose installed profile pins Luna Max; Host observation recorded Luna Max. The Host's internal precedence/override reason remains unknown. Calibration runs therefore record requested, accepted, and observed Agent identity separately and require all three to equal the frozen materialized profile.

A challenger being syntactically valid in the campaign does not prove the current Host can run it. Host availability and actual runtime route are execution evidence. Unsupported, rejected, or unobservable candidate routes stay failed/UNKNOWN; never silently substitute another model or effort.

## 5. Role workload strata

Calibrate against the responsibility the role actually owns.

### Reader

Use narrow read-only evidence tasks such as focused call/path tracing, exact configuration/source discovery, or bounded test/ownership mapping.

Measure evidence correctness, completeness for the bounded question, scope discipline, and avoidable repeated discovery.

### Worker

Use fully specified bounded implementation tasks where consequential behavior and architecture are already settled.

Measure task correctness, scope discipline, verification, correction burden, and resource use.

### Solver

Use writing tasks where material judgment is genuinely coupled to implementation and cannot safely be settled once before the edit.

Measure both deliverable correctness and the quality of decisions made inside the granted decision rights.

### Investigator

Use broad read-heavy technical investigations whose semantic intent is stable and which require more exploration/synthesis than a narrow Reader task.

Include narrow-read and judgment-heavy negative controls in the overall campaign mix so a large-context route is not rewarded simply for being stronger or more verbose.

### Advisor

Use one-shot material decisions and independent reviews. Keep the responsibility read-only.

Measure decision/review quality, material issue detection, false positives, and unnecessary correction/review loops.

## 6. Real workload requirement

Formal experiments use real repositories and real engineering tasks, not synthetic prose-only task shapes.

Each workload binds at minimum:

```text
repository identity
immutable base revision
exact task text and SHA256
clean reset procedure
acceptance rubric/oracle
verification commands/checks
Main-session route fingerprint
permission fingerprint
tool-surface fingerprint
applicable project-rule refs
```

Prefer tasks whose outcome can be checked by repository tests, a containerized benchmark harness, exact artifact/diff/schema inspection, or another reproducible oracle.

Synthetic fixtures remain useful for testing the evaluator itself. They are not evidence for public product or route performance claims.

A formal campaign validator rejects obvious placeholder repository identities.

`main_session_route_fingerprint` is a controlled-input identity. It records which Main route/configuration selection the paired experiment intends to hold fixed. It is not Observed runtime evidence by itself. If a result or README claim says which Main model/effort actually ran, that claim needs Host evidence at the proof level the Host exposes; do not promote the fingerprint or config into runtime truth.

## 7. Runtime Attestation is a hard route-calibration gate

Every included role-calibration run must bind the actual route using `docs/runtime-attestation.md`.

Record separately:

```text
Configured
Requested
Accepted
Observed
route_assurance
permission_state_assurance
permission_provenance_assurance
```

For a run to support a model/effort conclusion, the exact role/agent_type, model, effort, required ancestry, and actual child sandbox/profile must be verified. Permission state must be equivalent across compared arms, alongside the other frozen controls.

Each recorded child route keeps actual `sandbox_policy_type` / `permission_profile_type` separate from `permission_provenance`. Route, permission state, and provenance have independent `verified` / `unknown` / `failed` verdicts. Unknown provenance does not relabel a verified route or verified permission state.

If the Host cannot prove a required dimension, the run is ineligible for that claim. Do not copy configured values into Observed. Every campaign declares a typed `claim_kind` and classifies all three dimensions as either required or allowed unknown. Current role-calibration campaigns are limited to `model_effort`; product benchmarks are limited to `product_behavior`. Neither can be relabeled as a Host permission-source claim. Model/effort calibration may explicitly allow unknown permission provenance when route and actual permission state are verified. A future Host permission-source or source-selection experiment must use `host_permission_provenance` and require provenance, so it remains claim-ineligible on a Host that does not expose that evidence.

For product benchmarks, route-attest every materialized Dispatch child so the report can say what actually ran. A single-agent baseline has no project child route to invent. A Dispatch run that correctly chooses zero project children also has no child route to invent; record zero materialized children rather than fabricating an attestation row.

## 8. Repetition and ordering

Agent runs are stochastic even when repository state and the grader are deterministic.

An `exploratory` campaign may begin with one run per arm to find broken setup or obviously unsuitable route candidates.

A `formal` campaign requires at least three completed repeats per workload arm. Three is a floor for replication discipline, not a claim of statistical sufficiency. If observed variance is large or one run dominates a mean, add repeats rather than hiding instability behind an average.

For formal `role_calibration`, the minimum is three claim-eligible completed runs per workload arm. Every campaign declares required assurance dimensions. A run with `UNKNOWN` or failed status in a required dimension does not count. `permission_provenance_assurance=unknown` may count only when the campaign explicitly allows it and route plus permission state are verified. Preserve every failed, no-op, zero-child, quarantined, and UNKNOWN run in the evidence record.

For `product_benchmark`, failed/UNKNOWN runs remain part of the reported distribution and must not be erased to improve an aggregate. If a missing route observation limits what can be claimed about the actual child model/effort, narrow the claim accordingly rather than deleting the run.

Interleave or randomize arm order where practical so service state, time, cache warmth, or evaluator drift are not perfectly confounded with one arm. Fixed ordering requires a recorded reason.

Report per-run results and distributions. Summary means must not erase failed, quarantined, or UNKNOWN runs.

## 9. Quality before efficiency

Do not collapse an experiment into one global score.

Evaluate in this order:

```text
1. hard correctness and safety
2. task/acceptance quality
3. correction and rework burden
4. evidence/context efficiency
5. latency and exact attributable token use
```

A faster or lower-token route/product arm does not win if it introduces a material correctness, safety, authority, scope, or acceptance regression.

Useful measure vocabulary already represented in the live behavioral-eval layer includes:

```text
success
acceptance_score
scope_violations
wrong_edits
regressions
material_judgment_violations
correction_turns
unjustified_retry_calls
unjustified_repeated_discovery
review findings / false positives
input/output/reasoning tokens when exact
latency when exact
```

Reuse this vocabulary where it fits. Do not create a second semantically equivalent metric namespace just because formal campaigns have a different input format.

Missing telemetry remains null/UNKNOWN. Never estimate token counts from response length, infer cost from configured model names, or convert configured routes into observed usage.

## 10. Oracle discipline

Use the strongest task-specific oracle available.

Preferred order:

```text
repository's deterministic tests or benchmark harness
exact artifact/diff/schema checks
predeclared functional rubric with reproducible checks
blinded independent review for material semantics that cannot be mechanized
```

Do not use the producing Agent's self-assessment as the grader.

When an LLM judgment is unavoidable, freeze the rubric, keep the grader independent from the producing child, preserve the review artifact, and report judge variance instead of presenting the result as deterministic truth.

## 11. Single-agent versus Dispatch benchmark

This experiment evaluates the orchestration product, not one role route.

For each paired task, freeze the same:

```text
exact user prompt bytes
repository/base revision
starting state
Main-session route fingerprint
permissions
available tools
project rules
acceptance oracle
Host/runtime version
```

### Baseline arm

Run the task in one ordinary Codex session without invoking subagents-dispatch. The baseline may reason, read, edit, and verify using the same allowed Host surface, but it does not use Dispatch's project child roles or orchestration state.

### Dispatch arm

Start from an independently reset copy of the same repository state and run the same task through the explicit Dispatch Skill.

Dispatch may materialize extra Agents because orchestration is the product under test. Measure the total observable resource use of Main plus project children when the Host exposes attributable telemetry.

### Fairness rules

```text
no shared dirty worktree between arms
no carrying discoveries/evidence from the first arm into the second
same task bytes
same acceptance oracle
same external tool and permission envelope
same Main-session route when it is controllable/observable
record any unavoidable Host capability difference
route-attest materialized Dispatch children
```

Use fresh worktrees, containers, or equivalent isolated resets when caches/state can materially affect the task.

## 12. Product benchmark strata

A real product benchmark needs several task shapes:

```text
small_bounded
-> work where a good Dispatch should often choose zero children

bounded_read_write
-> focused reading plus already-specified implementation

read_heavy_investigation
-> broad technical investigation/synthesis

judgment_coupled_implementation
-> consequential choices remain coupled to writing

independent_final_review
-> consequence-driven candidate review

composite
-> a real task that legitimately crosses several of the above responsibilities
```

The `small_bounded` stratum is required in the eventual public campaign mix. A useful dispatcher must be allowed to keep simple work in Main rather than manufacturing Agents to improve an orchestration benchmark.

Report results by task stratum and repository. A global aggregate may be descriptive, but it must not hide where Dispatch helps, does nothing, or hurts.

## 13. Campaign identity and validation

Freeze the complete campaign before expensive execution:

```text
campaign id
stage: exploratory | formal
exact plugin candidate SHA
Host/runtime target
one typed experiment spec
real workload definitions
repeat/ordering policy
acceptance/oracle ids
controlled Main route / permissions / tools / project rules
required assurance dimensions and dimensions explicitly allowed `UNKNOWN`
predeclared promotion criteria when role policy may change
```

Required campaign identity, Host target, route/ref, oracle, reset, and control-fingerprint text must be concrete. Whitespace-only strings and obvious placeholders such as `TBD`, `TODO`, `unknown`, or `placeholder` are not frozen experiment input.

Run from the exact plugin candidate checkout:

```text
python scripts/validate-experiment-campaign.py <campaign.json>
```

The campaign file may live outside that checkout. The validator checks schema and semantic integrity against the exact current candidate and emits a canonical campaign SHA256. It does not run Agents, score results, or change policy.

If any controlled input changes, issue a new campaign definition/hash rather than editing the definition underneath existing results.

## 14. Run evidence and result-layer boundary

Keep three evidence levels separate:

```text
frozen campaign definition
-> what was intended and controlled

per-run evidence artifact(s)
-> what actually ran and what the oracle/Host observed

accepted aggregate/report
-> descriptive comparison over the accepted run set, with exclusions and UNKNOWN states visible
```

This mirrors mature software-agent evaluation harnesses that keep reproducible task/run identity, per-instance logs/reports, and final evaluation output separate. subagents-dispatch deliberately does not copy full agent trajectories into its evidence model because raw transcript/thought/action histories conflict with the project's narrower context/privacy boundary.

Use `contracts/evidence-artifact.md` to bind complete accepted per-run provenance by reference, for example:

```text
campaign hash
workload/base identity
exact route attestation
verification/oracle output
candidate diff/artifact identity
exact token/time telemetry when exposed
quality/review result
```

Do not turn result files into transcript archives. Keep large/non-reproducible evidence in an explicit artifact and store only typed refs/digests in the accepted summary when possible.

The existing `behavioral-result.schema.json` and `score-behavioral-evals.py` remain the fixed behavioral-regression evaluator. They bind the historical workload registry and mode vocabulary used by those regression studies. Do not force a formal real-repository campaign through legacy names such as `external_baseline` or `adaptive_routing_v4` merely to reuse the scorer.

Do not create a second generic scoring engine either. Formal campaign aggregation should first consume real run evidence and reuse the established metric semantics. If repeated real campaigns demonstrate that a shared deterministic aggregation layer is useful, extract that common layer from the existing scorer at that time instead of maintaining two competing implementations.

## 15. Policy promotion gate

Role-calibration results never mutate `contracts/policy.json` automatically.

A route is eligible for promotion only when all of the following are true:

```text
policy_promotion=true was frozen before results
campaign stage is formal
required valid route-attested repeats completed
actual candidate routes were attested in included runs
no hard safety/authority/write-isolation invariant regressed
quality meets predeclared workload-specific acceptance floors/tradeoff rules
tradeoffs remain visible by role and workload
resource claims use only exact telemetry
residual UNKNOWN/failed/quarantined runs are disclosed
maintainer explicitly accepts the tradeoff
```

Non-inferiority margins, quality floors, or latency/token preferences are campaign inputs chosen before results are inspected. Do not invent a favorable threshold afterward.

After acceptance, change canonical role policy and managed profile templates together, run full repository validation, reinstall exact profiles, and repeat the five-role live route gate on the new candidate.

## 16. Final Role Policy

The final five-role policy may legitimately use different model families or reasoning efforts for different responsibilities.

Do not optimize for a visually tidy table. Optimize for the measured role contract:

```text
Reader        -> best supported narrow-evidence tradeoff
Worker        -> best supported bounded-execution tradeoff
Solver        -> best supported judgment-coupled-write tradeoff
Investigator  -> best supported broad-read investigation tradeoff
Advisor       -> best supported decision/review tradeoff
```

If candidates are practically indistinguishable at the evidence level available, prefer a simpler/lower-resource route only when the campaign's predeclared tradeoff policy supports that conclusion. Otherwise keep the current route and record insufficient evidence.

## 17. README publication gate

README reconstruction is downstream of accepted evidence, not part of calibration or benchmark execution.

Public claims may use only:

```text
implemented deterministic repository capability
human-observed App behavior for the exact candidate
actual Host route evidence
accepted formal benchmark results with Host/repository/task/repeat scope
```

Do not publish community recommendations, configured routes, synthetic fixtures, exploratory one-offs, missing telemetry estimates, campaign intentions, or excluded/UNKNOWN route runs as measured product superiority.

A benchmark statement must carry enough scope to interpret it: exact product/candidate generation, Host/runtime version, repositories/task strata, repeat counts, acceptance/oracle, and the relevant distribution/tradeoff rather than a decontextualized headline number.

When real experiments are still pending, describe role purposes and current configuration without claiming the model/effort choice is optimal or that Dispatch is faster/cheaper/better than single-agent work.
