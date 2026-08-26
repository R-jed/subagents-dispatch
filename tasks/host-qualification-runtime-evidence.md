# Real Host runtime evidence helpers

This note defines the maintainer-only rollout evidence path used by the real Host qualification campaign. The machine acceptance authority remains `docs/v4/host-smoke.json`. This helper does not add a new N0 through N8 requirement and is intentionally absent from `.codex-plugin/package-integrity.json`.

Use `scripts/host_qualification_evidence.py` only when the required fact is observable from the local Host-produced Codex rollout. Public Host metadata remains authoritative when it exposes the same fact; conflicting public and local evidence fails closed.

The V2 task-path interpretation used here is source-aligned in `docs/codex-v2-source-alignment.md`. `session_meta.agent_path` is a canonical Host task address. It must never be used as profile-file provenance.

## Evidence boundary

The helper may emit only compact Host facts needed for qualification. It must not emit prompts, assignment text, assistant output, reasoning, environment values, source contents, developer instructions, or raw tool payloads.

Missing or ambiguous evidence stays unavailable. Do not convert an unavailable token counter, tool name, permission field, sandbox field, timestamp, or identity into a zero/default value.

The helper is supporting qualification tooling. It does not select models, authorize a spawn, mutate Host state, restart the Desktop Host, create a root task, or replace the exact-turn V2 capability gate.

## H0 root observation

Use the `primary` mode after the operator has already created the current root task:

```text
python3 scripts/host_qualification_evidence.py \
  --sessions-dir "$HOME/.codex/sessions" \
  primary <current-root-thread-id>
```

The mode requires an exact root rollout, exactly one `session_meta`, no `parent_thread_id`, no managed `agent_role`, and an authoritative `session_id`. It selects the latest timestamped `turn_context` and may report its model, effort, provider, cwd, `multi_agent_version`, and runtime version.

This latest-turn route information is H0 supporting evidence only. H0 still binds the environment fields required by the machine contract. N0 and later Agent-control phases must establish V2 again on the exact covered turn.

Configured defaults and historical/user-attested model values do not replace current rollout evidence.

## N2 task address to child identity

When native spawn returns the canonical `/root/<task>` address but the caller does not receive a child UUID, record a UTC cutoff immediately before the spawn. After successful materialization, resolve the child with:

```text
python3 scripts/host_qualification_evidence.py \
  --sessions-dir "$HOME/.codex/sessions" \
  resolve-child \
  --agent-path /root/<canonical-task-address> \
  --since <spawn-cutoff-rfc3339> \
  --expected-parent-thread-id <root-thread-id> \
  --expected-agent-role <exact-managed-agent-type>
```

Only `session_meta.agent_path` is eligible for the match. Task-address text found in prompts, reasoning, messages, results, or other payloads is ignored.

For managed qualification children, the resolver accepts exactly one direct `/root/<task>` segment using the same lowercase-letter/digit/underscore segment rules as upstream `AgentPath`, with `root` reserved. Nested paths remain valid upstream V2 identities in general, but are rejected here because this resolver is for product-managed leaf children.

A matching rollout must be at or after the cutoff, have the expected parent and managed role when supplied, and resolve to exactly one child. Zero or multiple matches are `UNKNOWN`, never a "latest match" heuristic.

The resolved child UUID plus the canonical Host task address supplies the external identity binding required by N2. It does not replace ExecutionBinding evidence or lifecycle settlement.

## N1, N4, and N7 aggregate observation

Use `aggregate` for privacy-safe activity evidence on an exact rollout:

```text
python3 scripts/host_qualification_evidence.py \
  --sessions-dir "$HOME/.codex/sessions" \
  aggregate <child-thread-id> \
  --expected-parent-thread-id <root-thread-id> \
  --expected-agent-role <exact-managed-agent-type>
```

The output may contain:

- exact child/root identity and managed role;
- observed model and effort;
- sandbox and permission types when the Host exposed them;
- turn count;
- tool-call count;
- count and names of recognized Agent-control calls;
- context-compaction count;
- cumulative raw-token count when every observed token-count record is complete;
- latest event timestamp when all inspected event timestamps are complete.

Recognized current Agent-control names are `spawn_agent`, `followup_task`, `interrupt_agent`, and `list_agents`. Namespaced forms are normalized to their final tool name.

Current upstream Codex V2 can expose collaboration tools to a spawned child when that child's effective model metadata enables V2. Therefore a zero recognized-call count is supporting evidence only. N1 still needs authoritative evidence that the managed child did not create or control descendants and that no descendant materialized.

If a tool call is observable but its name is unavailable, `agent_control_call_count` is unavailable. Do not report zero. This aggregate count is supporting evidence for N1/N4/N7. It cannot by itself prove the absence of a future Host Agent-control primitive that is not in the current allowlist. N1 still requires authoritative Host activity or rollout evidence covering the actual callable Agent-control surface for the tested child.

If a `token_count` event exists but its cumulative total is absent or malformed, `raw_tokens` is unavailable. Do not report zero. Token usage is diagnostic only and is not a release gate unless a future machine contract explicitly makes it one.

Missing sandbox or permission evidence remains unavailable. A missing sandbox must never be interpreted as writable. N8 continues to apply its stricter effective read-only requirement through the canonical machine contract and runtime-evidence permission logic.

## Stale and ambiguous evidence

All three modes fail closed on ambiguous identity. Evidence from an older rollout with the same role, task address, model, or effort cannot satisfy a fresh-child identity requirement.

The task-address resolver uses the spawn cutoff to exclude older reuse. The exact UUID modes bind the rollout filename and `session_meta.id`. Expected parent and role should be supplied whenever the probe knows them.

If public Host metadata and local rollout evidence disagree, quarantine the result and stop. Do not choose whichever source is more convenient.

## Host lifecycle boundary

These commands run only inside a live Codex task. If obtaining fresh evidence requires quitting or restarting the Desktop Host or creating a replacement root task, stop with `OPERATOR_ACTION_REQUIRED_STOP`. The operator performs that lifecycle action outside the terminating task, then the new/current root collects evidence.
