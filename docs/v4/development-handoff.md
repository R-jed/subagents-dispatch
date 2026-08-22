# V4 实时开发交接记录

初始记录时间：2026-08-22T21:58Z，对应 2026-08-23 05:58 +08:00。

最新记录时间：2026-08-22T22:15Z，对应 2026-08-23 06:15 +08:00。

状态：持续维护。此文件是 V4 当前开发上下文的仓库内交接入口。新会话、新维护者或新的 Codex session 接手前，应先读本文件，再核 GitHub 当前分支、PR、CI 和真实 Host evidence。

## 1. 强制维护规则

从本记录建立起，任何后续仓库内容修改都必须同步更新 `docs/v4/development-handoff.md`。同一修改应记录时间、触发原因、技术背景、实际改动、影响文件、明确未变化的边界、验证方法、验证要求、风险、下一步和注意事项。受 GitHub 单文件写入接口限制时，相关文件修改和 handoff 补录可以是同一 PR 内相邻提交，但 handoff 补录必须在合并前完成。

不改变仓库内容的活动不要求为了“记录结果”额外制造新 HEAD。这类活动包括 post-commit GitHub CI、review/comment/PR metadata、real Host evidence、安装审计和人工观察。它们可以保存在 GitHub、仓库外部 evidence 或当前会话记录中，并在下一次真实仓库内容修改时顺带补录到 handoff。禁止仅为了记录某个 CI PASS、review 状态或 Host 结果而修改 handoff，因为那会让被记录的 exact HEAD 立即失效并形成无限自更新循环。

本文件不能为了填写“包含本文件修改的那个 commit SHA”再单独制造一个 commit，否则会形成 SHA 自引用循环。该 commit 通过 `git log -- docs/v4/development-handoff.md` 解析。记录中写修改前基线、分支、PR 和语义结果。

`docs/v4/host-smoke.json` 的 tracked `status` 必须保持 `PENDING`，`results` 必须保持空对象。真实 N0 到 N8 结果只允许存放在仓库外部 evidence。

PR #81 在 real Host N0 到 N8、fresh Final Review、external release evidence、installed-product gate 和 human App observation 全部完成前保持 Draft。

## 2. 当前正式候选状态

当前正式候选分支：`v4/rc5-native-core`

当前主发布 PR：`#81 RC5 Native Core: remove Hook control plane`

PR #81 状态：OPEN、Draft、未合并。

截至 handoff PR 合并前，正式候选 HEAD：

`4530382427556f20fe8fd57e56108016d5f2a3e2`

正式候选 tree：

`2d6499de095cfde124c85a9cc195e014af1bbf75`

PR #81 synthetic merge commit：

`d24c2dc995d2394582313fed60584ab4405b24f0`

synthetic merge tree：

`2d6499de095cfde124c85a9cc195e014af1bbf75`

因此截至 handoff PR 建立前，PR #81 synthetic merge tree 与正式候选 tree 完全一致。

候选 exact-head repository CI：workflow `32600567749`。

该 workflow 已确认：Ubuntu Python 3.11 PASS，Ubuntu Python 3.12 PASS，macOS Python 3.11 PASS，Windows Python 3.11 PASS，aggregate `policy-tests` PASS，generated package-integrity PASS，Ruff PASS，适用 job 的官方 OpenAI Plugin validator PASS，Doctor 和 managed Agent lifecycle PASS，完整 pytest 为 `527 passed`。

当前 handoff 落仓 PR：`#90 Add live V4 development handoff`。

PR #90 base：`v4/rc5-native-core@4530382427556f20fe8fd57e56108016d5f2a3e2`。

PR #90 工作分支：`docs/v4-live-development-handoff`。

PR #90 当前文档范围包括 `docs/v4/development-handoff.md` 和 `README_AI.md`。`README_AI.md` 负责让新 AI/维护会话能从既有入口发现实时 handoff。两者都不改变 production runtime、machine Host contract 或 Plugin package payload。

接手时必须先读取 PR #90 当前状态。如果 PR #90 已合并，则本节中的 `453038...` 和 PR #90 信息只作为合并前历史基线，正式候选必须重新从 `v4/rc5-native-core` 当前 HEAD/tree 读取，不能继续把旧 SHA 当现状。

