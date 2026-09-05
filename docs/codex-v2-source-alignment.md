# Codex Multi-Agent V2 Source Alignment

Research snapshot: OpenAI `openai/codex` `main` at commit `25a6e316c81fb7600d1d75f3e63ffe26be10b7c8` on 2026-08-26.

This note records upstream implementation facts relevant to the first public `subagents-dispatch` v1.0.0 Native Host boundary. Release qualification now uses `docs/v4/host-reference.json`, which pins mature `sol-advisor` and `astra-advisor` integration patterns; this source snapshot remains supporting implementation context rather than a second release gate.

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

Implication for this repository: runtime reconciliation treats the canonical task path as the V2 native routing identity and keeps any concrete Host thread identity distinct when the Host exposes it.

## 4. Upstream V2 does not make children leaf-only by default

Current Codex tool assembly enables collaboration tools for a V2 root. For a spawned child, collaboration tools are enabled when the child's effective model metadata reports `multi_agent_version == V2`.

The bundled V2 sub-agent usage guidance also explicitly says child agents can spawn their own sub-agents and have access to the same tool set.

Primary sources:

- https://github.com/openai/codex/blob/25a6e316c81fb7600d1d75f3e63ffe26be10b7c8/codex-rs/core/src/tools/spec_plan.rs
- https://github.com/openai/codex/blob/25a6e316c81fb7600d1d75f3e63ffe26be10b7c8/codex-rs/core/src/session/multi_agents.rs

Implication for this repository: `subagents-dispatch` leaf-only managed-child behavior is a semantic product invariant. A V2 child route alone cannot prove Host-hard containment, and profile declarations cannot be treated as such proof. If a task specifically requires Host-hard isolation, direct current-Host evidence is required for that stronger claim.

## 5. Agent-control state is scoped to a root thread tree

Codex `AgentControl` is designed to be shared across the root and its descendants, with the live-agent registry scoped to that root-thread/session tree. V2 `list_agents` works against this tree and includes `/root` plus path-backed descendants when visible.

Primary source:

- https://github.com/openai/codex/blob/25a6e316c81fb7600d1d75f3e63ffe26be10b7c8/codex-rs/core/src/agent/control.rs

Implication for this repository: runtime evidence should keep root identity explicit and should not merge observations from unrelated root trees merely because task names match.

## 6. Boundary between source/reference facts and runtime truth

The source facts above and the two mature projects pinned by `docs/v4/host-reference.json` establish the design basis for using Native Codex controls. They do not prove that a particular installed Host exposes every model, effort or observation.

The current runtime rules therefore remain:

1. treat `agent_path` as V2 task identity when it has the canonical form;
2. keep profile/configuration intent separate from observed runtime identity;
3. use the current callable Host schema as authority for available controls;
4. keep requested, accepted and observed route facts separate;
5. fail the affected delegation/review closed when a required Host fact is missing, conflicting or unobservable.
