<p align="center">
  <img src="assets/subagents-dispatch-banner.png" alt="subagents-dispatch" width="900">
</p>

<h1 align="center">subagents-dispatch</h1>

<p align="center"><em>Codex 子代理调度框架。</em></p>

<p align="center">
  <a href="README_EN.md">English</a> · <a href="README_AI.md">AI Agent</a> · <a href="docs/plugin-installation.md">安装</a> · <a href="docs/architecture.md">架构</a> · <a href="LICENSE">MIT</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-2.1.2-green.svg" alt="Version">
  <img src="https://img.shields.io/badge/Codex-%E5%8E%9F%E7%94%9F%20Subagents-111827.svg" alt="Codex 原生 Subagents">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
</p>

---

> **如果你是 AI Agent，请跳转到 [README_AI.md](README_AI.md) 并严格按照说明操作。**

subagents-dispatch 是一个 Codex 插件。它负责把一个大任务拆给几个专门的小助手去干，主会话留目标、盯进度，最后验收结果。

## 快速开始

在 Codex App 里，输入 `/` 打开 Skill 菜单，选择 **Subagents Dispatch**，然后输入你的任务。

比如你说：

```text
给 /api/users 加分页参数，补上测试
```

插件会自己判断怎么分工。查现有接口、查相关测试，这两件只读的活可以同时进行；等信息查清楚了，再派一个负责写代码的小助手动手改。也就是说：查资料可以并行，但同一份代码不会有两个写入者同时改。最后仍由主会话检查、整合，把最终结果交给你。

简单任务不会为了“多人协作”硬拆。只有真能更快、更稳、或更适合分工的活，才会派出小助手。

## 运行中控制

先从 `/` 菜单选择 **Subagents Dispatch**，再使用下面这些控制。

想先看看准备怎么分工，不真的启动小助手：

```text
preview 给 /api/users 加分页参数，补上测试
```

任务已经在跑，想看看现在做到哪一步：

```text
status
```

想给正在工作的小助手补一句新要求：

```text
steer U2: 先看现有的分页中间件
```

想停止某个职责，改由主会话接手：

```text
takeover U2
```

## 执行摘要：最后告诉你刚才做了什么

只要这次任务真的启动过小助手，结束时会多一行简单说明。

```text
Dispatch: 读取 → 实现 · 完成 · 未重试 · 无需最终复核
```

这行摘要只写系统能确认的事实，比如用了哪些角色、有没有重试、有没有做最终复核。它不写小助手的内部思考过程，也不根据模型名称或运行时长去猜 Token 用量和费用。

## 交接包（Handoff Capsule）：避免后一个 Agent 从头再查一遍

每个小助手都从一份新的上下文开始。什么都不传，后一个很可能会把前一个已经查清的内容重新查一遍，白费功夫。

Handoff Capsule 就是一份很小的“交接便签”。主会话把已经核实过、后面还能继续用的信息整理进去，交给下一个职责。

- **已经确认的事实可以直接接着用**。只有主会话检查并接受过的内容，才会放进交接包
- **`DO NOT REDO` 表示“这部分不用重做”**。已经有可靠证据的检查，可以明确告诉下一个不用重复
- **主会话负责把关**。小助手自己说“我完成了”还不够，主会话要检查证据后才会把它当成已知事实
- **`STALE IF` 表示“出现这些变化后，旧结论要作废”**。比如相关文件后来被改了，就需要重新检查

## 四条必须守住的规则

分工再多，安全规则一条不少。核心是下面四条。

- **同一份代码，同一时间只让一个写入者修改**。同一次 subagents-dispatch 调度里，同一个 Git 工作目录同一时间最多只有一个写入者实际改文件，这个写入者只能是主会话、Worker 或 Solver。前一个写入者还没有确认停止，主会话不会抢着改同一份代码。其他独立的 Codex 会话、编辑器、自动化脚本和外部程序不受这个规则控制
- **子 Agent 不能继续叫更多子 Agent**。所有分工都只由主会话安排。用户的目标、权限、团队组成和最终结果始终由主会话负责
- **`UNKNOWN` 就停下来确认，不靠猜**。遇到无法确认某个职责的真实状态时，不会随便换一个 Agent 顶上，不会自动重试，也不会偷偷改变任务路线
- **只报告确认过的事实**。执行摘要不会根据模型名称、运行时间或输出长度去猜 Token 用量和费用

