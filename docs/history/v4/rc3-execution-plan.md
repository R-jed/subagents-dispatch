> Historical archive. This document records a superseded design/review state. It is not a current V4 contract, implementation guide, release gate, or source of runtime authority. Use current `contracts/`, current non-history `docs/`, and `docs/v4/` for present behavior.

# Native Core V4 RC3 Execution Plan

Baseline:

- base branch: `v4/rc2-adversarial-remediation`
- base commit: `3f69f6c3f3f7e844104cd24328c555b0c433fbbf`
- base tree: `2bc2f8a585cacea28e8ca37020e886405d14acac`
- RC3 branch: `v4/rc3-integrity-closure`

Execution order:

1. Lock adversarial red contracts and RC3 normative contracts.
2. Enforce canonical managed execution construction and independent Guard verification.
3. Establish current-execution, acceptance, lifecycle acknowledgement, and duplicate-event truth.
4. Correct progressive fan-out semantics and canonical path authority.
5. Replace caller assertions with authoritative Host evidence ingestion and settlement provenance.
6. Close Doctor and release identity into one authoritative predicate.
7. Run repository regression, cross-platform checks, Real Host H00-H19, candidate freeze, and fresh Final Review.

At each implementation stage:

- preserve fixed Luna Max, Terra High, and Sol High routing;
- keep the public product surface limited to Orchestrate and Doctor;
- run the smallest targeted test set that proves the changed invariant;
- run the wider V4 regression suite before advancing;
- review changed tests for weakened assertions or tests that codify the implementation instead of the contract;
- stop and return to architecture review if the Host evidence surface cannot support the required provenance boundary.

RC3 does not add dynamic reasoning-effort routing, nested managed delegation, new public Skills, a daemon scheduler, or speculative execution.
