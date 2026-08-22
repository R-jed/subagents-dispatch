# V4 实时开发交接记录

初始记录时间：2026-08-23 05:58 +08:00。

最新记录时间：2026-08-23 06:51 +08:00。

状态：持续维护。

此文件是 `subagents-dispatch` V4 当前开发上下文的仓库内交接入口。任何新会话、新维护者或新的 Codex session 接手 V4 前，应先读本文件，再核 GitHub 当前分支、PR、CI、Real Host Test Ledger 和真实 Host evidence。本文负责保存项目背景、关键决策、当前 release 状态和操作纪律，不替代机器合同或真实 Host 证据。

## 1. 项目是什么，为什么存在

仓库：`R-jed/subagents-dispatch`。

产品目标：在 OpenAI Codex 原生 Subagents 之上提供一层面向真实软件工程任务的受控编排策略，让 Main 能在值得分工时把读取、调查、实现、求解和复核职责交给固定子 Agent，同时继续由 Main 负责用户意图、判断、整合、验收和最终结果。

项目解决的核心问题不是“怎样开更多 Agent”。真正要解决的是：

- 什么时候分工有价值，什么时候 0 个 child 更合理；
- 怎样把工作拆成可验收、可追踪、有依赖关系的责任单元；
- 怎样防止多个可写 child 在同一个可变工作区互相踩文件；
- 怎样把 Codex Host 的真实生命周期、身份、容量和权限事实与插件自己的产品状态分开；
- 怎样处理 Host 状态不清楚、child 是否真正 materialize 不清楚、writer 是否已经停止不清楚等危险边界；
- 怎样让同一个 child 可以被 Steer、Correction、Continue，而不会随意创建 replacement；
- 怎样确保 child 完成只产生候选结果，最终 acceptance 仍由 Main 基于真实 artifact 和证据决定；
- 怎样在 release 时区分 repository CI、真实 Codex Host 行为、installed product、Final Review 和人工 App 观察。

当前版本是 `4.0.0` release candidate。V4 的设计目标是把复杂度压回必要范围，尽量复用 Codex Native Subagents 的 Host truth，避免插件自己复制一套 Agent runtime。

## 2. V4 为什么演进成 Hookless Native Core

项目历史上出现过更重的 lifecycle interception、Hook/Guard、PendingControl、capacity token、固定 fanout、固定 retry/followup budget 等机制。这些历史设计保留在 `docs/history/` 仅供 provenance 使用，不能继续定义当前产品行为。

V4 Native Core 的核心判断是：Codex Host 已经拥有 child materialization、native lifecycle、ThreadId、真实 admission、permission 和 collaboration surface。插件如果再维护一套平行 lifecycle truth，会形成双重事实源，增加竞态、漂移和错误授权风险。

所以当前 V4 主动移除了旧 Hook correctness control plane，并采用以下原则：

- Host 负责原生事实；
- Main 负责产品判断和用户授权；
- WorkGraph / WorkUnit 负责责任、依赖、readiness 和 acceptance truth；
- ExecutionBinding 只表示一次具体 managed execution attempt；
- WriterLease 只负责 canonical mutable workspace 的 managed writer 协调；
- UNKNOWN fail closed；
- repository helper 只做约束投影，不伪造 Host truth；
- Hook 最多作为未来 optional observability、diagnostics 或 defense-in-depth，不能重新成为 release correctness authority。

`CHANGELOG.md` 中 V4.0.0 RC 的“Native Core runtime”和“Complexity reduction”是这一演进的产品级摘要。当前规范性机器结构以 `docs/v4/architecture.json` 为准。

## 3. 当前正式候选和 Git 状态

在本次“补全 handoff 背景”修改开始前，正式候选为：

- branch：`v4/rc5-native-core`
- commit：`6f1f3179f087e72fb1329c13bc6a9024faf117de`
- tree：`d3cdefb0944adc8bdd00f500e5e4ea3b4e67bd7b`
- 主发布 PR：`#81 RC5 Native Core: remove Hook control plane`
- PR #81：OPEN、Draft、未合并
- PR #81 synthetic merge commit：`7ff64c86335ecb331f1ce29b8193d0fc7e47cca7`
- synthetic merge tree：`d3cdefb0944adc8bdd00f500e5e4ea3b4e67bd7b`
- candidate tree 与 PR #81 synthetic merge tree 完全一致
- exact-head repository CI：workflow `32602156632`
- Ubuntu Python 3.11：PASS
- Ubuntu Python 3.12：PASS
- macOS Python 3.11：PASS
- Windows Python 3.11：PASS
- aggregate `policy-tests`：PASS
- generated package-integrity：PASS
- Ruff：PASS
- pinned official OpenAI Plugin validator：适用 job PASS
- managed Agent profile lifecycle：PASS

本次文档补全工作分支：`docs/v4-handoff-project-background`，从 `6f1f3179...` 精确分出。

本分支只允许修改 handoff 文档及与 handoff 可发现性直接相关的文档。它不能顺手修改 runtime、contracts、profiles、package payload 或 Host machine gate。如果该分支最终合并，正式 candidate SHA 会变化，因此必须重新读取 `v4/rc5-native-core` HEAD/tree 并做 post-merge exact-head repository validation，然后才允许进入正式 N0。

仓库还存在若干历史或已完成工作分支，例如：

