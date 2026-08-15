<p align="center">
  <img src="assets/subagents-dispatch-banner.png" alt="subagents-dispatch" width="900">
</p>

<h1 align="center">subagents-dispatch</h1>

<p align="center"><em>让 Codex 在值得分工时分工，让 Main 始终掌控目标、权限和最终结果。</em></p>

<p align="center">
  <a href="README_EN.md">English</a> · <a href="docs/plugin-installation.md">安装</a> · <a href="docs/architecture.md">架构</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-3.0.0-green.svg" alt="Version">
  <img src="https://img.shields.io/badge/Codex-Native%20Subagents-111827.svg" alt="Codex Native Subagents">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
</p>

> **如果你是 AI Agent，请跳转到 [README_AI.md](README_AI.md) 并严格按照说明操作。**

subagents-dispatch 是一个基于 Codex Native Subagents 的调度插件。Main 继续负责用户目标、授权范围、技术整合和最终验收。插件只把值得独立处理的职责交给专门的 Subagent，并尽量让每个 child 只拿到完成当前职责真正需要的上下文。

Codex 仍然是唯一的 Agent runtime。这个项目不额外运行 daemon、任务数据库、事件总线或独立 scheduler。

## 安装

```bash
codex plugin marketplace add R-jed/subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

安装后启动一个新的 Codex session，然后从 Skill 菜单选择 **Dispatch**。

第一次真正需要创建 child 时，插件会检查自己管理的五个 Agent profiles。如果 profiles 需要首次创建，当前任务会返回 `RESTART_REQUIRED`。重新开一个 Codex task/session，再次选择 Dispatch 即可。

Profile provisioning、Doctor helpers 和 Runtime Attestation helpers 需要可用的 Python 3.11+。完整安装、更新和卸载流程见 [Plugin Installation](docs/plugin-installation.md)。

## 它解决什么问题

复杂开发任务经常把读代码、调查、实现、技术判断和复核全部堆进 Main 的同一段上下文。任务越长，重复发现、上下文污染和职责混杂越容易出现。

subagents-dispatch 把 Main 放在技术负责人的位置：

```text
用户任务
  ↓
Main
  ├─ 判断是否值得委派
  ├─ 划分职责、权限和验收条件
  ├─ 并行展开独立读取或调查
  ├─ 保持 canonical workspace 单写入者
  ├─ 验证并整合 child 输出
  └─ 对最终结果负责
