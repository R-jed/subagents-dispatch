# N1 Managed Delegation Depth Remediation Plan

## Objective

Correct the V4 N1 release oracle so it verifies the product's real single-layer managed delegation contract without requiring Codex Host to remove all latent V2 recursive capability.

This plan implements `tasks/SPEC-n1-managed-depth.md` and keeps the Native Core architecture intact.

## Source boundary

- Product requirement: Main is the sole managed coordinator; managed children do not create or control further Agents.
- Current official OpenAI Codex source confirms MultiAgent V2 may expose recursive collaboration to V2-capable child models.
- Therefore Host latent recursion is recorded as a platform fact, while N1 must judge actual managed execution behavior.

Official source:

- `openai/codex` `codex-rs/core/src/tools/handlers/multi_agents_v2/spawn.rs`
- `openai/codex` `codex-rs/core/src/tools/spec_plan.rs`

## Implementation order

1. Correct Host readiness semantics.
   - Keep `managed_child_containment` as optional diagnostic compatibility data.
   - Remove it from ordinary execution-readiness requirements.
   - Preserve strict validation when the field is supplied.

2. Correct the N1 machine oracle.
   - Replace generic Host hard-containment acceptance with managed-profile leaf-behavior evidence.
   - Require canonical managed spawn, real delegation boundary, adversarial untrusted input, no child-issued nested Agent action, and no descendant identity/spawn edge.
   - Treat ambiguous evidence as UNKNOWN.

3. Align architecture and release documentation.
   - Keep `max_depth=1` explicitly scoped to product policy.
   - Record latent V2 recursion as residual Host capability rather than a release blocker by itself.
   - Keep N8 strict read-only Host evidence unchanged.

4. Verify and simplify.
   - Run focused regression tests first.
   - Review changed code for unnecessary branching or duplicated semantics.
   - Refresh package integrity because `scripts/host_capabilities.py` is shipped.
   - Run the complete GitHub Actions matrix on the exact final head.
   - Perform an adversarial diff review before merge.

## Risks and mitigations

- Risk: weakening the product boundary accidentally.
  - Mitigation: N1 still fails on any actual managed nested delegation or descendant materialization.

- Risk: converting Host facts into assumptions.
  - Mitigation: keep Host collaboration capability observable and document it as residual risk; do not claim hard isolation.

- Risk: weakening unrelated safety gates.
  - Mitigation: do not change WriterLease, UNKNOWN lifecycle handling, fixed profiles, spawn contract, or N8 effective read-only requirements.

## Verification checkpoints

1. Focused host-capability tests prove failed/unknown/omitted hard containment does not block otherwise valid native execution readiness.
2. N1 contract tests prove the release oracle targets actual managed children and requires zero descendants.
3. Package integrity regenerates cleanly.
4. Ruff and full pytest pass.
5. Ubuntu 3.11, Ubuntu 3.12, macOS 3.11, Windows 3.11 and aggregate policy-tests all pass on the final exact head.
6. Fresh adversarial review confirms no managed child is authorized to create or control another Agent layer.

## Boundaries

Always: preserve Main-only coordination, managed delegation depth 1, UNKNOWN fail-closed lifecycle semantics, one-writer safety, candidate-bound release evidence and exact profile model/effort contracts.

Ask first: any fixed profile change, any nested-managed-delegation allowance, or any restored Plugin-owned lifecycle interception.

Never: claim Host-hard descendant isolation without evidence, use generic V2 recursion alone as N1 failure, or mark N1 PASS from repository CI.