- `v4/phase7-public-cutover`
- `v4/rc5-phase0-host-gate`
- `v4/rc5-phase0-validation`
- `v4/rc5-phase3-recovery-gate`
- `v4/rc5-hookless-feasibility`
- `v4/rc5-review-remediation`
- `fix/v4-host-contract-hardening`
- `fix/v4-n4-release-doc-closure`
- `docs/v4-live-development-handoff`

这些分支可用于追溯演进，但都不能覆盖当前 `v4/rc5-native-core` 的 authority。接手时不要根据分支名字猜当前实现，必须读取当前正式 candidate HEAD 和具体文件。

## 4. 当前公开产品面

V4 对用户只公开两个 Skills：

- `Orchestrate`
- `Doctor`

`Orchestrate` 负责：plan-only、是否分工、责任拆分、delegated execution、status、Steer、Correction、Continue、Interrupt、Cancel、Takeover、integration、consequence-based review 和最终交付流程。

`Doctor` 负责：Plugin package、managed Agent profiles、Host capability surface、orchestration state、legacy compatibility、ownership-safe maintenance 和明确请求的修复动作。

当前产品明确允许小任务使用 0 个 child。managed-child ceiling 为 4，4 是安全上限，不是目标 fanout。

V4.0.0 明确排除：dynamic effort routing、nested managed delegation、autonomous peer authority transfer、daemon scheduler、persistent orchestration database、automatic worktree management、parallel isolated managed writers。

## 5. 固定 Agent profile 合同

机器 authority：`contracts/policy.json`。

| Profile | Model | Reasoning effort | 普通 mutation posture | 主要用途 |
| --- | --- | --- | --- | --- |
| Reader | `gpt-5.6-luna` | `max` | none requested | 窄范围读代码、追调用链 |
| Worker | `gpt-5.6-luna` | `max` | bounded-source-write | 已明确做法的有界实现 |
| Investigator | `gpt-5.6-terra` | `high` | none requested | 大范围只读调查和证据收集 |
| Solver | `gpt-5.6-sol` | `high` | bounded-source-write | 高判断强度实现/求解 |
| Advisor | `gpt-5.6-sol` | `high` | none requested | 独立复核和 Final Review |

Reasoning effort 当前固定，不做动态切换。

Profile TOML 中的 `sandbox_mode`、`agents.enabled=false`、`features.multi_agent_v2=false` 和“不继续创建 subagents”的 developer instruction 都只代表产品请求和行为意图，不能单独证明 Host enforcement。

项目的 `max_depth=1` 也是 product policy，不能作为 MultiAgent V2 descendant containment proof。

## 6. 权威层级，接手时先信谁

如果文件之间有冲突，按以下顺序处理：

1. 当前 Git commit 中实际 production implementation 与当前 machine-readable contracts。
2. `contracts/` 下的当前产品合同。
3. `docs/v4/architecture.json` 的 runtime ownership 和机器结构。
4. `docs/v4/host-smoke.json` 的 candidate-bound N0-N8 Host release contract。
5. `docs/release-checklist.md` 的人工 release 操作顺序。
6. `docs/v4/phase-status.json` 的 repository/release phase bookkeeping。
7. `docs/v4/technical-debt.json` 的已知 debt。
8. 本 handoff 的实时背景、决策、历史和下一步。
9. `README_AI.md` 和普通产品文档作为 onboarding/说明。
10. `docs/history/` 仅为历史 provenance，不能定义当前行为。

若 handoff 内记录的旧 SHA、Host build 或 upstream SHA 与 GitHub 当前状态冲突，以当前 GitHub/Host 重新读取结果为准，并在下一次仓库内容修改时更新 handoff。

## 7. 仓库目录地图

新会话至少要知道以下目录的职责：

### 根目录和 Plugin 元数据

- `.codex-plugin/plugin.json`：Plugin identity/version。
- `.codex-plugin/package-integrity.json`：当前 shipped Plugin payload 的 SHA-256 期望集合。
- `.agents/plugins/marketplace.json`：Marketplace identity/source。
- `README.md` / `README_EN.md`：人类用户产品说明。
- `README_AI.md`：AI/维护者入口，要求先读本 handoff。
- `CHANGELOG.md`：版本级产品变化摘要。

### `skills/`

只应有公开 `skills/orchestrate` 和 `skills/doctor`。任何新公开 Skill 都属于产品面变更，需要重新审查 public-surface contract。

### `agent-profiles/`

五个固定 managed Agent profile。这里的配置只证明 requested role/model/effort/posture，不能替代 Host-observed effective behavior。

### `contracts/`

- `policy.json`：固定 profiles、delegation ceiling、review policy。
- `routing.md`：delegation value、profile selection、dispatch judgment。
- `responsibility-packet.md`：child responsibility serialization。
- `team-plan.md`：RC compatibility boundary，没有 runtime planning authority。
- `guardrails.md`：authority、depth、mutation、writer、consent、external-action boundaries。
- `interaction.md`：用户可见 Orchestrate controls。
- `recovery.md`：WorkUnit / ExecutionBinding recovery semantics。
- `state.md`：V4 state contract。
- `handoff.md`：可选 Main-accepted evidence bridge，和本 development handoff 不是同一个概念。
- `evidence-artifact.md`：可检查 evidence provenance。
- `receipt.md`：用户可见 factual execution summary。
- `final-review.md`：exact-candidate independent review contract。

### `scripts/` 核心运行时

