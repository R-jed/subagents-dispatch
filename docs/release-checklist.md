# Release Checklist

Use this checklist for a formal subagents-dispatch release candidate. It covers the product users install and run. Role-calibration campaigns and formal product-benchmark campaigns remain development/research infrastructure.

The rule for adding a hard release gate is simple:

```text
hard release gate
-> must protect one concrete public capability, safety property, distribution property, or release claim
```

If a proposed gate cannot name that protected claim, keep it out of the release path.

The historical v3.0.0 release path established the repository/package, managed-profile, App Skill, native route, runtime-attestation, control-surface, Doctor, update/uninstall, and tagged Marketplace gates. Formal role calibration, formal model/effort comparison campaigns, formal single-agent versus Dispatch product benchmark campaigns, and calibration profile materialization are valid research capabilities but are not hard release blockers unless a release claim depends on them. Runtime attestation remains part of the release path when a release claim says what actually ran.

A release that changes the packaged spawn guard additionally validates the exact Hook package, Host trust/discovery state, one legal managed spawn, and representative illegal managed spawn calls. A release that changes Plugin installation/update diagnostics additionally validates package/cache/source identity and the explicit update transaction. It does not rerun unrelated Host behavior merely because a later release exists. Release gates follow the actual release delta.

## 1. Candidate identity

Before validation, record:

```text
version
candidate commit SHA
candidate tree SHA
Codex App / CLI version used for Host smoke
operating system used for Host smoke
resolved Python helper invocation
sys.executable
Python version
```

The version in `.codex-plugin/plugin.json` must match the public README badges, `README_AI.md`, and newest `CHANGELOG.md` entry for a release-prep candidate. `.agents/plugins/marketplace.json` must bind the formal release to `v<version>`, not a mutable branch.

Do not create a release tag until the exact candidate commit has passed every applicable pre-tag product gate.

### Evidence ownership

Use the strongest evidence source available for each claim.

```text
Repository/API/CI evidence
-> version, SHA, tree contents, branch/ruleset state, CI, tag peel, Release state

Codex Plugin inventory evidence
-> machine-readable installed cache version, enabled state, Marketplace source/ref

Public Host runtime evidence
-> spawn/details metadata and Hook state the Host actually reports

Exact Host-produced rollout evidence
-> allowlisted child route/identity/permission metadata from scripts/inspect-agent-runtime.py

Raw Host/rollout evidence
-> public runtime metadata, exact inspected rollout metadata, spawn_agent arguments,
   child identity, lifecycle events, Hook allow/block output, retry accounting, implicit activation

Direct human Codex App observation
-> what appears in the Skill menu, exact rendered entry names, namespace/prefix,
   Hook trust/review presentation when surfaced, post-selection presentation

Model self-report
-> explanatory only; it cannot by itself close a Host/UI gate or prove runtime route, Hook trust, or installed Plugin identity
```

For child runtime attestation, follow `docs/runtime-attestation.md`. Public Host metadata is preferred. If a required field is omitted and the exact child rollout is available, use the bundled inspector and place only its allowlisted output in the local runtime-evidence source.

Configured profile values, accepted role values, manually copied JSON, and child prose cannot be substituted for Observed fields. Public and exact-rollout evidence must agree wherever both expose the same field. Route, effective permission state, and permission-source provenance close separate claims.

The following App facts require direct human observation:

```text
all six Plugin Skills are visible in the App Skill menu
their exact user-visible names are namespaced and distinguishable from generic skills
an unrelated generic entry such as doctor is not mistaken for this Plugin's Doctor
selecting each entry binds to the expected subagents-dispatch Plugin Skill
the post-selection presentation is recorded
Hook review/trust UI is recorded when this release changes the packaged Hook
```

A model or repository file cannot by itself close a Host/UI gate. During the Human App gate, record the exact rendered entry labels and post-selection presentation. Do not invent literal slash-command syntax when the App presents a Skill chip or another selection form.

## 2. Repository gates

The exact candidate must pass the canonical GitHub Actions workflow on all configured platforms:

```text
Ubuntu / Python 3.11
Ubuntu / Python 3.12
macOS / Python 3.11
Windows / Python 3.11
```

Required deterministic checks are:

