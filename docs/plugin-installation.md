# Plugin Installation

Install the Marketplace source and Plugin:

```bash
codex plugin marketplace add R-jed/subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

After installation, start a new Codex session.

## First delegated run

The Plugin package and its five managed custom-Agent profiles have separate local lifecycle state. On the first explicit `/dispatch` task that actually needs a child, Dispatch checks those five profiles before delegated execution.

If the profiles are absent and the managed paths are safe, Dispatch automatically provisions only subagents-dispatch's five fixed Agent profiles plus its ownership manifest and installer lock, then runs the bundled installer `--check`. This routine first-use provisioning is covered by the explicit `/dispatch` request; it does not modify `config.toml`, credentials, MCP configuration, repositories, or unrelated Agent profiles.

Codex loads custom-Agent role declarations when a task/session starts. Profiles created during the current live task are therefore not available to that task's in-memory Agent registry. After successful first-use provisioning, Dispatch enters `RESTART_REQUIRED`, does not attempt to spawn the newly installed roles in the current task, and asks you to start one fresh Codex task/session and rerun the original `/dispatch` request. Once the profiles were present before task startup, later tasks can delegate normally.

If a managed path is symlinked, conflicting, modified without proven ownership, or otherwise unsafe, automatic provisioning fails closed. Nothing unrelated is overwritten; use `/doctor` for the exact diagnosis and next action.

Preview, Status, and other non-spawning control operations do not provision missing profiles.

Normal development work:

```text
/dispatch <task>
```

Optional 2.1 controls use the same Skill:

```text
/dispatch preview <task>
/dispatch status
/dispatch steer <unit_id>: <guidance>
/dispatch takeover <unit_id>
```

Use `/doctor` for installation, configuration, managed-profile, and upgrade diagnostics. You can also use `/skills` to open the Codex Skill picker.

## Update

```bash
codex plugin marketplace upgrade subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

Start a new Codex session after updating.

Doctor can perform the supported upgrade flow when explicitly requested:

```text
/doctor Upgrade subagents-dispatch and tell me what remains afterward.
```

## Uninstall

Remove the Plugin registration and the Marketplace source:

```bash
codex plugin remove subagents-dispatch@subagents-dispatch
codex plugin marketplace remove subagents-dispatch
```

If delegated work previously provisioned the managed Agent profiles, remove those exact files and the install manifest as well:

```bash
rm ~/.codex/agents/subagents-dispatch-reader.toml
rm ~/.codex/agents/subagents-dispatch-worker.toml
rm ~/.codex/agents/subagents-dispatch-solver.toml
rm ~/.codex/agents/subagents-dispatch-investigator.toml
rm ~/.codex/agents/subagents-dispatch-advisor.toml
rm ~/.codex/.subagents-dispatch-agents.json
```

The installer lock is a local coordination file and may remain. Do not delete unrelated Agent profiles or Codex configuration.
