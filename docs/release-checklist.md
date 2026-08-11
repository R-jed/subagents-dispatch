# Release Checklist

Use this checklist for a formal subagents-dispatch release candidate. Static repository checks, raw Host evidence, exact Host-produced rollout evidence, and direct human App UI observations are separate evidence classes; none may silently substitute for another.

## 1. Candidate identity

Before validation, record:

```text
version
candidate commit SHA
Codex App / CLI version used for Host smoke
operating system used for Host smoke
resolved Python helper invocation / sys.executable / version when bundled helpers are used
```

The version in `.codex-plugin/plugin.json` must match the public README badges, `README_AI.md`, and the newest `CHANGELOG.md` entry.

For a formal versioned release, `.agents/plugins/marketplace.json` must bind the Plugin Git source to the matching immutable semantic-version tag (`v<version>`), not to a mutable branch such as `main`.

Do not create a release tag until the exact candidate commit has passed every pre-tag gate below.

### Evidence ownership

Use the strongest evidence source available for each gate.

```text
Repository/API/CI evidence
-> version, SHA, tree contents, branch/ruleset state, CI, tag peel, Release state

Public Host runtime evidence
-> spawn/details metadata the Host actually reports for the exact child

Exact Host-produced rollout evidence
-> allowlisted child route/identity/permission metadata from scripts/inspect-agent-runtime.py

Raw Host/rollout evidence
-> public runtime metadata, exact inspected rollout metadata, spawn_agent arguments, child identity,
   lifecycle events, retry accounting, and implicit activation as applicable to the gate

Direct human Codex App observation
-> what appears in the `/` Skill menu, exact rendered entry names, visible namespace/prefix,
   duplicate/conflicting entries, post-selection presentation, and which Plugin/Skill is actually selected

Model self-report
-> explanatory only; it cannot by itself close a Host/UI gate or a runtime-route gate about the model's own registration, selection, model, or reasoning effort
```

For child runtime attestation, follow `docs/runtime-attestation.md`. Public Host metadata is preferred. If a required field is omitted and the exact child rollout is available, use the bundled inspector and place only its allowlisted output in the `local` runtime-evidence source. Configured profile values, accepted role values, manually copied JSON, and child prose cannot be substituted for Observed fields. Public and exact-rollout evidence must agree wherever both expose the same field. Effective permission-source evidence must also be bound to a concrete source identity plus source and source-selection provenance before it can close a formal permission gate.

The following App facts require direct human observation and cannot be delegated entirely to the Codex instance under test:

```text
all six Plugin Skills are visible in the App `/` menu
their exact user-visible names are namespaced and distinguishable from generic skills
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

For the current single-maintainer phase, use this integration workflow:

```text
short-lived feature branch
-> local full validation
-> adversarial/deep review
-> repair on the same branch
-> local full revalidation
-> direct merge to main
-> push main
-> GitHub Actions cross-platform confirmation
```

A pull request is optional. Do not invent a required PR merge-result gate when repository governance does not require one. Feature-branch CI is useful cross-platform evidence for the branch candidate; after direct integration, the final `main` push run confirms the merged candidate. GitHub Actions remains enabled even when it is not a pre-merge branch-protection requirement.

Before any local gate or real Host gate invokes a bundled Python helper, resolve one Python 3.11+ interpreter from the actual environment according to `docs/python-runtime.md`. Record the resolved invocation, `sys.executable`, and Python version and use that same interpreter for the operation. A missing command named `python` is not a failed prerequisite when another supported Python 3.11+ invocation is available. Interpreter command-name resolution is environment adaptation, not role/model/Agent/evidence substitution.

If no Python 3.11+ interpreter can be resolved, record `PYTHON_PREREQUISITE_UNMET` and stop before Host spawn. The Python-backed precondition fails; downstream Host acceptance, runtime route, inspector, and behavioral gates are `NOT TESTED` or `INVALIDATED` as appropriate. Do not report a Host role rejection or route mismatch when the helper never ran.

Deterministic local gate, after `<python-3.11+>` has been resolved:

```text
<python-3.11+> -m json.tool .codex-plugin/plugin.json
<python-3.11+> -m json.tool .agents/plugins/marketplace.json
<python-3.11+> -m ruff check scripts tests --ignore E402
<python-3.11+> -m pytest -q
create an isolated temporary CODEX_HOME
<python-3.11+> scripts/install-agents.py --codex-home <temporary-codex-home>
<python-3.11+> scripts/install-agents.py --codex-home <temporary-codex-home> --check
<python-3.11+> scripts/doctor.py --codex-home <temporary-codex-home> --check
<python-3.11+> scripts/install-agents.py --codex-home <temporary-codex-home>
<python-3.11+> scripts/install-agents.py --codex-home <temporary-codex-home> --check
```

`<python-3.11+>` is a protocol placeholder for the resolved interpreter invocation. It is not a literal command. The canonical GitHub Actions workflow may continue to use `python` after `actions/setup-python` has provisioned that command inside CI; that does not establish the command name available inside a real Codex task shell.

The official OpenAI Plugin validator is pinned by `.github/workflows/ci.yml`; run that exact pinned validator in the supported validation environment. Do not report App or Host smoke as passed until direct App observation and raw Host evidence are recorded.

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
Python 3.11+ helper prerequisite is resolved from the actual task environment
clean absence -> bounded automatic provisioning
installer --check passes
RESTART_REQUIRED is returned
0 child spawns occur before restart
no extra routine provisioning confirmation is requested
no unrelated Codex state is modified
```