```text
plugin JSON validation
Marketplace JSON validation
hooks/hooks.json JSON validation
pinned official OpenAI Plugin validator
Ruff
full pytest suite
spawn-guard regression and adversarial tests
Plugin installation/update transaction tests
managed Agent install
installer --check
Doctor --check
idempotent reinstall
ownership-aware managed Agent uninstall
post-uninstall installer --check fails as Not installed
reinstall after uninstall
final installer --check
tag/version parity when running from a release tag
```

The official OpenAI Plugin validator remains pinned by `.github/workflows/ci.yml`. The Plugin manifest intentionally relies on the Host's default `hooks/hooks.json` discovery path so the exact public manifest continues to pass that official validator. Do not generate a validator-only manifest or delete fields only for CI.

The spawn guard tests must prove at minimum:

```text
valid prepared managed spawn -> allow
fork_turns omitted -> block
fork_turns=all -> block
partial-history fork -> block
wrong managed agent_type -> block
wrong native task name -> block
reserved managed spawn without prepared state -> block
corrupt/unsafe matching state -> block
managed child nested spawn -> block
pending takeover -> block
unrelated non-Dispatch spawn -> pass through
raw message/tool input is not emitted or persisted by the guard
```

The Plugin installation/update tests must prove at minimum:

```text
exact package/cache/versioned source -> OK
installed cache newer than current task package -> package/cache skew warning
versioned Marketplace snapshot newer than installed cache -> update available warning
duplicate installed identity -> fail closed
unversioned Marketplace source -> UNKNOWN
Marketplace source older than installed cache -> fail closed
explicit update refreshes only the configured subagents-dispatch Marketplace
Marketplace refresh alone does not count as Plugin update success
returned Plugin identity/version/installedPath must match the selected release
post-install inventory must converge
new package manifest, managed profiles, and new Doctor must verify before completion
already-current release refresh does not reinstall the same Plugin
```

For the current single-maintainer phase, use this integration workflow:

```text
short-lived feature branch
-> local full validation where available
-> adversarial/deep review
-> repair on the same branch
-> full revalidation
-> direct merge to main or reviewed pull request
-> GitHub Actions cross-platform confirmation
```

A pull request is optional. When a PR is used, validate the merge result before merge. In either path, the final `main` push run confirms the integrated candidate.

Before a local or real-Host gate invokes a bundled Python helper, resolve one Python 3.11+ interpreter from the actual environment according to `docs/python-runtime.md`. Record the resolved invocation, `sys.executable`, and Python version and keep that interpreter fixed for the operation.

A missing command named `python` is not a failed prerequisite when another supported Python 3.11+ invocation is available. Interpreter command-name resolution is environment adaptation, not role/model/Agent/evidence substitution.

If no Python 3.11+ interpreter can be resolved, record `PYTHON_PREREQUISITE_UNMET` and stop before a Python-backed Host spawn, update verification, or inspection gate. The downstream affected gates are `NOT TESTED` or `INVALIDATED` as appropriate. Do not relabel that prerequisite failure as a Host role rejection or route mismatch.

Deterministic local gate after `<python-3.11+>` has been resolved:

```text
<python-3.11+> -m json.tool .codex-plugin/plugin.json
<python-3.11+> -m json.tool .agents/plugins/marketplace.json
<python-3.11+> -m json.tool hooks/hooks.json
<python-3.11+> -m ruff check scripts tests --ignore E402
<python-3.11+> -m pytest -q
<python-3.11+> scripts/install-agents.py --codex-home <isolated-test-home>
<python-3.11+> scripts/install-agents.py --codex-home <isolated-test-home> --check
<python-3.11+> scripts/doctor.py --codex-home <isolated-test-home> --check --thread-id release-doctor
<python-3.11+> scripts/uninstall-agents.py --codex-home <isolated-test-home>
```

The isolated repository gate may not have a Codex CLI/Plugin inventory. In that environment `Plugin installation` is allowed to remain `UNKNOWN`; this does not turn the isolated package/lifecycle check unhealthy.

## 3. Real Codex Host gates

Run only applicable Host checks against the same candidate that will be tagged. Reuse prior release evidence for unchanged Host behavior where the release delta does not affect that behavior.

### Plugin and App Skill discovery

Package identity remains:

```text
Plugin: subagents-dispatch
Skill: dispatch
Skill: preview
Skill: status
Skill: steer
Skill: takeover
Skill: doctor
```

Human App gate:

1. restart the Codex App when installed Plugin metadata or Hook package changed;
2. open the App Skill menu;
3. confirm all six Plugin Skills;
4. record the exact rendered entry labels, visible namespace, and post-selection presentation;
5. confirm selection binds to the expected Plugin Skill;
6. run one unrelated ordinary task and confirm subagents-dispatch does not implicitly activate.

### First-use readiness

When this lifecycle changed in the release delta, start from a clean state where the five managed profiles are absent and confirm:

```text
Python 3.11+ helper prerequisite resolves
a bounded automatic provisioning operation creates only the five owned profiles plus ownership metadata
installer --check passes
RESTART_REQUIRED is returned
0 child spawns occur before restart
unrelated Codex state remains unchanged
```

### Spawn guard Hook

When `hooks/hooks.json`, the launchers, `scripts/spawn_guard.py`, `contracts/policy.json` delegation invariants, or related Host composition changed, run the Hook gate.

Record the Host-observed Hook state separately from packaged configuration:

```text
source = Plugin
PreToolUse matcher = spawn_agent
handler type = command
execution mode = sync
trust = Trusted or Managed for a full PASS
enabled = true for a full PASS
```

`Untrusted` or disabled is an environment/user-control state and must not be rewritten by Doctor. `Modified`, duplicate, wrong-source, or wrong-mode evidence is a failure for the Hook-runtime claim. Missing Hook evidence remains `UNKNOWN`.

Run one real legal Dispatch spawn prepared through the normal state machine. Confirm the Hook allows it and the native Host still owns returned child identity and lifecycle.

Then test representative invalid proposed managed calls without creating a child:

```text
omit fork_turns
set fork_turns=all
use a wrong policy role or wrong native task name
attempt nested spawn from a managed child when practical
```

Each must be blocked before Host child materialization. Confirm a separate unrelated non-Dispatch `spawn_agent` call is not captured by the Plugin guard.

A generic non-blocking Hook command failure is a Hook failure, not a Spawn Guard block and not a Host role rejection. The Host may continue the proposed `spawn_agent` call after such a failure, so the actual native spawn result determines whether a child materializes and whether an Agent attempt begins. Existing Skill/contract checks remain the correctness fallback. Do not record the Hook failure itself as either a successful guard block or a child attempt.

### Five production routes

When route/profile/runtime behavior changed in the release delta, prove controlled real Host spawn for all applicable exact production roles:

```text
subagents_dispatch_reader
subagents_dispatch_worker
subagents_dispatch_solver
subagents_dispatch_investigator
subagents_dispatch_advisor
```

Use one bounded smoke child per role with `fork_turns = none` and settle every child before returning.

For each role record Configured, Requested, Accepted, Observed route, effective permission state, and permission provenance separately. An accepted exact `agent_type` proves role acceptance only. It does not establish observed model, effort, or permission. Missing source provenance makes only that dimension `UNKNOWN`. Observed mismatches and public/local conflicts fail closed.

If a current test account lacks entitlement for a configured model, record that affected route as entitlement-limited / not tested for that environment. Do not silently substitute a fallback model or rewrite the production route merely to make a smoke test green. Existing verified evidence for unchanged route behavior may be inherited according to the release-delta rule.

When exact local inspection is required:

```text
<python-3.11+> scripts/inspect-agent-runtime.py <child-thread-id> \
  --expected-parent-thread-id <root-thread-id> \
  --expected-agent-role <exact-agent-type>
```

### Control Surface integrated scenario

When Dispatch/Status/Steer/Takeover/state ownership changed, run one real orchestration that exercises the changed control surface. Confirm current Host truth is reconciled before writer ownership transfer and `UNKNOWN` never releases a writer.

### Doctor

Static Doctor must remain read-only. Verify exactly eleven production layers:

```text
Plugin
Plugin installation
Skills
Spawn guard package
Managed Agent profiles
Dispatch state
Codex Host
Spawn guard runtime
Runtime route
Effective permission state
Permission-source provenance
```

`Plugin` proves only the package currently executing. `Plugin installation` uses the machine-readable installed Plugin inventory and must keep installed cache version, versioned Marketplace ref, enablement, update availability, and active package/cache skew distinct. Ordinary Doctor must not refresh the Marketplace merely to check health.

