# Plugin Installation

Install the Marketplace source and Plugin:

```bash
codex plugin marketplace add R-jed/subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

After installation, start a new Codex session.

In the Codex App, open the Skill menu. This Plugin packages six explicit Skill identities:

```text
Dispatch
Preview
Status
Steer
Takeover
Doctor
```

The exact slash entry rendered by the App is a Host/UI fact. Release validation records it directly from the App instead of deriving it from package metadata.

## Python helper prerequisite

Managed-profile provisioning, deterministic Doctor helpers, explicit runtime-attestation helpers, and the packaged spawn guard require Python 3.11 or newer in the environment that runs them. Codex itself does not imply that the task shell exposes a command named `python`.

Before an interactive bundled helper is needed, resolve one supported Python 3.11+ interpreter according to [Python Helper Runtime](python-runtime.md). `python3`, `python`, or a platform launcher may be used when it resolves to Python 3.11+, and the same resolved interpreter should be used throughout that operation. Resolving an available interpreter command is environment adaptation and does not change Agent, model, permission, or evidence semantics.

The Plugin Hook uses small platform launchers under `hooks/`. Unix checks supported `python3` and `python` invocations. Windows checks `py -3.11`, `python`, and `python3`. Each candidate must report Python 3.11+ before the launcher executes the guard. If no supported interpreter is available, that Hook run is unavailable and reports a Hook execution failure. Existing Dispatch contracts remain the correctness fallback. A launcher failure is not a Host role rejection and does not consume a child attempt.

If no Python 3.11+ interpreter is available for an interactive helper, provisioning or diagnostics that depend on that helper stop before child spawn with `PYTHON_PREREQUISITE_UNMET`. A missing command named `python` alone does not establish that failure when another supported Python 3.11+ invocation is available.

## Spawn guard Hook

The Plugin packages one synchronous Codex Hook at the Host's default Plugin discovery path:

```text
hooks/hooks.json
```

The Hook matches only `PreToolUse` for `spawn_agent`. It does not add an MCP control plane, daemon, scheduler, event bus, database, or background service.

For a proposed subagents-dispatch managed child, the guard checks the already-prepared Dispatch state before Codex executes the Host call. It requires the exact policy-owned `agent_type`, the prepared `native_task_name`, explicit `fork_turns=none`, delegation depth one, and no unresolved takeover transition. The guard reads state only. It does not create or mutate `active.json`, choose a route, bind the returned child identity, settle a writer, or perform Takeover.

Unrelated `spawn_agent` calls outside the reserved `subagents_dispatch_*` role namespace pass through unchanged. Native Host lifecycle observation plus `dispatch_state.py` reconciliation remain authoritative after a call crosses the tool boundary.

Codex may require the user to review and trust a new or changed Plugin Hook. subagents-dispatch does not edit Hook trust state to make diagnostics green. If the current Host does not support, trust, enable, or successfully run the Hook, Dispatch still applies the canonical Skill and contract checks. Doctor reports the runtime Hook status separately when explicit Host evidence is available.

## First delegated run

The Plugin package and its five managed custom-Agent profiles have separate local lifecycle state. On the first explicit task run through **Dispatch** that actually needs a child, Dispatch checks those five profiles before delegated execution.

If the profiles are absent and the managed paths are safe, Dispatch automatically provisions only subagents-dispatch's five fixed Agent profiles plus its ownership manifest and installer lock, then runs the bundled installer `--check`. This routine first-use provisioning is covered by the explicit Dispatch request; it does not modify `config.toml`, credentials, MCP configuration, repositories, Hook trust state, or unrelated Agent profiles.

Codex loads custom-Agent role declarations when a task/session starts. Profiles created during the current live task are therefore not available to that task's in-memory Agent registry. After successful first-use provisioning, Dispatch enters `RESTART_REQUIRED`, does not attempt to spawn the newly installed roles in the current task, and asks you to start one fresh Codex task/session, select **Dispatch** again, and rerun the original request. Once the profiles were present before task startup, later tasks can delegate normally.

If a managed path is symlinked, conflicting, modified without proven ownership, or otherwise unsafe, automatic provisioning fails closed. Nothing unrelated is overwritten; use **Doctor** for the exact diagnosis and next action.

Preview, Status, and other non-spawning control operations do not provision missing profiles.

For normal development work, choose **Dispatch** from the App's Skill menu and enter the task. Choose **Preview**, **Status**, **Steer**, or **Takeover** for the corresponding control. Use **Doctor** for installation, configuration, spawn-guard, and managed-profile diagnostics.

## Doctor diagnostics

Doctor is deterministic and read-only by default. It reports exactly ten production layers:

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

`Spawn guard package` verifies the shipped default-discovered Hook config, launchers, guard script, and machine policy. `Spawn guard runtime` is a different fact. Packaged files cannot prove that the current Host discovered, trusted, enabled, or executed the Hook. Without explicit Host Hook evidence, that layer remains `UNKNOWN` and ordinary Doctor may still report a healthy local installation.

Doctor uses stable `[OK]`, `[WARN]`, `[FAIL]`, and `[UNKNOWN]` output. An actionable warning or failure includes an exact next action when one exists. The Doctor Skill displays the deterministic report verbatim rather than reinterpreting its status.

A configured Agent profile is configured truth only; it is not observed runtime route proof. Missing Host capability is `UNKNOWN` with the supported limitation recorded; an externally captured capability record may be supplied with `--host-evidence <file>`. Runtime route integrity is not run during normal diagnosis; pass explicit evidence to `scripts/doctor.py --runtime-evidence <file>` when that claim matters. The deterministic `scripts/doctor.py` report never spawns a child. The Doctor Skill's explicit live-route workflow may create bounded smoke children only when the user explicitly requests live route verification.

Experiment Plane calibration remains separate from the ten production layers. Existing calibration CLI arguments are compatibility adapters to the dedicated calibration checker and appear only under development checks.

Stale, corrupt, ambiguous, or unresolved-writer temporary state is reported and preserved. Repair, migration, stale cleanup, and managed-profile uninstall require explicit intent.

## Update

```bash
codex plugin marketplace upgrade subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