- `orchestrate_v4.py`：Orchestrate runtime control preparation。
- `managed_execution_v4.py`：managed spawn contract 和责任投影。
- `execution_lifecycle_v4.py`：ExecutionBinding lifecycle reconciliation。
- `work_graph_v4.py`：WorkGraph / WorkUnit dependency、readiness、acceptance。
- `scheduler_v4.py`：约束投影，不做自动 ranking 或 Host truth ledger。
- `writer_lease_v4.py`：single canonical workspace WriterLease。
- `host_capabilities.py`：Host capability normalization，不能伪造实际 Host fact。
- `state_storage.py`：schema-neutral private state path/lock/atomic storage primitives。
- `inspect-agent-runtime.py`、`inspect-collaboration-runtime.py`：受限 runtime evidence inspection。
- `doctor.py`：installed product diagnosis。
- `install-agents.py`、`uninstall-agents.py`：managed Agent profile ownership-safe lifecycle。
- `package_integrity.py`：Plugin package identity verification。
- `review-artifact.py`：Final Review artifact binding。
- `legacy_migration.py`、`legacy_state_cleanup.py`：V3 compatibility/cleanup boundary，不能重新成为当前 V4 runtime owner。

### `docs/v4/`

- `architecture.json`：机器 runtime ownership 与 V4 architecture truth。
- `host-smoke.json`：N0-N8 real Host gate machine contract。
- `host-capability-matrix.json`：fail-closed feasibility evidence，不具有 release authority。
- `phase-status.json`：阶段 bookkeeping。
- `technical-debt.json`：已知 debt。
- `writer-lifecycle.json`：writer lifecycle 机器说明。
- `scheduler.json`、`orchestrate.json`：对应子系统机器说明。
- `development-handoff.md`：本实时开发交接。

### `docs/history/`

只保存已淘汰 release、review、experiment 和 remediation 记录。这里可能故意保留 `Dispatch` standalone Skill、Hook/Guard authority、PendingControl、TeamPlan runtime authority、固定 2/3 fanout、固定 retry/followup budget 等旧术语。看到这些内容时只能当历史，不得恢复到当前实现。

### `tests/`

Repository CI 的回归合同。修复当前实现时不要为了保留死架构而让测试继续维护旧行为；但也不能为了让新方案过 CI 而删除仍然有效的安全断言。

## 8. 当前架构责任边界

| 事实或责任 | Owner |
| --- | --- |
| child materialization | Codex Host |
| native child lifecycle | Codex Host |
| underlying Host thread identity | Codex Host |
| actual capacity / admission | Codex Host |
| effective sandbox / permission | Codex Host |
| effective child collaboration surface | Codex Host |
| user intent / decomposition | Main |
| explicit fixed-profile selection | Main |
| dispatch judgment | Main |
| artifact verification | Main |
| WorkUnit acceptance | Main |
| irreversible external side effects | Main |
| final response | Main |
| responsibility / dependency / readiness / acceptance truth | WorkGraph / WorkUnit |
| one concrete native attempt | ExecutionBinding |
| canonical mutable workspace managed writer coordination | WriterLease |

严禁重新引入第二套 lifecycle control plane、私有 Host occupancy ledger、固定 fanout phase、固定 retry budget、固定 followup budget、daemon scheduler 或平行 writer runtime，除非先重新做架构设计和 release contract 评估。

## 9. WorkGraph、ExecutionBinding、acceptance 的关系

WorkUnit 表示稳定责任和 acceptance truth。ExecutionBinding 表示一个具体 native attempt。

Host `COMPLETED` 只把候选工作推进到 `RESULT_READY`，不能自动等于 `ACCEPTED`。Main 必须检查实际 artifact、证据和责任完成情况后显式 accept WorkUnit。依赖只从 `ACCEPTED` 解锁。

Fresh retry 没有固定次数上限。只有 prior attempt 安全 settled，并且存在 changed execution basis，才允许再开 fresh attempt。

Focused same-child correction 要有新的 correction basis。`followup_count` 是诊断量，不是授权预算。

CONTINUE 复用被中断的同一个 ExecutionBinding，不创建 fresh attempt。

RUNNING Steer 也保持同一个 ExecutionBinding，并且当前 V2 adapter contract 使用 `followup_task`。

## 10. WriterLease 和 UNKNOWN

当前 Codex Agent 共享 container、filesystem 和 cwd。不同职责仍可能通过 Git index、generated files、config、dependencies 或跨文件 mutation 互相影响，因此 V4 当前对 canonical mutable workspace 只允许一个 managed writer。

WriterLease states：`RESERVED`、`HELD`、`REVOKING`、`UNKNOWN`、`RELEASED`。

前四种 blocking state 都不能授权冲突 writer。

`interrupt_agent` 返回成功只说明 interrupt request 被处理，不能证明 writer 已经停止，也不能自动 release WriterLease。

只有 current-generation authoritative Host lifecycle evidence 才能 settle execution 并允许 writer transfer/takeover。

materialization、identity、lifecycle 或 writer settlement 存在歧义时进入 UNKNOWN。UNKNOWN 永远不能授权 replacement、writer transfer、Main takeover 或 final acceptance。

## 11. Hook 状态

当前 V4 correctness path 不依赖 Hook。

Hook 可以作为未来 optional observability、diagnostics 或 defense-in-depth，但不能成为：

- spawn authorization；
- child lifecycle settlement；
- WriterLease release；
- retry authorization；
- WorkUnit acceptance；
- Main final acceptance。

任何恢复旧 Hook control plane 的提议都要先重新做架构审查。

