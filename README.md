<p align="center">
  <img src="assets/subagents-dispatch-banner.png" alt="subagents-dispatch" width="900">
</p>

<h1 align="center">subagents-dispatch</h1>

<p align="center"><em>给 Codex 一支临时小队。该分工时分工，该自己做时自己做。</em></p>

<p align="center">
  <a href="README_EN.md">English</a> · <a href="docs/plugin-installation.md">安装</a> · <a href="docs/architecture.md">架构</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-3.0.1-green.svg" alt="Version">
  <img src="https://img.shields.io/badge/Codex-Native%20Subagents-111827.svg" alt="Codex Native Subagents">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
</p>

> **如果你是 AI Agent，请跳转到 [README_AI.md](README_AI.md) 并严格按照说明操作。**

你给 Codex 一个稍大的任务。它先翻 API，再追调用链，接着改代码、补测试、查文档，最后还要回头 review 自己刚刚做的东西。

它能做完。问题是，读、查、改、判断和复核全挤在 Main 的同一个上下文里。

subagents-dispatch 给 Main 一支按需组建的小队。有人专心读代码，有人做大范围调查，有人处理边界明确的实现。Main 决定要不要分工，控制谁能写，验证 child 的结论，最后自己整合结果。

很多任务根本不需要 child。`0 child` 是完全有效的结果。

## 一个例子

你可以直接对 Codex 说：

```text
选择 Dispatch
给 /api/users 加分页，补测试，再检查前端调用有没有受影响
```

一个可能的分工会像这样：

```text
Main
├─ Luna Max 读取      → 先把 API、测试和调用链摸清
├─ Terra XHigh 调研   → 查跨文件影响和容易漏掉的依赖
├─ Luna Max 执行      → 边界明确后实现并补测试
└─ Sol High 验收      → 变更影响较大时做独立复核
```

Main 拿回证据，决定哪些内容可信，再完成最终整合。

也可能 Main 看完任务后直接自己做。Dispatch 没有最低 child 数量，多开 Agent 本身没有价值。

## 它怎么工作

核心思路很简单：

```text
1. 先判断这一步值不值得独立出去
2. child 只拿完成自己职责需要的上下文
3. 能并行读取的并行读取
4. canonical workspace 同时只保留一个 active writer
5. child 给出证据，Main 验证、整合并负责最终结果
```

新的 project child 默认拿 fresh context。Main 会把目标、范围、约束、验收条件和已经接受的事实传过去，而不是把整段主对话复制一遍。

当 Codex Host 已信任并启用插件自带的 spawn guard 时，`spawn_agent` 真正执行前还会机械核对 prepared state、exact Agent type、task name 和 `fork_turns=none`。这个 Hook 只守调用边界，Codex Native Subagents 仍然负责真实 child identity 和 lifecycle。

这也是项目的取舍。它希望减少重复调查和上下文混杂，同时避免为了“多 Agent”而制造更多协调工作。

## 安装