当前 `docs/v4/host-smoke.json` 仍应保持 `PENDING` 和空 `results`。repository CI 不代表 real Host gate 已完成。

## 3. 2026-08-23 handoff 落仓时的并发纠偏

用户在 PR #89 后要求把完整实时开发上下文写进仓库，并要求今后每次修改同步记录 handoff。

第一次 handoff 文件尝试写在旧工作分支 `fix/v4-n4-release-doc-closure`，commit 为：

`6398444ee184a268980ebee39d7449f8b6ebfd60`

但 GitHub 随后核对发现 PR #89 已于 `2026-08-22T21:46:35Z` 合并，也就是该 handoff commit 产生前 PR 已结束。PR #89 的 merge commit 为：

`4530382427556f20fe8fd57e56108016d5f2a3e2`

因此 `6398444...` 只存在于已经完成使命的旧工作分支，没有进入正式候选。它只能作为历史痕迹，不能被当作正式候选 handoff authority。

纠偏方案：从正式候选 `4530382427556f20fe8fd57e56108016d5f2a3e2` 新建短分支：

`docs/v4-live-development-handoff`

本文件在该分支重新建立，并以真实候选状态为基础，通过 PR #90 合入 `v4/rc5-native-core`。这一处理避免把旧 PR 分支上的额外提交误认为已进入候选。

## 4. 当前产品和架构边界

产品版本：`4.0.0`。

公开 Skills 只有 `Orchestrate` 和 `Doctor`。

V4 架构是 Hookless Native Core。Codex Host 保持真实 Agent runtime authority，插件只维护编排责任、安全状态和 acceptance 边界。

| 责任 | 当前 owner |
| --- | --- |
| child materialization | Codex Host |
| child native lifecycle | Codex Host |
| native child thread identity | Codex Host |
| actual Host capacity 和 admission | Codex Host |
| effective sandbox 和 permission | Codex Host |
| effective child collaboration surface | Codex Host |
| user intent 和 decomposition | Main |
| fixed managed profile selection | Main |
| dispatch judgment | Main |
| artifact verification | Main |
| WorkUnit acceptance | Main |
| irreversible external side effects | Main |
| final response | Main |
| dependency、readiness、acceptance truth | WorkGraph / WorkUnit |
| one concrete managed attempt | ExecutionBinding |
| canonical workspace managed writer coordination | WriterLease |

禁止重新引入第二套 lifecycle control plane、私有 Host occupancy ledger、固定 fanout、固定 retry budget、固定 followup budget、daemon scheduler、自动 worktree runtime 或平行 isolated writer 模式。

## 5. 固定 Agent profile 合同

机器权威：`contracts/policy.json`。

| Profile | Model | Reasoning effort | Ordinary mutation posture |
| --- | --- | --- | --- |
| Reader | `gpt-5.6-luna` | `max` | none requested |
| Worker | `gpt-5.6-luna` | `max` | bounded-source-write |
| Investigator | `gpt-5.6-terra` | `high` | none requested |
| Solver | `gpt-5.6-sol` | `high` | bounded-source-write |
| Advisor | `gpt-5.6-sol` | `high` | none requested |

Profile 中的 `sandbox_mode`、`agents.enabled=false`、`features.multi_agent_v2=false` 以及不继续创建 subagents 的 developer instruction 都属于产品请求和行为意图。它们不能单独证明真实 Host enforcement。

项目的 `max_depth=1` 也是产品 policy，不能直接作为 Codex MultiAgent V2 descendant containment proof。

## 6. OpenAI Codex MultiAgent V2 技术基线

最近一次针对 OpenAI 官方 `openai/codex` upstream 的源码审查基线：

`343074d4207d572809bd8cea15f4be1d09d98e0b`

以下结论属于该 upstream 基线的源码事实。未来 upstream 变化后必须重新核对，不能永久假设行为不变。

### 6.1 V2 native control surface

已核对 V2 control family 包含：`spawn_agent`、`send_message`、`followup_task`、`wait_agent`、`list_agents`、`interrupt_agent`。