## 角色

大部分活，主会话自己就干完了。只有值得分工时，下面这些角色才会被叫出来。

| 角色 | 干什么 |
|------|--------|
| Luna Reader | 读代码、追调用链、收集事实 |
| Luna Worker | 需求和做法已经清楚时，负责实现和测试 |
| Sol Solver | 一边实现、一边还需要做技术判断的工作 |
| Terra Investigator | 范围较大的只读调查和证据整理 |
| Sol Advisor | 独立技术判断，或需要时做最终复核 |

没有固定人数，也没有固定流水线。需要并行、隔离、专门能力或独立判断时，才会叫不同角色来帮忙。

## 安装

```bash
codex plugin marketplace add R-jed/subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

插件装好后，先开一个新的 Codex 会话。

第一次通过 **Subagents Dispatch** 确实需要子 Agent 时，subagents-dispatch 会自动准备自己的 5 个 Agent 配置文件。你不需要理解 TOML，也不用为这些内部配置多点一次确认。

Codex 会在任务启动时读取可用的 Agent 列表，所以刚刚新建的配置不能在当前任务里立刻生效。第一次准备完成后，系统会请你新开一个任务，再从 `/` 菜单选择 **Subagents Dispatch** 并重跑刚才的请求。当前任务不会先做一次明知道看不到新 Agent 的失败尝试。以后这些配置已经提前存在，正常任务就可以直接委托。

如果发现同名文件有冲突、文件被改过、无法确认文件归谁管理，或者路径本身不安全，系统不会直接覆盖，而会停止并让 **Subagents Doctor** 告诉你该怎么处理。

## 更新

```bash
codex plugin marketplace upgrade subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

也可以从 `/` 菜单选择 **Subagents Doctor**，让它帮你升级。

更新后开一个新的 Codex 会话。

## 卸载

```bash
# 移除插件注册
codex plugin remove subagents-dispatch@subagents-dispatch

# 移除插件市场注册和缓存
codex plugin marketplace remove subagents-dispatch
```

如果之前运行过需要 Agent 的任务，还需要删除相关文件。

```bash
# 删除 5 个 Agent 配置文件
rm ~/.codex/agents/subagents-dispatch-reader.toml
rm ~/.codex/agents/subagents-dispatch-worker.toml
rm ~/.codex/agents/subagents-dispatch-solver.toml
rm ~/.codex/agents/subagents-dispatch-investigator.toml
rm ~/.codex/agents/subagents-dispatch-advisor.toml

# 删除安装记录文件
rm ~/.codex/.subagents-dispatch-agents.json
```

## 常见问题

**会不会有几个 Agent 同时改代码，把文件搞乱？**
同一次调度里不会。系统会保证同一份代码同一时间最多只有一个写入者，避免多个 Agent 并发抢写。但任何代码修改本身仍可能有 bug，所以主会话最后还会检查和验证结果。

**每次都要我盯着吗？**
不用。真启动了子 Agent 时，最后会有一行执行摘要，告诉你刚才干了什么、有没有重试、有没有复核。

**我的活很简单，也要用它吗？**
简单任务它不会硬拆。能自己干完的活，主会话自己就干了。

## 项目结构

```text
.
├── .agents/plugins/                  # Codex 插件市场注册
├── .codex-plugin/                    # 插件清单
├── agent-profiles/                   # 五个 Agent 配置文件
├── policy-contract.json              # 角色定义和核心规则
├── scripts/                          # 安装、检查和运行记录工具
├── skills/
│   ├── dispatch/                     # Subagents Dispatch Skill
│   └── doctor/                       # Subagents Doctor Skill
├── docs/                             # 架构和运行边界文档
├── evals/                            # 评估用例
└── tests/                            # 回归测试
```

## 文档

- [安装说明](docs/plugin-installation.md)
- [架构说明](docs/architecture.md)
- [Codex 原生 Subagent 运行边界](docs/native-subagent-runtime.md)
- [AI Agent 项目参考](README_AI.md)

## 许可证

[MIT](LICENSE)
