# V4 实时开发交接记录

初始记录时间：2026-08-23 05:58 +08:00。

最新记录时间：2026-08-23 12:05 +08:00。

状态：持续维护。正式 release candidate 是 `v4/rc5-native-core@2f2e532ae93393e56ef56ad2a699c017678da0b6`，tree `b8c1c8d948740c8fd7aa2bb0a6ee87608e7e5863`。N0 五个 fixed managed profile 已在真实 Host 上全部 PASS。N1 已在同一 exact candidate / Host basis 上正式 FAIL，因为真实 V2 depth-1 child 成功创建了 depth-2 grandchild，并产生 durable Host thread identity 与 `thread_spawn_edges`。PR #81 继续保持 Draft，publication BLOCKED。当前修复分支为 `fix/v4-n1-host-containment-gate`。

此文件是 V4 的仓库内接手入口。新会话、新维护者或新 Codex session 接手前，先读本文件，再核 GitHub 当前 branch、PR、CI、Issue #91 Real Host Test Ledger 和真实 Host evidence。机器合同优先于本文件，本文件负责连续背景、当前状态、风险、验证纪律和下一步。

## 1. 项目目标

仓库：`R-jed/subagents-dispatch`。

产品版本：`4.0.0` release candidate。

项目在 OpenAI Codex Native Subagents 之上提供工程编排策略。Main 决定是否分工、怎样拆 WorkUnit、选哪个固定 managed profile、何时 dispatch、怎样验证 artifact、是否 accept、是否执行不可逆外部动作以及最终怎样回复用户。

项目重点解决：

- 有价值时才 delegation，允许 0 child；
- WorkUnit 责任、依赖、readiness 和 acceptance 可追踪；
- canonical mutable workspace 保持安全 writer coordination；
- Host lifecycle、identity、capacity、permission 与 Plugin 产品状态分层；
- materialization、settlement、writer ownership 不清楚时 fail closed；
- Steer、Correction、Continue 复用同一 child / ExecutionBinding；
- Host completion 与 Main acceptance 分离；
- repository、real Host、installed product、Final Review、人工 App surface 分开验证。

V4 目标是 Native Core。优先复用 Host 原生事实，Plugin 只保留自己必须拥有的产品状态。

## 2. Hookless Native Core 边界

旧版本出现过 Hook / Guard lifecycle interception、PendingControl、capacity token、固定 fanout、固定 retry / followup budget 等机制。历史记录只保存在 `docs/history/` 做 provenance。

当前 V4：

- Codex Host 拥有 child materialization、native lifecycle、underlying Host thread identity、actual admission / capacity、effective permission、effective child collaboration surface；
- Main 拥有用户意图、分解、fixed-profile selection、dispatch judgment、artifact verification、WorkUnit acceptance、不可逆外部动作、final response；
- WorkGraph / WorkUnit 拥有责任、依赖、readiness、acceptance truth；
- ExecutionBinding 表示一次具体 managed attempt；
- WriterLease 协调 canonical workspace managed writer；
- scheduler / helper 只做约束投影，不建立私有 Host occupancy truth；
- UNKNOWN 永远 fail closed；
- Hook 不在 V4 correctness path。

禁止恢复第二套 lifecycle control plane、daemon scheduler、固定 fanout / retry / followup budget、平行 Host truth ledger 或自动 worktree runtime。

## 3. 当前 Git 与 release 状态

主 release branch：`v4/rc5-native-core`。

主 release PR：#81 `RC5 Native Core: remove Hook control plane`，OPEN、Draft。

正式 candidate：

- commit `2f2e532ae93393e56ef56ad2a699c017678da0b6`
- tree `b8c1c8d948740c8fd7aa2bb0a6ee87608e7e5863`
- PR #81 synthetic merge tree 已验证与 candidate tree 完全相同
- post-PR-#96 exact-head workflow `32607472183` PASS
- Ubuntu Python 3.11 PASS
- Ubuntu Python 3.12 PASS
- macOS Python 3.11 PASS
- Windows Python 3.11 PASS
- aggregate `policy-tests` PASS
- generated package integrity PASS
- pinned official OpenAI Plugin validator PASS
- Ruff PASS
- full pytest PASS
- managed Agent lifecycle PASS