## 12. OpenAI Codex MultiAgent V2 技术背景

### 12.1 Upstream 基线怎么读

较完整的 V2 源码审查基线曾锁在：

`343074d4207d572809bd8cea15f4be1d09d98e0b`

在 2026-08-23 06:51 +08:00 重新读取 OpenAI 官方 `openai/codex` `main` 时，最新 HEAD 已变为：

`8e649e3afa5cdddfb09a1b85a090b94775045d9b`

该 commit 的 parent 正是 `343074d...`。本轮针对 V2 messaging files 的复核确认 `send_message` / `followup_task` 关键语义没有变化。其他较大范围 V2 结论仍以此前源码审查和当前 Host 实测为依据；未来若需要依赖某个 upstream 细节做新实现，必须重新读取目标 commit 的官方源码，不允许因为 handoff 写过就永久假设不变。

OpenAI upstream `main` 自己继续前进，不会自动让已经绑定某个实际 Host build 的 real Host evidence 失效。真正决定是否需要重跑的是 target Host environment、candidate、machine contract 和 evidence 完整性。

### 12.2 V2 native control surface

当前已核过的 V2 control family：

- `spawn_agent`
- `send_message`
- `followup_task`
- `wait_agent`
- `list_agents`
- `interrupt_agent`

V1 与 V2 是不同工具族。历史 V1 行为不能未经重新验证直接升级为 V2 release proof。

### 12.3 `fork_turns`

V2 `spawn_agent` 使用 `fork_turns`。正式 managed spawn 要求 `fork_turns="none"`，表示不 fork parent conversation history。

历史 V1 使用 `fork_context`。V1 `fork_context=false` 不能证明 V2 `fork_turns=none`。

正式 N0 必须在真实当前 Host 观察到实际 V2 spawn 和 `fork_turns=none`。

### 12.4 `send_message` 与 `followup_task`

当前 OpenAI 官方 V2 源码中：

- `send_message` 使用 `MessageDeliveryMode::QueueOnly`，`trigger_turn=false`；
- `followup_task` 使用 `MessageDeliveryMode::TriggerTurn`，`trigger_turn=true`；
- 两者共享 messaging submission path；
- `followup_task` 对 RUNNING target 会在 sampling message boundary 或 pending tool call 完成后交付，对 idle target 可触发 turn。

因此当前 V4 RUNNING Steer 继续使用 `followup_task`。但 native tool-call accepted 本身不能证明 guidance 已经被 child 应用。N4 必须看到 same-child post-guidance evidence，并证明没有 replacement identity materialize。

### 12.5 canonical task address 与 Host thread identity

V2 模型可见 control address 主要是 canonical `task_name`。Host 内部另有 ThreadId/agent identity。

ExecutionBinding 支持 `native_task_name` 和 Host evidence 可获得时的 `agent_id`。

普通 runtime 在公共 V2 surface 不暴露 `agent_id` 时允许只使用 canonical task address。正式 N2 release evidence 要从 authoritative Host activity/lifecycle data 把 canonical task address 与底层 Host thread identity 对上。禁止猜测或伪造 `agent_id`。

### 12.6 durable identity、resident runtime、active execution

当前 V2 要区分：

- logical/durable child identity；
- resident runtime；
- active child execution/turn。

AgentRegistry 中的 durable identity 可能继续存在，即使对应 runtime 已从 ThreadManager unload。因此 resident surface 没看到 child，不能推出 child identity 从未 materialize。

N3 必须结合成功 spawn result、Started activity、Host thread identity、durable identity、resident runtime 等可获得 authoritative evidence。排除不了 materialization 时就是 UNKNOWN。

### 12.7 Capacity

公开配置 `agents.max_concurrent_threads_per_session` 的用户层语义是 spawned agents 数量，不包含 primary。内部 V2 session limit 是 root-inclusive。

项目机器合同继续用 root-inclusive Host session capacity 语义。若 probe 来源是公开配置值，先做 spawned-agent-only value 加 primary 的 normalization，再进入 scheduler projection。

实际 Host admission rejection 才是最终 capacity authority。scheduler 只做保守约束投影，不创建私有 occupancy truth。

### 12.8 Role 与 effective permission

Role 配置参与 child config layering，但 live runtime permission、approval、cwd 等还会由 Host runtime 层处理。

因此 profile 中 `sandbox_mode=read-only` 只能证明 requested posture。N8 必须用真实 Host evidence 证明 Advisor effective permission 满足 strict read-only Final Review boundary。

## 13. Real Host 测试为什么必须单独管理

Repository CI 只能证明确定性的 repository/product contracts，没有能力证明当前真实 Codex Host 的：

- 实际 MultiAgent version；
- effective model/effort；
- `fork_turns`；
- descendant collaboration containment；
- Host ThreadId binding；
- actual admission/materialization；
- RUNNING Steer consumption；
- interrupt settlement；
- effective sandbox/permission；
- installed App surface。

因此 V4 release 把 real Host qualification 与 repository CI 分开。

机器 Host gate authority：`docs/v4/host-smoke.json`。

tracked 文件必须保持：

- `status = PENDING`
- `results = {}`

真实结果不能回填这个 tracked JSON，因为一旦写入 repository 就会改变 candidate artifact。

## 14. Real Host Test Ledger，Issue #91

为防止后续会话重复跑已经有结论的实机测试，建立非修改性的 GitHub ledger：

`#91 V4 Real Host Test Ledger`

