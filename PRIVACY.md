# Privacy Policy

Last updated: 2026-08-16

subagents-dispatch is a local Codex plugin built around Skills, Codex Native Subagents, one local spawn-guard Hook, and bundled local helper scripts. The project does not operate a developer-controlled server, analytics service, account system, advertising system, telemetry endpoint, or remote orchestration service.

## Data collected by the project

The subagents-dispatch project does not collect, transmit to the maintainer, sell, or retain personal data, conversation content, repository content, credentials, or usage telemetry through the plugin.

The plugin runs inside the user's Codex environment and may work with files, repositories, tools, and context that the user has already made available to Codex. Data handling performed by OpenAI Codex or by tools and services that the user enables is governed by those services' own terms, privacy policies, and workspace settings.

## Local configuration

When an explicit **Dispatch** Skill task actually needs delegation and the plugin's managed custom Agent roles are absent, subagents-dispatch may automatically provision five fixed TOML Agent profiles plus an ownership manifest and installer lock under the user's `CODEX_HOME`. Routine provisioning is limited to those plugin-owned paths. It does not modify `config.toml`, credentials, MCP configuration, Hook trust state, repositories, or unrelated Agent profiles, and unsafe or unowned conflicting state is not overwritten automatically.

These local files contain plugin configuration and ownership/synchronization metadata. They do not contain project-operated credentials, conversation transcripts, or usage telemetry, and they are not sent to the project maintainer.

## Local spawn guard Hook

The Plugin packages one synchronous `PreToolUse` Hook for `spawn_agent` under the Host's default Plugin Hook path `hooks/hooks.json`.

Codex supplies the proposed tool call to the local Hook process. For a subagents-dispatch managed spawn, the guard reads only the structural fields required to check the action boundary, including the caller/target Agent identity when present, `task_name`, and `fork_turns`. It compares those facts with the already-prepared thread-local Dispatch state and the bundled machine policy.

The proposed spawn may also contain a task message or other Host fields. The guard does not use those fields as task evidence, does not persist them, does not echo them in a block reason, and does not write the raw Hook input to logs or project state. Hook failures emit only bounded generic diagnostic information. The Hook performs no network request, sends no telemetry, and subagents-dispatch sends no Hook data to the maintainer.

The Hook does not create a second orchestration control plane. It does not spawn Agents itself, route work, create or mutate `active.json`, bind child identity, release a writer, or perform Takeover. Native Host observation and the existing Dispatch state/reconciliation contracts remain authoritative.

Codex may require user review and trust for a new or changed Hook. subagents-dispatch does not silently change that Host trust state. If the Hook is unsupported, untrusted, disabled, or fails to launch, the Plugin's existing Skill and contract checks remain the correctness fallback and Doctor reports the runtime Hook fact only when supported Host evidence is available.

## Plugin installation identity and explicit update operations

Ordinary Doctor diagnosis may invoke the local Codex CLI command `codex plugin list --json` to inspect the currently installed subagents-dispatch Plugin cache, enablement state, and configured Marketplace source identity. This read-only check does not refresh the Marketplace and does not intentionally send conversation content, repository content, prompts, transcripts, or tool payloads to the project maintainer.

When the user explicitly asks to check for updates, the bundled update-check helper asks Codex to refresh only the configured subagents-dispatch Marketplace snapshot and then rereads the local Plugin inventory. This explicit check may contact the configured Git/Marketplace source through Codex, but it does not install a Plugin, reconcile managed Agent profiles, edit Hook trust, or mutate Dispatch state. A request to check for updates does not authorize installing the update.

When the user explicitly requests a subagents-dispatch update, the bundled updater invokes Codex's supported Plugin lifecycle commands to refresh the configured subagents-dispatch Marketplace and install the selected versioned Plugin release when needed. Those Codex commands may contact the configured Git/Marketplace source as part of the user-requested operation. Network transport and cache management performed by Codex or Git are governed by those tools and services. The subagents-dispatch project does not operate its own update server, telemetry service, account service, or network endpoint.

