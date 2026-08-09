# Repository Architecture

This document defines the target repository organization for subagents-dispatch. The goal is a small, inspectable Codex Plugin whose user-facing Skills remain thin while orchestration contracts and deterministic helpers have clear single owners.

## Design principles

1. The Codex Plugin package is obvious from the repository root.
2. User-facing Skills are discoverable as independent actions.
3. Runtime policy has one canonical owner per concept.
4. Deterministic code lives outside Skill prose when code can enforce the invariant more reliably.
5. Codex Native Subagents remain the runtime. The project does not introduce another scheduler, daemon, event bus, routing proxy, control server, or telemetry collector.
6. Repository layout communicates architecture without requiring README archaeology.
7. Public documentation, internal AI orientation, runtime contracts, tests, and evaluation fixtures remain separate surfaces.

## Target tree

```text
subagents-dispatch/
├── .agents/
│   └── plugins/
│       └── marketplace.json
├── .codex-plugin/
│   └── plugin.json
├── .github/
│   ├── SECURITY.md
│   └── workflows/
│       └── ci.yml
├── agent-profiles/
│   ├── subagents-dispatch-reader.toml
│   ├── subagents-dispatch-worker.toml
│   ├── subagents-dispatch-solver.toml
│   ├── subagents-dispatch-investigator.toml
│   └── subagents-dispatch-advisor.toml
├── docs/
│   ├── architecture.md
│   ├── behavioral-evals.md
│   ├── native-subagent-runtime.md
│   ├── openai-references.md
│   ├── plugin-installation.md
│   ├── release-checklist.md
│   └── repository-architecture.md
├── evals/
├── scripts/
│   ├── dispatch_state.py
│   ├── doctor.py
│   ├── install-agents.py
│   ├── legacy_migration.py
│   ├── policy.py
│   ├── review-artifact.py
│   ├── runtime-evidence.py
│   ├── score-behavioral-evals.py
│   ├── validate_team_ledger.py
│   └── validate_team_plan.py
├── skills/
│   ├── dispatch/
│   │   ├── SKILL.md
│   │   ├── agents/
│   │   │   └── openai.yaml
│   │   └── references/
│   │       ├── dispatch-receipt.md
│   │       ├── dispatch-state.md
│   │       ├── final-review.md
│   │       ├── guardrails.md
│   │       ├── handoff-capsule.md
│   │       ├── interaction.md
│   │       ├── recovery.md
│   │       ├── router-core.md
│   │       └── team-plan.md
│   ├── preview/
│   │   ├── SKILL.md
│   │   └── agents/openai.yaml
│   ├── status/
│   │   ├── SKILL.md
│   │   └── agents/openai.yaml
│   ├── steer/
│   │   ├── SKILL.md
│   │   └── agents/openai.yaml
│   ├── takeover/
│   │   ├── SKILL.md
│   │   └── agents/openai.yaml
│   └── doctor/
│       ├── SKILL.md
│       └── agents/openai.yaml
├── tests/
├── policy-contract.json
├── README.md
├── README_EN.md
└── README_AI.md
```

Do not add placeholder top-level directories merely to imitate another plugin architecture. In particular, do not add MCP, hook, server, storage, or source-runtime trees unless the product genuinely acquires those capabilities.

## Skill surface

The target Plugin exposes six explicit user-facing Skills:

```text
dispatch
preview
status
steer
takeover
doctor
```

Each Skill has its own `SKILL.md` and `agents/openai.yaml`. All are explicit-only and must set `policy.allow_implicit_invocation: false`.

The App-visible namespace and literal slash presentation are Host/UI facts. Repository metadata defines intended Plugin and Skill identities; final user-facing command syntax is published only after direct Codex App observation confirms it.

### Thin entry-point rule

`preview`, `status`, `steer`, and `takeover` are adapters over the canonical Dispatch orchestration contracts. They must not duplicate Recovery, Guardrail, TeamPlan, writer-safety, or lifecycle rules.

`doctor` is a thin diagnostic entry point over deterministic diagnostics. It must not become a second implementation of installer, state, or runtime-evidence validation.

`dispatch` remains the orchestration kernel and owns the canonical reference set.

## Runtime ownership map

