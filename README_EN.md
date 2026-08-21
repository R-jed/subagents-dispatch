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

One Main can do all of that. But as the task grows, reading, investigating, editing, testing, and reviewing all pile into the same context. Eventually the context starts to look like rush hour.

**subagents-dispatch gives Codex a temporary team when splitting the work is actually useful.**

One subagent can read the code. Another can investigate wider impact. Another can implement a well-bounded change. Main keeps the goal, the judgment, and the final answer.

Small task? Use zero subagents. Spinning up a committee just to look busy is not a feature.

## Codex already has Subagents. Why use this Plugin?

Codex provides Native Subagents. This Plugin adds an engineering coordination policy around them.

It decides when delegation is worth the overhead, turns work into responsibilities with dependencies and done conditions, limits pointless fan-out, prevents managed writers from colliding in one mutable workspace, and requires Main to accept evidence before dependent work unlocks. When Host state is unclear, it preserves `UNKNOWN` instead of turning a guess into authority.

The useful distinction is therefore not whether another Agent can be spawned. It is whether a complex engineering task can be split cleanly, run with controlled parallelism, brought back together safely, and still end with one accountable owner.

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

If Main looks at the task and realizes it can finish it in three minutes, Main just does it.

## When it helps

subagents-dispatch is most useful when a task has work that can be investigated separately, or when implementation should wait until the impact is understood.

Typical examples:

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

For normal work, use **Orchestrate**. If the environment looks suspicious, call **Doctor**.

Orchestrate can show a plan without starting delegated work. You can simply say:

```text
Show me how you would split this work first.
```

During a run, natural control requests can stay in the same Skill:

```text
What is the current status?
Pause U2.
I will take over this part.
Continue the interrupted work.
```

There is no need to remember a row of separate control Skills.

## It tries not to become a group chat

Multi-agent systems can turn parallel work into coordination overhead very quickly. This project keeps a few deliberately boring rules:

- small tasks may use zero subagents
- start with at most 2 managed subagents, normally no more than 3
- only one managed writer may mutate the same workspace at a time
- each subagent gets only the context needed for its responsibility
- investigation results need evidence before Main accepts them
- unclear state stops progress instead of becoming permission by guesswork
- Main remains responsible for the final result

Single-writer is a workspace boundary. A future Host that can reliably isolate writers into separate worktrees or workspaces could support multiple independent writer domains when the work is also semantically independent. The current product manages one canonical workspace, so one writer remains the safer default. See [Writer Boundary](docs/writer-boundary.md).

## Current fixed team

| Work | Model | Good at |
|---|---|---|
| Reading | Luna Max | focused code reading and call-path tracing |
| Implementation | Luna Max | bounded changes once the approach is clear |
| Investigation | Terra XHigh | broad read-only investigation and cross-file evidence |
| Problem solving | Sol High | implementation that needs substantial technical judgment |
| Review | Sol High | independent review of plans and final results |

The lineup is fixed for now. There is no dynamic model or reasoning-effort switching. Fixed behavior is easier to understand and reproduce; if real evidence later supports a better combination, it can change then.

## Install

Install through the Codex Plugin Marketplace:

```bash
codex plugin marketplace add R-jed/subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

Start a fresh Codex session after installation and choose **Orchestrate** from the Skill menu.

The first delegated task checks the five managed Agent profiles. If they are safely absent, the Plugin creates only the files it owns. Current V4 has no authoritative observation from an already-running task that proves newly written custom-Agent profiles have entered that task's Agent registry, so that task conservatively returns `RESTART_REQUIRED` and never substitutes another Agent. Start one fresh Codex task and submit the original request again. This activation step occurs only when managed profiles are first created or need to be reactivated.

If you want the first real development task to avoid that initialization interruption, use **Doctor** once after installation and explicitly ask it to repair or prepare the managed Agent profiles, then start a fresh work session. The bundled helpers require Python 3.11 or newer.

See [Plugin Installation](docs/plugin-installation.md) for the full setup.

Update:

```bash
codex plugin marketplace upgrade subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

Before uninstalling, use **Doctor** to remove only Agent profiles that can be proven to belong to this Plugin. Then remove the Plugin and Marketplace source:

```bash
codex plugin remove subagents-dispatch@subagents-dispatch
codex plugin marketplace remove subagents-dispatch
```

If Doctor says ownership is unclear, resolve the conflict first. Do not silence the warning by deleting files manually.

## Will it make Codex faster?

Sometimes, especially when investigation can happen in parallel or the Main context would otherwise get crowded.

More agents do not automatically mean more speed. Small tasks can get slower, and coordination has a cost. The project has an experiment protocol for measuring correctness, rework, user intervention, time, and token usage before making performance claims.

This README does not advertise unproven speedups or token savings. Product evaluation looks at correctness and safety first, then rework, coordination burden, context efficiency, latency, and tokens. See [Product Success Criteria](docs/product-success.md).

The more important question is whether a complicated job can be split cleanly, brought back together safely, and still have one place where responsibility ends.

For technical details:

[Architecture](docs/architecture.md) · [Installation](docs/plugin-installation.md) · [Writer Boundary](docs/writer-boundary.md) · [Product Success Criteria](docs/product-success.md) · [Runtime Evidence](docs/runtime-attestation.md) · [Experiment Protocol](docs/experiment-protocol.md) · [Changelog](CHANGELOG.md) · [AI Reference](README_AI.md)

## License

[MIT](LICENSE)
