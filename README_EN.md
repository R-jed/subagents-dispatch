<p align="center">
  <img src="assets/subagents-dispatch-banner.png" alt="subagents-dispatch" width="900">
</p>

<h1 align="center">subagents-dispatch</h1>

<p align="center"><em>Give Codex a small team when the job actually deserves one.</em></p>

<p align="center">
  <a href="README.md">中文</a> · <a href="docs/plugin-installation.md">Install</a> · <a href="docs/architecture.md">Architecture</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-3.0.0-green.svg" alt="Version">
  <img src="https://img.shields.io/badge/Codex-Native%20Subagents-111827.svg" alt="Codex Native Subagents">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
</p>

> **If you are an AI Agent, jump to [README_AI.md](README_AI.md) and follow the instructions strictly.**

You give Codex a change that touches an API, tests, docs, and a few call sites. Main starts reading everything, then implementing, then checking its own work, all inside the same context.

It can get the job done. The trouble is that reading, investigation, editing, judgment, and review all compete for the same attention.

subagents-dispatch gives Main a temporary team. One child can focus on reading the code. Another can investigate a wider area. Another can take a bounded implementation once the direction is clear. Main decides whether any split is worth it, controls write authority, verifies child findings, and owns the final result.

Sometimes the right team size is zero. `0 child` is a completely valid outcome.

## A quick example

A normal request can be this simple:

```text
Choose Dispatch
Add pagination to /api/users, add tests, and check whether frontend callers are affected
```

One possible split might look like this:

```text
Main
├─ Luna Max Read       → map the API, tests, and call chain
├─ Terra XHigh Research → inspect cross-file impact and hidden dependencies
├─ Luna Max Execute    → implement and test once the boundary is clear
└─ Sol High Review     → independently check a higher-impact change
```

Main takes the evidence back, decides what is trustworthy, and integrates the final change.

Main may also look at the task and do the whole thing itself. Dispatch has no minimum child count, and adding more Agents is never the goal on its own.

## How it works

The basic loop is small:

```text
1. Decide whether this step is worth isolating
2. Give each child only the context its responsibility needs
3. Parallelize independent reading when useful
4. Keep one active writer in the canonical workspace
5. Let Main verify, integrate, and own the final result
```

New project children start with fresh context by default. Main passes the objective, scope, constraints, acceptance conditions, and accepted facts that matter for that responsibility instead of copying the entire conversation.

The point is to reduce repeated discovery and context mixing without creating coordination work for its own sake.

## Install

