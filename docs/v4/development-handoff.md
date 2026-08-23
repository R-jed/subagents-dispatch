# V4 实时开发交接记录

初始记录时间：2026-08-23 05:58 +08:00。

最新记录时间：2026-08-23 13:31 +08:00。

状态：持续维护。正式 release branch 为 `v4/rc5-native-core`，主 release PR 为 #81 `RC5 Native Core: remove Hook control plane`，保持 OPEN / Draft。当前正式 candidate 为 `3bc593fbae535b1d31d28f3f46dc59677ef87c52`，tree `eadcf99c3c339428256412319da005f482df8935`。PR #98 `Fail closed on unverified V4 child containment` 已合并，post-merge exact-head workflow `32617888028` 全绿。N0 的 exact managed routing/model/effort 证据可从前一 candidate 复用，因为 PR #98 未修改 managed profile、canonical spawn path 或相关 runtime bytes。N1 的真实 Host FAIL 同样继续有效，因为 PR #98 只修 capability readiness 的 fail-closed 语义，没有改变 Host containment enforcement。N2-N8 继续 NOT_RUN / BLOCKED BY N1，Final Review NOT_RUN，publication BLOCKED。

此文件是 V4 的仓库内接手入口。新会话、新维护者或新 Codex session 接手时，先读本文件，再核 GitHub 当前 PR #81、Issue #91 Real Host Test Ledger、当前 branch/head/tree、最新 CI 和相关 machine contract。机器合同优先于本文件。新聊天本身不能触发 Real Host 重跑。

## 1. 项目目标

仓库：`R-jed/subagents-dispatch`。

产品版本：`4.0.0` release candidate。

项目在 OpenAI Codex Native Subagents 之上提供工程编排策略。Main 决定是否 delegation、怎样拆 WorkUnit、选哪个固定 managed profile、何时 dispatch、怎样验证 artifact、是否 accept、何时执行不可逆外部动作以及最终怎样回复用户。

核心目标：

- delegation 只在有独立价值时发生，0 child 是正常结果；
- WorkGraph / WorkUnit 管责任、依赖、readiness 和 acceptance；
- ExecutionBinding 表示一次具体 managed attempt；
- canonical mutable workspace 通过 WriterLease 保持单 managed writer 协调；
- Host lifecycle、identity、capacity、effective permission、effective collaboration surface 与 Plugin 产品状态分层；
- materialization、settlement、writer ownership 有歧义时 fail closed；
- Steer、Correction、Continue 尽量复用同一 child / ExecutionBinding；
- Host completion 与 Main acceptance 分离；
- repository、real Host、installed product、Final Review、人工 App surface 分开验证。

V4 继续采用 Hookless Native Core。优先复用 Host 原生事实，Plugin 只保留自身必须拥有的产品状态。禁止为解决 N1 恢复第二套 lifecycle correctness runtime。

## 2. 当前 authority 与架构边界

冲突时优先顺序：

1. 当前 commit 的 production implementation 与 machine-readable contracts；
2. `contracts/` 当前产品合同；
3. `docs/v4/architecture.json` runtime ownership；
4. `docs/v4/host-smoke.json` N0-N8 machine gate；
5. `docs/release-checklist.md` release sequence；
6. `docs/v4/phase-status.json` phase bookkeeping；
7. `docs/v4/technical-debt.json` technical debt；
8. 本 handoff；
9. README 和普通说明文档；
10. `docs/history/` 历史 provenance。

当前 ownership：

- Codex Host 拥有 child materialization、native lifecycle truth、underlying Host thread identity、actual admission/capacity、effective permission、effective child collaboration surface；
- Main 拥有用户意图、decomposition、explicit fixed-profile selection、dispatch judgment、integration、artifact verification、WorkUnit acceptance、不可逆外部动作、final response；
- WorkGraph / WorkUnit 拥有责任结构、依赖、readiness、acceptance truth；
- ExecutionBinding 拥有一次 managed attempt 与 generation；
- WriterLease 拥有 canonical workspace managed writer coordination；
- scheduler/helper 只做约束投影，不维护私有 Host occupancy truth；
- UNKNOWN 永远 fail closed；
- Hook 不在 V4 correctness path。

