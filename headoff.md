# Headoff

Updated: 2026-09-05.

## Purpose

Development-session continuity only. This file is not Plugin runtime, release evidence, or a release gate.

## Current branch and architecture

Canonical local repository: `/Users/qunqing/2026-Project-Agent/subagents-dispatch`.

Active implementation branch: `feat/gpt6-routing`.

The first-public `1.0.0` architecture now has three managed semantic roles:

```text
Programmer             gpt-5.6-luna / max
Product Manager        gpt-5.6-sol / medium | high
Department Director    gpt-6-astra / high
```

Main owns semantic classification and orchestration. Deterministic policy owns the exact legal managed route. Persistent role TOMLs carry behavior/configuration only and do not pin model or effort.

## Verified implementation commits

```text
499d743  refactor: establish three-role routing core
91d577e  feat: guard parallel semantic reads
3801479  refactor: simplify calibration evidence plane
988c50e  fix: make plugin updates exact and transactional
```

Each commit passed the repository pre-commit checks. Before the current Host-reference closure began, full pytest was 510/510 PASS, Ruff passed, package integrity passed, managed-profile lifecycle/Doctor passed, and the pinned official OpenAI Plugin validator passed.

## Host release-policy amendment

The user explicitly changed the first-release Host verification strategy during implementation: do not run a project-owned real-Host N0-N7 campaign. Reuse the mature Native Codex integration patterns from these pinned projects instead:

```text
sol-advisor
https://github.com/DannyMac180/sol-advisor
37b75cad535abdd46531f0227483a8842d045ab8

astra-advisor
https://github.com/DannyMac180/astra-advisor
c72d3280551f118eba51a5884e3971a0c0058aa6
```

`docs/v4/host-reference.json` is the new machine release owner for these assumptions. The retired N0-N7 campaign contract, qualification guard, rollout collector, procedure and carry-forward release machinery have been removed from the active design.

This amendment changes release qualification, not runtime truth. Ordinary Orchestrate must still use the current callable Host surface as authority and fail the affected delegation/review closed when required model/effort/control or realized-route evidence is missing, conflicting, unavailable or unobservable.

Depth one remains a semantic product boundary. The references do not prove Host-hard descendant isolation. If a specific user requirement demands hard isolation, direct current-Host evidence is required for that stronger claim.

## Final Review

The formal release Final Review remains required after the exact release source is frozen:

```text
subagents_dispatch_department_director
gpt-6-astra
reasoning_effort = high
fork_turns = none
fresh context
semantic mutation authority = none
```

The Main-owned pre-review request and result both bind the exact candidate and request digest. Permission assurance follows `contracts/final-review.md`.

## Current safe continuation

Host-reference Slice 7 source work is now stabilized:

```text
release/reference focused tests   14/14 PASS
affected Slice 7 tests            122/122 PASS
full pytest                       428/428 PASS
Ruff                              PASS
package integrity                 PASS
managed profile lifecycle/Doctor PASS
official OpenAI Plugin validator  PASS
git diff --check                  PASS
```

Use Git history as the authority for whether this verified Slice 7 source has already been committed. No project-owned Host campaign is required.

Do not push, tag, publish or create a release without explicit user authorization.
