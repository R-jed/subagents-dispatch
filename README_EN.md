<p align="center">
  <img src="assets/subagents-dispatch-banner.png" alt="subagents-dispatch" width="900">
</p>

<h1 align="center">subagents-dispatch</h1>

<p align="center"><em>Give Codex a temporary team while keeping the control surface small.</em></p>

<p align="center">
  <a href="README.md">中文</a> · <a href="docs/plugin-installation.md">Install</a> · <a href="docs/architecture.md">Architecture</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-4.0.0-green.svg" alt="Version">
  <img src="https://img.shields.io/badge/Codex-Native%20Subagents-111827.svg" alt="Codex Native Subagents">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
</p>

> **If you are an AI Agent, use [README_AI.md](README_AI.md).**

V4 reduces the public surface to two explicit Skills: **Orchestrate** and **Doctor**. Orchestrate owns planning, execution, status, correction, continuation, cancellation, takeover, review, and integration. Doctor owns package integrity, fixed profiles, V4 state, WriterLease, PendingControl, Host capability evidence, Hook evidence, and release-readiness diagnostics.

The repository implementation and offline verification can be completed without Codex quota. The real Codex Host H00-H20 lifecycle-Hook smoke remains a release gate. The project does not mark that gate as passed or activate the V4 production three-event Hook manifest without real Host evidence.

## Install

After the V4 release is approved:

```bash
codex plugin marketplace add R-jed/subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

Update:

```bash
codex plugin marketplace upgrade subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

Before removing the Plugin, use Doctor or `scripts/uninstall-agents.py` to remove only managed profiles whose ownership can be proven. Then run:

```bash
codex plugin remove subagents-dispatch@subagents-dispatch
codex plugin marketplace remove subagents-dispatch
```

Do not bypass ownership checks with manual deletion. Python helpers require Python 3.11+. See [Plugin Installation](docs/plugin-installation.md).

## Two public Skills

| Skill | Responsibility |
|---|---|
| **Orchestrate** | plan-only, execution, status, correction, continuation, cancellation, takeover, review, and integration |
| **Doctor** | package, profile, V4 state, Host capability, Hook evidence, and release-readiness diagnostics |

Orchestrate plan-only mode creates no runtime state, acquires no WriterLease, prepares no PendingControl, and invokes no Host lifecycle tool.

## Fixed execution profiles

V4.0.0 freezes the following profiles:

| Profile | Model / effort | Authority |
|---|---|---|
| Reader | Luna Max | read-only |
| Worker | Luna Max | bounded write |
| Investigator | Terra High | read-only |
| Solver | Sol High | bounded write and high-judgment work |
| Advisor | Sol High | read-only review |

V4.0.0 does not perform dynamic reasoning-effort routing. The router selects only among the fixed capability profiles.

## Scheduling and safety

Core invariants:

```text
Main owns user intent, integration, and acceptance
initial managed children <= 2
normal managed children <= 3 and bounded by Host capacity
dependencies unlock only from WorkUnit.ACCEPTED
Host COMPLETED advances only to RESULT_READY
at most one canonical managed writer
fork_turns = none
depth = 1
UNKNOWN remains fail closed
```

Runtime truth separates WorkUnit state, ExecutionBinding, `control_epoch`, PendingControl, and WriterLease. WriterLease uses `RESERVED / HELD / REVOKING / UNKNOWN / RELEASED`. PendingControl uses `PREPARED / IN_FLIGHT / ACKED / UNKNOWN / CANCELLED`. A Host observation may mutate current state only while its execution, control epoch, and lease epoch still match.

A child can receive one bounded correction or a distinct `CONTINUE` operation without creating a fresh Agent attempt. `CONTINUE` does not consume the correction budget. Interrupt acknowledgement alone cannot release WriterLease. Takeover additionally requires fresh current-generation settlement evidence, a completed authoritative `list_agents` Hook receipt, and no unresolved PendingControl.

A V3.x `active.json` remains legacy migration evidence. Unresolved V3.x ownership, active writer, pending takeover, or corrupt state is never silently enrolled into V4.

## Host Hook release gate

The staged V4 lifecycle Hook manifest is `docs/v4/hooks.json`. Activation requires the H00-H20 real-Host evidence defined by `docs/v4/host-smoke.json`. The gate covers Hook trust and activation, lifecycle Pre/Post pairing, `SubagentStop` veto behavior, fixed-profile and fresh-context behavior, authoritative unfiltered root `list_agents` occupancy, duplicate/delayed/out-of-order delivery, candidate binding, mixed managed/unmanaged Host occupancy, and Windows effective-path aliases.

H07 additionally requires stale capacity truth to be consumed before a lifecycle Host mutation crosses the tool boundary and requires failed or ambiguous PostToolUse to use the Host-supported result-rejection path. PostToolUse `continue:false` is not accepted as turn-stop evidence; managed-child stop/continuation behavior is validated at `SubagentStop`.

Offline CI, Plugin validation, and source review do not substitute for this evidence. Doctor `--release-check` exits non-zero while the gate remains pending.

## Configuration and runtime evidence

Treat route and permission facts as separate evidence levels:

```text
Configured
→ Requested
→ Accepted
→ Observed
```

Configuration proves intent. Host behavior that affects release readiness requires direct observation.

## Performance

The repository keeps a separate Experiment Plane for correctness, rework, wall-clock, Main/child token usage, total token usage, and coordination overhead. Luna Max / Terra High / Sol High is the V4.0.0 product policy and is not claimed to be globally cost-optimal for every workload.

**This README does not claim that subagents-dispatch is proven faster or cheaper in total tokens.**

## Repository layout

```text
.
├── .agents/plugins/
├── .codex-plugin/
├── agent-profiles/
├── contracts/
├── docs/
│   └── v4/
├── hooks/
├── skills/
│   ├── orchestrate/
│   └── doctor/
├── scripts/
├── evals/
└── tests/
```

References: [AI Reference](README_AI.md) · [Plugin Installation](docs/plugin-installation.md) · [Architecture](docs/architecture.md) · [Native Subagent Runtime](docs/native-subagent-runtime.md) · [Runtime Attestation](docs/runtime-attestation.md) · [Experiment Protocol](docs/experiment-protocol.md) · [Composition Contract](contracts/composition.md) · [CHANGELOG](CHANGELOG.md)

## License

[MIT](LICENSE)
