# Product Success Criteria

The product benchmark answers one question: when a developer explicitly chooses Orchestrate, does the coordination policy improve the engineering outcome enough to justify its additional coordination and compute cost?

Do not collapse that question into a single speed or token number.

Evaluate evidence in this order:

```text
1. correctness and safety
2. task and acceptance quality
3. rework and user intervention
4. context and coordination efficiency
5. latency and attributable token use
```

An Orchestrate arm cannot count as a product win when it is faster but introduces a material correctness, authorization, scope, data-integrity, writer-safety, or acceptance regression.

## What a positive product claim requires

A useful product result should show all of the following on representative workloads:

- hard correctness and safety are at least preserved;
- material wrong edits, scope violations, and regressions do not increase in a way that invalidates the workflow;
- correction, takeover, repeated discovery, and manual recovery burden are measured rather than hidden;
- zero-child decisions are counted as successful product behavior when delegation would add no value;
- coordination overhead is visible, including extra review or integration work;
- latency and token claims use exact attributable telemetry when available and remain unknown when the Host cannot expose it.

The Plugin should not claim that more children, more parallelism, or a higher materialization rate is inherently better.

## Workload strata

Product evaluation should include different shapes because orchestration value is workload-dependent:

```text
parallel read-heavy investigation
investigate then implement
bounded implementation plus verification
strongly sequential work
small tasks where zero children should win
high-judgment changes that may justify independent review
```

A product can be useful even if it deliberately does little on some strata. In particular, small and strongly sequential tasks should not be forced into delegation merely to improve a utilization metric.

## Registered simplification comparisons

Two architecture comparisons should be measured before either becomes a new product default.

### Value-driven fanout versus one-child-first

Compare the current Main-owned value-driven fanout under the four-child safety ceiling with a treatment that starts at most one child and opens a second independent lane only after evidence shows that the additional concurrency is still worthwhile.

Measure correctness and safety first, then repeated discovery, parent idle time, user intervention, wall-clock latency, integration work, and attributable token use. Segment results by workload stratum. A one-child-first policy should not replace the current ceiling merely because it uses fewer Agents; it must improve the overall engineering tradeoff without suppressing valuable parallel read-heavy work.

### Compact responsibility packet versus expanded packet

Compare the five-section `contracts/responsibility-packet.md` projection with the expanded canonical responsibility representation on matched delegated tasks.

Measure contract omissions, scope violations, clarification or retry frequency, verification success, parent repair work, child input size, latency, and attributable token use. The compact form is successful only when it preserves material task truth and acceptance quality while reducing coordination/context burden. Recovery, handoff, and other specialized state remain available in both arms when the task actually needs them.

These comparisons are registered hypotheses, not current product claims. Freeze task sets, treatment definitions, and decision thresholds before a formal campaign. Do not use repository test counts as evidence that either treatment improves developer outcomes.

## Threshold discipline

Do not invent public percentage thresholds before exploratory data exists.

Exploratory campaigns should first establish variance, common failure modes, and the scale of measurable effects. Before a formal campaign begins, freeze the decision thresholds and the workload mix. Do not tune thresholds after observing formal results merely to make the candidate pass. A changed threshold or workload definition creates a new campaign decision boundary.

When data is insufficient, narrow the claim. For example, evidence may support “helps on parallel investigation-heavy tasks” without supporting “makes Codex development faster overall.”

## Evidence boundaries

Repository tests answer whether the implementation satisfies deterministic contracts.

The real Host campaign answers whether the target Codex Host actually exposes and enforces the lifecycle behavior the product relies on.

The product benchmark answers whether the resulting user workflow is worth using on real engineering tasks.

Passing one evidence class does not substitute for another. `docs/experiment-protocol.md` owns the detailed campaign format and measurement discipline.
