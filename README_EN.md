<p align="center">
  <img src="assets/subagents-dispatch-banner.png" alt="subagents-dispatch" width="900">
</p>

<h1 align="center">subagents-dispatch</h1>

<p align="center"><em>Let Codex delegate when the split is worth it, while Main keeps control of scope, authority, and the final result.</em></p>

<p align="center">
  <a href="README.md">中文</a> · <a href="docs/plugin-installation.md">Install</a> · <a href="docs/architecture.md">Architecture</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-3.0.0-green.svg" alt="Version">
  <img src="https://img.shields.io/badge/Codex-Native%20Subagents-111827.svg" alt="Codex Native Subagents">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
</p>

> AI Agents should read [README_AI.md](README_AI.md) first.

subagents-dispatch is an orchestration plugin built on Codex Native Subagents. Main keeps ownership of the user goal, authorized scope, technical integration, and final acceptance. The plugin delegates only responsibilities that are worth isolating, and each child receives only the context it actually needs for that responsibility.

Codex remains the only Agent runtime. This project does not add a daemon, task database, event bus, or separate scheduler.

## Install

```bash
codex plugin marketplace add R-jed/subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

Start a new Codex session after installation, then choose **Dispatch** from the Skill menu.

On the first run that genuinely needs a child, the plugin checks its five managed Agent profiles. If those profiles need to be created, the current task returns `RESTART_REQUIRED`. Start a fresh Codex task/session and choose Dispatch again.

Profile provisioning, Doctor helpers, and Runtime Attestation helpers require an available Python 3.11+ interpreter. See [Plugin Installation](docs/plugin-installation.md) for the complete install, update, and uninstall lifecycle.

## What it is for

Larger development tasks often accumulate code reading, investigation, implementation, technical judgment, and review in the same Main context. As the task grows, repeated discovery, context pressure, and mixed responsibilities become more likely.

subagents-dispatch keeps Main in the technical lead role:

```text
user task
  ↓
Main
  ├─ decides whether delegation adds value
  ├─ defines responsibility, authority, and acceptance
  ├─ opens independent reads or investigations in parallel
  ├─ keeps one writer in the canonical workspace
  ├─ verifies and integrates child output
  └─ owns the final result
