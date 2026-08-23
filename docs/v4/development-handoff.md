# V4 实时开发交接记录

初始记录时间：2026-08-23 05:58 +08:00。

最新记录时间：2026-08-23 08:15 +08:00。

状态：持续维护。正式 release candidate 仍为 `v4/rc5-native-core@630a36e846a8a3de9bc6396b2e1a6de3cb995ebd`。Real Host campaign 在 N0 Reader 首次正式 probe 中发现 release-blocking managed spawn drift，PR #96 正在做根因修复。PR #81 保持 Draft，publication BLOCKED。

此文件是 V4 的仓库内接手入口。新会话、新维护者或新 Codex session 接手前，先读本文件，再核 GitHub 当前 branch、PR、CI、Issue #91 Real Host Test Ledger 和真实 Host evidence。机器合同优先于本文件，本文件负责连续背景、当前状态、风险、验证纪律和下一步。

## 1. 项目目标

仓库：`R-jed/subagents-dispatch`。

产品版本：`4.0.0` release candidate。

项目在 OpenAI Codex Native Subagents 之上提供工程编排策略。Main 决定是否分工、怎样拆 WorkUnit、选哪个固定 managed profile、何时 dispatch、怎样验证 artifact、是否 accept、是否执行不可逆外部动作以及最终怎样回复用户。

项目重点解决：

- 有价值时才 delegation，允许 0 child；
- WorkUnit 责任、依赖、readiness 和 acceptance 可追踪；
- canonical mutable workspace 保持安全 writer coordination；
- Host lifecycle/identity/capacity/permission 与 Plugin 产品状态分层；
- materialization、settlement、writer ownership 不清楚时 fail closed；
- Steer、Correction、Continue 复用同一 child/ExecutionBinding；
- Host completion 与 Main acceptance 分离；
- repository、real Host、installed product、Final Review、人工 App surface 分开验证。

V4 目标是 Native Core。优先复用 Host 原生事实，Plugin 只保留自己必须拥有的产品状态。

## 2. Hookless Native Core 边界

旧版本出现过 Hook/Guard lifecycle interception、PendingControl、capacity token、固定 fanout、固定 retry/followup budget 等机制。历史记录只保存在 `docs/history/` 做 provenance。

当前 V4：

- Codex Host 拥有 child materialization、native lifecycle、underlying Host thread identity、actual admission/capacity、effective permission、effective child collaboration surface；
- Main 拥有用户意图、分解、fixed-profile selection、dispatch judgment、artifact verification、WorkUnit acceptance、不可逆外部动作、final response；
- WorkGraph/WorkUnit 拥有责任、依赖、readiness、acceptance truth；
- ExecutionBinding 表示一次具体 managed attempt；
- WriterLease 协调 canonical workspace managed writer；
- scheduler/helper 只做约束投影，不建立私有 Host occupancy truth；
- UNKNOWN 永远 fail closed；
- Hook 不在 V4 correctness path。

禁止恢复第二套 lifecycle control plane、daemon scheduler、固定 fanout/retry/followup budget、平行 Host truth ledger 或自动 worktree runtime。

## 3. 当前 Git 与 release 状态

主 release branch：`v4/rc5-native-core`。

主 release PR：#81 `RC5 Native Core: remove Hook control plane`，OPEN、Draft。

PR #96 开始前的正式 candidate：

- commit `630a36e846a8a3de9bc6396b2e1a6de3cb995ebd`
- tree `c5b425e39c64981290d514fe68d62853efbbac08`
- PR #81 synthetic merge commit `5979f98548d39f3ea12cb1b14d4c22d234c96448`
- synthetic merge tree `c5b425e39c64981290d514fe68d62853efbbac08`
- post-merge exact-head CI `32604117828`
- Ubuntu 3.11 PASS
- Ubuntu 3.12 PASS
- macOS 3.11 PASS
- Windows 3.11 PASS
- aggregate `policy-tests` PASS
- generated package integrity PASS
- Ruff PASS
- pinned official OpenAI Plugin validator PASS where applicable
- managed Agent lifecycle PASS

当前修复 branch：`fix/v4-n0-exact-managed-agent-type`。

当前修复 PR：#96 `Fix V4 exact managed agent selector drift`，base 为 `630a36e...`，Draft。

