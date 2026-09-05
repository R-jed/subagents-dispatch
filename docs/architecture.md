# Architecture

subagents-dispatch is a bounded orchestration layer over Codex Native Subagents. Codex remains the Agent runtime and the authority for child materialization, lifecycle state, native control results, actual Host capacity, effective permission and effective child collaboration capability.

The complete machine-readable V4 architecture and runtime owner map live in `docs/v4/architecture.json`. This document is the human overview and should not duplicate a second machine contract.

## Product surface

The Plugin exposes exactly two explicit Skills:

```text
Orchestrate
Doctor
```

`Orchestrate` owns user-requested orchestration controls and coordinated engineering work. `Doctor` owns deterministic installed-product diagnosis and explicitly requested ownership-safe maintenance.

Main keeps the user goal, decomposition, semantic classification, dispatch judgment, integration, WorkUnit acceptance, irreversible external effects and final response. Main model/effort never changes a managed route.

## Managed team

| Role | Model / effort | Authority |
| --- | --- | --- |
| Programmer | Luna Max | WorkUnit-defined; may be semantic read or bounded write |
| Product Manager | Sol Medium / High | WorkUnit-defined; Standard Review is fresh/read-only |
| Department Director | Astra High | highest acceptance only; semantic read-only |

The three persistent profiles carry behavior/configuration only. `policy.json` owns exact model/effort, and every managed spawn sends it explicitly. Product Manager uses Medium by default and High only for confirmed material-decision or Standard Review obligations. Department Director appears only after Candidate Ready for highest-consequence acceptance.

Fresh managed children use `fork_turns=none`. Main is the sole managed coordinator. Managed children must not create or control another Agent layer. The product ceiling is four active managed children, and four is a safety ceiling rather than a utilization target.

## Responsibility and acceptance

WorkGraph and WorkUnit own responsibility structure, dependencies and acceptance truth. ExecutionBinding represents one concrete managed attempt and generation. WriterLease represents managed write ownership for the canonical mutable workspace.

Host `COMPLETED` produces candidate work only. Main verifies the artifact and evidence before a WorkUnit becomes `ACCEPTED`; dependencies unlock from acceptance, not directly from Host lifecycle state.

`UNKNOWN` is fail closed. Ambiguous materialization, stale lifecycle evidence or uncertain writer ownership cannot authorize conflicting replacement work, writer transfer or final acceptance.

## Native lifecycle boundary

The current Native Core uses Codex lifecycle primitives directly. It does not introduce a second Agent runtime, daemon scheduler, background heartbeat, private Host occupancy ledger or persistent lifecycle database.

A fresh managed spawn validates responsibility, role, exact policy-backed route and write authority before Host activation. Same-child steering, correction and continuation preserve the existing ExecutionBinding where the corresponding contract allows it. Interrupt acknowledgement alone never releases WriterLease; current-generation Host settlement is required.

Detailed lifecycle and first-use behavior remain in `docs/native-subagent-runtime.md`. Runtime evidence and bounded rollout inspection are documented in `docs/runtime-attestation.md`.

## Scheduling and writer ownership

Scheduling helpers project constraints such as the ready frontier, active managed count, known Host capacity and WriterLease state. They do not rank WorkUnits or emit automatic launch decisions.

The current product has one canonical managed writer per mutable workspace. Multiple semantic-read Programmer/Product Manager responsibilities may overlap; under broader Host permission this requires no active WriterLease plus a before/after artifact-immutability guard. Planned disjoint write lists do not prove physical or semantic isolation. The reasoning and future isolated-workspace boundary are documented in `docs/writer-boundary.md`.

## Host truth and managed depth

Profile configuration and project depth policy express product intent. Effective collaboration capability remains a Host fact.

Current Codex MultiAgent V2 can expose latent recursive capability to V2-capable child models. The Plugin therefore treats depth one as a semantic product boundary: managed role instructions and responsibility packets forbid descendants, but those declarations are not Host-hard containment proof. A task that explicitly requires Host-hard isolation must establish that stronger fact from the current Host or report it unavailable.

Release integration does not repeat a project-owned Host campaign. `docs/v4/host-reference.json` pins mature `sol-advisor` and `astra-advisor` implementations as the release-design basis for explicit native route controls, fresh context, public Host-schema authority, requested-versus-observed separation and fail-closed unavailability. Ordinary runtime observations remain authoritative for the current task.

## Repository ownership

Current ownership is intentionally concentrated:

```text
contracts/
  product contracts and safety semantics

scripts/
  deterministic Native Core and installed-product helpers

agent-profiles/
  three managed behavior/configuration profiles

skills/
  Orchestrate and Doctor public surfaces

docs/v4/architecture.json
  complete machine runtime-owner map

docs/v4/host-reference.json
  pinned mature Host-integration reference contract
```

Human documents describe how to use or reason about those owners. They should not maintain a second path inventory or parallel machine projection.

## Release boundary

Repository tests establish deterministic implementation behavior. The pinned Host-reference contract establishes the mature Native Codex integration assumptions reused by the release, while current runtime Host evidence remains authoritative whenever execution depends on a concrete capability. One separate Department Director / Astra High Final Review binds independent assurance to the exact final release source; installed-product verification and release evidence close the remaining gates.

The release sequence is maintained in `docs/release-checklist.md`. New development sessions should read root `headoff.md` first for project background, important workflow history, current progress and next direction. Historical design records belong in Git history and `docs/history/`.
