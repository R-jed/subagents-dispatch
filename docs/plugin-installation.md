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

Orchestrate owns plan-only, execution, status, steer, takeover, cancel, continue, correction, review, and integration controls. Dispatch, Preview, Status, Steer, and Takeover are retired public Skill identities in V4. The exact slash entry rendered by the App is a Host/UI fact. Release validation records it directly from the App instead of deriving it from package metadata.

## Python helper prerequisite

Managed-profile provisioning, deterministic Doctor helpers, explicit runtime-attestation helpers, Plugin update checks/verification, and the packaged guards require Python 3.11 or newer in the environment that runs them. Codex itself does not imply that the task shell exposes a command named `python`.

Before an interactive bundled helper is needed, resolve one supported Python 3.11+ interpreter according to [Python Helper Runtime](python-runtime.md). `python3`, `python`, or a platform launcher may be used when it resolves to Python 3.11+, and the same resolved interpreter should be used throughout that operation. Resolving an available interpreter command is environment adaptation and does not change Agent, model, permission, or evidence semantics.

The Plugin Hook uses small platform launchers under `hooks/`. Unix checks supported `python3` and `python` invocations. Windows checks `py -3.11`, `python`, and `python3`. Each candidate must report Python 3.11+ before the launcher executes the guard. If no supported interpreter is available, that Hook run is unavailable and reports a Hook execution failure. V4 Orchestrate contracts remain fail closed when a required lifecycle guard is unavailable. A launcher failure is not a Host role rejection and does not consume a child attempt.

If no Python 3.11+ interpreter is available for an interactive helper, provisioning or diagnostics that depend on that helper stop before child spawn with `PYTHON_PREREQUISITE_UNMET`. A missing command named `python` alone does not establish that failure when another supported Python 3.11+ invocation is available.

## Lifecycle Hook boundary

The current pre-cutover package keeps the hardened V3.x synchronous spawn guard at the Host's default Plugin discovery path:

```text
hooks/hooks.json
```

Before V4 release promotion, this production Hook matches only `PreToolUse` for `spawn_agent`. Its role is compatibility fail-closed protection while `docs/v4/hooks.json` remains staged. The staged V4 manifest adds managed lifecycle `PreToolUse`, `PostToolUse`, authoritative `list_agents` observation, and `SubagentStop` coverage. It may be promoted only after the exact-candidate H00-H20 Host campaign passes.

For a proposed subagents-dispatch managed child, the current production guard checks the already-prepared legacy-compatible state boundary before Codex executes the Host call. It requires the exact policy-owned `agent_type`, the prepared `native_task_name`, explicit `fork_turns=none`, delegation depth one, and no unresolved takeover transition. The pre-cutover guard does not establish V4 PendingControl ACK, WriterLease settlement, or H00-H20 evidence.

Unrelated `spawn_agent` calls outside the reserved `subagents_dispatch_*` role namespace pass through unchanged. In the V4 staged path, authoritative lifecycle truth comes from exact root `list_agents` Pre/Post Hook observations bound to the current execution/control/lease generation. Lifecycle capacity truth is consumed before a lifecycle Host mutation crosses the tool boundary. Failed or ambiguous `PostToolUse` rejects the tool result and preserves fail-closed state; `SubagentStop` owns managed-child stop/veto behavior.

Codex may require the user to review and trust a new or changed Plugin Hook. subagents-dispatch does not edit Hook trust state to make diagnostics green. If the current Host does not support, trust, enable, or successfully run the required V4 Hook set, V4 delegated execution remains unsupported and release readiness stays blocked. Doctor reports installed Host integration separately when explicit Host evidence is available.

## First delegated run

The Plugin package and its five managed custom-Agent profiles have separate local lifecycle state. On the first explicit task run through **Orchestrate** that actually needs a child, Orchestrate checks those five profiles before delegated execution.

If the profiles are absent and the managed paths are safe, Orchestrate automatically provisions only subagents-dispatch's five fixed Agent profiles plus its ownership manifest and installer lock, then runs the bundled installer `--check`. This routine first-use provisioning is covered by the explicit Orchestrate request; it does not modify `config.toml`, credentials, MCP configuration, repositories, Hook trust state, or unrelated Agent profiles.