PR #96 合并前，`630a36e...` 仍是正式 release candidate。PR #96 修改 shipped package bytes，合并后必须形成新 candidate、新 package binding 和 fresh Host session。旧 candidate-bound N0 verdict 只能保留为历史 evidence。

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

Profile TOML 里的 `sandbox_mode`、`agents.enabled=false`、`features.multi_agent_v2=false` 和禁止继续创建 subagents 的 developer instruction 都只是 requested posture。N1/N8 必须用真实 Host evidence 证明 containment/effective permission。

`max_depth=1` 也是 product policy，不能替代 V2 descendant containment proof。

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
9. README/普通产品文档；
10. `docs/history/` 历史 provenance。

## 7. 核心目录职责

- `.codex-plugin/plugin.json`：Plugin identity/version。
- `.codex-plugin/package-integrity.json`：shipped payload SHA256 manifest。
- `.agents/plugins/marketplace.json`：Marketplace identity/source。
- `skills/orchestrate`、`skills/doctor`：唯一公开 Skills。
- `agent-profiles/`：五个固定 managed profile。
- `contracts/policy.json`：profile、delegation ceiling、review policy。
- `contracts/routing.md`：delegation value/Main dispatch judgment。
- `contracts/responsibility-packet.md`：child responsibility serialization。
- `contracts/interaction.md`：控制操作。
- `contracts/recovery.md`：ExecutionBinding recovery。
- `contracts/final-review.md`：exact-candidate Final Review。
- `scripts/orchestrate_v4.py`：Main-facing V4 production facade。
- `scripts/managed_execution_v4.py`：exact managed spawn contract。
- `scripts/execution_lifecycle_v4.py` / `_core.py`：ExecutionBinding lifecycle preparation/reconciliation。
- `scripts/work_graph_v4.py`：WorkGraph/WorkUnit/dependencies/readiness/acceptance。
- `scripts/scheduler_v4.py`：constraint projection。
- `scripts/writer_lease_v4.py`：single canonical writer coordination。
- `scripts/host_capabilities.py`：Host capability normalization。
- `scripts/inspect-agent-runtime.py` / `inspect-collaboration-runtime.py`：allowlisted Host evidence extraction。
- `scripts/doctor.py`：installed-product diagnosis。
- `scripts/package_integrity.py`：package identity。
- `docs/v4/host-smoke.json`：N0-N8 machine gate。
- `docs/v4/development-handoff.md`：本文件。

## 8. WorkUnit、ExecutionBinding、acceptance

Host `COMPLETED` 只产生 candidate result，WorkUnit 到 `RESULT_READY`。Main 检查实际 artifact/evidence 后才 accept。Dependencies 只从 `ACCEPTED` 解锁。

Fresh retry 需要 prior attempt safely settled 加 changed execution basis。没有固定 retry count。

Focused correction 必须有新的 correction basis。`followup_count` 只做诊断。

CONTINUE 复用 interrupted ExecutionBinding。

RUNNING Steer 当前使用 V2 `followup_task`，保持原 ExecutionBinding。

每个 fresh managed attempt 的 canonical task name：

```text
sd_<case-folded-unit-id>_a<attempt-no>
```

该名字必须来自 ExecutionBinding/runtime generation，不能由 Main 自由手写。

## 9. WriterLease 与 UNKNOWN

当前 Agent 共享 filesystem/cwd，因此 canonical mutable workspace 保持一个 managed writer。

WriterLease blocking states：`RESERVED`、`HELD`、`REVOKING`、`UNKNOWN`。

`interrupt_agent` success 不能释放 WriterLease。必须等 current-generation authoritative Host settlement。

materialization、identity、lifecycle、writer settlement 有歧义时进入 UNKNOWN。UNKNOWN 不能授权 replacement、writer transfer、Main takeover、final acceptance。

## 10. OpenAI Codex MultiAgent V2 背景

已复核 official `openai/codex` upstream commit `8e649e3afa5cdddfb09a1b85a090b94775045d9b`。

V2 control family包括 `spawn_agent`、`send_message`、`followup_task`、`wait_agent`、`list_agents`、`interrupt_agent`。

V2 `spawn_agent` 使用 `fork_turns`。managed fresh spawn 要求 `fork_turns="none"`。历史 V1 `fork_context=false` 不能替代这条 release proof。