V1 和 V2 是不同工具族。V1 行为不能未经重新验证直接升级为 V2 release proof。

### 6.2 fresh context 和 `fork_turns`

V2 `spawn_agent` 使用 `fork_turns`。省略时可继承 parent turns，`fork_turns="none"` 表示不 fork parent conversation history。

旧 V1 使用 `fork_context`。当前 V2 会拒绝已废弃的 `fork_context` 参数，并要求使用 `fork_turns`。

因此正式 N0 必须真实观察到 V2 和 `fork_turns=none`。历史 V1 `fork_context=false` 不能算 V2 PASS。

### 6.3 `send_message` 和 `followup_task`

当前 upstream 中，`send_message` 使用 QueueOnly 语义，不主动触发新的 turn。

`followup_task` 使用 TriggerTurn 语义。目标 child 正在 RUNNING 时，消息可以在采样消息边界或当前 pending tool call 完成后交付；目标 idle/reusable 时可触发 turn。

当前 V4 RUNNING Steer 继续采用 V2 `followup_task`。N4 不能把 native tool call accepted 当成 guidance 已应用。必须从 post-guidance evidence 证明 original child 实际消费了 guidance，并且没有 replacement identity materialize。

### 6.4 canonical task address 与 Host thread identity

模型可见 `spawn_agent` 的 canonical control address 可以主要表现为 `task_name`。Host 内部另有 ThreadId 或 agent identity。

项目 ExecutionBinding 已支持 `native_task_name` 和 Host evidence 可获得时的 `agent_id`。

普通 runtime 必须继续允许公共 V2 surface 没有暴露 `agent_id` 时使用 `native_task_name`。正式 N2 release evidence 则必须从 authoritative Host activity/lifecycle evidence 把 task address 和底层 Host thread identity 对上。禁止猜测或伪造 `agent_id`。

### 6.5 durable identity、resident runtime、active execution

当前 upstream 已经把 logical/durable child identity、resident runtime、active child execution 拆成不同事实。

AgentRegistry 中的 durable identity 可以继续存在，即使对应 runtime 已从 ThreadManager unload。因此“当前 resident surface 没看到 child”不能推出“从未 materialize child identity”。

N3 必须检查可获得的 authoritative evidence，例如成功 spawn result、Started activity、Host thread identity、durable child identity、resident runtime。任何无法排除 materialization 的情况都进入 UNKNOWN。

### 6.6 capacity

当前公开配置 `agents.max_concurrent_threads_per_session` 的用户层语义是 spawned agents 数量，不含 primary。内部 V2 session concurrency 采用 root-inclusive limit。

项目保留稳定的 root-inclusive Host session capacity 机器语义。若 release probe 的 capacity 来源是公开配置，必须先做 spawned-agent-only value 加 primary 的 normalization，再进入 scheduler projection。

Host actual admission rejection 才是最终 capacity authority。scheduler 只做保守 constraint projection，不创造私有 Host occupancy truth。

### 6.7 role 与 effective permission

当前 upstream role 通过 Config layering 参与 child config 构建，但 spawn 后还会应用 live parent runtime permission profile、approval、cwd 等 runtime override。

因此 profile 中声明 `sandbox_mode=read-only` 只能证明 requested posture。N8 必须用真实 Host evidence 证明 Advisor 的 effective sandbox/permission 满足 strict read-only Final Review 边界。

## 7. 历史 Host evidence

### 7.1 build 6892 旧 N0

历史 run：`01a02ad1-dbb9-7cb0-990c-188c76f48848`。

Host build：6892。

当时五个 child 的目标 model/effort 被观察到，但实际工具路径为 MultiAgent V1，raw spawn 使用 `fork_context=false`，没有 V2 `fork_turns`。

正式结论：`N0: UNKNOWN`。

原因：V1 fresh-context 不能替代 V2 `fork_turns=none` release proof。

### 7.2 build 6962 Main V2 audit

后续独立 audit 观察到 Host build 6962，embedded Codex `0.149.0-alpha.4.1`，Main runtime `multi_agent_version=v2`，并可见 V2 tool family。

