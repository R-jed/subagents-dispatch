# Changelog

本文件记录 subagents-dispatch 的重要变更。格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

## [2.1.2] - 2026-08-09

### Fixed

- **Codex App 用户入口**：撤销把 `$dispatch` / `$doctor` 当成唯一公开入口的错误文档化；App 使用 `/` 打开 Skill 菜单，具体渲染的 slash entry 由真实 App UI 验证，不再从底层 Skill mention 或其他产品语法推导
- **Skill 身份冲突**：主 Skill 改为稳定 ID `subagents-dispatch`、显示名 `Subagents Dispatch`；诊断 Skill 改为稳定 ID `subagents-doctor`、显示名 `Subagents Doctor`，避免通用 `dispatch` / `doctor` 名称与其他项目 Skill 混淆
- **发行证据责任**：发布清单明确区分 Repository/API/CI、raw Host/rollout、人工 App UI 与模型自报四类证据；App `/` 菜单中的实际条目、前缀、冲突和选择绑定必须由人工直接观察，不能由被测 Codex 自证
- **合同恢复**：撤回上一版 2.1.2 候选中过度压缩的 runtime、Guardrails、eval 和测试合同，恢复到已经过 Host 回归的成熟 2.1.1 基线，再叠加最小的 2.1.2 身份修复

### Changed

- **不可变发行身份**：Marketplace Plugin source 绑定未来 `v2.1.2`；已存在的 `v2.1.1` tag 保持不可变且不创建对应 GitHub Release

## [2.1.1] - 2026-08-08

### Fixed

- **首次委托状态机**：当显式 `/dispatch` 确认需要子 Agent 且项目 profiles 干净缺失时，自动进行仅限插件自有文件的 provisioning；安装与 `--check` 成功后，当前任务直接进入 `RESTART_REQUIRED`，不再尝试一次 stale-session `spawn_agent`，要求从 fresh Codex task/session 重跑原请求
- **当前会话角色不可见**：如果磁盘上的 managed profiles 已经精确存在，但当前任务启动时没有加载对应 Agent role，同样返回 `RESTART_REQUIRED`，不会用其他 role 替代或继续猜测
- **安全失败边界**：同名冲突、symlink、未证明所有权、被修改或其他不安全状态继续 fail closed，并转由用户与 `/doctor` 处理，不自动覆盖
- **安装器诊断**：首次 `--check` 对未安装状态给出明确的 `Not installed` 引导，并将安装成功后的提示与 `RESTART_REQUIRED` 行为保持一致
- **Custom Agent fresh-context spawn**：所有新 project child 在调用 `spawn_agent` 前必须显式使用 `fork_turns: none`；禁止 full-history (`all`) 或省略 `fork_turns`，避免 exact custom role 与 full-history 组合被 Host 拒绝
- **重试计数准确性**：Host 在返回任何 child identity 前拒绝的 spawn tool call 定义为 pre-attempt rejection，不消耗 Agent attempt budget，也不会让 Execution Receipt 错误显示一次 Agent retry

### Changed

- **首次使用体验**：routine first-use provisioning 不再要求用户理解或额外确认 TOML/profile 级安装细节；自动授权严格限制在 5 个 managed Agent profiles、ownership manifest 和 installer lock
- **文档与评估同步**：README、AI reference、Privacy、安装/架构/原生运行文档、Behavioral Eval H、interaction fixtures 与回归测试统一到新的 first-use contract
- `RESTART_REQUIRED` 明确定义为 pre-dispatch readiness outcome，不属于 Recovery/Agent lifecycle 状态；由于没有实际 spawn child，也不产生 Execution Receipt
- **发布前工程收口**：README 示例明确只读工作可并行、同一代码目录只保留一个写入者；新增 first-use、Status、Steer 的真实 Host workload，Ruff lint、正式发布清单，以及版本号/Changelog 一致性回归检查
- **Host 回归门**：新增 custom-role fresh-context spawn workload，固定检查首次 spawn 直接使用 `fork_turns: none`，并验证 pre-child rejection 不会被记作 Agent retry
- **不可变发行身份**：Marketplace 的 Plugin Git source 由 rolling `main` 改为与 `plugin.json` 版本一致的 `v2.1.1` tag，并新增回归测试确保后续版本的 Marketplace source 始终绑定 `v<version>`；GitHub Release 只在 tag 绑定后的安装 smoke 通过后创建

