<p align="center">
  <img src="assets/subagents-dispatch-banner.png" alt="subagents-dispatch" width="900">
</p>

<h1 align="center">subagents-dispatch</h1>

<p align="center"><em>让 Codex 在值得分工时分工，同时把控制权留在主会话。</em></p>

<p align="center">
  <a href="README_EN.md">English</a> · <a href="docs/plugin-installation.md">安装</a> · <a href="docs/architecture.md">架构</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-2.1.2-green.svg" alt="Version">
  <img src="https://img.shields.io/badge/Codex-%E5%8E%9F%E7%94%9F%20Subagents-111827.svg" alt="Codex 原生 Subagents">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
</p>

---

> **如果你是 AI Agent，请跳转到 [README_AI.md](README_AI.md) 并严格按照说明操作。**

subagents-dispatch 是一个 Codex 原生 Subagent 调度插件。主会话继续负责用户目标、范围、权限、整合和最终验收；插件只在分工确实有价值时，把边界清楚的职责交给一层专门子代理。

简单任务可以完全留在 Main。复杂任务可以把独立读取并行化，把大范围调查隔离到单独上下文，把需要技术判断的工作交给更合适的模型通道，同时保持同一工作区只有一个写入者。

## 它改变了什么

普通单会话任务里，读取、调查、实现、判断和复核都可能堆在同一段上下文里。

subagents-dispatch 把这些工作按职责拆开：

```text
用户目标
  ↓
Main
  ├─ 判断是否值得委派
  ├─ 编译职责 / 权限 / 验收条件
  ├─ 接受和验证子代理证据
  └─ 负责最终结果
       │
       ├─ 读取 / 调研可以并行
       ├─ 写入保持单写入者
       ├─ 需要判断时才使用更强职责通道
       └─ 必要时独立验收
```

这里没有固定“必须叫几个子代理”的目标。一个合理的 Dispatch 可以启动多个子代理，也可以一个都不启动。

## 快速开始

```text
选择 Dispatch，然后输入：给 /api/users 加分页参数，补上测试
```

Main 会先判断有没有值得独立处理的职责。例如现有接口和测试结构可以并行读取，语义明确后再交给一个写入职责实现。如果任务很小，Main 可以直接完成，不为了显示“多代理”而强行拆分。

## 你仍然掌控全局

六个 Skill 都是显式入口，不会因为安装插件就自动接管普通任务。

| Skill | 用途 |
|---|---|
| **Dispatch** | 开始或继续一次有价值的编排 |
| **Preview** | 只看预计怎么分工，不启动子代理、不写状态 |
| **Status** | 对当前编排做一次状态观察 |
| **Steer** | 给同一个职责、同一个 attempt、同一个子代理追加指导 |
| **Takeover** | 等旧写入者确认停止后，把职责安全交回 Main |
| **Doctor** | 检查插件、Skills、Agent profiles、状态和运行时路由证据 |

`Status` 不会后台轮询。`Steer` 不会偷偷换一个子代理。`Takeover` 也不会在旧写入者还是 `UNKNOWN` 或 `INTERRUPTED` 时让 Main 抢写同一工作区。

## 五个角色

角色描述的是职责边界；模型配置是当前运行策略。中文用户界面只展示活动类型，不暴露内部角色名。

| 当前模型 / 思考强度 | 对外活动 | 负责什么 |
|---|---|---|
| Luna Max | 读取 | 窄范围读代码、追调用链、收集可核对事实 |
| Luna Max | 执行 | 做法已经决定后的边界明确实现和测试 |
| Terra XHigh | 调研 | 大范围只读调查、跨文件证据整理和综合 |
| Sol High | 执行 | 实现过程中存在不可分离的实质技术判断 |
| Sol High | 决策 / 验收 | 只读技术决策或独立 Final Review |

这些配置是当前 policy，不代表我们已经证明它们是所有任务上的“最优组合”。模型和 reasoning effort 的正式校准由真实实验数据决定，见 [Experiment Protocol](docs/experiment-protocol.md)。

## 实际跑的是不是配置里的模型

