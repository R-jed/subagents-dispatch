> Historical archive. This document records a superseded design/review state. It is not a current V4 contract, implementation guide, release gate, or source of runtime authority. Use current `contracts/`, current non-history `docs/`, and `docs/v4/` for present behavior.

# V4.0.0 RC3 Remediation Matrix

| Root area | Primary owners | Required negative proof | Required positive proof | Release impact |
|---|---|---|---|---|
| Managed execution contract | `execution_lifecycle_v4.py`, `dispatch_control_v4.py`, `orchestration_guard.py`, profile contract | profile/agent_type mismatch, wrong fork_turns, incomplete assignment | canonical invocation matches ExecutionBinding and profile | hard blocker |
| State truth kernel | `dispatch_state_v4.py`, `work_graph_v4.py`, `dispatch_control_v4.py`, `writer_lease_v4.py` | corrupt ACCEPTED, stale attempt, ACK replay, duplicate/out-of-order PostToolUse | one current correctness authority and exact idempotency | hard blocker |
| Scheduler/path authority | `scheduler_v4.py`, state scope validation and write guard path | premature third child, separator/case/ancestor alias | accepted-progress refill and canonical scope enforcement | hard blocker when authority affected |
| Host evidence authority | `host_capabilities.py`, Host observation ingestion, WriterLease settlement | arbitrary trust JSON, arbitrary lifecycle string, unsupported surface | evidence originates from accepted Host/Hook path and binds current identities | hard blocker |
| Release identity closure | `doctor_runtime.py`, package integrity, Host campaign, Final Review tooling | fake green smoke, unhealthy+release flag, candidate drift | one release predicate bound to exact candidate and review | publication blocker |

## Deferred from RC3 unless touched naturally

- dynamic reasoning-effort routing
- nested managed delegation
- additional public Skills
- speculative execution
- background scheduler daemon
- broader UX redesign

Bounded accounting compaction may be included if lifecycle-evidence representation is already being changed. Otherwise it is tracked as post-4.0 hardening.
