# Plugin Installation

Install the Marketplace source and Plugin:

```bash
codex plugin marketplace add R-jed/subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

Start a fresh Codex session after installation. In the Skill menu, this Plugin exposes two public entries:

```text
Orchestrate
Doctor
```

Use **Orchestrate** for normal coding work and orchestration controls. Use **Doctor** when the installed Plugin, managed Agent profiles, Host integration, or orchestration state needs diagnosis or explicitly requested maintenance.

## Python prerequisite

Bundled helpers and Hook launchers require Python 3.11 or newer. A command literally named `python` is not required when another supported invocation resolves to Python 3.11+.

The packaged launchers try supported platform commands and verify the interpreter version before running the Guard. If no supported interpreter is available, the required operation stops safely. See [Python Helper Runtime](python-runtime.md) for the exact resolution rules.

## First delegated run

The Plugin ships five fixed managed Agent profiles, but those profile files live in the active Codex home and have a lifecycle separate from the Plugin package.

When an explicit Orchestrate task first decides that a child is useful, it requires the exact selected managed profile. If the managed files are safely absent, Orchestrate may provision only the five subagents-dispatch profile files, its ownership manifest, and installer lock. It does not edit credentials, MCP configuration, repositories, Hook trust, or unrelated Agent profiles.

Current V4 does not have an authoritative in-task registry observation that can prove a newly written custom-Agent profile became selectable in the already-running task. After provisioning in that task, Orchestrate therefore returns `RESTART_REQUIRED` and does not probe readiness by making a speculative `spawn_agent` call or substituting a generic Agent type. Start one fresh Codex task and submit the original request again. The fresh task must expose and honor the exact managed `agent_type` before delegated execution can proceed.

The real Host campaign records the Host's actual profile visibility and selector behavior. If future Host evidence provides a reliable in-task readiness boundary, a later product version may remove this conservative restart without weakening exact-profile guarantees.

If you want the first real development task to avoid the initialization interruption, use **Doctor** once in the first post-install session and explicitly request managed-profile repair or preparation. Then start a fresh work session and use Orchestrate normally.

If the profile files are symlinked, conflicting, modified without proven ownership, or otherwise unsafe, automatic provisioning stops. Use Doctor for the exact diagnosis. Plan-only and other non-spawning Orchestrate controls do not provision profiles merely to make their output more detailed.

## Writer boundary

The current Plugin manages one canonical mutable workspace. At most one managed writing actor may mutate that workspace at a time. Main can continue read-only work while a writing child owns the WriterLease, but conflicting integration writes wait for a safe ownership handoff.

Separate intended file lists inside one checkout do not prove safe write isolation. Future parallel writer support would require Host-bound independent worktrees or workspaces plus semantic independence and integration evidence. See [Writer Boundary](writer-boundary.md).

## Host integration

The installed Hook configuration is part of the Plugin package. Local configuration proves what the Plugin intends to run; it does not prove that a particular Codex Host discovered, trusted, or executed the Hook.

Doctor therefore keeps configured Host integration separate from observed Host truth. Missing current Host evidence remains visible as `UNKNOWN` where appropriate. The Plugin does not edit Hook trust or unrelated Codex configuration to make diagnostics green.

Release qualification of the exact production lifecycle Hook set is a maintainer workflow outside the Doctor Skill. `docs/v4/host-smoke.json` owns the real Host campaign contract.

## Doctor

Normal Doctor diagnosis is deterministic, read-only, and offline. Select **Doctor** in the Skill menu, or use the equivalent bundled helper:

```text
<python-3.11+> scripts/doctor.py --codex-home <active-codex-home> --check
```

The report covers:

```text
Plugin package
Managed Agents
Host integration
Orchestration state
Legacy compatibility
```

Doctor preserves `[OK]`, `[WARN]`, `[FAIL]`, and `[UNKNOWN]` instead of rewriting missing evidence into success. Top-level health reflects confirmed problems or warnings, while verification completeness separately records whether diagnostic facts remain `UNKNOWN`.

Doctor changes local state only after explicit user intent. Supported owned maintenance actions are:

```text
--repair
--migrate-legacy
--cleanup-stale
--uninstall-managed
--update
```

Repair touches only the five managed profiles. Legacy migration applies only to proven-owned profile installation state and never silently upgrades active V3 orchestration state. Stale cleanup removes only safe terminal legacy state. Managed uninstall removes only files proven to belong to this Plugin.

## Check for updates

Update checking is an explicit network-enabled operation and is separate from normal Doctor diagnosis:

```text
<python-3.11+> scripts/check-plugin-update.py --codex-home <active-codex-home>
```

It refreshes only the configured subagents-dispatch Marketplace and compares machine-readable installed and available version identity. Checking does not install a Plugin, repair profiles, change Hook trust, or mutate orchestration state.

## Update

For an explicit Doctor-managed update:

```text
<python-3.11+> scripts/doctor.py --codex-home <active-codex-home> --update
```

The updater accepts only the canonical subagents-dispatch Marketplace/Plugin identity, installs a versioned release when needed, verifies the newly installed package, reconciles the owned managed profiles, and runs the new Doctor contract before reporting success.

A changed Plugin package requires a fresh Codex session. A changed Hook may also require a Host trust review. The updater never edits Hook trust to force activation.

## Uninstall

If managed profiles were provisioned, remove them while the Plugin is still installed. Select **Doctor** and explicitly request managed-profile uninstall, or use:

```text
<python-3.11+> scripts/doctor.py --codex-home <active-codex-home> --uninstall-managed
```

The helper verifies the ownership manifest and exact recorded hashes before deleting anything. Modified, ambiguous, symlinked, or unowned files are preserved and the uninstall fails closed.

Then remove the Plugin and Marketplace source:

```bash
codex plugin remove subagents-dispatch@subagents-dispatch
codex plugin marketplace remove subagents-dispatch
```

The supported removal commands may update `config.toml` only to persist removal of this Plugin and Marketplace registration. All unrelated configuration semantics and other Codex state must remain unchanged.

Do not replace a refused ownership check with wildcard or manual deletion of ambiguous Agent configuration.