禁止引入 daemon scheduler、persistent orchestration database、固定 fanout、固定 retry/followup budget、自动 worktree runtime、第二套 Host lifecycle ledger 或自动平行 writers。

## 3. 当前正式 Git / CI 状态

正式 branch：`v4/rc5-native-core`。

正式 PR：#81，OPEN、Draft，当前 mergeable。

当前 exact candidate：

- commit `3bc593fbae535b1d31d28f3f46dc59677ef87c52`
- tree `eadcf99c3c339428256412319da005f482df8935`
- PR #81 synthetic merge commit `1bb48b1b36dd6a4b61795bf95e6ebd5214beb26c`
- synthetic merge tree `eadcf99c3c339428256412319da005f482df8935`
- candidate tree 与 synthetic merge tree 完全相同
- authoritative exact-head workflow `32617888028` PASS
- Ubuntu Python 3.11 PASS
- Ubuntu Python 3.12 PASS
- macOS Python 3.11 PASS
- Windows Python 3.11 PASS
- aggregate `policy-tests` PASS
- generated package-integrity PASS
- pinned official OpenAI Plugin validator PASS where applicable
- Ruff PASS
- full pytest PASS on required platforms
- managed Agent lifecycle PASS on required platforms

当前 publication 仍为 BLOCKED。Repository CI 全绿只证明 repository gate，不改变 N1 FAIL。

## 4. 当前公开产品面与 fixed profiles

公开 Skills 只有：

- `Orchestrate`
- `Doctor`

机器 authority：`contracts/policy.json`。

当前正式 fixed managed profiles 仍为：

| Profile | Exact Host `agent_type` | Model | Effort | Mutation posture |
| --- | --- | --- | --- | --- |
| Reader | `subagents_dispatch_reader` | `gpt-5.6-luna` | `max` | none requested |
| Worker | `subagents_dispatch_worker` | `gpt-5.6-luna` | `max` | bounded-source-write |
| Investigator | `subagents_dispatch_investigator` | `gpt-5.6-terra` | `high` | none requested |
| Solver | `subagents_dispatch_solver` | `gpt-5.6-sol` | `high` | bounded-source-write |
| Advisor | `subagents_dispatch_advisor` | `gpt-5.6-sol` | `high` | none requested |

Reasoning effort固定。Production runtime 不做 dynamic effort routing。

`max_managed_children=4` 是 safety ceiling，不是目标 fanout。

V4.0.0 继续排除 dynamic effort routing、nested managed delegation、autonomous peer authority transfer、daemon scheduler、persistent orchestration database、automatic worktree management 和 parallel isolated managed writers。

Profile TOML 中的 `sandbox_mode`、`agents.enabled=false`、`features.multi_agent_v2=false` 和禁止继续创建 subagents 的 developer instruction 都属于 configured / behavioral posture。N1 和 N8 必须依靠真实 Host evidence。

## 5. PR #96 canonical managed spawn 修复

旧 candidate `630a36e846a8a3de9bc6396b2e1a6de3cb995ebd` 的 formal N0 Reader probe 曾观察到：

```text
agent_type = codex_agent_team_reader
task_name = v4_n0_reader_probe
fork_turns = none
```

它违反 exact managed selector 与 canonical ExecutionBinding task naming。

PR #96 `Fix V4 exact managed agent selector drift` 已合并，并形成 prior candidate：

- commit `2f2e532ae93393e56ef56ad2a699c017678da0b6`
- tree `b8c1c8d948740c8fd7aa2bb0a6ee87608e7e5863`
- post-merge exact-head workflow `32607472183` PASS

PR #96 的关键修复：

