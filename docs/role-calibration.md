# Role Calibration and Real Benchmark Protocol

This document owns the evidence process for changing the five managed role routes and for measuring whether Dispatch adds value over a single-agent baseline.

It does not define runtime routing semantics. `contracts/routing.md` owns role responsibilities. `contracts/policy.json` owns the currently active route configuration. This document determines when evidence is strong enough to propose changing that configuration.

## 1. Current routes are operational defaults, not benchmark claims

The current five-role model/effort settings are a working policy:

```text
Reader        -> current configured route
Worker        -> current configured route
Solver        -> current configured route
Investigator  -> current configured route
Advisor       -> current configured route
```

Do not describe a current route as optimal, faster, cheaper, or higher quality merely because it is configured or because another project recommends it.

Community configurations are useful sources of challenger hypotheses. They are not evidence about this plugin's role contracts, workloads, Host, or user experience.

## 2. Keep the role contract fixed while calibrating the route

Role calibration changes one independent variable at a time: the model/effort route used for a fixed responsibility contract.

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

Do not change task decomposition, acceptance, allowed tools, write scope, or role decision rights between route candidates. If those change, it is a different experiment.

## 3. Real workload requirement

Formal policy promotion uses real repositories and real engineering tasks, not synthetic prose-only examples.

A workload must bind at minimum:

```text
repository identity
immutable base revision
exact task definition or immutable issue/task reference
clean starting-state procedure
acceptance rubric/oracle
allowed verification commands
material project rules
```

Prefer tasks whose outcome can be checked by repository tests, a deterministic evaluator, exact artifact inspection, or another reproducible oracle.

Public benchmark instances such as containerized real-repository issue tasks may be used when their setup is reproducible and appropriate for the role under test. Fresh real issues or maintainer-curated tasks may also be used when they are frozen before the first run.

Do not tune a role on one repository family only and then publish a universal claim.

## 4. Workload strata

Calibrate against the responsibility the role actually owns.

### Reader

Use narrow, read-only evidence tasks:

```text
call/path tracing
focused test or ownership mapping
exact configuration/source discovery
bounded factual repository questions
```

Quality is evidence correctness, completeness for the bounded question, scope discipline, and repeated-discovery cost.

### Worker

Use fully specified bounded implementation tasks where material behavior and architecture are already settled.

Quality is task correctness, scope discipline, deterministic verification, correction work, and resource use.

### Solver

Use implementation tasks where consequential judgment remains coupled to the write and cannot safely be decided once before implementation.

Quality includes correctness of both the implementation and the material choices made inside the granted decision rights.

### Investigator

Use broad read-heavy technical investigations with stable semantics and no unresolved material product decision.

Include a narrow Reader negative control and a judgment-heavy Sol negative control so the Investigator is not rewarded merely for being stronger or more verbose.

### Advisor

Use one-shot material decisions and independent review tasks. Keep it read-only. Measure decision/review quality, false positives, material issue detection, and unnecessary correction/review loops.

## 5. Candidate routes

Every campaign has one current-policy control and one or more challengers.

A challenger must be an exact route the current Host can actually expose and run. Record the exact model identifier, reasoning effort, and required sandbox intent. Do not guess aliases, translate names across hosts, or silently replace an unavailable candidate.

The current Luna Max and Terra XHigh choices therefore enter calibration as controls/hypotheses. They remain unchanged until real measurements justify a policy update.

Do not add a challenger simply because it looks aesthetically simpler or because a different project uses it.

## 6. Runtime Attestation is a hard calibration gate

Every role-calibration run must bind the actual route using `docs/runtime-attestation.md`.

Record separately:

```text
Configured
Requested
Accepted
Observed
provenance grade
```

For a run to contribute to a model/effort policy conclusion, required model, effort, role identity, ancestry, and permission/sandbox facts must be observed at the evidence level required by the workload.

If the Host cannot prove the route, mark the run `UNKNOWN` for route calibration. Do not copy configured values into Observed and do not use the run to claim that a particular model/effort produced the result.

The task result may still be useful for a different product-behavior question, but it is not valid model/effort calibration evidence.

## 7. Repetition and ordering

Agent runs are stochastic even when the repository task and grader are deterministic.

Exploratory campaigns may start with one run per arm to find broken setup or obviously unsuitable candidates.

A formal policy-promotion campaign requires at least three completed, route-attested repeats per workload arm. If observed variance is large or one result dominates the mean, run more repeats rather than treating three as statistically sufficient by definition.

Interleave or randomize candidate order where practical so time-of-day, service state, cache warmth, and evaluator drift are not perfectly confounded with one route.

Report distributions and per-run results. Summary means must not hide failed, quarantined, or UNKNOWN runs.

## 8. Quality before efficiency

Do not collapse calibration into one global score.

Evaluate in this order:

```text
1. hard correctness and safety
2. task/acceptance quality
3. correction and rework burden
4. evidence/context efficiency
5. latency and exact attributable token use
```

