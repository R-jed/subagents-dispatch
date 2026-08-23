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

Main keeps the user goal, decomposition, fixed-profile selection, dispatch judgment, integration, WorkUnit acceptance, irreversible external effects and final response.

## Fixed managed profiles

| Profile | Model / effort | Ordinary authority |
| --- | --- | --- |
| Reader | Luna Max | none |
| Worker | Luna Max | bounded source write when granted |
| Investigator | Terra High | none |
| Solver | Sol High | bounded source write when granted |
| Advisor | Sol High | none |

Main selects from these fixed profiles. The runtime does not use a dynamic model or reasoning-effort ladder.

Fresh managed children use `fork_turns=none`. Main is the sole managed coordinator. Managed children must not create or control another Agent layer. The product ceiling is four active managed children, and four is a safety ceiling rather than a utilization target.

## Responsibility and acceptance

WorkGraph and WorkUnit own responsibility structure, dependencies and acceptance truth. ExecutionBinding represents one concrete managed attempt and generation. WriterLease represents managed write ownership for the canonical mutable workspace.

Host `COMPLETED` produces candidate work only. Main verifies the artifact and evidence before a WorkUnit becomes `ACCEPTED`; dependencies unlock from acceptance, not directly from Host lifecycle state.

`UNKNOWN` is fail closed. Ambiguous materialization, stale lifecycle evidence or uncertain writer ownership cannot authorize conflicting replacement work, writer transfer or final acceptance.

## Native lifecycle boundary

The current Native Core uses Codex lifecycle primitives directly. It does not introduce a second Agent runtime, daemon scheduler, background heartbeat, private Host occupancy ledger or persistent lifecycle database.

A fresh managed spawn validates responsibility, fixed profile and write authority before Host activation. Same-child steering, correction and continuation preserve the existing ExecutionBinding where the corresponding contract allows it. Interrupt acknowledgement alone never releases WriterLease; current-generation Host settlement is required.

Detailed lifecycle and first-use behavior remain in `docs/native-subagent-runtime.md`. Runtime evidence and bounded rollout inspection are documented in `docs/runtime-attestation.md`.

## Scheduling and writer ownership

Scheduling helpers project constraints such as the ready frontier, active managed count, known Host capacity and WriterLease state. They do not rank WorkUnits or emit automatic launch decisions.

The current product has one canonical managed writer per mutable workspace. Planned disjoint file lists do not prove physical or semantic isolation. The reasoning and future isolated-workspace boundary are documented in `docs/writer-boundary.md`.

## Host truth and managed depth

Profile configuration and project depth policy express product intent. Effective collaboration capability remains a Host fact.

Current Codex MultiAgent V2 can expose latent recursive capability to V2-capable child models. Revised N1 therefore checks what the product actually promises: every fixed managed profile is exercised through the canonical managed route with the no-further-Agent assignment boundary, including adversarial input that asks for nested delegation. Managed child Agent creation/control or descendant materialization fails N1; ambiguous evidence is `UNKNOWN`.

The machine Host campaign is `docs/v4/host-smoke.json`. Repository CI cannot substitute for required real-Host observations.

## Repository ownership

Current ownership is intentionally concentrated:

```text
contracts/
  product contracts and safety semantics

scripts/
  deterministic Native Core and installed-product helpers

agent-profiles/
  fixed managed Agent requests

skills/
  Orchestrate and Doctor public surfaces

docs/v4/architecture.json
  complete machine runtime-owner map

docs/v4/host-smoke.json
  real-Host release campaign contract
```

Human documents describe how to use or reason about those owners. They should not maintain a second path inventory or parallel machine projection.

## Release boundary

Repository tests establish deterministic implementation behavior. Real Host N0-N8 establishes the Host behavior the release depends on. Final Review, installed-product verification and external evidence bind to the exact candidate after those earlier gates are satisfied.

The release sequence is maintained in `docs/release-checklist.md`. New development sessions should read root `headoff.md` first for project background, important workflow history, current progress and next direction. Historical design records belong in Git history and `docs/history/`.
