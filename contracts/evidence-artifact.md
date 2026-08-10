# Evidence Artifact

An Evidence Artifact is an optional, structured evidence bundle for one Dispatch responsibility, integrated candidate, review, runtime attestation, or evaluation run.

Its purpose is to keep child-to-Main and Main-to-child context small while preserving complete inspectable provenance outside the conversational return packet.

It is not a transcript archive, memory database, second TeamPlan, recovery ledger, task-result summary, or background telemetry store.

## 1. Core pattern

Use references before copies:

```text
child does focused work
-> child returns a compact result plus evidence references
-> Main inspects actual evidence
-> Main accepts or rejects each material claim
-> when the accepted evidence is too large or too reusable for inline context, Main materializes an Evidence Artifact
-> later handoff/review/benchmark receives the artifact ref plus only the facts it needs
```

A child may propose evidence references. Main owns artifact acceptance and sealing.

Do not require a read-only child to write an artifact merely to satisfy the protocol. A Host-native artifact channel may be used when actually available, but it is an adapter, not a project invariant.

## 2. When to create one

Create an Evidence Artifact only when at least one of these is true:

```text
material verification output would otherwise bloat the return packet
several downstream responsibilities need the same accepted evidence
a final reviewer needs an exact candidate/evidence bundle
a runtime-attestation gate needs durable provenance for the current validation session
a real benchmark run needs reproducible inputs/results
```

Do not create an artifact for a trivial result that is already clear from a small diff, one deterministic command, or one narrow source ref.

## 3. Default storage boundary

Ephemeral artifacts belong outside the repository under the same user-scoped OS temporary root used by Dispatch continuity:

```text
<OS TEMP>/subagents-dispatch/<CODEX_THREAD_ID>/artifacts/<artifact-id>/manifest.json
```

Optional attachments, when truly needed, live below that artifact directory.

The repository and project working tree are not implicit artifact stores. A user-requested report, release bundle, benchmark result, or other explicit durable deliverable may be exported to a declared path, but that is a separate authorized output.

If a stable root-thread identity is required to find an ephemeral artifact across turns and the Host does not expose one, do not invent a cwd/repository/random identity fallback.

Evidence artifacts are separate from `active.json`. The active state remains a bounded coordination index and does not absorb evidence payloads.

## 4. Manifest semantics

The manifest is a compact index over evidence. It should contain only the fields required to bind and interpret that evidence:

```text
schema_version
artifact_id
purpose
root_thread_id, when available
created_at
subject
source_units / task / attempt refs, when applicable
candidate_ref, when applicable
evidence entries
acceptance summary
stale_if
```

`artifact_id` binds the canonical manifest plus any project-owned attachment digests. It is an integrity identity, not a signature or a claim that local files are tamper-proof.

### Subject

Describe the smallest thing the artifact proves, such as:

```text
one delegated responsibility
one integrated Git candidate
one independent review input/verdict
one exact child runtime route
one benchmark run
```

Do not use one artifact as a project history bucket.

## 5. Evidence entries

Each material evidence entry should provide enough typed provenance to inspect or reproduce the claim without copying unrelated context.

Recommended semantic fields are:

```text
ref
kind
summary
sha256 or another exact identity when available
producer
accepted_by_main: true | false
observed_at, when time matters
stale_if
attachment_ref, only when a referenced external source cannot preserve required evidence
```

`kind` describes evidence shape, not task semantics. Examples include file/diff identity, command/test result, Host runtime observation, review verdict, external source, and benchmark measurement.

A path alone is not strong evidence when the bytes may change. Bind mutable evidence with an appropriate digest, revision, command/result identity, or other reproducible oracle.

## 6. Attachments

Prefer an existing stable source ref over an attachment.

An attachment is justified when the full evidence cannot otherwise be re-inspected after the producing operation, for example an ephemeral command log or a Host observation that has no stable external identifier.

Attachments must remain scoped to the artifact subject. Do not copy:

```text
raw child or Main transcripts
hidden reasoning / chain-of-thought
whole repositories
unrelated source files
credentials or secrets
browser/session dumps
unbounded tool logs
```