- `select_profile()` 返回 policy-owned exact `agent_type`；
- Skill 明列五个 exact selector；
- 新增 Main-facing `orchestrate_v4.prepare_managed_spawn(thread_id, orchestration_id, execution_id, ...)`；
- facade 不接受 caller supplied freehand spawn payload；
- 从 persisted ExecutionBinding 构建 canonical `task_name/message/agent_type/fork_turns`；
- `prepare_spawn()` 做 exact equality validation；
- Main 必须把返回的 `tool_input` 原样交给 Host `spawn_agent`；
- exact selector unavailable/omitted/rejected 时停止 delegation；
- generic fallback 禁止。

该修复已经被 prior candidate 的 N0 真实 Host evidence 验证有效。

## 6. Real Host Test Ledger 纪律

Issue #91 `V4 Real Host Test Ledger` 是 append-only real Host operational ledger。

每一个真实 Host action 前必须先查 #91，并明确：

- `REUSE`：已有 conclusive evidence 仍有效，本次不做 Host call；
- `RERUN`：存在与该 gate 直接相关的 material changed basis；
- `NOT_RUN`：prerequisite 未满足。

新会话、新窗口、新 Codex conversation、新 assistant 本身都不能成为 rerun 理由。

每个 Host action 要记录 candidate commit/tree、PR #81 head、Host build/version、platform/arch、root session/thread、gate/substep、操作、输入、预期、观察结果、evidence、verdict、state change 和 reuse/rerun basis。

`PASS`、`FAIL`、`UNKNOWN`、`NOT_RUN`、`INVALIDATED` 必须分开。UNKNOWN 不能升级成 PASS。

Tracked `docs/v4/host-smoke.json` 始终保持 `status=PENDING`、`results={}`。真实 Host result 留在 #91，不回填 tracked JSON。

## 7. Formal Host environment 与 prior exact install

N0/N1 campaign 的 Host basis：

- ChatGPT bundle `com.openai.codex`
- App version `26.818.41509`
- Host build `6962`
- embedded Codex `0.149.0-alpha.4.1`
- macOS `27.0`, build `26A5416b`, arm64
- Python `3.14.6`
- root thread `01a02c45-2e2b-73c0-9f50-697198ece83e`
- root initial rollout `/Users/qunqing/.codex/sessions/2026/08/23/rollout-2026-08-23T09-38-46-01a02c45-2e2b-73c0-9f50-697198ece83e.jsonl`
- root continuation rollout preserves same root thread identity
- cwd `/Users/qunqing/2026-Project-Agent/subagents-dispatch`
- root `multi_agent_version=v2`

Prior candidate `2f2e532a...` 的 installed package identity 曾正式 PASS：

- package entries 50
- missing 0
- mismatched 0
- manifest equality PASS
- package integrity `ok=true`
- Doctor Plugin package OK
- Doctor managed profiles 5 OK
- repository exact and clean

当前 candidate `3bc593fb...` 修改了 shipped `scripts/host_capabilities.py` 和对应 manifest bytes，因此 prior installed-package byte identity不能直接代表当前 candidate。需要 installed-product verification 时必须重新绑定当前 exact candidate。

## 8. N0 结果与当前复用判断

Prior exact candidate `2f2e532a...` 上，五个 fixed managed profile 都取得 formal Real Host PASS 与 terminal settlement。

Reader：

- task `sd_n0_reader_a1`
- selector `subagents_dispatch_reader`
- child `01a02c4c-8c7e-7550-9a6c-07c5a623ebfd`
- model `gpt-5.6-luna`
- effort `max`
- `fork_turns=none`

Worker：

- task `sd_n0_worker_a1`
- selector `subagents_dispatch_worker`
- child `01a02c56-b344-7342-9ac8-016cddeae980`
- model `gpt-5.6-luna`
- effort `max`

Investigator：

- task `sd_n0_investigator_a1`
- selector `subagents_dispatch_investigator`
- child `01a02c5a-d199-7c12-8648-ab8d774eedb3`
- model `gpt-5.6-terra`
- effort `high`

Solver：

- task `sd_n0_solver_a1`
- selector `subagents_dispatch_solver`
- child `01a02c61-92df-7223-8a21-0b738579a186`
- model `gpt-5.6-sol`
- effort `high`

