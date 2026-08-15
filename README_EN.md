<p align="center">
  <img src="assets/subagents-dispatch-banner.png" alt="subagents-dispatch" width="900">
</p>

<h1 align="center">subagents-dispatch</h1>

<p align="center"><em>Let Codex delegate when delegation adds value, while Main keeps control.</em></p>

<p align="center">
  <a href="README.md">中文</a> · <a href="docs/plugin-installation.md">Install</a> · <a href="docs/architecture.md">Architecture</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-3.0.0-green.svg" alt="Version">
  <img src="https://img.shields.io/badge/Codex-Native%20Subagents-111827.svg" alt="Codex Native Subagents">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
</p>

---

> **If you are an AI Agent, jump to [README_AI.md](README_AI.md) and follow the instructions strictly.**

subagents-dispatch is a Codex-native Subagent orchestration plugin. Main keeps ownership of the user goal, scope, permissions, integration, and final acceptance. The plugin delegates only bounded responsibilities that are worth isolating in one layer of specialist Subagents.

Small tasks can stay entirely in Main. Larger tasks can parallelize independent reading, isolate evidence-heavy investigation, route material judgment to the right capability lane, and still keep one writer in the canonical workspace.

## What changes

In one long session, reading, investigation, implementation, judgment, and review can all accumulate in the same context.

subagents-dispatch separates those responsibilities:

```text
user goal
  ↓
Main
  ├─ decides whether delegation is worth it
  ├─ compiles responsibility / authority / acceptance
  ├─ verifies and accepts Subagent evidence
  └─ owns the final result
       │
       ├─ independent reads can run in parallel
       ├─ writing remains single-writer
       ├─ stronger judgment lanes are used only when the responsibility needs them
       └─ independent review is triggered when consequences justify it
```

There is no target number of Subagents. A valid Dispatch may create several children, one child, or zero children.

## Quick start

```text
Choose Dispatch, then enter: Add pagination to /api/users, with tests
```

Main first decides whether any responsibility deserves its own context. Existing API behavior and test structure may be read independently, then a bounded writer can implement once semantics are clear. If the task is small, Main can simply do it instead of manufacturing a multi-Agent workflow.

## You stay in control

All six Skills are explicit entry points. Installing the plugin does not make it take over unrelated tasks.

| Skill | Purpose |
|---|---|
| **Dispatch** | start or resume value-driven orchestration |
| **Preview** | predict likely orchestration without spawning or writing state |
| **Status** | take one observation of the current orchestration |
| **Steer** | add guidance to the same responsibility, attempt, and native child |
| **Takeover** | return responsibility to Main only after the old writer is proven settled |
| **Doctor** | inspect Plugin, Skills, Agent profiles, dispatch state, and runtime-route evidence |

`Status` is not a background poller. `Steer` does not silently replace a child. `Takeover` does not let Main start a conflicting write while the previous writer is still `UNKNOWN` or `INTERRUPTED`.

## Five roles

Role semantics and runtime policy are separate. A role says what responsibility is allowed to do; the configured model/effort says which current lane is assigned to it.

| Internal role | Current model / effort | Public activity | Responsibility |
|---|---|---|---|
| Reader | Luna Max | Read | narrow code reading, call tracing, inspectable fact collection |
| Worker | Luna Max | Execute | bounded implementation and tests after behavior is already decided |
| Investigator | Terra XHigh | Investigate | broad read-only investigation and cross-file evidence synthesis |
| Solver | Sol High | Execute | implementation where material technical judgment cannot be separated from the edit |
| Advisor | Sol High | Decide / Review | read-only material judgment or independent Final Review |

“Read-only” is a behavioral responsibility that forbids project-file mutation, not a per-role OS sandbox. The actual sandbox and permission profile are Host runtime facts that require observation; internal source and selection provenance remain `UNKNOWN` when the Host does not expose them. Worker / Solver gain behavioral write authority only for an explicit scope assigned by Main. See [Guardrails](contracts/guardrails.md) and [Runtime Attestation](docs/runtime-attestation.md).