If evidence contains secrets or unrelated user data, redact or omit it before artifact creation. A digest of secret material can itself be sensitive and should not be persisted merely to prove the secret existed.

## 7. Inline child return discipline

The normal return packet in `routing.md` remains compact. It is an index and status report, not the evidence body.

Use the existing fields, with these constraints:

```text
summary
-> only the result Main needs to understand

files_changed
-> paths/refs, not copied file contents

verification
-> command/check + concise outcome; full non-reproducible output belongs in an artifact attachment when material

new_evidence
-> concise evidence refs/facts, not raw logs

evidence_artifact_ref
-> optional, only when an Evidence Artifact was actually materialized and accepted
```

Do not impose a universal token target before live evaluation establishes a useful tradeoff. Compactness is consequence-driven: remove duplicated or reconstructable context first.

## 8. Main acceptance boundary

A child cannot mark its own evidence `accepted_by_main=true` merely by returning a manifest-like object.

The safe flow is:

```text
child claim/ref
-> Main inspects actual artifact/Host/result
-> Main decides which claims are supported
-> Main seals the accepted evidence bundle
```

Unsupported claims stay outside accepted evidence or are explicitly marked unresolved.

An Evidence Artifact cannot grant write authority, decision rights, user scope, broader permissions, role escalation, or final acceptance.

## 9. Relationship to Handoff Capsule

A Handoff Capsule carries the minimum accepted truth a downstream responsibility needs.

When full evidence is substantial:

```text
Handoff Capsule
-> accepted fact
-> evidence_artifact_ref
-> narrow source/artifact refs needed now
-> DO NOT REDO / STALE IF
```

Do not paste the Evidence Artifact body into the capsule. The downstream child inspects the referenced evidence only when its responsibility actually needs it.

This preserves fresh context and progressive disclosure.

## 10. Relationship to Final Review

`review-artifact.py` owns exact Git candidate identity. Evidence Artifact does not replace it.

For an independent review, bind both when useful:

```text
exact review_artifact_id
+ Evidence Artifact containing accepted verification/runtime evidence refs
```

The reviewer still inspects the actual candidate. A verification bundle is supporting evidence, not a substitute for reviewing the deliverable.

## 11. Relationship to Runtime Attestation

`runtime-attestation.md` owns whether a model/effort/sandbox/identity claim is actually observed.

An Evidence Artifact may preserve the resulting normalized attestation and its source refs. It must preserve provenance grades and UNKNOWN/FAIL states exactly. It cannot upgrade configured/accepted values into Observed truth.

## 12. Relationship to Benchmarks

A benchmark Evidence Artifact may bind:

```text
campaign/workload identity
immutable repository base
exact task definition hash
actual route attestation
verification/oracle output
exact token/time telemetry when exposed
quality result
candidate diff/result identity
```

Missing telemetry remains missing. The artifact must not estimate unavailable token, time, model, effort, sandbox, or cost facts.

## 13. Staleness

Evidence reuse is valid only while its dependencies remain unchanged.

`stale_if` should name concrete invalidators such as:

```text
referenced file bytes change
candidate SHA/diff identity changes
verification command or environment changes
Host/runtime version changes when material to the claim
route identity changes
acceptance rubric/oracle changes
upstream contract changes
```

A stale artifact remains historical evidence about its original subject. It stops being current acceptance evidence for the changed subject.

## 14. Lifecycle and cleanup

Ephemeral artifacts are not permanent project memory.

Normal orchestration may remove unneeded temporary artifacts after all dependent handoffs/reviews finish. Interrupted work may retain them with the thread-scoped temporary directory long enough for safe continuation. Stale cleanup must never interpret artifact age as proof that an unresolved writer stopped.

Formal benchmark/release evidence that must survive the temporary lifecycle is exported explicitly to an evaluator/release-owned location. The export is a deliberate deliverable, not a hidden persistence feature.

## 15. No hidden telemetry system

Evidence Artifact is created on demand by the current workflow. It does not watch tasks, scan all sessions, subscribe to an event stream, or upload telemetry in the background.

Ordinary Dispatch remains lightweight when no large/reusable evidence bundle is needed.