```

There is no minimum child count. Small tasks can stay entirely in Main, and larger tasks create only the children that add value at the current stage.

A normal request can be as simple as:

```text
Choose Dispatch
Add pagination to /api/users, with tests
```

Main first decides which parts of the API, test structure, implementation, and review deserve their own responsibility before spawning anything.

## Six explicit Skills

Installing the plugin does not make it take over normal Codex work. All six entry points are explicit.

| Skill | Purpose |
|---|---|
| **Dispatch** | start or resume useful orchestration |
| **Preview** | show likely delegation without spawning or writing active state |
| **Status** | take one observation of the current orchestration |
| **Steer** | add guidance to the same unit, attempt, and child |
| **Takeover** | return responsibility to Main after the old writer is safely settled |
| **Doctor** | inspect Plugin, Skills, profiles, state, and runtime evidence |

`Status` performs one observation and does not background poll. `Steer` keeps the same child. `Takeover` does not release conflicting write authority while the old writer is `RUNNING`, `INTERRUPTED`, or `UNKNOWN`.

## Dispatch rules

The current production policy has five responsibility roles:

| Role | Current lane | Write authority | Typical responsibility |
|---|---|---|---|
| Reader | Luna Max | none | narrow code reading, call tracing, inspectable fact collection |
| Worker | Luna Max | bounded | implementation and tests after behavior is already decided |
| Investigator | Terra XHigh | none | broad read-only investigation and cross-file evidence synthesis |
| Solver | Sol High | bounded | implementation where material technical judgment is inseparable from the edit |
| Advisor | Sol High | none | technical decision or independent Final Review |

These lanes are the current runtime policy in `contracts/policy.json`. They are not presented as a universally proven optimal model mix.

A few boundaries stay hard:

* Main owns project-level delegation. Project children do not create more project children.
* One orchestration keeps one active writer in the canonical workspace.
* Every responsibility binds to its exact `subagents_dispatch_*` Agent type. Built-in roles, aliases, and model-equivalent profiles are not substitutes.
* `UNKNOWN` stays unknown. It cannot authorize replacement, rerouting, ownership transfer, or conflicting mutation.
* Child output becomes task truth only after Main verifies and accepts it.
* Final Review is consequence-driven rather than a fixed extra reviewer on every task.

See [Architecture](docs/architecture.md), [Routing](contracts/routing.md), and [Guardrails](contracts/guardrails.md) for the complete contracts.

## Context, evidence, and runtime facts

New project children use fresh context by default. Main sends the objective, scope, constraints, acceptance conditions, and accepted evidence needed for the current responsibility. When later work would otherwise repeat expensive discovery, a compact Handoff Capsule can carry accepted facts, evidence refs, and open questions without copying the full transcript or large source blocks into the next child.

For runtime claims such as model, reasoning effort, and permission, the project keeps four layers separate:

```text
Configured
→ Requested
→ Accepted
→ Observed
```

Configuration proves configuration intent. Observed fields require actual Host runtime evidence. Doctor's explicit live-route workflow can verify an exact child when that proof matters. Ordinary Dispatch does not scan local Codex rollouts.

See [Runtime Attestation](docs/runtime-attestation.md), [Handoff Contract](contracts/handoff.md), and [Privacy](PRIVACY.md).

## When to use it

Dispatch is a good fit when a task has:

* independent repository areas that can be read in parallel
* broad read-only investigation that is worth isolating from Main's implementation context
* a clear evidence-gathering stage before implementation
* a high-impact change that benefits from independent acceptance
* several bounded responsibilities with clear dependencies

Main is usually simpler when:

* the task is small and local, with the relevant context already present
* the work is strongly serial and each step depends on the previous result
* the user's authority boundary is still unclear
* correctness depends on a Host control capability that is currently `UNKNOWN`
* the only reason to split the work is to make the run look multi-Agent

Choose **Preview** first when you want to inspect the likely plan without executing it.

## Performance claims

The repository includes an experiment protocol, campaign schema, and validator for comparing single-agent Codex with explicit Dispatch across correctness, safety, rework, wall-clock time, Main and child tokens, aggregate tokens, context pressure, and Host route evidence.

This README does not claim that Dispatch is already proven faster or cheaper in total tokens, and it does not claim that the current five model and effort routes are proven optimal. Those conclusions require repeatable evidence from real tasks.

See the [Experiment Protocol](docs/experiment-protocol.md) and [Evaluations](evals/README.md).

## Update and uninstall

Update:

```bash
codex plugin marketplace upgrade subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

Start a fresh Codex session after updating.

If managed Agent profiles have been provisioned, keep the Plugin installed first and use **Doctor** to explicitly uninstall the profiles owned by subagents-dispatch. Doctor verifies the ownership manifest and file SHA-256 values and removes only configuration it can prove belongs to this plugin.

Then remove the Plugin and Marketplace registration:

```bash
codex plugin remove subagents-dispatch@subagents-dispatch
codex plugin marketplace remove subagents-dispatch
```

Do not bypass an ownership conflict with `rm`, wildcards, or manual deletion. See [Plugin Installation](docs/plugin-installation.md) for the complete procedure.

## Repository

```text
.
├── .agents/plugins/      # Marketplace registration
├── .codex-plugin/        # Plugin manifest
├── agent-profiles/       # five managed Agent profiles
├── contracts/            # routing, state, safety, and evidence contracts
├── skills/               # Dispatch, Preview, Status, Steer, Takeover, Doctor
├── scripts/              # provisioning, validation, and runtime helpers
├── docs/                 # architecture, runtime, experiment, and release docs
├── evals/                # behavioral and experiment fixtures
└── tests/                # regression and adversarial tests
```

Main docs:

[Installation](docs/plugin-installation.md) · [Architecture](docs/architecture.md) · [Native Subagent Runtime](docs/native-subagent-runtime.md) · [Runtime Attestation](docs/runtime-attestation.md) · [Experiment Protocol](docs/experiment-protocol.md) · [Composition](contracts/composition.md) · [CHANGELOG](CHANGELOG.md) · [Privacy](PRIVACY.md)

## License

[MIT](LICENSE)
