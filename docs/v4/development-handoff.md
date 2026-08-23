# V4 实时开发交接记录

初始记录时间：2026-08-23 05:58 +08:00。

最新记录时间：2026-08-23 08:02 +08:00。

状态：持续维护。V4 repository candidate 已完成确定性验证，Real Host campaign 在 N0 Reader 首次正式 probe 中发现 release-blocking selector drift，当前由 PR #96 修复。PR #81 保持 Draft，publication 继续 BLOCKED。

此文件是 `subagents-dispatch` V4 的仓库内接手入口。新会话、新维护者或新的 Codex session 接手前，应先读本文件，再核 GitHub 当前 branch、PR、CI、Issue #91 Real Host Test Ledger 和真实 Host evidence。本文保存项目背景、关键决策、当前 release 状态、已验证事实和操作纪律。机器合同和真实 Host evidence 仍由各自 authority 文件与外部 ledger 负责。

## 1. 项目目标

仓库：`R-jed/subagents-dispatch`。

当前产品版本：`4.0.0` release candidate。

产品目标是在 OpenAI Codex Native Subagents 之上提供一层工程编排策略。Main 在分工有价值时，把读取、调查、实现、求解和复核职责交给固定 managed Agent，同时继续掌握用户意图、分解、profile 选择、dispatch 判断、artifact 验证、WorkUnit acceptance、不可逆外部动作和最终回复。

项目重点解决这些问题：

- 哪些任务值得 delegated execution，哪些任务应保持 0 child；
- 怎样把工作拆成稳定、可验收、可追踪、有依赖关系的 WorkUnit；
- 怎样避免多个可写 child 在同一个 canonical mutable workspace 互相踩文件；
- 怎样把 Codex Host lifecycle、identity、capacity、permission、collaboration surface 和 Plugin 自己的产品状态分开；
- Host materialization、settlement 或 writer ownership 不清楚时怎样 fail closed；
- 怎样对同一个 child 做 Steer、Correction、Continue，同时避免无依据 replacement；
- Host `COMPLETED` 后怎样保留 Main 的最终 acceptance authority；
- release 时怎样分别验证 repository、real Host、installed product、Final Review 和人工 App surface。

V4 追求 Native Core：尽量依赖 Codex Host 的原生事实，Plugin 只维护产品必须拥有的责任、接受、执行绑定和 writer coordination 状态。

## 2. 为什么是 Hookless Native Core

旧版本曾有更重的 lifecycle interception、Hook/Guard、PendingControl、capacity token、固定 fanout、固定 retry/followup budget 等设计。历史材料保留在 `docs/history/` 供 provenance 使用。

V4 的核心边界：Codex Host 已拥有 child materialization、native lifecycle、underlying thread identity、实际 admission/capacity、effective permission 和 effective child collaboration surface。Plugin 再复制同类 truth 会制造双事实源、竞态和错误授权。

因此 V4 当前采用：

- Host 保存 Host 原生事实；
- Main 保存产品判断和用户目标；
- WorkGraph / WorkUnit 保存责任、依赖、readiness 和 acceptance truth；
- ExecutionBinding 表示一次具体 managed attempt；
- WriterLease 只协调 canonical workspace 的 managed writer；
- UNKNOWN 永远 fail closed；
- scheduler/helper 只做约束投影，不创建私有 Host occupancy truth；
- Hook 不进入 V4 correctness path。

Hook 未来最多用于 observability、diagnostics 或 defense in depth。它不能承担 spawn authorization、lifecycle settlement、WriterLease release、retry authorization 或 WorkUnit acceptance。

## 3. 当前 Git 和 release 状态

正式 release branch：`v4/rc5-native-core`。

主发布 PR：#81 `RC5 Native Core: remove Hook control plane`。

截至 PR #96 开始前，正式候选：

- commit：`630a36e846a8a3de9bc6396b2e1a6de3cb995ebd`
- tree：`c5b425e39c64981290d514fe68d62853efbbac08`
- PR #81 synthetic merge commit：`5979f98548d39f3ea12cb1b14d4c22d234c96448`
- synthetic merge tree：`c5b425e39c64981290d514fe68d62853efbbac08`
- post-merge exact-head CI：workflow `32604117828`
- Ubuntu Python 3.11：PASS
- Ubuntu Python 3.12：PASS
- macOS Python 3.11：PASS
- Windows Python 3.11：PASS
- aggregate `policy-tests`：PASS
- generated package integrity：PASS
- Ruff：PASS
- pinned official OpenAI Plugin validator：适用 job PASS
- managed Agent lifecycle：PASS

当前 release-blocking 修复分支：`fix/v4-n0-exact-managed-agent-type`。

当前修复 PR：#96 `Fix V4 exact managed agent selector drift`，base 为 `v4/rc5-native-core@630a36e...`，保持 Draft 直到 package manifest、handoff、full CI 和 review 全部闭环。

