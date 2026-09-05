# 1.0.0 Release Checklist

Use this checklist for the first public `1.0.0` release built on Native Core V4.

## 1. Freeze exact release identity

The release source is the exact final Git commit/tree. The shipped package is additionally bound by `.codex-plugin/package-integrity.json`.

The Host integration basis is `docs/v4/host-reference.json`. It pins the mature `sol-advisor` and `astra-advisor` sources whose Native Codex usage establishes the Host assumptions reused by this Plugin. The release verifier binds the exact canonical digest of that reference contract.

`.codex-plugin/plugin.json`, Marketplace metadata and the changelog must agree on `1.0.0`. Create the versioned semantic-version tag `v1.0.0` only after every release gate below passes. Resolving Marketplace installation to the expected commit does not by itself prove platform-enforced tag immutability.

## 2. Repository gates

The exact frozen source must pass the canonical GitHub Actions matrix:

```text
Ubuntu / Python 3.11
Ubuntu / Python 3.12
macOS / Python 3.11
Windows / Python 3.11
```

Required checks include:

```text
Plugin and Marketplace JSON validation
generated package-integrity verification
official OpenAI Plugin validator
Ruff
full pytest
managed profile install/check/uninstall/reinstall lifecycle
Doctor
Native Core state/work graph/scheduler/lifecycle/writer tests
exact-identity transactional updater tests
unsupported pre-1.0 state rejection
product-surface consistency
```

The public Skill directories remain exactly `skills/orchestrate` and `skills/doctor`.

Supported removal commands may update `config.toml` only to persist removal of this Plugin and Marketplace registration. Release verification must allow only the semantic delta required by the supported Plugin and Marketplace registration removal commands; all unrelated configuration semantics must remain unchanged, and other Codex state must remain unchanged.

Production managed routes remain:

```text
Programmer             gpt-5.6-luna / max
Product Manager        gpt-5.6-sol / medium | high
Department Director    gpt-6-astra / high
```

Main model/effort never substitutes for or changes these managed routes. Every managed spawn sends the exact policy-backed model and `reasoning_effort`; the persistent role TOMLs do not pin either field.

## 3. Native Core safety gates

Verify at minimum:

```text
state is bounded and root-session scoped
WorkUnit acceptance is separate from Host lifecycle
Host COMPLETED advances to RESULT_READY only
dependencies unlock only from ACCEPTED
managed spawn requires complete responsibility context
fresh child uses exact policy-backed agent_type/model/reasoning_effort and fork_turns = none
requested/accepted/observed Host facts remain distinct
missing or conflicting required Host facts fail the affected delegation closed
stale control/lease observations are rejected
explicit pre-materialization rejection consumes no fresh attempt
ambiguous materialization becomes UNKNOWN
WriterLease.UNKNOWN never auto-releases
interrupt return alone never releases WriterLease
fresh retry requires changed execution basis and settled prior execution
same-child correction requires a new correction basis
CONTINUE preserves the same interrupted ExecutionBinding
unsupported pre-1.0 state is rejected without migration
plan-only creates no runtime state, lease or Host action
semantic-read overlap under broader Host permission is protected by the artifact-immutability guard
Department Director has no semantic mutation authority
```

Managed children are instructed not to create or control further project Agents. This is a product semantic boundary, not a claim that Codex removes collaboration tools from every child. If a user requirement specifically demands Host-hard descendant isolation, require direct current-Host evidence for that stronger requirement or report it unavailable.

## 4. Host reference conformance

Do **not** run a project-owned N0-N7 Host campaign for release qualification.

`docs/v4/host-reference.json` is the machine-readable release authority for the Native Host assumptions borrowed from the two mature reference implementations:

```text
sol-advisor
  https://github.com/DannyMac180/sol-advisor
  37b75cad535abdd46531f0227483a8842d045ab8

astra-advisor
  https://github.com/DannyMac180/astra-advisor
  c72d3280551f118eba51a5884e3971a0c0058aa6
```

The shared assumptions used by this Plugin are deliberately narrow:

```text
fresh native child context can request fork_turns = none
current callable Host schema is the authority for available controls
model and reasoning_effort are explicit when that Host surface exposes them
requested settings are not proof of realized settings
missing, conflicting, unavailable or unobservable required route controls fail closed
no silent model/effort/role substitution
```

Reference conformance is a release-design basis, not a statement that every installed Codex build exposes every managed route. Ordinary Orchestrate still evaluates the current Host surface when a material claim depends on it. If the required route or observation cannot be established, only that delegation/review obligation is blocked; the verifier never fabricates Host support from the reference repositories.

## 5. Final Review

After the source is frozen and repository/reference gates pass, bind a Main-owned pre-review request to the exact current `review_artifact_id` and run one fresh independent release Final Review under `contracts/final-review.md`:

```text
agent_type = subagents_dispatch_department_director
model = gpt-6-astra
reasoning_effort = high
fork_turns = none
fresh_context = true
no_edit_instruction = true
```

The result must reference the canonical SHA-256 of the pre-review request, repeat the exact reviewer route, bind the exact same candidate, and return `verdict = ship`.

Permission assurance uses exactly one supported path:

```text
enforced_read_only
  current Host evidence proves effective read-only

artifact_immutability_fallback
  current Host positively reports broader permission
  hard isolation is not required
  semantic mutation authority remains none
  the exact candidate is unchanged before/after
  residual risk is disclosed
```

Unobservable permission, a hard-isolation mismatch, reviewer mutation, changed candidate, route mismatch, or stale request/result binding is `INSUFFICIENT_EVIDENCE`, not PASS.

Then verify the release envelope:

```text
<python-3.11+> scripts/release_evidence_v4.py \
  --repo <candidate-root> \
  --evidence <external-release-evidence>
```

The envelope binds the exact Git commit/tree, current Host-reference digest, current review artifact, pre-review request, and Final Review result. The verifier rejects the retired Host-campaign/carry-forward envelope shape.

## 6. Installed-product gate

Install the exact shipped package basis into an isolated Codex home. Run Doctor and require no blocking product-health failure. Verify the two public Skills and the three managed profiles. Exercise explicit update/check documentation against the shipped CLI surface so docs cannot drift from the transactional updater.

## 7. Final sequence

```text
merge approved source into the release line and freeze the exact release commit
final release-source repository matrix PASS on that frozen commit
product-surface consistency PASS
pinned sol-advisor/astra-advisor Host-reference conformance PASS
fresh final-source Department Director / Astra High Final Review PASS
release evidence verifies
installed Doctor has no blocking failure
human two-Skill App observation PASS
create v1.0.0 versioned semantic-version tag
verify Marketplace resolves the exact tagged source
publish release notes
```

Do not push, tag or publish merely because repository tests pass. Those publication actions remain explicit release decisions.