These routes are current policy. They are not a claim that this is already proven to be the universally optimal model/effort mix. Formal route calibration belongs to real experiments under the [Experiment Protocol](docs/experiment-protocol.md).

## Proving which model actually ran

A profile saying `Luna Max` proves configuration intent. A Host accepting an `agent_type` proves role acceptance. Neither alone proves the actual runtime model or reasoning effort.

When strict proof is required, Doctor's live-route workflow keeps the layers separate:

```text
Configured
→ Requested
→ Accepted
→ Observed
```

Observed fields come only from actual Host runtime evidence. When public Host metadata omits a required field, the exact child's local Codex rollout can be inspected through a read-only allowlist path for model, reasoning effort, sandbox / permission, and parent / child identity. Actual child permission is verified as an independent fact. Source identity and selection provenance are reported only when the Host separately exposes them; equal permission values do not prove a source. Configured values and model self-report never fill an Observed field.

See [Runtime Attestation](docs/runtime-attestation.md).

## Fresh child context without throwing away accepted evidence

New project children use fresh context by default. Main sends only the objective, scope, constraints, acceptance conditions, and accepted evidence that the current responsibility actually needs.

If a later responsibility would otherwise repeat expensive discovery, Main can build a small Handoff Capsule:

```text
ACCEPTED FACTS
ACCEPTED EVIDENCE
ARTIFACT REFS
DO NOT REDO
OPEN QUESTIONS
STALE IF
```

Only facts Main has checked and accepted can cross that boundary. Full logs, complete transcripts, private reasoning, and large source copies are not pushed into the next child just to avoid a read. When complete provenance matters, a references-first Evidence Artifact can hold it while the Handoff carries only the relevant refs.

## Receipts report orchestration facts

```text
Dispatch: Luna Max Read · Luna Max Execute · Sol High Review
Control: Status×1
Review: 1 round · passed
```

The Receipt describes Subagent dispatch, control, and independent review. It does not replace Main's final task summary, and it does not infer tokens, cost, or observed runtime identity from model names, elapsed time, or output length.

## Works with project rules, Skills, and hooks

subagents-dispatch does not build another AGENTS precedence system and does not copy an external Skill body into every child.

Composition uses constraint intersection:

```text
Host capability and policy
∩ current user / system / developer authority
∩ Host-effective project rules
∩ accepted upstream Skill / workflow constraints
∩ subagents-dispatch guardrails
∩ the current responsibility packet
```

A lower layer can narrow authority but cannot widen a higher layer. An external Skill may define how domain work should be done, but it cannot turn a read-only responsibility into a writer or expand the user's authorized scope. Hooks may observe or block actions, but they do not become a second scheduler, persistent state store, or authority system.

See the [Composition Contract](contracts/composition.md).

## Safety boundaries

- **Exact role binding**: every semantic role must resolve to its `subagents_dispatch_*` `agent_type` in `contracts/policy.json`; built-in roles, legacy aliases, custom Agents from other plugins, and model-equivalent profiles are never substitutes
- **Single writer**: one active writer per orchestration in the canonical workspace. Main cannot start a conflicting write until the Host proves the previous writer is stopped or terminal
- **One delegation layer**: Main owns project-level delegation; project children do not create more project children
- **`UNKNOWN` stays unknown**: uncertainty does not authorize replacement, hidden retry, or semantic reroute
- **Bounded recovery**: one responsibility has at most two materialized Agent attempts; same-child resume is not a retry
- **Main keeps final authority**: child output, hooks, external Skills, and configured routes are evidence or constraints, not task acceptance by themselves
- **Ordinary Dispatch does not scan Codex rollouts**: local rollout inspection exists only for explicit runtime attestation

## Performance data: no headline before the evidence

One goal of this project is to test whether responsibility isolation and routing can reduce repeated discovery, lower Main-context pressure, and shorten completion time when real parallelism exists. Those are empirical questions.

The repository now includes a formal experiment protocol and campaign validator for controlled comparisons such as:

```text
same real repository / exact base revision / exact task
single-agent Codex
vs
explicit Dispatch
```