PR #96 合并前，`630a36e...` 仍是正式 release candidate。PR #96 合并后会产生新 candidate，而且本次修复修改 shipped package bytes，所以旧 exact-candidate Host PASS 不能直接升级为新 candidate 的 formal PASS。

## 4. 当前公开产品面

公开 Skills 只有：

- `Orchestrate`
- `Doctor`

`Orchestrate` 负责 plan-only、delegation judgment、WorkUnit 分解、profile selection、managed execution、status、Steer、Correction、Continue、Interrupt、Takeover、integration、acceptance 和 consequence-based review 流程。

`Doctor` 负责 Plugin package、managed profiles、Host capability evidence、orchestration state、legacy compatibility 和 ownership-safe maintenance。

产品允许 0 child。`max_managed_children=4` 是 safety ceiling，不代表目标 fanout。

V4.0.0 当前排除 dynamic effort routing、nested managed delegation、autonomous peer authority transfer、daemon scheduler、persistent orchestration database、automatic worktree management 和 parallel isolated managed writers。

## 5. 固定 managed profile 合同

机器 authority：`contracts/policy.json`。

| Profile | Exact Host `agent_type` | Model | Effort | Mutation posture |
| --- | --- | --- | --- | --- |
| Reader | `subagents_dispatch_reader` | `gpt-5.6-luna` | `max` | none requested |
| Worker | `subagents_dispatch_worker` | `gpt-5.6-luna` | `max` | bounded-source-write |
| Investigator | `subagents_dispatch_investigator` | `gpt-5.6-terra` | `high` | none requested |
| Solver | `subagents_dispatch_solver` | `gpt-5.6-sol` | `high` | bounded-source-write |
| Advisor | `subagents_dispatch_advisor` | `gpt-5.6-sol` | `high` | none requested |

Reasoning effort 固定。生产 runtime 不做动态 effort routing。

Profile TOML 中 `sandbox_mode`、`agents.enabled=false`、`features.multi_agent_v2=false` 和禁止继续创建 subagents 的 developer instruction 都属于 requested posture。N1/N8 仍需要真实 Host evidence 才能证明 containment 或 effective read-only。

`max_depth=1` 也是 product policy，不能代替 V2 descendant containment proof。

## 6. authority 层级

出现冲突时按以下层级判断：

1. 当前 commit 的 production implementation 和 machine-readable contracts；
2. `contracts/` 当前产品合同；
3. `docs/v4/architecture.json` runtime ownership；
4. `docs/v4/host-smoke.json` N0-N8 Host release machine contract；
5. `docs/release-checklist.md` 人工 release sequence；
6. `docs/v4/phase-status.json` phase bookkeeping；
7. `docs/v4/technical-debt.json` open debt；
8. 本 handoff 的连续背景、当前状态和操作记录；
9. README 和普通产品文档；
10. `docs/history/` 只做历史 provenance。

如果本 handoff 的旧 SHA、Host build 或 upstream SHA 与当前 GitHub/Host 不一致，以重新读取的当前事实为准，并在下一次真实 repository content change 时更新本文件。

## 7. 目录和核心文件职责

根目录与元数据：

- `.codex-plugin/plugin.json`：Plugin identity/version；
- `.codex-plugin/package-integrity.json`：shipped payload SHA256 manifest；
- `.agents/plugins/marketplace.json`：Marketplace identity/source；
- `README_AI.md`：AI/维护者入口，链接本 handoff；
- `CHANGELOG.md`：版本级变化摘要。

`skills/`：只允许 `skills/orchestrate` 和 `skills/doctor` 作为当前公开面。

`agent-profiles/`：五个固定 managed profile。配置表示 requested route/posture，Host effective behavior 仍需实测。

`contracts/`：

- `policy.json`：固定 profile、delegation ceiling、review policy；
- `routing.md`：delegation value 和 Main dispatch judgment；
- `responsibility-packet.md`：child responsibility serialization；
- `guardrails.md`：authority/depth/mutation/writer/consent boundaries；
- `interaction.md`：Orchestrate controls；
- `recovery.md`：ExecutionBinding recovery；
- `state.md`：V4 state；
- `final-review.md`：exact-candidate independent review；
- `team-plan.md`：compatibility boundary，不拥有 runtime planning authority。

`scripts/`：