Advisor：

- task `sd_n0_advisor_a1`
- selector `subagents_dispatch_advisor`
- child `01a02c6a-2559-7fa3-a321-37b4afad31dd`
- model `gpt-5.6-sol`
- effort `high`

Advisor canonical spawn 位于同一 root thread 的 continuation rollout。初始 rollout 未包含该 spawn，后续通过 continuation rollout 完成绑定，没有重跑 Advisor。

当前 candidate `3bc593fb...` 只修改 capability readiness / diagnosis 相关 shipped bytes，没有修改五个 managed profile、canonical spawn path、model/effort selector 或 N0 execution path。PR #81 已明确记录：N0 routing/model/effort evidence 可继续 REUSE。新会话不得仅因 candidate SHA 改变机械重跑 N0。

## 9. N1 machine contract

Authority：`docs/v4/host-smoke.json`。

N1 operation：managed child collaboration containment。

硬要求：

- 记录每个 fixed managed profile 的 effective child collaboration surface；
- 做一次 adversarial grandchild creation probe；
- accepted outcomes 只有 `collaboration_tool_absent` 或 `host_authoritative_deny`；
- denied/unavailable attempt 不得 materialize descendant child identity；
- profile behavior instruction、role label 和 project `max_depth` 都不能代替 Host containment evidence。

N1 FAIL 时 N2-N8 必须停止。

## 10. N1 调查与决定性 FAIL

五个 managed child 的 rollout audit 曾确认：

- 每个 child 都是 session-level `multi_agent_version=v2`；
- 每个 child 都有 collaboration metadata；
- 当时没有实际 child collaboration call；
- 当时 direct descendant count 为 0。

这些只构成干净基线，不能证明 tool absence。

Host SQLite 调查确认：

- `state_5.sqlite.thread_spawn_edges` 可权威绑定 parent / child；
- `thread_dynamic_tools` 的 0 rows只代表 dynamic/extra tools，不能推出 core collaboration tool absent；
- `tool_calls` 只记录发生过的调用，不能代表完整 available tool surface；
- 没有找到可直接绑定五 child 的完整 `tool_namespaces_info` request-level persisted snapshot，因此该路线不能形成 PASS。

Managed Investigator 曾收到一次 same-child probe。它因 developer instruction 返回 `BEHAVIOR_BLOCKED`，实际没有调用 `spawn_agent`，也没有 descendant identity。N1 contract 不接受行为层拒绝作为 Host deny，因此该结果保持 UNKNOWN。

随后 formal campaign 创建 dedicated generic V2 probe parent，用于验证 Host V2 descendant materialization能力。

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
- effective session `multi_agent_version=v2`

Probe parent 实际调用：

```text
task_name = n1_grandchild_probe
agent_type = default
fork_turns = none
call_id = call_OfQ3XxMMzDydhASzamc3WJqh
```

Host 返回 successful canonical task address：

```text
/root/n1_depth_probe_parent/n1_grandchild_probe
```

随后真实 grandchild materialize：

- thread `01a02cb5-e19d-7721-8c80-87dacce99912`
- role `default`
- session `multi_agent_version=v2`

`state_5.sqlite.thread_spawn_edges` 有 OPEN edge：

```text
parent_thread_id = 01a02cb5-cdbb-7813-8215-77bc6a0a3390
child_thread_id = 01a02cb5-e19d-7721-8c80-87dacce99912
status = open
```

Probe 后 repository 仍 exact and clean。

Formal verdict：`N1 FAIL`。

Issue #91 conclusive entry：`HOST-N1-GRANDCHILD-002`，comment `5384129697`。

该 evidence 在当前 Host containment basis 下可复用。PR #98 没有改变 Host containment enforcement，因此当前 candidate 继续继承该 incompatibility verdict。禁止仅因 candidate SHA变化重跑相同 grandchild probe。

## 11. OpenAI Codex source 根因