A faster or lower-token candidate does not win if it causes a material correctness, safety, scope, or acceptance regression.

Useful measures already supported by the live-eval layer include:

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

Missing telemetry remains null/UNKNOWN. Never estimate token counts from output length or infer cost from configured model names.

## 9. Oracle discipline

Use the strongest task-specific oracle available.

Preferred order:

```text
repository's deterministic tests or benchmark harness
exact artifact/diff/schema checks
predeclared functional rubric with reproducible checks
blinded independent review for material semantics that cannot be mechanized
```

Do not use the producing Agent's self-assessment as the grader.

When an LLM judgment is unavoidable, preserve the exact rubric and review artifact, keep the grader independent from the producing child, and report that the result contains judge variance rather than presenting it as deterministic truth.

## 10. Single-agent versus Dispatch benchmark

This benchmark answers a different question from role calibration: does the orchestration product add enough value to justify its coordination and compute cost?

For each paired task, freeze the same:

```text
user prompt bytes
repository/base revision
starting state
main-session model/effort when exposed
permissions and tools
project rules
acceptance oracle
runtime version
```

### Baseline

Run the task in one ordinary Codex session without invoking subagents-dispatch. The baseline may reason, read, edit, and verify using the normal allowed Host surface, but it does not use Dispatch's child roles or orchestration state.

### Dispatch candidate

Start from an independently reset copy of the same repository state and run the same task through the explicit Dispatch Skill.

Dispatch may use additional children because that is the product under test. Measure the total observable resource use of Main plus project children when the Host exposes attributable telemetry.

### Fairness rules

```text
no shared dirty worktree between arms
no carrying discoveries from the first arm into the second
same acceptance oracle
same external tool/permission envelope
record any Host capability difference
route-attest every materialized project child
```

Use fresh environments/worktrees/containers so one arm does not inherit the other's edits or caches when those caches can affect the measured task.

## 11. Real benchmark task selection

Use several task shapes instead of one headline repository issue:

```text
small bounded fix where Dispatch should often choose zero children
read + bounded write task where focused delegation may help
large read-heavy investigation
judgment-coupled implementation
change requiring independent final review
```

The first category is essential. A good dispatch system must be allowed to lose the delegation opportunity and keep simple work in Main rather than manufacturing Agents to improve an orchestration benchmark.

Report results by task stratum and repository. A single aggregate may be descriptive, but it must not erase where Dispatch helps or hurts.

## 12. Campaign identity

Freeze every formal campaign before execution.

A campaign definition should bind:

```text
campaign id and purpose
candidate plugin commit
Host/runtime version target
roles/routes under test
real workload definitions
repeat policy
acceptance/oracle ids
controlled permissions/tool surface
predeclared promotion criteria
```

Hash the canonical campaign definition. If a controlled field changes, issue a new campaign revision/hash rather than editing the definition underneath existing results.

The repository may store campaign definitions and schemas. Actual expensive run evidence may remain in explicit evaluator-owned artifacts until the campaign is accepted for publication.

## 13. Policy promotion gate

Benchmark results never mutate `contracts/policy.json` automatically.

A route is eligible for promotion only when all of the following are true:

```text
formal campaign was frozen before the compared runs
required repeats completed
actual candidate route was attested in included runs
no hard safety/authority/write-isolation invariant regressed
quality meets the predeclared workload-specific acceptance floor
tradeoffs are visible by role and workload stratum
resource claims use only exact telemetry
residual UNKNOWN/failed runs are disclosed
maintainer explicitly accepts the tradeoff
```

Non-inferiority margins, quality floors, or latency/token preferences are campaign inputs chosen before results are inspected. Do not hide a loss by inventing a favorable threshold afterward.

After acceptance, change the canonical role policy and managed profile templates together, rerun repository validation, reinstall exact profiles, and repeat the five-role live route gate on the new candidate.

## 14. Final Role Policy

The final five-role policy may legitimately keep different model families or reasoning efforts for different responsibilities.

Do not optimize for a visually tidy table. Optimize for the measured role contract:

```text
Reader        -> best supported narrow-evidence tradeoff
Worker        -> best supported bounded-execution tradeoff
Solver        -> best supported judgment-coupled-write tradeoff
Investigator  -> best supported broad-read investigation tradeoff
Advisor       -> best supported decision/review tradeoff
```

If two candidates are practically indistinguishable at the evidence level available, prefer the simpler/lower-resource route only when the campaign's predeclared tradeoff policy permits that conclusion. Otherwise keep the current route and record insufficient evidence.

## 15. README publication gate

README reconstruction is downstream of calibration, not part of the experiment.

Public claims may use only accepted evidence:

```text
implemented and deterministic repository capability
human-observed App behavior for the exact candidate
actual Host route evidence
accepted benchmark results with scope/sample context
```

Do not publish community recommendations, configured routes, synthetic fixtures, or one-off exploratory results as measured product superiority.

When benchmark evidence is not yet complete, describe role purposes and current configuration without claiming that the model/effort choice is optimal.
