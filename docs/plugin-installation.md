# Plugin Installation

Install the Marketplace source and Plugin:

```bash
codex plugin marketplace add R-jed/subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

Start a fresh Codex session after installation. The public Plugin surface contains exactly two Skills:

```text
Orchestrate
Doctor
```

Use **Orchestrate** for normal engineering work and orchestration controls. Use **Doctor** for installed-product diagnosis and explicitly requested ownership-safe maintenance.

## Python prerequisite

Bundled helpers require Python 3.11 or newer. The executable does not have to be named `python`; resolve one supported Python 3.11+ invocation from the current environment and use it consistently. See [Python Helper Runtime](python-runtime.md).

## First delegated run

The Plugin ships five fixed managed Agent profiles, but Codex loads custom-Agent availability at a Host/session boundary that may not hot-reload files created during the current task.

When Orchestrate first decides delegation is useful:

```text
exact managed role already available
-> delegate normally

role unavailable + managed files safely absent
-> provision only the five Plugin-owned profiles, ownership manifest, and installer lock
-> verify the installed files
-> return RESTART_REQUIRED for the current task

role unavailable + unsafe/conflicting ownership state
-> stop automatic provisioning
-> use Doctor for diagnosis
```

`RESTART_REQUIRED` means no child attempt was created. Start one fresh Codex task and submit the original request again. Orchestrate never substitutes a generic Agent merely to avoid this boundary.

If you want the first real development task to avoid the initialization interruption, run Doctor once after installation with explicit managed-profile repair/preparation intent, then start a fresh work session.

## Writer boundary

The current product manages one canonical mutable workspace. At most one managed writing actor may mutate that workspace at a time. Main may continue read-only work while a child writer owns the WriterLease, but conflicting integration writes wait for safe Host settlement and ownership transfer. See [Writer Boundary](writer-boundary.md).

## Host integration

Native Core relies on Codex Native Subagent lifecycle primitives and current Host observations. Plugin Hooks are outside the V4.0.0 correctness path.

When execution readiness must be proven, Doctor can consume a caller-supplied current Host capability snapshot. Missing Host evidence remains `UNKNOWN`; configured files or model self-report do not become observed Host truth.

Release qualification uses the candidate-bound N0-N8 campaign in `docs/v4/host-smoke.json`.

## Doctor

Normal Doctor diagnosis is deterministic, read-only, and offline:

```text
<python-3.11+> scripts/doctor.py --codex-home <active-codex-home> --check
```

It reports five current product areas:

```text
Plugin package
Managed Agents
Host integration
Orchestration state
Legacy compatibility
```

Doctor preserves `[OK]`, `[WARN]`, `[FAIL]`, and `[UNKNOWN]`. `--check` exits non-zero only for confirmed blocking failures; missing evidence remains visible rather than being rewritten as success.

Supported explicit maintenance actions are:

```text
--repair
--migrate-legacy
--cleanup-stale
--uninstall-managed
```

Only one maintenance action may be selected at a time. Ownership and filesystem safety checks remain fail closed.

## Check for updates

Update checking is explicit and may refresh only the configured canonical subagents-dispatch Marketplace:

```text
<python-3.11+> scripts/check-plugin-update.py --codex-home <active-codex-home>
```

This reports installed and available version identity. It does not install a Plugin or mutate managed profiles.

## Update

Run the explicit updater only when the user intends to install an update:

```text
<python-3.11+> scripts/plugin_update.py --codex-home <active-codex-home>
```

The updater verifies the canonical Marketplace and Plugin identity, refreshes the Marketplace, installs a newer stable release when available, verifies the installed package, reconciles only Plugin-owned managed profiles, and runs the newly installed Native Core Doctor contract as post-write validation.

A changed Plugin package requires a fresh Codex session before normal work resumes.

## Uninstall

If managed profiles were provisioned, remove them while the Plugin is still installed:

```text
<python-3.11+> scripts/doctor.py --codex-home <active-codex-home> --uninstall-managed
```

Then remove the Plugin and Marketplace source:

```bash
codex plugin remove subagents-dispatch@subagents-dispatch
codex plugin marketplace remove subagents-dispatch
```

Modified, ambiguous, symlinked, or unowned managed files are preserved and reported. Do not replace a refused ownership check with wildcard or manual deletion.
