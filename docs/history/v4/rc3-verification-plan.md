> Historical archive. This document records a superseded design/review state. It is not a current V4 contract, implementation guide, release gate, or source of runtime authority. Use current `contracts/`, current non-history `docs/`, and `docs/v4/` for present behavior.

# V4.0.0 RC3 Verification Plan

RC3 uses four mandatory gates.

## Gate 1: Red contract gate

Before production remediation, adversarial tests MUST demonstrate the known failure modes against the RC2 behavior.

Required classes:

- physical profile and managed `agent_type` mismatch
- missing or incorrect `fork_turns = "none"`
- corrupted persisted `ACCEPTED` truth
- stale attempt authority after a newer attempt exists
- initial fan-out expansion without accepted progress
- independent release readiness that ignores overall Doctor health

The red tests are expected to fail until the corresponding RC3 production changes land. Existing tests that encode the opposite behavior MUST be corrected during the owning remediation commit.

## Gate 2: Repository adversarial gate

After each remediation area is green, inspect the end-to-end path across module seams rather than relying only on isolated helpers.

Minimum path:

`ExecutionBinding -> managed invocation -> PendingControl -> Guard -> acknowledgement -> WriterLease -> WorkUnit acceptance -> scheduler refill`

For each HIGH or CRITICAL invariant, verify both the intended path and at least one hostile cross-module counterexample.

## Gate 3: Real Host gate

The final frozen RC3 candidate MUST pass the existing H00-H10 Host campaign plus RC3 additions H11-H20:

- H11: managed Sol child lifecycle delegation is blocked by V4 policy
- H12: managed Terra child lifecycle delegation is blocked by V4 policy
- H13: every physical profile activates the expected effective model, effort, permissions, and tools
- H14: Luna child behaves as the expected Host leaf capability
- H15: fresh assignment delivery is complete and parallel sibling assignments remain isolated
- H16: same-child follow-up preserves native child identity and effective profile
- H17: duplicate, delayed, and out-of-order lifecycle Hook delivery is fail-closed or idempotent as specified
- H18: scheduler capacity remains correct with mixed managed and unmanaged Host children
- H19: Host/release evidence bound to candidate A is rejected for candidate B
- H20: Windows effective path aliases, including case-insensitive and supported reparse-point aliases, cannot bypass canonical write-scope authority; unclassifiable aliases fail closed

Issue reports or repository mocks do not replace these Host checks.

## Gate 4: Fresh Final Review

After all deterministic and Host verification is green:

1. Freeze the candidate.
2. Record exact commit SHA and tree SHA.
3. Bind the review artifact identity.
4. Launch a fresh read-only Sol High Advisor with `fork_turns = "none"`.
5. Require a `ship` verdict for the exact candidate.
6. Reverify the artifact identity after review.
7. Run the authoritative Doctor release check.

Any candidate mutation invalidates the prior Final Review verdict and requires the affected verification and review steps to run again.

## Release verdict

Unresolved CRITICAL findings result in `NO-GO`.

Unresolved HIGH authority, correctness, provenance, or release-identity findings on a production path result in `NO-GO`.

Mandatory Host probes that are not complete prevent `GO`.