### Fresh-task role discovery and spawn context

Open one fresh Codex task/session and rerun the same request through Dispatch. Confirm the exact required custom Agent role is available before spawning.

For the v3 formal Host route gate, prove controlled real Host spawn for all five exact project roles:

```text
subagents_dispatch_reader
subagents_dispatch_worker
subagents_dispatch_solver
subagents_dispatch_investigator
subagents_dispatch_advisor
```

Use one bounded smoke child per role with `fork_turns = none`, no broader behavioral authority than the route check requires, and settle every child before returning. For each role, keep these columns separate:

| Configured model | Configured reasoning | Behavioral authority | Observed model | Observed reasoning | Observed Host permission | Permission inheritance | Overall |
| --- | --- | --- | --- | --- | --- | --- | --- |
| policy value | policy value | none or assigned bounded-source-write | Host evidence | Host evidence | sandbox + permission profile | OK / UNKNOWN / FAIL | OK / UNKNOWN / FAIL |

Follow `docs/runtime-attestation.md` for every smoke child. Inspect public Host/spawn/details metadata first. If it omits a required field and the exact local Codex rollout exists, run with the same resolved interpreter:

```text
<python-3.11+> scripts/inspect-agent-runtime.py <child-thread-id> \
  --expected-parent-thread-id <root-thread-id> \
  --expected-agent-role <exact-agent-type>
```

Put public Host runtime fields in `native`, put only the inspector's allowlisted object in `local`, and record the effective parent-turn or selected-environment permission in `effective_permission_source`. Formal permission evidence must include `source_kind`, concrete `source_id`, sandbox, permission profile, `evidence_source`, `evidence_ref`, and `selection_evidence_ref`. For `parent_turn`, the source id must equal the exact root/parent thread id. For `selected_environment`, the source id must be a concrete Host-observed environment identity. Source-selection evidence must establish why that source was effective under the ordered `permission_semantics.sources` precedence. Set `runtime_observation_required=true` and `requires_permission_observation=true`, then normalize through `scripts/runtime-evidence.py`. Record the source for every Observed field as `native`, `local`, or `both`.

An accepted exact `agent_type` proves role acceptance only. It does not prove observed model, reasoning effort, or permission. An exact Host-produced rollout is actual runtime evidence, but only after the bundled inspector binds it to the exact child/parent/role and rejects ambiguous or drifting records. Missing runtime evidence or unbound permission-source provenance remains `UNKNOWN`; an observed mismatch is `FAIL`, including a route mismatch, child/inheritance-source permission mismatch, or bound parent-source identity mismatch; a public/local runtime conflict is also `FAIL`. Matching broad inherited permission is not a failure by itself, but behavioral read-only remains binding and hard isolation still requires `requires_enforced_read_only`. If hard isolation is required, Main may retain the responsibility only when Main itself is proven Host-enforced read-only; otherwise the responsibility remains blocked. Never copy configured values, accepted values, or child self-report into observed columns.

For Reader, Investigator, and Advisor, record a narrow workspace mutation baseline before the smoke responsibility and verify the project-file state is unchanged after the child settles. This verifies behavioral read-only compliance only; it is not Host sandbox evidence and cannot replace permission attestation.

For each new project child, inspect the first actual `spawn_agent` call and confirm:

```text
exact required agent_type
fork_turns is present
fork_turns = none
0 full-history (`all`) custom-role spawn calls
0 omitted-fork_turns project-child spawn calls
```

A Host/tool rejection before any child identity is returned is a pre-attempt spawn rejection. It must not consume the two-attempt Agent recovery budget and must not increment the Dispatch Receipt retry count. If a corrected first valid child then succeeds, the exceptional Recovery line remains absent because no materialized Agent attempt was retried.

If configured/requested model information is available but observed runtime model identity is not, record the observation as unavailable rather than inferring it from TOML.

