# Release Checklist

Use this checklist for a formal subagents-dispatch release candidate. Static repository checks and real Codex Host checks are separate gates; neither substitutes for the other.

## 1. Candidate identity

Before validation, record:

```text
version
candidate commit SHA
Codex App / CLI version used for Host smoke
operating system used for Host smoke
```

The version in `.codex-plugin/plugin.json` must match the public README badges, `README_AI.md`, and the newest `CHANGELOG.md` entry.

For a formal versioned release, `.agents/plugins/marketplace.json` must bind the Plugin Git source to the matching immutable semantic-version tag (`v<version>`), not to a mutable branch such as `main`.

Do not create a release tag until the exact candidate commit has passed every pre-tag gate below.

## 2. Repository gates

The exact candidate must pass the canonical GitHub Actions workflow on all configured platforms:

```text
Ubuntu / Python 3.11
Ubuntu / Python 3.12
macOS / Python 3.11
Windows / Python 3.11
```

Required repository checks are:

```text
plugin and marketplace JSON validation
pinned official OpenAI Plugin validator
Ruff Python lint
full pytest suite
managed Agent install
installer --check
Doctor --check
idempotent reinstall
```

A green branch run does not replace the pull-request merge-result run. A green pull-request run does not replace the final `main` push run for the merged candidate.

## 3. Real Codex Host gates

Run these against the same candidate that will be tagged.

### Plugin and Skill discovery

After installing the Plugin, open a fresh Codex task/session and confirm the Skill registry contains:

```text
Dispatch -> explicit invocation $dispatch
Doctor   -> explicit invocation $doctor
```

When the Host exposes source/path metadata, confirm both Skills come from the installed `subagents-dispatch@subagents-dispatch` payload for the candidate version. `/skills` may be used to open the Skill picker.

Bare `/dispatch` and `/doctor` slash commands are not a Skill-discovery requirement and must not be advertised as the supported Plugin entrypoint.

Confirm one harmless explicit `$dispatch` request and one read-only `$doctor` request are accepted. Unrelated ordinary tasks must not implicitly invoke subagents-dispatch.

### First-use readiness

Start from a clean state where the five managed subagents-dispatch Agent profiles are absent. Run a real `$dispatch` task that genuinely needs delegation and confirm:

```text
clean absence -> bounded automatic provisioning
installer --check passes
RESTART_REQUIRED is returned
0 child spawns occur before restart
no extra routine provisioning confirmation is requested
no unrelated Codex state is modified
```

### Fresh-task role discovery and spawn context

Open one fresh Codex task/session and rerun the same `$dispatch` request. Confirm the exact required custom Agent role is available before spawning.

At minimum, prove real Host spawn for:

```text
subagents_dispatch_reader
subagents_dispatch_worker
```

For each new project child, inspect the first actual `spawn_agent` call and confirm:

```text
exact required agent_type
fork_turns is present
fork_turns = none
0 full-history (`all`) custom-role spawn calls
0 omitted-fork_turns project-child spawn calls
```

A Host/tool rejection before any child identity is returned is a pre-attempt spawn rejection. It must not consume the two-attempt Agent recovery budget and must not increment the execution receipt retry count. If a corrected first valid child then succeeds, the receipt still reports `no retry` / `未重试` unless a materialized Agent attempt was actually retried.

If configured/requested model information is available but observed runtime model identity is not, record the observation as unavailable rather than inferring it from TOML.

### Parallel read-only work

Run two genuinely independent read-only responsibilities. Confirm unit identity remains distinct, returned evidence is not mixed, and no writer is started accidentally.

### Status and steering

While a child is active, confirm `$dispatch status` is a one-shot observation and preserves `UNKNOWN` when the Host cannot establish state.

Confirm `$dispatch steer` keeps the same responsibility, attempt, role, and authority. If the Host lacks live steering, report the limitation instead of simulating a replacement or retry.

### Takeover and writer safety

While a writing child is active, use `$dispatch takeover <unit_id>`. Main must remain read-only until Host evidence establishes that the old writer is stopped, terminal, or closed. `UNKNOWN` does not authorize a conflicting write.

### Doctor safety

Use `$doctor` to exercise exact, modified-managed, and unowned/conflicting profile states. Modified or unowned state must fail closed and must not overwrite unrelated files.

### Update and uninstall

Run the documented update flow, open a fresh task, and confirm the exact managed profiles and at least one custom Agent spawn still work.

Run the documented uninstall flow and confirm unrelated Agent profiles and Codex configuration remain untouched.

## 4. Hard release blockers

Do not release if any of these are observed on the supported Host candidate:

```text
installed/enabled Plugin does not register Dispatch or Doctor in a fresh-session Skill registry
$dispatch or $doctor cannot be explicitly invoked on the supported Host
fresh task cannot resolve the exact required custom Agent role
Luna Reader or Worker cannot be spawned on the supported Host
first-use stale task attempts a child spawn after provisioning
normal project-child spawn uses fork_turns other than none or omits fork_turns
pre-child spawn rejection is counted as an Agent retry or receipt retry
UNKNOWN is treated as FAILED
Main writes before a previous writer is proven settled during takeover
modified or unowned Agent configuration is overwritten automatically
subagents-dispatch implicitly activates on unrelated ordinary tasks
public docs or Plugin metadata advertise unsupported bare /dispatch, /doctor, or legacy namespaced slash identities as the entrypoint
```

Keep Codex Host limitations separate from project defects in the validation report.

## 5. Repository governance before tagging

Before the formal tag, verify repository settings outside the codebase:

```text
main requires pull requests
canonical policy-tests is a required check
required branch is up to date before merge
force pushes to main are disabled
```

These settings are repository administration state and cannot be proven by the project test suite alone.

## 6. Tag, distribution smoke, and GitHub Release

Only after the exact merged candidate passes repository, Host, governance, and immutable Marketplace-source gates:

1. confirm `main` still points to the validated candidate SHA;
2. create the immutable semantic-version tag, for example `v2.1.2`, on that exact SHA;
3. from a clean Codex environment, add the Marketplace from that exact tag and install the Plugin; confirm the installed Plugin reports the same version;
4. open a fresh task/session and confirm **Dispatch** and **Doctor** are present in the Skill registry, `$dispatch` and `$doctor` are accepted, and both resolve to the installed tagged Plugin payload;
5. confirm the Marketplace entry at the tag resolves the Plugin source from the same tag rather than a mutable branch;
6. confirm an ordinary task does not implicitly activate subagents-dispatch;
7. only after that distribution smoke passes, create the GitHub Release from the tag using the matching Changelog entry;
8. do not move or recreate the release tag if `main` advances later.

The post-tag distribution smoke is intentionally narrow. It verifies release packaging/identity and Skill discovery; it does not repeat the full Host behavior suite already completed on the exact candidate.

## 7. Public Plugin submission

If publishing through the OpenAI Plugin directory, separately verify the current submission portal requirements, developer identity/permissions, listing assets, test cases, availability, privacy/terms links, and release notes. These are external platform gates and are not closed by repository CI.