```text
skills/dispatch/SKILL.md
-> orchestration entry, task understanding, high-level control loop

references/router-core.md
-> delegation value, role selection, semantic coverage, adaptive ready frontier

references/interaction.md
-> Preview / Status / Steer / Takeover interaction semantics and target resolution

references/dispatch-state.md
-> thread-scoped ephemeral coordination continuity and Host reconciliation

references/dispatch-receipt.md
-> orchestration accounting, review/rework/recovery presentation, localization

references/team-plan.md
-> multi-responsibility identity, dependency DAG, structural ownership, revisions

references/recovery.md
-> delegated attempt identity, native lifecycle, retries, UNKNOWN / INTERRUPTED semantics

references/guardrails.md
-> authority, trust boundary, mutation permission, writer coordination safety

references/handoff-capsule.md
-> compact Main-accepted evidence transfer

references/final-review.md
-> exact-candidate independent review

policy-contract.json
-> stable machine-readable role/model constants and hard product invariants

scripts/dispatch_state.py
-> deterministic temporary-state storage only

scripts/doctor.py
-> deterministic multi-layer health diagnostics

scripts/runtime-evidence.py
-> requested / accepted / observed runtime-route normalization
```

No second policy ledger is created around these owners.

## Hard invariants versus adaptive policy

The repository must distinguish correctness constraints from adaptive orchestration choices.

Hard invariants include:

```text
delegation depth is one
user authority never widens implicitly
UNKNOWN is not FAILED
native route claims require evidence at the required proof level
one active writer owns one canonical mutation domain by default
exact-candidate review binding
no duplicate active responsibility ownership
```

Adaptive policy includes:

```text
whether delegation adds value
which specialized role fits the responsibility
how many independent responsibilities are worth delegating
whether TeamPlan is needed
whether Final Review is warranted by consequences
whether Main should keep the work
```

Do not encode adaptive policy as arbitrary numeric team-size targets.

### Delegation quantity

There is no minimum Subagent count. A zero-child result is the natural outcome when delegation does not add enough distinct value to justify coordination cost.

There is no ordinary project-level maximum Subagent instance count. Native Host capacity is a ceiling, never a target. Useful distinct ready work, authority, writer safety, and integration semantics determine actual concurrency.

Five Agent role definitions do not imply a five-Agent team-size limit.

### Writer coordination

The current safe behavior remains one active writer for the canonical workspace/mutation domain. Treat this as a semantic write-coordination policy rather than a tunable numeric capacity.

Future isolated parallel writing may be considered only when the product can establish all required boundaries, including independent physical workspace, explicit disjoint write ownership, no unresolved semantic dependency, an integration owner, and deterministic integration verification.

Do not change `1` to another writer count as a shortcut. The current release target keeps single-writer behavior while making the policy extensible by semantics instead of raw capacity numbers.

## Ephemeral state boundary

Cross-turn Status, Steer, Takeover, and Dispatch resume require a small thread-scoped state capsule. It belongs under the operating-system temporary directory and is governed by `dispatch-state.md`.

The normal terminal state is no capsule. The project does not retain a growing history of TeamPlan JSON files in the repository or Codex home.

## Doctor architecture

Doctor covers six diagnostic layers:

```text
Plugin
Skills
Managed Agent profiles
Ephemeral dispatch state
Native Host capabilities
Runtime route evidence
```

Diagnosis is read-only by default. Expensive or mutating diagnostics, including live five-role route smoke, stale-state cleanup, repair, migration, or upgrade, require explicit intent appropriate to their effect.

Static configuration health must remain distinct from runtime observation. A configured model/effort match cannot be reported as an observed runtime match.

## Documentation boundary

```text
README.md / README_EN.md
-> concise product and user workflow

README_AI.md
-> orientation index and owner map, not a second runtime policy

docs/architecture.md
-> behavioral architecture

docs/repository-architecture.md
-> repository/package organization

docs/native-subagent-runtime.md
-> native Host boundary and runtime evidence

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

Pull requests are optional rather than a required integration mechanism. Force-push and deletion protection for `main` remain valuable safety boundaries.

A future multi-maintainer phase may restore mandatory pull-request review without changing the product architecture.