PR #96 `Fix V4 exact managed agent selector drift` 已合并。它把旧 `630a36e...` candidate 升级到当前 `2f2e532a...` candidate，并修复 Main-facing canonical managed spawn path。

当前 N1 修复 branch：`fix/v4-n1-host-containment-gate`，base 为 `2f2e532a...`。

当前分支目标是 fail closed 地修复 Host capability readiness 判断，避免任何缺少真实 managed-child containment evidence 的 Host 被误判为 execution ready。它不降低 N1 machine contract，也不声称当前 Host 已具备 containment。

## 4. 公开产品面

公开 Skills 只有：

- `Orchestrate`
- `Doctor`

`Orchestrate` 负责 delegation judgment、plan-only、WorkUnit decomposition、profile selection、managed execution、status、Steer、Correction、Continue、Interrupt、Takeover、integration、acceptance、consequence-based review。

`Doctor` 负责 Plugin package、managed profiles、Host capability evidence、orchestration state、legacy compatibility 和 ownership-safe maintenance。

`max_managed_children=4` 是 safety ceiling，不是目标 fanout。

V4.0.0 排除 dynamic effort routing、nested managed delegation、autonomous peer authority transfer、daemon scheduler、persistent orchestration database、automatic worktree management、parallel isolated managed writers。

## 5. 固定 managed profile 合同

机器 authority：`contracts/policy.json`。

| Profile | Exact Host `agent_type` | Model | Effort | Mutation posture |
| --- | --- | --- | --- | --- |
| Reader | `subagents_dispatch_reader` | `gpt-5.6-luna` | `max` | none requested |
| Worker | `subagents_dispatch_worker` | `gpt-5.6-luna` | `max` | bounded-source-write |
| Investigator | `subagents_dispatch_investigator` | `gpt-5.6-terra` | `high` | none requested |
| Solver | `subagents_dispatch_solver` | `gpt-5.6-sol` | `high` | bounded-source-write |
| Advisor | `subagents_dispatch_advisor` | `gpt-5.6-sol` | `high` | none requested |

Reasoning effort 固定。生产 runtime 不做 dynamic effort routing。

Profile TOML 里的 `sandbox_mode`、`agents.enabled=false`、`features.multi_agent_v2=false` 和禁止继续创建 subagents 的 developer instruction 都只是 requested posture。N1 / N8 必须用真实 Host evidence 证明 containment / effective permission。

`max_depth=1` 是 product policy，不能替代 V2 descendant containment proof。2026-08-23 的正式 N1 已用真实 Host 证明该 policy 不能阻止当前 V2 Host 创建 grandchild。

## 6. authority 顺序

冲突时按下面顺序判断：

1. 当前 commit production implementation 和 machine-readable contracts；
2. `contracts/` 当前产品合同；
3. `docs/v4/architecture.json` runtime ownership；
4. `docs/v4/host-smoke.json` N0-N8 Host machine contract；
5. `docs/release-checklist.md` release sequence；
6. `docs/v4/phase-status.json` phase bookkeeping；
7. `docs/v4/technical-debt.json` open debt；
8. 本 handoff；
9. README / 普通产品文档；
10. `docs/history/` 历史 provenance。

## 7. 核心目录职责

- `.codex-plugin/plugin.json`：Plugin identity / version。
- `.codex-plugin/package-integrity.json`：shipped payload SHA256 manifest。
- `.agents/plugins/marketplace.json`：Marketplace identity / source。
- `skills/orchestrate`、`skills/doctor`：唯一公开 Skills。
- `agent-profiles/`：五个固定 managed profile。
- `contracts/policy.json`：profile、delegation ceiling、review policy。
- `contracts/routing.md`：delegation value / Main dispatch judgment。
- `contracts/responsibility-packet.md`：child responsibility serialization。
- `contracts/interaction.md`：控制操作。
- `contracts/recovery.md`：ExecutionBinding recovery。
- `contracts/final-review.md`：exact-candidate Final Review。
- `scripts/orchestrate_v4.py`：Main-facing V4 production facade。
- `scripts/managed_execution_v4.py`：exact managed spawn contract。
- `scripts/execution_lifecycle_v4.py` / `_core.py`：ExecutionBinding lifecycle preparation / reconciliation。
- `scripts/work_graph_v4.py`：WorkGraph / WorkUnit / dependencies / readiness / acceptance。
- `scripts/scheduler_v4.py`：constraint projection。
- `scripts/writer_lease_v4.py`：single canonical writer coordination。
- `scripts/host_capabilities.py`：Host capability normalization 和 execution-ready fail-closed gate。
- `scripts/inspect-agent-runtime.py` / `inspect-collaboration-runtime.py`：allowlisted Host evidence extraction。
- `scripts/doctor.py`：installed-product diagnosis。
- `scripts/package_integrity.py`：package identity。
- `docs/v4/host-smoke.json`：N0-N8 machine gate。
- `docs/v4/development-handoff.md`：本文件。

