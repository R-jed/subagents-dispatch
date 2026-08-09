# Native Subagent Runtime Contract

subagents-dispatch uses Codex Native Subagents and child threads directly. It does not create another Agent runtime, persistent scheduler, daemon, thread pool, routing proxy, control server, or telemetry collector.

| Native Codex | subagents-dispatch |
| --- | --- |
| runs the main session and child threads | decides whether delegation helps and which exact project role is useful |
| exposes available capacity/wait/update/control/runtime metadata | uses only observed capability without inventing a universal runtime contract |
| provides custom Agent configuration and sandbox/tool surfaces | adds one-writer, consent, trust, exact-role, and interaction-control boundaries |
| returns child output | verifies claims against actual artifacts and evidence |

## Explicit Skill entry point and controls

The Plugin registers bundled Skills. Explicit use is:

```text
$dispatch <task>
$dispatch preview <task>
$dispatch status
$dispatch steer <unit_id>: <guidance>
$dispatch takeover <unit_id>

$doctor <diagnostic or maintenance request>
```

Codex users may also open `/skills` and choose **Dispatch** or **Doctor**. Bare `/dispatch`, `/doctor`, and legacy namespaced slash identities are not the supported Plugin entrypoint. Implicit invocation is disabled.

Preview does not touch the native child runtime. Status is one-shot observation. Steer and Takeover use native child-control capability when the current Host exposes it. The Plugin does not emulate unavailable controls with a background controller.

## Native control boundary

Steer keeps the same responsibility, attempt, role, and authority. Takeover requests child stop when needed, proves the old owner is no longer active, verifies usable evidence, and only then transfers responsibility to Main.

For a writing child, Main remains read-only until the previous writer is confirmed stopped/terminal/closed. If native state cannot be established, it stays `UNKNOWN`.

## First-use readiness

The exact project roles use Codex's native custom-Agent TOML mechanism. The supported Host loads custom-Agent declarations into task/session configuration when that task starts. A role file written after startup does not become newly selectable merely because TOML now exists on disk.

When an explicit `$dispatch` task actually needs a child:

```text
exact required role already available
-> delegate normally

role unavailable + managed profiles cleanly absent
-> automatically provision only the five plugin-owned profiles + ownership manifest + installer lock
-> run installer --check
-> RESTART_REQUIRED
-> 0 spawn_agent attempts in the current task
-> ask for one fresh task/session and rerun the original $dispatch

role unavailable + managed profiles already exact
-> RESTART_REQUIRED
-> do not probe by spawning

role unavailable + unsafe/conflicting/unowned managed state
-> USER_ACTION_REQUIRED
-> do not overwrite, substitute a role, or spawn
-> use $doctor for exact diagnosis when useful
```

`RESTART_REQUIRED` is a pre-dispatch readiness outcome, not a native child lifecycle state. No child attempt exists yet.

## Current exact roles

```text
subagents_dispatch_reader        -> gpt-5.6-luna  / max   / read-only
subagents_dispatch_worker        -> gpt-5.6-luna  / max   / workspace-write
subagents_dispatch_solver        -> gpt-5.6-sol   / high  / workspace-write
subagents_dispatch_investigator  -> gpt-5.6-terra / xhigh / read-only
subagents_dispatch_advisor       -> gpt-5.6-sol   / high  / read-only
```

Terra is an investigation lane rather than an automatic escalation destination. Model-specific delegation requires the exact current profile. Profile matching proves configuration intent only; it does not prove the route a live child actually ran.

## Main-session capability dedup

Main-session route evidence is optional optimization data. Only when material judgment already requires Sol capability may trusted current-session model/effort metadata avoid a redundant Advisor/Solver call. Missing/partial/conflicted telemetry remains unknown. A capable Main cannot satisfy fresh independent review of its own candidate.

## Runtime evidence is diagnostic

`scripts/runtime-evidence.py` supports `subject: main_session` and `subject: child`. For child diagnostics it keeps:

```text
route_evidence
ancestry_evidence
permission_evidence
```

separate.

Use runtime diagnostics when a claim actually depends on runtime observation, such as exact route/model/effort proof, hard host-enforced read-only, main capability dedup, ancestry, independent-review provenance, configuration/runtime conflict, or release validation.

Do not run these checks as routine ceremony for every bounded child. Configured values never become observed values by assumption.

## Token and usage boundary

When attributable exact Host usage is available, it may be reported. Otherwise usage stays unavailable. The Plugin does not add a private App Server client, hook-based telemetry collector, transcript scraper, or token estimator. Currency cost is also unreported without exact attributable billing semantics.

## Completion and wait surface

Characterize only what the current Host actually exposes:

```text
barrier_only
per_child_terminal
any_child_update
```

The Plugin degrades to the observed native surface and does not simulate event-driven behavior with model-mediated busy polling. Child progress observability is separate and may be `none`, `terminal_only`, `periodic_summary`, or `structured_live`.

`$dispatch status` reads the best current evidence once and returns.

## Capacity

subagents-dispatch has no project-level ordinary numeric child ceiling and no target Agent count. Active concurrency is bounded by useful independent ready work, writer safety, exact role availability, user scope/compute consent, and native runtime capacity.

## Writer ownership

One canonical physical checkout has one active writing actor inside the current orchestration:

```text
main session while mutating
subagents_dispatch_worker
subagents_dispatch_solver
```

Takeover does not weaken this boundary. A stop request is an action request; Main waits for evidence that the old writer is actually no longer active before writing.

## Context transfer

Children normally use fresh context (`fork_turns=none`) and receive a compact responsibility packet. Handoff Capsules may pass Main-accepted evidence, interfaces/invariants, `DO NOT REDO`, open questions, and `STALE IF` conditions. They exclude raw transcripts and unverified child claims.

## Delegation depth

```text
main session -> child
child -> no further project delegation
```

Unexpected descendants are outside the supported product contract.

## Lifecycle

Process completed/no-longer-needed children promptly and close them when the native surface supports it so capacity can recover. If the runtime exposes stale slots, missing completion signals, absent route metadata, unresolved stop state, or other limitations, record the exact build and adapt product claims.

## User-facing takeaway

The installed Plugin is discovered through the Codex Skill registry. Users explicitly select **Dispatch** or **Doctor** from `/skills`, or invoke `$dispatch` / `$doctor`. Native Codex owns thread execution, custom-Agent registration timing, and native child control; subagents-dispatch owns delegation policy, evidence acceptance, and safety around those primitives.
