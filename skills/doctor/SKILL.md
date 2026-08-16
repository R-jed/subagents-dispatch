---
name: doctor
description: Diagnose subagents-dispatch package, installation, spawn guard, managed profiles, state, Host, and runtime-route health; mutate only on explicit lifecycle intent.
---

# Doctor

Diagnosis is read-only by default. Run `../../scripts/doctor.py --check` as the deterministic report owner and show its user-facing output verbatim. Do not rewrite statuses, hide `UNKNOWN`, or convert warnings into reassurance. Doctor never refreshes the Marketplace during ordinary diagnosis.

Before the eleven-layer report can start, `../../scripts/package_integrity.py` verifies the shipped runtime package against `.codex-plugin/package-integrity.json`. A bootstrap integrity failure is reported separately and is not a twelfth production layer.

The production report has exactly eleven layers, in this order:

```text
Plugin
Plugin installation
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

Keep evidence boundaries exact. Packaged configuration does not prove Host discovery, Hook trust, runtime route, permission state, or provenance. Missing evidence stays `UNKNOWN`. Do not edit Hook trust or `config.toml` to make Doctor green. The Experiment Plane remains separate from production health; compatibility calibration output belongs to development checks.

Use deterministic owners rather than reproducing their logic: `../../contracts/policy.json`, `../../contracts/state.md`, `../../contracts/guardrails.md`, `../../contracts/composition.md`, `../../docs/python-runtime.md`, `../../scripts/doctor_core.py`, `../../scripts/plugin_update.py`, `../../scripts/spawn_guard.py`, `../../scripts/install-agents.py`, `../../scripts/uninstall-agents.py`, `../../scripts/inspect-agent-runtime.py`, and `../../scripts/runtime-evidence.py`.

Resolve one Python 3.11+ interpreter according to `../../docs/python-runtime.md` before invoking bundled Python helpers interactively. Hook launcher failure is a Hook-runtime limitation, not a Host role rejection.

## Explicit update check

Only when the user asks whether an update is available, run:

```text
<python-3.11+> ../../scripts/check-plugin-update.py --codex-home <active-codex-home>
```

This is an explicit network/cache-refresh operation. It may refresh only the configured `subagents-dispatch` Marketplace snapshot, then reads `codex plugin list --json`. It must not run `codex plugin add`, reconcile profiles, mutate Dispatch state, or edit Hook trust. Show its deterministic output verbatim; a failed or ambiguous check must not fall through into update.

## Explicit update

Only when the user asks to update or upgrade, run:

```text
<python-3.11+> ../../scripts/doctor.py --codex-home <active-codex-home> --update
```

`--update` is exclusive with other Doctor checks and mutations. The updater requires the canonical versioned Marketplace source, installs the exact `subagents-dispatch@subagents-dispatch` release when needed, verifies the returned installed root, manifest and package integrity before managed-profile reconciliation, rechecks installed identity, and runs the newly installed Doctor. It never edits Hook trust. Show its output verbatim and honor `[RESTART]`.

`--repair`, `--migrate-legacy`, and `--cleanup-stale` are separate explicit mutation intents. Preserve unresolved writers, pending takeover, corrupt state, and unproven ownership. For managed-profile uninstall, run `../../scripts/uninstall-agents.py --codex-home <active-codex-home>` while the Plugin is still installed; never replace a refusal with wildcard deletion.

## Explicit live route workflow

Run live route verification only when explicitly requested. The Skill may create one bounded no-op child for each exact role:

```text
subagents_dispatch_reader
subagents_dispatch_worker
subagents_dispatch_solver
subagents_dispatch_investigator
subagents_dispatch_advisor
```

Spawn with `fork_turns = none`, delegation depth one, and no extra authority. Capture requested route, accepted role only when Host-exposed, parent/root and child identity, observed model/effort, effective permission state, and permission-source provenance only when directly evidenced. Settle every smoke child before returning.

Prefer public Host metadata. If required fields are absent and the exact rollout is locally available, use `../../scripts/inspect-agent-runtime.py` with exact child, parent, and role identity. The inspector streams exactly one rollout and enforces bounded total-rollout and per-line input limits. Oversized rollout input fails closed. Normalize once through `../../scripts/runtime-evidence.py` with `runtime_observation_required=true` and `requires_permission_observation=true`; candidate source kinds remain policy-owned, direct Host source evidence maps to `native_permission_source`, exact local inspector source evidence maps to `local_permission_source`, and `requires_permission_provenance=true` is added only when the claim actually requires source/selection provenance. Never infer a source from equal permission values. Configured, Requested, Accepted, and Observed remain distinct. Any observed mismatch or native/local conflict is `FAIL`; unavailable facts remain `UNKNOWN` only in the affected dimension.