Start a new Codex session after updating. A changed Hook may require a fresh Host trust review before the mechanical spawn guard becomes active.

Doctor can run the supported managed-profile repair or legacy migration only when explicitly requested. A Plugin upgrade still follows the Marketplace commands above and requires a fresh Codex session afterward. Doctor never silently changes Hook trust or unrelated Codex configuration.

## Uninstall

If delegated work provisioned the five managed Agent profiles, remove those profiles **before** removing the Plugin package. While the Plugin is still installed, choose **Doctor** and explicitly ask it to uninstall the subagents-dispatch managed Agent profiles. Doctor must use the bundled ownership-aware helper:

```text
scripts/uninstall-agents.py
```

The helper reads the existing subagents-dispatch ownership manifest, verifies every existing managed profile against the exact recorded SHA-256, rejects symlinks and modified or unowned files, removes only the exact proven-owned profile paths, then removes the ownership manifest. A profile already missing from an otherwise valid owned set does not authorize deletion of anything else. The installer lock is retained as a harmless local coordination file.

If ownership metadata is missing, invalid, or no longer matches an existing managed profile, uninstall fails closed. Do not replace that failure with `rm`, wildcard deletion, or manual removal of ambiguous Agent configuration.

After the managed profiles are safely removed, remove the Plugin registration and Marketplace source:

```bash
codex plugin remove subagents-dispatch@subagents-dispatch
codex plugin marketplace remove subagents-dispatch
```

The packaged Hook is part of the Plugin tree and disappears with the Plugin package. The managed-profile uninstall helper does not edit `config.toml`, credentials, MCP configuration, Hook trust state, repositories, or Plugin-unrelated Agent profiles. The supported `codex plugin remove` and `codex plugin marketplace remove` commands may update `config.toml` only to persist removal of this Plugin and Marketplace registration; unrelated configuration semantics and other Codex state must remain unchanged.
