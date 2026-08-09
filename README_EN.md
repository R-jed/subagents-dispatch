<p align="center">
  <img src="assets/subagents-dispatch-banner.png" alt="subagents-dispatch" width="900">
</p>

<h1 align="center">subagents-dispatch</h1>

<p align="center"><em>One command. Parallel agents. Controlled results.</em></p>

<p align="center">
  <a href="README.md">中文</a> · <a href="README_AI.md">AI Agent</a> · <a href="docs/plugin-installation.md">Install</a> · <a href="docs/architecture.md">Architecture</a> · <a href="LICENSE">MIT</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-2.1.1-green.svg" alt="Version">
  <img src="https://img.shields.io/badge/Codex-Native%20Subagents-111827.svg" alt="Codex Native Subagents">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
</p>

---

> **If you are an AI Agent, jump to [README_AI.md](README_AI.md) and follow the instructions strictly.**

subagents-dispatch is a Codex plugin that hands the right work to a specialist Agent while Main keeps the goal, the permissions, and the final answer. It does not delegate for show. Work Main can finish alone stays in Main.

## Quick start

You ask Codex to add pagination to `/api/users` and write the tests.

Without the plugin, the main session does everything itself: reads the code, changes the implementation, writes the tests, one step at a time.

With it, one line is enough:

```
/dispatch Add pagination to /api/users, with tests
```

Main decides what is worth splitting. For example, one Reader can inspect the existing API while another Reader inspects the related tests, so those read-only tasks can run in parallel. Once the evidence is clear, one Worker can make the implementation and test changes. Read-only discovery may run concurrently, but the same checkout never has two active writers. Main then checks, integrates, and delivers.

Simple tasks are not force-split to look collaborative. A subagent only starts when it is genuinely faster, safer, or a better fit.

## Control surface

Preview the delegation plan without spawning:

```
/dispatch preview Add pagination to /api/users, with tests
```

Check status during execution:

```
/dispatch status
```

Guide a running Agent:

```
/dispatch steer U2: check existing pagination middleware first
```

Take back control:

```
/dispatch takeover U2
```

## Compact execution receipt

When a task spawns Agents, it ends with a one-line receipt:

```
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

| Role | What it does |
|------|-------------|
| Luna Reader | read code, trace call paths, gather facts |
| Luna Worker | implementation and tests when the behavior is already decided |
| Sol Solver | implementation that needs judgment calls along the way |
| Terra Investigator | broad read-only investigation, evidence synthesis |
| Sol Advisor | independent technical judgment or final review |

Simple work stays in Main. Delegation happens when parallelism, isolation, or specialist capability justifies the cost. No fixed team size, no fixed pipeline.

## Install

```bash
codex plugin marketplace add R-jed/subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

Start a new Codex session after installing the Plugin. The first `/dispatch` task that actually needs a child automatically prepares subagents-dispatch's five managed Agent profiles without asking you to make a TOML-level setup decision. Codex loads custom-Agent registrations when a task starts, so that first setup task ends by asking you to open one fresh task and rerun the original `/dispatch`; it does not first attempt to spawn a role that the current task cannot see. After the profiles were present before task startup, later tasks can delegate normally.

If an existing managed path is conflicting, modified without proven ownership, or unsafe, subagents-dispatch does not overwrite it and stops with `/doctor` guidance.

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

## Update

```bash
codex plugin marketplace upgrade subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

Or ask Doctor:

```
/doctor Upgrade subagents-dispatch
```

Start a new Codex session after updating.

## Repository layout

```
.
├── .agents/plugins/                  # Codex Marketplace registration
├── .codex-plugin/                    # plugin manifest
├── agent-profiles/                   # five Agent profiles
├── policy-contract.json              # role definitions and core constraints
├── scripts/                          # installer, validators, runtime evidence tools
├── skills/
│   ├── dispatch/                     # main Skill, interaction controls, runtime rules
│   └── doctor/                       # install diagnostics and upgrade
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