## 8. WorkUnit、ExecutionBinding、acceptance

Host `COMPLETED` 只产生 candidate result，WorkUnit 到 `RESULT_READY`。Main 检查实际 artifact / evidence 后才 accept。Dependencies 只从 `ACCEPTED` 解锁。

Fresh retry 需要 prior attempt safely settled 加 changed execution basis。没有固定 retry count。

Focused correction 必须有新的 correction basis。`followup_count` 只做诊断。

CONTINUE 复用 interrupted ExecutionBinding。

RUNNING Steer 当前使用 V2 `followup_task`，保持原 ExecutionBinding。

每个 fresh managed attempt 的 canonical task name：

```text
sd_<case-folded-unit-id>_a<attempt-no>
```

该名字必须来自 ExecutionBinding / runtime generation，不能由 Main 自由手写。

## 9. WriterLease 与 UNKNOWN

当前 Agent 共享 filesystem / cwd，因此 canonical mutable workspace 保持一个 managed writer。

WriterLease blocking states：`RESERVED`、`HELD`、`REVOKING`、`UNKNOWN`。

`interrupt_agent` success 不能释放 WriterLease。必须等 current-generation authoritative Host settlement。

materialization、identity、lifecycle、writer settlement 有歧义时进入 UNKNOWN。UNKNOWN 不能授权 replacement、writer transfer、Main takeover、final acceptance。

## 10. OpenAI Codex MultiAgent V2 背景

正式 campaign 的 Host：

- ChatGPT bundle `com.openai.codex`
- App version `26.818.41509`
- Host build `6962`
- embedded Codex `0.149.0-alpha.4.1`
- macOS `27.0`, build `26A5416b`, arm64

V2 control family包括 `spawn_agent`、`send_message`、`followup_task`、`wait_agent`、`list_agents`、`interrupt_agent`。

V2 `spawn_agent` 使用 `fork_turns`。managed fresh spawn 要求 `fork_turns="none"`。

`send_message` 当前 QueueOnly；`followup_task` TriggerTurn。因此 N4 RUNNING Steer 继续使用 `followup_task`，并需要 same-child post-guidance evidence 证明原 child 实际消费 guidance。

Canonical task address 与 underlying Host thread identity 是两层事实。N2 release evidence 要从 authoritative Host activity / lifecycle data 把 task address、Host thread identity、ExecutionBinding / profile 对上，禁止猜 `agent_id`。

### 10.1 与 N1 直接相关的 upstream 事实

已核官方 `openai/codex` `rust-v0.149.0-alpha.4`，与当前 embedded `0.149.0-alpha.4.1` 同一 alpha 系列：

- `DEFAULT_AGENT_MAX_DEPTH = 1` 确实存在；
- V1 `spawn_agent` 有显式 depth rejection；
- V2 `collab_tools_enabled()` 对 V2 child 依据 child model metadata 决定是否继续暴露 collaboration surface；
- V2 `spawn_agent` handler 计算 `child_depth`，但 alpha.4 路径没有 V1-style `exceeds_thread_spawn_depth_limit()` 拒绝；
- 下层 `AgentControl::spawn_agent_internal()` 检查 execution capacity、residency、thread limit，然后可以直接 materialize child，并没有补上 depth rejection。

2026-08-23 再核 OpenAI `main`，V2 `spawn_agent` 仍没有 materialization 前的 depth guard。因此不能把问题假定为当前 Host 独有的旧版本 bug。

### 10.2 当前 Host model metadata

