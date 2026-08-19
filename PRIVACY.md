# Privacy Policy

Last updated: 2026-08-20

subagents-dispatch is a local Codex Plugin built around two explicit Skills, Codex Native Subagents, local Hook definitions, and bundled helper scripts. The project does not operate a developer-controlled server, analytics service, account system, advertising system, telemetry endpoint, or remote orchestration service.

## Data collected by the project

The subagents-dispatch project does not collect, transmit to the maintainer, sell, or retain personal data, conversation content, repository content, credentials, or usage telemetry through the Plugin.

The Plugin runs inside the user's Codex environment and may work with files, repositories, tools, and context that the user has already made available to Codex. Data handling performed by OpenAI Codex or by tools and services that the user enables is governed by those services' own terms, privacy policies, and workspace settings.

## Local configuration

When an explicit **Orchestrate** task actually needs delegation and the Plugin's managed custom Agent roles are absent, subagents-dispatch may automatically provision five fixed TOML Agent profiles plus an ownership manifest and installer lock under the user's `CODEX_HOME`. Routine provisioning is limited to those Plugin-owned paths. It does not modify `config.toml`, credentials, MCP configuration, Hook trust state, repositories, or unrelated Agent profiles, and unsafe or unowned conflicting state is not overwritten automatically.

These local files contain Plugin configuration and ownership or synchronization metadata. They do not contain project-operated credentials, conversation transcripts, or usage telemetry, and they are not sent to the project maintainer.

## Local lifecycle Hooks

subagents-dispatch packages local synchronous Codex Hook definitions used to enforce managed Agent boundaries and to bind inspectable Host lifecycle evidence. Before the V4 lifecycle cutover, the production `hooks/hooks.json` remains the compatibility managed-spawn guard. The complete V4 PreToolUse, PostToolUse, and SubagentStop definition is staged separately and is activated only after the real Host campaign required by the release contract passes.

For a managed lifecycle call, Codex supplies the proposed tool call to the local Hook process. The Guard inspects only the structural identity and control fields needed for the safety boundary, such as the Hook event, root session identity, caller Agent type when exposed, exact tool identity, `tool_use_id`, target or task name, profile selector, `fork_turns`, and the tool-input representation needed to verify a prepared control. A managed child peer-message attempt may also be blocked when the Host exposes `send_message`.

The proposed call may contain a task message or another Host field. The Guard does not use raw message text as repository evidence, does not persist raw Hook input, does not echo raw message bodies in block reasons, and does not write raw Hook payloads to a project-operated log. Prepared V4 controls retain a bounded deterministic digest and the structural state required for lifecycle authorization. The H08 Host gate must verify that the Host's actual message representation is compatible with that binding before V4 lifecycle Hooks become production authority.

PostToolUse processing may inspect the structural response needed to acknowledge an exact control or ingest a paired `list_agents` observation. Missing, stale, ambiguous, or unbound evidence remains fail closed. The Plugin does not parse arbitrary response prose to manufacture release or writer authority when the Host does not expose a reliable outcome contract.

SubagentStop processing may return a local stop decision for managed Agent types so automatic continuation remains under the main session's orchestration control.

The Hook processes perform no project-operated network request and send no Hook data to the maintainer. Hook trust and enablement remain Host or user controls.

## Plugin installation identity and explicit update operations

Ordinary Doctor diagnosis may invoke the local Codex CLI command `codex plugin list --json` to inspect the currently installed subagents-dispatch Plugin cache, enablement state, and configured Marketplace source identity. This read-only check does not refresh the Marketplace and does not intentionally send conversation content, repository content, prompts, transcripts, or tool payloads to the project maintainer.

When the user explicitly asks to check for updates, the bundled update-check helper asks Codex to refresh only the configured subagents-dispatch Marketplace snapshot and then rereads the local Plugin inventory. This explicit check may contact the configured Git or Marketplace source through Codex, but it does not install a Plugin, reconcile managed Agent profiles, edit Hook trust, or mutate orchestration state. A request to check for updates does not authorize installing the update.