官方 V2 source 支持 `spawn_agent.agent_type`，Host 可以通过 tool options 控制是否 expose。当前 formal Host probe 已实际看到 `agent_type` 字段，所以该次失败不能归因为字段完全不可用。

`send_message` 当前 QueueOnly；`followup_task` TriggerTurn。因此 N4 RUNNING Steer 继续使用 `followup_task`，并需要 same-child post-guidance evidence 证明原 child 实际消费 guidance。

Canonical task address 与 underlying Host thread identity 是两层事实。N2 release evidence 要从 authoritative Host activity/lifecycle data 把 task address、Host thread identity、ExecutionBinding/profile 对上，禁止猜 `agent_id`。

## 11. Real Host Test Ledger

Issue #91 `V4 Real Host Test Ledger` 是 real Host operational ledger。它属于 GitHub metadata，不改变 candidate。

每一个真实 Host action 都必须单独记录，至少包括：candidate/local binding、package identity、Doctor、fresh session、Host build/version、V2 surface、每次 spawn、每个 N0 profile、grandchild probe、capacity rejection、Steer/Correction/Continue、Interrupt、WriterLease takeover、rollout inspection、Advisor permission probe、FAIL/UNKNOWN、人工观察、retry。

每个 action 前必须先查 #91，做：

- `REUSE`：旧 conclusive evidence 仍有效，禁止重复 Host action；
- `RERUN`：有明确 invalidation/changed basis 才能重跑；
- `NOT_RUN`：prerequisite 未满足。

新聊天、新维护者、新 Codex conversation 本身都不是 rerun 理由。

Tracked `docs/v4/host-smoke.json` 必须保持 `status=PENDING`、`results={}`。真实 Host 结果不能回填 tracked JSON，否则会改变 candidate。

## 12. 历史 Host evidence

### build 6892

历史 run `01a02ad1-dbb9-7cb0-990c-188c76f48848` 使用 MultiAgent V1，raw spawn 为 `fork_context=false`。历史 N0 结论 UNKNOWN。

### build 6962 capability context

曾观察 ChatGPT App build 6962、embedded Codex `0.149.0-alpha.4.1`、Main `multi_agent_version=v2` 和 V2 control family。它只能作为 capability context，不能替代 exact-candidate formal N0。

### 旧 exact install

候选 `d565af4d1274c07451a803b2ee831ef4a5233883` 曾完成 exact Marketplace reinstall，50 files，missing 0、unexpected 0、hash mismatch 0，Doctor package/profile health OK。

到 `630a36e...` 前 shipped manifest blob 一直相同，因此 package-byte continuity 曾可 REUSE。PR #96 修改 shipped runtime/Skill bytes，合并后这条 continuity 不再覆盖新 candidate。

## 13. N0-N8 machine gate

Authority：`docs/v4/host-smoke.json`。

- N0：exact managed role/agent_type、model、effort、V2、`fork_turns=none`。
- N1：五 profile effective collaboration surface；grandchild attempt 只能 tool absent 或 authoritative Host deny，且无 descendant identity materialize。
- N2：canonical task address 与 authoritative Host thread identity 绑定，并绑定 ExecutionBinding/profile。
- N3：deliberate Host admission rejection；证明 no successful spawn result、Started activity、Host thread identity、durable identity、resident runtime materialize；歧义为 UNKNOWN。
- N4：RUNNING Steer via `followup_task`；原 child 消费 guidance；无 replacement；same-child Correction/Continue 不开 fresh attempt。
- N5：interrupt return 不释放 WriterLease；current-generation Host settlement 才 settle。
- N6：UNKNOWN/unsettled writer 阻止 replacement/Main takeover；settlement 后才 transfer。
- N7：rollout evidence 绑定 lifecycle call、child identity、result，并满足 privacy allowlist。
- N8：fresh exact-candidate Advisor review；Host-observed effective permission 满足 strict read-only；artifact mutation 使旧 verdict 失效。

N0 未 PASS 前禁止 N1。

## 14. 2026-08-23 formal Host environment binding

用户本机 repo：`/Users/qunqing/2026-Project-Agent/subagents-dispatch`。

最初本机 branch 名为 `v4/rc5-native-core`，但 HEAD 仍是旧 `d565af4d...`。GitHub compare 证明新 candidate ahead 4、behind 0，随后 `git merge --ff-only origin/v4/rc5-native-core` 安全快进。

