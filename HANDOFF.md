# HANDOFF

Updated: 2026-09-05

This file is continuity documentation only. It is not Plugin runtime, release evidence, or a release gate. Use Git and the referenced contracts as source of truth.

## Next-session purpose

Close the remaining first-public `1.0.0` release gates without reopening the completed GPT-6-era architecture work and without reintroducing the retired project-owned Host qualification campaign.

The source implementation is stabilized. The remaining hard gate is the exact-source fresh Department Director / Astra High Final Review, followed by release evidence and the release-line/installed-product gates in `docs/release-checklist.md`.

## Exact repository state to establish first

Repository root: the directory containing this file.

Branch:

```text
feat/gpt6-routing
```

Code baseline immediately before this continuity-only HANDOFF update:

```text
a86c101  fix: align plugin model metadata
```

This HANDOFF update itself changes the Git tree. Therefore the next agent MUST run:

```text
git status --short --branch
git rev-parse HEAD
git rev-parse HEAD^{tree}
git log --oneline --decorate -12
```

and treat that result, not the baseline above, as the exact current candidate.

Do not push, tag, publish, or create a release without explicit user authorization.

## Current product contract

Do not restate or redesign it here. Read:

- `contracts/policy.json`
- `contracts/routing.md`
- `contracts/final-review.md`
- `docs/v4/architecture.json`
- `docs/v4/host-reference.json`
- `tasks/gpt6-refactor-design.md` — implementation amendment / Slice 7 is the relevant settled section; earlier grilling text is historical context.

Current managed routes are:

```text
Programmer          -> gpt-5.6-luna / max
Product Manager     -> gpt-5.6-sol / medium | high
Department Director -> gpt-6-astra / high
```

Public Skills remain exactly `Orchestrate` and `Doctor`.

## Completed work

Use the commits instead of duplicating their implementation details:

```text
499d743  refactor: establish three-role routing core
91d577e  feat: guard parallel semantic reads
3801479  refactor: simplify calibration evidence plane
988c50e  fix: make plugin updates exact and transactional
6c283f7  refactor: adopt mature Host reference conformance
d29b008  docs: record current implementation handoff
7ec0538  docs: remove retired host campaign wording
a86c101  fix: align plugin model metadata
```

Latest release-readiness work completed in this conversation:

1. Slice 7 stale Skill wording was removed at `7ec0538`:
   - `skills/orchestrate/SKILL.md` no longer refers to retired `N1` gating;
   - `skills/doctor/SKILL.md` no longer lists retired Native Core Host campaigns as a current maintainer workflow;
   - package-integrity hashes were regenerated.
   Independent Spec and Standards reviews both returned PASS.

2. A static public-release audit found one additional real metadata defect: `.codex-plugin/plugin.json` still advertised retired `gpt-5.6-terra` in `keywords` while the current third role is Astra. `a86c101` fixes that to `gpt-6-astra`, adds the public-surface regression in `tests/test_product_surface.py`, and regenerates package integrity. Independent Spec and Standards reviews both returned PASS.

3. Current non-historical Terra scan after the fix finds only the negative regression assertion. Current product/release surfaces contain no old five-profile Agent names; remaining `worker`/`advisor` text is either upstream Codex terminology or the pinned `sol-advisor` / `astra-advisor` reference identity.

4. Release/version surface was checked:
   - Plugin version: `1.0.0`;
   - latest `CHANGELOG.md` release: `1.0.0`;
   - Marketplace source remains canonical local `./`;
   - public Skills: exactly `orchestrate`, `doctor`;
   - managed profiles: exactly Programmer, Product Manager, Department Director.

5. The stale pre-1.0 five-profile installation under the user's Codex home was handled without manual deletion. The old ownership manifest and all five profile SHA-256 values exactly matched historical owner commit `c6c663e`; that historical ownership-safe uninstaller removed only its owned files. Current installer then provisioned the three schema-2 profiles and `--check` passed. Do not repeat this migration unless current ownership evidence again proves an exact old-owner match.

## Verification already green

On the current implementation line, including the latest metadata fix:

```text
Ruff                                      PASS
full pytest                               428/428 PASS
focused product-surface test              8/8 PASS
release/product contract focused tests    19/19 PASS
package integrity                         PASS
git diff --check                          PASS
managed profile lifecycle / Doctor        PASS
pinned official OpenAI Plugin validator   PASS
Metadata Spec Review                      PASS
Metadata Standards Review                 PASS
```

The official validator pin is defined by `.github/workflows/ci.yml`; do not float the validator ref.

Doctor may report Host integration as `UNKNOWN` when no current Host capability snapshot is supplied. That is expected and must not be upgraded into Host proof.

## Host release strategy

Do not run or recreate the old project-owned N0-N7 campaign. The release-design reference contract is `docs/v4/host-reference.json`, pinned to the exact mature `sol-advisor` and `astra-advisor` sources recorded there.

This changes release qualification only. Ordinary runtime Host truth remains current, requested/accepted/observed evidence remains distinct, and unavailable/conflicting required route/control evidence still fails the affected operation closed.