这证明该环境支持 V2，但不能替代新 exact candidate 的 N0。

正式 N0 运行时必须记录实际当前 Host build，不能假定仍是 6962。如果 Host 自动更新，新的 build 只代表新的 environment identity，需要重新验证 V2 surface。

### 7.3 旧 exact-candidate reinstall

旧候选 `d565af4d1274c07451a803b2ee831ef4a5233883` 曾完成 local exact Marketplace reinstall，50 个 package files missing 0、unexpected 0、hash mismatch 0，Doctor 没有 blocking product-health failure。

当前候选已经变化，因此旧 reinstall evidence 不能证明 `453038...` 或未来 handoff merge 后的新 candidate exact installation。

## 8. PR #88：Host contract hardening

PR #88：`Harden V4 Host identity and Steer gates`。

base：旧正式候选 `d565af4d1274c07451a803b2ee831ef4a5233883`。

最终 squash commit：

`d79ead8ff70e799368e59616693309bc8598a321`

commit title：`fix: harden V4 Host identity and Steer gates`。

修改文件：`docs/v4/architecture.json`、`docs/v4/host-smoke.json`、`tests/test_host_contract_v4.py`。

没有修改 production runtime Python，没有修改 WriterLease、WorkGraph、scheduler implementation、managed profiles 或 Hook path。

主要变化：N2 区分 canonical `native_task_name` 和 release-evidence Host thread identity；N3 增强 admission rejection 和 durable/resident materialization oracle；N4 明确 RUNNING Steer、correction、continuation，并把当前 Steer V2 tool 固定为 `followup_task`。

审查中修复两个关键 P1。

第一个 P1 指出 capacity 字段初版破坏稳定机器合同。最终保留既有 `session_concurrency_includes_primary`，把 public config 与 internal normalization 作为附加 truth 字段。

第二个 P1 指出 N2 初版可能让普通 runtime 错误强制要求 `agent_id`。最终边界为：release campaign 必须双绑定 task address 和 Host thread identity；ordinary runtime 在 public V2 没有暴露 `agent_id` 时继续允许 canonical `native_task_name`。

PR #88 最终四平台 CI 全绿，完整 pytest 为 526 passed，package-integrity、Ruff、官方 Plugin validator 和 managed Agent profile lifecycle 均通过。

## 9. PR #89：N4 release documentation closure

PR #89：`Close V4 N4 release documentation gap`。

触发原因：PR #88 把 machine `host-smoke.json` 的 N4 扩成 RUNNING Steer 后，`docs/release-checklist.md` 和 `docs/architecture.md` 的人工操作摘要仍写旧的 same-child followup/continue，存在 operator 漏跑 Steer 仍提交 N4 PASS 的风险。

修改文件：`docs/release-checklist.md`、`docs/architecture.md`、`tests/test_release_contracts.py`。

没有修改 production runtime，没有修改 Plugin package payload，没有修改 `docs/v4/host-smoke.json`。

人工 release summary 现在明确：N2 canonical task address 加 Host-thread identity evidence binding；N3 Host admission rejection 且 no child identity or resident runtime materialization；N4 RUNNING Steer via `followup_task`，original child consumption evidence，no replacement identity，保持 `ExecutionBinding`、`attempt_no`、`control_epoch`、`followup_count`。

Representative flows 增加 `RUNNING Steer consumed by the same child`。

第一次 PR #89 workflow `32598858689` 四平台确定性失败同一新增测试，结果 1 failed、526 passed。根因是新增 regression test 要求人工文档出现明确 `tool-call` 负向证据措辞，而 release checklist 只写了语义等价的 “successful followup_task call is not sufficient by itself”。

处理方式没有删除测试，也没有放松证据标准。commit `d2f68d68af6e0fef56afa20332ddf8c29fa3aa52`，message `docs: state N4 tool-call evidence boundary`，把人工文档补成与 machine contract 一致的 tool-call acceptance boundary。

第二轮 workflow `32600406233` 四平台全绿。