快进后 repository evidence：

- HEAD `630a36e846a8a3de9bc6396b2e1a6de3cb995ebd`
- tree `c5b425e39c64981290d514fe68d62853efbbac08`
- working tree clean
- Python `3.14.6`
- package integrity `ok=true`
- Doctor Plugin package OK
- Doctor 5 managed profiles OK
- Legacy compatibility OK

Fresh Host session evidence：

- ChatGPT bundle `com.openai.codex`
- App version `26.818.41509`
- Host build `6962`
- embedded Codex `0.149.0-alpha.4.1`
- macOS `27.0`, build `26A5416b`, arm64
- root rollout `/Users/qunqing/.codex/sessions/2026/08/23/rollout-2026-08-23T07-46-10-01a02bde-1702-7580-b850-fb4d555c5ab5.jsonl`
- root session/thread id `01a02bde-1702-7580-b850-fb4d555c5ab5`
- cwd exact repo
- `turn_context.multi_agent_version=v2`

关键 #91 comments：

- exact local binding PASS `5383194153`
- fresh Host session PASS `5383217607`
- N0 preflight `5383218764`

## 15. Formal N0 Reader 首次 FAIL

同一 fresh root session 中执行一次 N0 Reader probe。Main 被要求 Orchestrate 只 delegate 一个 read-only Reader，读取 `README_AI.md` 第一条 Markdown heading，不写文件、不创建其他 child、不提前跑 N1。

Root rollout authoritative call：

```text
spawn_agent
call_id = call_DlAFzcAwvdfAKTX0k6BFkDyz
task_name = v4_n0_reader_probe
agent_type = codex_agent_team_reader
fork_turns = none
message_present = true
input_keys = [agent_type, fork_turns, message, task_name]
```

Expected machine contract：

```text
task_name = sd_<unit>_a<attempt>
agent_type = subagents_dispatch_reader
model = gpt-5.6-luna
effort = max
fork_turns = none
```

已确认：

- `fork_turns=none` PASS；
- exact `agent_type` FAIL；
- `task_name` 也绕过 canonical ExecutionBinding naming contract。

因此问题范围比“Reader selector 字符串选错”更大。真实 Host call 绕过了 deterministic managed spawn preparation path。

第一次证据解析辅助脚本发生本地 `TypeError: unhashable type: 'dict'`。它只影响读取，不允许因此重跑 Host。修正后继续读取同一 rollout，得到上述 conclusive call evidence。

正式 Reader FAIL 已记录 #91 comment `5383236842`。N0 整体 FAIL/BLOCKED。Worker、Investigator、Solver、Advisor、N1 均未开始。

## 16. PR #96 根因与最终修复方向

原 candidate 已有这些严格底层合同：

- `contracts/policy.json` 保存五个 exact `agent_type`；
- profile TOML 使用 exact names；
- `managed_execution_v4.expected_spawn_input_for_execution()` 生成 canonical `task_name + message + agent_type + fork_turns`；
- `execution_lifecycle_v4.build_managed_spawn_tool_input()` 从 persisted ExecutionBinding 生成 payload；
- `execution_lifecycle_v4.prepare_spawn()` 对实际 payload 做 exact equality validation。

原缺口位于 Main-facing product path：

1. `orchestrate_v4.FIXED_PROFILES` 漏掉 `agent_type` projection；
2. Skill 没有列出五个 literal selector；
3. 更关键的是，Orchestrate facade 没有提供一个唯一的 Main-facing canonical spawn preparation API，所以 Main 仍可能自由手写 `task_name`、`agent_type`、`fork_turns`、message transport。

Formal Host call 中同时出现 `codex_agent_team_reader` 和 `v4_n0_reader_probe`，证实第三点必须修。

PR #96 当前最终设计：

- `select_profile()` 返回 policy-owned exact `agent_type`；
- Skill 明列五个 exact selector；
- 新增 `orchestrate_v4.prepare_managed_spawn(thread_id, orchestration_id, execution_id, ...)`；
- 该 facade 不接受 caller-supplied `tool_input`；
- 它先确认 current orchestration/current ExecutionBinding；
- 调 `lifecycle.build_managed_spawn_tool_input()` 从 persisted state 生成 canonical payload；
- 再调 `lifecycle.prepare_spawn()` 做 exact validation；
- Main 只能把返回的 `tool_input` 原样交给 Host `spawn_agent`；
- Skill 明确禁止在 Host call site 手写/覆盖 `task_name`、`message`、`agent_type`、`fork_turns`；
- exact managed agent unavailable/omitted/rejected 时停止 delegation，禁止 generic fallback。

