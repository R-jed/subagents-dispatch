# Repository Architecture

This document defines the target repository organization for subagents-dispatch. The repository should read like the product architecture: user-facing Skills at the edge, shared orchestration contracts in one place, deterministic helpers in one place, one narrow Host Hook at the action boundary, explicit evidence/experiment tooling outside the ordinary runtime path, and Codex Native Subagents as the only Agent runtime.

## Design principles

1. The Codex Plugin package is obvious from the repository root.
2. User-facing actions are first-class Skills, not hidden payload grammar.
3. Shared orchestration semantics are independent of any one Skill folder.
4. One concept has one canonical owner.
5. Deterministic invariants move into code when code can enforce them more reliably than prose.
6. Codex Native Subagents remain the runtime. The project does not introduce another scheduler, daemon, event bus, routing proxy, MCP control plane, control server, or telemetry collector.
7. A Host Hook is added only when its event boundary provides a capability the Skill layer cannot mechanically guarantee at the same point.
8. Runtime evidence, composition, context/evidence handoff, and experiments are separate planes rather than conditionals scattered through every Skill.
9. Public docs, AI orientation, runtime contracts, deterministic helpers, tests, and evaluation fixtures stay visibly separate.
10. Experimental results never mutate runtime policy automatically. Policy changes happen only after accepted evidence.

## Target tree

```text
subagents-dispatch/
├── .agents/plugins/marketplace.json
├── .codex-plugin/plugin.json
├── .github/workflows/ci.yml
├── agent-profiles/
│   ├── subagents-dispatch-reader.toml
│   ├── subagents-dispatch-worker.toml
│   ├── subagents-dispatch-solver.toml
│   ├── subagents-dispatch-investigator.toml
│   └── subagents-dispatch-advisor.toml
├── hooks/
│   ├── hooks.json
│   ├── run-python.sh
│   └── run-python.cmd
├── contracts/
│   ├── policy.json
│   ├── routing.md
│   ├── composition.md
│   ├── interaction.md
│   ├── state.md
│   ├── receipt.md
│   ├── team-plan.md
│   ├── recovery.md
│   ├── guardrails.md
│   ├── handoff.md
│   ├── evidence-artifact.md
│   └── final-review.md
├── docs/
│   ├── architecture.md
│   ├── behavioral-evals.md
│   ├── experiment-protocol.md
│   ├── native-subagent-runtime.md
│   ├── openai-references.md
│   ├── plugin-installation.md
│   ├── release-checklist.md
│   ├── repository-architecture.md
│   └── runtime-attestation.md
├── evals/
├── scripts/
│   ├── dispatch_state.py
│   ├── doctor.py
│   ├── doctor_core.py
│   ├── spawn_guard.py
│   ├── inspect-agent-runtime.py
│   ├── install-agents.py
│   ├── uninstall-agents.py
│   ├── legacy_migration.py
│   ├── policy.py
│   ├── review-artifact.py
│   ├── runtime-evidence.py
│   └── ...
├── skills/
│   ├── dispatch/
│   ├── preview/
│   ├── status/
│   ├── steer/
│   ├── takeover/
│   └── doctor/
├── tests/
├── README.md
├── README_EN.md
└── README_AI.md
```

Legal files, changelog, assets, and development metadata remain at the repository root when they are part of the package/public project.

Do not add MCP, additional hooks, servers, databases, storage layers, or source-runtime trees merely to resemble another Plugin. Add a component only when subagents-dispatch owns a concrete capability and the simpler native/Skill path cannot provide the same value.

## Four planes plus one action-boundary guard

```text
Runtime Evidence Plane
-> prove what actually ran
-> docs/runtime-attestation.md
-> scripts/inspect-agent-runtime.py
-> scripts/runtime-evidence.py

Composition Plane
-> define how Host capability, current authority, project instructions,
   external Skills/workflows, Hooks, Dispatch guardrails, and role contracts compose
-> contracts/composition.md

Handoff / Claims Plane
-> compact child-to-Main context with inspectable provenance
-> contracts/handoff.md
-> contracts/evidence-artifact.md
-> scripts/review-artifact.py

Experiment Plane
-> freeze real experiments before execution
-> docs/experiment-protocol.md
-> evals/

Action-boundary Guard
-> optional synchronous PreToolUse(spawn_agent)
-> hooks/hooks.json
-> scripts/spawn_guard.py
-> reads prepared state and policy; does not become orchestration truth
```

