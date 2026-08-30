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

有人读代码，有人查影响，有人动手实现，有人负责复核。主会话仍然掌握目标、判断和最终结果。任务很小的时候，它可以一个子代理都不叫。为了显得忙而拉一群 Agent 开会，不算生产力。

## Codex 已经有 Subagents，为什么还需要它

Codex 提供原生 Subagents。这个插件提供的是一套面向工程任务的协调策略。

它会判断什么时候值得分工，把工作拆成有完成条件和依赖关系的职责，限制无意义的并发，在同一个可变工作区避免多个写入者互相踩文件，并要求主会话验收结果后再解锁后续工作。Host 状态说不清时会保留 `UNKNOWN`，不会把猜测当成授权。

所以它关注的重点是复杂任务能不能分得清、并行得稳、收得回来，并且最后还有一个明确负责的人。

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

如果主会话看两眼就发现这事三分钟能做完，那它自己做。这个项目没有“必须多开几个子代理”的业绩指标。

## 它适合什么时候用

当任务里有几块可以分头调查的工作，或者实现前需要先把影响范围摸清，subagents-dispatch 通常会比较有价值。

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
| **Orchestrate** | 让它判断是否需要分工，并负责规划、执行、继续、纠正、接管、复核和整合 |
| **Doctor** | 检查插件、Agent 配置、Host 集成和运行状态，或者执行你明确要求的安全维护 |

日常干活选 **Orchestrate**。感觉环境有点不对劲，叫 **Doctor**。

Orchestrate 也支持只看计划。你可以直接说：

```text
先只告诉我你准备怎么分工。
```

任务运行后，也可以自然地控制它：

```text
现在进度怎么样？
U2 先停一下。
这部分我自己接手。
继续刚才被打断的工作。
```

这些控制都留在同一个 Orchestrate 入口里，不需要记一排额外 Skill。

## 它会克制自己

多 Agent 很容易从“并行工作”滑向“多人群聊”。这个项目给自己定了几条很朴素的规矩：

- 小任务允许 0 个子代理
- 只开真正有用的最少子代理：一个可分责任通常一个子代理；多个独立且可安全并行的责任才会同时开多个
- 最多 4 个受管理子代理，4 是安全上限，不是目标数量；空闲槽位本身不是开子代理的理由
- 同一个可变工作区同时只有一个受管理的写入者
- 子代理只拿完成自己那份工作需要的上下文
- 子代理接走一份责任后，主会话负责复核和整合，不会为了“再确认一次”把同一份工作重做一遍
- 调查结果要有证据，主会话会复核后再接受
- 状态说不清时先停住，不拿猜测当授权
- 最终交付仍由主会话负责

这里的单写入者是工作区边界。未来如果 Host 能可靠地把不同写入者隔离到独立 worktree 或 workspace，并且这些工作在语义上也互不冲突，就可以形成多个独立写入域。当前版本只管理一个 canonical workspace，因此保持一个写入者更稳妥。详细说明见 [写入者边界](docs/writer-boundary.md)。

## 当前固定阵容

| 工作 | 模型 | 擅长什么 |
|---|---|---|
| 阅读 | Luna Max | 窄范围读代码、追调用链 |
| 实现 | Luna Max | 做法已经明确的有界修改 |
| 调研 | Terra High | 大范围只读调查、跨文件找证据 |
| 解题 | Sol High | 需要较多技术判断的实现 |
| 复核 | Sol High | 独立检查方案和最终结果 |

目前先把阵容固定下来，不做动态模型和思考强度切换。这样行为更容易理解，也更容易复现。以后如果真实数据证明某个组合值得调整，再调整。

## 安装

通过 Codex 插件市场安装：

```bash
codex plugin marketplace add R-jed/subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

安装完成后启动一个新的 Codex 会话，在 Skill 菜单里选择 **Orchestrate**。

第一次真正需要子代理时，插件会检查自己的五个固定 Agent profile。如果缺失且路径安全，插件只会创建自己拥有的配置。当前 V4 无法从已经运行中的 task 获得权威证据，证明刚创建的 custom Agent profile 已经进入这个 task 的 Agent registry，因此这次任务会保守返回 `RESTART_REQUIRED`，不会尝试用别的 Agent 顶替。重新开一个 Codex 任务后提交原请求即可，这个步骤只发生在 profile 首次创建或需要重新激活时。

如果你希望第一条正式开发任务不被这个初始化步骤打断，可以在安装后的首次会话里先选择 **Doctor**，明确要求它修复或准备 managed Agent profiles，然后启动一个新的正式工作会话。相关辅助功能需要 Python 3.11 或更高版本。

完整说明见 [安装文档](docs/plugin-installation.md)。

更新：

```bash
codex plugin marketplace upgrade subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

卸载时，先通过 **Doctor** 清理能够确认属于本插件的 Agent profile，然后再移除插件和插件市场：

```bash
codex plugin remove subagents-dispatch@subagents-dispatch
codex plugin marketplace remove subagents-dispatch
```

如果 Doctor 报告配置归属不清楚，先处理冲突。不要直接手工删文件把警报按掉。

## 它能让 Codex 更快吗

有可能，尤其是调查可以并行、主上下文很容易被塞满的时候。

但“开更多 Agent”本身不会自动变快。小任务可能更慢，协调也有成本。项目已经准备了实验协议去比较正确性、返工、人工干预、耗时和 Token，等真实重复实验够多再谈数字。

这里不会提前宣传“更快”或者“更省 Token”。产品实验会先看正确性和安全，再看返工、协调负担、上下文效率、耗时与 Token。判断框架见 [产品成功标准](docs/product-success.md)。

我们更关心另一件事：复杂任务能不能分得清、收得回来、最后有人真正负责。

想继续往下看技术细节：

[架构](docs/architecture.md) · [安装](docs/plugin-installation.md) · [写入者边界](docs/writer-boundary.md) · [产品成功标准](docs/product-success.md) · [运行时证据](docs/runtime-attestation.md) · [实验方法](docs/experiment-protocol.md) · [更新记录](CHANGELOG.md) · [AI 参考说明](README_AI.md)

## 许可证

[MIT](LICENSE)