Issue #91 是当前 real Host operational ledger。它属于 GitHub metadata，不改变 candidate commit/tree。

### 14.1 强制规则

每一个真实 Host 动作都必须单独记录，然后才能进入下一真实 Host 动作。包括：

- local checkout/candidate binding；
- installed package identity check；
- Doctor；
- fresh session 创建；
- Host build/version capture；
- V2 tool surface capture；
- 每一次 `spawn_agent`；
- 每一个 profile 的 N0 route/model/effort/fork 检查；
- 每一次 grandchild adversarial attempt；
- capacity saturation/admission attempt；
- Steer/Correction/Continue；
- Interrupt；
- WriterLease takeover；
- rollout inspection；
- Advisor Final Review permission probe；
- FAIL、UNKNOWN、异常中断、人工观察和 retry。

禁止把多个真正独立的 Host 动作事后压成一句“整个 N0 PASS”。必须保留足够粒度，让新会话知道哪些步骤已经跑过、哪些没有跑、哪些 evidence 可复用。

### 14.2 每条 Host ledger entry 必填字段

```text
HOST-<gate>-<sequence>
Time with timezone:
Candidate commit:
Candidate tree:
PR #81 head:
Host build/version:
Embedded Codex version if observable:
Platform / architecture:
Run/session/thread IDs:
Gate / substep:
Prerequisites:
Operation / exact tool / command:
Material inputs:
Expected outcome:
Observed outcome:
Evidence ref:
Verdict: PASS | FAIL | UNKNOWN | NOT_RUN | INVALIDATED
State / side effects:
Reuse status: reusable | invalidated | superseded
Rerun required: yes/no
Rerun reason or invalidation trigger:
Next allowed step:
Notes:
```

如果某字段拿不到，写 `UNKNOWN` 或 `not observable`，不能猜。

### 14.3 防止非必要重复跑 Host 的规则

一个已经得到 conclusive PASS 的 Host substep，在以下条件全部保持时应直接复用，不得仅因为换了聊天会话就重复运行：

- candidate commit/tree 对该 formal gate 仍有效；
- relevant Plugin/package bytes 未发生影响该步骤的变化；
- target Host build/runtime environment identity 可证明相同；
- 该 gate/substep 的 machine contract 没有发生实质语义变化；
- prerequisite facts 没变；
- evidence 仍存在、可读取、完整且没有 ambiguity；
- previous verdict 明确为 PASS；
- 没有新的失败事实推翻之前的观察。

以下情况才允许或要求重跑 affected step：

1. formal exact-candidate gate 所绑定的 candidate artifact 变化；
2. target Host build/runtime version 或关键 environment identity 变化；
3. 该 gate/substep 的 machine contract 或 oracle 实质变化；
4. 之前 evidence missing、corrupt、ambiguous 或无法重新定位；
5. previous verdict 是 FAIL/UNKNOWN，并且现在存在 changed basis；
6. prerequisite 改变，使旧结果不再代表当前条件；
7. 安装包或 relevant profile/runtime bytes 改变；
8. 实际 Host 行为出现与旧证据冲突的新事实。

OpenAI upstream `main` 变动本身不构成自动重跑理由。如果当前测试目标仍是同一个已安装 Host build，而且 machine contract 没变，upstream 新 commit 只用于技术背景，不应导致无意义重复 Host 测试。

### 14.4 Candidate 变化时怎样处理旧 Host 结果

Formal N0-N8 release gate 要求 exact candidate binding，因此 candidate commit 变化后，旧 formal PASS 不能直接宣称为新 candidate 的正式 PASS。

但旧记录仍保留价值：

- 可证明某 Host build 曾支持某 capability；
- 可帮助识别哪些 probe 无需重新探索设计；
- 可对比新旧环境行为；
- 可帮助只重跑真正受 candidate 绑定影响的动作。

旧 entry 应标记 `superseded` 或 `invalidated`，不要删除。

### 14.5 Ledger 与 handoff 的同步关系

每个 Host 动作立即写 Issue #91 comment，不修改 repository candidate。

只有下一次真实 repository content change 时，才把阶段性 Host 进度摘要顺带更新到本 handoff。禁止为了“记录某个 Host PASS”单独改 handoff，否则会改变 exact candidate，反过来制造新的 Host 重跑需求。

## 15. 历史 Host evidence，禁止重复误用

### 15.1 build 6892 旧 N0

历史 run：`01a02ad1-dbb9-7cb0-990c-188c76f48848`。

Host build：6892。

当时五个 child 的目标 model/effort 曾被观察，但实际 tool path 是 MultiAgent V1，raw spawn 使用 `fork_context=false`，没有 V2 `fork_turns`。

正式结论：`N0 = UNKNOWN`。

这条历史记录不能再次被解释成 V2 N0 PASS，也没有必要为了确认“它确实是 V1”再重复跑旧 build。

### 15.2 build 6962 V2 capability audit

后续独立 audit 观察到 Host build 6962，embedded Codex `0.149.0-alpha.4.1`，Main runtime `multi_agent_version=v2`，并可见 V2 control family。

这证明该环境当时支持 V2，但它不是当前 candidate-bound N0。

如果当前真实 Host build 已变化，不要为了复现旧 6962 audit 而刻意重复。应记录当前 Host build，再测试当前 environment。

### 15.3 旧 exact install

旧候选 `d565af4d1274c07451a803b2ee831ef4a5233883` 曾完成 exact local Marketplace reinstall：50 package files，missing 0、unexpected 0、hash mismatch 0，Doctor 没有 blocking package/profile failure。

