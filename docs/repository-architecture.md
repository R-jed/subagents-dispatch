# Repository Architecture

This document defines the target repository organization for subagents-dispatch. The repository should read like the product architecture: user-facing Skills at the edge, shared orchestration contracts in one place, deterministic helpers in one place, explicit evidence/experiment tooling outside the ordinary runtime path, and Codex Native Subagents as the only Agent runtime.

## Design principles

1. The Codex Plugin package is obvious from the repository root.
2. User-facing actions are first-class Skills, not hidden payload grammar.
3. Shared orchestration semantics are independent of any one Skill folder.
4. One concept has one canonical owner.
5. Deterministic invariants move into code when code can enforce them more reliably than prose.
6. Codex Native Subagents remain the runtime. The project does not introduce another scheduler, daemon, event bus, routing proxy, control server, or telemetry collector.
7. Runtime evidence, composition, context/evidence handoff, and experiments are separate planes rather than conditionals scattered through every Skill.
8. Public docs, AI orientation, runtime contracts, deterministic helpers, tests, and evaluation fixtures stay visibly separate.
9. Experimental results never mutate runtime policy automatically. Policy changes happen only after accepted evidence.
10. Inside an unreleased architecture change, migrate a concept once and remove the superseded path rather than carrying compatibility shells.

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
│   ├── behavioral-workloads.json
│   ├── behavioral-result.schema.json
│   ├── experiment-campaign.schema.json
│   └── ...
├── scripts/
│   ├── dispatch_state.py
│   ├── doctor.py
│   ├── inspect-agent-runtime.py
│   ├── install-agents.py
│   ├── uninstall-agents.py
│   ├── legacy_migration.py
│   ├── policy.py
│   ├── review-artifact.py
│   ├── runtime-evidence.py
│   ├── score-behavioral-evals.py
│   ├── validate-experiment-campaign.py
│   ├── validate_team_ledger.py
│   └── validate_team_plan.py
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

Legal files, changelog, assets, and development metadata remain at the repository root when they are part of the package/public project. They are omitted above only to keep the architectural tree focused.

Do not add MCP, hook, server, database, storage, or source-runtime trees merely to resemble another Plugin. Add a top-level component only when subagents-dispatch genuinely owns that capability.

## Four-plane architecture

The A–G hardening work is deliberately collapsed into four planes instead of seven independent feature stacks.

```text
Runtime Evidence Plane
-> prove what actually ran
-> docs/runtime-attestation.md
-> scripts/inspect-agent-runtime.py
-> scripts/runtime-evidence.py

Composition Plane
-> define how Host capability, current authority, project instructions,
   external Skills/workflows, hooks, Dispatch guardrails, and role contracts compose
-> contracts/composition.md

Handoff / Claims Plane
-> keep child-to-Main context compact while preserving complete inspectable provenance by reference
-> contracts/handoff.md
-> contracts/evidence-artifact.md
-> scripts/review-artifact.py for exact Git candidate identity

Experiment Plane
-> freeze real experiments before execution
-> role_calibration: fixed role contract, model/effort route is the independent variable
-> formal model_effort materialization: two profile-only Agent TOMLs in the confirmed active normal Host home; exact origin/SHA and frozen provider are claim gates; no Marketplace, Plugin, config.toml, or alternate CODEX_HOME state
-> product_benchmark: fixed real task/environment, single_agent vs dispatch is the independent variable
-> docs/experiment-protocol.md
-> evals/experiment-campaign.schema.json
-> scripts/validate-experiment-campaign.py
-> reuse scripts/score-behavioral-evals.py where its paired result schema applies
```

The planes meet at explicit boundaries. Runtime Evidence can feed an experiment or release artifact, but ordinary Dispatch does not scan rollouts. Evidence Artifacts may preserve accepted runtime/verification/benchmark provenance, but they do not become active state. Experiments may recommend a role-policy change, but they never rewrite `policy.json` automatically.

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

Dispatch loads `composition.md` when Host/project-rule/external-Skill/hook composition matters. It loads `evidence-artifact.md` only when complete accepted provenance should remain outside inline conversational context.

