# Repository Architecture

This document defines the target repository organization for subagents-dispatch. The repository should read like the product architecture: user-facing Skills at the edge, shared orchestration contracts in one obvious place, deterministic helpers in one obvious place, and Codex Native Subagents as the only Agent runtime.

## Design principles

1. The Codex Plugin package is obvious from the repository root.
2. User-facing actions are first-class Skills, not hidden payload grammar.
3. Shared orchestration semantics are independent of any one Skill folder.
4. One concept has one canonical owner.
5. Deterministic invariants move into code when code can enforce them more reliably than prose.
6. Codex Native Subagents remain the runtime. The project does not introduce another scheduler, daemon, event bus, routing proxy, control server, or telemetry collector.
7. Public docs, AI orientation, runtime contracts, deterministic helpers, tests, and evaluation fixtures stay visibly separate.
8. A structural move is acceptable when it leaves the final architecture simpler. Do the migration once and update all references rather than preserving awkward paths for compatibility inside an unreleased major version.

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
├── contracts/
│   ├── policy.json
│   ├── routing.md
│   ├── interaction.md
│   ├── state.md
│   ├── receipt.md
│   ├── team-plan.md
│   ├── recovery.md
│   ├── guardrails.md
│   ├── handoff.md
│   └── final-review.md
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
│   │   └── agents/openai.yaml
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
├── README.md
├── README_EN.md
└── README_AI.md
```

Keep `assets/`, legal files, changelog, and development metadata at the root when they remain part of the packaged/public repository. They are omitted above only to keep the architectural tree focused.

Do not add MCP, hook, server, database, storage, or source-runtime trees merely to resemble another Plugin. Add a top-level component only when subagents-dispatch genuinely owns that capability.

## Why contracts are top-level

The target control surface has six user-facing Skills. Preview, Status, Steer, Takeover, Doctor, and Dispatch all need some subset of the same orchestration semantics. Keeping those semantics under `contracts/` makes their shared ownership explicit.

The `contracts/` directory therefore becomes the single semantic kernel. Skill folders are adapters into it.

This also prevents a future anti-pattern where every Skill copies its own UNKNOWN, retry, writer-safety, lifecycle, or localization rules.

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

Each Skill owns only:

```text
its explicit user intent
its minimal entry / completion contract
its App metadata
which shared contracts it must load
```

Each has `SKILL.md` plus `agents/openai.yaml`, and each must set:

```yaml
policy:
  allow_implicit_invocation: false
```

The App-visible namespace and literal slash presentation are Host/UI facts. Repository metadata defines intended Plugin and Skill identities; final user-facing literal command syntax is published only after direct Codex App observation confirms it.

### Thin entry-point rule

`preview`, `status`, `steer`, and `takeover` are thin adapters over `contracts/interaction.md`, `contracts/state.md`, and the other contracts required by the action.

`doctor` is a thin adapter over deterministic diagnostics. It does not implement a second installer, state parser, route matcher, or cleanup engine in Skill prose.

`dispatch` understands the task and leads orchestration but no longer owns private copies of shared runtime policy.

## Contract ownership map

```text
contracts/policy.json
-> stable machine-readable role/model constants and hard product invariants

contracts/routing.md
-> delegation value, role selection, responsibility packets, semantic coverage, phase recompilation, adaptive ready frontier

contracts/interaction.md
-> Preview / Status / Steer / Takeover semantics, target resolution, control detours

contracts/state.md
-> thread-scoped ephemeral coordination continuity and native Host reconciliation

contracts/receipt.md
-> orchestration accounting, review/rework/recovery presentation, localization

contracts/team-plan.md
-> multi-responsibility identity, dependency DAG, structural ownership, revisions

contracts/recovery.md
-> delegated attempt identity, native lifecycle, retries, UNKNOWN / INTERRUPTED semantics, Main takeover

contracts/guardrails.md
-> authority, trust boundary, mutation permission, writer coordination safety, consent

contracts/handoff.md
-> compact Main-accepted evidence transfer

contracts/final-review.md
-> exact-candidate independent review
```

## Deterministic helper ownership

```text
scripts/policy.py
-> load and validate the shared machine policy location

scripts/dispatch_state.py
-> safe temporary-state storage, locking, inspection, cleanup primitives only

scripts/doctor.py
-> deterministic multi-layer health diagnostics

scripts/install-agents.py
-> managed Agent profile lifecycle

scripts/runtime-evidence.py
-> requested / accepted / observed runtime-route normalization

scripts/validate_team_plan.py
-> TeamPlan structure validation

scripts/validate_team_ledger.py
-> delegated lifecycle/recovery ledger validation

scripts/review-artifact.py
-> exact-candidate Git review binding
```

These helpers enforce deterministic facts. They do not become a background orchestration runtime.

## Hard invariants versus adaptive policy

The repository must distinguish correctness constraints from adaptive orchestration choices.

Hard invariants include:

```text
delegation depth is one
user authority never widens implicitly
UNKNOWN is not FAILED
runtime route claims require evidence at the claimed proof level
one active writer owns one canonical mutation domain by default
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

### Delegation quantity

There is no minimum Subagent count. A zero-child result is derived when delegation does not add enough distinct value to justify coordination cost.

There is no ordinary project-level maximum Subagent instance count. Native Host capacity is a ceiling, never a target. Useful distinct ready work, authority, writer coordination, and integration semantics determine actual concurrency.

Five Agent role definitions do not imply a five-Agent team-size limit.

The canonical wording is therefore value-driven delegation with no minimum team size, rather than treating `0` as a routing target or special numeric rule.

### Writer coordination

The current safe behavior remains one active writer for the canonical workspace / mutation domain. Treat this as a semantic coordination mode rather than a tunable numeric capacity.

The machine policy should evolve from a field such as:

```text
max_active_writers_per_workspace = 1
```

toward a semantic policy such as:

```text
write_coordination.mode = single_writer
write_coordination.scope = canonical_workspace
```

The v3 target keeps single-writer behavior. It does not enable parallel writers merely because the schema becomes more expressive.

Future isolated parallel writing is a separate capability and may be considered only when the product can establish all required boundaries, including independent physical workspace, explicit disjoint write ownership, no unresolved semantic dependency, an integration owner, and deterministic integration verification.

Never change `1` to another writer count as a shortcut.

## Ephemeral state boundary

Cross-turn Status, Steer, Takeover, and Dispatch resume require a small thread-scoped state capsule governed by `contracts/state.md`.

Ordinary state belongs under the operating-system temporary directory. Normal completion removes it. The project does not retain a growing history of TeamPlan JSON files in the repository or Codex home.

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

Static configuration health remains distinct from runtime observation. A configured model/effort match cannot be reported as an observed runtime match.

## Documentation boundary

```text
README.md / README_EN.md
-> concise product and user workflow

README_AI.md
-> orientation index and owner map, not a second runtime policy

docs/architecture.md
-> behavioral architecture

docs/repository-architecture.md
-> package / repository organization

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

Pull requests are optional rather than a required integration mechanism. Force-push and deletion protection for `main` remain useful safety boundaries.

A future multi-maintainer phase may restore mandatory pull-request review without changing the product architecture.
