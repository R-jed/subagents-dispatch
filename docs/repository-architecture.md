# Repository Architecture

This document defines the target repository organization for subagents-dispatch. The repository should read like the product architecture: user-facing Skills at the edge, shared orchestration contracts in one obvious place, deterministic helpers in one obvious place, explicit evidence/experiment tooling outside the ordinary runtime path, and Codex Native Subagents as the only Agent runtime.

## Design principles

1. The Codex Plugin package is obvious from the repository root.
2. User-facing actions are first-class Skills, not hidden payload grammar.
3. Shared orchestration semantics are independent of any one Skill folder.
4. One concept has one canonical owner.
5. Deterministic invariants move into code when code can enforce them more reliably than prose.
6. Codex Native Subagents remain the runtime. The project does not introduce another scheduler, daemon, event bus, routing proxy, control server, or telemetry collector.
7. Runtime evidence, composability, context/evidence handoff, and experiments are separate planes rather than conditionals scattered through every Skill.
8. Public docs, AI orientation, runtime contracts, deterministic helpers, tests, and evaluation fixtures stay visibly separate.
9. Experimental results never mutate runtime policy automatically. Policy changes happen only after accepted evidence.
10. A structural move is acceptable when it leaves the final architecture simpler. Do the migration once and update all references rather than preserving awkward paths for compatibility inside an unreleased major version.

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
│   ├── native-subagent-runtime.md
│   ├── openai-references.md
│   ├── plugin-installation.md
│   ├── release-checklist.md
│   ├── repository-architecture.md
│   ├── role-calibration.md
│   └── runtime-attestation.md
├── evals/
│   ├── behavioral-workloads.json
│   ├── behavioral-result.schema.json
│   ├── role-calibration-campaign.schema.json
│   └── ...
├── scripts/
│   ├── dispatch_state.py
│   ├── doctor.py
│   ├── inspect-agent-runtime.py
│   ├── install-agents.py
│   ├── legacy_migration.py
│   ├── policy.py
│   ├── review-artifact.py
│   ├── runtime-evidence.py
│   ├── score-behavioral-evals.py
│   ├── validate-role-calibration.py
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

## Four-plane architecture

The A–G hardening work is deliberately collapsed into four planes instead of seven independent feature stacks.

```text
Runtime Evidence Plane
-> prove what actually ran
-> runtime-attestation.md
-> inspect-agent-runtime.py
-> runtime-evidence.py

Composition Plane
-> define how Host capability, current authority, project instructions, external Skills/workflows,
   hooks, Dispatch guardrails, and role contracts compose
-> composition.md

Handoff / Claims Plane
-> keep child-to-Main context compact while preserving complete inspectable provenance by reference
-> handoff.md
-> evidence-artifact.md
-> review-artifact.py for exact Git candidate identity

Experiment Plane
-> freeze real role-calibration / single-agent-vs-Dispatch experiments before execution
-> reuse the existing paired behavioral scorer instead of creating a second generic benchmark engine
-> role-calibration.md
-> role-calibration-campaign.schema.json
-> validate-role-calibration.py
```

The planes meet at explicit boundaries. Runtime Evidence can feed an experiment or release artifact, but ordinary Dispatch does not scan rollouts. Evidence Artifacts may preserve accepted runtime/verification/benchmark provenance, but they do not become active state. Experiments may recommend a role-policy change, but they never rewrite `policy.json` automatically.

## Why contracts are top-level

The target control surface has six user-facing Skills. Preview, Status, Steer, Takeover, Doctor, and Dispatch all need some subset of the same orchestration semantics. Keeping those semantics under `contracts/` makes their shared ownership explicit.

The `contracts/` directory therefore becomes the single semantic kernel. Skill folders are adapters into it.

This also prevents a future anti-pattern where every Skill copies its own UNKNOWN, retry, writer-safety, lifecycle, localization, composition, or evidence-transfer rules.

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

