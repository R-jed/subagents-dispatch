<p align="center">
  <img src="assets/subagents-dispatch-banner.png" alt="subagents-dispatch" width="900">
</p>

<h1 align="center">subagents-dispatch</h1>

<p align="center"><em>给 Codex 一支靠谱的小队。大任务分头做，小任务别折腾。</em></p>

<p align="center">
  <a href="README_EN.md">English</a> · <a href="docs/plugin-installation.md">安装</a> · <a href="docs/architecture.md">架构</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-4.0.0-green.svg" alt="Version">
  <img src="https://img.shields.io/badge/Codex-Native%20Subagents-111827.svg" alt="Codex Native Subagents">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
</p>

> **如果你是 AI Agent，请跳转到 [README_AI.md](README_AI.md)。**

你给 Codex 一个稍大的任务：改 API、补测试、追调用链，再顺手看看前端会不会受影响。

一个 Main 从头包到尾当然能做。只是任务一长，读代码、查资料、写实现、跑测试、做复核全塞进同一个上下文，脑子很快就会挤成早高峰。

**subagents-dispatch 会在值得分工的时候，临时给 Codex 组一支小队。**

有人读代码，有人查影响，有人动手实现，有人负责复核。Main 仍然掌握目标、判断和最终结果。任务很小的时候，它可以一个子代理都不叫。为了显得忙而拉一群 Agent 开会，不算生产力。

## 30 秒看懂

比如你说：

```text
给 /api/users 加分页，补测试，再检查前端调用有没有受影响。
```

一次合理的分工可能是：

```text
Main
├─ 先读 API、测试和调用链
├─ 同时检查前端和跨文件影响
├─ 边界清楚后安排实现
└─ 变更比较大时再做一次独立复核
```

最后由 Main 把结果收回来，检查证据，整合代码，再决定任务到底算不算完成。

如果 Main 看两眼就发现这事三分钟能做完，那它自己做。Dispatch 没有“必须多开几个子代理”的业绩指标。

## 它适合什么时候用

当任务里有几块可以分头调查的工作，或者实现前需要先把影响范围摸清，subagents-dispatch 通常会比较有价值。

例如：

- 要同时追多条调用链
- 要先调查再实现
- 改动跨前后端、配置、测试或文档
- 有一块工作很适合独立交给另一个子代理
- 变更影响较大，希望有人单独复核

任务很小、步骤强串行、上下文已经齐全时，Main 自己做通常更省事。

## 你只需要记住两个入口

V4 把以前分散的入口收成两个：

| 入口 | 什么时候用 |
|---|---|
| **Orchestrate** | 让它规划、分工、执行、继续、纠正、接管、复核或整合 |
| **Doctor** | 安装后不确定哪里有问题，或者想检查版本、配置和运行环境 |

日常干活选 **Orchestrate**。感觉环境有点不对劲，叫 **Doctor**。

Orchestrate 也支持只看计划。你可以先让它说准备怎么分工，再决定要不要真的开工。

## 它会克制自己

多 Agent 很容易从“并行工作”滑向“多人群聊”。V4 给自己定了几条很朴素的规矩：

- 小任务允许 0 个子代理
- 一开始最多叫 2 个，正常工作时最多 3 个
- 同一个工作区同时只让一个受管理的子代理写代码
- 子代理只拿完成自己那份工作需要的上下文
- 调查结果要有证据，Main 会复核后再接受
- 状态说不清时先停住，不拿猜测当授权
- 最终交付仍由 Main 负责

这些限制会让它少一点“看起来很聪明”的热闹，多一点真正可控的并行。

## 当前固定阵容

V4.0.0 先把阵容固定下来，不做动态模型和思考强度切换：

| 工作 | 模型 | 擅长什么 |
|---|---|---|
| 阅读 | Luna Max | 窄范围读代码、追调用链 |
| 实现 | Luna Max | 做法已经明确的有界修改 |
| 调研 | Terra High | 大范围只读调查、跨文件找证据 |
| 解题 | Sol High | 需要较多技术判断的实现 |
| 复核 | Sol High | 独立检查方案和最终结果 |

固定配置的好处很简单：行为更容易理解，也更容易复现。以后如果真实数据证明某个组合值得调整，再调整。

## 安装

正式发布后，通过 Codex Plugin Marketplace 安装：

```bash
codex plugin marketplace add R-jed/subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

安装完成后启动一个新的 Codex 会话，在 Skill 菜单里选择 **Orchestrate**。

第一次真正需要子代理时，插件会检查自己的五个固定 Agent 配置。如果这些配置刚刚被创建，当前任务会提示重新启动。开一个新的 Codex 任务，再选一次 Orchestrate 即可。相关辅助功能需要 Python 3.11 或更高版本。

完整安装说明见 [Plugin Installation](docs/plugin-installation.md)。

更新：

```bash
codex plugin marketplace upgrade subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

卸载时，先通过 **Doctor** 清理能够确认属于本插件的 Agent 配置，然后再移除插件和 Marketplace：

```bash
codex plugin remove subagents-dispatch@subagents-dispatch
codex plugin marketplace remove subagents-dispatch
```

如果 Doctor 报告配置归属不清楚，先处理冲突。不要直接手工删文件把警报按掉。

## 它能让 Codex 更快吗

有可能，尤其是调查可以并行、主上下文很容易被塞满的时候。

但“开更多 Agent”本身不会自动变快。小任务可能更慢，协调也有成本。项目已经准备了实验协议去比较正确性、返工、耗时和 Token，等真实重复实验够多再谈数字。

**本 README 不声称 subagents-dispatch 已经被证明更快、更省总 Token。**

我们更关心另一件事：复杂任务能不能分得清、收得回来、最后有人真正负责。

## V4 现在到哪了

V4.0.0 的仓库实现和离线验证已经推进到发布候选阶段。正式发布前还需要完成真实 Codex 环境里的生命周期验证。

这项验证没过之前，项目不会把发布状态提前写成“已验证”。想看具体工程进度，可以去 [Release Checklist](docs/release-checklist.md) 和 [V4 docs](docs/v4/)。README 到这里就不继续开设计评审会了。

想继续往下看技术细节：

[架构](docs/architecture.md) · [安装](docs/plugin-installation.md) · [运行时证据](docs/runtime-attestation.md) · [实验方法](docs/experiment-protocol.md) · [更新记录](CHANGELOG.md) · [AI Reference](README_AI.md)

## License

[MIT](LICENSE)