The planes meet at explicit boundaries. Runtime Evidence can feed an experiment or release artifact, but ordinary Dispatch does not scan rollouts. Evidence Artifacts do not become active state. Experiments may recommend a role-policy change, but they never rewrite `policy.json` automatically.

The spawn guard consumes existing policy plus `SPAWN_PENDING` state. It has no durable state of its own and cannot create, settle, retry, reroute, or adopt a child.

## Skill surface

The Plugin exposes six explicit user-facing Skills:

```text
dispatch
preview
status
steer
takeover
doctor
```

Each Skill owns only its user intent, minimal entry/completion contract, App metadata, and which shared contracts it needs. Shared orchestration semantics live under `contracts/`.

Each Skill has `SKILL.md` plus `agents/openai.yaml`, with implicit invocation disabled. The App-visible namespace and literal slash presentation are Host/UI facts and are published only from direct observation.

`preview`, `status`, `steer`, and `takeover` stay thin over the interaction/state contracts. `doctor` stays thin over deterministic diagnostics and explicit managed-profile lifecycle helpers. `dispatch` leads orchestration but does not keep private copies of shared runtime policy.

## Contract ownership map

```text
contracts/policy.json
-> machine-readable hard invariants, fresh-context requirement, and five configured routes

contracts/routing.md
-> delegation value, role selection, responsibility packets, semantic coverage, ready frontier

contracts/composition.md
-> Host / authority / project rules / upstream workflow / Hook / role boundaries

contracts/interaction.md
-> Preview / Status / Steer / Takeover semantics and target resolution

contracts/state.md
-> thread-scoped ephemeral coordination continuity and Host reconciliation

contracts/receipt.md
-> orchestration accounting and presentation

contracts/team-plan.md
-> multi-responsibility identity, dependencies, structural ownership, revisions

contracts/recovery.md
-> delegated attempt identity, lifecycle, retries, UNKNOWN / INTERRUPTED, Main takeover

contracts/guardrails.md
-> authority, trust, mutation permission, writer safety, consent

contracts/handoff.md
-> compact Main-accepted evidence transfer

contracts/evidence-artifact.md
-> optional references-first evidence bundles outside conversational context

contracts/final-review.md
-> exact-candidate independent review
```

Codex owns project-instruction discovery and precedence. subagents-dispatch does not parse a parallel AGENTS hierarchy.

## Deterministic helper ownership

```text
scripts/policy.py
-> shared policy loading

scripts/dispatch_state.py
-> compact thread-scoped state, locking, reconciliation, control targeting, cleanup, receipt primitives

scripts/spawn_guard.py
-> read-only validation of a proposed reserved managed spawn against prepared state

scripts/doctor_core.py
-> deterministic ten-layer production diagnostics and user-facing rendering

scripts/doctor.py
-> CLI, explicit lifecycle actions, legacy status, and Experiment Plane compatibility adapter

scripts/install-agents.py
-> managed Agent profile install/check lifecycle

scripts/uninstall-agents.py
-> ownership-aware managed Agent profile removal

scripts/inspect-agent-runtime.py
-> explicit exact-child rollout inspection with allowlisted route/identity/permission output

scripts/runtime-evidence.py
-> Configured / Requested / Accepted / Observed normalization and conflict quarantine

scripts/validate_team_plan.py
-> TeamPlan structure validation

scripts/validate_team_ledger.py
-> delegated lifecycle/recovery ledger validation

scripts/review-artifact.py
-> exact-candidate review binding
```

These helpers enforce deterministic facts from canonical contracts or frozen experimental input. They do not own adaptive routing policy and do not become a background runtime.

## Spawn guard boundary

The Plugin uses Codex's default `hooks/hooks.json` discovery path. The manifest stays compatible with the pinned official OpenAI Plugin validator and does not add a parallel Hook registration mechanism.

The current Hook surface is exactly one synchronous `PreToolUse` matcher for `spawn_agent`. It validates only reserved `subagents_dispatch_*` traffic. It mechanically checks `fork_turns=none`, exact role binding, prepared native task identity, delegation depth, and unresolved takeover state.

Unrelated Agent traffic passes through. A failed or unavailable Hook does not create a replacement child or retry. The Skill and contract path remains the baseline correctness mechanism.

`PostToolUse(spawn_agent)` is not used to bind child identity because current Host output does not provide the exact child/thread identity required by the state contract. Native Host reconciliation therefore remains authoritative.

## Runtime Evidence Plane

Configured route intent, Host acceptance, and observed runtime facts are distinct.