当前 `6f1f...` 与旧 `d565...` 的 `.codex-plugin/package-integrity.json` 是同一个 Git blob：

`68d45d987a4883aa1d0af7511afce79801e95a77`

因此截至本 handoff 修改前，Plugin package-byte continuity 已确认。没有技术理由仅因为 PR #88/#89/#90 的 repository-only 文档/Host-contract改动重复 reinstall 同一 50-file payload。

但 current local checkout 和 fresh target Host session 是否绑定正式 candidate 仍是单独的 environment fact，正式 N0 前必须记录。

## 16. N0-N8 当前机器合同

机器 authority：`docs/v4/host-smoke.json`。

| Gate | 当前 release requirement |
| --- | --- |
| N0 | exact role/model/effort，真实 V2，managed spawn `fork_turns=none` |
| N1 | 五个 profile 的 effective collaboration surface；grandchild attempt 必须 tool absent 或 authoritative Host deny，且无 descendant identity materialize |
| N2 | canonical task address 与 authoritative Host thread identity 的 release-evidence binding，并绑定目标 ExecutionBinding/profile |
| N3 | deliberate Host admission rejection；证明 no child identity / no resident runtime materialization；任何歧义为 UNKNOWN |
| N4 | RUNNING Steer via `followup_task`；original child 消费 guidance；无 replacement；same-child Correction/Continue；无 fresh attempt |
| N5 | interrupt return 不释放 WriterLease；current-generation Host settlement 才能 settle |
| N6 | UNKNOWN/unsettled writer 阻止 replacement 和 Main takeover；settlement 后才能 transfer writer |
| N7 | rollout evidence 绑定 lifecycle call、child identity、result，并满足 privacy allowlist |
| N8 | fresh exact-candidate Advisor review；effective Host permission 满足 strict read-only；artifact mutation 使旧 verdict 失效 |

正式 campaign 必须按 gate 依赖推进。N0 未 PASS 时不提前跑 N1。某个 gate 内部也要按实际 substep 逐步写 Issue #91，而不能到最后才补账。

## 17. Repository CI 与 Real Host 的关系

Repository CI 要验证：

- Plugin/Marketplace manifests；
- generated package integrity；
- official Plugin validator；
- Ruff；
- full pytest；
- managed Agent install/check/uninstall/reinstall lifecycle；
- Doctor；
- V4 state/work graph/scheduler/lifecycle/writer contracts；
- update lifecycle；
- migration fail-closed；
- product-surface consistency。

Required matrix：

- Ubuntu Python 3.11
- Ubuntu Python 3.12
- macOS Python 3.11
- Windows Python 3.11

CI PASS 不等于 Host PASS。Host PASS 也不能替代 repository CI。

任何 repository content mutation 产生新的 candidate 后，必须跑新 exact-head repository matrix。Post-commit CI 结果属于非修改性 evidence，不要为了把 PASS 写回 handoff再制造新 HEAD。

## 18. Package、安装与 fresh-session 边界

Plugin version 当前为 `4.0.0`。

生产安装文档使用 Codex Plugin Marketplace。Candidate qualification 可使用 exact local Marketplace checkout 来证明字节身份，production update path 则需要 canonical Git Marketplace resolution。

Package identity 和 repository candidate identity 是两个层次：

- repository commit/tree 可以因为不进入 package 的 docs/test 改动而变化；
- `.codex-plugin/package-integrity.json` 表示 shipped payload 文件和 hash；
- package bytes 相同不等于当前 Host session 已绑定最新 candidate；
- current Host/session binding 仍需 ledger 记录。

首次创建 managed Agent profiles 后，如果当前运行中的 task 无法权威证明 custom Agent registry 已加载这些 profiles，应返回 `RESTART_REQUIRED`，要求 fresh Codex session，不能偷换成其他 Agent profile。

## 19. Release phase 和已知 technical debt

`docs/v4/phase-status.json` 当前 repository phases 为 PASS，但：

- real Host gate：`PENDING_RELEASE_GATE`
- Final Review：`PENDING_RELEASE_GATE`
- external release evidence：`PENDING_RELEASE_GATE`
- publication：`BLOCKED`

`repository_validation.candidate_sha` 中保留的旧 SHA 是历史 repository-validation attestation basis，不是当前 release candidate identity。当前 candidate identity 必须从 Git branch/PR 读取。

`docs/v4/technical-debt.json` 当前主要 open items：

- P2 Doctor Host evidence UX：先观察 N0-N8，再决定是否值得增加更小的 capture UX，不能为了方便重新造 control plane；
- P2 experiment-plane consolidation：非 runtime，release-critical Native Core 稳定后再收敛 calibration helpers；
- P3 state path TOCTOU hardening：现有 state storage 已有 symlink、private dir、`O_NOFOLLOW`、bounded files、fsync、atomic replace 等保护； hostile same-user namespace swap 仍有窄窗口，当前 threat model 下非 blocking。

这些 debt 不能放松 N0-N8 gate。

## 20. PR #88、#89、#90 的关键修复历史

### PR #88，Host contract hardening

