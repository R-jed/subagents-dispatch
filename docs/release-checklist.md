# Release Checklist

Use this checklist for a formal subagents-dispatch release candidate. It covers the product that users install and run. Role-calibration campaigns and formal product-benchmark campaigns belong to the development/research Experiment Plane and do not gate v3.0.0 unless a public release claim explicitly depends on their result.

The rule for adding a hard release gate is simple:

```text
hard release gate
-> must protect one concrete public capability, safety property, distribution property, or release claim
```

If a proposed gate cannot name that protected claim, keep it out of the release path.

The v3.0.0 release path includes repository/package integrity, managed Agent profile lifecycle, Codex App Skill discovery, first-use provisioning, five production Agent routes, runtime attestation required by release claims, Preview / Dispatch / Status / Steer / Takeover behavior, single-writer takeover safety, Doctor safety, update/uninstall safety, and immutable tagged Marketplace distribution.

The following remain valid development/research capabilities but are not v3.0.0 hard release blockers:

```text
role calibration
formal model/effort comparison campaigns
formal single-agent versus Dispatch product benchmark campaigns
calibration profile materialization
experiment campaign/run provenance
performance claims that are not published in the release
```

Runtime attestation remains part of the release path where the release claims what actually ran. Configured values, Host acceptance, and observed runtime facts stay separate. A small real-task product canary may be run before release to catch obvious correctness, safety, scope, writer, or correction-burden regressions. It does not require the formal Experiment Plane unless its result will support a published performance claim.

## 1. Candidate identity

Before validation, record:

```text
version
candidate commit SHA
Codex App / CLI version used for Host smoke
operating system used for Host smoke
resolved Python helper invocation
sys.executable
Python version
```

The version in `.codex-plugin/plugin.json` must match the public README badges, `README_AI.md`, and newest `CHANGELOG.md` entry.

For a formal versioned release, `.agents/plugins/marketplace.json` must bind the Plugin Git source to the matching immutable semantic-version tag (`v<version>`), not a mutable branch such as `main`.

Do not create a release tag until the exact candidate commit has passed every applicable pre-tag product gate below.

### Evidence ownership

Use the strongest evidence source available for each claim.

```text
Repository/API/CI evidence
-> version, SHA, tree contents, branch/ruleset state, CI, tag peel, Release state

Public Host runtime evidence
-> spawn/details metadata the Host actually reports for the exact child

Exact Host-produced rollout evidence
-> allowlisted child route/identity/permission metadata from scripts/inspect-agent-runtime.py

Raw Host/rollout evidence
-> public runtime metadata, exact inspected rollout metadata, spawn_agent arguments,
   child identity, lifecycle events, retry accounting, implicit activation

Direct human Codex App observation
-> what appears in the `/` Skill menu, exact rendered entry names, namespace/prefix,
   duplicate/conflicting entries, post-selection presentation, selected Plugin/Skill

Model self-report
-> explanatory only; it cannot by itself close a Host/UI gate or prove the model's own runtime route
```

For child runtime attestation, follow `docs/runtime-attestation.md`. Public Host metadata is preferred. If a required field is omitted and the exact child rollout is available, use the bundled inspector and place only its allowlisted output in the local runtime-evidence source.

Configured profile values, accepted role values, manually copied JSON, and child prose cannot be substituted for Observed fields. Public and exact-rollout evidence must agree wherever both expose the same field. Route, effective permission state, and permission-source provenance close separate claims. Provenance is required only when the release claim names source identity or Host selection.

The following App facts require direct human observation:

```text
all six Plugin Skills are visible in the App `/` menu
their exact user-visible names are namespaced and distinguishable from generic skills
an unrelated generic entry such as `doctor` is not mistaken for this Plugin's Doctor
selecting each entry binds to the expected subagents-dispatch Plugin Skill
the post-selection UI form is recorded
full App restart refreshes the visible registry when Skill metadata changed
```

