# Current State

Updated: 2026-08-23.

This is the short continuation entrypoint for current development and release work. Keep it durable. Do not copy candidate SHA, workflow result, synthetic merge identity, installed-candidate binding, or real-Host verdict into tracked status documents. Read GitHub and Issue #91 directly for those facts.

## Current position

Repository-side V4 Native Core remediation is complete. The remaining release work is real Codex Host qualification on the exact current candidate.

No repository mutation is required before Host qualification unless a real defect or durable handoff defect is discovered. If repository content changes, treat the resulting commit as a new candidate and re-run the affected repository and Host gates.

## Product boundaries

The durable product contract remains:

- `Orchestrate` and `Doctor` are the only public Skills.
- Main is the sole managed coordinator.
- Managed children must not create or control another Agent layer.
- Reader and Worker use Luna Max.
- Investigator uses Terra High.
- Solver and Advisor use Sol High.
- Fresh managed children use `fork_turns=none`.
- The managed-child ceiling is four.
- WorkGraph and WorkUnit own responsibility, dependency and acceptance truth.
- WriterLease owns canonical-workspace managed writer coordination.
- `UNKNOWN` remains fail closed.
- Codex Host owns materialization, lifecycle, capacity, child identity, effective permission and effective collaboration capability.

The historical generic V2 recursion probe remains platform-capability evidence. Revised N1 evaluates actual canonical managed-profile behavior and descendant evidence. Latent recursive Host capability alone does not decide the managed N1 verdict.

## Authority map

Use one owner per kind of truth:

- `contracts/policy.json`: fixed product policy and profile values.
- `docs/v4/architecture.json`: current V4 machine architecture and runtime owners.
- `docs/v4/host-smoke.json`: N0-N8 real-Host campaign contract.
- `docs/v4/technical-debt.json`: explicitly tracked V4 technical debt.
- `docs/architecture.md`: human-readable architecture overview.
- `docs/release-checklist.md`: release sequence and gate checklist.
- GitHub: current branch, PR, candidate and CI state.
- Issue #91: append-only real-Host evidence and `REUSE | RERUN | NOT_RUN` preflight decisions.

`docs/v4/` is reserved for version-specific machine or maintenance contracts. Human continuation notes live at `docs/current-state.md`.

## Host qualification startup

Before any real Host probe, establish the candidate and installed-product basis without spawning or controlling an Agent.

1. Start from the current release branch with a clean working tree and confirm the exact Git `HEAD` against GitHub.
2. Read `codex plugin list --json` and identify the installed `subagents-dispatch@subagents-dispatch` source.
3. When the installed Plugin source is the local repository checkout, the checkout itself is the Plugin source. Do not run the stable Marketplace updater merely to refresh that local candidate. A Marketplace updater is for an explicit stable-update operation and may change the candidate basis.
4. Verify package bytes with `python3 scripts/package_integrity.py --check-generated` and `python3 scripts/package_integrity.py`.
5. Run `python3 scripts/doctor.py --codex-home "$HOME/.codex" --check` and require Plugin package plus all five managed profiles to be healthy. `Host integration = UNKNOWN` is expected until current Host evidence is supplied. `Orchestration state = UNKNOWN` is expected when no task is selected.
6. Record the static checkout, Plugin source and package/profile binding in Issue #91. Do not treat these static checks as fresh Host identity evidence.
7. Start a fresh Codex session. Before invoking `Orchestrate` or any Agent-control primitive, capture the current Host build/version, platform/architecture, run/session/thread identity and the actually exposed Native Subagent V2 capability surface from authoritative current-session evidence.
8. Keep any unavailable Host fact as `UNKNOWN`. Configured values, requested profile settings and model self-report do not become observed Host truth.
9. Record the fresh Host binding in Issue #91 before the first N0 or N1 child spawn.

The fresh Host binding and package/profile binding are separate evidence layers. Both are required for exact-candidate qualification.

## Next allowed sequence

Before every real Host action, read Issue #91 and record the preflight decision.

1. Bind the exact checkout, installed Plugin/package, fresh Codex Host build/version/platform and run/session identity to the current candidate.
2. Verify installed package/profile bytes against the current package-integrity manifest.
3. Record that binding in Issue #91 before any N0/N1 child spawn.
4. Apply the current N0 and revised N1 preflight.
5. Run the canonical managed-profile N1 once when authorized. Do not repeat the old generic recursion probe.
6. Continue N2-N8 only after revised N1 passes.
7. After N0-N8 pass, run the exact-candidate Advisor Final Review, installed-product/external evidence checks and human two-Skill App observation.
8. Keep publication blocked until every required gate passes.

## Maintenance rules

- One semantic fact gets one machine owner.
- Human documentation explains or links canonical owners. It does not become a second oracle.
- Tests protect behavior, schema, ownership, public interfaces and safety invariants. Avoid prose synchronization tests unless wording is itself an interface.
- A compatibility surface needs a real consumer and a removal condition.
- Preserve UNKNOWN handling, WriterLease settlement, Host identity/materialization evidence, managed-depth checks and strict read-only evidence when simplifying.
- Generate package-integrity data with repository tooling. Do not hand-copy hashes.
- Historical development chronology belongs in Git history or `docs/history/`, not in the active handoff.
