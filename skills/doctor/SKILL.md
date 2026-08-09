---
name: subagents-doctor
description: Diagnose subagents-dispatch Plugin, Skill, managed-Agent, dispatch-state, Codex Host, Marketplace, and runtime-route health; mutate only when the user explicitly requests a supported repair, cleanup, migration, or upgrade.
---

# Subagents Doctor

Use this Skill for subagents-dispatch health, installation, configuration, Marketplace, managed-Agent profiles, ephemeral dispatch state, Host capability, runtime-route evidence, legacy migration, repair, and upgrade work. Development routing remains owned by the Subagents Dispatch orchestration kernel.

The current stable Skill identity is `subagents-doctor`. Do not infer or hard-code a user-visible Codex App slash-command string from package metadata alone. App rendering and selection are release-gated with direct human UI evidence.

Diagnosis is read-only by default. Do not mutate Plugin, Marketplace, Codex configuration, Agent profile state, dispatch state, repositories, or unrelated files unless the user explicitly asks for a supported mutation.

## Diagnostic model

Doctor reports six independent health layers:

```text
Plugin
Skills
Managed Agent profiles
Dispatch state
Codex Host
Runtime route evidence
```

Use only these report states when supported by evidence:

```text
OK
WARN
FAIL
UNKNOWN
```

Keep configuration truth separate from runtime observation. A correct TOML model or effort value proves configured intent only. It does not prove the route a live child actually ran.

## Canonical sources

Use one owner for each diagnostic fact:

```text
.codex-plugin/plugin.json
-> Plugin identity, version, package metadata

policy-contract.json
-> exact project roles, model/effort/sandbox intent, hard product constants

scripts/install-agents.py --check
-> canonical managed-profile verification

scripts/dispatch_state.py
-> ephemeral state inspection / cleanup after that helper exists

scripts/runtime-evidence.py
-> requested / accepted / observed runtime-route normalization

Codex CLI / native Host evidence
-> installed Plugin state, custom-role discovery, child lifecycle/control, runtime metadata
```

Do not implement a second profile validator, state parser, or route-matching algorithm inside this Skill when a deterministic owner already exists.

## 1. Plugin health

Collect the smallest available evidence set:

```bash
codex --version
codex doctor --json
codex plugin marketplace list --json
codex plugin list --available --json
```

If a Codex command is unavailable on the installed build, report that specific check as `UNKNOWN` and continue with independent checks.

Validate package-local identity from:

```text
skill_dir/../../.codex-plugin/plugin.json
skill_dir/../../policy-contract.json
```

Check version and Plugin identity consistency without claiming Marketplace freshness unless current Marketplace evidence was actually obtained.

## 2. Skill health

Inspect the installed package's user-facing Skill surface.

For each expected Skill definition, check:

```text
SKILL.md exists
frontmatter name is valid
agents/openai.yaml exists when required by package policy
display metadata is valid
policy.allow_implicit_invocation = false
```

Repository/package inspection can prove the installed Skill definitions. It cannot prove the exact labels or literal slash syntax rendered by the Codex App. Direct human App observation remains the source of truth for that UI gate.

Do not treat a missing future/optional Skill as an installed-runtime failure until the current package version contract says that Skill is required.

## 3. Managed Agent profile health

The managed-profile installer is:

```text
installer = skill_dir/../../scripts/install-agents.py
```

Run the canonical read-only checks:

```bash
python "$installer" --check
python "$installer" --legacy-status
```

`python "$installer" --check` is the canonical managed-profile verifier. Do not reimplement profile hashing, ownership, model, effort, or sandbox checks in Doctor prose.

Report configured role health separately from live route health. Example:

```text
[OK] Configured Reader route: Luna Max / read-only
[UNKNOWN] Live Reader route: not observed in this diagnostic run
```

### Legacy migration states

Interpret legacy state conservatively:

```text
legacy_only / mixed
-> automatic migration may be offered only when ownership evidence is valid

legacy_ownership_unknown
-> automatic migration is blocked; preserve files and report the ownership problem

current_with_preserved_legacy_modified
current_with_preserved_legacy
current_with_preserved_legacy_ownership_unknown
-> current profiles are installed and user-owned legacy state was intentionally preserved
-> do not loop on migration

migration_complete / current_only
-> no legacy cleanup is needed
```