PR #89 最终于 `2026-08-22T21:46:35Z` 合并，正式候选变成 `4530382427556f20fe8fd57e56108016d5f2a3e2`，tree `2d6499de095cfde124c85a9cc195e014af1bbf75`。

合并后 exact-head workflow `32600567749` 再次四平台全绿，完整 pytest 为 527 passed。这是当前 handoff PR 建立前的正式 repository validation 基线。

## 10. N0 到 N8 当前机器合同

机器权威：`docs/v4/host-smoke.json`。

| Gate | 当前 release requirement |
| --- | --- |
| N0 | exact role/model/effort，真实 MultiAgent V2，managed spawn `fork_turns=none` |
| N1 | 五个 fixed profile 的 effective collaboration surface，adversarial grandchild probe，结果必须是 tool absent 或 authoritative Host deny，并且无 descendant identity materialize |
| N2 | canonical task address 与 authoritative Host thread identity 的 release-evidence binding，并绑定目标 ExecutionBinding/profile |
| N3 | deliberate Host admission rejection，证明 no child identity 和 no resident runtime materialization，任何歧义为 UNKNOWN |
| N4 | RUNNING Steer via `followup_task`，original child 消费 guidance，无 replacement，same-child correction/continue，无 fresh attempt |
| N5 | interrupt return 不能释放 WriterLease，current-generation Host settlement 才能 settle |
| N6 | UNKNOWN/unsettled writer 阻止 replacement 和 Main takeover，settlement 后才能 transfer writer |
| N7 | rollout evidence 绑定 lifecycle call、child identity、result，并满足 privacy allowlist |
| N8 | fresh exact-candidate Advisor review，effective Host permission 满足 strict read-only，artifact mutation 使旧 verdict 失效 |

N0 到 N8 必须写外部 evidence，不回填 tracked `host-smoke.json`。

## 11. WriterLease 和 UNKNOWN 原则

当前 Codex Agent 共享 container、filesystem 和 current working directory。即使职责文件不同，也可能通过 Git index、generated files、config、dependency state 或 cross-file mutation 产生冲突。因此 V4 当前只允许一个 canonical managed writer。

WriterLease 的 `RESERVED`、`HELD`、`REVOKING`、`UNKNOWN` 均为 blocking state。

`interrupt_agent` 成功返回不能证明 writer 已停止写入，也不能自动释放 WriterLease。

只有 current-generation authoritative Host lifecycle evidence 才能结算 execution 和 WriterLease。

materialization、identity 或 lifecycle 存在歧义时进入 UNKNOWN。UNKNOWN 不授权 replacement、writer transfer、Main takeover 或 final acceptance。

## 12. Hook 状态

当前 V4 correctness path 不依赖 Hook。旧 Hook lifecycle control plane 已从正式 package correctness path 删除。

未来 Hook 可以作为 optional observability、diagnostics 或 defense-in-depth，但不能成为 spawn authorization、child lifecycle settlement、WriterLease release、retry authorization、WorkUnit acceptance 或 Main final acceptance authority。

任何恢复旧 Hook control plane 的提议都必须重新做架构审查。

## 13. package 与 install 边界

PR #88 和 PR #89 都没有改变 50-file Plugin package payload。PR #81 当前描述确认 `.codex-plugin/package-integrity.json` 与此前 exact-installed package payload byte-identical。

`docs/v4/development-handoff.md` 和 `README_AI.md` 都不在当前 50-file Plugin package payload 内。PR #90 的 repository CI 已持续通过 generated package-integrity check，说明文档改动没有意外改变 shipped payload。最终 PR head 仍必须通过同一检查。

不过 candidate commit 会因为 handoff 文件和 AI 入口落仓而变化，所以即使 package payload byte-identical，正式 release 仍要重新记录 exact candidate commit/tree，并做 non-mutating installed-package identity re-audit，确认已安装 package 与最终 frozen candidate 的 package manifest 一致。

## 14. 当前 remaining release gates

接手时先判断 PR #90 状态。

如果 PR #90 仍 OPEN：完成其 final-head repository matrix、review 和 diff 审查；只有全部通过后才允许 squash merge。最终 CI 和 review 结果属于非仓库修改证据，不需要为了写回 PASS 再制造新的 handoff commit。

