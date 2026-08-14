---
name: dispatch
description: Start or resume value-driven orchestration with Codex Native Subagents while preserving user authority, runtime truth, one-writer safety, and evidence-bound completion.
---

# Dispatch

Use this Skill to start a new orchestration when none is active, or to resume the current orchestration when explicitly invoked without a new task. Resume the bound unit/task/attempt/Agent/role/responsibility/authority; do not create a duplicate child, retry, follow-up, work pass, or rework. If active unresolved ownership exists, do not silently create a second unrelated top-level orchestration in the same root thread.

Load the canonical contracts required by the task:

- `../../contracts/policy.json`: hard machine-readable invariants and five route definitions
- `../../contracts/routing.md`: delegation value, role selection, responsibility compilation, and adaptive ready work
- `../../contracts/composition.md`: Host/project-rule/external-Skill/hook/role-contract composition when those surfaces participate
- `../../contracts/guardrails.md`: authority, trust, mutation boundaries, and writer coordination
- `../../contracts/state.md`: ephemeral root-thread continuity and Host reconciliation
- `../../contracts/team-plan.md`: multi-responsibility identity, dependencies, ownership, and revisions
- `../../contracts/recovery.md`: attempt lifecycle, bounded recovery, `UNKNOWN`, and `INTERRUPTED`
- `../../contracts/handoff.md`: compact Main-accepted evidence transfer
- `../../contracts/evidence-artifact.md`: references-first evidence bundle only when inline evidence would be materially duplicated or oversized
- `../../contracts/final-review.md`: consequence-driven exact-candidate review
- `../../contracts/receipt.md`: terminal orchestration accounting and presentation

Before every new project-child spawn, bind the selected semantic role to the exact production `agent_type` from the current `../../contracts/policy.json`. Use `roles.<semantic-role>.agent_type` verbatim in the pending Host call. Do not choose an `agent_type` from Host-discovered role names, prior memory, built-in roles, unrelated installed custom Agents, legacy aliases, similarly named roles, or model-equivalent profiles. Unrelated Agent suites may coexist in the same Codex home and are never substitutions for a subagents-dispatch production role. Inspect the pending spawn before invocation and require both the exact policy-owned `agent_type` and `fork_turns: none`. If the exact role is unavailable, follow first-use readiness and fail closed. A successful spawn of any different role is a routing failure, not a fallback path.

When managed-profile readiness requires a bundled Python helper, follow `../../docs/python-runtime.md`. Resolve one Python 3.11+ interpreter from the actual task environment and use that same resolved interpreter for the helper operation. Interpreter command-name resolution is environment adaptation; it does not authorize role, model, Agent-type, permission-evidence, or acceptance substitution. If no supported interpreter is available, stop before child spawn and report the prerequisite failure.

Delegate only when a distinct responsibility adds enough value to justify coordination cost. There is no child minimum or ordinary project-level child maximum; native Host capacity is only a ceiling. Keep delegation depth at one.

Main retains the user's goal, authorization, team composition, integration, acceptance, and final response. Before conflicting writes, preserve semantic `single_writer` coordination for the canonical workspace. Treat configured, accepted, and observed route facts as different evidence levels. Preserve an accepted upstream workflow or external Skill's domain semantics and apply Dispatch only as an orchestration layer; role contracts may narrow authority but never widen it.

Keep child returns compact. Prefer inspectable refs over copied logs/source, and materialize an Evidence Artifact only when complete accepted provenance should stay out of conversational context. A child result or child-created artifact-shaped claim is not accepted task truth until Main verifies it.

When the orchestration reaches a stable return boundary, produce the Dispatch Receipt defined by `../../contracts/receipt.md`. Do not invent App slash syntax or Host facts.