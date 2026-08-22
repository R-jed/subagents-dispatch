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

- [x] Truth closure: active contract owner sweep
  - Acceptance: no active contract gives TeamPlan runtime authority or fixed retry/followup budget semantics.
  - Verify: contract-owner regression tests and exact-head contract review.

- [x] Truth closure: eval migration
  - Acceptance: current expected-behavior evals use Native Core product rules; historical experiments are explicitly historical and cannot act as current oracle.
  - Verify: eval loader/tests.

- [x] Truth closure: profile effort single source
  - Acceptance: Terra is `high` everywhere current behavior is represented; consumers derive fixed route truth from `contracts/policy.json` where practical.
  - Verify: model/effort contract tests.

- [x] Truth closure: evidence-based phase status
  - Acceptance: repository phase PASS values match the remediated, verified state; release/Host gates remain pending until real evidence exists.
  - Verify: phase-status/release-contract tests.

- [x] Candidate verification
  - Acceptance: generated integrity refreshed, Ruff clean, full pytest clean, all GitHub Actions matrix jobs pass, fresh adversarial review finds no blocking repository issue.
  - Verified repository basis: `5bff43f9d50ca138711969e5407ac2f93ab160c7`, workflow run `32579090645`, four platform jobs plus aggregate policy check passed.
  - Final stop check: run the same full CI once more on the status/task-record exact head; no further repository mutation follows a green result.