- `orchestrate_v4.py`：Main-facing V4 production facade；
- `managed_execution_v4.py`：exact managed spawn contract；
- `execution_lifecycle_v4.py` / `_core.py`：ExecutionBinding lifecycle preparation/reconciliation；
- `work_graph_v4.py`：WorkGraph、WorkUnit、dependencies、readiness、acceptance；
- `scheduler_v4.py`：constraint projection；
- `writer_lease_v4.py`：single canonical writer coordination；
- `host_capabilities.py`：Host capability normalization；
- `state_storage.py`：private state path、lock、atomic storage；
- `inspect-agent-runtime.py` / `inspect-collaboration-runtime.py`：allowlisted runtime evidence extraction；
- `doctor.py`：installed-product diagnosis；
- `install-agents.py` / `uninstall-agents.py`：owned managed profile lifecycle；
- `package_integrity.py`：package identity；
- `review-artifact.py`：Final Review artifact binding；
- `legacy_migration.py` / `legacy_state_cleanup.py`：legacy boundary。

`docs/v4/`：

- `architecture.json`：machine architecture ownership；
- `host-smoke.json`：N0-N8 machine gate；
- `host-capability-matrix.json`：feasibility evidence，无 release authority；
- `phase-status.json`：phase bookkeeping；
- `technical-debt.json`：open debt；
- `development-handoff.md`：本文件。

`docs/history/` 中可能出现旧 Dispatch Skill、Hook/Guard authority、PendingControl、TeamPlan runtime authority、固定 fanout/retry/followup budget。它们都不能重新定义 V4 当前行为。

## 8. 核心 ownership

| 事实或责任 | Owner |
| --- | --- |
| child materialization | Codex Host |
| native child lifecycle | Codex Host |
| underlying Host thread identity | Codex Host |
| actual capacity/admission | Codex Host |
| effective sandbox/permission | Codex Host |
| effective child collaboration surface | Codex Host |
| user intent/decomposition | Main |
| fixed-profile selection | Main |
| dispatch judgment | Main |
| artifact verification | Main |
| WorkUnit acceptance | Main |
| irreversible external effects | Main |
| final response | Main |
| responsibility/dependency/readiness/acceptance truth | WorkGraph / WorkUnit |
| one concrete managed attempt | ExecutionBinding |
| canonical workspace writer coordination | WriterLease |

禁止恢复第二套 lifecycle control plane、private Host occupancy ledger、固定 fanout/retry/followup budget、daemon scheduler 或平行 writer runtime。

## 9. WorkUnit、ExecutionBinding 和 acceptance

WorkUnit 表示稳定责任。ExecutionBinding 表示某一次 managed native attempt。

Host `COMPLETED` 只产生 candidate result，并把工作推进到 `RESULT_READY`。Main 检查 artifact、evidence 和责任完成情况后显式 accept。Dependencies 只从 `ACCEPTED` 解锁。

Fresh retry 需要 prior attempt safely settled，并且有 changed execution basis。没有固定 retry count。

Focused correction 必须有新的 correction basis。`followup_count` 只做诊断。

CONTINUE 复用 interrupted 的同一个 ExecutionBinding。

RUNNING Steer 当前使用 V2 `followup_task`，也保持原 ExecutionBinding。

## 10. WriterLease 和 UNKNOWN

当前 Agent 共享 filesystem/cwd，因此 canonical mutable workspace 保持一个 managed writer。

WriterLease blocking states：`RESERVED`、`HELD`、`REVOKING`、`UNKNOWN`。

`interrupt_agent` 成功只证明 interrupt request 被处理。WriterLease 必须等 current-generation authoritative Host settlement 后才能 release/transfer。

materialization、identity、lifecycle 或 writer settlement 有歧义时进入 UNKNOWN。UNKNOWN 不能授权 replacement、writer transfer、Main takeover 或 final acceptance。

## 11. OpenAI Codex MultiAgent V2 技术背景

此前较完整 upstream review baseline：`343074d4207d572809bd8cea15f4be1d09d98e0b`。

2026-08-23 06:51 +08:00 重新读取官方 `openai/codex` `main` 时，目标 HEAD 为 `8e649e3afa5cdddfb09a1b85a090b94775045d9b`，parent 为 `343074d...`。针对 V2 messaging 的复核确认关键 QueueOnly/TriggerTurn 语义没有变化。

已核过 V2 control family：

- `spawn_agent`
- `send_message`
- `followup_task`
- `wait_agent`
- `list_agents`
- `interrupt_agent`

V2 `spawn_agent` 使用 `fork_turns`。managed fresh spawn 要求 `fork_turns="none"`。历史 V1 的 `fork_context=false` 不能替代这条 release proof。

当前官方 V2 source 支持 `spawn_agent.agent_type`，但是否向模型暴露受 Host tool options/config 影响。近期 upstream issue 也出现 custom-agent selector exposure/routing 相关报告。这些 upstream 信息只做背景。正式 release 判断仍以当前安装 Host build 和 candidate-bound real Host evidence 为准。

`send_message` 当前走 QueueOnly；`followup_task` 走 TriggerTurn。RUNNING Steer 因此继续使用 `followup_task`，同时必须通过 same-child post-guidance evidence 证明 guidance 实际被原 child 消费。