Historical campaign documents remain under `docs/history/` and may intentionally contain retired terms. `docs/history/README.md` explains that boundary.

## Release evidence prepared before this HANDOFF edit

For code baseline `a86c101c780f8d93ca310f350ec1fb1dab412ca6`, the following external draft was generated:

```text
candidate tree:
  a60fea06965ae62fb31c8d7d5195532a834f8075

review_artifact_id:
  sha256:da5a1f35a5b241bb4e616fce92e0af04c408e463efc0d25574e4227fb04a9879

host_reference_sha256:
  f5dbc59663f67b4bdb41c3f0eeeb32e75b1b6c659372418c11b37f1e1f22d60d

Main-owned final-review request SHA-256:
  51da36452cd7a6f2183e6202a2b88154954406abce68076bd4fe094ba8142ed4

request:
  /tmp/subagents-dispatch-final-review-request-a86c101.json

draft release evidence:
  /tmp/subagents-dispatch-release-evidence-a86c101.draft.json
```

The draft intentionally has `final_review: null`. Running `scripts/release_evidence_v4.py` against the clean `a86c101` baseline failed with exactly one issue:

```text
final review must be an object
```

That proves the remaining evidence dependency was only the formal Final Review at that exact baseline.

IMPORTANT: because this HANDOFF file is tracked, any HANDOFF commit changes candidate commit/tree and `review_artifact_id`. The `a86c101` request/draft above then becomes historical only. Regenerate all candidate-bound values before the real Final Review; do not reuse them.

## Current blocker

The formal release Final Review has NOT run successfully.

Required exact route from `contracts/final-review.md`:

```text
agent_type       = subagents_dispatch_department_director
model            = gpt-6-astra
reasoning_effort = high
fork_turns       = none
fresh_context    = true
```

A fresh local Codex session was attempted after the three current managed profiles were provisioned. It failed before a reviewer result existed because:

- current Host reported no model metadata for `gpt-6-astra` and would fall back;
- the local Codex account had reached its usage limit and the turn failed.

Under the fail-closed contract, do not substitute another model/role and do not treat earlier ChatGPT Spec/Standards reviews as the formal Department Director release review.

## Next steps

1. Read this file plus `docs/release-checklist.md`, `contracts/final-review.md`, `docs/v4/host-reference.json`, and current Git status/history.
2. Because this HANDOFF update changes the tracked tree, freeze the new exact candidate and rerun the deterministic source gates needed by the checklist.
3. Generate a fresh `scripts/review-artifact.py` receipt, Host-reference digest, Main-owned pre-review request, and external draft release-evidence file for that exact clean candidate. Verify the draft fails only because `final_review` is absent.
4. When the current Host can actually expose and run the exact Department Director / `gpt-6-astra` / High route, run one fresh exact-candidate Final Review. No fallback route.
5. If verdict is `ship` and artifact identity is unchanged, insert that real result into the external evidence and run `scripts/release_evidence_v4.py` to PASS.
6. Complete the remaining checklist gates on the same frozen source: canonical remote CI matrix, release-line identity, installed-product verification, and required human two-Skill observation.
7. Only after explicit user authorization perform any push, tag, Marketplace publication, or release creation.

## Pitfalls to preserve

- Do not rebuild the retired N0-N7 qualification control plane under a new name.
- Do not confuse release-only Host machinery with ordinary runtime Host authority; runtime fail-closed behavior stays.
- Any tracked documentation edit changes the exact release candidate. Candidate-bound review/evidence must be regenerated afterward.
- Public metadata can lag architecture contracts. The stale Terra keyword survived until a dedicated release-surface scan; keep metadata checks in release review.
- Current `1.0.0` installer intentionally rejects unsupported pre-1.0 ownership manifests. Never bypass that by wildcard/manual deletion. Use an ownership-safe historical lifecycle owner only when exact manifest/profile hashes prove ownership.
- `Doctor UNKNOWN` without Host evidence is not a PASS and is not itself a defect.
- Exact final review route unavailability or model fallback is a hard stop, not permission to downgrade.
- Semantic version alone is not installed-product identity; updater correctness is exact-source/package based.

## Suggested skills for the next agent

- Use the user's `实施开发` workflow only if a new source defect is actually found; keep changes TDD-first at an existing public seam and smallest scope.
- Use `code-review` for any new implementation diff: independent Spec and Standards axes, exact fixed point, read-only reviewers.
- Use `Doctor` for installed-product/profile health and ownership-safe maintenance.
- Use `Orchestrate` only when delegated work adds value and the current Host can prove the required managed route; do not use it to bypass Final Review route unavailability.

## Conversation summary

This session closed two release-surface defects without changing the runtime architecture: retired Host-campaign wording in the public Skills (`7ec0538`) and stale Terra model metadata in the Plugin manifest (`a86c101`). Both were independently reviewed and fully tested. It also normalized the local managed-profile installation from the exact historically owned five-profile state to the current three-profile schema, prepared and dry-ran release evidence, and confirmed the formal release remains blocked only on exact Department Director/Astra High Final Review plus the later release-line/CI/installed-product gates.