如果 PR #90 已 MERGED：跳过所有“等待或合并 PR #90”的步骤，立即读取 `v4/rc5-native-core` 当前 HEAD/tree 和 PR #81 当前 synthetic merge tree，把它们作为新的正式 candidate identity，并完成 post-merge exact-head repository CI。

完成 handoff 合并后的 candidate re-freeze 后，进行 non-mutating installed-package identity re-audit。若需要 reinstall，则重新完成 exact local Marketplace binding、plugin reinstall、50-file identity、Doctor 和 fresh-session boundary。

之后才进入正式 N0。N0 PASS 后才能准备 N1。N0 UNKNOWN 或 FAIL 时停止并记录 blocker。

N1 到 N8、fresh Final Review、external release evidence、installed-product gate、human two-Skill App observation 仍未完成。

PR #81 继续保持 Draft，publication BLOCKED。

## 15. 禁止错误推理

不能从 profile `sandbox_mode=read-only` 推出 effective Host read-only。

不能从 `max_depth=1` 推出 V2 descendant containment。

不能从 child 自述推出 model、effort、permission 或 collaboration surface 的 Host truth。

不能从 V1 `fork_context=false` 推出 V2 `fork_turns=none` 已验证。

不能从没有 resident runtime 推出没有 durable child identity。

不能从 `interrupt_agent` 返回成功推出 WriterLease 可释放。

不能从 `followup_task` accepted 推出 RUNNING Steer 已被 child 实际应用。

不能从 repository CI PASS 推出 real Host N0 到 N8 PASS。

不能从旧 candidate exact install 推出新 candidate package identity。

不能把 UNKNOWN 当 PASS。

## 16. 下一步严格顺序

先读取 GitHub 当前 PR #90 状态，按以下分支执行。

### A. PR #90 仍 OPEN

1. 读取 PR #90 当前 head，确认 final-head repository matrix 全绿。
2. 再次检查 PR #90 review threads 和 changed files。
3. 只有无 blocking review 且 changed files 仅为文档范围 `docs/v4/development-handoff.md` 和 `README_AI.md` 时，squash merge PR #90。建议 commit title：`docs: add live V4 development handoff`。
4. final-head CI 和 review PASS 不需要再次修改 handoff。它们是当前 exact HEAD 的外部验证事实。
5. 合并后立即转入下面的 B 流程，不再继续引用 PR #90 的旧 head 作为 candidate。

### B. PR #90 已 MERGED，或完成 A 后

1. 读取 `v4/rc5-native-core` 当前 HEAD/tree，作为新的正式 candidate identity。
2. 读取 PR #81 当前 head 和 synthetic merge commit/tree，要求 PR #81 head 等于当前 `v4/rc5-native-core` HEAD，synthetic merge tree 等于正式 candidate tree。
3. 等待并确认这个正式 candidate exact-head repository CI 四平台和 aggregate `policy-tests` 全绿。该 CI 结果保存在 GitHub，不为了把 PASS 写入 handoff再次修改 candidate。
4. 检查 `docs/v4/host-smoke.json` 仍是 `PENDING`、`results={}`。
5. 做 non-mutating installed-package identity re-audit。实际 Host build 以当时观测为准。
6. 如果已安装 package 不能证明 exact candidate identity，再使用官方 CLI 做 exact local Marketplace reinstall，并重新 Doctor。
7. fresh Codex session 后执行正式 N0，只执行 N0，不提前启动 N1。
8. N0 通过后更新外部 campaign evidence，再准备 N1。

任何接手者都不能因为本 handoff 内保留了旧 candidate SHA，就跳过当前 Git HEAD 和 PR #81 的重新读取。

## 17. Modification Log

### H001 2026-08-22T21:58Z：建立正式候选可继承的实时 handoff

触发：用户要求把开发上下文事无巨细写入仓库，并规定今后每次修改都同步 handoff。

修改前正式候选：`v4/rc5-native-core@4530382427556f20fe8fd57e56108016d5f2a3e2`，tree `2d6499de095cfde124c85a9cc195e014af1bbf75`。