`doctor` is a thin adapter over deterministic diagnostics. It does not implement a second installer, state parser, route matcher, runtime inspector, or cleanup engine in Skill prose.

`dispatch` understands the task and leads orchestration but no longer owns private copies of shared runtime policy. It loads `composition.md` when another Skill/workflow, project-instruction boundary, hook, or Host capability affects the current responsibility. It loads `evidence-artifact.md` only when complete accepted provenance should remain outside the inline child/Main context.

## Contract ownership map

```text
contracts/policy.json
-> stable machine-readable role/model constants and hard product invariants

contracts/routing.md
-> delegation value, role selection, responsibility packets, semantic coverage, phase recompilation, adaptive ready frontier

contracts/composition.md
-> Host / current authority / project rules / external Skill or workflow / hook / role-contract composition boundaries

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

contracts/evidence-artifact.md
-> optional references-first evidence bundles when complete provenance should remain outside conversational context

contracts/final-review.md
-> exact-candidate independent review
```

`composition.md` does not reimplement Codex project-instruction precedence. It consumes the Host-effective constraint surface. Hooks are optional observer/guard inputs and are not a required runtime path.

`evidence-artifact.md` does not turn the repository or `active.json` into a log store. Ephemeral artifact semantics are separate from coordination state, and artifact creation remains on-demand rather than a background telemetry system.

## Deterministic helper ownership

```text
scripts/policy.py
-> load and validate the shared machine policy location

scripts/dispatch_state.py
-> compact thread-scoped state storage/locking, Host reconciliation, control targeting, cleanup, and idempotent Receipt accounting primitives

scripts/doctor.py
-> deterministic multi-layer health diagnostics

scripts/install-agents.py
-> managed Agent profile lifecycle

scripts/inspect-agent-runtime.py
-> explicit exact-child Codex rollout inspection with allowlisted route/identity/permission output

scripts/runtime-evidence.py
-> configured/requested / accepted / observed runtime-route normalization and source-conflict quarantine

scripts/validate_team_plan.py
-> TeamPlan structure validation

scripts/validate_team_ledger.py
-> delegated lifecycle/recovery ledger validation

scripts/review-artifact.py
-> exact-candidate Git review binding

scripts/score-behavioral-evals.py
-> validate and summarize paired live behavioral results; no hidden global quality score

scripts/validate-role-calibration.py
-> validate and freeze-hash a real role-calibration campaign against the current policy control route
```

These helpers enforce deterministic facts from the canonical contracts or experimental input definitions. They do not own adaptive routing policy and do not become a background orchestration runtime.

The role-calibration validator intentionally does not run Agents, score outputs, or edit `policy.json`. The existing behavioral scorer is reused for paired measurements where its result schema applies rather than introducing a parallel scoring engine merely because a new experiment is being added.

## Runtime evidence plane

Configured route intent, Host acceptance, and observed runtime facts are distinct.

The runtime evidence plane therefore uses:

```text
policy.json / managed profile
-> configured intent

actual spawn request / Host role acceptance
-> requested / accepted identity

public Host runtime metadata
-> preferred observed evidence

exact Host-produced child rollout, inspected explicitly when needed
-> local observed fallback for omitted fields
```

When public Host metadata and exact rollout expose the same fact, they must agree. Missing evidence stays UNKNOWN. Configuration never fills an Observed field. Exact local rollout evidence is inspectable Host-produced runtime evidence, but it is not cryptographically signed or claimed to be tamper-proof.

Ordinary Dispatch does not run the rollout inspector merely to manufacture certainty. Runtime attestation is explicit and consequence-driven.

## Composition plane

Effective child action is an intersection, not a priority engine owned by this plugin:

```text
Host capability/policy
∩ current system/developer/user authority
∩ applicable project instructions
∩ accepted upstream Skill/workflow contract
∩ Dispatch guardrails
∩ bounded role/responsibility packet
```

A lower layer may narrow, never widen.