## 4. Dispatch-state health

When the ephemeral dispatch-state helper is present, diagnose only plugin-owned temporary state.

Report:

```text
state root available / unavailable
current thread state: none | healthy | corrupt | unsafe | unknown
active orchestration: yes | no | unknown
stale capsule count
state lock health
schema health
```

The state root belongs under the operating-system temporary directory. Repository-local TeamPlan/ledger accumulation is a warning when it is being used as ordinary runtime state.

Doctor diagnosis does not automatically delete an active, corrupt, ambiguous, or stale capsule. Cleanup requires explicit user intent and may remove only subagents-dispatch-owned state proven safe to discard.

If state claims an active writer and native Host evidence is unavailable, do not declare the state safe to delete merely because it is old.

## 5. Codex Host capability health

Characterize the current Host only from capabilities actually exposed by that build. Useful checks include:

```text
custom project role discovery
spawn support with exact agent_type
fork_turns control
one-shot child status observation
live steering, when exposed
stop / close control, when exposed
thread identity, when exposed
runtime model / reasoning metadata, when exposed
```

A missing Host surface is `UNKNOWN` or a supported limitation, depending on evidence. Do not simulate an unavailable control with a background process or private scheduler.

## 6. Runtime route integrity

A normal Doctor run does not automatically spawn five Agents. Live route verification consumes real Host work and must be explicitly requested when it would create child execution.

When the user explicitly requests the live route check, verify all five managed project lanes with fresh controlled children:

```text
subagents_dispatch_reader
-> gpt-5.6-luna / max / read-only

subagents_dispatch_worker
-> gpt-5.6-luna / max / workspace-write

subagents_dispatch_solver
-> gpt-5.6-sol / high / workspace-write

subagents_dispatch_investigator
-> gpt-5.6-terra / xhigh / read-only

subagents_dispatch_advisor
-> gpt-5.6-sol / high / read-only
```

For every controlled project child:

```text
use the exact project agent_type
require fork_turns = none
capture inspectable child identity
collect the strongest native route / ancestry / permission evidence exposed by the Host
normalize with scripts/runtime-evidence.py
```

A formal live-route PASS requires the runtime evidence level demanded by the check. If the Host does not expose model or effort identity, report `UNKNOWN` / `not observed`; never upgrade configuration intent into observed runtime proof.

Any observed route mismatch is `FAIL` and the affected route claim is quarantined until resolved.

## Repair managed Agent profiles

Only with explicit repair/install intent:

```bash
python "$installer"
python "$installer" --check
```

Do not copy managed TOML files manually. If the current Codex session still cannot discover a required custom Agent role after a successful repair, ask the user to start a fresh Codex session.

## Cleanup ephemeral dispatch state

Only with explicit cleanup intent and only after the deterministic state helper proves ownership and safety:

```text
current active state
-> preserve unless the user explicitly abandons it and native ownership is safely settled

stale state with no active native owner
-> may be removed

corrupt / identity-conflicted / writer-ambiguous state
-> fail closed and report exact remediation instead of guessing
```

Doctor is not a garbage-collection daemon.

## Install Plugin

Only when installation is requested and the Plugin is not already installed:

```bash
codex plugin marketplace add R-jed/subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

Then start a fresh Codex session and invoke the installed Doctor again against the installed package.

## Upgrade Plugin

Report current and available-version evidence before mutation. With explicit upgrade intent:

```bash
codex plugin marketplace upgrade subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

After upgrade, start a fresh Codex session and invoke the new Doctor again. The new package must run its own installer, state, and compatibility diagnostics before any repair so an older running package cannot write newer managed state.

## Report

Prefer a compact layered report such as:

```text
[OK] Plugin
[OK] Skills
[OK] Managed Agent profiles
[OK] Dispatch state
[WARN] Host live steering unavailable on this build
[UNKNOWN] Live route integrity not run
```

A healthy current installation with intentionally preserved legacy user state is `OK` for current managed profiles plus `WARN` for preserved legacy state.

If every required layer is healthy, stop. Do not mutate a healthy installation.