工作分支：`docs/v4-live-development-handoff`。

改动文件：新增 `docs/v4/development-handoff.md`。

目的：把聊天和临时外部上下文中容易丢失的实时开发状态转为仓库内持续交接入口，记录架构、upstream V2 技术背景、历史 Host evidence、PR #88/#89、当前 release gates、错误推理禁区、验证要求和下一步。

明确未变化：production runtime、contracts、Host machine gate、WriterLease、WorkGraph、scheduler、managed profiles、Plugin package payload、Hook path 均未修改。

初始 handoff commit：`3a6daae346fdebb16405ac0c4dcce30eaaa7bd67`，message `docs: establish live V4 development handoff`。

注意：旧工作分支上的 `6398444ee184a268980ebee39d7449f8b6ebfd60` 是一次未进入正式候选的 handoff 尝试，只保留为历史痕迹。正式 authority 以 PR #90 和后续合入候选的版本为准。

### H002 2026-08-22T22:02Z：记录 PR #90 和首轮 handoff validation

触发：handoff 初始版本进入 PR #90 后完成首次完整 repository validation，需要把实际 PR、CI 和 review 状态写回持续交接记录。

PR：`#90 Add live V4 development handoff`。

base：`v4/rc5-native-core@4530382427556f20fe8fd57e56108016d5f2a3e2`。

初始 PR head：`3a6daae346fdebb16405ac0c4dcce30eaaa7bd67`。

首轮 workflow：`32601201287`。

首轮验证结果：Ubuntu Python 3.11 PASS，Ubuntu Python 3.12 PASS，macOS Python 3.11 PASS，Windows Python 3.11 PASS，aggregate `policy-tests` PASS。各平台 full pytest、managed Agent profile lifecycle、manifest validation、generated package-integrity 和 Ruff 均 PASS；Ubuntu 3.11 的 pinned official OpenAI Plugin validator PASS。

首轮 review：PR #90 review threads 为 0。

首轮 diff：只有 `docs/v4/development-handoff.md`。

本次实际改动：只更新 `docs/v4/development-handoff.md`，加入 PR #90、首轮 CI、review、package boundary 和 final-head 执行顺序。

明确未变化：production runtime、machine contracts、Plugin package payload、WriterLease、WorkGraph、scheduler、profiles、Hook、tracked Host results 均未变化。

同步 commit：`7230a9c12158e3601eb7bb2a01f7a412c44864d9`，message `docs: record handoff PR validation`。

该同步 commit 对应 final-head workflow：`32601391850`。四个平台和 aggregate `policy-tests` 已验证 PASS。

### H003 2026-08-22T22:06Z：修复 handoff 合并后自失效的下一步流程

触发：PR #90 final-head CI 全绿后，review 提出 P1。原“下一步严格顺序”只描述 PR #90 仍 OPEN 的状态。文件一旦按预期合入 `v4/rc5-native-core`，继续要求下一位接手者等待并合并 PR #90 会立刻变成无效流程，还可能让接手者继续使用旧 `453038...` candidate identity。

根因：handoff 把一次性 PR 状态写成了无条件未来指令，没有把 pre-merge 和 post-merge 状态机分开。

实际修复：更新第 2、14、16 节。明确旧 SHA 只作为历史基线；接手时先读取 PR #90 当前状态；OPEN 走 A 流程完成 PR；MERGED 直接走 B 流程，从 `v4/rc5-native-core` 当前 HEAD/tree 和 PR #81 synthetic merge tree 重新建立 candidate identity。

改动文件：仅 `docs/v4/development-handoff.md`。

明确未变化：production runtime、machine Host contracts、Plugin package payload、WriterLease、WorkGraph、scheduler、managed profiles、Hook、N0 到 N8 tracked results 均未变化。

修复 commit：`4011a4eea97844e4b1cff620a244540d9fe7230f`，message `docs: make V4 handoff merge-state aware`。

验证：workflow `32601607606` 四个平台和 aggregate `policy-tests` 全部 PASS。该结果属于不改变仓库内容的 CI evidence，因此无需为了重新写入 PASS 再制造新 commit。

