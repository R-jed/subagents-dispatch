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

subagents-dispatch is most useful when a task has work that can be investigated separately, or when the implementation should wait until the impact is understood.

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
| **Orchestrate** | planning, delegation, execution, continuation, correction, takeover, review, and integration |
| **Doctor** | checking installation, configuration, versions, and the runtime environment |

For normal work, use **Orchestrate**. If the environment looks suspicious, call **Doctor**.

Orchestrate can also show a plan without starting delegated work, so you can inspect the proposed split before anything runs.

## It tries not to become a group chat

Multi-agent systems can turn parallel work into coordination overhead very quickly. This project keeps a few deliberately boring rules:

- small tasks may use zero subagents
- start with at most 2 managed subagents, normally no more than 3
- only one managed subagent writes to the canonical workspace at a time
- each subagent gets only the context needed for its responsibility
- investigation results need evidence before Main accepts them
- unclear state stops progress instead of becoming permission by guesswork
- Main remains responsible for the final result

Less agent theater. More controlled parallel work.

## Current fixed team

| Work | Model | Good at |
|---|---|---|
| Reading | Luna Max | focused code reading and call-path tracing |
| Implementation | Luna Max | bounded changes once the approach is clear |
| Investigation | Terra High | broad read-only investigation and cross-file evidence |
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

The first delegated task checks the five managed subagent profiles. If they are created during that task, Codex will ask for a restart because those profiles need to exist before the session starts. Open a fresh task and choose Orchestrate again. The bundled helpers require Python 3.11 or newer.

See [Plugin Installation](docs/plugin-installation.md) for the full setup.

Update:

```bash
codex plugin marketplace upgrade subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

Before uninstalling, use **Doctor** to remove only subagent profiles that can be proven to belong to this plugin. Then remove the plugin and marketplace source:

```bash
codex plugin remove subagents-dispatch@subagents-dispatch
codex plugin marketplace remove subagents-dispatch
```

If Doctor says ownership is unclear, resolve the conflict first. Do not silence the warning by deleting files manually.

## Will it make Codex faster?

Sometimes, especially when investigation can happen in parallel or the Main context would otherwise get crowded.

More agents do not automatically mean more speed. Small tasks can get slower, and coordination has a cost. The project has an experiment protocol for measuring correctness, rework, time, and token usage before making performance claims.

This README does not advertise unproven speedups or token savings.

The more important question is whether a complicated job can be split cleanly, brought back together safely, and still have one place where responsibility ends.

For technical details:

[Architecture](docs/architecture.md) · [Installation](docs/plugin-installation.md) · [Runtime Evidence](docs/runtime-attestation.md) · [Experiment Protocol](docs/experiment-protocol.md) · [Changelog](CHANGELOG.md) · [AI Reference](README_AI.md)

## License

[MIT](LICENSE)