## Contract ownership map

```text
contracts/policy.json
-> machine-readable hard invariants and current five configured routes

contracts/routing.md
-> delegation value, role selection, responsibility packets, semantic coverage, phase recompilation, ready frontier

contracts/composition.md
-> Host / current authority / project rules / upstream Skill/workflow / hook / role-contract boundaries

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

`composition.md` does not reimplement Codex project-instruction precedence. It consumes the Host-effective constraint surface. Hooks are optional observer/guard inputs and are not a required runtime path.

`evidence-artifact.md` does not turn the repository or `active.json` into a log store. Artifact creation is on demand, separate from coordination state, and references-first.

## Deterministic helper ownership

```text
scripts/policy.py
-> shared policy loading

scripts/dispatch_state.py
-> compact thread-scoped state, locking, reconciliation, control targeting, cleanup, receipt primitives

scripts/doctor.py
-> deterministic eight-layer diagnostics

scripts/install-agents.py
-> managed Agent profile install/check lifecycle

scripts/uninstall-agents.py
-> ownership-aware managed Agent profile removal using the install manifest and installer lock

scripts/inspect-agent-runtime.py
-> explicit exact-child rollout inspection with allowlisted route/identity/permission output

scripts/runtime-evidence.py
-> configured/requested / accepted / observed normalization and conflict quarantine

scripts/validate_team_plan.py
-> TeamPlan structure validation

scripts/validate_team_ledger.py
-> delegated lifecycle/recovery ledger validation

scripts/review-artifact.py
-> exact-candidate Git review binding

scripts/validate-experiment-campaign.py
-> validate/freeze a typed experiment campaign against the exact current candidate

scripts/score-behavioral-evals.py
-> validate/summarize paired behavioral results; no hidden global quality score
```

These helpers enforce deterministic facts from canonical contracts or frozen experimental input. They do not own adaptive routing policy and do not become a background runtime.

The experiment validator does not run Agents, score results, or edit `policy.json`. The existing paired behavioral scorer is reused where its result schema fits rather than creating a second generic benchmark engine.

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
-> local observed fallback for fields the public Host surface omits
```

When public Host metadata and the exact rollout expose the same fact, they must agree. Missing evidence stays UNKNOWN. Configuration never fills an Observed field.

Exact local rollout evidence is inspectable Host-produced runtime evidence. It is not cryptographically signed and is not claimed to be tamper-proof.

Ordinary Dispatch does not run the rollout inspector merely to manufacture certainty.

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

Codex owns project-instruction discovery and precedence. subagents-dispatch does not parse a parallel AGENTS hierarchy. If a fresh child may not inherit a material project constraint, Main carries only the narrow material constraint/source ref it needs.

Hooks may improve observation or stop an action when the Host provides a trusted blocking hook, but ordinary product correctness does not depend on hook presence or ordering. Hook output does not replace native child identity/state reconciliation or runtime attestation.

## Handoff / Claims Plane

Fresh child context remains the default. The return packet is an index, not an evidence dump.

```text
child claim + compact refs
-> Main inspects actual evidence
-> Main accepts supported truth
-> small reusable truth goes to a Handoff Capsule
-> substantial reusable provenance stays in an Evidence Artifact and is referenced
```

A child cannot self-promote a manifest/path into Main-accepted evidence.

Evidence Artifacts prefer stable source/revision/digest refs over copied bytes. Raw transcripts, hidden reasoning, whole repositories, unrelated source, credentials, and unbounded tool output are outside the artifact contract.

There is no universal child-return token target yet. Context discipline first removes duplication and reconstructable data; real product benchmarks can later establish whether a tighter numeric budget improves the measured tradeoff.

## Experiment Plane

One common campaign envelope contains one typed experiment spec.

### Role calibration

Role calibration holds responsibility semantics and sandbox/isolation fixed while changing model/effort. The current `policy.json` route is the control. A challenger cannot silently widen sandbox authority.

