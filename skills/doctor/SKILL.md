---
name: doctor
description: Diagnose subagents-dispatch installation, Codex host and marketplace state, and managed Agent profiles; repair managed profiles or upgrade the Plugin only when the user explicitly asks for mutation.
---

# doctor

Use this Skill for subagents-dispatch installation, configuration, Marketplace, managed-profile, legacy-migration, repair, and upgrade work. Development routing remains owned by `/dispatch`.

Diagnosis is read-only by default. Do not mutate Plugin, Marketplace, Codex configuration, or Agent profile state unless the user explicitly asks to install, repair, migrate, or upgrade. Never edit Codex config files directly when the supported Codex CLI can perform the operation. Do not use `marketplace remove` as a generic reset.

## Canonical identities

```text
marketplace: subagents-dispatch
plugin:      subagents-dispatch@subagents-dispatch
main skill:  /dispatch (internal: /subagents-dispatch:dispatch)
doctor:      /doctor   (internal: /subagents-dispatch:doctor)
```

The managed-profile installer is:

```text
installer = skill_dir/../../scripts/install-agents.py
```

## Diagnose

Collect the smallest useful evidence set:

```bash
codex --version
codex doctor --json
codex plugin marketplace list --json
codex plugin list --available --json
python "$installer" --check
python "$installer" --legacy-status
```

If a Codex command is unavailable on the installed build, report that limitation as `UNKNOWN` and continue with the remaining checks. Preserve exact stderr for failures.

`python "$installer" --check` is the canonical managed-profile verifier. Do not implement a second profile validator in Doctor.

Use package-local files for package facts:

```text
skill_dir/../../.codex-plugin/plugin.json
skill_dir/../../policy-contract.json
```

## Legacy migration states

Interpret legacy state conservatively:

```text
legacy_only / mixed
  -> automatic migration may be offered only when ownership evidence is valid

legacy_ownership_unknown
  -> automatic migration is blocked; preserve the files and report the exact ownership problem

current_with_preserved_legacy_modified
current_with_preserved_legacy
current_with_preserved_legacy_ownership_unknown
  -> current profiles are installed and legacy user state was intentionally preserved
  -> do not loop on --migrate-legacy
  -> tell the user which files need explicit review

migration_complete / current_only
  -> no legacy cleanup is needed
```

When migration is authorized and ownership is valid:

```bash
python "$installer" --migrate-legacy
python "$installer" --check
python "$installer" --legacy-status
```

The installer acquires the legacy lock before the current lock, preserves the legacy lock file for cross-generation coordination, removes only hash-proven unchanged legacy files, detects snapshot drift, and rolls back both legacy cleanup and current installation when a transaction fails.

Modified or unowned legacy profiles are preserved together with the legacy manifest so ownership evidence is not discarded. A preserved terminal state is a warning requiring explicit review, not a reason to repeat migration indefinitely.

## Repair managed Agent profiles

Only with explicit repair/install intent:

```bash
python "$installer"
python "$installer" --check
```

Do not copy managed TOML files manually. If the current Codex session still cannot discover a required custom Agent role after a successful repair, ask the user to start a fresh Codex session.

## Install Plugin

Only when installation is requested and the Plugin is not already installed:

```bash
codex plugin marketplace add R-jed/subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

Then start a fresh Codex session and run `/doctor` again against the installed package.

## Upgrade Plugin

Report current and available-version evidence before mutation. With explicit upgrade intent:

```bash
codex plugin marketplace upgrade subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

After upgrade, start a fresh Codex session and invoke `/doctor` again. The new Doctor should run its own installer checks and legacy diagnostics before repairing profiles. This prevents an older running package from writing newer managed state.

## Report

Use `OK`, `WARN`, `FAIL`, and `UNKNOWN` only when supported by evidence. A healthy current installation with intentionally preserved legacy user state is `OK` for current managed profiles plus `WARN` for the preserved legacy state.

If everything required is healthy, stop. Do not mutate a healthy installation.
