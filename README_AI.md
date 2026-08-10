# subagents-dispatch: AI Agent Reference

This file is an index to canonical project owners, not a second copy of runtime policy.

## Project identity

```text
Product name:        subagents-dispatch
Repository:          R-jed/subagents-dispatch
Repo marketplace id: subagents-dispatch
Plugin id:           subagents-dispatch
Plugin directory:    .
Current version:     2.1.2
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

scripts/validate-role-calibration.py
-> validate/freeze real role-calibration campaign definitions against the current policy control route

scripts/dispatch_state.py
-> compact thread-scoped state, reconciliation, control targeting, and receipt accounting primitives

scripts/doctor.py
-> deterministic installation diagnostics; consumes explicit normalized runtime evidence but never spawns or scans Host runtime automatically
```

For install, first-run provisioning, update, or uninstall commands, read `docs/plugin-installation.md`. For architecture, read `docs/repository-architecture.md`. For native runtime boundaries, read `docs/native-subagent-runtime.md`. For the exact child model/effort/sandbox proof protocol, read `docs/runtime-attestation.md`. For real route calibration and single-agent-versus-Dispatch benchmark rules, read `docs/role-calibration.md`. For broader evaluation boundaries, read `evals/README.md`.

For release evidence, read `docs/release-checklist.md`: repository gates are deterministic, App labels require direct human observation, and Codex Host route/control evidence remains pending until a real supported Host run proves it. During the single-maintainer phase, implement non-trivial changes on a short-lived feature branch, run full local validation and adversarial review there, repair and revalidate on the same branch, then merge directly to `main` and use the `main` push GitHub Actions run as cross-platform confirmation. A pull request is optional, not a hidden requirement.

Runtime truth is layered. `contracts/policy.json` and managed profile TOMLs establish configuration intent. A requested or Host-accepted `agent_type` establishes request/acceptance facts. Observed child runtime truth comes only from actual Host evidence: public Host metadata and, when needed, the exact Host-produced Codex child rollout inspected by `scripts/inspect-agent-runtime.py`. Never copy configured or accepted values into an observed field, and never treat a child's prose self-identification as evidence. When public Host metadata and the exact rollout both expose a field, they must agree or the route claim is quarantined.

Composition is also layered. Host/current user authority and applicable project instructions constrain the work; an accepted external Skill or workflow may own domain planning and acceptance; subagents-dispatch adds orchestration only; the child role/responsibility packet narrows the result further. Hooks are optional observations/guards and are not a required control plane.

An ordinary Dispatch Receipt may show the selected project lane for materialized work; explicit live-route proof still requires actual Host evidence. Ordinary Dispatch does not scan Codex session rollouts. Current role model/effort settings are operational policy, not benchmark-proven optimality claims. Do not claim benchmark gains, public availability, token/cost attribution, or App UI behavior without current accepted evidence.