Canonical task address 与 underlying Host thread identity 是两层事实。普通 runtime 可在公共 V2 surface 没暴露 thread identity 时使用 `native_task_name`。N2 formal evidence 要从 authoritative Host activity/lifecycle data 把 task address、Host thread identity 和目标 ExecutionBinding/profile 对上，禁止猜 `agent_id`。

## 12. Real Host gate 为什么单独管理

Repository CI 无法证明当前真实 Host 的：

- actual MultiAgent version；
- effective child model/effort；
- actual `fork_turns`；
- managed child collaboration containment；
- Host ThreadId binding；
- admission/materialization；
- RUNNING Steer consumption；
- interrupt settlement；
- effective permission；
- installed App surface。

因此 repository CI 和 Real Host qualification 是独立 release gates。

机器 Host gate authority：`docs/v4/host-smoke.json`。

Tracked 文件必须保持：

- `status = PENDING`
- `results = {}`

真实 Host 结果不能写回 tracked JSON，否则会改变 candidate artifact。

## 13. Issue #91 Real Host Test Ledger

Issue #91 是当前 Real Host operational ledger。它属于 GitHub metadata，不改变 candidate commit/tree。

每个真实 Host action 必须单独记录，然后才能进入下一 action。至少包括 candidate/local binding、package identity、Doctor、fresh session、Host build/version、V2 tool surface、每次 spawn、每个 N0 profile、grandchild probe、capacity rejection、Steer/Correction/Continue、Interrupt、WriterLease takeover、rollout inspection、Advisor permission probe、FAIL/UNKNOWN、人工观察和 retry。

每条记录至少保存：

```text
HOST-<gate>-<sequence>
Time with timezone
Candidate commit/tree
PR #81 head
Host build/version
Embedded Codex version
Platform/architecture
Run/session/thread IDs
Gate/substep
Prerequisites
Preflight lookup
Preflight decision: REUSE | RERUN | NOT_RUN
Exact operation/tool/command
Material inputs
Expected outcome
Observed outcome
Evidence ref
Verdict: PASS | FAIL | UNKNOWN | NOT_RUN | INVALIDATED
State/side effects
Reuse status
Rerun required
Invalidation or changed-basis reason
Next allowed step
Notes
```

拿不到的字段写 UNKNOWN 或 not observable，禁止猜测。

## 14. 防止重复跑 Real Host

每个 Host action 前先查 #91，然后明确选择：

- `REUSE`：旧 conclusive evidence 仍完整有效，禁止重复 Host action；
- `RERUN`：存在具体 invalidation 或 changed basis，才允许重跑；
- `NOT_RUN`：prerequisite 未满足。

新聊天、新维护者或新 Codex conversation 本身不能成为 rerun 理由。

以下条件保持时应复用 conclusive PASS：candidate 对该 formal gate 仍有效，相关 package/profile bytes 没变，target Host build/runtime identity 相同，machine contract 没实质变化，prerequisite 没变，evidence 完整可读，没有新事实推翻旧结论。

以下变化可以要求 affected step 重跑：candidate artifact 变化、Host build/runtime 变化、machine contract/oracle 变化、旧 evidence missing/corrupt/ambiguous、previous FAIL/UNKNOWN 且出现 changed basis、prerequisite 变化、相关 package/profile/runtime bytes 变化、真实 Host 出现冲突新事实。

OpenAI upstream `main` 前进本身不构成当前已安装 Host 的自动 rerun 理由。

## 15. 历史 Host evidence

### build 6892

历史 run `01a02ad1-dbb9-7cb0-990c-188c76f48848` 使用 MultiAgent V1，raw spawn 为 `fork_context=false`。五个目标 model/effort 当时有观察，但无法证明 V2 `fork_turns=none`。正式历史结论：N0 UNKNOWN。

### build 6962 capability audit

后续 audit 观察过 ChatGPT App build 6962、embedded Codex `0.149.0-alpha.4.1`、Main `multi_agent_version=v2` 和 V2 control family。它证明该 Host build 曾支持 V2，只能作为 capability context，不能替代 exact-candidate formal N0。

### 旧 exact install

候选 `d565af4d1274c07451a803b2ee831ef4a5233883` 曾完成 exact local Marketplace reinstall，50 files，missing 0、unexpected 0、hash mismatch 0，Doctor package/profile health OK。

截至 `630a36e...`，package manifest 仍是同一 Git blob `68d45d987a4883aa1d0af7511afce79801e95a77`，因此此前 package-byte continuity 可以 REUSE。

PR #96 现在修改 `scripts/orchestrate_v4.py` 和 `skills/orchestrate/SKILL.md` 两个 shipped payload 文件。PR #96 一旦合并，旧 package-byte continuity 不再覆盖新 candidate。新 package 必须重新绑定 installed product 和 fresh Host session。

