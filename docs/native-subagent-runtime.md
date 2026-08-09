# Native Subagent Runtime Contract

subagents-dispatch uses Codex Native Subagents and child threads directly. It does not create another Agent runtime, persistent scheduler, daemon, thread pool, routing proxy, control server, or telemetry collector.

The distinction is deliberate:

| Native Codex | subagents-dispatch |
| --- | --- |
| runs the main session and child threads | decides whether delegation helps and which exact project role is useful |
| exposes whatever capacity/wait/update/control/runtime metadata the build supports | uses only observed capability without inventing a universal runtime contract |
| provides custom Agent configuration and sandbox/tool surfaces | adds one-writer, consent, trust, exact-role, and interaction-control boundaries |
| can expose native child status/control surfaces | maps explicit user Status/Steer/Takeover requests onto those surfaces when available |
| returns child output | verifies claims against the actual artifact and relevant evidence |

## Explicit entry point and control intents

Normal execution:

```text
/dispatch <task>
```

Explicit interaction controls:

```text
/dispatch preview <task>
/dispatch status
/dispatch steer <unit_id>: <guidance>
/dispatch takeover <unit_id>
```

Codex CLI/IDE users may also open the Skill picker with `/skills`. Implicit invocation is disabled. The user chooses when adaptive delegation or dispatch control is worth applying.

Preview does not touch the native child runtime. Status is a one-shot observation. Steer and Takeover use native child-control capability when the current Host exposes it. The Plugin does not emulate unavailable Host controls with a background controller.

## Native control boundary

Current Codex Subagents documentation exposes user-facing management of Agent threads, including inspecting Agents and asking Codex to steer, stop, or close child work. subagents-dispatch treats that native surface as the control primitive.

The Plugin adds semantic safety around it:

```text
Steer
-> same responsibility / attempt / role / authority

Takeover
-> request child stop when needed
-> prove old owner is no longer active
-> verify/preserve useful evidence
-> transfer responsibility to Main
```

For a writing child, Main remains read-only until the previous writer is confirmed stopped/terminal/closed. If native state cannot be established, it stays `UNKNOWN`. The Plugin does not claim a successful takeover or start conflicting mutation.

## First-use readiness

The exact project roles use Codex's native custom-Agent TOML mechanism. Personal custom Agents are stored under the active Codex home `agents` directory, normally `~/.codex/agents/`.

The current supported Host behavior loads custom-Agent role declarations into the task/session configuration when that task starts. A role file written after startup does not become a newly selectable `agent_type` for the already-running task merely because the TOML now exists on disk.

When an explicit `/dispatch` task actually needs a child, role readiness is checked before delegated implementation starts:

```text
exact required role already available
-> delegate normally

role unavailable + managed profiles cleanly absent
-> automatically provision only the five plugin-owned profiles + ownership manifest + installer lock
-> run installer --check
-> readiness outcome RESTART_REQUIRED
-> do not attempt spawn_agent in the current task
-> ask for one fresh Codex task/session and rerun the original /dispatch

role unavailable + managed profiles already exact
-> current task still cannot use the role
-> readiness outcome RESTART_REQUIRED
-> do not probe by spawning
-> retry from one fresh task/session

role unavailable + unsafe/conflicting/unowned managed state
-> USER_ACTION_REQUIRED
-> do not overwrite, substitute a role, or spawn
-> use /doctor for the exact diagnosis when useful
```

`RESTART_REQUIRED` is a pre-dispatch readiness outcome, not a native child lifecycle state. No child attempt exists yet. On the fresh task, exact role availability is checked again; if it still fails despite exact installed profiles, the condition is treated as a Host/configuration limitation and fails closed.

Routine first-use provisioning is bounded to the Plugin's fixed managed paths and is covered by the explicit `/dispatch` request once real delegation is already justified. It does not authorize `config.toml`, credentials, MCP configuration, repositories, unrelated Agent profiles, repair of unowned conflicts, migration, or upgrade changes.

Preview and Status do not provision missing profiles solely to make a read-only answer richer.

The installer is a project-specific lifecycle and ownership layer around native custom Agent files; it is not a second runtime.

## Current exact roles

```text
subagents_dispatch_reader        -> gpt-5.6-luna  / max   / read-only
subagents_dispatch_worker        -> gpt-5.6-luna  / max   / workspace-write
subagents_dispatch_solver        -> gpt-5.6-sol   / high  / workspace-write
subagents_dispatch_investigator  -> gpt-5.6-terra / xhigh / read-only
subagents_dispatch_advisor       -> gpt-5.6-sol   / high  / read-only
```

Responsibility semantics follow the current model guidance:

```text
Luna Reader/Worker
-> clear, repeatable, bounded work

Terra Investigator
-> bounded read-heavy technical investigation / evidence synthesis after semantics stabilize

Sol Advisor/Solver
-> demanding, ambiguous, multi-step material judgment and judgment-coupled implementation
```

Terra is an investigation lane rather than an automatic escalation destination. A difficult technical problem that still requires demanding or material judgment belongs on the Sol path.

Model-specific delegation requires the exact current profile. There is no built-in-role substitution or hidden model ladder.

Profile matching proves configuration intent only. It does not prove the route a live child actually ran.

## Main-session capability dedup

Main-session route evidence is optional optimization data.

Only when the router has already established that material judgment needs Sol capability may trusted current-session model/effort metadata be used to avoid a redundant Advisor/Solver call.

`policy-contract.json` owns the capability reference. `scripts/runtime-evidence.py` normalizes observed metadata.

Current reference is Solver, GPT-5.6 Sol `high`:

```text
Sol family + high/xhigh/max
-> covered

Sol family + medium/low
-> uncovered

other model family
-> uncovered

missing / partial / local-only / conflicted / unranked effort
-> unknown
```

Routine bounded work does not inspect main-session metadata. `unknown` is allowed to remain unknown.

A covered main session can suppress ordinary Sol capability uplift. It cannot satisfy fresh independent review of its own final candidate.

## Runtime evidence is diagnostic

The helper supports:

```text
subject: main_session
subject: child
```

For child diagnostics it keeps route, ancestry, and permission evidence separate:

```text
route_evidence
ancestry_evidence
permission_evidence
```

Use runtime diagnostics when the claim actually depends on runtime observation, including:

- exact model/role/effort proof;
- hard host-enforced read-only;
- main capability dedup;
- ancestry when depth-one proof matters;
- independent-review provenance;
- configuration/runtime conflicts;
- release validation.

Do not run these checks as routine ceremony for every bounded child. Exact profile configuration plus real artifact verification may be sufficient when runtime route proof is not part of acceptance.

Configured values never become observed values by assumption. Execution Receipts follow this same rule.

## Token and usage boundary

Codex App Server can expose thread token-usage update events to clients. That is a Host/client API surface and is not assumed to be available inside this Skill execution path.

Therefore subagents-dispatch 2.1 does not add a private App Server client, hook-based telemetry collector, transcript scraper, or token estimator.

```text
attributable exact Host usage available
-> may report exact usage when useful

usage surface unavailable to the Skill
-> usage remains unavailable
```

Currency cost is also left unreported unless a future supported surface supplies exact attributable billing semantics. Model name, output length, and elapsed time are insufficient evidence.

## Completion and wait surface

The desired scheduling behavior is completion-driven when the native runtime exposes a usable completion surface.

For release-relevant builds characterize the strongest actually observed surface:

```text
barrier_only
per_child_terminal
any_child_update
```

These are observed runtime labels, not permanent Codex constants.

Example:

```text
A slow independent read-only task
B fast independent read-only task
C depends only on B

spawn A + B
B completes
-> process B
-> start C while A remains active only if the runtime exposes B completion and reusable capacity
```

If the runtime exposes only a barrier, subagents-dispatch degrades to that surface. It does not simulate event-driven behavior with model-mediated busy polling.

Child progress observability is separate:

```text
none
terminal_only
periodic_summary
structured_live
```

A wake-up event does not imply deterministic insight into child progress.

`/dispatch status` reads the best current evidence once and returns. It does not turn this completion surface into a private poll loop.

## Capacity

subagents-dispatch has no project-level ordinary numeric child ceiling and no target Agent count.

The main session chooses the active set from responsibilities that are ready, distinct, non-duplicative, worth delegating, and safe to run now. It may use several child Agents when a task contains several independent valuable lanes. It may use none when delegation adds no value.

Actual active concurrency remains bounded by:

```text
useful independent ready work
writer safety
exact role availability
user scope and compute consent
native runtime capacity
```

The Host capacity is treated as an upper bound, never a target to fill. A single observed or configured capacity value applies only to that runtime/environment.

Material compute expansion is governed by `skills/dispatch/references/guardrails.md`. Child count alone is not the trigger.

## Writer ownership

One canonical physical checkout has one active writing actor inside the current orchestration:

```text
main session while mutating
subagents_dispatch_worker
subagents_dispatch_solver
```

When a child writer owns the checkout, Main can continue read-only analysis but waits for ownership handoff before integration writes.

Takeover follows the same boundary. A stop request is an action request; Main waits for evidence that the old writer is actually no longer active before writing.

Concurrent writers require genuine filesystem isolation such as separate worktrees/workspaces/repositories plus semantic independence or explicit dependency/integration order.

This session-local rule cannot exclude another Codex session, editor, hook, or external process. Current safety relies on recommended isolation plus drift detection and fail-closed behavior. Cross-session coordination must be validated empirically before a stronger mechanism is claimed.

## Context transfer

Children normally use fresh context (`fork_turns=none`) and receive a compact responsibility packet from `skills/dispatch/references/router-core.md`.

Fresh context does not require repeated discovery. When Main has already verified material evidence that a later responsibility can reuse, it may add a Handoff Capsule from `skills/dispatch/references/handoff-capsule.md`:

```text
artifact refs
accepted facts/evidence
interfaces/invariants
DO NOT REDO
open questions
staleness conditions
```

The capsule contains distilled accepted task truth. It excludes private reasoning, raw transcripts, copied source files, and unverified child claims. Relevant drift invalidates affected facts until narrow re-verification.

## Delegation depth

```text
main session -> child
child -> no further project delegation
```

Unexpected descendants are outside the supported product contract.

## Lifecycle

Process completed/no-longer-needed children promptly and close them when the native surface supports it so capacity can recover.

If a runtime shows stale slots, blocking close operations, missing completion signals, absent route metadata, unresolved stop state, or other limitations, record the exact build and adapt product claims. Do not hide runtime limitations behind policy wording.

## User-facing takeaway

subagents-dispatch lets the main session lead a specialist team whose size follows the task. The user can preview the likely delegation, inspect or steer active responsibilities, and safely take work back into Main. Reusable context stays small and evidence-bound.

Native Codex still owns thread execution, custom-Agent registration timing, and native control. subagents-dispatch handles the first-use registration boundary by provisioning cleanly missing plugin-owned profiles, returning `RESTART_REQUIRED`, and continuing only from a fresh task/session instead of attempting a known-stale spawn.