对应 regression test 直接证明 `prepare_managed_spawn()` 返回：

```text
task_name = sd_u1_a1
agent_type = subagents_dispatch_reader
fork_turns = none
message = non-empty canonical responsibility packet
```

同时验证它是 transient preparation，不改 state，并拒绝错误 orchestration target。

这比只在文档中要求 exact selector 更强，因为 Main-facing API 本身不允许 caller 注入 freehand spawn transport。

## 17. PR #96 validation 历史

首轮 workflow `32606666309` 在 manifest 尚未刷新时按预期停在 generated package-integrity check，用于取得第一版 payload hash。

第一次 selector-only 修复后的 exact-head workflow `32606876564`：

- Ubuntu 3.11 full PASS；
- Ubuntu 3.12 full PASS；
- macOS 3.11 full PASS；
- Windows 3.11 tests/lifecycle PASS；
- Ubuntu 3.11 full pytest `528 passed`；
- official validator、Ruff、package integrity、managed profile lifecycle PASS。

随后 adversarial review 发现真实 Host `task_name` 也漂移，因此该 head 被主动视为不足，不合并。

新增 `prepare_managed_spawn()` 和 Skill canonical facade 规则后，workflow `32607144507` 按预期因 manifest 仍是前一版 hash 在 package-integrity step 失败。生成器给出当前新 hash：

- `scripts/orchestrate_v4.py` `e641fd9562f8c13c8b1e4c0c131cc7225c5269ecd2443a2aa09fba0bdd776a01`
- `skills/orchestrate/SKILL.md` `224a2e7629b10a395ee20d302ed4a6f0cd2de12f11e086428bc3e22d234c2b63`

manifest 已按生成器结果刷新。必须在本 handoff sync 后跑新的 exact-head full matrix。旧 workflow 不能替代最终验证。

## 18. Package/install/fresh-session 边界

Plugin version仍为 `4.0.0`。

PR #96 修改 shipped `scripts/orchestrate_v4.py` 和 `skills/orchestrate/SKILL.md`，所以合并后：

- 旧 package-byte continuity 失效；
- 用户本机必须 fast-forward 到新 formal candidate；
- 必须重新验证/安装 exact candidate package 和 managed profiles；
- 必须完全 fresh ChatGPT/Codex session；
- 重新记录 Host build/runtime/session identity；
- 然后 #91 preflight 才能把旧 Reader FAIL 标为 superseded，并因 changed basis 重跑 Reader。

不能在旧 `630a36e...` session 中测试 PR #96 effectiveness。

## 19. 当前 technical debt

`docs/v4/technical-debt.json` 中的非 blocking 项继续保留，例如 Doctor Host evidence UX、experiment-plane consolidation、state path TOCTOU hardening。

这些 debt 不放松 N0-N8 gate。

## 20. 关键 PR 历史

- PR #88：harden N2 identity、N3 admission/materialization、N4 RUNNING Steer machine contract。
- PR #89：补齐 N4 human release documentation，明确 tool acceptance alone insufficient。
- PR #90：建立 live V4 handoff、README_AI 入口，解决 CI/self-update loop 和 trailing newline regression。
- PR #92：扩展 complete takeover background，建立 Issue #91 Real Host Test Ledger，合并后 candidate `630a36e...`。
- PR #96：由 formal N0 Reader FAIL 触发，当前根因修复 branch。

## 21. 禁止错误推理

- profile read-only 配置不能推出 effective Host read-only；
- `max_depth=1` 不能推出 V2 descendant containment；
- child 自述不能证明 model/effort/permission；
- V1 `fork_context=false` 不能证明 V2 `fork_turns=none`；
- resident runtime 不可见不能推出 durable identity 未 materialize；
- interrupt success 不能推出 WriterLease 可释放；
- `followup_task` accepted 不能推出 guidance 已消费；
- repository CI PASS 不能推出 N0-N8 PASS；
- 旧 exact install 不能推出当前 package/session binding；
- 新聊天不能作为 Host rerun 理由；
- generic Host Reader/Worker 不能算 managed profile；
- semantic role name 不能替代 exact `agent_type`；
- freehand task name 不能替代 canonical `sd_<unit>_a<attempt>`；
- Skill文字要求不能替代产品级 deterministic preparation boundary；
- UNKNOWN 不能当 PASS。