优先 source basis：`openai/codex@rust-v0.149.0-alpha.4`，与 embedded `0.149.0-alpha.4.1` 同一 alpha 系列。

已确认：

1. `DEFAULT_AGENT_MAX_DEPTH = 1` 存在。
2. V1 `spawn_agent` 有显式 spawn-depth rejection。
3. V2 child collaboration exposure 依赖 effective V2/model metadata。
4. alpha.4 V2 `spawn_agent` path会计算 child depth，但没有 V1-style pre-materialization `exceeds_thread_spawn_depth_limit()` rejection。
5. 下层 `AgentControl::spawn_agent_internal()` 检查 execution capacity、residency 和 thread limits，然后可以 materialize child，没有补上 depth rejection。
6. Codex agent role override 是受限投影，不能假设 custom profile TOML 的任意 `[agents]` / `[features]` 字段都会成为 child effective Host config。
7. 对 OpenAI current `main` 的后续复核也没有发现 equivalent V2 pre-materialization depth guard。

当前 Host model metadata 曾观察：

- `gpt-5.6-luna`：`multi_agent_version=v1`
- `gpt-5.6-terra`：`multi_agent_version=v2`
- `gpt-5.6-sol`：`multi_agent_version=v2`

这些 source/model facts解释真实 Host FAIL，但最终 release verdict仍绑定 real Host evidence。

## 12. PR #97 实验分支，禁止误当当前方案

PR #97 `Fix V4 V2 grandchild containment` 已 CLOSED，未合并。

Branch：`fix/v4-n1-v2-containment-safe-lanes`。

最后观察 head：`86b288941237bb1a9b6ed4aab70f355f5d9f6ab5`。

该实验探索过把五个 managed child 全部固定到 Luna Max，以利用当时 Host Luna `multi_agent_version=v1` 关闭 V2 child collaboration surface。实验过程中也发现：

- `scripts/doctor.py` 旧逻辑仍把 `[agents].enabled=false` 与 `[features].multi_agent_v2=false` 当 profile correctness 条件；
- `runtime-evidence.py` 的 Main Sol judgment coverage 曾错误依赖 managed Solver route，managed Solver 降到 Luna 会污染 Main capability reference；
- `docs/v4/orchestrate.json`、routing evals 和若干 tests 与新 route发生 authority drift；
- 初始 PR scope 同时带入较多无关 README / architecture 精简，review 面积过大；
- 全 Luna 会牺牲 Investigator / Solver / Advisor 原来的 Terra/Sol managed specialization，需要正式产品能力决策。

该分支曾进行部分修复和测试同步，但它没有成为 release authority。随后正式方向收敛到 PR #98 的 fail-closed Host readiness gate。

新会话不得默认恢复 PR #97、不得把全 Luna 当已批准架构、不得从其 head 继续 formal release work。若未来要重新评估 model-based containment，必须先做新的架构决策，并重新验证当前 Host contract、能力 tradeoff 和 N1 machine acceptance。

## 13. PR #98 fail-closed remediation

PR #98 `Fail closed on unverified V4 child containment` 已合并，形成当前 formal candidate `3bc593fb...`。

核心目标：消除错误 execution-readiness 判定，同时保留 N1 FAIL，不伪造 Host 已修复。

`scripts/host_capabilities.py` 要求 Host evidence 显式提供：

```text
managed_child_containment = verified | failed | unknown
```

语义：

- `verified`：外部 exact-candidate Host campaign 已按 N1 机器合同证明 containment；
- `failed`：Host campaign 已证明 descendant materialization 或其它硬失败；
- `unknown`：证据不足。

只有 `verified` 可以让 `execution_ready=true`。

`failed` 和 `unknown` 都 fail closed，并把 `managed_child_containment` 加入 missing requirements。

Missing 或 malformed containment evidence 被拒绝。Normalizer 会重新计算 readiness，调用方不能通过自带 `execution_ready=true` 绕过 containment gate。

Doctor 对 `failed` containment evidence 报 Host integration FAIL。

回归覆盖：