### Parallel read-only work

Run two genuinely independent read-only responsibilities. Confirm unit identity remains distinct, returned evidence is not mixed, and no writer is started accidentally.

### Status and steering

Invoke Status through the human-verified App entry while a child is active. Confirm it is a one-shot observation and preserves `UNKNOWN` when the Host cannot establish state.

Use the Steer Skill with an exact unit id and guidance, then confirm steering keeps the same responsibility, attempt, role, authority, and native child. If the Host lacks live steering, report the limitation instead of simulating a replacement or retry.

### Takeover and writer safety

While a writing child is active, invoke the Takeover Skill for the exact unit. Main must remain read-only until Host evidence establishes that the old writer is stopped, terminal, or closed. `UNKNOWN` and `INTERRUPTED` do not authorize a conflicting write.

### Doctor safety

Through the human-verified Doctor App entry, exercise exact, modified-managed, and unowned/conflicting profile states. Modified or unowned state must fail closed and must not overwrite unrelated files. For a formal `--live-route --check`, omit one required formal flag and separately omit permission-source provenance; both cases must fail to produce a passing gate. Ordinary Doctor without explicit live-route evidence may still report Runtime route `UNKNOWN` while remaining healthy.

### Update and uninstall

Run the documented update flow, open a fresh task, and confirm the exact managed profiles and at least one custom Agent spawn still work.

Run the documented uninstall flow and confirm unrelated Agent profiles and Codex configuration remain untouched.

## 4. Hard release blockers

Do not release if any of these are observed on the supported Host candidate:

```text
Codex App `/` menu does not expose all six namespaced Plugin Skills
the App-visible entries are ambiguous with generic/unrelated skills
an App entry selects the wrong Plugin/Skill
fresh task cannot resolve the exact required custom Agent role
any of the five configured project roles cannot be spawned as its exact `agent_type` on the supported Host
first-use stale task attempts a child spawn after provisioning
normal project-child spawn uses fork_turns other than none or omits fork_turns
pre-child spawn rejection is counted as an Agent retry or receipt retry
For a release gate that explicitly requires observed evidence, `UNKNOWN` blocks that gate. Formal Doctor `--live-route --check` must not pass on `UNKNOWN`, missing formal flags, or unbound permission-source provenance. A normal Doctor run remains healthy when route evidence was not requested and therefore reports `UNKNOWN`; it must not be relabeled as a runtime pass.
Main writes before a previous writer is proven settled during takeover
modified or unowned Agent configuration is overwritten automatically
subagents-dispatch implicitly activates on unrelated ordinary tasks
```

`PYTHON_PREREQUISITE_UNMET` is an environment/precondition blocker for Python-backed validation or first-use provisioning. It invalidates the downstream gate that could not execute, but it is not evidence of Host role rejection, route mismatch, inspector regression, or permission failure.

Keep Codex Host limitations separate from project defects in the validation report.

## 5. Repository governance before tagging

Before a formal tag, inspect current repository administration state directly rather than assuming policy from documentation. At minimum verify that unsafe history rewriting is prevented for `main` and record any active deletion protection, pull-request requirement, or required status checks exactly as they are configured at that time.

For the current single-maintainer workflow, PR and pre-merge status-check requirements are optional. Code must not silently change repository protection settings.

## 6. Tag, distribution smoke, and GitHub Release

Only after the exact merged candidate passes repository, Host, human App UI, governance, and immutable Marketplace-source gates:

1. confirm `main` still points to the validated candidate SHA;
2. create the immutable semantic-version tag on that exact SHA;
3. from a clean environment, add the Marketplace from that exact tag and install the Plugin;
4. confirm the installed Plugin reports the same version and the Marketplace entry resolves the Plugin source from the same tag rather than a mutable branch;
5. fully restart the Codex App when required for registry refresh;
6. human-check the `/` menu again and confirm the same six namespaced Skill entries are present and select the expected tagged Plugin payload, recording the post-selection presentation rather than assuming a slash string;
7. use raw Host/rollout evidence for any behavior gate that cannot be established from UI alone;
8. only after that distribution smoke passes, create the GitHub Release from the tag using the matching Changelog entry;
9. do not move or recreate the release tag if `main` advances later.

The post-tag distribution smoke is intentionally narrow. It verifies immutable packaging/identity plus the human-visible App Skill entries and does not repeat the full Host behavior suite already completed on the exact candidate.

## 7. Public Plugin submission

If publishing through the OpenAI Plugin directory, separately verify the current submission portal requirements, developer identity/permissions, listing assets, test cases, availability, privacy/terms links, and release notes. These are external platform gates and are not closed by repository CI.
