# subagents-dispatch: AI Agent Reference

This file is the compact machine-oriented map for agents working in this repository. User-facing explanation belongs in `README.md` and `README.zh-CN.md`; canonical behavior belongs in `contracts/` and each explicit Skill.

## Product boundary

subagents-dispatch is a thin orchestration control surface on top of Codex native subagent primitives. It does not own or replace the Host scheduler, lifecycle runtime, transport, sandbox, session store, or UI.

The project deliberately does **not** add an MCP server, daemon, background event bus, persistent orchestration database, telemetry collector, or second scheduler.

## Public Skills

```text
skills/dispatch
skills/preview
skills/status
skills/steer
skills/takeover
skills/doctor
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

scripts/validate-experiment-campaign.py
-> validate/freeze either a role-calibration or single-agent-versus-Dispatch campaign against the exact current candidate

scripts/validate-experiment-run.py
-> validate one actual run against its frozen campaign, including plugin/input attestation, complete materialized-child evidence, route evidence, oracle/result refs, and exact measurement provenance; never scores, aggregates, or mutates policy

scripts/score-behavioral-evals.py
-> validate and summarize paired behavioral result records without inventing a global quality score

scripts/dispatch_state.py
-> compact thread-scoped state, reconciliation, control targeting, and receipt accounting primitives

scripts/doctor.py
-> deterministic installation diagnostics; consumes explicit normalized runtime evidence but never spawns or scans Host runtime automatically
```

For install, first-run provisioning, update, or uninstall commands, read `docs/plugin-installation.md`. For architecture, read `docs/repository-architecture.md`. For native runtime boundaries, read `docs/native-subagent-runtime.md`. For the exact child model/effort/sandbox proof protocol, read `docs/runtime-attestation.md`. For role calibration, single-agent-versus-Dispatch benchmarking, policy promotion, and README claim publication rules, read `docs/experiment-protocol.md`. For broader evaluation boundaries and the campaign/run implementation, read `evals/README.md`.

For release evidence, read `docs/release-checklist.md`: repository gates are deterministic, App labels require direct human observation, and Codex Host route/control evidence remains pending until a real supported Host run proves it. During the single-maintainer phase, implement non-trivial changes on a short-lived feature branch, run full local validation and adversarial review there, repair and revalidate on the same branch, then merge directly to `main` and use the `main` push GitHub Actions run as cross-platform confirmation. A pull request is optional, not a hidden requirement.

Runtime truth is layered. `contracts/policy.json` and managed profile TOMLs establish configuration intent. A requested or Host-accepted `agent_type` establishes request/acceptance facts. Observed child runtime truth comes only from actual Host evidence: public Host metadata and, when needed, the exact Host-produced Codex child rollout inspected by `scripts/inspect-agent-runtime.py`. Never copy configured or accepted values into an observed field, and never treat a child's prose self-identification as evidence. When public Host metadata and the exact rollout both expose a field, they must agree or the route claim is quarantined.

Composition is also layered. Host/current user authority and applicable project instructions constrain the work; an accepted external Skill or workflow may own domain planning and acceptance; subagents-dispatch adds orchestration only; the child role/responsibility packet narrows the result further. Hooks are optional observations/guards and are not a required control plane.

Experiments are typed. Role calibration keeps the responsibility/isolation contract fixed and changes model/effort. Its campaign freezes an evaluator-owned responsibility packet identity so a packet change cannot be misattributed to model/effort. Product benchmark keeps the real task/environment fixed and compares ordinary `single_agent` with explicit `dispatch`; it does not pre-script which project roles Dispatch must use. Campaign fields define expected/frozen inputs. Per-run input evidence must independently attest actual plugin state, Host, repository/base, task, reset procedure, acceptance contract, applicable calibration packet, and controlled environment; copying campaign values is not observation. For product benchmarks, `single_agent` must prove the plugin is absent while `dispatch` must prove the exact campaign candidate SHA is active. Per-run materialization evidence independently records the complete project-child count, so an empty route list cannot by itself be relabeled as a zero-child Dispatch. Every observed materialized child must have one route row; unavailable child-set evidence keeps route assurance `UNKNOWN`. Formal experiment claims require repeated real runs and exact evidence. Policy never changes automatically from benchmark output.

An ordinary Dispatch Receipt may show the selected project lane for materialized work; explicit live-route proof still requires actual Host evidence. Ordinary Dispatch does not scan Codex session rollouts. Current role model/effort settings are operational policy, not benchmark-proven optimality claims. Do not claim benchmark gains, public availability, token/cost attribution, or App UI behavior without current accepted evidence.