## 16. N0-N8 当前合同

机器 authority：`docs/v4/host-smoke.json`。

| Gate | release requirement |
| --- | --- |
| N0 | exact managed role/agent_type、model、effort、真实 V2、`fork_turns=none` |
| N1 | 五 profile effective collaboration surface；grandchild attempt 只能 tool absent 或 authoritative Host deny，且无 descendant identity materialize |
| N2 | canonical task address 与 authoritative Host thread identity 绑定，并绑定目标 ExecutionBinding/profile |
| N3 | deliberate Host admission rejection；证明 no successful spawn result、Started activity、Host thread identity、durable identity 或 resident runtime materialize；歧义为 UNKNOWN |
| N4 | RUNNING Steer via `followup_task`；原 child 实际消费 guidance；无 replacement；same-child Correction/Continue 不开 fresh attempt |
| N5 | interrupt return 不释放 WriterLease；current-generation Host settlement 才能 settle |
| N6 | UNKNOWN/unsettled writer 阻止 replacement 和 Main takeover；settlement 后才可 transfer |
| N7 | rollout evidence 绑定 lifecycle call、child identity、result，并满足 privacy allowlist |
| N8 | fresh exact-candidate Advisor review；Host-observed effective permission 满足 strict read-only；artifact mutation 使旧 verdict 失效 |

N0 没 PASS 前不开始 N1。某个 gate 内部也按真实 action 逐步写 #91。

## 17. 2026-08-23 正式 Real Host campaign 已确认环境

正式候选：`630a36e846a8a3de9bc6396b2e1a6de3cb995ebd`，tree `c5b425e39c64981290d514fe68d62853efbbac08`。

用户本机仓库：`/Users/qunqing/2026-Project-Agent/subagents-dispatch`。

第一次 binding 发现本机分支名虽为 `v4/rc5-native-core`，实际 HEAD 仍停在旧 `d565af4d...`。GitHub compare 证明 `630a36e...` 比旧 HEAD ahead 4、behind 0，随后使用 `git merge --ff-only origin/v4/rc5-native-core` 安全快进。

快进后的实机 repository evidence：

- HEAD `630a36e846a8a3de9bc6396b2e1a6de3cb995ebd`
- tree `c5b425e39c64981290d514fe68d62853efbbac08`
- working tree clean
- Python `3.14.6`
- package integrity `ok=true`
- Doctor Plugin package OK
- Doctor 5 managed profiles OK
- Host integration UNKNOWN，尚未给 Host evidence 时这是预期状态
- Orchestration state UNKNOWN，没有 active task inspection 时这是预期状态
- Legacy compatibility OK

Fresh Host session evidence：

- ChatGPT App bundle identifier `com.openai.codex`
- App version `26.818.41509`
- Host build `6962`
- embedded Codex `0.149.0-alpha.4.1`
- macOS `27.0`, build `26A5416b`, arm64
- root rollout `/Users/qunqing/.codex/sessions/2026/08/23/rollout-2026-08-23T07-46-10-01a02bde-1702-7580-b850-fb4d555c5ab5.jsonl`
- root session/thread id `01a02bde-1702-7580-b850-fb4d555c5ab5`
- cwd exact repo
- `turn_context.multi_agent_version=v2`

对应 #91 关键记录：

- candidate binding PASS：comment `5383194153`
- fresh Host session PASS：comment `5383217607`
- N0 preflight：comment `5383218764`

## 18. N0 Reader 首次正式 probe 的 FAIL

同一 fresh root session 中执行了一次 N0 Reader probe。用户要求 Orchestrate 只 delegate 一个 read-only Reader，读取 `README_AI.md` 第一条 Markdown heading，不写文件、不再开其他 child、不提前跑 N1。

Root rollout 的 authoritative tool-call evidence：

```text
spawn_agent
call_id = call_DlAFzcAwvdfAKTX0k6BFkDyz
task_name = v4_n0_reader_probe
agent_type = codex_agent_team_reader
fork_turns = none
message_present = true
input_keys = [agent_type, fork_turns, message, task_name]
```

N0 Reader machine contract 要求：

```text
agent_type = subagents_dispatch_reader
model = gpt-5.6-luna
effort = max
fork_turns = none
```

因此该 attempt 的 `fork_turns=none` 通过，exact managed selector 失败。只凭这个 mismatch 已足够判 N0 Reader FAIL，无需用 child 自述补救。

第一次本地证据解析脚本因把 dict 当 set element 触发 `TypeError: unhashable type: 'dict'`。该错误只发生在读取现有 rollout 的辅助脚本，不能作为重跑 Host 的理由。修正解析器后，从同一 root rollout 得到上述真实 spawn input。