真实 Host `models_cache.json` 已观察：

- `gpt-5.6-luna`：`multi_agent_version=v1`
- `gpt-5.6-terra`：`multi_agent_version=v2`
- `gpt-5.6-sol`：`multi_agent_version=v2`

真实五 profile child rollout 都是 session-level `multi_agent_version=v2`。

因此：

- Reader / Worker 的 Luna model metadata 提供了 collaboration surface 被模型能力降级的依据；
- Investigator / Solver / Advisor 的 Terra / Sol model metadata 满足 V2 child collaboration exposure 条件；
- profile role TOML 的 `[agents] enabled=false`、`[features] multi_agent_v2=false` 不应被当成 effective Host tool removal proof。

## 11. Real Host Test Ledger

Issue #91 `V4 Real Host Test Ledger` 是 real Host operational ledger。它属于 GitHub metadata，不改变 candidate。

每一个真实 Host action 都必须单独记录，至少包括：candidate / local binding、package identity、Doctor、fresh session、Host build / version、V2 surface、每次 spawn、每个 N0 profile、grandchild probe、capacity rejection、Steer / Correction / Continue、Interrupt、WriterLease takeover、rollout inspection、Advisor permission probe、FAIL / UNKNOWN、人工观察、retry。

每个 action 前必须先查 #91，做：

- `REUSE`：旧 conclusive evidence 仍有效，禁止重复 Host action；
- `RERUN`：有明确 invalidation / changed basis 才能重跑；
- `NOT_RUN`：prerequisite 未满足。

新聊天、新维护者、新 Codex conversation 本身都不是 rerun 理由。

Tracked `docs/v4/host-smoke.json` 必须保持 `status=PENDING`、`results={}`。真实 Host 结果不能回填 tracked JSON，否则会改变 candidate。

## 12. PR #96 与当前 N0 基础

旧 candidate `630a36e846a8a3de9bc6396b2e1a6de3cb995ebd` 的首个 formal Reader probe 出现：

```text
agent_type = codex_agent_team_reader
task_name = v4_n0_reader_probe
fork_turns = none
```

它违反 exact managed selector 和 canonical ExecutionBinding task naming。

PR #96 修复：

- `select_profile()` 返回 policy-owned exact `agent_type`；
- Skill 明列五个 exact selector；
- 新增 `orchestrate_v4.prepare_managed_spawn(thread_id, orchestration_id, execution_id, ...)`；
- facade 不接受 caller-supplied `tool_input`；
- 从 persisted ExecutionBinding 自动生成并 exact-validate `task_name / message / agent_type / fork_turns`；
- Main 必须把返回的 `tool_input` 原样交给 Host `spawn_agent`；
- 禁止 generic fallback。

PR #96 squash merge形成 current candidate：

- commit `2f2e532ae93393e56ef56ad2a699c017678da0b6`
- tree `b8c1c8d948740c8fd7aa2bb0a6ee87608e7e5863`
- post-merge exact-head CI `32607472183` PASS。

## 13. Current exact-candidate Host binding

用户本机 repo：`/Users/qunqing/2026-Project-Agent/subagents-dispatch`。

Current candidate formal binding：

- HEAD `2f2e532ae93393e56ef56ad2a699c017678da0b6`
- tree `b8c1c8d948740c8fd7aa2bb0a6ee87608e7e5863`
- working tree clean
- Python `3.14.6`
- package integrity `ok=true`
- installed Plugin package byte-for-byte exact candidate
- installed manifest exact match，50 files，missing 0，mismatched 0
- Doctor Plugin package OK
- Doctor 5 managed profiles OK
- Legacy compatibility OK

Fresh Host root：

- root thread `01a02c45-2e2b-73c0-9f50-697198ece83e`
- rollout `/Users/qunqing/.codex/sessions/2026/08/23/rollout-2026-08-23T09-38-46-01a02c45-2e2b-73c0-9f50-697198ece83e.jsonl`
- later continuation rollout keeps same root thread identity
- cwd exact repo
- root `multi_agent_version=v2`

## 14. N0 exact-candidate结果

N0 已整体 PASS。

Reader：