## [2.1.0] - 2026-08-07

### Added

- **运行中控制面**：`/dispatch preview`、`/dispatch status`、`/dispatch steer`、`/dispatch takeover` 四个命令，支持执行前预览、执行中监控、实时指导和职责接管
- **Handoff Capsule**：证据绑定的交接包，包含 `ACCEPTED FACTS`、`DO NOT REDO`、`STALE IF` 等语义字段，减少子 Agent 间的重复发现
- **执行摘要**：任务结束时附加一行事实性摘要，报告角色、重试、复核状态，不暴露推理过程
- **四条核心约束**明确文档化：一个写入者、一层委托深度、UNKNOWN 不猜测、摘要只报事实

### Changed

- README 重写为直接人类语音风格，去除 AI 写作痕迹
- 补充所有 README 的卸载说明

## [2.0.0] - 2026-07-22

### Changed

- **产品重命名**：从 Codex Delegate 更名为 subagents-dispatch
- **插件迁移到根目录**：遵循 Codex Marketplace 标准布局
- **旧版迁移工具**：支持从 codex-delegate 自动迁移，含回滚机制

### Added

- **Doctor 技能**：安装诊断、配置检查、插件升级
- **Legacy Migration**：两阶段迁移，支持事务回滚

## [1.2.0] - 2026-07-15

### Added

- **发布门控**：强化的发布候选验证流程
- **Final Review Gate**：基于后果触发的独立复核机制

### Fixed

- 跨代安装器状态序列化
- 旧版迁移事务硬编码

## [1.1.0] - 2026-06-28

### Added

- **编排恢复**：TeamPlan 验证器和有界恢复合约
- **Recovery Ledger**：原生恢复状态验证
- **TeamPlan**：多职责并行时的依赖 DAG 协调

### Changed

- 路由策略与当前 MultiAgentV2 合约对齐
- 原生能力和上下文 fork 规则强化

## [1.0.0] - 2026-06-15

### Added

- **正式发布**：完整的五角色 Agent 团队
- **Final Review**：风险触发的独立复核
- **运行时保障**：从运行时保障到运行时真相的演进
- **一键安装器**：Skill 和锁定 Agent profiles 的确定性安装

### Changed

- 锁定路由 profiles 成为默认安装路径

## [0.10.0] - 2026-06-01

### Added

- **自适应委派合约**：渐进式扇出，无固定波次
- **确定性辅助工具**：install-agents.py、validate_team_plan.py 等

## [0.9.1] - 2026-05-20

### Added

- **路由验证**：路由行为评估 schema 和用例
- **策略回归套件**：策略文档和运行时合约回归覆盖

## [0.8.0] - 2026-05-10

### Added

- **Routing V4**：精确路由绑定和动态团队选择
- **Sol 判断耦合求解器**：实现过程中需要判断的工作
- **主会话路由证据**：路由事实的三层分离（requested/accepted/observed）

### Changed

- 路由绑定从观察到精确
- 团队选择从静态到动态

## [0.5.0] - 2026-04-15

### Added

- **渐进任务包**：自适应扇出调度
- **安全策略**：权限、变更权限、写入安全
- **同意策略**：用户授权和信任边界
- **路由策略**：角色选择和职责分配

## [0.3.0] - 2026-03-20

### Added

- **核心 Skill**：Codex Agent Team 主技能
- **Agent Profiles**：Luna Worker、Luna Explorer、Terra Reviewer
- **Skill UI 元数据**：插件清单和市场注册

## [0.1.0] - 2026-03-01

### Added

- 项目初始化
- 架构文档
- 贡献指南和安全策略
- CI 工作流和测试配置

---

## 版本说明

- **主版本 (X.0.0)**：重大架构变更或产品重命名
- **次版本 (0.X.0)**：新功能或重要改进
- **修订版本 (0.0.X)**：Bug 修复和小改动

## 链接

- [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)
- [语义化版本](https://semver.org/lang/zh-CN/)