The experiment model keeps correctness, safety, rework, wall-clock time, Main/child tokens, aggregate tokens, context pressure, and Host route evidence separate. Small tasks are required in the campaign mix because a good dispatcher must be allowed to choose `0 child`.

**Until repeated real-task evidence exists, this README does not claim that subagents-dispatch is proven faster, uses fewer total tokens, or that the current five model/effort routes are optimal.**

See the [Experiment Protocol](docs/experiment-protocol.md) and [Evaluations](evals/README.md). When results are ready, public numbers should remain traceable to the campaign, Host, repository, task, repeats, and oracle that produced them.

## When Dispatch should probably stay out of the way

Main is usually the better place for:

- small local tasks whose relevant context is already present
- strongly serial work where every step depends on the previous one
- work whose authorization boundary is still unclear
- tasks that depend on a Host control capability that is still `UNKNOWN`
- decomposition whose only purpose is to make the run look “multi-Agent”

Use Preview when you want to inspect likely orchestration without executing it.

## Install

```bash
codex plugin marketplace add R-jed/subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

When delegation is first genuinely needed, choose Dispatch. The plugin manages only its own five Agent profiles. If they must be provisioned, the current task returns `RESTART_REQUIRED`; start a fresh Codex task/session and choose Dispatch again.

See [Installation](docs/plugin-installation.md) for the full lifecycle and safety rules.

## Update

```bash
codex plugin marketplace upgrade subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

You can also choose **Doctor** to inspect the installation and managed-profile state.

## Uninstall

If managed Agent profiles were provisioned, keep the Plugin installed first, choose **Doctor**, and explicitly ask it to uninstall the subagents-dispatch managed profiles. Doctor uses the ownership-aware cleanup path and removes only configuration that still matches the plugin's ownership manifest exactly. If ownership cannot be proven, it stops. See [Installation](docs/plugin-installation.md) for the full rules.

After the managed profiles are safely removed, remove the Plugin and Marketplace registration:

```bash
codex plugin remove subagents-dispatch@subagents-dispatch
codex plugin marketplace remove subagents-dispatch
```

Do not bypass an ownership conflict with `rm`, wildcards, or manual deletion.

## Privacy

Ordinary orchestration keeps one compact root-thread-scoped coordination capsule in the operating system's temporary directory only when cross-turn coordination state is needed. Preview and zero-child Dispatch do not create it, and normal terminal state is removed. The capsule is not a store for raw prompts, full transcripts, private reasoning, credentials, or full source files.

The local-rollout boundary used only during explicit Runtime Attestation is documented in [PRIVACY.md](PRIVACY.md).

## Repository layout

```text
.
├── .agents/plugins/                  # Codex Marketplace registration
├── .codex-plugin/                    # Plugin manifest
├── agent-profiles/                   # five managed Agent profiles
├── contracts/                        # orchestration, state, evidence, and safety contracts
├── scripts/                          # installer, validators, state, and runtime-evidence tools
├── skills/
│   ├── dispatch/                     # start or resume orchestration
│   ├── preview/                      # predict without execution
│   ├── status/                       # one-shot status observation
│   ├── steer/                        # guide an existing delegation
│   ├── takeover/                     # safely return responsibility to Main
│   └── doctor/                       # installation and runtime diagnostics
├── docs/                             # architecture, Host, experiment, and release docs
├── evals/                            # static, behavioral, and experiment schemas
└── tests/                            # regression and adversarial tests
```

## Documentation

- [Installation](docs/plugin-installation.md)
- [Architecture](docs/architecture.md)
- [Codex Native Subagent runtime boundaries](docs/native-subagent-runtime.md)
- [Runtime Attestation](docs/runtime-attestation.md)
- [Experiment Protocol](docs/experiment-protocol.md)
- [Composition Contract](contracts/composition.md)
- [Behavioral evals](docs/behavioral-evals.md)
- [OpenAI references](docs/openai-references.md)
- [AI Agent project reference](README_AI.md)
- [Changelog](CHANGELOG.md)
- [Privacy](PRIVACY.md)
- [Terms](TERMS.md)

## License

[MIT](LICENSE)