- verified containment 才 ready；
- failed containment阻断；
- unknown containment阻断；
- missing containment拒绝；
- invalid containment拒绝；
- Doctor failed containment path。

PR #98 首轮 workflow `32617364817` 曾暴露 14 个旧 Host evidence fixture 缺新字段。修复原则保持 fail closed，没有给旧 fixture 隐式默认 `verified`。相关 tests 显式补充 `managed_child_containment="verified"` 后重新跑完整 matrix。

PR #98 最终合并后 exact-head workflow `32617888028` 全绿。

该修复明确未改变：

- Orchestrate production spawn behavior；
- 五个 fixed profile routes；
- WriterLease；
- WorkGraph；
- Hook ownership；
- N1 machine contract；
- Host containment enforcement。

## 14. 当前 release gate 状态

当前正式结论：

- repository candidate：`3bc593fbae535b1d31d28f3f46dc59677ef87c52`
- repository exact-head CI：PASS via `32617888028`
- N0：REUSE prior conclusive routing/model/effort evidence，PR #98 未改变该执行路径
- N1：FAIL，REUSE conclusive Host incompatibility evidence `HOST-N1-GRANDCHILD-002`
- N2：NOT_RUN / blocked by N1
- N3：NOT_RUN / blocked by N1
- N4：NOT_RUN / blocked by N1
- N5：NOT_RUN / blocked by N1
- N6：NOT_RUN / blocked by N1
- N7：NOT_RUN / blocked by N1
- N8：NOT_RUN / blocked by N1
- Final Review：NOT_RUN
- external release evidence：PENDING
- current installed-product binding for `3bc593fb...`：尚未重新建立
- human two-Skill App observation：release gate仍未完成
- publication：BLOCKED

## 15. N2-N8 机器合同，N1 PASS 后才可执行

N2：canonical task address 与 authoritative Host thread identity 绑定，并绑定 intended ExecutionBinding/profile。普通 V2 path可用 native task name，不能猜 `agent_id`。

N3：deliberate Host admission rejection。必须证明 no successful spawn result、no Started activity、no Host thread identity、no durable child identity、no resident runtime materialization。歧义保持 UNKNOWN。

N4：RUNNING Steer 使用 `followup_task`。必须证明 original child 消费 guidance，无 replacement child。Correction/Continue 复用 same child/ExecutionBinding，不能为了控制动作新开 fresh attempt。

N5：interrupt result本身不能释放 WriterLease。必须看到 current-generation Host settlement。

N6：UNKNOWN / unsettled writer 阻止 replacement 和 Main conflicting takeover。只有 settlement后可 transfer。

N7：rollout reconciliation必须绑定 lifecycle call id、child identity 和 result，且满足 privacy allowlist。不得泄露 assignment body、reasoning 或无关私密内容。

N8：fresh exact-candidate Advisor review，同时要求 Host-observed effective permission满足 strict read-only。Configured sandbox/requested permission不能替代 Host truth。Artifact mutation会使旧 verdict失效。

## 16. WriterLease 与 UNKNOWN

当前 Agent 共享 filesystem/cwd，canonical mutable workspace保持一个 managed writer。

WriterLease blocking states：

```text
RESERVED
HELD
REVOKING
UNKNOWN
```

`interrupt_agent` success 不能释放 WriterLease。必须等 current-generation authoritative Host settlement。

Materialization、identity、lifecycle 或 writer settlement有歧义时进入 UNKNOWN。UNKNOWN 不能授权 replacement execution、writer transfer、Main conflicting takeover 或 final acceptance。

## 17. 当前 technical debt

`docs/v4/technical-debt.json` 中的非 blocking 项继续保留，包括 Doctor Host evidence UX、experiment-plane consolidation、state path TOCTOU hardening等。

N1 FAIL 是 release blocker，不能降级成普通 technical debt，也不能通过 README 声明绕开。

## 18. 关键 PR 历史

