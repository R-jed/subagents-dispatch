# RC5 Review Remediation Plan

## Objective

Close the ten repository-side findings from the three independent Native Core reviews without weakening the frozen Host/release boundaries. Keep `v4/rc5-native-core` unchanged; all remediation lands on `v4/rc5-review-remediation` until a new exact candidate is reviewed.

## Capability map

| Module id | Responsibility | Depends on |
| --- | --- | --- |
| runtime-safety | Scope containment, generation-safe execution identity, idempotent Host observation persistence, bounded same-child recovery evidence | none |
| host-adapter | Fail-closed capability readiness and Codex V2 session-capacity projection | runtime-safety |
| truth-closure | Remove stale TeamPlan/fixed-budget semantics, align evals and profile labels to current policy, make phase status evidence-based | runtime-safety, host-adapter |
| candidate-verification | Package integrity, lint, full tests, cross-platform CI, adversarial diff review | runtime-safety, host-adapter, truth-closure |

Build order: `runtime-safety` -> `host-adapter` -> `truth-closure` -> `candidate-verification`.

## Source and version boundary

- Python runtime: 3.11+ as declared by the repository.
- Dev validation uses the pinned versions in `requirements-dev.txt`.
- Codex Host semantics must be verified only against current official `openai/codex` source. Profile configuration remains requested intent unless the Host proves effective runtime behavior.

## Design decisions

### Runtime safety

- Repository write scopes are canonical repository-relative POSIX paths. Windows drive/UNC forms are rejected. Directory scopes contain descendants by path-segment ancestry.
- Bounded state cannot retain unbounded opaque identity or correction sets. Safety therefore binds lifecycle observations to monotonic attempt/control generations. Native task names must remain generation-distinct. Same-child correction evidence is compacted to a bounded generation summary rather than an unbounded event list.
- Duplicate current-generation Host observations are true no-ops and must not advance `state_revision`.

### Host adapter

- Missing Host capability evidence remains unavailable/unknown and cannot be projected as ready.
- Codex V2 capacity is treated as session-level evidence. Any child-capacity projection must account for the active root/session participant and must not invent a private capacity ledger.

### Truth closure

- WorkGraph/WorkUnit own responsibility and dependency truth. TeamPlan fields are compatibility residue only.
- `contracts/policy.json` owns managed model/effort truth; receipt/eval/test surfaces must not maintain independent stale copies.
- `phase-status.json` may report PASS only for currently verified repository phases.

## Verification checkpoints

1. Add focused regressions that fail on the frozen candidate for each runtime-safety issue, then implement the smallest coherent fix.
2. Validate Host-adapter behavior against official OpenAI Codex source and focused tests.
3. Sweep active contracts/evals/tests for retired semantics and duplicated model/effort constants.
4. Refresh generated package integrity only after runtime files stabilize.
5. Run Ruff and the full pytest suite through GitHub Actions on the remediation branch, then require all supported platform jobs to pass.
6. Compare the remediation branch against `5c577870a134e683c78a6c6dc584b18c878c99f5` and perform a fresh adversarial review before proposing a new candidate.

## Boundaries

Always: preserve fail-closed UNKNOWN semantics, one-writer safety, Main acceptance authority, WorkGraph dependency truth, candidate-bound release evidence, and the real Host N0-N8 gate.

Ask first: none for the ten already-approved review findings. Any newly discovered product-semantic change outside this scope must be reported instead of silently added.

Never: change the frozen `v4/rc5-native-core` branch in place, infer Host truth from profile TOML, restore fixed retry/followup ceilings, add an unbounded tombstone/event ledger, or mark release gates PASS from repository CI alone.
