# Privacy Policy

Last updated: 2026-08-22

subagents-dispatch is a local Codex Plugin built around two explicit Skills, Codex Native Subagents and bundled local helper scripts. The project does not operate a developer-controlled server, analytics service, account system, advertising system, telemetry endpoint or remote orchestration service.

## Data collected by the project

The project does not collect, transmit to the maintainer, sell or retain personal data, conversation content, repository content, credentials or usage telemetry through the Plugin.

The Plugin runs inside the user's Codex environment and may work with files, repositories, tools and context the user has made available to Codex. Data handling by Codex or user-enabled third-party tools is governed by those services and workspace settings.

## Managed local configuration

When an explicit Orchestrate task needs delegation and the five managed custom-Agent profiles are safely absent, subagents-dispatch may provision only:

```text
five fixed managed Agent TOML profiles
Plugin ownership manifest
installer lock
```

It does not modify credentials, MCP configuration, repositories, unrelated Agent profiles or unrelated Codex configuration as part of routine provisioning. Unsafe or unowned conflicts are preserved and reported.

The managed profiles contain Plugin configuration. They do not contain conversation transcripts, repository contents or project-operated credentials.

## Native lifecycle and orchestration state

V4.0.0 uses Codex Native Subagent lifecycle results and bounded local orchestration state.

For an active Orchestrate execution or control flow, the Plugin may write one bounded `active.json` file below the operating system temporary directory:

```text
<OS temporary directory>/subagents-dispatch/<root-session-id>/active.json
```

Current state contains bounded WorkUnit, ExecutionBinding, WriterLease, responsibility-context and accounting-reference metadata. It does not store raw prompts, child transcripts, private reasoning, credentials, complete source files or arbitrary Host output.

Ambiguous Host lifecycle truth is represented as `UNKNOWN` rather than being converted into permission to retry, replace or transfer a writer.

Legacy V3 capsules may remain locally for compatibility diagnosis and explicit ownership-checked migration or cleanup. They are never silently rewritten into active V4 execution state.

## Doctor

Normal Doctor diagnosis is local, read-only and offline. It verifies the Plugin package, managed profiles, optional caller-supplied Host capability evidence, current orchestration state and legacy compatibility.

Doctor does not scan unrelated Codex sessions, upload reports, run background monitoring or grant release authority. Maintenance actions require explicit user intent and remain limited to ownership-safe managed-profile or legacy-state operations.

## Update check and update

When the user explicitly requests an update check, the bundled helper may ask Codex to refresh the configured canonical subagents-dispatch Marketplace and reread local Plugin inventory. This may contact the configured Git/Marketplace source through Codex. It does not install a Plugin or mutate managed profiles.

When the user explicitly requests an update, the updater may refresh that Marketplace and install a selected stable release through supported Codex Plugin lifecycle commands. After installation it verifies the new local package, reconciles only Plugin-owned managed profiles and runs the newly installed Doctor for local post-write validation.

Update operations do not upload local validation results to the maintainer and do not modify unrelated Plugin registrations, Marketplaces, credentials or repositories.

## Optional runtime attestation

Ordinary Orchestrate and normal Doctor diagnosis do not inspect Codex rollout transcripts.

When a user explicitly requests live route verification, or release validation requires facts not exposed by public Host metadata, bundled inspectors may inspect the exact local child rollout bound to a requested child identity. They emit only allowlisted identity/routing/permission/runtime metadata defined by `docs/runtime-attestation.md`.

They do not emit prompts, assistant output, tool payloads, private reasoning, source contents or rollout paths. Extracted metadata remains local unless the user independently chooses to move it elsewhere.

## Release evidence

V4 publication uses candidate-bound external Host and Final Review evidence supplied by the release operator. The local verifier reads that evidence, checks candidate binding and required fields, and does not upload it to a project-operated service.

## Recipients and retention

The project maintainer does not receive user data through the Plugin. Local managed configuration remains until updated or removed by an authorized local action. Temporary orchestration state follows local cleanup rules. Source Codex session data follows Codex retention behavior.

## User controls

Users can disable or uninstall subagents-dispatch and remove Plugin-owned managed configuration through the documented ownership-safe flow. Update checks, updates, repair, migration, cleanup and rollout inspection remain explicit user-controlled actions.

Because the project operates no user account or remote data store, there is no project-held personal-data account to delete.

## Security and privacy reports

Use the repository's GitHub security reporting channel for security-sensitive reports. Other privacy questions may use the repository issue tracker.