```bash
codex plugin marketplace add R-jed/subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

安装后启动一个新的 Codex session，然后从 Skill 菜单选择 **Dispatch**。

第一次真正需要 child 时，插件会检查自己管理的五个 Agent profiles。如果需要首次创建，当前任务会返回 `RESTART_REQUIRED`。重新开一个 Codex task/session，再次选择 Dispatch 即可。

Profile provisioning、Doctor helpers、Runtime Attestation helpers 和 spawn guard 需要 Python 3.11+。完整流程见 [Plugin Installation](docs/plugin-installation.md)。

## 你会用到的六个 Skill

| Skill | 做什么 |
|---|---|
| **Dispatch** | 开始或继续一次编排 |
| **Preview** | 先看看会怎么分工，不创建 child |
| **Status** | 看一次当前状态 |
| **Steer** | 给正在工作的同一个 child 追加指导 |
| **Takeover** | 安全结束旧 writer 后，把职责交回 Main |
| **Doctor** | 检查安装版本、更新状态、spawn guard、profiles、state 和 runtime evidence |

`Status` 只观察一次，不做后台轮询。`Steer` 继续使用同一个 child。`Takeover` 会先确认旧 writer 已经安全结束。

不确定任务值不值得拆时，先用 **Preview**。

## 目前怎么分工

当前 production policy 使用下面五条职责通道：

| 当前模型 / 思考强度 | 对外活动 | 常见用途 |
|---|---|---|
| Luna Max | 读取 | 窄范围读代码、追调用链、整理可核对事实 |
| Luna Max | 执行 | 做法已经明确后的有界实现和测试 |
| Terra XHigh | 调研 | 大范围只读调查和跨文件证据整理 |
| Sol High | 执行 | 实现过程中需要实质技术判断的工作 |
| Sol High | 决策 / 验收 | 技术决策或独立 Final Review |

这是当前 `contracts/policy.json` 的运行策略。项目目前没有证据证明这套模型组合对所有任务都最优。

## 几条不会放松的规则

分工可以灵活，下面这些边界保持保守：

* Main 负责项目级委派，project child 不继续创建 project children。
* 同一次编排的 canonical workspace 保持一个 active writer。
* 每个职责使用 `contracts/policy.json` 指定的 exact `subagents_dispatch_*` Agent type。
* 每个新的 project child 都显式使用 `fork_turns=none`。
* `UNKNOWN` 就保持未知。它不会自动授权 replacement、reroute、ownership transfer 或冲突写入。
* child 的输出需要 Main 验证和接受，最终完成状态仍由 Main 判断。
* Final Review 看变更后果决定是否需要，不固定多开一个 reviewer。

完整规则见 [Architecture](docs/architecture.md)、[Routing](contracts/routing.md)、[Guardrails](contracts/guardrails.md) 和 [Composition Contract](contracts/composition.md)。

## 配置不等于运行时证据

模型、reasoning effort 和 permission 这类信息分成四层：

```text
Configured
→ Requested
→ Accepted
→ Observed
```

写在配置里只能说明配置意图。只有 Host 真正暴露的运行时证据才能支持 Observed。Doctor 的显式 live-route 流程可以在需要时核对 exact child。普通 Dispatch 不扫描本地 Codex rollouts。

任务结束时，Receipt 只汇报实际发生的编排和验收事实，例如：

```text
编排: Luna Max 读取 · Luna Max 执行 · Sol High 验收
控制: Status×1
验收: 1轮 · 通过
```

跨职责需要复用已经接受的调查结果时，可以通过 Handoff Capsule 传 accepted facts、evidence refs 和 open questions，不需要搬运完整 transcript。

更多细节见 [Runtime Attestation](docs/runtime-attestation.md)、[Handoff Contract](contracts/handoff.md) 和 [Privacy](PRIVACY.md)。

## 什么时候适合用

Dispatch 通常在这些任务里更有意义：代码库调查可以并行，某一部分调查很大但只读，实现前需要先收集证据，变更影响较大需要独立复核，或者一个长任务天然包含几块边界清楚的职责。

如果任务很小、强串行、上下文已经齐全，Main 直接完成通常更简单。用户授权范围还不清楚，或者关键 Host 能力仍是 `UNKNOWN` 时，也不应该为了分工强行继续。

## 关于性能

项目已经有 single-agent Codex 与 explicit Dispatch 的实验协议、campaign schema 和 validator，可以比较正确性、安全、返工、wall-clock、Main / child token、总 token、上下文压力和 Host route evidence。

**在重复真实任务数据完成前，本 README 不声称 subagents-dispatch 已经被证明更快、更省总 Token，或者当前五个 model / effort 是最优配置。**

方法见 [Experiment Protocol](docs/experiment-protocol.md) 和 [Evaluations](evals/README.md)。

## 更新和卸载

只想检查有没有新版本时，选择 **Doctor** 并明确要求检查更新。它会刷新这个插件的 Marketplace snapshot 并报告 Installed / Available，不会安装 Plugin。

明确要求更新时，Doctor 会刷新 Marketplace、安装版本化 Plugin，并在新安装目录里复核 manifest、managed profiles 和新 Doctor。底层仍使用 Codex 支持的命令：

```bash
codex plugin marketplace upgrade subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

更新后启动新的 Codex session。插件 Hook 发生变化时，Codex 可能要求重新 review/trust，Doctor 不会替用户静默修改这个 Host 状态。

如果已经创建过 managed Agent profiles，请先保持插件已安装，选择 **Doctor** 并明确要求卸载 subagents-dispatch 的 managed profiles。Doctor 会校验 ownership manifest 和文件 SHA-256，只删除能够证明属于本插件的配置。

然后移除 Plugin 和 Marketplace：

```bash
codex plugin remove subagents-dispatch@subagents-dispatch
codex plugin marketplace remove subagents-dispatch
```

遇到 ownership 冲突时不要用 `rm`、通配符或手工删除绕过检查。完整流程见 [Plugin Installation](docs/plugin-installation.md)。

## 项目结构

<details>
<summary><strong>展开目录</strong></summary>

```text
.
├── .agents/plugins/                  # Marketplace registration
├── .codex-plugin/                    # Plugin manifest
├── agent-profiles/                   # five managed Agent profiles
├── hooks/                            # default-discovered spawn guard + launchers
├── contracts/                        # routing, state, safety and evidence contracts
├── scripts/                          # provisioning, validation and runtime helpers
├── skills/
│   ├── dispatch/                     # start or resume orchestration
│   ├── preview/                      # predict without execution
│   ├── status/                       # one-shot status observation
│   ├── steer/                        # guide an existing delegation
│   ├── takeover/                     # safely return responsibility to Main
│   └── doctor/                       # installation and runtime diagnostics
├── docs/                             # architecture, runtime, experiment and release docs
├── evals/                            # behavioral and experiment fixtures
└── tests/                            # regression and adversarial tests
```

</details>

主要文档：

[安装](docs/plugin-installation.md) · [架构](docs/architecture.md) · [Native Subagent Runtime](docs/native-subagent-runtime.md) · [Runtime Attestation](docs/runtime-attestation.md) · [Experiment Protocol](docs/experiment-protocol.md) · [Composition Contract](contracts/composition.md) · [CHANGELOG](CHANGELOG.md) · [Privacy](PRIVACY.md)

## License

[MIT](LICENSE)