修正解析器按 `agent_role=subagents_dispatch_reader` 查 child 时得到 `reader_child_count=0`。这只说明没有找到该预期 role，不能推出没有 materialization。由于 selector failure 已经 conclusive，当前无需为了 N0 verdict 重跑或额外制造 child。

对应 #91：

- parser UNKNOWN entry：comment `5383230413`
- formal Reader FAIL：comment `5383236842`

N0 整体当前 FAIL/BLOCKED。Worker、Investigator、Solver、Advisor 和 N1 均未开始。

## 19. N0 Reader 根因与 PR #96

已确认 repository 设计缺口：

- `contracts/policy.json` 已拥有五个 exact `agent_type`；
- profile TOML 也使用对应 exact name；
- `scripts/managed_execution_v4.py` 能生成 exact managed spawn payload；
- `execution_lifecycle_v4_core.prepare_spawn()` 会逐字段拒绝错误 payload；
- 但 `scripts/orchestrate_v4.py` 的 `FIXED_PROFILES` projection 在 `630a36e...` 中只携带 model、effort、authority 和 semantic role，漏掉了 `agent_type`；
- 因而 `select_profile("reader")` 没把 Host 需要的 literal selector交给 Main-facing profile result；
- `skills/orchestrate/SKILL.md` 当时虽然要求 exact managed profile 和禁止 generic substitute，但没有显式列出五个 literal selector，也没有把 `build_managed_spawn_tool_input` + `prepare_spawn` 写成每次 native spawn 前必须执行的合同。

这能解释为什么 formal Host probe 中 Main 把 Reader 语义路由成了 Host generic `codex_agent_team_reader`。

当前修复分支：`fix/v4-n0-exact-managed-agent-type`。

PR #96 已做：

1. `scripts/orchestrate_v4.py`
   - `FIXED_PROFILES` 增加 policy-owned `agent_type`；
   - `select_profile()` 因此直接返回 exact Host selector。
2. `tests/test_orchestrate_v4.py`
   - 每个 fixed profile 必须返回与 policy 一致的 `agent_type`；
   - Orchestrate Skill 必须包含五个 literal selector；
   - Skill 必须包含 generic fallback 禁令和 deterministic pre-spawn helper 名称。
3. `skills/orchestrate/SKILL.md`
   - 明列五个 exact managed `agent_type`；
   - 每次 native spawn 前要求 `build_managed_spawn_tool_input` 和 `prepare_spawn`；
   - exact type unavailable/omitted/rejected 时停止 delegation；
   - 禁止 built-in/generic Host Agent fallback。
4. `.codex-plugin/package-integrity.json`
   - 因 production/Skill payload 发生变化，重新生成对应 SHA256。

首轮 PR #96 CI workflow `32606666309` 在 package-integrity step 按预期失败，因为 manifest 尚未刷新。CI 生成器给出的新 digest：

- `scripts/orchestrate_v4.py`：`be8ccb6610785e793313e56bda77a0703fa06cf2932e3a8441f138d70e34898d`
- `skills/orchestrate/SKILL.md`：`b24017af98286c0a2e11291513c8f0f61c18b4867297faff2d5cbfa8bc9d7cd5`

manifest 已按生成器结果刷新。后续 exact PR-head CI 必须重新全跑，首轮预期失败不能算验证通过。

这次修复提供了新的 repository changed basis，但它的真实 Host effectiveness 仍需在 PR #96 merge、post-merge exact-head CI、新 package installation/binding 和 fresh Host session 后验证。当前禁止在旧 `630a36e...` session 中重跑 Reader。

## 20. Repository CI 与 Real Host 的关系

Repository CI 要覆盖 Plugin/Marketplace manifests、package-integrity regeneration、official Plugin validator、Ruff、full pytest、managed profile install/check/uninstall lifecycle、Doctor、V4 state/work graph/scheduler/lifecycle/writer、update lifecycle、migration fail-closed 和 product-surface consistency。

Required matrix：Ubuntu Python 3.11、Ubuntu Python 3.12、macOS Python 3.11、Windows Python 3.11。

CI PASS 不能替代 Host PASS。Host PASS 也不能替代 repository CI。

任何 repository content mutation 产生新 candidate 后，都要重新跑 exact-head repository matrix。CI/review/Host结果属于 external evidence，禁止为了把 PASS 写回 handoff再制造一个新 candidate。

## 21. Package、安装和 fresh-session 边界

Plugin version 当前为 `4.0.0`。

Package identity 与 repository candidate identity 分层：repository commit/tree 可能因为 docs/tests 改动变化；`.codex-plugin/package-integrity.json` 只覆盖 shipped payload；package bytes 相同也不能证明当前 Host session 绑定新 candidate。

首次创建或更新 managed profile 后，如果 running task 不能权威证明 registry 已加载新的 profile state，应返回 `RESTART_REQUIRED` 并创建 fresh task。不能为了省一次 restart 改用 generic Agent。

