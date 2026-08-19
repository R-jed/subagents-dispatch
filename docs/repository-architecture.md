# Repository Architecture

This document describes the current V4 repository organization. It is subordinate to the normative product freeze in `docs/v4/architecture.json` and the runtime owner map in `docs/architecture.md`.

## Product surface

The Plugin exposes exactly two explicit Skills:

```text
Orchestrate
Doctor
```

`Orchestrate` is the single user-facing orchestration entrypoint. `Doctor` owns installed-product diagnosis and explicit ownership-safe maintenance. Preview, Status, Steer, Takeover, Cancel, Continue, and Correction are Orchestrate control intents, not separate public Skills.

## Current planes

The repository separates five concerns without adding another Agent runtime:

```text
Product contracts
-> contracts/

Deterministic runtime
-> scripts/*_v4.py and their current supporting modules

Host action boundary
-> hooks/
-> staged V4 lifecycle definition in docs/v4/hooks.json

Installed-product diagnosis and update
-> skills/doctor/
-> scripts/doctor.py
-> scripts/plugin_update.py
-> scripts/install-agents.py

Maintainer evidence and experiments
-> evals/
-> calibration / experiment validators
-> release evidence tooling
```

Codex Native Subagents remain the only Agent runtime. The repository does not add a daemon, event bus, background polling service, scheduler database, routing proxy, control server, or telemetry collector.

## Active contracts

The current V4 reasoning path is intentionally small:

```text
contracts/policy.json
-> fixed managed profile and review policy

contracts/routing.md
-> delegation value, role selection, semantic coverage

contracts/responsibility-packet.md
-> one serialized five-section responsibility record

contracts/team-plan.md
-> multi-responsibility dependency/integration truth

contracts/interaction.md
-> Orchestrate controls

contracts/recovery.md
-> WorkUnit / ExecutionBinding lifecycle and bounded recovery

contracts/final-review.md
-> exact-candidate independent review
```

Supporting composition, guardrail, handoff, evidence and receipt contracts remain separate only where they own a current concern. Historical V3 semantics must not be treated as current V4 runtime truth merely because a legacy file remains in the repository for migration or compatibility.

## Runtime owners

The V4 coordination runtime keeps one owner per correctness concern:

```text
scripts/orchestrate_v4.py
-> admission, routing facade and controls

scripts/dispatch_state_v4.py
-> current bounded orchestration state

scripts/work_graph_v4.py
-> WorkUnit installation, dependency and acceptance truth

scripts/scheduler_v4.py
-> sole admission/capacity/backpressure scheduler

scripts/execution_lifecycle_v4.py
-> ExecutionBinding lifecycle

scripts/dispatch_control_v4.py
-> PendingControl authorization and acknowledgement

scripts/writer_lease_v4.py
-> canonical workspace writer ownership

scripts/host_evidence_v4.py
-> paired current Host evidence

scripts/orchestration_guard.py
-> staged V4 lifecycle Guard
```

One dependency-free delegated responsibility is a smaller state shape inside this same runtime. It does not create TeamPlan or a second scheduler. Coordinated work adds TeamPlan and Work Graph dependency truth only when multiple unresolved delegated responsibilities or material dependency order requires them.

## Production Hook staging

The current production `hooks/hooks.json` remains the hardened compatibility spawn boundary until the real H00-H20 campaign proves the staged V4 lifecycle Hook contract on the target Codex Host.

`docs/v4/hooks.json` is the staged three-event candidate using `PreToolUse`, `PostToolUse`, and `SubagentStop`. Repository tests prove code behavior only. They do not promote staged configuration to observed Host truth.

## Package integrity boundary

The installed product integrity manifest should cover files required for current Skills, profiles, Hooks, Doctor/update, migration compatibility, Final Review, and the V4 runtime.

Maintainer-only calibration, experiment scoring/validation, and release-candidate evidence tools remain repository assets but do not need to make ordinary installed-product health fail when they are absent or changed. The integrity boundary is therefore an explicit product allowlist rather than an alias for every file in `scripts/`.

This integrity boundary does not claim that Codex physically omits maintainer files from the installed repository snapshot. Physical Plugin distribution is a separate Host/package behavior.

## Compatibility

V3 migration and compatibility code remains while it has active production, Doctor, or migration consumers. It is not dead code solely because V4 has a new runtime.

After V4 production Hook cutover and an explicit compatibility window, remaining V3 runtime paths should be reviewed for staged sunset with consumer proof. Storage extraction, facade/core consolidation, and legacy deletion are maintenance work and are intentionally outside the pre-H00 complexity closure.

## Design rule

One concept should have one current owner. Add a new component only when a concrete product or safety capability cannot be expressed safely through an existing owner. Prefer deleting competing representations and unused ceremony before adding abstractions.