Shared `config.toml` remains user-owned. Formal model/effort calibration has no shared `config.toml` mutation path. It requires `shared_config_mutations=[]`, and profile-only preparation rejects Marketplace, Plugin, shared-config, or alternate-home setup. If a future workflow genuinely requires shared-config mutation, design and validate that capability when the requirement exists instead of carrying an unreleased transaction shell. Filesystem ownership remains exact-path and wildcard-free.

Actual model/effort conclusions require runtime-attested runs. `UNKNOWN` cannot support a claim that a specific route produced a measured outcome.

### Product benchmark

Product benchmark holds the real task/environment fixed and compares ordinary `single_agent` with explicit `dispatch`.

Workloads are classified by task stratum, not by a predeclared Agent role. Dispatch may use zero or several project children according to normal routing; actual role use is result/runtime evidence.

The paired controls bind exact task bytes, repository/base revision, Main route, permissions, tools, project rules, Host/runtime, reset procedure, and acceptance oracle.

### Formal experiment discipline

A formal campaign uses real repositories/tasks, an exact candidate SHA, and at least three completed repeats per arm. Three is a minimum replication rule, not a guarantee that variance is small enough.

Correctness and safety dominate quality, correction/rework, context efficiency, latency, and exact token use in that order. Missing token/time telemetry stays missing rather than being estimated.

A role-policy promotion requires predeclared criteria and explicit maintainer acceptance. The benchmark never edits policy by itself.

README performance claims are downstream of accepted formal evidence. Synthetic fixtures and exploratory runs remain internal evidence about the evaluator, not public superiority claims.

## Hard invariants versus adaptive policy

Hard invariants include:

```text
delegation depth is one
user authority never widens implicitly
UNKNOWN is not FAILED
runtime route claims require evidence at the claimed proof level
one active writer owns the canonical mutation domain by default
exact-candidate review binding
no duplicate active responsibility ownership
```

Adaptive policy includes:

```text
whether delegation adds value
which specialized role fits a responsibility
how many independent responsibilities are worth delegating
whether TeamPlan is needed
whether independent Final Review is warranted by consequences
whether Main should keep the work
```

Do not encode adaptive policy as arbitrary numeric team-size targets.

There is no minimum Subagent count. Zero children is derived when delegation adds insufficient value. There is no ordinary project-level child maximum; native Host capacity is a ceiling, never a target.

The current writer policy remains semantic `single_writer` for the canonical workspace. Future parallel writers require real isolated workspaces plus semantic independence or explicit dependency/integration ownership; a tunable writer count is not a substitute.

## Ephemeral state and artifact boundary

Cross-turn Status, Steer, Takeover, and Dispatch resume use the bounded thread-scoped state governed by `contracts/state.md`. Normal state is under the OS temporary directory and normal completion removes `active.json`.

Evidence Artifacts, when needed, are a separate on-demand temporary namespace governed by `contracts/evidence-artifact.md`. They are not embedded into `active.json`, and artifact age never proves an unresolved writer stopped.

## Doctor architecture

Doctor covers exactly eight layers:

```text
Plugin
Skills
Managed Agent profiles
Dispatch state
Codex Host
Runtime route
Effective permission state
Permission-source provenance
```

Diagnosis is read-only by default. Live route smoke, repair, managed-profile uninstall, cleanup, migration, and other expensive/mutating diagnostics require explicit intent. Static configuration health is separate from runtime observation.

## Documentation boundary

```text
README.md / README_EN.md
-> concise product/user workflow; public claims limited to accepted evidence

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
-> role calibration, product benchmark, policy promotion, README publication gate

docs/release-checklist.md
-> release gates and direct human UI/runtime evidence requirements
```

Historical changelog text remains historical and is not rewritten to match later terminology.

## Development workflow

For the current single-maintainer phase:

```text
short-lived feature branch
-> local full validation
-> adversarial/deep review
-> repair on the same branch
-> local revalidation
-> direct merge into main
-> push main
-> GitHub Actions cross-platform confirmation
```

Pull requests are optional rather than a required integration mechanism. Force-push and deletion protection for `main` remain useful safety boundaries.
