<p align="center">
  <img src="assets/subagents-dispatch-banner.png" alt="subagents-dispatch" width="900">
</p>

<h1 align="center">subagents-dispatch</h1>

<p align="center"><em>给 Codex 一支按需组建的小队，同时把控制面保持简单。</em></p>

<p align="center">
  <a href="README_EN.md">English</a> · <a href="docs/plugin-installation.md">安装</a> · <a href="docs/architecture.md">架构</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-4.0.0-green.svg" alt="Version">
  <img src="https://img.shields.io/badge/Codex-Native%20Subagents-111827.svg" alt="Codex Native Subagents">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
</p>

> **如果你是 AI Agent，请跳转到 [README_AI.md](README_AI.md)。**

V4 把公开入口收敛为两个 Skill：**Orchestrate** 和 **Doctor**。Orchestrate 负责规划、执行、状态、纠正、继续、取消、接管、复核和整合。Doctor 负责安装、固定 profile、V4 state、WriterLease、PendingControl、Host 能力、Hook 证据与发布就绪诊断。

当前分支已经完成 V4 仓库实现与离线验证工作。真实 Codex Host 的 H01 到 H07 lifecycle Hook smoke 仍是发布门。没有真机证据时，项目不会把这项状态标成通过，也不会启用需要该证据才能成立的生产三面 Hook。

## 安装

正式发布后使用 Codex Plugin Marketplace：

```bash
codex plugin marketplace add R-jed/subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

更新：

```bash
codex plugin marketplace upgrade subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

卸载时先通过 Doctor 或 `scripts/uninstall-agents.py` 清理能够证明属于本插件的 managed profiles，再执行：

```bash
codex plugin remove subagents-dispatch@subagents-dispatch
codex plugin marketplace remove subagents-dispatch
```

不要用手工删除绕过 ownership 校验。完整流程见 [Plugin Installation](docs/plugin-installation.md)。Python helper 需要 Python 3.11+。

## 两个公开 Skill

| Skill | 责任 |
|---|---|
| **Orchestrate** | 统一处理 plan-only、执行、状态、纠正、继续、取消、接管、复核和整合 |
| **Doctor** | 检查包完整性、profile、V4 state、Host 能力、Hook 证据和 release readiness |

Orchestrate 的 `plan-only` 不创建运行态、不申请 WriterLease、不准备 PendingControl，也不调用 Host lifecycle tool。

## 固定执行 profile

V4.0.0 固定使用：

| Profile | 模型 / effort | 权限 |
|---|---|---|
| Reader | Luna Max | 只读 |
| Worker | Luna Max | 有界写 |
| Investigator | Terra High | 只读 |
| Solver | Sol High | 有界写与高判断 |
| Advisor | Sol High | 只读复核 |

V4.0.0 不做动态 reasoning-effort routing。路由器只选择已经冻结的 capability profile。

## 调度与安全边界

核心规则：

```text
Main 持有用户目标、集成和验收
初始 managed child <= 2
正常 managed child <= 3，且受 Host capacity 约束
依赖只从 WorkUnit.ACCEPTED 解锁
Host COMPLETED 只推进到 RESULT_READY
canonical managed writer 同时最多 1 个
fork_turns = none
depth = 1
UNKNOWN 保持 fail closed
```

运行态分离 WorkUnit 真值、ExecutionBinding、`control_epoch`、PendingControl 和 WriterLease。WriterLease 使用 `RESERVED / HELD / REVOKING / UNKNOWN / RELEASED`。PendingControl 使用 `PREPARED / IN_FLIGHT / ACKED / UNKNOWN / CANCELLED`。旧 Host observation 只有在 execution、control epoch 和 lease epoch 都仍匹配时才能生效。

同一个 child 可以做有界 correction 或 `CONTINUE`。correction 不消耗 fresh Agent attempt，但有单独预算。`CONTINUE` 不消耗 correction budget。中断调用成功本身不能释放 WriterLease，接管还需要当前代际的 fresh Host settlement evidence。

V3.x `active.json` 只作为 legacy migration evidence。未解决的 V3.x ownership、active writer、pending takeover 或 corrupt state 不会被静默迁移到 V4。

## Host Hook 发布门

V4 的 staged lifecycle Hook 位于 `docs/v4/hooks.json`。正式激活需要 `docs/v4/host-smoke.json` 的 H01 到 H07 真机证据，覆盖 `spawn_agent`、`followup_task`、`interrupt_agent` 的 Pre/Post Hook、`tool_use_id` 一致性、`SubagentStop` veto、child sibling control 阻断，以及缺失 PostToolUse 时的 fail-closed 行为。

离线 CI、插件校验和源码审查不能替代这项 Host 证据。Doctor 的 `--release-check` 会在该门仍待验证时返回非零。

## 配置与运行时证据

模型、effort、权限和 Host lifecycle 需要区分：

```text
Configured
→ Requested
→ Accepted
→ Observed
```

配置只能证明配置意图。真正影响 release readiness 的 Host 行为需要直接观察。

## 关于性能

项目保留独立 Experiment Plane 来比较正确性、返工、wall-clock、Main / child token、总 token 和协调开销。固定 Luna Max / Terra High / Sol High 是 V4.0.0 的产品策略，不宣称为所有 workload 的全局成本最优。

**本 README 不声称 subagents-dispatch 已经被证明更快、更省总 Token。**

## 项目结构

```text
.
├── .agents/plugins/          # Marketplace registration
├── .codex-plugin/            # Plugin manifest + integrity manifest
├── agent-profiles/           # five fixed managed profiles
├── contracts/                # hardened V3.x contracts retained as compatibility/reference owners
├── docs/
│   └── v4/                   # frozen V4 architecture, Host smoke and phase evidence
├── hooks/                    # current production Hook manifest and launchers
├── skills/
│   ├── orchestrate/
│   └── doctor/
├── scripts/                  # V4 state, scheduler, control, lifecycle, Doctor and installers
├── evals/                    # Experiment Plane fixtures
└── tests/                    # regression and adversarial tests
```

主要入口：[AI Reference](README_AI.md) · [安装](docs/plugin-installation.md) · [架构](docs/architecture.md) · [Runtime Attestation](docs/runtime-attestation.md) · [Experiment Protocol](docs/experiment-protocol.md) · [CHANGELOG](CHANGELOG.md)

## License

[MIT](LICENSE)
