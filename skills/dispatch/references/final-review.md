# Final Review

Final Review answers one question after the main session has a verified candidate:

```text
Does this exact deliverable need an independent second judgment before completion?
```

It is an assurance decision, not another execution stage and not a penalty for which models were used earlier.

## 1. When review is required

Use the semantic trigger codes in `../../../policy-contract.json`.

A fresh independent review is required when the current artifact materially involves:

```text
user_requested
public_contract_change
persistent_state_change
security_boundary
authorization_boundary
data_integrity
concurrency_semantics
migration
verification_gap
```

Interpret these by consequence. Process history such as Terra use, Solver use, recovery, a large diff, or many changed files is not a trigger by itself.

If process history leaves a real material uncertainty that deterministic verification cannot close, record the actual semantic reason such as `verification_gap`.

## 2. Candidate Ready

Before review, the main session must establish:

- implementation is complete enough for acceptance;
- actual complete artifact/diff has been inspected;
- scope and invariants are checked;
- relevant deterministic verification has run;
- remaining material risks are recorded;
- the review reasons are finalized.

If ordinary acceptance is still failing, continue normal routing. Do not use review to replace unfinished execution.

## 3. Bind the artifact

A review verdict applies only to the exact candidate reviewed.

For Git workspaces use:

```bash
skill_dir=<directory-containing-this-SKILL.md>
artifact_helper="$skill_dir/../../scripts/review-artifact.py"
python "$artifact_helper" --repo <workspace>
```

Capture `review_artifact_id`. Immediately before completion after a required review, verify the same identity:

```bash
python "$artifact_helper" --repo <workspace> --verify '<review_artifact_id>'
```

Any deliverable mutation after review invalidates the old verdict. Re-run affected deterministic checks, bind the new artifact, and review again.

If the full requested deliverable cannot be bound reliably, keep review unresolved.

## 4. Fresh independent Advisor

Use:

```text
agent_type: subagents_dispatch_advisor
fork_turns: none
```

Fresh context is required even when the main session is already Sol, Sol Solver implemented part of the work, or Sol Advisor previously answered a planning question. Those uses provide capability, not independent acceptance of the final integrated candidate.

Give the reviewer compressed facts, the actual candidate, acceptance conditions, verification results, and known residual risks. A Handoff Capsule may contribute Main-accepted facts/evidence, but the final reviewer still receives the exact current candidate and must not rely on stale capsule state. Do not pass raw child transcripts, dead-end narration, or tell the reviewer that another actor already believes the candidate is correct.

Return:

```text
VERDICT: ship | fix-first | rethink
REVIEWED_ARTIFACT_ID
DECISIVE_EVIDENCE
FINDINGS
RESIDUAL_RISK
```

If evidence needed for a justified verdict is missing, return `INSUFFICIENT_EVIDENCE` with the exact missing dependency.

## 5. Verdict lifecycle

### ship

Completion requires:

- reviewed artifact id matches current candidate;
- required deterministic/reproducible verification still passes;
- artifact verification still matches after review;
- main session still finds the user acceptance conditions satisfied.

### fix-first

Turn precise findings into normal work, apply the smallest correction, verify again, bind the new candidate, then run a fresh review. The old verdict is invalid after mutation.

### rethink

Return to the main session and invalidate only the affected design, contract, or evidence assumptions. Do not preserve a materially wrong premise merely to save work.

### INSUFFICIENT_EVIDENCE

Keep the candidate at review-pending. Gather only the missing evidence when possible and launch a fresh review. This is not completion.

## 6. Consent

A required quality state does not authorize unlimited compute.

The first ordinary fresh review after explicit `/dispatch` use may fit inside the normal bounded orchestration envelope. Repeated correction/re-review loops can become material compute expansion and require renewed consent under `guardrails.md`.

If required review is outside the current consent envelope and the user declines it, report that independent assurance remains incomplete. Do not silently downgrade the review requirement.
