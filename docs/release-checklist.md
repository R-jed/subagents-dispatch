# Release Checklist

Use this checklist for a formal subagents-dispatch release candidate. Static repository checks, raw Host evidence, and direct human App UI observations are separate evidence classes; none may silently substitute for another.

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

### Evidence ownership

Use the strongest evidence source available for each gate.

```text
Repository/API/CI evidence
-> version, SHA, tree contents, branch/ruleset state, CI, tag peel, Release state

Raw Host/rollout evidence
-> spawn_agent arguments, child identity, lifecycle events, retry accounting, implicit activation

Direct human Codex App observation
-> what appears in the `/` Skill menu, exact rendered entry names, visible namespace/prefix,
   duplicate/conflicting entries, post-selection presentation, and which Plugin/Skill is actually selected

Model self-report
-> explanatory only; it cannot by itself close a Host/UI gate about the model's own registration or selection
```

The following App facts require direct human observation and cannot be delegated entirely to the Codex instance under test:

```text
the two Plugin Skills are visible in the App `/` menu
their exact user-visible names contain a product-specific prefix and are distinguishable from generic skills
a generic conflicting entry such as an unrelated `doctor` is not mistaken for this Plugin's Doctor
selecting each entry binds to the expected subagents-dispatch Plugin Skill
the post-selection UI form is recorded, including whether the App shows a Skill chip, namespace, literal slash text, or another form
full App restart refreshes the visible registry when that behavior is material to the candidate
```

Record screenshots or equivalent direct UI notes for those gates. If the App does not render a literal slash-command string after selection, record that fact instead of inventing one. Raw Host evidence may supplement the UI observation by proving the selected Skill source/path, but the model's prose claim that it is registered is insufficient on its own.

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

This project is maintained by one maintainer. A short-lived branch and pull request are optional; a validated change may be updated directly on `main` when repository governance permits it. In either path, run the same local gates before updating `main`.

Deterministic local gate:

```bash
python -m json.tool .codex-plugin/plugin.json >/dev/null
python -m json.tool .agents/plugins/marketplace.json >/dev/null
python -m ruff check scripts tests --ignore E402
python -m pytest -q
tmp_home="$(mktemp -d)"
python scripts/install-agents.py --codex-home "$tmp_home"
python scripts/install-agents.py --codex-home "$tmp_home" --check
python scripts/doctor.py --codex-home "$tmp_home" --check
python scripts/install-agents.py --codex-home "$tmp_home"
```

The official OpenAI Plugin validator is pinned by `.github/workflows/ci.yml`; run that exact pinned validator in the Ubuntu validation environment. Do not report App or Host smoke as passed until direct App observation and raw Host evidence are recorded.

## 3. Real Codex Host gates

Run these against the same candidate that will be tagged.

### Plugin and App Skill discovery

Package identity must be:

```text
Plugin:        subagents-dispatch
Skill:         dispatch  -> intended label Dispatch
Skill:         preview   -> intended label Preview
Skill:         status    -> intended label Status
Skill:         steer     -> intended label Steer
Skill:         takeover  -> intended label Takeover
Skill:         doctor    -> intended label Doctor
```

Human App gate:

1. fully restart the Codex App when the candidate changes installed Skill metadata;
2. type `/` to open the App Skill menu;
3. confirm all six entries are visible;
4. record the exact rendered entry labels, any visible namespace, and the post-selection presentation;
5. confirm there is no ambiguity with unrelated Skills that use the same generic labels;
6. select each entry once and retain raw Host/rollout evidence when available to confirm it maps to the expected installed Plugin Skill.

Do not derive a literal App slash-command string from SKILL.md, `plugin.json`, folder names, another product's syntax, or model self-report. The App may render a display-name menu entry and then bind the selection as a Skill chip instead of leaving slash text in the composer. Direct UI observation is the source of truth for the user-facing selection flow.

Separately, run an unrelated ordinary task and use raw Host evidence to confirm subagents-dispatch does not implicitly activate.