PR #96 修改 shipped runtime/Skill payload。它合并后必须刷新本机 exact candidate/package binding，并启动 fresh ChatGPT/Codex session，旧 `630a36e...` session 不能承担新 candidate 的 formal rerun。

## 22. 当前 technical debt

`docs/v4/technical-debt.json` 仍记录若干非当前 blocking 项：

- Doctor Host evidence UX：先观察 N0-N8，再决定是否增加更小 capture UX；
- experiment-plane consolidation：release-critical Native Core 稳定后再收敛；
- state path TOCTOU hardening：已有 symlink/private dir/`O_NOFOLLOW`/bounded files/fsync/atomic replace 等保护，hostile same-user namespace swap 仍有窄窗口。

这些 debt 不放松 N0-N8 release gate。

## 23. 关键 PR 历史

### PR #88 Host contract hardening

修复 N2 identity binding、N3 admission/materialization oracle、N4 RUNNING Steer 等 Host contract。没有生产 runtime/package payload 变化。最终四平台 CI PASS。

### PR #89 N4 release documentation closure

把 RUNNING Steer 的人工 release probe 与 machine contract 对齐，并明确 tool-call acceptance alone insufficient。最终合并 commit `4530382427556f20fe8fd57e56108016d5f2a3e2`，post-merge workflow `32600567749` PASS。

### PR #90 live development handoff

创建本 handoff 并从 `README_AI.md` 建入口。修复 CI 写回导致 candidate 自更新循环、merge-state stale instruction 和 README trailing newline regression。最终 squash `6f1f3179f087e72fb1329c13bc6a9024faf117de`，workflow `32602156632` PASS。

### PR #92 complete project handoff background

把 handoff 扩成完整 takeover guide，并创建 Issue #91 作为非修改性 Real Host Test Ledger。合并为 `630a36e846a8a3de9bc6396b2e1a6de3cb995ebd`，post-merge workflow `32604117828` PASS。

### PR #96 exact managed agent selector drift

由 formal N0 Reader FAIL 触发。当前 Draft、开发中。它是当前 release 主阻塞项。

## 24. 禁止错误推理

接手时主动避免：

- 从 profile `sandbox_mode=read-only` 推 effective Host read-only；
- 从 `max_depth=1` 推 V2 descendant containment；
- 从 child 自述推 model、effort、permission 或 collaboration Host truth；
- 从 V1 `fork_context=false` 推 V2 `fork_turns=none`；
- 从 resident runtime 不可见推 durable child identity 从未 materialize；
- 从 interrupt return success 推 WriterLease 可释放；
- 从 `followup_task` accepted 推 guidance 已消费；
- 从 repository CI PASS 推 N0-N8 PASS；
- 从旧 exact install 推当前 package/session binding；
- 从换聊天会话推所有 Host tests 需要重跑；
- 从 OpenAI upstream `main` 更新推本机 installed Host 自动更新；
- 把 UNKNOWN 当 PASS；
- 把语义角色名 Reader 映射到 generic Host Reader 并当作 managed Reader；
- 用 generic Agent fallback 掩盖 exact `agent_type` unavailable/rejected。

## 25. Repository 开发工作流

每次 repository content change：

1. 读取本 handoff、当前 Git/PR、相关 machine contracts 和 #91；
2. 从 exact base 建短生命周期 branch；
3. 明确最小影响范围；
4. 实施时同步更新本 handoff；
5. 对非平凡变更检查是否有更简单的 root-cause 方案；
6. 跑 targeted tests，再跑 full required CI；
7. review findings 按根因修；
8. 全绿后才 merge；
9. merge 后重新读取 candidate commit/tree、PR #81 head/synthetic merge tree；
10. 跑 post-merge exact-head repository CI；
11. Real Host action 按 #91 逐动作记录。

Commit message 说明实际意图，保持小而可验证。

## 26. Handoff 自身维护规则

任何 repository content modification 都必须同步更新本文件。GitHub 单文件接口导致相关修改分成相邻 commits 时，handoff sync 必须在 PR merge 前完成。

CI、review、PR metadata、Issue #91 Host ledger、安装审计和人工观察都属于非 repository content facts。它们立即记录在外部证据位置，并在下一次真实 repository content change 时顺带汇总。禁止仅为了记录某个 PASS 改 handoff，否则会改变 exact candidate 并制造新的 Host rerun。

本文件不能为了填写包含自身修改的 commit SHA 再制造自引用 commit。需要时通过 Git history 解析。

## 27. 当前下一步

当前唯一允许的 release 路径：