```text
policy.json / managed profile
-> configured intent

actual spawn request / Host role acceptance
-> requested / accepted identity

public Host runtime metadata
-> preferred observed evidence

exact Host-produced child rollout, inspected explicitly when required
-> local observed fallback
```

When public Host metadata and exact rollout expose the same fact, they must agree. Missing evidence stays UNKNOWN. Configuration never fills an Observed field.

## Composition Plane

Effective child action is an intersection:

```text
Host capability/policy
∩ current system/developer/user authority
∩ applicable project instructions
∩ accepted upstream Skill/workflow contract
∩ Dispatch guardrails
∩ bounded role/responsibility packet
```

A lower layer may narrow, never widen.

Hooks may improve observation or stop a proposed action when the Host provides a trusted blocking Hook. Hook output does not replace native child identity/state reconciliation, ownership settlement, or runtime attestation.

## Handoff / Claims Plane

Fresh child context remains the default. The return packet is an index, not an evidence dump.

```text
child claim + compact refs
-> Main inspects actual evidence
-> Main accepts supported truth
-> small reusable truth goes to a Handoff Capsule
-> substantial provenance stays in an Evidence Artifact and is referenced
```

A child cannot self-promote a path or manifest into Main-accepted evidence.

## Experiment Plane

The Experiment Plane is development/research infrastructure. Role calibration changes model/effort for a fixed role contract. Product benchmark compares ordinary single-agent work with explicit Dispatch on controlled real tasks.

Formal model/effort calibration has no shared `config.toml` mutation path. Experiments never edit production policy automatically and do not become ordinary Doctor product-health layers.

## Hard invariants versus adaptive policy

Hard invariants include:

```text
delegation depth is one
project child fresh context requires fork_turns=none
user authority never widens implicitly
UNKNOWN is not FAILED
runtime route claims require evidence at the claimed proof level
one active writer owns the canonical mutation domain by default
exact-candidate review binding
no duplicate active responsibility ownership
```

Adaptive policy includes whether delegation adds value, which role fits, how many responsibilities are worth delegating, whether TeamPlan is needed, whether Final Review is warranted, and whether Main should keep the work.

There is no minimum Subagent count. Zero children is derived when delegation adds insufficient value. Native Host capacity is a ceiling, never a target.

## Ephemeral state and artifact boundary

Cross-turn Status, Steer, Takeover, and Dispatch resume use the bounded thread-scoped state governed by `contracts/state.md`. Normal state is under the OS temporary directory and normal completion removes `active.json`.

The spawn guard only reads this existing state. It does not add another capsule, log, database, or receipt ledger.

Evidence Artifacts, when needed, are a separate on-demand temporary namespace governed by `contracts/evidence-artifact.md`. They are not embedded into `active.json`, and artifact age never proves an unresolved writer stopped.

## Doctor architecture

Doctor covers exactly ten production layers:

```text
Plugin
Skills
Spawn guard package
Managed Agent profiles
Dispatch state
Codex Host
Spawn guard runtime
Runtime route
Effective permission state
Permission-source provenance
```

`doctor_core.py` owns these deterministic diagnostic semantics and rendering. `doctor.py` owns CLI parsing and explicit lifecycle actions. Runtime Hook trust/discovery is never inferred from packaged `hooks.json`; without explicit Host evidence it stays `UNKNOWN`.

Calibration readiness remains an Experiment Plane check and appears only under optional development checks.

Diagnosis is read-only by default. Live route smoke, repair, managed-profile uninstall, cleanup, migration, and other expensive/mutating diagnostics require explicit intent.

## Documentation boundary

```text
README.md / README_EN.md
-> concise product/user workflow

README_AI.md
-> orientation index and owner map

docs/architecture.md
-> behavioral architecture

docs/repository-architecture.md
-> package organization and plane ownership

docs/native-subagent-runtime.md
-> native Host boundary

docs/runtime-attestation.md
-> actual child route proof

docs/experiment-protocol.md
-> role calibration, product benchmark, policy promotion

docs/release-checklist.md
-> release gates and direct human UI/runtime evidence requirements
```

Historical changelog text remains historical and is not rewritten to match later terminology.

## Development workflow

For the current single-maintainer phase:

```text
short-lived feature branch
-> local full validation where available
-> adversarial/deep review
-> repair on the same branch
-> full revalidation
-> direct merge into main or reviewed pull request
-> GitHub Actions cross-platform confirmation
```

Pull requests are optional rather than a required integration mechanism. Force-push and deletion protection for `main` remain useful safety boundaries.
