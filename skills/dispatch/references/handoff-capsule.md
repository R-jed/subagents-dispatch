# Handoff Capsule

A Handoff Capsule is a compact, evidence-bound context bridge between responsibilities in one Subagents Dispatch workflow. It reduces repeated repository discovery while preserving the fresh-context benefits of native Subagents.

The capsule is optional and ephemeral by default. It is not a memory database, transcript summary, second TeamPlan, or persistent project ledger.

## When to use it

Create a capsule only when a later responsibility would otherwise repeat material discovery that Main has already accepted.

Do not create one when:

- the downstream responsibility can proceed safely from its normal packet;
- the source child result has not been verified by Main;
- the information is cheap to rediscover and likely to become stale;
- the capsule would mostly contain narrative reasoning rather than inspectable facts.

## Fresh context remains the default

New project children still use fresh context as required by the dispatch Skill. Do not forward a previous child transcript or full Main history merely to save reads.

The downstream packet may include one small Handoff Capsule containing only accepted task truth that is useful to that responsibility.

## Capsule shape

Use this semantic shape:

```text
HANDOFF CAPSULE
SOURCE UNITS
ARTIFACT REFS
ACCEPTED FACTS
ACCEPTED EVIDENCE
INTERFACES / INVARIANTS
DO NOT REDO
OPEN QUESTIONS
STALE IF
```

Fields are optional when empty except that a useful capsule must contain at least one accepted fact or accepted evidence item.

### SOURCE UNITS

The stable unit ids that produced evidence contributing to this capsule.

### ARTIFACT REFS

The smallest inspectable artifact references needed to orient the next responsibility, such as file paths, symbols, tests, commands, or a candidate artifact identity.

### ACCEPTED FACTS

Only facts Main has independently accepted after checking actual artifacts or other valid evidence.

A child assertion is not an accepted fact merely because the child reported it confidently.

### ACCEPTED EVIDENCE

The evidence that supports the accepted facts, including relevant artifact state, test/build output, or other reproducible checks. Keep enough provenance that the next responsibility can distinguish established truth from an assumption.

### INTERFACES / INVARIANTS

Stable boundaries the downstream responsibility must preserve.

This field cannot create new user requirements or widen decision rights. It carries already-established task truth.

### DO NOT REDO

Specific discovery that valid evidence already satisfies. Use this to suppress redundant repository scans, repeated call mapping, or re-running an expensive check when its result remains valid.

`DO NOT REDO` never forbids verification when the evidence has become stale or when downstream acceptance independently requires the check.

### OPEN QUESTIONS

Unresolved facts or decisions. These remain explicitly unresolved and must not be converted into accepted facts by transmission.

### STALE IF

Conditions that invalidate or weaken the capsule, such as mutation of named source files, a changed API/schema, a new commit, a failed verification, or a superseding TeamPlan revision.

## Main is the acceptance boundary

The safe flow is:

```text
child returns claim/evidence
-> Main inspects actual artifact/evidence
-> Main accepts supported facts
-> Main builds or updates the capsule
-> downstream responsibility receives the capsule
```

Do not pass child-to-child claims directly as settled truth.

If Main cannot verify a material claim, place it under `OPEN QUESTIONS` or omit it.

## Staleness and mutation

A capsule is a snapshot of accepted task truth, not a permanent cache.

Before reusing evidence after relevant mutation, Main checks whether any `STALE IF` condition is met. When staleness is plausible, re-read or re-run the narrow evidence needed to restore confidence.

If downstream work mutates an artifact that supported the capsule, facts depending on the old artifact state lose their accepted status until reverified.

## Authority boundary

A capsule cannot grant:

```text
write ownership
mutation authority
permissions
broader user scope
new external actions
role escalation
acceptance changes
```

Those remain owned by the normal responsibility packet, TeamPlan when active, Guardrails, and Main.

## Compactness

Prefer the smallest capsule that prevents meaningful duplicated discovery. Do not impose a fixed token target until behavioral evaluation establishes one.

Avoid:

- raw chain-of-thought;
- raw transcripts;
- large logs;
- copied source files;
- generic project summaries;
- speculative design narratives.

If the capsule grows large enough to resemble a second context history, discard it and send a smaller evidence packet instead.

## Relationship to return packets

The normal child return packet remains authoritative for what that child claims and produced. A Handoff Capsule is created only from the subset that Main accepts and expects another responsibility to reuse.

This distinction prevents unverified Agent claims from becoming inherited task truth.