- base：旧 candidate `d565af4d...`
- squash：`d79ead8ff70e799368e59616693309bc8598a321`
- title：`fix: harden V4 Host identity and Steer gates`
- files：`docs/v4/architecture.json`、`docs/v4/host-smoke.json`、`tests/test_host_contract_v4.py`
- 没改 production runtime/package payload
- N2：区分 canonical `native_task_name` 与 release-evidence Host thread identity
- N3：增强 admission rejection 与 durable/resident materialization oracle
- N4：明确 RUNNING Steer、Correction、Continue，Steer 当前绑定 V2 `followup_task`
- 修过 capacity 稳定字段兼容 P1
- 修过普通 runtime 不应强制 `agent_id` 的 P1
- 最终四平台 CI PASS，full pytest 526 passed

### PR #89，N4 release documentation closure

- 目的：machine N4 已包含 RUNNING Steer 后，人工 release checklist 也必须明确跑 Steer
- files：`docs/release-checklist.md`、`docs/architecture.md`、`tests/test_release_contracts.py`
- 首轮新增测试因缺少 literal `tool-call` 负向证据措辞失败，1 failed、526 passed
- commit `d2f68d68...` 补齐 “tool-call acceptance alone insufficient” 边界，没有删测试
- 最终合并 commit `4530382427556f20fe8fd57e56108016d5f2a3e2`
- post-merge workflow `32600567749` PASS，full pytest 527 passed

### PR #90，live development handoff

- 建立 `docs/v4/development-handoff.md`
- `README_AI.md` 建立入口
- 修复了 merge 后流程自失效 P1
- 修复了“把 CI 写回 handoff 导致无限新 HEAD” P2
- 修复了 handoff 不可发现 P2
- 修复 `README_AI.md` trailing newline regression，原失败为 1 failed、526 passed
- 最终 squash commit：`6f1f3179f087e72fb1329c13bc6a9024faf117de`
- title：`docs: add live V4 development handoff`
- post-merge exact-head workflow `32602156632` 全绿

## 21. 禁止错误推理

新会话必须主动避免以下推理：

- 从 profile `sandbox_mode=read-only` 推出 effective Host read-only；
- 从 `max_depth=1` 推出 V2 descendant containment；
- 从 child 自述推出 model、effort、permission 或 collaboration surface 的 Host truth；
- 从 V1 `fork_context=false` 推出 V2 `fork_turns=none`；
- 从没有 resident runtime 推出没有 durable child identity；
- 从 `interrupt_agent` 返回成功推出 WriterLease 可释放；
- 从 `followup_task` accepted 推出 RUNNING Steer 已实际应用；
- 从 repository CI PASS 推出 N0-N8 PASS；
- 从旧 candidate exact install 推出新 candidate/session binding；
- 从 OpenAI upstream `main` 更新推出当前已安装 Host 自动变更；
- 从换了新聊天会话推出“所有真 Host 测试都要重跑”；
- 把 UNKNOWN 当 PASS。

## 22. 开发工作流

每次 repository 内容变更：

1. 先读取本 handoff、当前 Git branch/HEAD、相关 machine contracts。
2. 从精确 base 建短生命周期 branch，不直接在 main 上开发。
3. 先确认计划和最小影响范围。
4. 实施变更时同步更新本 handoff，记录时间、触发原因、技术背景、文件、边界、验证、风险、下一步。
5. 非平凡改动要重新问是否有更简单、更符合现有 ownership 的方案。
6. 跑目标测试，再跑完整 required CI。
7. Review findings 必须按根因处理，不能只关 thread。
8. CI/Review 全绿后才允许 merge。
9. 合并后重新读取 exact candidate SHA/tree 和 PR synthetic tree。
10. 跑 post-merge exact-head repository CI。
11. 若进入 Host campaign，严格使用 Issue #91 逐动作记录。

Commit message 要说明实际意图，优先采用清晰 conventional-style，例如：

- `fix: ...`
- `docs: ...`
- `test: ...`
- `refactor: ...`

不要把多个无关修复塞进一个 commit。

## 23. Handoff 自身的维护规则

任何 repository content modification 都必须同步更新本文件。受 GitHub 单文件接口限制时，可以在同一 PR 内用相邻 commits 完成实际文件和 handoff 更新，但 merge 前必须同步完整。

CI、review、PR metadata、Issue #91 Host ledger、安装审计和人工观察属于非 repository content facts。它们不要求为了记录结果单独制造新 candidate。应立即写到对应外部证据位置，并在下一次真实 repository content change 时顺带把阶段摘要补到本 handoff。

本文件不能为了填写“包含本文件修改的 commit SHA”再额外制造自引用 commit。相关 commit 通过 `git log -- docs/v4/development-handoff.md` 解析。

## 24. 当前下一步

本次文档分支合并前：

1. review `docs/v4/development-handoff.md` 是否完整、无过期事实被误写成 current authority；
2. 确认 Issue #91 Host ledger 协议与 handoff 一致；
3. 跑本分支 full repository matrix；
4. 处理所有 review findings；
5. 只有全绿后才 squash merge 回 `v4/rc5-native-core`。

合并后：

1. 重新读取 `v4/rc5-native-core` HEAD/tree；
2. 重新读取 PR #81 head 和 synthetic merge tree，要求 tree 精确一致；
3. 跑新的 post-merge exact-head repository CI；
4. 确认 `docs/v4/host-smoke.json` 仍为 PENDING、`results={}`；
5. 在 Issue #91 记录当前 local checkout、package/session binding 和实际 Host environment identity；
6. fresh Codex session 后只执行正式 N0；
7. N0 每个真实 Host 动作立即写 Issue #91；
8. N0 PASS 后再准备 N1；
9. N1-N8、fresh Final Review、external release evidence、installed-product gate、human two-Skill App observation 全完成前，PR #81 保持 Draft，publication BLOCKED。