Record screenshots or equivalent direct UI notes. During the Human App gate, record the exact rendered entry labels, visible namespace, and post-selection presentation. Do not invent literal slash-command syntax when the App presents a Skill chip or another selection form.

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
ownership-aware managed Agent uninstall
post-uninstall installer --check fails as Not installed
reinstall after uninstall
final installer --check
tag/version parity when the workflow runs from a release tag
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

A pull request is optional. Feature-branch CI is useful cross-platform evidence for the branch candidate; after direct integration, the final `main` push run confirms the merged candidate.

Before a local or real-Host gate invokes a bundled Python helper, resolve one Python 3.11+ interpreter from the actual environment according to `docs/python-runtime.md`. Record the resolved invocation, `sys.executable`, and Python version and keep that interpreter fixed for the operation.

A missing command named `python` is not a failed prerequisite when another supported Python 3.11+ invocation is available. Interpreter command-name resolution is environment adaptation, not role/model/Agent/evidence substitution.

If no Python 3.11+ interpreter can be resolved, record `PYTHON_PREREQUISITE_UNMET` and stop before a Python-backed Host spawn or inspection gate. The downstream Host acceptance, runtime route, inspector, and behavioral gates are `NOT TESTED` or `INVALIDATED` as appropriate. Do not relabel that prerequisite failure as a Host role rejection or route mismatch.

Deterministic local gate after `<python-3.11+>` has been resolved:

```text
<python-3.11+> -m json.tool .codex-plugin/plugin.json
<python-3.11+> -m json.tool .agents/plugins/marketplace.json
<python-3.11+> -m ruff check scripts tests --ignore E402
<python-3.11+> -m pytest -q
<python-3.11+> scripts/install-agents.py --codex-home <isolated-test-home>
<python-3.11+> scripts/install-agents.py --codex-home <isolated-test-home> --check
<python-3.11+> scripts/doctor.py --codex-home <isolated-test-home> --check --thread-id release-doctor
<python-3.11+> scripts/install-agents.py --codex-home <isolated-test-home>
<python-3.11+> scripts/install-agents.py --codex-home <isolated-test-home> --check
<python-3.11+> scripts/uninstall-agents.py --codex-home <isolated-test-home>
<python-3.11+> scripts/install-agents.py --codex-home <isolated-test-home> --check   # expected non-zero: Not installed
<python-3.11+> scripts/install-agents.py --codex-home <isolated-test-home>
<python-3.11+> scripts/install-agents.py --codex-home <isolated-test-home> --check
```

The expected post-uninstall `--check` failure is part of the lifecycle assertion; it must not be treated as an overall gate failure when it reports the clean `Not installed` state. This deterministic repository gate does not materialize calibration profiles, mutate the user's normal Codex home, or run a formal experiment campaign.

The official OpenAI Plugin validator is pinned by `.github/workflows/ci.yml`; use that exact pin for the release candidate. On a tag push, the same workflow also requires the tag name to equal `v<plugin version>` before the tagged source can pass.

## 3. Real Codex Host gates

Run these checks against the same candidate that will be tagged.

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
5. confirm there is no ambiguity with unrelated Skills using generic labels;
6. select each entry once and retain raw Host/rollout evidence when available to confirm the expected installed Plugin Skill was selected.

Separately run an unrelated ordinary task and use raw Host evidence to confirm subagents-dispatch does not implicitly activate.

### First-use readiness

Start from a clean state where the five managed subagents-dispatch Agent profiles are absent. Through the human-verified Dispatch App entry, run a real task that genuinely needs delegation and confirm:

```text
Python 3.11+ helper prerequisite resolves from the actual task environment
clean absence -> bounded automatic provisioning
installer --check passes
RESTART_REQUIRED is returned
0 child spawns occur before restart
no extra routine provisioning confirmation is requested
no unrelated Codex state is modified
```

Open a fresh task after provisioning before testing project-child discovery.

### Five production routes