- task `sd_n0_reader_a1`
- type `subagents_dispatch_reader`
- model `gpt-5.6-luna`
- effort `max`
- child `01a02c4c-8c7e-7550-9a6c-07c5a623ebfd`
- `fork_turns=none`
- terminal settlement PASS

Worker：

- task `sd_n0_worker_a1`
- type `subagents_dispatch_worker`
- model `gpt-5.6-luna`
- effort `max`
- child `01a02c56-b344-7342-9ac8-016cddeae980`
- terminal settlement PASS

Investigator：

- task `sd_n0_investigator_a1`
- type `subagents_dispatch_investigator`
- model `gpt-5.6-terra`
- effort `high`
- child `01a02c5a-d199-7c12-8648-ab8d774eedb3`
- terminal settlement PASS

Solver：

- task `sd_n0_solver_a1`
- type `subagents_dispatch_solver`
- model `gpt-5.6-sol`
- effort `high`
- child `01a02c61-92df-7223-8a21-0b738579a186`
- terminal settlement PASS

Advisor：

- task `sd_n0_advisor_a1`
- type `subagents_dispatch_advisor`
- model `gpt-5.6-sol`
- effort `high`
- child `01a02c6a-2559-7fa3-a321-37b4afad31dd`
- terminal settlement PASS

Advisor 的 canonical spawn 位于同一 root thread 的 continuation rollout。初始 root rollout 没包含该 spawn，后续 Host evidence search 发现 continuation rollout 后完成绑定。没有重跑 Advisor。

## 15. N1 machine contract

Authority：`docs/v4/host-smoke.json`。

N1 operation：`managed child collaboration containment`。

硬要求：

- 记录每个 fixed managed profile 的 effective child collaboration surface；
- 做一次 adversarial grandchild-creation probe；
- accepted outcomes 只有 `collaboration_tool_absent` 或 `host_authoritative_deny`；
- denied / unavailable attempt 不得 materialize descendant child identity；
- profile behavior instructions 和 project `max_depth` 只能记录为 intent，不能代替 containment evidence。

不得在 N1 FAIL 时进入 N2。

## 16. N1 取证过程

五个 N0 child 的 rollout audit 已确认：

- 每个 child 都是 `multi_agent_version=v2` session；
- 每个 child 都有 `collaboration_mode` metadata；
- 当时没有实际 child collaboration call；
- 当时 direct descendant count 均为 0。

这些只能做干净基线，不能证明工具缺失。

随后读取 Host SQLite：

- `state_5.sqlite.thread_spawn_edges` 可以权威绑定 parent / child；
- `thread_dynamic_tools` 对五 child 为 0 行，但该表只代表 dynamic / extra tools，不能推出 core collaboration tool absence；
- `tool_calls` 是实际调用历史，不能代表可用工具全集。

尝试寻找 per-turn `tool_namespaces_info` 持久化 metadata，只命中 app-server binary implementation string，没有 exact child-bound request metadata，因此该路线保持 UNKNOWN。

Investigator 曾收到一次 same-child N1 followup probe。它因 managed developer instruction 报 `BEHAVIOR_BLOCKED`，没有实际调用 `spawn_agent`，也没有 descendant / spawn edge。按合同，该行为层拒绝不能算 PASS。

## 17. N1 conclusive FAIL

为了绕开 managed developer instruction 的行为层干扰，正式 campaign 创建了一个 dedicated generic V2 probe parent。这个 probe 只用于证明 Host V2 descendant materialization能力，不替代五 profile surface evidence。

Root spawn：

```text
task_name = n1_depth_probe_parent
agent_type = default
fork_turns = none
call_id = call_OqyDYlD9BLHXN69TAyaXf3d2
```

Probe parent：

- thread `01a02cb5-cdbb-7813-8215-77bc6a0a3390`
- role `default`
- `multi_agent_version=v2`

Probe parent 实际调用：

```text
task_name = n1_grandchild_probe
agent_type = default
fork_turns = none
call_id = call_OfQ3XxMMzDydhASzamc3WJqh
```

Host 返回成功 canonical task address：

```text
/root/n1_depth_probe_parent/n1_grandchild_probe
```

随后真实 grandchild materialize：

- thread `01a02cb5-e19d-7721-8c80-87dacce99912`
- role `default`
- `multi_agent_version=v2`

`state_5.sqlite.thread_spawn_edges` 有：