## 25. Modification Log

### H001 2026-08-23 05:58 +08:00，建立 live handoff

用户要求把开发上下文持久化到仓库。第一次尝试在已完成使命的旧 `fix/v4-n4-release-doc-closure` 分支产生 `6398444ee184a268980ebee39d7449f8b6ebfd60`，随后发现 PR #89 已先合并，因此该 commit 没进入正式候选。纠偏后从正式 candidate 建 `docs/v4-live-development-handoff`，通过 PR #90 正式落仓。

### H002 2026-08-23 06:02 +08:00，记录 PR #90 首轮 validation

PR #90 首轮 workflow `32601201287` 四平台和 aggregate `policy-tests` PASS。同步 commit `7230a9c12158e3601eb7bb2a01f7a412c44864d9`，message `docs: record handoff PR validation`。对应 final-head workflow `32601391850` PASS。

### H003 2026-08-23 06:06 +08:00，修复 handoff merge-state 自失效

Review P1 指出 handoff 合并后仍要求“等待 PR #90”会自失效。修为按 PR OPEN/MERGED 状态分支执行，并要求重新读取当前 Git HEAD。commit `4011a4eea97844e4b1cff620a244540d9fe7230f`，message `docs: make V4 handoff merge-state aware`。workflow `32601607606` PASS。

### H004 2026-08-23 06:12 +08:00，关闭 handoff 自更新循环并建立入口

Review P2 指出 post-commit CI 若也强制写回 handoff，会形成无限新 HEAD；另一个 P2 指出新会话从 `README_AI.md` 找不到 handoff。新增“非修改性验证不制造新 candidate”规则，并从 `README_AI.md` 链接 handoff。入口 commit `608ff7255454221c4c4555dd75f4219ae610eb33`，handoff commit `a2ca4666187584cd5fe78f290451b86203b3d57c`。

### H005 2026-08-23 06:15 +08:00，修复 README trailing newline regression

H004 后 full pytest 在多平台同步出现 `tests/test_public_surface_regressions.py::test_readme_files_are_valid_basic_text_files` 唯一失败，结果 1 failed、526 passed。根因是 GitHub 单文件写入导致 `README_AI.md` 缺末尾 newline。保留测试，恢复 newline。commit `4ad6be78ebb79bb54b427ef37180b73249244db8`，message `fix: preserve README trailing newline`。最终 PR #90 head workflow `32601974555` 全绿，随后 squash 到 `6f1f3179...`。

### H006 2026-08-23 06:51 +08:00，补全项目背景并建立 Real Host Test Ledger

触发：用户要求把 handoff 的项目交接背景补充完整，并进一步要求实机真 Host 测试的每一步都进行记录，防止后续会话非必要重复跑测试。

修改前正式 candidate：`v4/rc5-native-core@6f1f3179f087e72fb1329c13bc6a9024faf117de`，tree `d3cdefb0944adc8bdd00f500e5e4ea3b4e67bd7b`。

工作分支：`docs/v4-handoff-project-background`。

本次 repository 文件改动：仅 `docs/v4/development-handoff.md`。

新增/强化内容：

- 项目目标和问题定义；
- V4 从旧 lifecycle/Hook 体系迁到 Hookless Native Core 的原因；
- 当前产品面和固定 profiles；
- authority 层级；
- 仓库目录和核心文件职责地图；
- WorkGraph / ExecutionBinding / acceptance / WriterLease / UNKNOWN 关系；
- OpenAI Codex V2 技术背景；
- upstream 历史审查基线 `343074d...` 与当前 `main@8e649e3...` 的区分；
- PR #88/#89/#90 修复历史；
- repository CI、package、installed product、Real Host gate 的边界；
- technical debt；
- 禁止错误推理；
- 开发和 release 下一步；
- Real Host 逐动作记录和防重复运行规则。

同时创建 GitHub Issue `#91 V4 Real Host Test Ledger`。Issue 是 GitHub metadata，不改变 candidate。以后每个真实 Host action 必须立即追加一个独立 ledger entry，记录 candidate、Host environment、operation、inputs、expected/observed、evidence、verdict、side effects、复用状态、失效条件和 next step。

重要设计纠偏：不能为了记录每个 Host PASS 直接修改 repository handoff，否则每一步都会改变 candidate SHA，使刚产生的 exact-candidate evidence 立即失效并诱发重复测试。正确流程是 Host step 立即写 Issue #91，repository handoff 在下一次真实内容修改时汇总阶段进度。

当前 OpenAI upstream 复核：`openai/codex` `main` 已到 `8e649e3afa5cdddfb09a1b85a090b94775045d9b`，其 parent 为此前完整审查基线 `343074d4207d572809bd8cea15f4be1d09d98e0b`。本轮重新读取 V2 `message_tool.rs`、`send_message.rs`、`followup_task.rs` 和 tool spec，确认 QueueOnly / TriggerTurn 以及 RUNNING followup delivery 关键语义仍一致。

明确未变化：production runtime、contracts、`docs/v4/host-smoke.json`、WriterLease、WorkGraph、scheduler implementation、managed profiles、Hook path、Plugin package payload、tracked N0-N8 results 均未修改。

验证要求：本分支必须经过完整 repository matrix、review 和 post-merge exact-head validation 后，才允许新的 candidate 进入正式 Host campaign。
