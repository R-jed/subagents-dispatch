<p align="center">
  <img src="assets/subagents-dispatch-banner.png" alt="subagents-dispatch" width="900">
</p>

<h1 align="center">subagents-dispatch</h1>

<p align="center"><em>Give Codex a reliable team. Split the big jobs. Leave the tiny ones alone.</em></p>

<p align="center">
  <a href="README.md">中文</a> · <a href="docs/plugin-installation.md">Install</a> · <a href="docs/architecture.md">Architecture</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Codex-Native%20Subagents-111827.svg" alt="Codex Native Subagents">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License"></a>
</p>

> **If you are an AI Agent, use [README_AI.md](README_AI.md).**

Give Codex a medium-sized task: change an API, add tests, trace the call path, then check whether the frontend is affected.

One Main can do all of that. As the task grows, reading, investigation, editing, testing, and review all compete for the same context.

**subagents-dispatch gives Codex a temporary team when splitting the work is useful.**

Main keeps the user goal, the judgment, integration, and the final answer. Small tasks can use zero subagents.

## Codex already has Subagents. Why use this Plugin?

Codex provides Native Subagents. This Plugin adds an engineering coordination policy around them.

It decides when delegation is worth the overhead, turns work into responsibilities with dependencies and done conditions, limits pointless fan-out, prevents managed writers from colliding in one mutable workspace, and requires Main to accept evidence before dependent work unlocks. When Host state is unclear, it preserves `UNKNOWN` instead of turning a guess into authority.

## Understand it in 30 seconds

Suppose you ask:

```text
Add pagination to /api/users, add tests, and check whether the frontend callers are affected.
```

A sensible run might look like this:

```text
Main
├─ read the API, tests, and call path
├─ inspect frontend and cross-file impact in parallel
├─ hand off a bounded implementation once the shape is clear
└─ add an independent review when the change deserves one
```

Main gathers the results, checks the evidence, integrates the change, and decides whether the job is actually done.

If Main can finish the task directly, it does.

## When it helps

Typical examples include:

- tracing several call paths at once
- investigating before implementation
- changes spanning frontend, backend, configuration, tests, or docs
- handing one clearly bounded responsibility to another subagent
- getting an independent review for a change with meaningful impact

For tiny, strongly sequential tasks with all the context already available, Main is usually simpler.

## Two things to remember

| Entry | Use it for |
|---|---|
| **Orchestrate** | deciding whether to delegate, then planning, execution, continuation, correction, takeover, review, and integration |
| **Doctor** | checking Plugin health, Agent configuration, Host integration, runtime state, and explicitly requested safe maintenance |

Orchestrate can also show a plan without starting delegated work. Status, pause, takeover, and continuation stay in the same entrypoint.

## Deliberately bounded

- small tasks may use zero subagents
- at most 4 managed subagents; 4 is a safety ceiling
- only one managed writer may mutate the same workspace at a time
- each subagent gets only the context needed for its responsibility
- investigation results need evidence before Main accepts them
- unclear state blocks progress
- Main remains responsible for the final result

The current product manages one canonical workspace. See [Writer Boundary](docs/writer-boundary.md).

## Current fixed team

The five managed profiles keep separate responsibilities and authority boundaries, while the current release candidate pins every managed child to **Luna Max**:

| Work | Model | Good at |
|---|---|---|
| Reading | Luna Max | focused code reading and call-path tracing |
| Implementation | Luna Max | bounded changes once the approach is clear |
| Investigation | Luna Max | broad read-only investigation and cross-file evidence |
| Problem solving | Luna Max | implementation within explicitly granted decision rights |
| Review | Luna Max | independent review of plans and final results |

This is a containment constraint for the current Host family. Formal Real Host N1 testing showed that a MultiAgent V2-capable child can create a grandchild and that `agents.max_depth=1` does not block that V2 path. The currently qualified Host metadata reports Luna as V1, so a managed Luna child does not receive that V2 collaboration surface.

Main itself may still use other Host models. If Host model metadata or descendant-containment behavior changes, the managed lineup must be requalified before the Plugin relies on it. The profile instruction against further subagent creation remains defense in depth and is never treated as Host containment proof.

## Install

Install through the Codex Plugin Marketplace:

```bash
codex plugin marketplace add R-jed/subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

Start a fresh Codex session after installation and choose **Orchestrate** from the Skill menu.

The first delegated task checks the five managed Agent profiles. If they are safely absent, the Plugin creates only the files it owns. Current V4 has no authoritative observation from an already-running task proving that newly written custom-Agent profiles have entered that task's Agent registry, so that task conservatively returns `RESTART_REQUIRED`. Start one fresh Codex task and submit the original request again.

If you want the first real development task to avoid that initialization interruption, use **Doctor** once after installation and explicitly ask it to repair or prepare the managed Agent profiles, then start a fresh work session. The bundled helpers require Python 3.11 or newer.

See [Plugin Installation](docs/plugin-installation.md) for the full setup.

Update:

```bash
codex plugin marketplace upgrade subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

Before uninstalling, use **Doctor** to remove only Agent profiles that can be proven to belong to this Plugin, then remove the Plugin and Marketplace source.

## Will it make Codex faster?

Sometimes, especially when investigation can happen in parallel or the Main context would otherwise get crowded.

More agents do not automatically mean more speed. Product evaluation looks at correctness and safety first, then rework, coordination burden, context efficiency, latency, and tokens. See [Product Success Criteria](docs/product-success.md).

Technical details:

[Architecture](docs/architecture.md) · [Installation](docs/plugin-installation.md) · [Writer Boundary](docs/writer-boundary.md) · [Product Success Criteria](docs/product-success.md) · [Runtime Evidence](docs/runtime-attestation.md) · [Experiment Protocol](docs/experiment-protocol.md) · [Changelog](CHANGELOG.md) · [AI Reference](README_AI.md)

## License

[MIT](LICENSE)