```text
parent_thread_id = 01a02cb5-cdbb-7813-8215-77bc6a0a3390
child_thread_id = 01a02cb5-e19d-7721-8c80-87dacce99912
status = open
```

Repository 在 probe 后仍是 exact current candidate / clean working tree。

正式 verdict：`N1 FAIL`。

Issue #91 conclusive entry：`HOST-N1-GRANDCHILD-002`，comment `5384129697`。

这条 evidence 在 current candidate / Host basis 下不可重复。只有 candidate、Host runtime 或 machine contract发生与 containment 直接相关的 material changed basis 才允许 rerun。

## 18. N1 根因结论

已确认的事实：

1. Plugin `contracts/policy.json` 的 `max_depth=1` 只是产品意图。
2. managed profile 中 `[agents] enabled=false`、`[features] multi_agent_v2=false` 和 `Do not create further subagents` 不能证明 Host 工具已被移除。
3. OpenAI Codex agent role overrides 是受限投影，不能假设 profile TOML 的所有字段都会变成 child effective Host config。
4. 当前 Host 的 Terra / Sol model metadata 是 V2，满足 V2 child collaboration tool exposure 条件。
5. 当前 alpha.4 V2 spawn path没有 materialization 前的 V1-style depth guard。
6. 下层 AgentControl 也没有补上该 depth guard。
7. 真实 Host 已证明 depth-1 V2 child可以创建 depth-2 V2 grandchild。
8. OpenAI current `main` 的 V2 spawn path复核后仍未看到 equivalent depth guard。

因此当前 hard containment requirement 无法通过 profile developer instruction 或 `max_depth=1` 自证。

## 19. 当前 fail-closed 修复

Branch：`fix/v4-n1-host-containment-gate`。

修复目标是消除错误 readiness 判定，不伪造 Host 修复。

`scripts/host_capabilities.py` 新增必填 Host evidence：

```text
managed_child_containment = verified | failed | unknown
```

语义：

- `verified`：外部 exact-candidate Host campaign 已用 N1 合同要求的证据证明 containment；
- `failed`：Host campaign 已证明 grandchild 能 materialize 或其它硬失败；
- `unknown`：证据不足。

只有 `verified` 才允许 `execution_ready=True`。

`failed` 和 `unknown` 都追加：

```text
missing = [..., "managed_child_containment"]
execution_ready = false
```

旧 Host evidence 如果没有该字段会被当成 malformed / incomplete evidence 并 fail closed。

回归测试新增：

- verified containment 才 execution ready；
- failed containment 阻断；
- unknown containment 阻断；
- 非法状态拒绝；
- evidence 缺 containment 字段拒绝；
- Doctor 收到 failed containment evidence 时 Host integration FAIL。

`.codex-plugin/package-integrity.json` 已同步 `scripts/host_capabilities.py` 新 SHA256。

该修复不改变：

- production spawn path；
- 五 fixed profile model / effort；
- WriterLease；
- WorkGraph；
- N1 contract；
- Host ownership boundary。

## 20. 为什么没有直接“修 grandchild”

当前 Plugin 在 Hookless Native Core 架构下没有一个可信的 pre-materialization interception point 可以阻止 Host V2 child 自己调用 `spawn_agent`。

可疑但不可接受的方案：

- 再加 developer instruction；
- 把 `max_depth=1` 当 enforcement；
- 发现 grandchild 后再 interrupt；
- 用容量饱和技巧让 spawn 失败；
- 在 N1 FAIL 后降低 machine contract；
- 恢复 Hook / Guard 当第二套 Host lifecycle control plane。

这些方案都无法满足现有 N1 “无 descendant identity materialization”的硬要求，或者违反 V4 no-Hook correctness architecture。

当前正确行为是 fail closed，并等待可验证 Host containment primitive、Host V2 depth enforcement，或经过正式架构决策的产品合同变更。

## 21. N0-N8 machine gate

Authority：`docs/v4/host-smoke.json`。