Codex owns AGENTS/project-instruction discovery and precedence. subagents-dispatch does not parse a parallel instruction hierarchy. If a fresh child may not inherit a material project constraint, Main carries only that narrow constraint or source reference in the responsibility packet.

Hooks may improve observation or stop an unsafe action when the Host provides a trusted blocking hook, but the product remains correct without hooks. Hook output does not replace native child identity/state reconciliation or runtime attestation.

## Handoff / claims plane

Fresh child context remains the default. The return packet is intentionally an index rather than an evidence dump.

```text
child claim + compact refs
-> Main inspects actual artifact/evidence
-> Main accepts supported truth
-> small reusable truth goes into Handoff Capsule
-> substantial reusable provenance stays in an Evidence Artifact and is referenced from the capsule/review/experiment
```

A child cannot self-promote a manifest or path into Main-accepted evidence.

Evidence Artifacts prefer stable source/revision/digest refs over copied bytes. Attachments are justified only when required evidence cannot otherwise be re-inspected. Raw transcripts, hidden reasoning, whole repositories, unrelated source, credentials, and unbounded tool output are outside the artifact contract.

There is no universal token target for child returns yet. Context discipline removes duplication/reconstructable data first and lets later real benchmarks establish whether a tighter numeric budget improves quality/resource use.

## Experiment plane

Role calibration and single-agent-versus-Dispatch evaluation share one evidence discipline.

A formal campaign freezes before expensive runs:

```text
candidate plugin SHA
Host/runtime target
role semantic contract
current route control + challengers
real repository/base revision
exact task bytes/hash
reset procedure
permissions/tool fingerprints
project-rule refs
acceptance oracle
repeat/ordering policy
promotion criteria when the campaign can change policy
```

Role calibration changes model/effort while keeping the responsibility semantics and sandbox/isolation contract fixed. This prevents a route comparison from quietly testing a different authority envelope.

Actual model/effort policy conclusions require runtime-attested included runs. `UNKNOWN` route evidence cannot support a claim that a specific model or effort produced the measured outcome.

Formal policy promotion requires repeated real runs and predeclared criteria. A measured result may recommend a policy update, but a maintainer explicitly accepts the tradeoff before the canonical role/profile files change.

Public README benchmark claims are downstream of accepted experiment evidence. Synthetic/static fixtures protect semantics but are not published as measured product superiority.

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

The machine policy uses:

```text
write_coordination.mode = single_writer
write_coordination.scope = canonical_workspace
```

The v3 target keeps single-writer behavior. It does not enable parallel writers merely because the schema is expressive enough to describe future coordination modes.

Future isolated parallel writing is a separate capability and may be considered only when the product can establish all required boundaries, including independent physical workspace, explicit disjoint write ownership, no unresolved semantic dependency, an integration owner, and deterministic integration verification.

Do not replace semantic writer ownership with a tunable writer count.

## Ephemeral state and artifact boundary

Cross-turn Status, Steer, Takeover, and Dispatch resume require a small thread-scoped state capsule governed by `contracts/state.md`.

Ordinary state belongs under the operating-system temporary directory. Normal completion removes it. The project does not retain a growing history of TeamPlan JSON files in the repository or Codex home.

Evidence Artifacts, when needed, are a separate on-demand temporary namespace governed by `contracts/evidence-artifact.md`. They are not embedded into `active.json`, and age of an artifact never proves that an unresolved writer stopped.

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
-> concise product and user workflow; public claims limited to accepted evidence

README_AI.md
-> orientation index and owner map, not a second runtime policy

docs/architecture.md
-> behavioral architecture

docs/repository-architecture.md
-> package / repository organization and plane ownership

docs/native-subagent-runtime.md
-> native Host boundary and runtime evidence

docs/runtime-attestation.md
-> actual child route proof protocol

docs/role-calibration.md
-> role calibration, real benchmark, policy-promotion, README publication gate

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
