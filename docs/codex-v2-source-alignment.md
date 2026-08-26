# Codex Multi-Agent V2 Source Alignment

Research snapshot: OpenAI `openai/codex` `main` at commit `25a6e316c81fb7600d1d75f3e63ffe26be10b7c8` on 2026-08-26.

This note records upstream implementation facts that are relevant to the first public `subagents-dispatch` v1.0.0 Host qualification. It is source-alignment guidance, not a replacement for real-Host evidence from the exact Codex build under qualification.

## 1. `agent_path` is a canonical task path

V2 `spawn_agent` constructs a `SessionSource::SubAgent(ThreadSpawn)` with `thread_spawn_source(...)`. The resulting `agent_path` is derived from the parent session path plus the requested `task_name`. The root fallback is `AgentPath::root()`, so a root child named `worker` resolves to `/root/worker`.

The V2 handler then reads `spawn_source.get_agent_path()`, treats absence as an error, uses that path for inter-agent communication and activity events, and returns the path string as `task_name`.

Primary sources:

- https://github.com/openai/codex/blob/25a6e316c81fb7600d1d75f3e63ffe26be10b7c8/codex-rs/core/src/tools/handlers/multi_agents_v2/spawn.rs
- https://github.com/openai/codex/blob/25a6e316c81fb7600d1d75f3e63ffe26be10b7c8/codex-rs/core/src/tools/handlers/multi_agents_common.rs
- https://github.com/openai/codex/blob/25a6e316c81fb7600d1d75f3e63ffe26be10b7c8/codex-rs/core/src/tools/handlers/multi_agents_spec.rs

Implication for this repository: Host-produced `session_meta.agent_path` must be interpreted as the native task-path identity when it has the V2 canonical `/root/...` form. It must not be used as managed profile-file provenance.

`AgentPath::validate_agent_name` further constrains every non-root segment to lowercase ASCII letters, digits, and underscores, rejects the reserved segment `root`, and rejects `.` / `..` or embedded `/`. Runtime validation in this repository mirrors those canonical segment rules.

## 2. V2 spawn schema and fork semantics

The current V2 spawn arguments include `message`, `task_name`, optional `agent_type`, `model`, `reasoning_effort`, `service_tier`, `fork_turns`, and legacy `fork_context` only so the handler can reject it. `fork_context` is explicitly unsupported in V2. `fork_turns` accepts `none`, `all`, or a positive integer string and defaults to `all` when omitted.

Primary sources:

- https://github.com/openai/codex/blob/25a6e316c81fb7600d1d75f3e63ffe26be10b7c8/codex-rs/core/src/tools/handlers/multi_agents_v2/spawn.rs
- https://github.com/openai/codex/blob/25a6e316c81fb7600d1d75f3e63ffe26be10b7c8/codex-rs/core/src/tools/handlers/multi_agents_spec.rs

Implication for this repository: the first public release can continue requiring explicit `fork_turns=none` for fresh managed children. That is a stricter product policy layered on top of the Host's broader V2 capability.

## 3. V2 addresses agents by task path

The V2 tool descriptions use canonical task names for routing. `list_agents` returns the canonical task name when available, and target-bearing V2 tools resolve relative or canonical task paths in the current root-thread tree.

Primary sources:

- https://github.com/openai/codex/blob/25a6e316c81fb7600d1d75f3e63ffe26be10b7c8/codex-rs/core/src/tools/handlers/multi_agents_spec.rs
- https://github.com/openai/codex/blob/25a6e316c81fb7600d1d75f3e63ffe26be10b7c8/codex-rs/core/src/agent/control.rs

Implication for this repository: N2 materialization evidence should bind the canonical task path to exactly one child thread created after the authorized spawn cutoff. Thread id remains the concrete rollout identity; task path is the V2 native routing identity.

## 4. Upstream V2 does not make children leaf-only by default

Current Codex tool assembly enables collaboration tools for a V2 root. For a spawned child, collaboration tools are enabled when the child's effective model metadata reports `multi_agent_version == V2`.

The bundled V2 sub-agent usage guidance also explicitly says child agents can spawn their own sub-agents and have access to the same tool set.

Primary sources:

- https://github.com/openai/codex/blob/25a6e316c81fb7600d1d75f3e63ffe26be10b7c8/codex-rs/core/src/tools/spec_plan.rs
- https://github.com/openai/codex/blob/25a6e316c81fb7600d1d75f3e63ffe26be10b7c8/codex-rs/core/src/session/multi_agents.rs

Implication for this repository: `subagents-dispatch` leaf-only managed-child behavior is a product invariant that needs independent enforcement and real-Host verification. A V2 child route alone cannot prove containment. Profile declarations that are not applied by the Host cannot be treated as proof either.

## 5. Agent-control state is scoped to a root thread tree

Codex `AgentControl` is designed to be shared across the root and its descendants, with the live-agent registry scoped to that root-thread/session tree. V2 `list_agents` works against this tree and includes `/root` plus path-backed descendants when visible.

Primary source:

- https://github.com/openai/codex/blob/25a6e316c81fb7600d1d75f3e63ffe26be10b7c8/codex-rs/core/src/agent/control.rs

Implication for this repository: qualification evidence should keep root identity explicit and should not merge observations from unrelated root trees merely because task names match.

## 6. Boundary between upstream source facts and Host qualification

The source facts above describe current upstream Codex at one pinned commit. The release campaign still qualifies the actual installed Host build and its exact rollout behavior. When upstream source and the installed build differ, the observed Host behavior is the acceptance authority for that build, while the source comparison is supporting evidence and a diagnostic aid.

For the current campaign this means:

1. treat `agent_path` as V2 task identity;
2. keep profile-file provenance separate from runtime task identity;
3. use task-path plus time cutoff only to discover candidate child rollouts, then bind the exact child thread and parent;
4. keep N1 leaf containment as an explicit Host gate;
5. keep aggregate rollout statistics as supporting evidence only and fail closed when evidence needed by a gate is absent or ambiguous.
