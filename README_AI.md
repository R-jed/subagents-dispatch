# subagents-dispatch: AI Agent Reference

This file is an index to canonical project owners, not a second copy of runtime policy.

## Project identity

```text
Product name:        subagents-dispatch
Repository:          R-jed/subagents-dispatch
Repo marketplace id: subagents-dispatch
Plugin id:           subagents-dispatch
Plugin directory:    .
Current version:     3.0.0
Distribution:        Codex Plugin
License:             MIT
```

The Plugin exposes six explicit Skills:

| Skill id | Intended display label | Canonical responsibility |
| --- | --- | --- |
| `dispatch` | Dispatch | start or resume orchestration |
| `preview` | Preview | predict likely orchestration without execution |
| `status` | Status | observe and reconcile current orchestration once |
| `steer` | Steer | guide one unchanged delegated attempt |
| `takeover` | Takeover | safely return delegated work to Main |
| `doctor` | Doctor | diagnose installation and runtime health |

Do not invent a Codex App slash-command string from repository identifiers. Exact App labels and presentation are Host/UI facts requiring direct observation.

## Canonical owners

```text
contracts/policy.json
-> machine-readable hard invariants and five configured Agent routes

contracts/routing.md
-> delegation value, role selection, responsibility compilation, semantic coverage, adaptive ready work

contracts/composition.md
-> Host / project rules / external Skill / hook / role-contract composition boundaries

contracts/interaction.md
-> Preview, Status, Steer, Takeover, target resolution, control detours

contracts/state.md
-> root-thread ephemeral orchestration continuity and Host reconciliation

contracts/receipt.md
-> orchestration accounting and Chinese/English presentation

contracts/team-plan.md
-> multi-responsibility identity, dependencies, ownership, revisions

contracts/recovery.md
-> delegated attempt lifecycle, retries, UNKNOWN, INTERRUPTED, Main takeover

contracts/guardrails.md
-> authority, trust, mutation permissions, writer coordination, consent, runtime-evidence boundaries

contracts/handoff.md
-> compact Main-accepted evidence transfer

contracts/evidence-artifact.md
-> optional references-first evidence bundles that keep conversational handoff compact

contracts/final-review.md
-> consequence-driven exact-candidate independent review
```

Each `skills/<id>/SKILL.md` is a thin explicit entry adapter. Each `skills/<id>/agents/openai.yaml` owns its App metadata. `policy.allow_implicit_invocation` is false for all six.

## Deterministic helpers

```text
scripts/policy.py
-> shared contracts/policy.json loading

scripts/install-agents.py
-> managed Agent profile install/check lifecycle

scripts/uninstall-agents.py
-> ownership-aware managed Agent profile removal using the existing install manifest and lock

scripts/validate_team_plan.py
-> TeamPlan structural validation

scripts/validate_team_ledger.py
-> delegated lifecycle/recovery ledger validation

scripts/inspect-agent-runtime.py
-> explicit exact-child Codex rollout inspection; emits only allowlisted Host-produced route/identity/permission metadata

scripts/runtime-evidence.py
-> configured/requested, accepted, and actual-runtime evidence normalization; native/local overlap must agree

scripts/review-artifact.py
-> exact-candidate Git review binding

scripts/validate-experiment-campaign.py
-> validate/freeze either a role-calibration or single-agent-versus-Dispatch campaign against the exact current candidate

scripts/validate-experiment-run.py
-> validate one actual run against its frozen campaign, including input attestation, complete materialized-child evidence, route evidence, oracle/result refs, and exact measurement provenance; never scores, aggregates, or mutates policy

scripts/score-behavioral-evals.py
-> validate and summarize paired behavioral result records without inventing a global quality score

scripts/dispatch_state.py
-> compact thread-scoped state, reconciliation, control targeting, and receipt accounting primitives

scripts/doctor.py
-> deterministic installation diagnostics; consumes explicit normalized runtime evidence but never spawns or scans Host runtime automatically
```

For install, first-run provisioning, update, or uninstall commands, read `docs/plugin-installation.md`. For architecture, read `docs/repository-architecture.md`. For native runtime boundaries, read `docs/native-subagent-runtime.md`. For the exact child model/effort/sandbox proof protocol, read `docs/runtime-attestation.md`. For role calibration, single-agent-versus-Dispatch benchmarking, policy promotion, and README claim publication rules, read `docs/experiment-protocol.md`. For broader evaluation boundaries and the campaign/run implementation, read `evals/README.md`.

For release evidence, read `docs/release-checklist.md`: repository gates are deterministic, App labels require direct human observation, and Codex Host route/control evidence remains pending until a real supported Host run proves it. During the single-maintainer phase, implement non-trivial changes on a short-lived feature branch, run full local validation and adversarial review there, repair and revalidate on the same branch, then merge directly to `main` and use the `main` push GitHub Actions run as cross-platform confirmation. A pull request is optional, not a hidden requirement.

The Experiment Plane is development/research infrastructure. Role calibration, formal model/effort campaigns, formal single-agent-versus-Dispatch benchmark campaigns, calibration-profile materialization, and experiment-run provenance do not block v3.0.0 unless the release publishes a claim that specifically depends on that evidence. Runtime attestation remains a product release gate when a release claim states what actually ran. A small real-task product canary may be used to catch obvious regressions without turning the full formal experiment machinery into a release prerequisite.

Runtime truth is layered. `contracts/policy.json` and managed profile TOMLs establish configuration intent. A requested or Host-accepted `agent_type` establishes request/acceptance facts. Observed child runtime truth comes only from actual Host evidence: public Host metadata and, when needed, the exact Host-produced Codex child rollout inspected by `scripts/inspect-agent-runtime.py`. Never copy configured or accepted values into an observed field, and never treat a child's prose self-identification as evidence. When public Host metadata and the exact rollout both expose a field, they must agree or the route claim is quarantined.

Composition is also layered. Host/current user authority and applicable project instructions constrain the work; an accepted external Skill or workflow may own domain planning and acceptance; subagents-dispatch adds orchestration only; the child role/responsibility packet narrows the result further. Hooks are optional observations/guards and are not a required control plane.

Experiments are typed. Role calibration keeps the responsibility/isolation contract fixed and changes model/effort. Its campaign freezes an evaluator-owned responsibility packet identity so a packet change cannot be misattributed to model/effort. Product benchmark keeps the real task/environment fixed and compares ordinary `single_agent` with explicit `dispatch`; it does not pre-script which project roles Dispatch must use. Campaign fields define expected/frozen inputs. Per-run input evidence must independently attest the Host, repository/base, task, applicable calibration packet, and controlled environment; copying campaign values is not observation. Per-run materialization evidence independently records the complete project-child count, so an empty route list cannot by itself be relabeled as a zero-child Dispatch. Every observed materialized child must have one route row; unavailable child-set evidence keeps route assurance `UNKNOWN`. Formal experiment claims require repeated real runs and exact evidence. Policy never changes automatically from benchmark output.

An ordinary Dispatch Receipt may show the selected project lane for materialized work; explicit live-route proof still requires actual Host evidence. Ordinary Dispatch does not scan Codex session rollouts. Current role model/effort settings are operational policy, not benchmark-proven optimality claims. Do not claim benchmark gains, public availability, token/cost attribution, or App UI behavior without current accepted evidence.