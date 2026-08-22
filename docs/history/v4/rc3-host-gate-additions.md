> Historical archive. This document records a superseded design/review state. It is not a current V4 contract, implementation guide, release gate, or source of runtime authority. Use current `contracts/`, current non-history `docs/`, and `docs/v4/` for present behavior.

# RC3 Real Host Gate Additions

The existing H00-H10 campaign remains mandatory. RC3 adds H11-H20.

## H11 Managed Sol recursion containment

Spawn a managed Sol child using the production profile. Have the child attempt a lifecycle spawn. The V4 production Guard must block the call before nested managed work is created.

## H12 Managed Terra recursion containment

Repeat H11 with the managed Terra profile.

## H13 Physical profile activation

For Reader, Worker, Investigator, Solver, and Advisor, observe the actual effective child configuration and verify model, reasoning effort, permissions, and relevant tool surface against the authoritative profile contract.

## H14 Luna leaf capability

Verify the target Host exposes Luna as the expected leaf execution capability for the installed Codex version. Record actual child tool visibility. Do not infer this probe solely from repository model metadata.

## H15 Fresh assignment delivery and isolation

With `fork_turns = "none"`, verify each child receives the intended canonical assignment, performs it, and does not receive a sibling's assignment when parallel children are active.

## H16 Same-child identity continuity

Spawn, complete, follow up, interrupt when applicable, and reactivate the same managed child. Verify native child identity and effective profile do not drift.

## H17 Hook delivery semantics

Exercise duplicate, delayed, and out-of-order lifecycle Hook delivery. The exact duplicate successful event must be idempotent. Ambiguous or stale events must fail closed without creating a new authority fact.

## H18 Mixed Host capacity

Create a mixture of managed and unmanaged open children. Verify scheduler admission uses actual Host occupancy and does not over-admit from V4 state alone.

## H19 Candidate-bound evidence

Capture valid Host/release evidence for candidate A. Change the candidate identity without re-running the campaign. Candidate B must reject A's evidence.

## H20 Windows effective path aliases

On a Windows Host, verify canonical repository-relative scope enforcement against effective filesystem aliases that cannot be proven by platform-neutral lexical validation alone. Cover case-insensitive aliases and, where available, junction or reparse-point aliases that could identify the same effective target or escape an allowed subtree. Any unclassifiable alias remains fail-closed for write authority.
