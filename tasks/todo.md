# RC5 Review Remediation Tasks

- [x] Runtime safety: canonical scope containment
  - Acceptance: Windows drive/UNC paths fail closed; directory ceilings safely contain descendants; forbidden ancestry remains rejected.
  - Verify: focused state/lifecycle regressions plus full suite.
  - Files: `scripts/dispatch_state_v4_core.py`, `scripts/dispatch_state_v4.py`, `scripts/execution_lifecycle_v4_core.py`, focused tests.

- [x] Runtime safety: generation-safe identity after compaction
  - Acceptance: compacted attempts cannot make stale Host evidence current; native task names remain distinct by attempt generation; contract no longer promises an unenforceable unbounded opaque-id set.
  - Verify: compact an old attempt, create a later generation, replay old observation/identity inputs, require stale/rejection.
  - Files: state/lifecycle contracts and focused recovery tests.

- [x] Runtime safety: idempotent Host observation persistence
  - Acceptance: repeating the same current-generation Host observation produces `noop` without changing `state_revision` or `updated_at`.
  - Verify: focused duplicate-observation test.
  - Files: `scripts/dispatch_state_v4_core.py`, `scripts/writer_lease_v4.py`, tests.

- [x] Runtime safety: bounded same-child correction evidence
  - Acceptance: many legal followups do not grow `accounting_refs` linearly or hit the state-size bound because of recovery-basis history; current generation remains replay-safe.
  - Verify: high-count followup regression under the normal 64 KiB limit.
  - Files: state/lifecycle implementation, recovery/state contracts, tests.

- [x] Host adapter: fail-closed readiness
  - Acceptance: absent capability snapshot never becomes `host_ready=true`; known supported surface with unknown numeric capacity stays distinct from absent evidence.
  - Verify: scheduler capability tests.
  - Files: `scripts/scheduler_v4.py`, `docs/v4/scheduler.json`, tests.

- [x] Host adapter: V2 session capacity semantics
  - Acceptance: project never treats Host session concurrency as child-only capacity; root/session participation is accounted for or capacity remains advisory/unknown.
  - Verify: tests derived from current official OpenAI Codex semantics.
  - Files: `scripts/host_capabilities.py`, scheduler/doctor consumers, contracts, tests.

- [ ] Documentation truth closure: current authority sweep
  - Acceptance: current contracts/docs consistently describe the two-Skill Orchestrate/Doctor surface, WorkGraph authority, evidence-gated recovery, generation-safe compaction, and current V4 terminology; retired standalone pre-Orchestrate product wording is removed from current-authority prose.
  - Verify: repository-wide current-authority regression scan plus exact-head review.

- [ ] Documentation truth closure: eval migration
  - Acceptance: current expected-behavior evals use Native Core product rules; unchanged stalled work without new evidence cannot authorize a fresh same-role retry; historical experiment labels cannot act as runtime policy.
  - Verify: eval loader/tests and direct fixture inspection.

- [ ] Documentation truth closure: history isolation
  - Acceptance: `docs/history/` has an explicit archive authority boundary and every historical Markdown document declares that it cannot guide current implementation or release decisions.
  - Verify: archive-marker regression test.

- [x] Truth closure: profile effort single source
  - Acceptance: Terra is `high` everywhere current behavior is represented; consumers derive fixed route truth from `contracts/policy.json` where practical.
  - Verify: model/effort contract tests.

- [ ] Truth closure: evidence-based phase status
  - Acceptance: repository phase PASS values match the remediated, verified state; release/Host gates remain pending until real evidence exists.
  - Verify: phase-status/release-contract tests.

- [ ] Candidate verification
  - Acceptance: generated integrity refreshed if required, Ruff clean, full pytest clean, all GitHub Actions matrix jobs pass, fresh adversarial review finds no blocking repository issue.
  - Previous verified basis `787b008be319553c3c6e3fa40ea3198197e957cd` / workflow `32580889070` remains historical after this remediation branch mutates the candidate.
  - Final stop check: run the same full CI on the final exact head; no repository phase returns to PASS until that result is green.