For the v3 formal Host route gate, prove controlled real Host spawn for all five exact production roles:

```text
subagents_dispatch_reader
subagents_dispatch_worker
subagents_dispatch_solver
subagents_dispatch_investigator
subagents_dispatch_advisor
```

Use one bounded smoke child per role with `fork_turns = none`, no broader behavioral authority than the route check requires, and settle every child before returning.

For each role record separately:

| Configured model | Configured reasoning | Behavioral authority | Runtime route | Effective permission state | Permission provenance |
| --- | --- | --- | --- | --- | --- |
| policy value | policy value | none or assigned bounded-source-write | VERIFIED / UNKNOWN / FAIL | VERIFIED / UNKNOWN / FAIL | VERIFIED / UNKNOWN / FAIL |

Follow `docs/runtime-attestation.md`. Inspect public Host/spawn/details metadata first. If a required runtime field is omitted and the exact local child rollout exists, run:

```text
<python-3.11+> scripts/inspect-agent-runtime.py <child-thread-id> \
  --expected-parent-thread-id <root-thread-id> \
  --expected-agent-role <exact-agent-type>
```

Place public Host runtime fields in `native`, only the inspector's allowlisted object in `local`, and normalize through `scripts/runtime-evidence.py`.

An accepted exact `agent_type` proves role acceptance only. It does not prove observed model, reasoning effort, or permission. Missing source provenance makes only that dimension `UNKNOWN`. Observed mismatches and public/local conflicts fail closed.

If the release does not claim Host permission-source identity or selection, permission provenance may remain `UNKNOWN` while verified route and effective permission state remain independently usable evidence.

For Reader, Investigator, and Advisor, record a narrow project-file mutation baseline before the smoke responsibility and confirm that project-file state is unchanged after the child settles. This proves behavioral read-only compliance only; it does not substitute for Host sandbox evidence.

For every new project child confirm:

```text
exact required agent_type
fork_turns is present
fork_turns = none
0 full-history (`all`) custom-role spawn calls
0 omitted-fork_turns project-child spawn calls
```

A Host/tool rejection before any child identity is returned is a pre-attempt spawn rejection. It must not consume an Agent retry or Dispatch Receipt retry count.

### Control Surface integrated scenario

Run one real orchestration that exercises the public control surface:

```text
Preview
-> predicts without child spawn or active-state creation

Dispatch
-> creates only responsibilities that add distinct value

Status
-> performs one observation and preserves UNKNOWN when current Host truth is unavailable

Steer
-> keeps the same unit, task, attempt, role, authority, and native child

Takeover
-> does not release a writing responsibility until Host evidence settles the old writer

Completion
-> verifies the actual result and emits the applicable Dispatch Receipt
```

If live steering is unavailable on the supported Host, report the limitation instead of simulating a replacement child.

During writer takeover, Main remains read-only until the previous writer is proven stopped, terminal, or closed. `RUNNING`, `INTERRUPTED`, and `UNKNOWN` do not authorize conflicting mutation.

### Doctor safety

Through the human-verified Doctor App entry, exercise exact, modified-managed, and unowned/conflicting profile states. Modified or unowned state must fail closed and must not overwrite unrelated files.

Run static Doctor without spawning Agents. Separately run explicit live-route Doctor once when release route evidence is required. Route, effective permission state, and provenance remain separate assurance dimensions. Do not require provenance for a release claim that does not name permission-source identity or Host selection.

### Update and uninstall

Run the documented update flow, open a fresh task, and confirm the exact managed profiles and at least one custom Agent spawn still work.

For uninstall, keep the Plugin installed while the managed profiles are removed. Through the human-verified Doctor entry, explicitly request managed-profile uninstall and require the bundled ownership-aware helper to remove only profiles still proven by the existing ownership manifest. Exercise exact-owned, already-missing-owned, modified-owned, and unowned/conflicting cases. Modified or unowned state must fail closed without deleting other Agent configuration. Only after managed-profile cleanup succeeds should the Plugin registration and Marketplace source be removed.