After installation, the updater reads the new local Plugin manifest, reconciles only the five plugin-owned managed Agent profiles through the newly installed package, rechecks the installed Plugin inventory, and runs the newly installed Doctor for local post-write validation. It does not upload those validation results to the maintainer. It does not read or transmit conversation transcripts or repository source as part of Plugin update verification.

The updater does not edit Hook trust state, credentials, unrelated Plugin registrations, unrelated Marketplaces, unrelated Agent profiles, or project repositories to make an update pass. The update-check helper does not edit those surfaces either. If installed identity or post-write verification does not converge, the relevant operation reports failure rather than silently rewriting unrelated state.

## Temporary dispatch state

For Status, Steer, Takeover, and Dispatch resume, the plugin may write one compact `active.json` capsule below the operating system's temporary directory:

```text
<OS temporary directory>/subagents-dispatch/<root-thread-id>/active.json
```

The capsule is scoped to one root thread and is private to the local user. It stores only bounded orchestration identity, lifecycle, locale, responsibility, authority, and receipt references. It does not store raw prompts, transcripts, private reasoning, credentials, full source files, or full tool output. The lock and capsule are not transmitted to the maintainer.

Normal terminal completion removes the thread capsule. A capsule older than seven days is considered stale. Doctor reports stale, corrupt, ambiguous, or unresolved-writer state without deleting it; an explicit cleanup action may remove only state proven safe to discard, while unresolved active writers are retained.

## Local runtime attestation

Normal Dispatch, Preview, Status, Steer, Takeover, and static Doctor operation do not inspect Codex session rollouts. When the user explicitly requests live route verification, Doctor may use the bundled runtime inspector if the Host's public metadata does not expose all required route facts.

That helper searches the local Codex sessions directory for the one rollout whose filename matches the exact requested child thread UUID. It reads that rollout locally and parses only `session_meta` and `turn_context` records needed to establish child identity, ancestry, model, reasoning effort, sandbox/permission metadata, and runtime version. It does not scan transcript records for task facts and does not emit prompts, assistant output, tool payloads, reasoning, source contents, or the rollout path.

The inspector returns only the allowlisted routing/identity metadata to the local Doctor/runtime-evidence workflow. It does not upload the rollout, extracted metadata, or session content to the project maintainer, and subagents-dispatch does not retain a separate rollout copy or transcript archive.

## Recipients

The project maintainer does not receive user data through the plugin. Data may be processed by OpenAI Codex, Git hosting, or user-enabled tools only as part of capabilities the user chooses to run and according to those services' own settings and policies.

## Retention

The project retains no user data collected through the plugin. Managed local configuration remains on the user's device until it is updated or removed by the user or by an authorized plugin lifecycle action. Temporary dispatch state is removed on normal terminal completion; stale terminal state is eligible for explicit cleanup after seven days, while unresolved writer state is preserved for review.

The spawn guard does not create a project-owned history of Hook calls. The explicit update-check helper and Plugin updater do not create a project-operated update-history service or upload a separate update report. The explicit runtime-attestation helper does not create or retain a project-owned copy of a Codex rollout. Any source rollout remains part of the user's local Codex session data and follows the retention behavior of Codex itself.

## User controls

Users can disable or uninstall subagents-dispatch and remove the plugin's managed local configuration. Update checks, updates, repair, migration, broader configuration changes, and resolution of conflicting or unowned state remain explicit user-controlled actions. Live route verification is also explicit; ordinary plugin use does not require local rollout inspection. Hook enablement and trust remain Host/user controls. Ordinary Doctor diagnosis may inspect local installed Plugin identity without refreshing the Marketplace. Because the project does not operate a user account or remote data store, there is no project-held personal data account to delete.

## Security and privacy reports

Use the repository's GitHub security reporting channel for security-sensitive reports. Other privacy questions can be raised through the repository's GitHub issue tracker.