### First-use readiness

Start from a clean state where the five managed subagents-dispatch Agent profiles are absent. Through the human-verified Dispatch App entry, run a real task that genuinely needs delegation and confirm:

```text
clean absence -> bounded automatic provisioning
installer --check passes
RESTART_REQUIRED is returned
0 child spawns occur before restart
no extra routine provisioning confirmation is requested
no unrelated Codex state is modified
```

### Fresh-task role discovery and spawn context

Open one fresh Codex task/session and rerun the same request through Dispatch. Confirm the exact required custom Agent role is available before spawning.

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

Invoke Status through the human-verified App entry while a child is active. Confirm it is a one-shot observation and preserves `UNKNOWN` when the Host cannot establish state.

Use the `steer <unit_id>: <guidance>` control payload and confirm steering keeps the same responsibility, attempt, role, and authority. If the Host lacks live steering, report the limitation instead of simulating a replacement or retry.

### Takeover and writer safety

While a writing child is active, invoke the `takeover <unit_id>` control payload. Main must remain read-only until Host evidence establishes that the old writer is stopped, terminal, or closed. `UNKNOWN` does not authorize a conflicting write.

### Doctor safety

Through the human-verified Doctor App entry, exercise exact, modified-managed, and unowned/conflicting profile states. Modified or unowned state must fail closed and must not overwrite unrelated files.

### Update and uninstall

Run the documented update flow, open a fresh task, and confirm the exact managed profiles and at least one custom Agent spawn still work.

Run the documented uninstall flow and confirm unrelated Agent profiles and Codex configuration remain untouched.

## 4. Hard release blockers

Do not release if any of these are observed on the supported Host candidate:

```text
Codex App `/` menu does not expose both prefixed Plugin Skills
the App-visible entries are ambiguous with generic/unrelated skills
an App entry selects the wrong Plugin/Skill
fresh task cannot resolve the exact required custom Agent role
Luna Reader or Worker cannot be spawned on the supported Host
first-use stale task attempts a child spawn after provisioning
normal project-child spawn uses fork_turns other than none or omits fork_turns
pre-child spawn rejection is counted as an Agent retry or receipt retry
For a release gate that explicitly requires observed evidence, `UNKNOWN` blocks that gate. A normal Doctor run remains healthy when route evidence was not requested and therefore reports `UNKNOWN`; it must not be relabeled as a runtime pass.
Main writes before a previous writer is proven settled during takeover
modified or unowned Agent configuration is overwritten automatically
subagents-dispatch implicitly activates on unrelated ordinary tasks
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

Only after the exact merged candidate passes repository, Host, human App UI, governance, and immutable Marketplace-source gates:

1. confirm `main` still points to the validated candidate SHA;
2. create the immutable semantic-version tag, for example `v2.1.2`, on that exact SHA;
3. from a clean environment, add the Marketplace from that exact tag and install the Plugin;
4. confirm the installed Plugin reports the same version and the Marketplace entry resolves the Plugin source from the same tag rather than a mutable branch;
5. fully restart the Codex App when required for registry refresh;
6. human-check the `/` menu again and confirm the same two prefixed Skill entries are present and select the expected tagged Plugin payload, recording the post-selection presentation rather than assuming a slash string;
7. use raw Host/rollout evidence for any behavior gate that cannot be established from UI alone;
8. only after that distribution smoke passes, create the GitHub Release from the tag using the matching Changelog entry;
9. do not move or recreate the release tag if `main` advances later.

The post-tag distribution smoke is intentionally narrow. It verifies immutable packaging/identity plus the human-visible App Skill entry and does not repeat the full Host behavior suite already completed on the exact candidate.

## 7. Public Plugin submission

If publishing through the OpenAI Plugin directory, separately verify the current submission portal requirements, developer identity/permissions, listing assets, test cases, availability, privacy/terms links, and release notes. These are external platform gates and are not closed by repository CI.
