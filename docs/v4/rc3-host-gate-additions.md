# RC3 Real Host Gate Additions

The existing H00-H10 campaign remains mandatory. RC3 adds H11-H19.

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
