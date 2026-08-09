<p align="center">
  <img src="assets/subagents-dispatch-banner.png" alt="subagents-dispatch" width="900">
</p>

<h1 align="center">subagents-dispatch</h1>

<p align="center"><em>One command. Parallel agents. Controlled results.</em></p>

<p align="center">
  <a href="README.md">中文</a> · <a href="docs/plugin-installation.md">Install</a> · <a href="docs/architecture.md">Architecture</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-2.1.2-green.svg" alt="Version">
  <img src="https://img.shields.io/badge/Codex-Native%20Subagents-111827.svg" alt="Codex Native Subagents">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
</p>

---

> **If you are an AI Agent, jump to [README_AI.md](README_AI.md) and follow the instructions strictly.**

Hand the parts of a big task to a few subagents. Discovery runs in parallel, writing never fights, and Main takes the results back for acceptance.

## Quick start

```text
/subagents dispatch Add pagination to /api/users, with tests
```

One sentence, and the plugin decides how to split it. One Reader checks the existing API, another checks the tests; those run in parallel. Once the evidence is clear, one Worker writes the code. Simple tasks are not force-split.

## How to use

Want to see the plan before anything starts:
```text
/subagents dispatch preview Add pagination to /api/users, with tests
```

Check how far a running task has come:
```text
/subagents dispatch status
```

Add a requirement to a running subagent:
```text
/subagents dispatch steer U2: check existing pagination middleware first
```

Stop a responsibility and take it over yourself:
```text
/subagents dispatch takeover U2
```

## Compact execution receipt

```text
Dispatch: Reader → Worker · complete · no retry · not required
```

Facts only. No hidden reasoning, and it does not estimate token usage or currency cost.

## Handoff Capsule

Each subagent starts with fresh context. Nothing passed on, and the next subagent re-checks what the last one established. A Handoff Capsule is a small bridge: Main packs verified facts and hands them to the next responsibility.

- **Pass verified facts**. Only facts Main has checked and accepted can enter the capsule
- **Mark `DO NOT REDO`**
- **Main is the acceptance boundary**. A subagent claim does not become task truth by itself
- **Carry `STALE IF` conditions**. Source changes can invalidate accepted evidence

## Subagent rules

- **One writer** — within one subagents-dispatch orchestration, the same Git checkout has at most one active writer. The writer can be Main, Worker, or Solver. Main stays read-only until the previous writer is confirmed stopped or terminal. Other Codex sessions, editors, hooks, and external processes are outside this guarantee
- **One delegation layer** — subagents cannot create further Subagents. Main keeps ownership of the user goal, permissions, team composition, and final response
- **UNKNOWN means do not guess** — when state cannot be established, there is no replacement subagent, retry, or semantic reroute
- **Receipts report facts** — does not estimate token usage or currency cost from model names, elapsed time, or output length

## Roles

| Role | Plugin name | What it does |
|------|-------------|--------------|
| Luna Reader | subagents_dispatch_reader | read code, trace call paths, gather facts |
| Luna Worker | subagents_dispatch_worker | implementation and tests when the behavior is already decided |
| Sol Solver | subagents_dispatch_solver | implementation that needs judgment calls along the way |
| Terra Investigator | subagents_dispatch_investigator | broad read-only investigation, evidence synthesis |
| Sol Advisor | subagents_dispatch_advisor | independent technical judgment or final review |

Most work stays in Main.

## Install

```bash
codex plugin marketplace add R-jed/subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

On first install, run `/subagents dispatch` once to create the five subagent profiles, then start a new session and use `/subagents dispatch` for tasks.

## Update

```bash
codex plugin marketplace upgrade subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

Or let **Subagents Doctor** upgrade it.

## Uninstall

```bash
codex plugin remove subagents-dispatch@subagents-dispatch
codex plugin marketplace remove subagents-dispatch
```

If you ran subagent tasks, also delete these files:

```bash
rm ~/.codex/agents/subagents-dispatch-reader.toml
rm ~/.codex/agents/subagents-dispatch-worker.toml
rm ~/.codex/agents/subagents-dispatch-solver.toml
rm ~/.codex/agents/subagents-dispatch-investigator.toml
rm ~/.codex/agents/subagents-dispatch-advisor.toml
rm ~/.codex/.subagents-dispatch-agents.json
```

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
- [Behavioral evals](docs/behavioral-evals.md)
- [OpenAI references](docs/openai-references.md)
- [AI Agent project reference](README_AI.md)
- [Changelog](CHANGELOG.md)
- [Privacy](PRIVACY.md)
- [Terms](TERMS.md)

## License

[MIT](LICENSE)