Codex loads custom-Agent role declarations when a task/session starts. Profiles created during the current live task are therefore not available to that task's in-memory Agent registry. After successful first-use provisioning, Orchestrate enters `RESTART_REQUIRED`, does not attempt to spawn the newly installed roles in the current task, and asks you to start one fresh Codex task/session, select **Orchestrate** again, and rerun the original request. Once the profiles were present before task startup, later tasks can delegate normally.

If a managed path is symlinked, conflicting, modified without proven ownership, or otherwise unsafe, automatic provisioning fails closed. Nothing unrelated is overwritten; use **Doctor** for the exact diagnosis and next action.

Plan-only, Status, and other non-spawning Orchestrate control intents do not provision missing profiles.

For normal development work, choose **Orchestrate** from the App's Skill menu and enter the task or control intent. Use **Doctor** for installed Plugin, managed-profile, Host-integration, orchestration-state, legacy-compatibility, update, and ownership-aware maintenance diagnostics.

## Doctor diagnostics

Doctor is the installed Plugin's health and explicit maintenance surface. It diagnoses the Plugin the user is actually running. Repository publication approval, candidate evidence, H00-H20 release approval, CI state, runtime-attestation campaigns, and calibration campaigns remain outside the Doctor Skill.

Normal Doctor diagnosis is deterministic, read-only, and offline. Run:

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

`Managed Agents` checks the fixed Reader, Worker, Investigator, Solver, and Advisor contracts and whether the active Codex home has the owned profiles installed exactly. Missing or safely repairable profiles are `WARN`. Symlink, reserved-role collision, modified ownership, or filesystem-safety conflicts remain `FAIL`.

`Host integration` checks the installed production lifecycle Hook configuration. When explicit Host capability evidence is supplied with `--host-evidence <file>`, Doctor validates it through `scripts/host_capabilities.py`. Without live Host evidence, observed Host behavior remains `UNKNOWN`. Local Hook configuration never counts as proof that the Host discovered, trusted, or executed it.

`Orchestration state` checks the current thread-scoped V4 state. Corrupt state, `WriterLease.UNKNOWN`, `PendingControl.UNKNOWN`, unknown execution lifecycle, and unresolved legacy active ownership remain fail closed. Ordinary active controls may appear as `WARN` while the state remains internally valid.

`Legacy compatibility` reports legacy managed-profile and V3 orchestration state separately. Active or ambiguous V3 state is never silently migrated into V4.

Doctor uses stable `[OK]`, `[WARN]`, `[FAIL]`, and `[UNKNOWN]` output. Overall status is:

```text
HEALTHY   no diagnosed issue
DEGRADED  warnings or facts that cannot be observed from the current diagnostic context
BLOCKED   a confirmed package, ownership, Host-evidence, or orchestration safety failure
```

`--check` exits non-zero for `BLOCKED`. `WARN` and ordinary missing-observation `UNKNOWN` remain visible without pretending the package is corrupt. The Doctor Skill displays deterministic output verbatim rather than reinterpreting its status.

Normal Doctor diagnosis does not run `codex plugin marketplace upgrade`, fetch a newer Marketplace revision, reinstall the Plugin, change Hook trust, mutate orchestration state, or spawn a child.

Runtime attestation remains a separate compatibility workflow owned by `scripts/runtime-evidence.py`; Doctor does not expose its evidence or live-route flags. Release authority remains with the dedicated candidate-bound release verifier.

Doctor changes local state only when the user explicitly requests a maintenance action. Supported owned actions are:

```text
--repair
--migrate-legacy
--cleanup-stale
--uninstall-managed
--update
```

`--repair` reconciles only the five subagents-dispatch managed profiles. `--migrate-legacy` applies only to proven-owned legacy managed-profile installation state and never migrates a live V3 orchestration capsule. `--cleanup-stale` removes only stale terminal legacy orchestration state through the hardened compatibility helper. Active, corrupt, or ambiguous state remains preserved. `--uninstall-managed` delegates to the ownership-aware `scripts/uninstall-agents.py` helper.

