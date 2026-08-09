<p align="center">
  <img src="assets/subagents-dispatch-banner.png" alt="subagents-dispatch" width="900">
</p>

<h1 align="center">subagents-dispatch</h1>

<p align="center"><em> Codex子代理调度框架。</em></p>

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

subagents-dispatch 是一个 Codex 插件。它负责把一个大任务拆给几个专门的子代理角色去干，主会话定目标、盯进度，最后验收结果。

## 快速开始

```text
选择 Dispatch，然后输入：给 /api/users 加分页参数，补上测试
```

一句话任务，插件自己拆。查现有接口和查测试两件只读的活并行跑，查清了再派一个写代码的。简单任务不硬拆，值得分工才分配子代理。

## 怎么用

想先看看准备怎么分工，不真的启动子代理：
```text
选择 Preview，然后输入：给 /api/users 加分页参数，补上测试
```

任务在跑，想看看做到哪一步：
```text
选择 Status
```

想给正在工作的子代理补一句新要求：
```text
选择 Steer，然后输入：U2: 先看现有的分页中间件
```

想停止某个职责，改由主会话接手：
```text
选择 Takeover，然后输入：U2
```

## 执行摘要：最后告诉你刚才做了什么

```text
Dispatch: Luna Max 读取 → Luna Max 执行 · 完成 · 未重试 · 无需最终复核
```

只写确认过的事实，不猜 Token 用量和费用。

## 交接包 Handoff

如果每一个子代理都从新鲜上下文开始任务，什么信息都不传递，后一个会把前一个任务再重新执行一遍。交接包就是一份小交接文件，主会话把核实过的信息放进去交给下一个子代理。

- **已经确认的事实可以直接接着用**。只有主会话检查并接受过的内容才会放进交接包
- **`DO NOT REDO` 表示这部分不用重做**
- **主会话负责把关**。子代理说完成了不算，检查过证据才当成已知事实
- **`STALE IF` 表示出现这些变化，旧结论作废**

## 子代理规则

- **同一份代码，同一时间只让一个写入者修改**。同一次 subagents-dispatch 调度里，同一个 Git 工作目录同一时间最多只有一个写入者实际改文件，这个写入者只能是主会话或执行活动。前一个写入者还没有确认停止，主会话不会抢着改同一份代码。其他独立的 Codex 会话、编辑器、自动化脚本和外部程序不受这个规则控制
- **子代理不能继续叫更多子代理**。分工只由主会话安排
- **`UNKNOWN` 就停下来确认，不靠猜**。不会随便换一个子代理顶上，不会自动重试，也不会偷偷改变任务路线
- **只报告确认过的事实**。执行摘要不会根据模型名称、运行时间或输出长度去猜 Token 用量和费用

## 角色

| 模型通道 | 对外活动 | 干什么 |
|------|-----------|--------|
| Luna Max | 读取 | 读代码、追调用链、收集事实 |
| Luna Max | 执行 | 需求和做法清楚时负责实现和测试 |
| Sol High | 执行 | 实现过程中需要技术判断时负责执行 |
| Terra XHigh | 调研 | 大范围只读调查和证据整理 |
| Sol High | 决策 / 验收 | 独立技术判断，或需要时做最终复核 |

主会话判断，值得分工才叫人。

## 安装

```bash
codex plugin marketplace add R-jed/subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

首次需要委派时选择 Dispatch；插件会安全创建 5 个子代理配置文件，然后要求开启新会话再选择 Dispatch 执行任务。

## 更新

```bash
codex plugin marketplace upgrade subagents-dispatch
codex plugin add subagents-dispatch@subagents-dispatch
```

也可以选择 **Doctor** 并要求它升级。

## 卸载

```bash
codex plugin remove subagents-dispatch@subagents-dispatch
codex plugin marketplace remove subagents-dispatch
```

跑过子代理任务的还要删这六个文件：

```bash
rm ~/.codex/agents/subagents-dispatch-reader.toml
rm ~/.codex/agents/subagents-dispatch-worker.toml
rm ~/.codex/agents/subagents-dispatch-solver.toml
rm ~/.codex/agents/subagents-dispatch-investigator.toml
rm ~/.codex/agents/subagents-dispatch-advisor.toml
rm ~/.codex/.subagents-dispatch-agents.json
```

## 项目结构

```text
.
├── .agents/plugins/                  # Codex 插件市场注册
├── .codex-plugin/                    # 插件清单
├── agent-profiles/                   # 五个子代理配置文件
├── contracts/                        # 共享编排契约和角色规则
├── scripts/                          # 安装、检查和运行记录工具
├── skills/
│   ├── dispatch/                     # 开始或继续编排
│   ├── preview/                      # 只预览，不执行
│   ├── status/                       # 单次状态检查
│   ├── steer/                        # 引导现有委派
│   ├── takeover/                     # 安全收回委派
│   └── doctor/                       # 安装和运行诊断
├── docs/                             # 架构和运行边界文档
├── evals/                            # 评估用例
└── tests/                            # 回归测试
```

## 文档

- [安装说明](docs/plugin-installation.md)
- [架构说明](docs/architecture.md)
- [Codex 原生 Subagent 运行边界](docs/native-subagent-runtime.md)
- [行为评估](docs/behavioral-evals.md)
- [OpenAI 参考](docs/openai-references.md)
- [AI Agent 项目参考](README_AI.md)
- [变更日志](CHANGELOG.md)
- [隐私说明](PRIVACY.md)
- [服务条款](TERMS.md)

## 许可证

[MIT](LICENSE)
