# Independent Review and Acceptance

After Main has a verified Candidate Ready artifact, this contract decides whether the exact candidate needs an independent Standard Review or the highest-consequence Department Director acceptance before completion.

Review is assurance, not another implementation stage and not a penalty for which model was used earlier.

## 1. Review tiers

`policy.json` owns two explicit, non-overlapping trigger sets.

### Standard Review

Standard Review uses a fresh Product Manager at `gpt-5.6-sol / high` for:

```text
user_requested_review
public_contract_change
material_behavior_change
persistent_state_change
verification_gap
```

### Highest-consequence acceptance

Highest acceptance uses a fresh Department Director at `gpt-6-astra / high` for:

```text
security_boundary
authorization_boundary
data_integrity
critical_concurrency_or_ownership
migration
irreversible_external_effect
release
user_requested_highest_assurance
```

If a highest trigger is present, Department Director substitutes for the routine Standard Review. Do not stack Product Manager review underneath it unless a separate concrete evidence/decision gap independently justifies that work.

Task complexity, diff size, file count, retry count, prior Product Manager use, or the model that implemented the candidate are not review triggers.

Main confirms semantic trigger facts. Deterministic policy code selects the only legal review tier/route from those confirmed facts. A reviewer never decides its own admission.

## 2. Candidate Ready

Before any review, Main must establish:

- the requested deliverable is complete enough for acceptance;
- the actual deliverable/artifact and relevant diff/state are inspected;
- scope and invariants are checked;
- material obligations and cross-responsibility seams are closed;
- relevant deterministic/reproducible verification has run;
- residual risks and review triggers are recorded.

If ordinary acceptance is still failing, continue normal routing. Do not use review to replace unfinished execution or missing integration.

Department Director cannot be used before Candidate Ready for planning, implementation, speculative advice, or confidence checks.

## 3. Bind the exact artifact

A verdict applies only to the exact candidate reviewed.

For Git-backed deliverables use `scripts/review-artifact.py` to capture `review_artifact_id`, then verify the same identity immediately before completion. The helper fails closed when tracked changes may be hidden by `assume-unchanged` or `skip-worktree`. Resolve ambiguous repository state rather than clearing those flags automatically.

For non-Git deliverables, bind the exact serialized candidate bytes with a deterministic SHA-256 digest and record the serialization boundary.

Any deliverable mutation invalidates the old verdict. Re-run affected deterministic checks, bind the new candidate, and obtain a fresh required review. If the full deliverable cannot be represented and rebound reliably, keep review unresolved.

## 4. Fresh independent reviewer

Standard Review uses:

```text
agent_type: subagents_dispatch_product_manager
model: gpt-5.6-sol
reasoning_effort: high
fork_turns: none
```

Highest acceptance uses:

```text
agent_type: subagents_dispatch_department_director
model: gpt-6-astra
reasoning_effort: high
fork_turns: none
```

The reviewer must be fresh, semantically read-only, exact-candidate-bound, and uninvolved in candidate creation. A Product Manager that participated in decision or implementation cannot satisfy independent Standard Review of the same candidate. Model-family difference is not required for independence; execution/context independence is.

Before launch, Main records a pre-review request separate from the reviewer result. It binds the exact candidate identity, required tier/role/route, `fork_turns=none`, fresh context, hard-isolation requirement, explicit no-edit/no-external-side-effect instruction, and an external evidence reference. Review output must reference the canonical digest of that request.

## 5. Permission assurance

Semantic mutation authority for every reviewer is `none`. Host permission is separate runtime evidence and never expands it.

Use exactly one assurance path:

```text
A. enforced_read_only
   Host-observed effective permission is read-only.

B. artifact_immutability_fallback
   Host positively reports broader write-capable permission;
   hard_isolation_required is false;
   no-edit/no-external-side-effect semantics are explicit;
   the exact review artifact is unchanged before/after;
   broader Host permission is recorded as residual risk.

C. insufficient evidence / fail closed
   permission is unavailable or ambiguous;
   hard isolation is required without Host-enforced read-only;
   candidate artifact changes during review;
   or a reviewer violates the no-edit/external-side-effect boundary.
```

Path B is exact-candidate immutability evidence, not Host-hard isolation proof. If Path C applies, return `INSUFFICIENT_EVIDENCE` and keep review pending.

## 6. Verdict

Return:

```text
VERDICT: ship | fix-first | rethink
REVIEW_TIER
REVIEWED_ARTIFACT_ID
REVIEW_REQUEST_SHA256
PERMISSION_OBSERVATION
ASSURANCE_MODE
ARTIFACT_UNCHANGED
HARD_ISOLATION_REQUIRED
NO_EDIT_INSTRUCTION
DECISIVE_EVIDENCE
FINDINGS
RESIDUAL_RISK
EVIDENCE_REF
```

`ship` is independent assurance evidence; Main still owns user intent, integration, final acceptance sequencing, and the final response.

`fix-first` turns precise findings back into normal work. After mutation, bind a new candidate and use a fresh reviewer at the same tier unless the new candidate truth independently introduces a higher trigger. Failure itself does not escalate review tier.

`rethink` returns affected design/contract assumptions to Main without preserving a materially wrong premise merely to save work.

`INSUFFICIENT_EVIDENCE` keeps review pending and identifies the missing dependency.

## 7. No review fallback

If an exact required review route is unavailable, do not substitute another model or effort. Standard Review and Department Director acceptance remain pending until their exact route is available or the governing requirement changes. Product Manager evidence cannot satisfy a Department Director obligation.

## 8. Consent

A required quality state does not authorize unlimited compute. Repeated correction/re-review loops may become material compute expansion and require renewed consent under `guardrails.md`. Declined compute leaves independent assurance incomplete; never silently downgrade the review requirement.