- PR #88：加强 N2 identity、N3 admission/materialization、N4 RUNNING Steer machine contract。
- PR #89：补齐 N4 human release documentation，明确 tool acceptance alone不足以证明 guidance consumed。
- PR #90：建立 live V4 handoff、README_AI 入口，处理 CI self-update loop 和 trailing newline regression。
- PR #92：扩展 takeover background，建立 Issue #91 Real Host Test Ledger，形成 candidate `630a36e...`。
- PR #96：修 exact managed selector 与 canonical Main-facing spawn facade，形成 candidate `2f2e532a...`。
- PR #97：全 Luna containment-safe lane 实验，CLOSED / 未合并，禁止当 current authority。
- PR #98：fail closed on unverified child containment，已合并，形成 current candidate `3bc593fb...`。

## 19. 禁止错误推理

- profile read-only request不能推出 effective Host read-only；
- `max_depth=1` 不能推出 V2 descendant containment；
- `[agents].enabled=false` 不能推出 spawned child collaboration tool已移除；
- `[features].multi_agent_v2=false` 不能推出 spawned child effective session已降级；
- developer instruction拒绝不能推出 Host authoritative deny；
- child 自述不能证明 model/effort/permission；
- V1 `fork_context=false` 不能证明 V2 `fork_turns=none`；
- 找不到 resident runtime不能推出 durable identity未 materialize；
- interrupt success不能推出 WriterLease可释放；
- `followup_task` accepted不能推出 original child已消费 guidance；
- repository CI PASS不能推出 N0-N8 PASS；
- prior installed package不能推出 current candidate installed identity；
- 新聊天不能作为 Host rerun理由；
- generic Host Agent不能算 managed profile；
- semantic role name不能替代 exact `agent_type`；
- freehand task name不能替代 canonical `sd_<unit>_a<attempt>`；
- Skill文字要求不能替代 deterministic preparation boundary；
- `thread_dynamic_tools` 0 rows不能推出 core collaboration tool absent；
- 找不到 persisted `tool_namespaces_info`不能推出 tool absent；
- candidate SHA变化本身不能使 conclusive N1 FAIL失效；
- UNKNOWN不能当 PASS；
- N1 FAIL时禁止继续 N2-N8。

## 20. Repository 修改纪律

每次 repository content change：

1. 读本 handoff、当前 Git/PR、相关 machine contract和 #91；
2. 从 exact current base建立短生命周期普通 branch；
3. 做最小 root-cause change；
4. 同步更新本 handoff；
5. 做对抗性 review；
6. 跑 targeted tests与完整 required matrix；
7. blocking finding修完后重新跑 exact-head CI；
8. 全绿才 merge；
9. merge后重新冻结 candidate commit/tree；
10. post-merge exact-head CI；
11. Real Host action逐动作写 #91。

CI、review、Host evidence和 PR metadata属于 external evidence。不要为了记录一条 PASS 单独制造 candidate mutation。

代码简化也要保持 scope to changed code。不要在 containment修复中混入无关 README、architecture 或 runtime refactor。行为保持、错误行为保持和现有测试保护优先。

## 21. 新会话 takeover checkpoint

新会话开始时按以下顺序恢复状态：

1. 打开 `docs/v4/development-handoff.md` 当前正式版本。
2. 获取 PR #81 current head/tree/status，确认是否仍为 `3bc593fb...` / `eadcf99c...`。
3. 检查 PR #81 body中的 current release state与 required next sequence。
4. 检查 Issue #91 最新 ledger entries。任何 Real Host action前都先做 `REUSE | RERUN | NOT_RUN`。
5. 检查当前 exact-head workflow。若 formal head已经移动，先确认变化内容与 gates受影响范围。
6. 需要修改 repository时，从 current formal candidate建新短 branch，不从 PR #97 branch继续。
7. 不要重跑 N1 generic grandchild probe，除非存在 containment enforcement直接 changed basis。
8. 不要进入 N2，直到 N1有新的 formal PASS。

## 22. 当前允许的下一步

当前唯一合理 release 路线：