When the user explicitly requests a subagents-dispatch update, the bundled updater invokes Codex's supported Plugin lifecycle commands to refresh the configured Marketplace and install the selected release when needed. Those commands may contact the configured Git or Marketplace source. Network transport and cache management performed by Codex or Git are governed by those tools and services.

After installation, the updater reads the new local Plugin manifest, reconciles only the five Plugin-owned managed Agent profiles through the newly installed package, rechecks installed Plugin identity, and runs the newly installed Doctor for local post-write validation. It does not upload those validation results to the maintainer.

The updater does not edit Hook trust state, credentials, unrelated Plugin registrations, unrelated Marketplaces, unrelated Agent profiles, or project repositories to make an update pass. If installed identity or post-write verification does not converge, the operation reports failure instead of silently rewriting unrelated state.

## Temporary orchestration state

For an Orchestrate execution or control flow, the Plugin may write one bounded `active.json` state file below the operating system's temporary directory:

```text
<OS temporary directory>/subagents-dispatch/<root-session-id>/active.json
```

Current V4 state is scoped to one root session and contains bounded WorkUnit, ExecutionBinding, WriterLease, PendingControl, responsibility-context, and accounting-reference data. It does not store raw prompts, transcripts, private reasoning, credentials, complete source files, or full tool output. The state file and lock are local and are not transmitted to the maintainer.

Legacy V3.x capsules may remain locally for compatibility diagnosis and explicit migration or cleanup. Unresolved, corrupt, or ambiguous legacy state is not silently rewritten into V4 execution. Doctor can diagnose such state and only performs cleanup or migration through the documented explicit and ownership-checked paths.

Normal terminal completion can remove safe thread state. Stale or unresolved writer state is preserved when deleting it could erase ownership evidence.

## Local runtime attestation

Ordinary Orchestrate operation and static Doctor diagnosis do not scan Codex session rollouts. When a user explicitly requests live route verification, or when release validation requires runtime route evidence, the bundled runtime inspector may inspect the exact local Codex child rollout if public Host metadata does not expose all required facts.

The inspector searches for the rollout bound to the requested child identity and parses only allowlisted routing, identity, permission, and runtime-version metadata from `session_meta` and `turn_context`. It does not emit prompts, assistant output, tool payloads, reasoning, source contents, or rollout paths.

The extracted metadata remains local to the Doctor, runtime-evidence, or release-validation workflow. subagents-dispatch does not upload the rollout or extracted metadata to the maintainer and does not create a separate transcript archive.

## Release evidence

V4 publication uses a dedicated candidate-bound release verifier. The authoritative Host campaign and Final Review evidence are expected to live outside the candidate repository and are supplied by the release operator. The verifier reads those files locally, verifies their candidate identity and required evidence fields, and does not upload them to a project-operated service.

Doctor is a product-health diagnostic. It does not grant publication authority and does not convert missing Host evidence into a release pass.

## Recipients and retention

The project maintainer does not receive user data through the Plugin. Data may be processed by OpenAI Codex, Git hosting, or user-enabled tools only as part of capabilities the user chooses to run and according to those services' own settings and policies.

The project retains no user data collected through the Plugin. Managed local configuration remains on the user's device until updated or removed by the user or an authorized Plugin lifecycle action. Temporary orchestration state follows the local cleanup rules above. Source Codex rollouts remain part of the user's local Codex session data and follow Codex's own retention behavior.

## User controls

Users can disable or uninstall subagents-dispatch and remove the Plugin's managed local configuration. Update checks, updates, repair, migration, broader configuration changes, and resolution of conflicting or unowned state remain explicit user-controlled actions. Live route verification is explicit when it requires rollout inspection. Hook enablement and trust remain Host or user controls.

Because the project does not operate a user account or remote data store, there is no project-held personal-data account to delete.

## Security and privacy reports

Use the repository's GitHub security reporting channel for security-sensitive reports. Other privacy questions can be raised through the repository's GitHub issue tracker.
