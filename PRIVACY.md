# Privacy Policy

Last updated: 2026-08-08

subagents-dispatch is a local Codex plugin built around Skills. It also ships local helper scripts and managed custom-Agent templates used by those Skills. The project does not operate a developer-controlled server, analytics service, account system, advertising system, or telemetry endpoint.

## Data collected by the project

The subagents-dispatch project does not collect, transmit to the maintainer, sell, or retain personal data, conversation content, repository content, credentials, or usage telemetry through the plugin.

The plugin runs inside the user's Codex environment and may work with files, repositories, tools, and context that the user has already made available to Codex. Data handling performed by OpenAI Codex or by tools and services that the user enables is governed by those services' own terms, privacy policies, and workspace settings.

## Local configuration

When an explicit **Dispatch** Skill task actually needs delegation and the plugin's managed custom Agent roles are absent, subagents-dispatch may automatically provision five fixed TOML Agent profiles plus an ownership manifest and installer lock under the user's `CODEX_HOME`. Routine provisioning is limited to those plugin-owned paths. It does not modify `config.toml`, credentials, MCP configuration, repositories, or unrelated Agent profiles, and unsafe or unowned conflicting state is not overwritten automatically.

These local files contain plugin configuration and ownership/synchronization metadata. They do not contain project-operated credentials, conversation transcripts, or usage telemetry, and they are not sent to the project maintainer.

## Temporary dispatch state

For Status, Steer, Takeover, and Dispatch resume, the plugin may write one compact `active.json` capsule below the operating system's temporary directory:

```text
<OS temporary directory>/subagents-dispatch/<root-thread-id>/active.json
```

The capsule is scoped to one root thread and is private to the local user. It stores only bounded orchestration identity, lifecycle, locale, responsibility, authority, and receipt references. It does not store raw prompts, transcripts, private reasoning, credentials, full source files, or full tool output. The lock and capsule are not transmitted to the maintainer.

Normal terminal completion removes the thread capsule. A capsule older than seven days is considered stale. Doctor reports stale, corrupt, ambiguous, or unresolved-writer state without deleting it; an explicit cleanup action may remove only state proven safe to discard, while unresolved active writers are retained.

## Recipients

The project maintainer does not receive user data through the plugin. Data may be processed by OpenAI Codex or user-enabled tools only as part of the capabilities the user chooses to run and according to those services' own settings and policies.

## Retention

The project retains no user data collected through the plugin. Managed local configuration remains on the user's device until it is updated or removed by the user or by an authorized plugin lifecycle action. Temporary dispatch state is removed on normal terminal completion; stale terminal state is eligible for explicit cleanup after seven days, while unresolved writer state is preserved for review.

## User controls

Users can disable or uninstall subagents-dispatch and remove the plugin's managed local configuration. Repair, migration, upgrade, broader configuration changes, and resolution of conflicting or unowned state remain explicit user-controlled actions. Because the project does not operate a user account or remote data store, there is no project-held personal data account to delete.

## Security and privacy reports

Use the repository's GitHub security reporting channel for security-sensitive reports. Other privacy questions can be raised through the repository's GitHub issue tracker.