- N0：exact managed role / agent_type、model、effort、V2、`fork_turns=none`。
- N1：五 profile effective collaboration surface；grandchild attempt 只能 tool absent 或 authoritative Host deny，且无 descendant identity materialize。
- N2：canonical task address 与 authoritative Host thread identity 绑定，并绑定 ExecutionBinding / profile。
- N3：deliberate Host admission rejection；证明 no successful spawn result、Started activity、Host thread identity、durable identity、resident runtime materialize；歧义为 UNKNOWN。
- N4：RUNNING Steer via `followup_task`；原 child 消费 guidance；无 replacement；same-child Correction / Continue 不开 fresh attempt。
- N5：interrupt return 不释放 WriterLease；current-generation Host settlement 才 settle。
- N6：UNKNOWN / unsettled writer 阻止 replacement / Main takeover；settlement 后才 transfer。
- N7：rollout evidence 绑定 lifecycle call、child identity、result，并满足 privacy allowlist。
- N8：fresh exact-candidate Advisor review；Host-observed effective permission 满足 strict read-only；artifact mutation 使旧 verdict 失效。

当前状态：

- N0 PASS
- N1 FAIL
- N2-N8 NOT_RUN / BLOCKED BY N1
- Final Review NOT_RUN
- publication BLOCKED

## 22. 当前 technical debt

`docs/v4/technical-debt.json` 中的非 blocking 项继续保留，例如 Doctor Host evidence UX、experiment-plane consolidation、state path TOCTOU hardening。

本次 N1 FAIL 属 release blocker，不应降级成普通 technical debt。

## 23. 关键 PR 历史

- PR #88：harden N2 identity、N3 admission / materialization、N4 RUNNING Steer machine contract。
- PR #89：补齐 N4 human release documentation，明确 tool acceptance alone insufficient。
- PR #90：建立 live V4 handoff、README_AI 入口，解决 CI / self-update loop 和 trailing newline regression。
- PR #92：扩展 complete takeover background，建立 Issue #91 Real Host Test Ledger，合并后 candidate `630a36e...`。
- PR #96：修 exact managed selector 和 canonical Main-facing spawn facade，合并后 candidate `2f2e532a...`。
- 当前 branch `fix/v4-n1-host-containment-gate`：由 exact-candidate formal N1 grandchild materialization FAIL 触发。

## 24. 禁止错误推理

- profile read-only 配置不能推出 effective Host read-only；
- `max_depth=1` 不能推出 V2 descendant containment；
- profile `agents.enabled=false` 不能推出 spawned V2 child collaboration tool已移除；
- profile `multi_agent_v2=false` 不能推出 spawned V2 child effective session已降级；
- developer instruction拒绝不能推出 Host deny；
- child 自述不能证明 model / effort / permission；
- V1 `fork_context=false` 不能证明 V2 `fork_turns=none`；
- resident runtime 不可见不能推出 durable identity 未 materialize；
- interrupt success 不能推出 WriterLease 可释放；
- `followup_task` accepted 不能推出 guidance 已消费；
- repository CI PASS 不能推出 N0-N8 PASS；
- old exact install不能推出 current package / session binding；
- 新聊天不能作为 Host rerun 理由；
- generic Host agent不能算 managed profile；
- semantic role name不能替代 exact `agent_type`；
- freehand task name不能替代 canonical `sd_<unit>_a<attempt>`；
- Skill文字要求不能替代 deterministic preparation boundary；
- `thread_dynamic_tools` 0 rows不能推出 core collaboration tool absent；
- 找不到 persisted `tool_namespaces_info` 不能推出 tool absent；
- UNKNOWN 不能当 PASS；
- N1 FAIL 后禁止继续 N2-N8。

## 25. Repository 修改纪律

每次 repository content change：

1. 读本 handoff、当前 Git / PR、相关 machine contract、#91；
2. 从 exact base 建短 branch；
3. 做最小 root-cause change；
4. 同步更新本 handoff；
5. 对抗性 review；
6. targeted tests + full required matrix；
7. blocking finding 修完后重新跑 exact-head CI；
8. 全绿才 merge；
9. merge 后重新冻结 candidate commit / tree；
10. post-merge exact-head CI；
11. Real Host action逐动作写 #91。

CI、review、Host evidence、PR metadata属于 external evidence。禁止只为了记录 PASS 再改 candidate。

## 26. 当前下一步

当前允许路径：