1. 完成 PR #96 的 package-integrity、handoff sync、targeted/full CI 和 adversarial review；
2. PR #96 全绿且无 blocking review finding 后合并回 `v4/rc5-native-core`；
3. 重新冻结新的 formal candidate commit/tree；
4. 跑新 candidate 的 post-merge exact-head repository matrix；
5. 更新 PR #81 metadata，但不要为了 metadata 再改 candidate；
6. 用户本机 fast-forward 到新 candidate；
7. 因 shipped package bytes 已变化，重新做 exact installed package/managed-profile binding；
8. 完全 fresh ChatGPT/Codex session，重新记录 Host environment identity；
9. 查 #91，旧 Reader FAIL 因 candidate/package changed basis 可标记 superseded，然后只重跑 N0 Reader；
10. Reader PASS 后才依次推进其余 N0 profiles；
11. N0 整体 PASS 后才进入 N1；
12. N1-N8、fresh exact-candidate Final Review、external release evidence、installed-product gate、human two-Skill App observation 全完成前，PR #81 保持 Draft，publication BLOCKED。

当前不允许：在旧 `630a36e...` session 重跑 Reader、提前跑 Worker、提前跑 N1、把 generic `codex_agent_team_reader` 当 managed Reader PASS。

## 28. Modification Log

### H001 2026-08-23 05:58 +08:00，建立 live handoff

建立 repository-local development continuity record。旧分支上的第一次尝试没有进入正式候选，随后通过 PR #90 正式落仓。

### H002 2026-08-23 06:02 +08:00，记录首轮 validation

PR #90 workflow `32601201287` 四平台 PASS，后续 exact head workflow `32601391850` PASS。

### H003 2026-08-23 06:06 +08:00，修复 merge-state stale instruction

Review 发现 handoff 合并后仍要求等待自身 PR，会自失效。改为按当前 GitHub state 重新解析下一步。

### H004 2026-08-23 06:12 +08:00，关闭 CI 写回自更新循环

明确 post-commit CI、Host evidence、review metadata 不要求为记录 PASS 再修改 candidate；同时从 `README_AI.md` 建立 handoff 入口。

### H005 2026-08-23 06:15 +08:00，修复 README trailing newline regression

首轮 full pytest 唯一失败来自 `README_AI.md` 缺 final newline。保留 regression test，修正文件，PR #90 最终 workflow `32601974555` PASS。

### H006 2026-08-23 06:51 +08:00，补全 takeover background 和 Host ledger

PR #92 扩充项目目的、Native Core 演进、authority、目录地图、Host 技术背景、release gates、技术债和历史决策，并建立 Issue #91。PR #92 合并后正式候选成为 `630a36e...`，post-merge workflow `32604117828` PASS。

### H007 2026-08-23 08:02 +08:00，记录 formal N0 Reader FAIL 并修复 exact selector path

触发：正式 Real Host N0 Reader probe 在 build 6962 / embedded Codex `0.149.0-alpha.4.1` / V2 session `01a02bde-1702-7580-b850-fb4d555c5ab5` 中实际调用 `spawn_agent(agent_type="codex_agent_team_reader", fork_turns="none")`。机器合同要求 `subagents_dispatch_reader`，因此 Reader formal verdict 为 FAIL。

关键 evidence：call id `call_DlAFzcAwvdfAKTX0k6BFkDyz`，task `v4_n0_reader_probe`，实际 input keys 完整，`fork_turns=none` 正确，exact managed selector 错误。#91 formal FAIL comment `5383236842`。

根因分析发现 `contracts/policy.json` 和 managed execution helper 已保存 exact selector，但 Main-facing `orchestrate_v4.FIXED_PROFILES` 漏掉 `agent_type`，同时 Skill 没有列出五个 literal selector，也没有强制 native spawn 前走 deterministic payload/preparation helpers。

修复 branch：`fix/v4-n0-exact-managed-agent-type`。PR #96。

修改范围：

- `scripts/orchestrate_v4.py`
- `tests/test_orchestrate_v4.py`
- `skills/orchestrate/SKILL.md`
- `.codex-plugin/package-integrity.json`
- `docs/v4/development-handoff.md`

生产修复把 policy-owned exact `agent_type` 带入 `select_profile()`；Skill 明列五个 selector，要求 `build_managed_spawn_tool_input` + `prepare_spawn`，并禁止 generic Host Agent fallback；tests 增加 selector projection 和 Skill contract regression。

首轮 PR #96 workflow `32606666309` 在 manifest 尚未刷新时按预期停在 generated package-integrity check。CI 生成器提供新 digest 后已刷新 manifest。该首轮失败只用于生成/确认 package hash，不能算最终 validation。

本次修改改变 shipped package bytes，因此 PR #96 合并后必须重新做 package/install/fresh-session binding，并以 changed basis 重跑 Reader。旧 `630a36e...` Host Reader FAIL 保留为历史 evidence，不能删除，也不能直接在旧 session 重跑。