### H004 2026-08-22T22:12Z：关闭 handoff 自更新循环并建立仓库入口

触发：H003 CI PASS 后，review 新增两个 P2。

P2 一指出原规则容易被理解为 post-commit CI 也必须写回 handoff。这样每次写入 CI 结果都会产生新 HEAD，新 HEAD 又需要新 CI，再产生下一次写入，无法稳定冻结 exact candidate。

P2 二指出 handoff 虽然存在，但仓库既有 AI 入口 `README_AI.md` 没有链接它。新会话可能只读 AI Reference 后直接开发，从而错过最新 candidate、recent remediation、Host gate 和风险信息。

根因：第一处把“仓库内容修改”和“非修改性验证事件”混成一个记录要求；第二处只创建了 continuity artifact，没有把它接进已有 onboarding path。

实际修复：

1. 第 1 节明确规定仓库内容修改必须同步 handoff，但 CI、review、PR metadata、Host evidence、安装审计、人工观察属于非仓库修改事实，可以外部保存并在下一次真实内容修改时顺带补录，禁止为了记录这些结果单独改变 candidate。
2. `README_AI.md` 顶部新增 live handoff 入口，要求修改 V4 前先阅读 `docs/v4/development-handoff.md`，同时声明 handoff 不替代 machine contracts 或 external Host evidence。
3. 第 2、13、14、16 节同步更新 PR #90 文档范围、package 边界和可冻结的 CI 流程。

改动文件：`README_AI.md`、`docs/v4/development-handoff.md`。

`README_AI.md` 修改 commit：`608ff7255454221c4c4555dd75f4219ae610eb33`，message `docs: link live V4 development handoff`。随后本 handoff 在同一 PR 下一提交补齐本次改动记录，满足单文件 GitHub 写入接口下的同步要求。

明确未变化：production runtime、machine Host contracts、Plugin package payload、WriterLease、WorkGraph、scheduler、managed profiles、Hook、tracked N0 到 N8 results 均未变化。

H004 handoff commit：`a2ca4666187584cd5fe78f290451b86203b3d57c`，message `docs: close live handoff workflow gaps`。

验证要求：本次修改后的 PR #90 final head 必须重新通过四平台 repository matrix 和 aggregate `policy-tests`。该最终 PASS 可以留在 GitHub 作为 exact-head evidence，不需要再修改 handoff。review 中 H003 P1 和本轮两个 P2 只有在最终文件内容与 CI 都确认后才允许 resolve。

### H005 2026-08-22T22:15Z：修复 README 末尾换行回归

触发：H004 final-head workflow `32601827492` 在 Ubuntu Python 3.11、Ubuntu Python 3.12 和 macOS Python 3.11 同步失败 full pytest。Ubuntu 3.11 日志显示唯一失败为 `tests/test_public_surface_regressions.py::test_readme_files_are_valid_basic_text_files`，结果 `1 failed, 526 passed`。

根因：通过 GitHub 单文件写入 `README_AI.md` 时，提交内容末尾缺少 newline。现有公共 surface 回归测试要求所有 README 都是有效 UTF-8 文本、非空、无 NUL，并且 `text.endswith("\n")`。新增入口文字本身没有触发语义合同失败，失败来自文本文件格式不符合既有仓库规范。

实际修复：保持 `README_AI.md` 的 live handoff 入口内容不变，只恢复文件末尾换行。没有删除或放松现有回归测试。

README 格式修复 commit：`4ad6be78ebb79bb54b427ef37180b73249244db8`，message `fix: preserve README trailing newline`。

改动文件：`README_AI.md`，随后本 handoff 在同一 PR 下一提交记录根因和修复。

明确未变化：production runtime、machine Host contracts、Plugin package payload、WriterLease、WorkGraph、scheduler、managed profiles、Hook、tracked N0 到 N8 results 均未变化。

验证要求：本 H005 handoff 更新后的 PR #90 final head 必须重新通过四平台 repository matrix 和 aggregate `policy-tests`。根据第 1 节规则，最终 PASS 只保存在 GitHub CI，不再为了写入结果产生新 candidate HEAD。