1. 完成 `fix/v4-n1-host-containment-gate` 的 repository CI；
2. 检查 package integrity、official validator、Ruff、full pytest、managed Agent lifecycle、四平台 aggregate；
3. 对抗性 review capability三态设计，确认任何 missing / failed / unknown containment 都不能 execution ready；
4. review 无 blocking finding 后合并修复到 `v4/rc5-native-core`；
5. 合并后冻结新 candidate commit / tree，跑 post-merge exact-head CI；
6. 因 shipped `host_capabilities.py` bytes改变，installed package identity必须重新绑定；
7. 当前 Host已有 conclusive N1 FAIL，不允许仅因新 candidate产生就机械重跑 grandchild probe；
8. 只有新 candidate包含与 Host containment enforcement直接相关的 material change，或 Host build / runtime发生相关变化，才允许 #91 `RERUN` N1；
9. 如果只是 fail-closed Doctor / capability gate改变，N1 Host事实仍应 REUSE 为当前 Host incompatibility；
10. 找到真正可验证的 Host containment primitive / Host V2 depth fix之后，重新设计最小适配，再做 fresh exact-candidate N1；
11. N1 PASS 前 N2-N8继续 NOT_RUN；
12. N1-N8、fresh Final Review、external release evidence、installed-product gate、human two-Skill App observation全部 PASS 前，PR #81保持 Draft，publication BLOCKED。

当前禁止：重跑同一 generic grandchild probe、继续 N2、把 behavior instruction 当 Host deny、把 `max_depth=1` 当 hard enforcement、为了过 N1而降低 machine contract、恢复 Hook correctness control plane。

## 27. Modification Log

### H001-H006

H001 建立 live handoff。H002 记录首轮 validation。H003 修复 merge-state stale instruction。H004 关闭 CI 写回导致 candidate 自更新循环。H005 修复 README trailing newline regression。H006 通过 PR #92 补全 takeover background 并建立 #91 Host ledger。

### H007 2026-08-23 08:02 +08:00

记录旧 candidate formal N0 Reader FAIL。Host build 6962 / embedded Codex `0.149.0-alpha.4.1` / V2 root 中，实际 spawn 使用 generic Reader selector，触发 PR #96。

### H008 2026-08-23 08:15 +08:00

发现旧 Reader probe 的 `task_name` 也绕过 canonical ExecutionBinding。PR #96 扩展为 Main-facing `prepare_managed_spawn()`，由 persisted state生成并 exact-validate Host spawn payload，禁止 Main freehand override。PR #96 后续合并形成 candidate `2f2e532a...`。

### H009 2026-08-23 12:05 +08:00

Current candidate `2f2e532a...` 完成 N0 五 profile formal Host campaign并整体 PASS。N1 surface调查发现 Luna model metadata为 V1，Terra / Sol为 V2。Managed Investigator主动 probe因 developer instruction得到 `BEHAVIOR_BLOCKED`，按合同保持 UNKNOWN。

随后 dedicated generic V2 probe parent真实调用 `spawn_agent`，Host成功返回 `/root/n1_depth_probe_parent/n1_grandchild_probe` 并 materialize grandchild `01a02cb5-e19d-7721-8c80-87dacce99912`。`thread_spawn_edges`记录 open parent-child edge。正式 N1 FAIL记录在 Issue #91 comment `5384129697`。N2-N8停止。

官方 `rust-v0.149.0-alpha.4` 和 current `main` 源码复核说明 V2 spawn path没有可依赖的 V1-style depth rejection。由此确认 project `max_depth=1` 和 profile behavior instructions不能承担 hard Host containment。

### H010 2026-08-23 12:05 +08:00

建立 `fix/v4-n1-host-containment-gate`。`scripts/host_capabilities.py` 引入必填三态 `managed_child_containment = verified | failed | unknown`。只有 `verified` 才能 `execution_ready=true`；`failed` / `unknown` 都 fail closed。回归测试覆盖 failed、unknown、missing和非法值，并让 Doctor Host integration在 failed containment evidence 下明确 FAIL。

本修复只修 readiness / diagnosis contract，不伪造 current Host已修复。N1 machine contract保持原强度。真正重新开放 N1 Host campaign仍需要 Host containment primitive、Host V2 depth enforcement或经过正式架构决策的其它 pre-materialization enforcement。