## 22. Repository 修改纪律

每次 repository content change：

1. 读本 handoff、当前 Git/PR、相关 machine contract、#91；
2. 从 exact base 建短 branch；
3. 做最小 root-cause change；
4. 同步更新本 handoff；
5. 对抗性 review；
6. targeted tests + full required matrix；
7. blocking finding 修完后重新跑 exact-head CI；
8. 全绿才 merge；
9. merge 后重新冻结 candidate commit/tree；
10. post-merge exact-head CI；
11. Real Host action 逐动作写 #91。

CI、review、Host evidence、PR metadata 属于 external evidence。禁止只为了记录 PASS 再改 candidate。

## 23. 当前下一步

唯一允许路径：

1. 本 handoff sync 后等待 PR #96 新 exact-head full matrix；
2. 检查 package integrity、official validator、Ruff、full pytest、managed Agent lifecycle、四平台 aggregate 全 PASS；
3. 再做一次 PR #96 adversarial review，重点确认 Main-facing canonical spawn facade 无旁路、无新增 lifecycle authority、无 WriterLease/WorkGraph 回归；
4. 无 blocking finding 后 merge PR #96 到 `v4/rc5-native-core`；
5. 冻结新的 formal candidate commit/tree，更新 PR #81 metadata；
6. 跑 post-merge exact-head repository matrix；
7. 用户本机 fast-forward 到新 candidate；
8. 因 package bytes 已改变，重新做 exact installed package/profile binding；
9. 创建完全 fresh ChatGPT/Codex session并记录环境 identity；
10. #91 preflight 确认 changed basis 后只重跑 N0 Reader；
11. Reader PASS 后才继续其余 N0 profiles；
12. N0 整体 PASS 后才进入 N1；
13. N1-N8、fresh Final Review、external release evidence、installed-product gate、human two-Skill App observation 全 PASS 前，PR #81 保持 Draft，publication BLOCKED。

当前禁止：在旧 session 重跑 Reader、提前跑 Worker、提前跑 N1、把 `codex_agent_team_reader` 当 managed Reader、把 selector-only CI 当最终修复验证。

## 24. Modification Log

### H001-H006

H001 建立 live handoff。H002 记录首轮 validation。H003 修复 merge-state stale instruction。H004 关闭 CI 写回导致 candidate 自更新循环。H005 修复 README trailing newline regression。H006 通过 PR #92 补全 takeover background 并建立 #91 Host ledger。

### H007 2026-08-23 08:02 +08:00

记录 formal N0 Reader FAIL。Host build 6962 / embedded Codex `0.149.0-alpha.4.1` / V2 root session `01a02bde-1702-7580-b850-fb4d555c5ab5` 中，实际 `spawn_agent` 使用 `agent_type="codex_agent_team_reader"`、`fork_turns="none"`。机器合同要求 `subagents_dispatch_reader`。formal FAIL #91 comment `5383236842`。建立 PR #96，先修 exact selector projection 和 Skill literal selector。

### H008 2026-08-23 08:15 +08:00

对抗性 review 继续检查真实 Host call，发现 `task_name="v4_n0_reader_probe"` 同样绕过 canonical `sd_<unit>_a<attempt>`。这证明 selector-only 修复不足，Main 实际绕过了 deterministic managed spawn preparation path。

基于现有 lifecycle contract 实现更完整的最小修复：新增 Main-facing `prepare_managed_spawn()`，只接收 orchestration/execution identity，不接收 caller-supplied spawn payload；由 persisted ExecutionBinding 自动构建、严格校验 `task_name/message/agent_type/fork_turns`，Skill 要求 Host call 使用该返回值原样执行，禁止手写/覆盖 transport 字段。

新增 regression test 锁定 canonical task name、exact managed selector、fresh-context fork、responsibility packet 和 wrong-orchestration fail closed。再次刷新 package manifest。由于 production/Skill bytes 再次变化，前一轮 CI 自动失效，必须跑新的 exact-head full matrix。
