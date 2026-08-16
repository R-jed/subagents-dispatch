---
name: doctor
description: Diagnose subagents-dispatch Plugin, Skill, spawn-guard, managed-Agent, dispatch-state, Codex Host, and runtime-route health; mutate only on explicit supported lifecycle intent.
---

# Doctor

Use this Skill for subagents-dispatch installation and runtime health. Diagnosis is read-only by default. Repair, uninstall, cleanup, migration, or live route smoke requires explicit user intent.

Run `../../scripts/doctor.py --check` as the deterministic report owner and show its user-facing output verbatim. Do not rewrite statuses, hide `UNKNOWN`, or convert a warning into reassurance. The production report has exactly ten layers, in this order:

```text
Plugin
Skills
Spawn guard package
Managed Agent profiles
Dispatch state
Codex Host
Spawn guard runtime
Runtime route
Effective permission state
Permission-source provenance
```

`Spawn guard package` verifies the bundled `spawn_agent` PreToolUse Hook, cross-platform launchers, deterministic guard script, and machine policy. `Spawn guard runtime` is separate Host evidence. Static configuration never proves that Codex discovered, trusted, enabled, or executed a Hook. Missing explicit Host Hook evidence remains `UNKNOWN`; ordinary Doctor may still be healthy when all required static and local layers pass.

Use deterministic owners instead of reproducing their logic:

- `../../contracts/policy.json`: required Skills, five configured routes, `fork_turns=none`, and hard invariants
- `../../contracts/state.md`: ephemeral dispatch-state meaning and safety
- `../../contracts/guardrails.md`: mutation, trust, and user-authority boundaries
- `../../contracts/composition.md`: optional Hook composition and the prohibition on a second orchestration control plane
- `../../docs/python-runtime.md`: Python 3.11+ helper-runtime resolution and prerequisite failure semantics
- `../../scripts/doctor.py`: CLI, explicit lifecycle actions, and deterministic report invocation
- `../../scripts/doctor_core.py`: production diagnostic semantics and rendering
- `../../scripts/spawn_guard.py`: read-only proposed-spawn validator
- `../../scripts/install-agents.py`: managed-profile install/check lifecycle
- `../../scripts/uninstall-agents.py`: ownership-aware managed-profile removal
- `../../scripts/inspect-agent-runtime.py`: exact Codex child-rollout allowlist inspection for explicit live attestation
- `../../scripts/runtime-evidence.py`: configured/requested, accepted, and observed route normalization

Before invoking a bundled Python helper interactively, resolve one Python 3.11+ interpreter from the actual task environment according to `../../docs/python-runtime.md` and keep it fixed for the operation. The packaged Hook uses its own small Unix/Windows launcher to resolve an equivalent Python 3.11+ process at Hook execution time. If that Hook launcher cannot resolve Python, the Hook run itself is unavailable and existing Skill/contract validation remains the correctness fallback; do not misreport that launcher failure as a Host role rejection.

Do not edit Codex Hook trust state or `config.toml` to make Doctor green. When the Host exposes Plugin Hook state, capture only directly observed facts and normalize them into explicit Host evidence. A normalized `plugin_hooks` row may contain `plugin`, `event`, `source`, `handler_type`, `execution_mode`, `trust_status`, and `enabled`. Do not infer trust, enablement, or source from the packaged `hooks.json`. `Trusted` or managed Host state is evidence only when the Host reports it. `Untrusted` or disabled is a warning; `Modified`, duplicate, wrong-source, or wrong-mode state fails the Hook-runtime layer.

The Experiment Plane remains separate. Legacy calibration CLI flags are compatibility adapters to `scripts/calibration_profiles.py check` and appear under development checks, outside the ten production Doctor layers. They do not become ordinary product health requirements.

`--repair`, `--migrate-legacy`, and `--cleanup-stale` are explicit mutation intents. Preserve unresolved writers, planned work, pending takeover, and corrupt capsules for review. For explicit managed-profile uninstall intent, run the bundled ownership-aware helper while the Plugin is still installed:

```text
<python-3.11+> ../../scripts/uninstall-agents.py --codex-home <active-codex-home>
```

Do not replace an uninstall refusal with manual wildcard deletion or edits to the ownership manifest.

## Explicit live route workflow

Run this workflow only when the user explicitly requests live route verification. The Doctor Skill, not `scripts/doctor.py`, may create five bounded native children, one for each exact configured role:

```text
subagents_dispatch_reader
subagents_dispatch_worker
subagents_dispatch_solver
subagents_dispatch_investigator
subagents_dispatch_advisor
```

Spawn each controlled child with `fork_turns = none`, delegation depth one, a no-op verification responsibility, and no authority beyond what the role check requires. Capture requested route, Host-accepted role identity when exposed, parent/root identity, child identity, and only the model, effort, and permission facts the Host actually exposes. Stop or settle every smoke child before returning.

For each child, inspect public Host/spawn/details metadata first. Public Host metadata is preferred. If it omits a required runtime field and the exact Codex rollout is locally available, run:

```text
<python-3.11+> ../../scripts/inspect-agent-runtime.py <child-thread-id> \
  --expected-parent-thread-id <root-thread-id> \
  --expected-agent-role <exact-agent-type>
```

The inspector streams exactly one rollout, enforces bounded total-rollout and per-line input limits, emits only allowlisted identity/route/permission fields, and fails closed on oversized or ambiguous evidence. Oversized rollout input fails closed. It never promotes transcript content into task truth.

Build the expected route from `contracts/policy.json`, set `runtime_observation_required=true` and `requires_permission_observation=true`, place public Host runtime metadata in `native`, and place only the exact inspector output in `local`. When the Host directly exposes permission-source provenance, place that evidence in `native_permission_source`; use `local_permission_source` only for the exact inspector-derived source record. The candidate source kinds remain policy-owned by `contracts/policy.json`. Never infer a source from equal permission values. Add `requires_permission_provenance=true` only for a claim that actually requires source or selection provenance. Missing provenance stays `UNKNOWN` without erasing independently verified route or effective permission state.

Normalize once through `scripts/runtime-evidence.py`. Configured, Requested, Accepted, and Observed remain separate evidence levels. A matching accepted role is not observed runtime proof. Any observed mismatch or conflicting native/local evidence is `FAIL`; unavailable facts remain `UNKNOWN` only in the affected dimension.