profile 写着 `Luna Max`，只能证明配置意图；Host 接受了某个 `agent_type`，也只能证明角色被接受。

需要严格核对时，Doctor 的 live-route 流程把事实分开记录：

```text
Configured
→ Requested
→ Accepted
→ Observed
```

Observed 只来自 Host 真正暴露的运行时信息。Host 公共 metadata 不完整时，可以对 exact child 的本地 Codex rollout 做只读 allowlist 检查，核对 model、reasoning effort、sandbox / permission、parent / child identity。配置值和子代理自报身份都不能填进 Observed。

完整协议见 [Runtime Attestation](docs/runtime-attestation.md)。

## 子代理之间不互相灌完整上下文

新 project child 默认使用 fresh context。Main 只把当前职责真正需要的目标、范围、约束、验收和已接受证据传进去。

如果后续职责会重复一段昂贵调查，Main 可以创建一个很小的 Handoff Capsule：

```text
ACCEPTED FACTS
ACCEPTED EVIDENCE
ARTIFACT REFS
DO NOT REDO
OPEN QUESTIONS
STALE IF
```

只有 Main 已检查并接受的内容可以进入交接。完整日志、整段 transcript、私有 reasoning、大段源码不会为了“省一次读取”塞给下一个子代理。需要保留完整证据时，使用 references-first 的 Evidence Artifact，再在 Handoff 里只传引用。

## 调度摘要只报编排事实

```text
编排: Luna Max 读取 · Luna Max 执行 · Sol High 验收
控制: Status×1
验收: 1轮 · 通过
```

Receipt 说明子代理怎么被调度、控制和验收，不代替 Main 对任务结果的最终说明。它不会根据模型名字、运行时间或输出长度去猜 Token、成本或真实运行模型。

## 和现有项目规则、Skills、Hooks 一起工作

subagents-dispatch 不复制一套新的 AGENTS 规则系统，也不会把其他 Skill 的完整提示词塞进每个 child。

它使用约束交集：

```text
Host 能力和策略
∩ 当前用户 / system / developer 授权
∩ Host 生效的项目规则
∩ 已接受的上游 Skill / workflow 约束
∩ subagents-dispatch guardrails
∩ 当前职责 packet
```

更低层只能缩小权限，不能扩大上层授权。外部 Skill 可以规定“这项工作应该怎么做”，但不能让一个只读职责突然获得写权限，也不能突破当前用户范围。Hooks 可以提供观察或阻断信号，但不会成为第二个 scheduler、第二份状态或第二套 authority。

完整规则见 [Composition Contract](contracts/composition.md)。

## 安全边界

- **单写入者**：同一次编排、同一 canonical workspace 同时只有一个写入者。旧 writer 没有被 Host 证明停止前，Main 不能冲突写入
- **一层委派**：只有 Main 负责项目级分工，child 不继续创建 project children
- **`UNKNOWN` 不猜**：运行状态无法确定时不自动替换、不偷偷重试、不用另一个角色顶上
- **恢复有界**：同一职责最多两个 materialized Agent attempts；same-child resume 不算 retry
- **Main 保留最终 authority**：child、hook、外部 Skill、配置文件都不能自己宣布任务完成
- **普通 Dispatch 不扫描 Codex rollout**：本地 rollout inspection 只用于显式 runtime attestation

## 性能数据：现在不提前写结论

这个项目的目标之一，是验证合理的职责隔离和调度能不能减少重复发现、降低 Main context 压力，并在有并行机会时缩短完成时间。但这些是要用真实任务证明的问题。

目前仓库已经有正式实验协议和 campaign validator，用来比较：

```text
同一个真实 repo / exact base revision / exact task
single-agent Codex
vs
explicit Dispatch
```

实验会分别记录正确性、安全、返工、wall-clock、Main / child token、总 token、上下文压力和 Host 路由证据。小任务也必须进入样本，因为好的 dispatcher 应该允许 `0 child`。

**在重复真实任务数据完成前，本 README 不声称 subagents-dispatch 已经被证明更快、更省总 Token，或者当前五个 model / effort 是最优配置。**

