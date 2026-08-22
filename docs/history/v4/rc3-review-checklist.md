> Historical archive. This document records a superseded design/review state. It is not a current V4 contract, implementation guide, release gate, or source of runtime authority. Use current `contracts/`, current non-history `docs/`, and `docs/v4/` for present behavior.

# V4.0.0 RC3 Review Checklist

Before advancing each RC3 stage, the reviewer checks:

- the changed invariant is stated in a normative contract;
- the hostile counterexample fails before the production change and passes after it;
- no test weakens the frozen V4 contract to accommodate the implementation;
- state validation is at least as strict as mutation-time validation for authority-bearing facts;
- no caller-supplied digest, boolean, lifecycle string, or evidence reference becomes authoritative without a trusted ingestion path;
- fixed model and effort mappings remain unchanged;
- managed depth remains one by V4 Guard policy rather than Host `max_depth` assumptions;
- UNKNOWN remains fail-closed for writer and replacement authority;
- any candidate mutation after Final Review invalidates the verdict;
- release readiness is derived from one authoritative predicate.

Before release, repeat the checklist from the frozen candidate without relying on remediation history as evidence.