1. 保持 PR #81 Draft，publication BLOCKED。
2. 需要 installed-product验证时，把本机 Plugin/package重新绑定到 current candidate `3bc593fb...`，因为 `scripts/host_capabilities.py` shipped bytes已变。
3. 不重跑同一 Host的 N1 grandchild probe。PR #98只改变 readiness语义，没有改变 containment enforcement。
4. 持续关注能够改变 N1 basis的真实机制，例如 Host/runtime提供可证明的 child collaboration tool absence、authoritative pre-materialization deny、V2 depth enforcement，或经过正式批准并仍满足 machine contract的架构变化。
5. 出现 material changed basis后，先更新 spec/machine contract如果需要，再从 exact current candidate实施最小适配。
6. 通过 repository validation和 installed binding后，Issue #91 preflight决定 N1 `RERUN`。
7. N1 PASS后才顺序执行 N2-N8。
8. N0-N8全部 PASS后，运行 fresh exact-candidate Advisor Final Review，并取得 Host-observed effective read-only evidence。
9. 再完成 candidate-bound external release evidence、current installed-product checks和 human two-Skill App observation。
10. 所有 gates通过后，PR #81才可以离开 Draft、merge、tag `v4.0.0`、验证 Marketplace解析到 exact tag并发布。

## 23. Modification Log

### H001-H006

建立 live handoff、repository validation纪律、merge-state修正、CI self-update loop修复、README trailing newline修复、完整 takeover background和 Issue #91 Host ledger。

### H007 2026-08-23 08:02 +08:00

旧 candidate formal N0 Reader发现 generic selector drift，触发 PR #96。

### H008 2026-08-23 08:15 +08:00

继续发现 freehand `task_name`绕过 canonical ExecutionBinding。PR #96扩展为 Main-facing `prepare_managed_spawn()`，从 persisted state生成并 exact-validate Host spawn payload。

### H009 2026-08-23 12:05 +08:00

Prior candidate `2f2e532a...` 完成五 profile N0并整体 PASS。N1 调查发现 Luna metadata V1，Terra/Sol metadata V2。Managed Investigator行为层拒绝保持 UNKNOWN。Dedicated generic V2 probe parent真实 materialize depth-2 grandchild，Issue #91记录 `HOST-N1-GRANDCHILD-002` comment `5384129697`，N1正式 FAIL，N2-N8停止。

### H010 2026-08-23 12:05 +08:00

建立 `fix/v4-n1-host-containment-gate`。`scripts/host_capabilities.py`引入 `managed_child_containment = verified | failed | unknown`三态，只有 verified可 execution ready。Missing、failed、unknown全部 fail closed。

### H011 2026-08-23 12:15 +08:00

PR #98首轮 CI 暴露旧 Host evidence fixtures缺新字段。保持 fail-closed设计，显式修正代表已验证 Host的 fixtures，没有给 normalizer增加隐式 verified默认。

### H012 2026-08-23 13:31 +08:00

PR #98 已完成修复、完整 matrix验证并合并到 `v4/rc5-native-core`。当前 formal candidate 为 `3bc593fbae535b1d31d28f3f46dc59677ef87c52`，tree `eadcf99c3c339428256412319da005f482df8935`，post-merge exact-head workflow `32617888028` 全绿。

PR #98 只改变 Host capability readiness / diagnosis语义和对应 tests/manifest，没有修改 managed profiles、canonical spawn runtime或 Host containment enforcement。因此 prior N0 routing/model/effort PASS继续可 REUSE，N1 conclusive FAIL也继续可 REUSE。N2-N8与 Final Review保持 NOT_RUN。

同时确认 PR #97 `Fix V4 V2 grandchild containment` 已 CLOSED / 未合并，branch `fix/v4-n1-v2-containment-safe-lanes` 的全 Luna实验不属于 current release authority。新会话不得从 PR #97继续 formal开发，也不得因新会话或 candidate SHA变化重跑 N1。

本次 handoff 刷新工作放在短 branch `docs/v4-handoff-20260823-1331`，只用于把跨会话接手状态同步到仓库。该 handoff 文档变更本身不改变任何 release gate verdict。