Maintenance actions are mutually exclusive in one Doctor invocation. After an action, Doctor reruns the same deterministic health report so the user can see the resulting state.

## Check for updates

When you want to know whether the configured Marketplace currently offers a newer release without installing it, run the explicit update check:

```text
<python-3.11+> scripts/check-plugin-update.py --codex-home <active-codex-home>
```

This operation explicitly allows a network/cache refresh. It invokes only the configured subagents-dispatch Marketplace upgrade command, then rereads the machine-readable installed Plugin inventory:

```bash
codex plugin marketplace upgrade subagents-dispatch
codex plugin list --json
```

The check reports Installed and Available versions plus package/cache skew. It does not run `codex plugin add`, reconcile managed Agent profiles, edit Hook trust, or mutate V4 orchestration state. If the Marketplace refresh fails, it stops and reports that failure. A request to check for updates never falls through into installing an update.

## Update

For an explicit Doctor-managed update, resolve the supported Python interpreter and run:

```text
<python-3.11+> scripts/doctor.py --codex-home <active-codex-home> --update
```

This operation is deliberately separate from normal diagnosis and the update check. The updater uses Codex's supported machine-readable commands. It first records the installed Plugin identity, refreshes only the configured subagents-dispatch Marketplace, requires the refreshed Plugin source to be pinned to a semantic-version tag, and installs the exact Plugin identity when the refreshed release differs:

```bash
codex plugin marketplace upgrade subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

After Codex returns the new installed root and version, the updater verifies that root's Plugin manifest, runs that newly installed package's managed-profile installer and `--check`, rereads `codex plugin list --json`, and runs the newly installed Doctor for package/static post-write verification. Marketplace refresh alone never counts as a successful Plugin update.

If the refreshed versioned Marketplace ref already equals the installed version, the updater does not reinstall the same Plugin. If Codex's installed cache is current but the active task is still running an older package, Doctor reports package/cache skew and the corrective action is a fresh session.

A successful package change reports `[RESTART]`. Start a fresh Codex session after updating. A changed Hook may require a fresh Host trust review before the mechanical guard becomes active. The updater never edits Hook trust or unrelated Codex configuration to make verification pass.

Doctor can also run supported managed-profile repair, legacy migration, stale cleanup, or owned managed-profile uninstall only when explicitly requested. These are separate lifecycle intents and cannot be combined with `--update` in one Doctor invocation.

## Uninstall

If delegated work provisioned the five managed Agent profiles, remove those profiles **before** removing the Plugin package. While the Plugin is still installed, choose **Doctor** and explicitly ask it to uninstall the subagents-dispatch managed Agent profiles. Doctor delegates to the bundled ownership-aware helper. The equivalent explicit CLI action is:

```text
<python-3.11+> scripts/doctor.py --codex-home <active-codex-home> --uninstall-managed
```

The helper reads the existing subagents-dispatch ownership manifest, verifies every existing managed profile against the exact recorded SHA-256, rejects symlinks and modified or unowned files, removes only the exact proven-owned profile paths, then removes the ownership manifest. A profile already missing from an otherwise valid owned set does not authorize deletion of anything else. The installer lock is retained as a harmless local coordination file.

If ownership metadata is missing, invalid, or no longer matches an existing managed profile, uninstall fails closed. Do not replace that failure with `rm`, wildcard deletion, or manual removal of ambiguous Agent configuration.

After the managed profiles are safely removed, remove the Plugin registration and Marketplace source:

```bash
codex plugin remove subagents-dispatch@subagents-dispatch
codex plugin marketplace remove subagents-dispatch
```

The packaged Hook is part of the Plugin tree and disappears with the Plugin package. The managed-profile uninstall helper does not edit `config.toml`, credentials, MCP configuration, Hook trust state, repositories, or Plugin-unrelated Agent profiles. The supported `codex plugin remove` and `codex plugin marketplace remove` commands may update `config.toml` only to persist removal of this Plugin and Marketplace registration; unrelated configuration semantics and other Codex state must remain unchanged.
