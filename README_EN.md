<p align="center">
  <img src="assets/subagents-dispatch-banner.png" alt="subagents-dispatch" width="900">
</p>

<h1 align="center">subagents-dispatch</h1>

<p align="center"><em>One command. Parallel agents. Controlled results.</em></p>

<p align="center">
  <a href="README.md">中文</a> · <a href="README_AI.md">AI Agent</a> · <a href="docs/plugin-installation.md">Install</a> · <a href="docs/architecture.md">Architecture</a> · <a href="LICENSE">MIT</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-2.1.2-green.svg" alt="Version">
  <img src="https://img.shields.io/badge/Codex-Native%20Subagents-111827.svg" alt="Codex Native Subagents">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
</p>

---

> **If you are an AI Agent, jump to [README_AI.md](README_AI.md) and follow the instructions strictly.**

subagents-dispatch is a Codex plugin with one job: hand parts of a big task to a few specialist Agents, while Main keeps the goal, watches progress, and takes the results back for acceptance.

Nothing to learn, nothing to configure. Install the plugin, pick it from a menu, say what you want in plain words, and let it work.

## Quick start

In the Codex App, type `/` to open the Skill menu, choose **Subagents Dispatch**, and enter your task.

For example:

```text
Add pagination to /api/users, with tests
```

The plugin decides how to split the work. One Reader can inspect the existing API while another Reader inspects the related tests, so those read-only tasks run in parallel. Once the evidence is clear, one Worker makes the implementation and test changes. Read-only discovery may run concurrently, but the same checkout never has two active writers. Main then checks, integrates, and delivers the final result.

Simple tasks are not force-split to look collaborative. A subagent only starts when it is genuinely faster, safer, or a better fit.

## Control surface

Choose **Subagents Dispatch** from the `/` menu, then use these control intents.

Preview without spawning:

```text
preview Add pagination to /api/users, with tests
```

Check status during execution:

```text
status
```

Guide a running Agent:

```text
steer U2: check existing pagination middleware first
```

Take back control:

```text
takeover U2
```

## Compact execution receipt

When a task spawns Agents, it ends with a one-line receipt:

```text
Dispatch: Reader → Worker · complete · no retry · not required
```

The receipt covers verifiable facts only: which roles ran, whether anything retried, whether a final review happened. It exposes no hidden reasoning and does not estimate token usage or currency cost.

## Handoff Capsule: evidence-bound handoffs

Each child receives fresh context. With nothing passed on, the next Agent often re-checks what the previous one already established.

A Handoff Capsule is a small bridge. Main packs the facts it has verified and accepted into it, then hands them to the next responsibility.

- **Pass verified facts**. Only facts Main has checked and accepted can enter the capsule
- **Mark `DO NOT REDO`**. Work already satisfied by valid evidence can be marked as do not repeat
- **Main is the acceptance boundary**. A child claim does not become inherited task truth by itself
- **Carry `STALE IF` conditions**. Source changes can invalidate previously accepted evidence

## Four core invariants

These hold no matter how many responsibilities a task splits into:

- **One writer** — within one subagents-dispatch orchestration, the same Git checkout has at most one active writer. The writer can be Main, Worker, or Solver. Main stays read-only until the previous writer is confirmed stopped or terminal. Other Codex sessions, editors, hooks, and external processes are outside this guarantee
- **One delegation layer** — child Agents cannot create further Subagents. Main keeps ownership of the user goal, permissions, team composition, and final response
- **UNKNOWN means do not guess** — when state cannot be established, there is no replacement Agent, retry, or semantic reroute
- **Receipts report facts** — does not estimate token usage or currency cost from model names, elapsed time, or output length

## Roles

Most work stays in Main. These roles only come out when delegation earns its keep.

| Role | What it does |
|------|-------------|
| Luna Reader | read code, trace call paths, gather facts |
| Luna Worker | implementation and tests when the behavior is already decided |
| Sol Solver | implementation that needs judgment calls along the way |
| Terra Investigator | broad read-only investigation, evidence synthesis |
| Sol Advisor | independent technical judgment or final review |

No fixed team size, no fixed pipeline. Delegation happens when parallelism, isolation, or specialist capability justifies the cost.

## Install

```bash
codex plugin marketplace add R-jed/subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

Start a new Codex session after installing the Plugin. The first task run through **Subagents Dispatch** that actually needs a child automatically prepares subagents-dispatch's five managed Agent profiles without asking you to make a TOML-level setup decision. Codex loads custom-Agent registrations when a task starts, so that first setup task ends by asking you to open one fresh task, choose **Subagents Dispatch** from the `/` menu again, and rerun the original request. It does not first attempt to spawn a role that the current task cannot see. After the profiles were present before task startup, later tasks can delegate normally.

If an existing managed path is conflicting, modified without proven ownership, or unsafe, subagents-dispatch does not overwrite it and stops with **Subagents Doctor** guidance.

## Update

```bash
codex plugin marketplace upgrade subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

Or choose **Subagents Doctor** from the `/` menu and ask it to upgrade subagents-dispatch.

Start a new Codex session after updating.

## Uninstall

```bash
# Remove plugin registration
codex plugin remove subagents-dispatch@subagents-dispatch

# Remove marketplace registration and snapshot cache
codex plugin marketplace remove subagents-dispatch
```

If you previously ran tasks that needed Agents, also delete these files:

```bash
# Delete 5 Agent profiles
rm ~/.codex/agents/subagents-dispatch-reader.toml
rm ~/.codex/agents/subagents-dispatch-worker.toml
rm ~/.codex/agents/subagents-dispatch-solver.toml
rm ~/.codex/agents/subagents-dispatch-investigator.toml
rm ~/.codex/agents/subagents-dispatch-advisor.toml

# Delete install manifest
rm ~/.codex/.subagents-dispatch-agents.json
```

## FAQ

**Do I need to learn anything first?**
No. Install the plugin, pick **Subagents Dispatch** from the `/` menu, and say what you want in plain words.

**Can multiple Agents overwrite each other's changes?**
Not within one dispatch. The same checkout has at most one active writer at a time, which prevents concurrent writer conflicts. Any code change can still contain bugs, so Main checks and verifies the result before delivery.

**Do I have to watch it work?**
No. When a task spawns Agents, it ends with a one-line receipt that tells you what ran, whether anything retried, and whether a review happened.

**My task is simple. Do I still need it?**
It will not force-split simple work. What Main can finish alone stays in Main.

## Repository layout

```text
.
├── .agents/plugins/                  # Codex Marketplace registration
├── .codex-plugin/                    # plugin manifest
├── agent-profiles/                   # five Agent profiles
├── policy-contract.json              # role definitions and core constraints
├── scripts/                          # installer, validators, runtime evidence tools
├── skills/
│   ├── dispatch/                     # Subagents Dispatch Skill
│   └── doctor/                       # Subagents Doctor Skill
├── docs/                             # architecture and runtime boundary docs
├── evals/                            # static and behavioral evaluation data
└── tests/                            # regression tests
```

## Documentation

- [Installation](docs/plugin-installation.md)
- [Architecture](docs/architecture.md)
- [Codex Native Subagent runtime boundaries](docs/native-subagent-runtime.md)
- [AI Agent project reference](README_AI.md)

## License

[MIT](LICENSE)