```

委派没有最低数量。小任务可以由 Main 直接完成，`0 child` 是完全有效的结果。复杂任务也只创建当前阶段真正有价值的 children。

一个典型请求可以直接写成：

```text
选择 Dispatch
给 /api/users 加分页参数，补上测试
```

Main 会先判断现有接口、测试结构、实现和复核中哪些职责值得独立展开，再决定是否创建 child。

## 六个显式 Skill

安装插件不会自动接管普通 Codex 任务。六个入口都需要显式选择。

| Skill | 作用 |
|---|---|
| **Dispatch** | 开始或继续一次有价值的编排 |
| **Preview** | 只看预计分工，不创建 child，不写 active state |
| **Status** | 对当前编排做一次状态观察 |
| **Steer** | 给同一个 unit、attempt 和 child 追加指导 |
| **Takeover** | 在旧 writer 已安全结束后，把职责交回 Main |
| **Doctor** | 检查 Plugin、Skills、profiles、state 和 runtime evidence |

`Status` 只观察一次，不做后台轮询。`Steer` 保持同一个 child。`Takeover` 在旧 writer 仍为 `RUNNING`、`INTERRUPTED` 或 `UNKNOWN` 时不会释放冲突写权限。

## 调度规则

当前 production policy 使用五条职责通道：

| 当前模型 / 思考强度 | 对外活动 | 典型职责 |
|---|---|---|
| Luna Max | 读取 | 窄范围读代码、追调用链、收集可核对事实 |
| Luna Max | 执行 | 做法已明确后的有界实现和测试 |
| Terra XHigh | 调研 | 大范围只读调查和跨文件证据整理 |
| Sol High | 执行 | 实现与实质技术判断无法拆开的工作 |
| Sol High | 决策 / 验收 | 技术决策或独立 Final Review |

这些 lane 是当前 `contracts/policy.json` 的运行策略，不代表已经证明为所有任务的最优组合。

项目有几条硬边界：

* Main 负责项目级委派，project child 不继续创建 project children。
* 同一次编排的 canonical workspace 保持一个 active writer。
* 每个职责精确绑定 `contracts/policy.json` 指定的 `subagents_dispatch_*` Agent type，其他 built-in role、alias 或 model-equivalent profile 不能替代。
* `UNKNOWN` 保持未知。它不能自动授权 replacement、reroute、ownership transfer 或冲突写入。
* child 输出需要经过 Main 接受和整合，最终完成状态仍由 Main 判断。
* Final Review 按变更后果触发，不为了形式固定增加一个 reviewer。

详细规则见 [Architecture](docs/architecture.md)、[Routing](contracts/routing.md)、[Guardrails](contracts/guardrails.md) 和 [Composition Contract](contracts/composition.md)。

## 上下文、证据和运行时事实

新的 project child 默认使用 fresh context。Main 只传当前职责需要的目标、范围、约束、验收条件和已经接受的证据。需要跨职责复用调查结果时，可以用紧凑的 Handoff Capsule 传 accepted facts、evidence refs 和 open questions，避免把完整 transcript 或大段源码重复塞给下一个 child。

对于模型、reasoning effort 和 permission 等运行时事实，项目明确区分：

```text
Configured
→ Requested
→ Accepted
→ Observed
```

配置文件只能证明配置意图。Observed 需要 Host 真正暴露的运行时证据。Doctor 的显式 live-route 流程可以在需要时核对 exact child；普通 Dispatch 不扫描本地 Codex rollouts。

Receipt 只汇报编排和验收事实，例如：

```text
编排: Luna Max 读取 · Luna Max 执行 · Sol High 验收
控制: Status×1
验收: 1轮 · 通过
```

更多细节见 [Runtime Attestation](docs/runtime-attestation.md)、[Handoff Contract](contracts/handoff.md) 和 [Privacy](PRIVACY.md)。

## 什么时候值得用

Dispatch 比较适合这些任务：

* 可以并行读取多个独立区域的代码库调查
* 需要把大范围只读调查和 Main 的实现上下文隔离
* 实现前有明确的证据收集阶段
* 存在可独立验收的高影响变更
* 一个长任务中有多个边界清楚、依赖关系明确的职责

这些情况通常让 Main 直接完成更简单：

* 很小、很局部，而且相关上下文已经齐全
* 强串行任务，每一步都依赖上一步结果
* 用户授权范围仍不明确
* 正确性依赖某个 Host 控制能力，但该能力当前还是 `UNKNOWN`
* 唯一目的只是让任务看起来使用了多个 Agent

不确定是否值得拆分时，可以先选择 **Preview**。

## 性能结论

项目包含 single-agent Codex 与 explicit Dispatch 的实验协议、campaign schema 和 validator，用于比较正确性、安全、返工、wall-clock、Main / child token、总 token、上下文压力和 Host route evidence。

**在重复真实任务数据完成前，本 README 不声称 subagents-dispatch 已经被证明更快、更省总 Token，或者当前五个 model / effort 是最优配置。**

方法见 [Experiment Protocol](docs/experiment-protocol.md) 和 [Evaluations](evals/README.md)。

## 更新和卸载

更新：

```bash
codex plugin marketplace upgrade subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

更新后启动新的 Codex session。

如果已经创建过 managed Agent profiles，请先保持插件已安装，选择 **Doctor** 并明确要求卸载 subagents-dispatch 的 managed profiles。Doctor 会校验 ownership manifest 和文件 SHA-256，只删除能够证明属于本插件的配置。

然后移除 Plugin 和 Marketplace：

```bash
codex plugin remove subagents-dispatch@subagents-dispatch
codex plugin marketplace remove subagents-dispatch
```

遇到 ownership 冲突时不要用 `rm`、通配符或手工删除绕过检查。完整流程见 [Plugin Installation](docs/plugin-installation.md)。

## 项目结构

```text
.
├── .agents/plugins/                  # Marketplace registration
├── .codex-plugin/                    # Plugin manifest
├── agent-profiles/                   # five managed Agent profiles
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

主要文档：

[安装](docs/plugin-installation.md) · [架构](docs/architecture.md) · [Native Subagent Runtime](docs/native-subagent-runtime.md) · [Runtime Attestation](docs/runtime-attestation.md) · [Experiment Protocol](docs/experiment-protocol.md) · [Composition Contract](contracts/composition.md) · [CHANGELOG](CHANGELOG.md) · [Privacy](PRIVACY.md)

## License

[MIT](LICENSE)
