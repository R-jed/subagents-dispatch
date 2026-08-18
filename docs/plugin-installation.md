# Plugin Installation

Install the Marketplace source and Plugin:

```bash
codex plugin marketplace add R-jed/subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

After installation, start a new Codex session.

In the Codex App, open the Skill menu. This Plugin packages two explicit Skill identities:

```text
Orchestrate
Doctor
```

Orchestrate owns plan-only, execution, status, steer, takeover, cancel, continue, correction, review, and integration controls. Dispatch, Preview, Status, Steer, and Takeover are retired public Skill identities in V4. The exact slash entry rendered by the App is a Host/UI fact and must be observed directly rather than derived from package metadata.

## Python helper prerequisite

Managed-profile provisioning, deterministic Doctor helpers, explicit runtime-attestation helpers, Plugin update checks/verification, and the packaged guards require Python 3.11 or newer in the environment that runs them. Codex itself does not imply that the task shell exposes a command named `python`.

Before an interactive bundled helper is needed, resolve one supported Python 3.11+ interpreter according to [Python Helper Runtime](python-runtime.md). `python3`, `python`, or a platform launcher may be used when it resolves to Python 3.11+, and the same resolved interpreter should be used throughout that operation.

The Plugin Hook uses small platform launchers under `hooks/`. Unix checks supported `python3` and `python` invocations. Windows checks `py -3.11`, `python`, and `python3`. Each candidate must report Python 3.11+ before the launcher executes the guard. If no supported interpreter is available, the required Hook run is unavailable and managed V4 orchestration remains fail closed.

## Lifecycle Hook boundary

The current pre-cutover package keeps the hardened V3.x synchronous spawn guard at the Host's default Plugin discovery path:

```text
hooks/hooks.json
```

Before V4 release promotion, this production Hook matches only `PreToolUse` for `spawn_agent`. Its role is compatibility fail-closed protection while `docs/v4/hooks.json` remains staged. The staged V4 manifest adds managed lifecycle `PreToolUse`, `PostToolUse`, authoritative `list_agents` observation, and `SubagentStop` coverage. It may be promoted only after the exact-candidate H00-H20 Host campaign passes.

For a proposed subagents-dispatch managed child, the current production guard checks the already-prepared legacy-compatible state boundary before Codex executes the Host call. It requires the exact policy-owned `agent_type`, the prepared `native_task_name`, explicit `fork_turns=none`, delegation depth one, and no unresolved takeover transition.

Unrelated `spawn_agent` calls outside the reserved `subagents_dispatch_*` role namespace pass through unchanged. In the V4 staged path, authoritative lifecycle truth comes from exact root `list_agents` Pre/Post Hook observations bound to the current execution/control/lease generation. Lifecycle capacity truth is consumed before a lifecycle Host mutation crosses the tool boundary. Failed or ambiguous `PostToolUse` preserves fail-closed state; `SubagentStop` owns managed-child stop/veto behavior.

Codex may require the user to review and trust a new or changed Plugin Hook. subagents-dispatch does not edit Hook trust state to make diagnostics green.

## First delegated run

The Plugin package and its five managed custom-Agent profiles have separate local lifecycle state. On the first explicit task run through **Orchestrate** that actually needs a child, Orchestrate checks those five profiles before delegated execution.

If the profiles are absent and the managed paths are safe, Orchestrate automatically provisions only subagents-dispatch's five fixed Agent profiles plus its ownership manifest and installer lock, then runs the bundled installer `--check`. This first-use provisioning does not modify `config.toml`, credentials, MCP configuration, repositories, Hook trust state, or unrelated Agent profiles.

Codex loads custom-Agent role declarations when a task/session starts. Profiles created during the current live task are therefore not available to that task's in-memory Agent registry. After successful first-use provisioning, Orchestrate enters `RESTART_REQUIRED`, does not attempt to spawn the newly installed roles in the current task, and asks you to start one fresh Codex task/session, select **Orchestrate** again, and rerun the original request.

If a managed path is symlinked, conflicting, modified without proven ownership, or otherwise unsafe, automatic provisioning fails closed. Nothing unrelated is overwritten; use **Doctor** for the diagnosis and supported next action.

Plan-only, Status, and other non-spawning Orchestrate control intents do not provision missing profiles.

## Doctor

Doctor is the installed Plugin's health and maintenance surface. It diagnoses the Plugin the user is actually running. It does not decide whether a repository candidate may be published.

Normal Doctor diagnosis is read-only and offline. Run:

```text
<python-3.11+> scripts/doctor.py --codex-home <active-codex-home> --check
```

The user-facing report has five layers:

```text
Plugin package
Managed Agents
Host integration
Orchestration state
Legacy compatibility
```

`Plugin package` checks the executing package identity, package-integrity bootstrap, and exact Orchestrate/Doctor public surface.

`Managed Agents` checks the fixed Reader, Worker, Investigator, Solver, and Advisor contracts and whether the active Codex home has the owned profiles installed exactly. Missing or stale profiles are actionable installation health problems, not evidence that the bundled profile contract itself is invalid.

`Host integration` checks the production lifecycle Hook configuration in the installed package. When explicit Host capability evidence is supplied with `--host-evidence <file>`, Doctor validates it through `scripts/host_capabilities.py`. Without live Host evidence, observed Host behavior remains `UNKNOWN`. A local Hook file never counts as proof that the Host discovered, trusted, or executed it.

`Orchestration state` checks the current thread-scoped V4 state. Corrupt state, `WriterLease.UNKNOWN`, `PendingControl.UNKNOWN`, unknown execution lifecycle, and unresolved legacy active ownership remain fail closed. Ordinary active controls may appear as `WARN` while the state remains internally valid.

`Legacy compatibility` reports legacy managed-profile and V3 orchestration state separately. Active or ambiguous V3 state is never silently migrated into V4.

Doctor uses `[OK]`, `[WARN]`, `[FAIL]`, and `[UNKNOWN]`. Overall status is:

```text
HEALTHY   no diagnosed issue
DEGRADED  warnings or facts that cannot be observed from the current diagnostic context
BLOCKED   a confirmed package, ownership, Host-evidence, or orchestration safety failure
```

`--check` exits non-zero for `BLOCKED`. `WARN` and ordinary missing-observation `UNKNOWN` remain visible without pretending the package is corrupt.

### Explicit Doctor maintenance

Doctor changes local state only when the user explicitly requests a maintenance action. Supported owned actions are:

```text
--repair
--migrate-legacy
--cleanup-stale
--uninstall-managed
--update
```

`--repair` reconciles only the five subagents-dispatch managed profiles.

`--migrate-legacy` applies only to proven-owned legacy managed-profile installation state. It never migrates a live V3 orchestration capsule.

`--cleanup-stale` removes only stale terminal legacy orchestration state through the hardened compatibility helper. Active, corrupt, or ambiguous state remains preserved.

`--uninstall-managed` delegates to `scripts/uninstall-agents.py`. That helper verifies the ownership manifest, exact SHA-256 for every existing managed profile, regular-file identity, and race-sensitive revalidation before deleting anything. A missing, modified, symlinked, or unowned profile causes the uninstall to fail closed.

Maintenance actions are mutually exclusive in one Doctor invocation. After an action, Doctor reruns the same deterministic health report so the user can see the resulting state.

## Check for updates

Checking for an update is an explicit network/cache-refresh operation and is not part of normal Doctor diagnosis:

```text
<python-3.11+> scripts/check-plugin-update.py --codex-home <active-codex-home>
```

The update check may refresh only the configured subagents-dispatch Marketplace and then reread the machine-readable Plugin inventory. It must not install a Plugin, reconcile managed profiles, edit Hook trust, or mutate orchestration state.

## Update

For an explicit Doctor-managed update, run:

```text
<python-3.11+> scripts/doctor.py --codex-home <active-codex-home> --update
```

The updater is protected by package-integrity bootstrap. It records the installed Plugin identity, refreshes only the configured subagents-dispatch Marketplace, requires the refreshed Plugin source to be pinned to a semantic-version tag, installs the exact Plugin identity when the release differs, verifies the new installed root, reconciles its managed profiles, and reruns the newly installed package's static Doctor verification.

A successful package change reports `[RESTART]`. Start a fresh Codex session after updating. A changed Hook may require a fresh Host trust review. The updater never edits Hook trust or unrelated Codex configuration.

## Uninstall

If delegated work provisioned the five managed Agent profiles, remove those profiles before removing the Plugin package. While the Plugin is still installed, choose **Doctor** and explicitly request managed-profile uninstall, or run:

```text
<python-3.11+> scripts/doctor.py --codex-home <active-codex-home> --uninstall-managed
```

After the managed profiles are safely removed, remove the Plugin registration and Marketplace source:

```bash
codex plugin remove subagents-dispatch@subagents-dispatch
codex plugin marketplace remove subagents-dispatch
```

The packaged Hook is part of the Plugin tree and disappears with the Plugin package. Supported removal commands must leave unrelated Codex configuration and unrelated Agent profiles unchanged.