方法见 [Experiment Protocol](docs/experiment-protocol.md) 和 [Evaluations](evals/README.md)。真实结果完成后，这里只发布能够回溯到 campaign、Host、repo、task、repeat 和 oracle 的数据。

## 什么时候不值得 Dispatch

以下情况通常更适合 Main 直接做：

- 很小、很局部、上下文已经齐全的任务
- 后一步完全依赖前一步、没有独立工作可展开的强串行任务
- 用户授权范围还没明确的任务
- 需要的 Host 控制能力是 `UNKNOWN`，而正确性依赖那个能力
- 为了“看起来用了多个 Agent”才想拆分的任务

Preview 可以在不执行的情况下先看预计编排。

## 安装

```bash
codex plugin marketplace add R-jed/subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

首次真正需要委派时选择 Dispatch。插件只管理自己的五个 Agent profiles；如果 profiles 需要首次创建，当前任务会进入 `RESTART_REQUIRED`，然后在新的 Codex task/session 里重新选择 Dispatch。

详细步骤和安全边界见 [安装说明](docs/plugin-installation.md)。

## 更新

```bash
codex plugin marketplace upgrade subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

也可以选择 **Doctor** 检查安装和 managed profiles 状态。

## 卸载

```bash
codex plugin remove subagents-dispatch@subagents-dispatch
codex plugin marketplace remove subagents-dispatch
```

如果已经创建过 managed profiles，再删除插件自有的六个 managed 文件：

```bash
rm ~/.codex/agents/subagents-dispatch-reader.toml
rm ~/.codex/agents/subagents-dispatch-worker.toml
rm ~/.codex/agents/subagents-dispatch-solver.toml
rm ~/.codex/agents/subagents-dispatch-investigator.toml
rm ~/.codex/agents/subagents-dispatch-advisor.toml
rm ~/.codex/.subagents-dispatch-agents.json
```

完整卸载流程见 [安装说明](docs/plugin-installation.md)，不要删除未证明属于本插件的 Agent 配置。

## 隐私

只有需要跨 turn 协调时，普通编排才会在操作系统临时目录维护一个 root-thread scoped 的紧凑 coordination capsule；Preview 和零子代理 Dispatch 不需要创建它，正常终态会清理。它不用于保存 raw prompt、完整 transcript、私有 reasoning、credentials 或整份源码。

显式 Runtime Attestation 对本地 rollout 的访问边界见 [PRIVACY.md](PRIVACY.md)。

## 项目结构

```text
.
├── .agents/plugins/                  # Codex Marketplace 注册
├── .codex-plugin/                    # Plugin manifest
├── agent-profiles/                   # 五个 managed Agent profiles
├── contracts/                        # 编排、状态、证据和安全契约
├── scripts/                          # 安装、校验、状态和 runtime evidence 工具
├── skills/
│   ├── dispatch/                     # 开始或继续编排
│   ├── preview/                      # 只预览，不执行
│   ├── status/                       # 单次状态检查
│   ├── steer/                        # 引导现有委派
│   ├── takeover/                     # 安全把职责交回 Main
│   └── doctor/                       # 安装和运行时诊断
├── docs/                             # 架构、Host、实验和发布文档
├── evals/                            # 静态、行为和实验 schema
└── tests/                            # 回归与对抗性测试
```

## 文档

- [安装说明](docs/plugin-installation.md)
- [架构说明](docs/architecture.md)
- [Codex 原生 Subagent 运行边界](docs/native-subagent-runtime.md)
- [Runtime Attestation](docs/runtime-attestation.md)
- [Experiment Protocol](docs/experiment-protocol.md)
- [Composition Contract](contracts/composition.md)
- [行为评估](docs/behavioral-evals.md)
- [OpenAI 参考](docs/openai-references.md)
- [AI Agent 项目参考](README_AI.md)
- [变更日志](CHANGELOG.md)
- [隐私说明](PRIVACY.md)
- [服务条款](TERMS.md)

## License

[MIT](LICENSE)
