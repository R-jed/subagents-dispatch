# V4.0.0 Release Checklist

Use this checklist for the exact V4.0.0 candidate. Repository implementation may complete while real Codex Host evidence is unavailable, but publication remains blocked until the required Host lifecycle campaign is captured.

## Evidence ownership

Keep these evidence classes separate:

```text
Repository/API/CI evidence
Raw Host/rollout evidence
Direct human Codex App observation
Model self-report
```

Repository/API/CI evidence closes deterministic package, schema, test, and distribution checks. Raw Host/rollout evidence owns lifecycle and runtime truth. Direct human Codex App observation owns rendered UI labels and post-selection presentation. Model self-report is supporting context and cannot close a Host/UI gate by itself.

Formal calibration and benchmark campaigns remain Experiment Plane work unless a release claim explicitly depends on them. Runtime attestation and the real Host lifecycle campaign remain release-path evidence where the corresponding claims depend on observed Host behavior.

## 1. Candidate identity

Record the exact candidate commit, tree, Plugin version, Marketplace ref, package-integrity manifest, production Hook digest, profile contract digest, Host contract digest, Codex Host version/build, and operating systems used for smoke.

`.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json`, and the V4 changelog entry must agree on `4.0.0` before tagging. Use a versioned semantic-version tag only after all release gates pass. Verify that Marketplace installation resolves the exact tagged candidate rather than a mutable branch.

The checklist does not claim platform-enforced tag immutability. Evidence that a ref resolves to an expected commit does not by itself prove platform-enforced tag immutability.

## 2. Repository gates

The exact candidate must pass the canonical GitHub Actions matrix:

```text
Ubuntu / Python 3.11
Ubuntu / Python 3.12
macOS / Python 3.11
Windows / Python 3.11
```

Required deterministic checks include:

```text
Plugin and Marketplace JSON validation
package-integrity regeneration check
pinned official OpenAI Plugin validator
Ruff
full pytest suite
managed Agent install/check/uninstall/reinstall lifecycle
Doctor --check
V4 state / Work Graph / Scheduler tests
PendingControl / Guard / WriterLease tests
Orchestrate tests
migration and fail-closed tests
tag/version parity when running from a release tag
```

Production model/effort remains fixed:

```text
Reader / Worker        Luna Max
Investigator           Terra High
Solver / Advisor       Sol High
```

Public Skill directories must be exactly:

```text
skills/orchestrate
skills/doctor
```

For route evidence preserve `Configured -> Requested -> Accepted -> Observed`. Never promote accepted routing metadata or child prose into observed runtime truth.

Supported uninstall commands may update `config.toml` only to persist removal of this Plugin and Marketplace registration. Release verification must allow only the semantic delta required by the supported Plugin and Marketplace registration removal commands; unrelated configuration semantics and other Codex state must remain unchanged. In addition, all unrelated configuration semantics must remain unchanged.

## 3. State and migration gates

Verify:

```text
state v4 remains bounded and thread scoped
WorkUnit acceptance is separate from Host lifecycle
Host COMPLETED advances only to RESULT_READY
dependencies unlock only from WorkUnit ACCEPTED
single responsibility may keep team_plan_revision = null
managed spawn requires complete responsibility_context
stale execution/control/lease observations are discarded
WriterLease.UNKNOWN never auto-releases
PendingControl.UNKNOWN remains fail closed
V3.x active or corrupt state is never silently migrated
plan-only creates no runtime state, lease, control, or Host action
```

The production V3.x compatibility spawn Guard remains installed until the lifecycle Hook cutover. `dispatch_state.py`, legacy migration, and the tests that still protect compatibility or shared storage remain active dependencies during this window.

## 4. Real Codex Host gate

The machine-readable authority is `docs/v4/host-smoke.json`. Its exact required probes and requirements are authoritative. This checklist deliberately does not maintain a second full copy of the H00-H20 field list.

Offline CI, source inspection, the official Plugin validator, prior V3 spawn-guard evidence, or model self-report cannot substitute for this gate. The tracked contract remains `PENDING` with empty embedded results; authoritative campaign results remain external and candidate-bound.

Before spending the full campaign budget, run the feasibility wave against the exact staged `docs/v4/hooks.json` definition:

```text
H00  exact Hook trust + complete exposed collaboration tool identities
H01  spawn lifecycle identity/namespace coverage
H08  encrypted/transformed message representation compatibility
H13  exact managed profile selectors, effective model/effort/permissions/tool surface
H14  managed leaf tool surface + send_message containment
H07  reliable lifecycle PostToolUse success/failure discrimination
H15  fresh-context assignment semantic completeness
```

If any exposed lifecycle or observation alias is not intercepted exactly, stop. Coverage of `spawn_agent` does not prove coverage of `collaboration.spawn_agent` or another Host identity.

If the Host exposes `send_message` to a managed child, every exposed peer-message identity must hit PreToolUse and be blocked before peer delivery. Peer messaging may not become a side channel for sibling control.

If H08 cannot bind the authorized plaintext responsibility to the actual Hook representation without weakening PendingControl integrity, stop and redesign the binding. Do not use string heuristics or simply omit message semantics from authorization.

If H07 cannot reliably distinguish a successful lifecycle operation from a failed one, stop. Do not infer success from arbitrary response text and do not ACK a control merely because PostToolUse fired.

Only after the feasibility wave passes should the remaining H00-H20 probes be completed. Every probe must be bound to one declared environment and the exact candidate identity required by the external release-evidence contract. H20 must run on Windows.

## 5. Lifecycle Hook cutover

Only after all H00-H20 probes pass against the staged definition may `docs/v4/hooks.json` be promoted to production `hooks/hooks.json`.

Promotion mutates the candidate. Therefore:

1. refresh package integrity and exact candidate identity;
2. rerun the complete four-platform repository matrix;
3. repeat every Host probe affected by the promoted candidate/Hook identity;
4. ensure installed Doctor accepts the production lifecycle Hook contract;
5. keep any ambiguous Host behavior fail closed.

With production lifecycle Hooks active verify representative flows:

```text
plan-only
zero-child task
single dependency-free delegated responsibility
two-child initial fanout
Host-capacity-limited fanout
progressive refill
acceptance backpressure
same-child correction
CONTINUE after interrupt
takeover
cancellation
fresh Advisor review
post-review mutation invalidation
V3.x unresolved-state block
```

Writer safety must still prove:

```text
fresh writer activation reserves WriterLease before Host call
second managed writer is blocked
followup cannot bypass a newer lease
interrupt ACK alone does not release WriterLease
settlement requires exact current Host observation + retained receipt
takeover transfers WriterLease atomically to Main
stale lease identity cannot release a newer lease
```

## 6. Final Review and release evidence

After the promoted candidate is deterministic and relevant Host probes pass, run a fresh independent Final Review under `contracts/final-review.md` against the exact candidate.

Any subsequent mutation invalidates that verdict.

Release authority belongs to:

```text
<python-3.11+> scripts/release_evidence_v4.py --repo <candidate-root> --evidence <external-release-evidence>
```

The verifier must remain non-zero when external candidate-bound evidence is absent, stale, incomplete, or bound to another candidate.

Doctor is a product-health diagnostic. It must remain read-only/offline by default and must not grant publication authority.

## 7. Installed Doctor and human App gates

Run installed Doctor against an isolated Codex home and require no blocking product-health failure.

After installing the exact release candidate in Codex, directly observe the rendered entries for Orchestrate and Doctor. Verify both are distinguishable, presentation is correct, unrelated tasks do not implicitly activate either Skill, and fresh managed profiles are visible after the documented restart boundary when required.

Do not infer literal App menu syntax from repository identifiers.

## 8. Governance, tag, and distribution

Final sequence:

```text
repository matrix PASS
real staged-Host H00-H20 PASS
promote staged lifecycle Hooks
repository matrix PASS again
repeat affected Host probes against promoted exact candidate
fresh exact-candidate Advisor Final Review PASS
external release evidence verifies exactly
installed Doctor has no BLOCKED product-health failure
human two-Skill App observation PASS
merge approved candidate
create v4.0.0 semantic-version tag
verify Marketplace installs the exact tagged candidate
publish release notes
```

If a real Host gate remains unavailable or fails, record the candidate as repository-complete and release-blocked. Do not relabel `PENDING`, `UNKNOWN`, or `NOT TESTED` as PASS.