Without available installed inventory, explicit Host Hook state, or runtime evidence, the corresponding supported dimensions remain `UNKNOWN`. A local package cannot promote installed identity, Hook trust, or runtime route to PASS. The user-facing output uses stable `[OK]`, `[WARN]`, `[FAIL]`, and `[UNKNOWN]` status lines and provides an exact action for actionable warnings/failures.

Explicit live-route smoke is a separate user-requested workflow and never becomes an automatic side effect of static Doctor.

### Update and uninstall

For a release that changes Plugin update lifecycle, exercise the explicit update transaction from the previous public release to the new tagged release before creating the GitHub Release.

The tagged-distribution update smoke must confirm:

```text
previous public release is the installed starting identity
Doctor sees that installed identity before update
explicit update refreshes the configured subagents-dispatch Marketplace
refreshed source resolves to v<new-version>
Codex installs the exact subagents-dispatch Plugin identity
returned installed version and installed root match the tagged release
new installed manifest matches the returned version
new package reconciles and verifies the five owned managed Agent profiles
post-update Plugin inventory converges
new installed Doctor verifies package/static production surfaces
update reports RESTART for a changed package
fresh session loads the new package identity
changed Hook trust remains a Host/user review decision
```

If the versioned Marketplace ref already equals the installed version, explicit update may be a no-op after the user-requested refresh and must not reinstall the same Plugin merely to produce activity.

Uninstall order remains:

```text
ownership-aware managed Agent uninstall while Plugin files are still available
-> remove Plugin registration
-> remove Marketplace source
```

The supported Plugin and Marketplace removal commands may update user configuration only for those registrations. During uninstall, allow only the semantic delta required by the supported Plugin and Marketplace registration removal commands; all unrelated configuration semantics must remain unchanged.

The default-discovered Hook disappears with the Plugin package and does not require a user-global Hook entry cleanup path.

## 4. Hard release blockers

Stop release for any applicable gate with:

```text
candidate/main drift before tag
required CI failure
Plugin validator failure
package/version/ref mismatch
ambiguous or contradictory installed Plugin identity
explicit update reports completion without installed version/path/inventory convergence
explicit update modifies unowned managed state
unsafe managed-profile ownership state
spawn guard allows a managed full-history/omitted-history fork when that guard is in release scope
spawn guard blocks unrelated Agent traffic
Hook package differs from the reviewed candidate
required Host route mismatch
required runtime evidence conflict
writer ownership can transfer while previous writer is active or UNKNOWN
App Skill identity ambiguity after a changed Skill surface
update/uninstall modifies unowned state
```

An unavailable non-required observation is recorded as `UNKNOWN` or `NOT TESTED`; it is not converted into a fabricated PASS.

## 5. Repository governance before tagging

Immediately before the tag write:

1. re-fetch `main`;
2. confirm its exact SHA/tree match the validated candidate;
3. confirm no conflicting release tag exists;
4. confirm open change state is understood;
5. record the current ruleset/tag-governance residuals.

Do not move or overwrite an existing public release tag to repair a changed candidate.

## 6. Tag, distribution smoke, and GitHub Release

Create an annotated versioned semantic-version tag `v<version>` on the exact validated commit. Verify:

```text
tag ref
-> annotated tag object
-> exact candidate commit
```

The ref/object/commit peel proves release identity; it does not by itself prove platform-enforced tag immutability. Record tag signature/verification status accurately. Do not describe a tag as platform-enforced immutable without a tag ruleset or equivalent platform evidence.

Require tag-triggered canonical CI on all four configured platforms and tag/version parity.

Then install from a clean Marketplace environment and verify that the Marketplace entry resolves the Plugin source from the same tag rather than a mutable branch. Confirm the installed package version, six Skills, five managed profiles, and default-discovered `hooks/hooks.json` identity.

When the update lifecycle changed, also perform the tagged-distribution update smoke described above from the previous public release. A source defect discovered after the public tag must not be repaired by moving that tag; create a new version strategy instead.

If App-visible Skill or Hook trust UI changed, do the direct human App observation on the tagged distribution. If it did not change and the release-delta rule allows inherited evidence, record the inherited evidence rather than mechanically repeating every historical Host test.

Create the GitHub Release only after the applicable tagged-distribution gates pass. The release record should include the exact release commit, tag object/peel, canonical CI run, distribution identity, applicable Host/UI/update evidence, and remaining residual risks.