```bash
codex plugin marketplace add R-jed/subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

Start a new Codex session after installation, then choose **Dispatch** from the Skill menu.

On the first run that genuinely needs a child, the plugin checks its five managed Agent profiles. If those profiles need to be created, the current task returns `RESTART_REQUIRED`. Start a fresh Codex task/session and choose Dispatch again.

Profile provisioning, Doctor helpers, and Runtime Attestation helpers require Python 3.11+. See [Plugin Installation](docs/plugin-installation.md) for the complete lifecycle.

## The six Skills you will actually use

| Skill | What it does |
|---|---|
| **Dispatch** | start or continue an orchestration |
| **Preview** | see the likely split without creating a child |
| **Status** | take one look at the current state |
| **Steer** | add guidance to the same child already doing the work |
| **Takeover** | safely settle the old writer, then return responsibility to Main |
| **Doctor** | inspect installation, profiles, state, and runtime evidence |

`Status` performs one observation and does not background poll. `Steer` keeps the same child. `Takeover` checks that the old writer is safely settled before conflicting write authority can move.

If you are unsure whether a task is worth splitting, start with **Preview**.

## How work is routed today

The current production policy uses five responsibility lanes:

| Current model / effort | User-facing activity | Typical use |
|---|---|---|
| Luna Max | Read | narrow code reading, call tracing, inspectable fact collection |
| Luna Max | Execute | bounded implementation and tests after the behavior is clear |
| Terra XHigh | Research | broad read-only investigation and cross-file evidence synthesis |
| Sol High | Execute | implementation that still requires material technical judgment |
| Sol High | Decide / Review | technical decisions or independent Final Review |

This is the current runtime policy in `contracts/policy.json`. The project does not currently have evidence that this model mix is optimal for every task.

## A few rules stay strict

Delegation can be flexible. These boundaries stay conservative:

* Main owns project-level delegation. Project children do not create more project children.
* One orchestration keeps one active writer in the canonical workspace.
* Every responsibility uses the exact `subagents_dispatch_*` Agent type specified by `contracts/policy.json`.
* `UNKNOWN` stays unknown. It cannot authorize replacement, rerouting, ownership transfer, or conflicting mutation.
* Child output becomes task truth only after Main verifies and accepts it.
* Final Review is driven by the consequence of the change instead of a fixed extra reviewer on every task.

See [Architecture](docs/architecture.md), [Routing](contracts/routing.md), [Guardrails](contracts/guardrails.md), and the [Composition Contract](contracts/composition.md) for the complete rules.

## Configuration is not runtime proof

Model, reasoning effort, and permission facts are tracked in four layers:

```text
Configured
→ Requested
→ Accepted
→ Observed
```

A configuration file proves configuration intent. Only Host runtime evidence can support an Observed claim. Doctor's explicit live-route workflow can check an exact child when that proof matters. Ordinary Dispatch does not scan local Codex rollouts.

At the end of a run, a Receipt reports orchestration and review facts independently, for example:

```text
Dispatch: Luna Max Read · Luna Max Execute · Sol High Review
Control: Status×1
Review: 1 round · passed
```

When later work needs accepted findings from an earlier responsibility, a Handoff Capsule can carry accepted facts, evidence refs, and open questions without moving the full transcript into the next child.

See [Runtime Attestation](docs/runtime-attestation.md), [Handoff Contract](contracts/handoff.md), and [Privacy](PRIVACY.md) for the details.

## When Dispatch is useful

Dispatch tends to make sense when repository investigation can run in parallel, a large read-only investigation is worth isolating, implementation needs a clear evidence-gathering stage first, a higher-impact change benefits from independent review, or a long task naturally contains several bounded responsibilities.

Main is usually simpler for a small local task, strongly serial work, or a task where the relevant context is already in hand. It should also stay conservative when the user's authority boundary is unclear or a required Host capability is still `UNKNOWN`.

## About performance

The repository includes an experiment protocol, campaign schema, and validator for comparing single-agent Codex with explicit Dispatch across correctness, safety, rework, wall-clock time, Main and child tokens, aggregate tokens, context pressure, and Host route evidence.

**Until repeated real-task evidence exists, this README does not claim that subagents-dispatch is proven faster, uses fewer total tokens, or that the current five model/effort routes are optimal.**

See the [Experiment Protocol](docs/experiment-protocol.md) and [Evaluations](evals/README.md).

## Update and uninstall

Update:

```bash
codex plugin marketplace upgrade subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

Start a fresh Codex session after updating.

If managed Agent profiles were provisioned, keep the Plugin installed first, choose **Doctor**, and explicitly ask it to uninstall the subagents-dispatch managed profiles. Doctor verifies the ownership manifest and file SHA-256 values and removes only configuration it can prove belongs to this plugin.

Then remove the Plugin and Marketplace registration:

```bash
codex plugin remove subagents-dispatch@subagents-dispatch
codex plugin marketplace remove subagents-dispatch
```

Do not bypass an ownership conflict with `rm`, wildcards, or manual deletion. See [Plugin Installation](docs/plugin-installation.md) for the complete procedure.

<details>
<summary><strong>Repository layout</strong></summary>

```text
.
├── .agents/plugins/                  # Marketplace registration
├── .codex-plugin/                    # Plugin manifest
├── agent-profiles/                   # five managed Agent profiles
├── contracts/                        # routing, state, safety, and evidence contracts
├── scripts/                          # provisioning, validation, and runtime helpers
├── skills/
│   ├── dispatch/                     # start or resume orchestration
│   ├── preview/                      # predict without execution
│   ├── status/                       # one-shot status observation
│   ├── steer/                        # guide an existing delegation
│   ├── takeover/                     # safely return responsibility to Main
│   └── doctor/                       # installation and runtime diagnostics
├── docs/                             # architecture, runtime, experiment, and release docs
├── evals/                            # behavioral and experiment fixtures
└── tests/                            # regression and adversarial tests
```

</details>

Main docs:

[Installation](docs/plugin-installation.md) · [Architecture](docs/architecture.md) · [Native Subagent Runtime](docs/native-subagent-runtime.md) · [Runtime Attestation](docs/runtime-attestation.md) · [Experiment Protocol](docs/experiment-protocol.md) · [Composition Contract](contracts/composition.md) · [CHANGELOG](CHANGELOG.md) · [Privacy](PRIVACY.md)

## License

[MIT](LICENSE)