Confirm config.toml, credentials, unrelated Agent profiles, repositories, and other Plugin-unrelated Codex state remain untouched throughout uninstall.

### Optional real-task product canary

Before final documentation freeze, run a small paired canary on real repository tasks when practical:

```text
ordinary single-agent baseline
vs
explicit Dispatch
```

Use independently reset workspaces and the same task, Main route, tools, permissions, project rules, and acceptance oracle. Treat material correctness, safety, authority, scope, writer, or correction-burden regression as a release concern.

Do not turn this canary into a performance claim. Formal repeat counts, exact telemetry, statistical summaries, route calibration, and public superiority claims belong to `docs/experiment-protocol.md`.

## 4. Hard release blockers

Do not release if any of these are observed on the supported candidate:

```text
repository CI or required package validation fails
Codex App `/` menu does not expose all six namespaced Plugin Skills
an App-visible entry is ambiguous with an unrelated Skill or selects the wrong Plugin/Skill
fresh task cannot resolve the exact required custom Agent role
any of the five configured production roles cannot be spawned as its exact agent_type
first-use stale task attempts a child spawn after provisioning
normal project-child spawn uses fork_turns other than none or omits fork_turns
pre-child spawn rejection is counted as an Agent retry or Receipt retry
required runtime route evidence is UNKNOWN or mismatched for a claim that depends on it
required effective permission-state evidence is UNKNOWN or mismatched for a claim that depends on it
Main writes before a previous writer is proven settled during takeover
modified or unowned Agent configuration is overwritten automatically
managed-profile uninstall deletes a modified, unowned, symlinked, or unrelated Agent configuration
subagents-dispatch implicitly activates on an unrelated ordinary task
update or uninstall mutates unrelated Codex state
```

Permission-source provenance `UNKNOWN` is not a blocker unless the release explicitly claims the source identity or Host selection decision.

Role-calibration incompleteness, an unfinished formal product benchmark, or missing experiment telemetry is not a v3.0.0 blocker when the release makes no claim that depends on it.

`PYTHON_PREREQUISITE_UNMET` blocks the Python-backed gate that could not execute. It is not evidence of Host route rejection, inspector regression, or permission mismatch.

Keep Host limitations separate from project defects in the validation report.

## 5. Repository governance before tagging

Before a formal tag, inspect current repository administration state directly. At minimum verify that unsafe history rewriting is prevented for `main` and record active deletion protection, pull-request requirements, and required status checks exactly as configured at that time.

For the current single-maintainer workflow, PR and pre-merge status-check requirements are optional. Code must not silently change repository protection settings.

## 6. Tag, distribution smoke, and GitHub Release

Only after the exact merged candidate passes repository, Host, human App UI, governance, and immutable Marketplace-source gates:

1. confirm `main` still points to the validated candidate SHA;
2. confirm tag, Plugin version, Marketplace tag ref, README version, and CHANGELOG version are consistent;
3. create the immutable semantic-version tag on that exact SHA;
4. require the tag-triggered canonical CI run to pass, including `GITHUB_REF_NAME == v<plugin version>` and the full repository/managed-profile lifecycle on the tagged source;
5. from a clean environment, add the Marketplace from that exact tag and install the Plugin;
6. confirm the installed Plugin reports the same version and the Marketplace entry resolves the Plugin source from the same tag rather than a mutable branch;
7. fully restart the Codex App when required for registry refresh;
8. human-check the `/` menu again and confirm the same six namespaced Skill entries select the expected tagged payload;
9. run one bounded tagged-distribution Dispatch smoke with at least one real production child;
10. use raw Host/rollout evidence for any runtime claim that cannot be established from UI alone;
11. create the GitHub Release only after the tagged distribution smoke passes.

The GitHub Release must describe only capabilities and performance claims supported by the evidence completed for that exact tagged candidate.