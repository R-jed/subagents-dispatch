<p align="center">
  <img src="assets/subagents-dispatch-banner.png" alt="subagents-dispatch" width="900">
</p>

<h1 align="center">subagents-dispatch</h1>

<p align="center"><em>给 Codex 一支靠谱的小队。大任务分头做，小任务别折腾。</em></p>

<p align="center">
  <a href="README_EN.md">英文版</a> · <a href="docs/plugin-installation.md">安装</a> · <a href="docs/architecture.md">架构</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Codex-Native%20Subagents-111827.svg" alt="Codex 原生子代理">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="许可证"></a>
</p>

> **如果你是 AI Agent，请跳转到 [README_AI.md](README_AI.md)。**

你给 Codex 一个稍大的任务：改 API、补测试、追调用链，再顺手看看前端会不会受影响。

一个主会话从头包到尾当然能做。只是任务一长，读代码、查资料、写实现、跑测试、做复核全塞进同一个上下文，脑子很快就会挤成早高峰。

**subagents-dispatch 会在值得分工的时候，临时给 Codex 组一支小队。**

有人读代码，有人查影响，有人动手实现，有人负责复核。主会话仍然掌握目标、判断和最终结果。任务很小的时候，它可以一个子代理都不叫。

## Codex 已经有 Subagents，为什么还需要它

Codex 提供原生 Subagents。这个插件提供一套面向工程任务的协调策略。

它会判断什么时候值得分工，把工作拆成有完成条件和依赖关系的职责，限制无意义的并发，在同一个可变工作区避免多个写入者互相踩文件，并要求主会话验收结果后再解锁后续工作。Host 状态说不清时会保留 `UNKNOWN`，不会把猜测当成授权。

## 30 秒看懂

比如你说：

```text
给 /api/users 加分页，补测试，再检查前端调用有没有受影响。
```

一次合理的分工可能是：

```text
主会话
├─ 先读 API、测试和调用链
├─ 同时检查前端和跨文件影响
├─ 边界清楚后安排实现
└─ 变更比较大时再做一次独立复核
```

最后由主会话把结果收回来，检查证据，整合代码，再决定任务到底算不算完成。

如果主会话看两眼就发现这事三分钟能做完，它自己做。

## 它适合什么时候用

当任务里有几块可以分头调查的工作，或者实现前需要先把影响范围摸清，subagents-dispatch 通常比较有价值。

例如：

- 要同时追多条调用链
- 要先调查再实现
- 改动跨前后端、配置、测试或文档
- 有一块工作很适合独立交给另一个子代理
- 变更影响较大，希望有人单独复核

任务很小、步骤强串行、上下文已经齐全时，主会话自己做通常更省事。

## 你只需要记住两个入口

| 入口 | 什么时候用 |
|---|---|
| **Orchestrate** | 判断是否需要分工，并负责规划、执行、继续、纠正、接管、复核和整合 |
| **Doctor** | 检查插件、Agent 配置、Host 集成和运行状态，或者执行你明确要求的安全维护 |

Orchestrate 也支持只看计划。任务运行后，进度、暂停、接管、继续都留在同一个入口里。

## 它会克制自己

- 小任务允许 0 个子代理
- 最多 4 个受管理子代理，4 是安全上限
- 同一个可变工作区同时只有一个受管理的写入者
- 子代理只拿完成自己那份工作需要的上下文
- 调查结果要有证据，主会话复核后再接受
- 状态说不清时先停住
- 最终交付仍由主会话负责

单写入者是工作区边界。当前版本只管理一个 canonical workspace。详细说明见 [写入者边界](docs/writer-boundary.md)。

## 当前固定阵容

五个 managed profile 保留不同职责和权限边界，但当前 release candidate 的 child 模型统一固定为 **Luna Max**：

| 工作 | 模型 | 擅长什么 |
|---|---|---|
| 阅读 | Luna Max | 窄范围读代码、追调用链 |
| 实现 | Luna Max | 做法已经明确的有界修改 |
| 调研 | Luna Max | 大范围只读调查、跨文件找证据 |
| 解题 | Luna Max | 在明确 decision rights 内处理需要判断的实现 |
| 复核 | Luna Max | 独立检查方案和最终结果 |

这是当前 Host 的 containment 安全约束。正式 Real Host N1 测试确认，当前 Codex MultiAgent V2 中，V2-capable child 可以继续创建 grandchild，而且 `agents.max_depth=1` 没有阻止这条路径。当前 Host 的 Luna 模型元数据为 V1，因此 managed child 不会获得这条 V2 collaboration surface。

主会话本身仍可使用 Host 提供的其他模型。以后如果 Host 提供可验证的 V2 descendant containment，或者模型能力元数据发生变化，会重新做 Host qualification 后再调整 managed 阵容。角色里的“不要继续创建 subagent”仍保留为防御性行为约束，不拿它替代 Host 证据。

## 安装

通过 Codex 插件市场安装：

```bash
codex plugin marketplace add R-jed/subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

安装完成后启动一个新的 Codex 会话，在 Skill 菜单里选择 **Orchestrate**。

第一次真正需要子代理时，插件会检查自己的五个固定 Agent profile。如果缺失且路径安全，插件只创建自己拥有的配置。当前 V4 无法从已经运行中的 task 获得权威证据，证明刚创建的 custom Agent profile 已进入这个 task 的 Agent registry，因此这次任务会保守返回 `RESTART_REQUIRED`。重新开一个 Codex 任务后提交原请求即可。

如果希望第一条正式开发任务不被初始化打断，可以先用 **Doctor** 明确要求修复或准备 managed Agent profiles，再启动新的正式工作会话。辅助功能需要 Python 3.11 或更高版本。

完整说明见 [安装文档](docs/plugin-installation.md)。

更新：

```bash
codex plugin marketplace upgrade subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

卸载前先通过 **Doctor** 清理能够确认属于本插件的 Agent profile，再移除插件和插件市场。

## 它能让 Codex 更快吗

有可能，尤其是调查可以并行、主上下文很容易被塞满的时候。

更多 Agent 不会自动带来更快速度。项目会先看正确性和安全，再看返工、协调负担、上下文效率、耗时与 Token。判断框架见 [产品成功标准](docs/product-success.md)。

技术细节：

[架构](docs/architecture.md) · [安装](docs/plugin-installation.md) · [写入者边界](docs/writer-boundary.md) · [产品成功标准](docs/product-success.md) · [运行时证据](docs/runtime-attestation.md) · [实验方法](docs/experiment-protocol.md) · [更新记录](CHANGELOG.md) · [AI 参考说明](README_AI.md)

## 许可证

[MIT](LICENSE)
