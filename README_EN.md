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

subagents-dispatch is a Codex plugin that hands the right work to a specialist Agent while Main keeps the goal, the permissions, and the final answer. It does not delegate for show. Work Main can finish alone stays in Main.

## Quick start

After installation, open a fresh Codex session. Use `/skills` to select **Dispatch**, or invoke it directly with `$dispatch`.

For example:

```
$dispatch Add pagination to /api/users, with tests
```

Main decides what is worth splitting. One Reader can inspect the API while another checks related tests; those read-only responsibilities may run in parallel. Once the evidence is clear, one Worker can implement and test the change. The same checkout never has two active writers. Main verifies, integrates, and delivers the final result.

Simple work is not force-split to look collaborative. A child starts only when delegation adds concrete value.

## Control surface

All controls use the same Dispatch Skill:

```
$dispatch preview Add pagination to /api/users, with tests
$dispatch status
$dispatch steer U2: check existing pagination middleware first
$dispatch takeover U2
```

Preview does not spawn. Status is one-shot inspection. Steer keeps the same responsibility and authority. Takeover settles the old owner before Main continues the responsibility.

## Compact execution receipt

When a task actually spawns Agents, the final response includes one factual line:

```
Dispatch: Reader → Worker · complete · no retry · not required
```

The receipt reports only inspectable orchestration facts. It exposes no hidden reasoning and does not estimate token usage or currency cost.

## Handoff Capsule: evidence-bound handoffs

Each child receives fresh context. A Handoff Capsule lets Main pass forward facts it has already verified without forwarding an entire transcript.

- **Pass verified facts**. Only facts Main checked and accepted can enter the capsule
- **Mark `DO NOT REDO`**. Reliable completed discovery can be explicitly skipped downstream
- **Main is the acceptance boundary**. A child claim is not inherited task truth until Main verifies it
- **Carry `STALE IF` conditions**. Relevant artifact drift invalidates old evidence and triggers narrow re-verification

## Four core invariants

- **One writer**. Within one subagents-dispatch orchestration, the same checkout has at most one active writer. Main remains read-only until the previous writer is confirmed stopped or terminal. Other Codex sessions, editors, hooks, and external processes are outside this guarantee
- **One delegation layer**. Child Agents do not create more project Subagents. Main keeps ownership of the user goal, permissions, team composition, and final response
- **UNKNOWN means do not guess**. Missing runtime state does not trigger a replacement Agent, automatic retry, or semantic reroute
- **Receipts report facts**. Token usage and currency cost are not inferred from model names, elapsed time, or output length

## Roles

| Role | What it does |
|------|-------------|
| Luna Reader | read code, trace call paths, gather facts |
| Luna Worker | implementation and tests when behavior is already decided |
| Sol Solver | implementation that needs material judgment along the way |
| Terra Investigator | broader read-only technical investigation and evidence synthesis |
| Sol Advisor | independent technical judgment or final review |

Simple work stays in Main. Delegation follows the actual responsibility; there is no fixed team size or fixed pipeline.

## Install

```bash
codex plugin marketplace add R-jed/subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

Start a fresh Codex session after installing. Use `/skills` to select **Dispatch** or **Doctor**, or invoke them directly as `$dispatch` and `$doctor`.

The first `$dispatch` task that genuinely needs a child automatically prepares subagents-dispatch's five managed Agent profiles without asking you to make a TOML-level setup decision. Codex loads custom-Agent registrations when a task starts, so that setup task ends with `RESTART_REQUIRED` and asks you to open one fresh task and rerun the original `$dispatch`. It does not first attempt to spawn a role the current task cannot see.

If a managed path is conflicting, modified without proven ownership, symlinked, or otherwise unsafe, subagents-dispatch fails closed and points you to `$doctor` for diagnosis.

## Uninstall

```bash
codex plugin remove subagents-dispatch@subagents-dispatch
codex plugin marketplace remove subagents-dispatch
```

If delegated work previously provisioned the Agent profiles, also remove only these managed files:

```bash
rm ~/.codex/agents/subagents-dispatch-reader.toml
rm ~/.codex/agents/subagents-dispatch-worker.toml
rm ~/.codex/agents/subagents-dispatch-solver.toml
rm ~/.codex/agents/subagents-dispatch-investigator.toml
rm ~/.codex/agents/subagents-dispatch-advisor.toml
rm ~/.codex/.subagents-dispatch-agents.json
```

## Update

```bash
codex plugin marketplace upgrade subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

Or invoke Doctor explicitly:

```
$doctor Upgrade subagents-dispatch
```

Start a fresh Codex session after updating.

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
