# GPT-6 Refactor Design Record

Status: GRILLING COMPLETE — AWAITING SHARED-UNDERSTANDING CONFIRMATION
Started: 2026-09-05

This is the development decision record for the current GPT-6-era refactor of
`subagents-dispatch`. It records the design tree, user decisions, supporting facts,
and unresolved branches while the design is being grilled. It is not a runtime
contract, release gate, Host qualification artifact, or compatibility promise.

Do not implement the refactor from this document until the grilling frontier is empty
and the user confirms shared understanding.

## Current source baseline

- Repository: `subagents-dispatch`
- Current local source: `c6c663ec68b30bbcab5f18fa7b889e042ddff3ce`
- Local `main` and `v4/rc5-native-core` both point at that source.
- Remote `origin/main` and `origin/v4/rc5-native-core` remain at `dacc8253383c345fbb069b27e094facd28f112ed`.
- The local source contains the two unpushed per-probe Host qualification commits:
  `27a86db` and `c6c663e`.
- Working tree was clean when grilling started.

## Already-settled project constraints

These are treated as existing project truth unless the user explicitly reopens them:

- Public product surface remains centered on `Orchestrate` and `Doctor`.
- Main owns user intent, decomposition, dispatch judgment, integration, acceptance,
  irreversible external effects, and the final response.
- WorkGraph / WorkUnit own responsibility and acceptance truth.
- ExecutionBinding owns one concrete managed attempt/generation.
- WriterLease remains the single canonical-workspace managed writer authority.
- Host lifecycle truth is native Host truth; `UNKNOWN` fails closed.
- No second Agent runtime, daemon scheduler, heartbeat, occupancy ledger, or persistent
  lifecycle authority is introduced.
- Pre-1.0 internal compatibility is not preserved merely to keep retired designs alive.
- Verification starts with the smallest behavior-sensitive tests and expands only for
  failures, cross-module effects, architecture changes, or final integration gates.
- No Tag or GitHub Release is created without explicit user authorization.

## Evidence established before grilling

- Current production roles are Reader=Luna Max, Worker=Luna Max,
  Investigator=Terra High, Solver=Sol High, Advisor=Sol High.
- Current implementation ships five persistent custom Agent TOML profiles and ties
  profile installation, Doctor, updates, calibration, Host qualification, and release
  evidence to those profiles.
- Profile/calibration-related source and tests account for roughly 7k lines; this is a
  candidate obligation, not proof that it should be deleted.
- `release_evidence_v4.py` is intentionally not an early simplification target because
  its recent complexity closes real provenance failures and binds release authority.
- `state_storage.py`, WorkGraph, ExecutionBinding, WriterLease, and `UNKNOWN` currently
  have clear safety ownership and are not presumed simplification targets.
- Focused routing/model/runtime/Final Review baseline: 35 tests passed.
- Focused updater baseline: 7 tests passed.
- `plugin_update.py` still lacks regression coverage for same-semver/different-source
  drift and post-switch verification failure rollback; that is a separate correctness
  track, not a reason to mix updater fixes into routing refactoring.

## Design tree

### Frontier 1 — root product and routing decisions

Status: SETTLED

- Q1 — Release timing: **B**. This refactor is part of the architecture for the first
  public `1.0.0`; do not publish the current pre-refactor architecture first.
- Q2 — Priority order: accepted as
  `correctness/safety/authority > conceptual simplicity > user friction > token/API-equivalent cost > latency`.
- Q3 — Parent model: **B**. `subagents-dispatch` remains parent-model agnostic. Astra is
  not a prerequisite for invoking Orchestrate. Parent runtime capability may affect
  deduplication/admission but does not define product eligibility.
- Q4 — Production routing: **A**. Semantic roles keep deterministic production model /
  effort routes. The dynamic decision is whether to delegate and which semantic role is
  warranted, not an additional per-task model-selection layer.
- Q5 — Semantic roles: keep all five roles: Reader, Worker, Investigator, Solver, Advisor.
  Current design direction removes Terra from the production model ladder while keeping
  Investigator as a semantic responsibility. Exact historical/experimental Terra scope
  remains a later decision.
- Q6 — Astra admission: accepted strict gate. Task size, file count, one failure, low
  confidence, or spare capacity are never sufficient. Solver/Astra requires unresolved
  material judgment that cannot safely be settled before writing, remains coupled to the
  implementation, and gains concrete value from independent delegation. Advisor/Astra
  requires genuinely independent judgment/review value. Prior Astra/Solver use is not an
  Advisor trigger. When Main already has equivalent Astra capability, capability uplift
  alone cannot justify another Astra child.
- Q7 — Managed profile implementation: **B**. Five persistent Host Agent profiles are not
  protected as a compatibility requirement. If real Host evidence proves that fewer or
  zero persistent profiles preserve the required semantic instructions, read-only / write
  boundary, leaf-agent constraint, exact model/effort route, and runtime attestation at
  equal or stronger safety, the implementation may be reduced or removed. The decision
  must follow Host proof rather than line-count pressure.

Derived constraints from Frontier 1:

- The public Skill entry remains fixed; this is a routing-generation refactor inside the
  existing product rather than a second Astra-specific Plugin or Skill.
- Five semantic roles and Host profile count are separate design dimensions.
- A deterministic role route does not imply automatic escalation from Luna to Sol to
  Astra; Astra remains an exceptional gated lane.
- Main capability must not be represented indirectly by `reference_role=solver`; parent
  capability and child semantic route are separate concepts.
- No implementation begins until all grilling frontiers are settled and shared
  understanding is explicitly confirmed.

### Frontier 2 — routing semantics and profile obligations

Status: SETTLED

- Q8 — Production route: Reader=Luna Max, Worker=Luna Max, Investigator=Sol High,
  Solver=Astra High, Advisor=Astra Light. The user explicitly chose a lower-effort
  Advisor than Solver to control review cost. Official Codex UI terminology now uses
  Light / Medium / High / Extra High / Max and exposes Ultra for eligible accounts and
  supported models; the Codex machine/config values remain low / medium / high / xhigh /
  max / ultra. Therefore the intended machine route for Advisor is Astra `low`; do not
  create a project-private `light` effort value.
- Q9 — Terra scope: **A**. Terra exits current production routing and receives no special
  first-class current calibration status. Historical commits, immutable evidence, and
  prior benchmark records remain intact. A generic experiment mechanism may still test
  Terra when explicitly chosen; current product policy does not privilege it.
- Q10 — Parent capability dedup: accepted responsibility-oriented dedup. Main capability
  suppresses a child only when capability uplift is the child’s only value. Independent
  responsibility, useful parallelism, context isolation, or independent-review value may
  still justify a child even when Main has equal or greater model capability.
- Q11 — Role contracts: keep all five role-specific behavioral contracts even if the
  eventual persistent Host profile count is reduced or becomes zero. Transport/configuration
  may change; Reader/Worker/Investigator/Solver/Advisor decision rights, stop conditions,
  authority, and behavioral boundaries remain product semantics.
- Q12 — Astra re-entry: accepted strict material-basis rule. Every new Astra dispatch for
  the same WorkUnit or review obligation must bind a new material basis such as candidate
  mutation, new decisive evidence, changed scope/contract, or a newly created independent
  review obligation. Uncertainty, mediocre output, or trying another expensive model pass
  is insufficient. Existing compute-expansion consent remains an outer user-consent bound,
  not a substitute for technical admission.
- Q13 — Final Review: remains consequence-driven and independent of implementation history.
  Prior Solver/Astra use, diff size, number of files, or correction count are not Final
  Review triggers. Existing consequence triggers continue to decide whether independent
  review is required.

Derived constraints from Frontier 2:

- The production model ladder is now conceptually Luna -> Sol -> Astra, but it is not an
  automatic escalation ladder. Semantic role admission precedes model selection.
- Investigator remains a role while Terra no longer owns a production tier.
- Solver and Advisor both use Astra as the intended model family but deliberately have
  different cost/admission profiles; Advisor is not simply Solver in read-only mode.
- Model capability and independent-review value are separate routing dimensions.
- Expensive-model repetition must be justified by changed task truth, not by lack of
  confidence in the previous expensive call.

### Frontier 3 — executable Astra policy, fallback, and routing failure semantics

Status: SETTLED

- Q14 — Reasoning vocabulary: the user's Light / Medium / High / Extra High / Max / Ultra
  names describe the current Codex UI, not a project-owned runtime enum. Machine policy
  follows OpenAI Codex's `ReasoningEffort` protocol directly. The current known variants
  are `None`, `Minimal`, `Low`, `Medium`, `High`, `XHigh`, `Max`, `Ultra`, plus
  `Custom(String)` for a future model-defined non-empty value. Their wire values are
  `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`, `ultra`, or the custom
  string. Therefore Advisor is `gpt-6-astra / low` and Solver is
  `gpt-6-astra / high`; no private `light` or `extra-high` enum is introduced.
- Q15 — Fallback: **none**. If the exact role route is not available, do not silently
  substitute another model or effort. The affected dispatch fails closed; Main may keep
  safe work itself or make a new semantic routing decision, but the original role is not
  relabeled as successfully executed.
- Q16 — Solver admission: strict logical AND. All material-judgment, inseparability,
  write-coupling, and concrete delegation-value conditions must hold. Importance or risk
  labels do not waive a missing condition.
- Q17 — Advisor scope: Advisor is **Final Review only**. Remove ordinary one-shot material
  judgment from current Advisor semantics. Main owns ordinary decisions; Investigator/Sol
  may gather and synthesize evidence but does not replace Main's product/architecture
  authority.
- Q18 — Astra count: no numeric ceiling. Control usage through strict first-admission,
  required new material basis for every re-entry, consequence-driven review, and the
  existing material-compute-expansion consent boundary.

#### Official-source facts for Q19

- Current Codex documentation distinguishes user-facing intelligence labels from config
  values: Light / Medium / High / Extra High / Max are normal UI levels; Ultra is available
  only for eligible accounts and supported models. `model_reasoning_effort` uses the
  machine values low / medium / high / xhigh / max / ultra.
- OpenAI API model pages and Codex Host capability are not the same authority surface.
  The current GPT-6 Astra API model page may advertise a narrower API effort set than the
  Codex product exposes through its model catalog and account/runtime feature surface.
- OpenAI Codex protocol defines known efforts through Ultra and deliberately accepts
  future non-empty custom effort values. Therefore a static project enum is not a safe
  future Host-capability oracle.
- OpenAI Codex `spawn_agent` builds its visible model/effort guidance from the current
  `ModelPreset` catalog. A requested model must occur in the currently available models
  for the active multi-agent backend, and a requested effort is validated against that
  selected model's current `supported_reasoning_levels`; unsupported values fail rather
  than being silently downgraded.
- Official Codex custom-agent precedence is significant: when a custom Agent TOML pins
  `model` or `model_reasoning_effort`, the file value takes precedence. Otherwise each
  field resolves independently from explicit spawn value -> `[agents]` default -> parent.
  If an explicit spawn changes model without an explicit/configured effort, the selected
  model's default effort is used.
- Current public `list_agents` V2 schema exposes canonical agent name and lifecycle status,
  not model/effort. A successful spawn request therefore does not by itself prove the
  realized route. Requested, accepted, and observed route truth must remain distinct.
- Local read-only observation on 2026-09-05 used `codex-cli 0.151.0`. Its live
  `codex debug models` catalog exposed Sol/Terra through Ultra and Luna through Max. The
  local config selected `gpt-6-astra / medium`, while that debug catalog did not currently
  list Astra. This is concrete evidence that configured selection alone must never be
  promoted to a Host-capability or runtime-observation claim.

Q19 authority hierarchy: **ACCEPTED**.

1. Product policy owns the exact route the Plugin requires for each semantic role; it is
   intent, not Host capability evidence.
2. The current callable Codex Host surface plus its live model catalog owns pre-spawn
   executability: exact model, exact supported effort, applicable multi-agent backend, and
   exact controls available for this turn/session. If this cannot prove the requested
   route is selectable, the dispatch does not run.
3. The exact spawn request/accepted Host response proves only what was requested/accepted;
   it is not realized runtime proof.
4. Host-produced runtime/session metadata owns realized child model/effort when exposed.
   Public native metadata is preferred. An exact Host-produced rollout/session record may
   fill a field the public surface omits, but cannot override a conflicting public Host
   fact. Conflict or insufficient observation remains UNKNOWN/quarantined whenever the
   claim requires runtime attestation.
5. API documentation, repository snapshots, `astra-advisor`, and `sol-advisor` are design
   references and compatibility guidance. They never override the current callable Codex
   Host/catalog for a concrete dispatch.

- Q20 — Exact route unavailable: accepted asymmetric failure semantics. Solver is an
  optional delegation lane, so an unavailable exact Solver route fails that dispatch
  closed and Main may reclaim the responsibility. A required Advisor Final Review is an
  acceptance obligation: if exact `gpt-6-astra / low` is unavailable, do not substitute
  another model/effort or claim reviewed acceptance; keep review pending /
  `INSUFFICIENT_EVIDENCE`. The same condition blocks the formal release review gate.
- Q21 — Ultra/proactive Host delegation: accepted managed-custody rule. Any delegation
  participating in Orchestrate must pass through the canonical managed route and cannot
  gain WorkUnit ownership, ExecutionBinding authority, WriterLease, or acceptance through
  an unmanaged generic/proactive spawn. If a parent/Host combination cannot keep native
  proactive delegation inside that custody boundary, Main-only remains available but
  delegated Orchestrate fails closed. Real Host evidence must prove the boundary where
  Ultra/proactive behavior is material.
- Q22 — Investigator admission: accepted. Reader/Luna owns bounded factual retrieval and
  tracing. Investigator/Sol owns bounded read-only synthesis where multiple facts or
  code paths must be combined into a technical conclusion after desired semantics are
  already settled. File count, one weak Reader result, long context, spare capacity, or a
  generic request to inspect more carefully are not Investigator admission reasons.
- Q23 — Effort routing: accepted fixed role effort. Solver remains Astra High and Advisor
  remains Astra Low for every production task. Security, migration, concurrency, diff
  size, or task risk do not cause per-task effort escalation. A future global effort
  change requires explicit policy revision plus appropriate qualification/calibration;
  it is not a runtime override.

Derived constraints from Frontier 3:

- Production policy uses Codex protocol/wire `ReasoningEffort` values rather than UI
  labels or a duplicated project enum. Current live model/catalog support still decides
  whether a selected effort can actually be used.
- No role has a runtime fallback model or fallback effort.
- Advisor is Final Review only and is an acceptance lane, not a general-purpose thinking
  assistant.
- Solver is optional execution delegation and may be reclaimed by Main when unavailable;
  required review cannot be reclaimed as a fake independent review.
- Host-native proactive delegation never bypasses WorkUnit/ExecutionBinding/WriterLease
  custody.

## Local development workspace constraint

The user requires all `subagents-dispatch` development to live under the single local
project root:

`/Users/qunqing/2026-Project-Agent/subagents-dispatch`

Do not create new sibling project/worktree directories such as
`/Users/qunqing/2026-Project-Agent/subagents-dispatch-*`. Any retained Git worktrees must
live under the canonical project root (for example a locally ignored `.worktrees/`
directory), and future implementation should prefer the canonical working tree unless an
isolated worktree is materially necessary.

Local consolidation completed during grilling:

- The four temporary worktrees for `feat/1.0-contract-close`, `feat/gpt6-routing`,
  `audit/per-probe-qualification`, and `audit/updater-identity` were all confirmed clean.
- They were removed with `git worktree remove` after their branch refs and commits were
  verified. The Git branches/commits were preserved; only the temporary working directories
  and worktree registrations were removed.
- The local `.worktrees/` directory was removed after it became empty.
- `/Users/qunqing/2026-Project-Agent/subagents-dispatch` is now the only registered Git
  worktree and the only `subagents-dispatch*` directory directly under
  `/Users/qunqing/2026-Project-Agent`.

### Frontier 4 — remaining routing/product boundaries

Status: SETTLED except that Q26 reopened the Final Review model/role design.

- Q24 — Parent capability ordering: accepted the recommendation to use a small, explicit,
  versioned production coverage relation across the supported Luna / Sol / Astra routes.
  Do not build a universal numeric model score. Unknown/future models have unknown coverage
  until explicitly added by policy and qualification.
- Q25 — Same-family review: allowed in principle. An Astra-produced candidate may receive
  an independent Astra Final Review when the chosen Final Review policy calls for it,
  provided the review is a fresh execution bound to the exact candidate and the reviewer
  did not participate in implementation. This remains subject to the reopened Q26 review
  tier/role design.
- Q26 — Final Review tiering: **REOPENED / SUPERSEDES the earlier single-route assumption**.
  The user wants at least two Final Review capability levels because Astra High is too
  expensive to use for every review. Ordinary Final Review should be supportable by
  Sol High, while Astra High is the framework's highest-responsibility review level. The
  user also raised the possibility that Solver and Advisor could dynamically carry review
  work. This conflicts with earlier fixed per-role model mapping and with Solver's current
  write-coupled semantic contract, so the exact role/model boundary must be grilled before
  implementation.
- Q27 — Role visibility: **B**. Reader / Worker / Investigator / Solver / Advisor remain
  stable product vocabulary visible in architecture, diagnostics, and route rationale,
  but are not separate public entrypoints or user-selected orchestration modes.
- Q28 — Profile simplification timing: **B**. If real Host proof supports reducing or
  removing persistent profiles, perform that as a separate verified implementation slice
  inside the same pre-1.0.0 release line rather than shipping the known removable
  first-use/profile lifecycle in the first public release.

Derived constraints from Frontier 4:

- Parent capability dedup may use only explicitly qualified production coverage, never a
  guessed global model ranking.
- Final Review cost needs its own bounded selection rule; the previous assumption that
  every Final Review is Advisor/Astra Low is no longer current design truth.
- Solver's write-coupled responsibility and Advisor's review-only responsibility remain
  intact until the next frontier explicitly decides otherwise.

### Architecture reconsideration — three-role candidate

Status: OPENED BY USER. This reopens the assumption that five semantic roles are the
desired end state. Earlier decisions that depend on five distinct semantic roles are now
provisional until this branch is resolved.

The user proposed a simpler three-role product model:

- **Work role**: Luna Max. Owns ordinary bounded implementation/execution work.
- **Decision role**: Sol, with Plugin-selected effort. Sol Medium handles light decisions;
  Sol High handles material/major decisions.
- **Acceptance role**: Astra High. Acts as the highest-responsibility reviewer/acceptance
  authority and is reserved for the closing acceptance of genuinely complex/high-consequence
  tasks rather than routine work.

Most ordinary tasks should use only Work=Luna Max plus Decision=Sol Medium/High as needed.
Astra High should be rare because of quota/token cost and should not be inserted merely
because a task is non-trivial.

The user also proposed a strict separation between Main and managed-role routing:

- The user's Main model and Main `ReasoningEffort` selection may influence planning and the
  orchestration strategy.
- Main model/effort must not rewrite, inherit into, weaken, or otherwise determine the
  managed Work / Decision / Acceptance role model-effort routes.
- Managed role model/effort is owned by Plugin routing policy plus live Host capability
  checks, so invoking Orchestrate from a weaker Main does not silently degrade managed
  execution/review quality.
- Main remains parent-model agnostic as a product entry point. The unresolved issue is how
  much decision authority a weak Main may exercise before it must delegate to Decision.

This proposal reopens at least these prior decisions:

- Q5/Q11: whether Reader+Worker and Investigator+Solver can collapse into Work+Decision
  without losing required authority boundaries.
- Q8/Q17/Q26/Q29-Q34: exact Advisor/Solver/Final Review semantics and model mappings are no
  longer settled because Acceptance may become a dedicated Astra role while Decision/Sol
  handles ordinary judgment and possibly ordinary review.
- Q10/Q24: parent capability dedup may become less important if managed-route quality is
  intentionally independent of Main strength, though Main must still avoid duplicate work
  and unnecessary child use.

No implementation decision follows yet. The three-role model must first prove that it
preserves all required safety/authority obligations with fewer concepts.

### Frontier 5 — three-role architecture

Status: SETTLED

- Q35 — Work collapse: accepted. Reader and Worker collapse into one semantic **Work**
  role backed by Luna Max. Read versus write is no longer encoded by distinct Agent role
  identity; it is owned by the WorkUnit/responsibility record through `intent`,
  `mutation_authority`, `write_scope`, decision boundary, and acceptance.
- Q36 — Decision collapse: accepted. Investigator and Solver collapse into one semantic
  **Decision** role backed by Sol. Read-only investigation/synthesis versus bounded
  judgment-coupled implementation is represented by the responsibility contract rather
  than by separate Agent role identities. When Decision receives write authority, the
  earlier strict Solver admission predicates still apply: unresolved material judgment,
  inability to settle it safely before writing, continued judgment/write coupling, and
  concrete delegation value must all hold.
- Q37 — Decision effort: accepted two-class route only. Sol Medium is for local/reversible
  technical judgment that does not alter core architecture, contract, authority, or
  persistent semantics. Sol High is for material decisions affecting architecture,
  contract, compatibility, ownership, persistent semantics, security/authorization, or
  similarly consequential boundaries. File count, task size, failure count, Main model,
  or a numeric risk score do not choose effort. No per-task Low/XHigh/Max/Ultra Decision
  routes are introduced.
- Q38 — Main decision authority: accepted strong separation. Main owns user intent,
  decomposition, orchestration, integration, ordinary local coordination choices, and
  acceptance sequencing. A responsibility that qualifies as a formal material Decision
  is delegated to the fixed Sol Decision lane regardless of whether Main itself is weak,
  Sol, or Astra. Main model/effort therefore cannot weaken managed-role quality or silently
  absorb a required managed Decision merely because Main happens to be strong.
- Q39 — Parent capability dedup: accepted removal. This supersedes Q24 and the earlier
  plan for a Luna/Sol/Astra capability-coverage graph. Delegation is controlled by useful
  independent responsibility, role admission, non-duplication, and acceptance/review
  obligations. The Plugin does not compare Main model strength with managed child model
  strength to decide whether a required role should exist.
- Q40 — Review split: accepted. Ordinary independent final review is a **Decision / Sol
  High** responsibility. Highest-consequence closing assurance is **Acceptance / Astra
  High**. Both are fresh, read-only, exact-candidate-bound review responsibilities and
  cannot fix their own findings. The generic phrase `Final Review` must no longer imply a
  single model/role route.
- Q41 — Acceptance admission: accepted narrow consequence set. Acceptance/Astra High is
  reserved for security or authorization boundaries, data integrity, critical concurrency
  or ownership semantics, persistent-state/cross-version migration, irreversible external
  effect safety, formal release acceptance, or an explicit user request for highest/Astra
  assurance. Ordinary feature work, refactors, public API changes without those higher
  consequences, diff size, file count, retries, or prior Sol usage do not qualify by
  themselves.
- Q42 — Consequence not complexity: accepted. Task complexity is not an Acceptance trigger.
  A complex low-consequence candidate may stop at Decision/Sol High review; a simple but
  authorization-sensitive candidate may require Acceptance/Astra High.
- Q43 — Acceptance timing: accepted strict temporal boundary. Acceptance does not exist
  before Candidate Ready. Main must first complete integration, deterministic/reproducible
  verification, candidate binding, and trigger classification. Astra High must not be used
  for early planning, mid-implementation advice, speculative pre-review, or repeated
  confidence checks.
- Q44 — Public vocabulary: accepted. Work / Decision / Acceptance are stable product
  vocabulary visible in architecture, diagnostics, and route rationale, but remain internal
  orchestration roles behind the fixed public `Orchestrate` and `Doctor` entry points. Users
  do not directly select a role to bypass admission policy.

Derived architecture after Frontier 5:

```text
Main
  user intent / decomposition / orchestration / integration
    |
    +-- Work       -> Luna Max
    |     inspect or implement according to Responsibility Record authority
    |
    +-- Decision   -> Sol Medium | Sol High
    |     investigate, decide, judgment-coupled implement, or standard review
    |
    `-- Acceptance -> Astra High
          highest-consequence closing assurance only, after Candidate Ready
```

This supersedes the previous five-role target mapping and the parent-capability coverage
graph. Five-role history remains relevant evidence for migration/tests, not the intended
1.0.0 production architecture.

### Frontier 6 — three-role naming, Main quality floor, and review ownership

Status: SETTLED except Q47 profile materialization, which was deferred for official-source
research and is resolved below as a research-backed recommendation awaiting explicit user
acceptance.

- Q45 — Product vocabulary: replace the abstract Work / Decision / Acceptance presentation
  with a personified bottom-up team. Chinese UI/documentation uses **程序员 / 产品经理 / 部门总监**.
  English uses the corresponding job-title vocabulary (currently recorded as Programmer /
  Product Manager / Department Director; exact English display wording may be polished later
  without changing the semantic roles). The personification is a presentation/product-language
  choice, not a change to authority semantics.
- Q46 — One Decision role: accepted. Product Manager remains one semantic role even though it
  has two allowed Sol effort routes. Medium versus High is an execution parameter chosen by the
  Plugin's two-class decision policy, not a fourth semantic role.
- Q48 — Weak-Main routing quality: accepted a bounded Product Manager / Sol Medium routing
  check when decomposition/admission is genuinely ambiguous. The check advises on missing
  material decisions, role mismatch, and acceptance triggers; it does not own WorkGraph or
  mutate orchestration state. Main remains the orchestration authority.
- Q49 — Routing-check admission: accepted consequence/ambiguity triggers rather than Main
  model strength. Clearly bounded low-consequence single-work responsibilities may skip the
  check. Cross-module semantics, unclear responsibility structure, public contracts,
  persistence, security/authorization, concurrency/ownership, migration, or likely material
  judgment can admit the check. Main=Luna does not itself trigger it; Main=Astra does not
  suppress it.
- Q50 — Routing-check scope: accepted. A Product Manager routing check does not silently widen
  itself into the later formal Decision responsibility. Main must establish the concrete
  WorkUnit/responsibility first. Any same-child continuity must use an existing legal lifecycle
  mechanism and cannot arise from prompt-driven self-expansion.
- Q51 — Acceptance trigger ownership: accepted deterministic trigger extraction plus Main
  confirmation. Department Director/Astra never decides its own admission. Candidate metadata
  and accepted task/change truth determine whether the narrow highest-consequence trigger set
  is present; Main confirms the set before dispatch.
- Q52 — Standard review: accepted consequence-driven Product Manager / Sol High review, not a
  mandatory review after every code change. Small low-consequence work with sufficient
  deterministic verification may finish without an independent review.
- Q53 — Final authority: accepted. Department Director/Astra High supplies the highest-capability
  independent assurance judgment but does not become a second Main. Main still owns user intent,
  integration, acceptance sequencing, and the final response; a reviewer cannot rewrite the
  user's goal, scope, product semantics, or permissions.

#### Q47 official-source research — custom-agent/profile materialization

Research basis: current OpenAI Codex subagent documentation and current `openai/codex` source.

Facts established from official documentation/source:

- `spawn_agent` can take an explicit model and reasoning effort. Current Codex source validates
  those values against the live model catalog before spawning; an unavailable model/effort is
  rejected rather than silently downgraded.
- A custom Agent TOML is still the native role/configuration layer for `name`, `description`, and
  `developer_instructions`, and may also carry ordinary Codex configuration such as model,
  reasoning effort, sandbox mode, MCP/skills configuration, and feature/agent settings.
- When a custom Agent file pins `model` or `model_reasoning_effort`, that file value takes
  precedence. If it omits a field, Codex resolves explicit spawn value first, then `[agents]`
  defaults, then parent value.
- Current Codex role-application source deliberately preserves the caller's already selected
  model and reasoning effort when the role file omits those keys. Therefore one Product Manager
  role file can pin Sol as the model while leaving effort unpinned, and the Plugin can explicitly
  select only `medium` or `high` per dispatch without creating two semantic roles or two profiles.
- Child sandbox/approval state is not proven merely by a role file. Codex reapplies live parent
  turn runtime permission/sandbox choices during child creation; configured `sandbox_mode` is
  therefore intent/default, while effective permission still requires Host observation under
  this project's existing assurance policy.
- `agents.enabled` is a global/session configuration control and MultiAgent V2 has separate
  feature semantics. A custom role can express leaf-agent intent through its configuration
  layer, but effective no-descendant behavior remains a real-Host property to qualify rather
  than a fact inferred from TOML bytes.

Research-backed architecture recommendation:

```text
Programmer profile
  model  = gpt-5.6-luna
  effort = max
  role-specific developer instructions
  configured leaf-agent intent

Product Manager profile
  model  = gpt-5.6-sol
  effort = intentionally UNPINNED
  every managed spawn MUST explicitly select medium or high
  role-specific developer instructions
  configured leaf-agent intent

Department Director profile
  model  = gpt-6-astra
  effort = high
  role-specific review-only developer instructions
  configured leaf-agent intent
```

This yields three semantic roles and three Host profiles. A fourth Product Manager profile is
not structurally needed because current Codex preserves an explicit effort when the role file
does not pin one. Zero persistent/custom profiles is not the preferred current architecture:
explicit model/effort alone cannot carry the complete native role configuration contract we
need (stable role instructions and leaf-agent/tool intent), and moving all of that into a freeform
message would weaken inspectability and Host-native role identity.

The three-profile recommendation still requires focused real-Host proof before publication:
exact role selection, exact realized model/effort, Product Manager Medium/High preservation,
effective permission observation, and no descendant Agent creation/control. Official source
establishes that the design is supported in principle; it does not substitute for those runtime
observations on the release Host.

### Frontier 7 — three-profile materialization and product presentation

Status: SETTLED

- Q54 — Profile count: accepted the research-backed target of **three semantic roles and
  three custom-Agent profiles**. Real-Host qualification still has to prove the exact realized
  route, effort preservation, permission behavior, and leaf-agent boundary before 1.0.0.
- Q55 — External names: Chinese product presentation is exactly **程序员 / 产品经理 / 部门总监**.
  English presentation uses the direct corresponding titles **Programmer / Product Manager /
  Department Director**. These are display/product-language names only. Internal machine
  identities, profile keys, schema values, and authority fields may use stable technical names
  chosen for implementation and are not coupled to localized UI text.
- Q56 — Personification boundary: same as Q55. Personification belongs to visible role names,
  status/rationale, and explanatory architecture language. Runtime contracts, evidence schema,
  ownership, lifecycle, and safety fields stay technical and unambiguous; the roles do not engage
  in theatrical dialogue or role-play that obscures responsibility.
- Q57 — Main presentation: **A**. Main remains Main / 主会话 and is not personified into a
  fourth organizational job title. It remains the orchestration/integration/final-response owner
  outside the three managed team roles.
- Q58 — Product Manager effort: accepted hard pre-spawn invariant. Every Product Manager spawn
  must explicitly carry `medium` or `high`; omission is invalid and must fail before Host spawn.
  Host defaults, parent inheritance, and arbitrary effort overrides are forbidden for this role.
- Q59 — Managed depth: accepted. Programmer, Product Manager, and Department Director are all
  leaf roles. None may create or control another Agent layer. Profile configuration expresses this
  intent, while real Host qualification must prove no descendant materialization/control.
- Q60 — Review precedence: accepted highest-applicable-tier substitution. Ordinary independent
  review is Product Manager / Sol High; highest-consequence acceptance review is Department
  Director / Astra High. When a candidate qualifies for Department Director review, do not also
  run a routine Sol High review by default. Add Product Manager only for a concrete, separately
  justified evidence/decision gap. This prevents stacked review tiers from becoming the normal
  path.

Derived architecture after Frontier 7:

```text
Main / 主会话
  user intent / decomposition / orchestration / integration / final response
      |
      +-- 程序员 / Programmer
      |     gpt-5.6-luna / max
      |     one role; inspect or bounded implement comes from WorkUnit authority
      |
      +-- 产品经理 / Product Manager
      |     gpt-5.6-sol / explicit medium | high
      |     routing check, technical decision, judgment-coupled implement, standard review
      |
      `-- 部门总监 / Department Director
            gpt-6-astra / high
            fresh highest-consequence acceptance review only, after Candidate Ready
```

Display names are localized product vocabulary. Internal schema/profile identifiers remain
technical and stable. Main model/effort never inherits into or rewrites the three managed routes.

### Frontier 8 — route ownership, permission semantics, and internal identity

Status: SETTLED, with Q63 opening a downstream concurrency-safety design branch.

- Q61 — Model/effort ownership: accepted the recommendation that the three custom-Agent
  profiles do **not** own production model/effort. `contracts/policy.json` owns the exact
  permitted managed routes, and `prepare_managed_spawn` must send the exact model and effort
  explicitly on every spawn. A missing or non-policy route fails before Host spawn. This keeps
  parent inheritance out of managed routing and gives model/effort one product owner.
- Q62 — Semantic versus Host permission: accepted the two-layer authority model. WorkUnit /
  Responsibility Record mutation authority is the semantic ceiling for a child. Effective Host
  sandbox/permission is separate runtime evidence and never expands that semantic authority.
  Hard-isolation requirements still fail closed when the Host cannot prove the required boundary;
  broader Host capability does not silently become semantic write authority.
- Q63 — Parallel read-only responsibilities: user explicitly chose to **allow parallelism** even
  when the Host only proves broader write-capable permission for children whose semantic mutation
  authority is `none`. This supersedes the current routing-contract rule that unproven effective
  read-only/isolation always forces the conservative serial path. The implementation must therefore
  add an explicit containment/detection rule for this case; the safety mechanism is not yet settled.
- Q64 — Product Manager effort selection: accepted `medium` as the default Decision tier and
  `high` only for an enumerated material trigger set: architecture boundary, public contract,
  compatibility, ownership/authority, persistent semantics, security/authorization, data
  integrity, concurrency semantics, or migration. File count, task size, retries, or Main model
  do not select High.
- Q65 — No self-escalation: accepted. A Product Manager / Medium routing check that discovers a
  High trigger returns the trigger and evidence to Main. It cannot upgrade itself in place. Main
  establishes the formal Product Manager / High WorkUnit/responsibility; any same-child reuse
  requires a legitimate lifecycle rebinding rather than prompt-driven scope expansion.
- Q66 — One Product Manager profile: accepted. Product Manager / Sol High standard review and
  Product Manager Medium/High decision work share the same custom-Agent profile. Review-specific
  requirements (fresh context, exact candidate binding, semantic read-only, self-fix forbidden)
  belong to the Responsibility Record/review contract, not to a separate review profile.
- Q67 — Department Director mode: accepted one narrow mode only. Department Director is always
  Astra High, fresh, semantically read-only, exact-candidate-bound highest-consequence acceptance
  review after Candidate Ready. It never plans, implements, performs routing checks, supplies
  mid-task advice, or substitutes for ordinary Product Manager review.
- Q68 — Internal identities: accepted the recommended stable machine identities:
  `programmer`, `product_manager`, `department_director`, with Host agent types
  `subagents_dispatch_programmer`, `subagents_dispatch_product_manager`, and
  `subagents_dispatch_department_director`. Localized display strings are not schema values.
- Q69 — Routing-check truth: accepted. Product Manager routing-check output remains a child claim
  / routing-evidence input. Main must verify and project accepted facts into canonical WorkGraph /
  WorkUnit / review-trigger owners before they can drive formal dispatch or acceptance.

Derived constraints from Frontier 8:

- Three custom-Agent profiles own stable role behavior/configuration intent; production
  model/effort comes only from explicit policy-backed spawn parameters.
- Product Manager is one semantic role and one profile across Medium, High, implementation,
  routing-check, and standard-review responsibilities; the responsibility contract supplies the
  narrower mode-specific authority.
- Department Director is structurally unable to become a general-purpose expensive adviser.
- Allowing parallel semantic-read responsibilities under broader Host permission is now an
  explicit product choice, but it requires a separately settled guard because the old
  "unproven read-only => serial" safety rule no longer applies unchanged.

### Frontier 9 — parallel-read safety and calibration simplification

Status: SETTLED

- Q70 — Parallel semantic-read work remains allowed even when Host permission is broader than
  semantic authority. The user did not yet accept the proposed artifact-immutability mechanism
  itself at Q70; that concrete guard is decided by Q79 below.
- Q71 — Workspace mutation during a protected parallel-read batch invalidates the whole batch.
  Do not guess which child caused the change, do not accept a subset of workspace-dependent
  evidence, do not auto-rollback user files, and pause new managed mutation until Main
  re-establishes current workspace truth.
- Q72 — Roles are not singleton Agent instances. Multiple Programmer or Product Manager
  executions may coexist when WorkUnits are independent and normal capacity/writer constraints
  permit it. For the same exact Department Director acceptance obligation, allow only one active
  review execution.
- Q73 — WriterLease remains role-agnostic and binds the exact ExecutionBinding. Programmer or
  Product Manager may hold the one canonical-workspace managed WriterLease when their
  responsibility grants bounded write authority. Department Director never holds WriterLease.
- Q74 — A Product Manager that participated in deciding or implementing the candidate cannot
  satisfy an independent Standard Review of that candidate. Required review uses a fresh Product
  Manager execution with no candidate-creation participation, exact candidate binding, and
  review-only authority.
- Q75 — Keep the existing three-path independent-review assurance model for both Product Manager
  Standard Review and Department Director Acceptance Review: Host-enforced read-only when proven;
  artifact-immutability fallback under positively broader permission when hard isolation is not
  required; otherwise insufficient evidence/fail closed. A broader Host permission never expands
  semantic mutation authority.
- Q76 — Department Director has no runtime review downgrade. If a highest-consequence acceptance
  obligation requires Astra High and that exact route is unavailable, keep the review pending /
  insufficient-evidence. Product Manager/Sol may provide supplementary evidence but cannot
  satisfy the Department Director obligation.
- Q77 — Do not add near-mandatory Product Manager routing preflight solely to defend against a
  hypothetically weak Main. The user expects Main selections ordinarily not to be very weak.
  Preserve the earlier ambiguity/consequence-triggered routing check from Q48/Q49; accept that
  routing judgment retains a limited Main-quality dependency even though managed-role routes do
  not inherit Main model/effort.
- Q78 — Semantic-read responsibilities do not overlap an active canonical-workspace managed
  writer by default. Multiple semantic-read children may overlap each other, but read/write
  overlap waits unless a future Host provides a separately verified immutable/isolated workspace
  boundary.
- Q79 — When semantic-read children run in parallel under broader write-capable Host permission,
  artifact immutability guarding is mandatory: bind the relevant workspace artifact before the
  batch, run the parallel reads with no active managed writer, and re-bind afterward. Host-proven
  effective read-only may use the stronger path without relying on this fallback.
- Q80 — Any workspace artifact drift during such a broader-permission read batch invalidates all
  workspace-dependent batch evidence even when the change may have come from the user. The issue
  is baseline uncertainty, not attribution of blame.
- Q81 — Delete the old profile-only calibration materialization mechanism. New calibration must
  not create temporary challenger TOMLs in the real Agent registry merely to vary model/effort.
  Retire the associated staging/locking/nonce/materialized-agent-identity/recovery obligations
  that exist only for that mechanism.
- Q82 — Calibration may exercise frozen-campaign challenger model/effort routes outside current
  production policy in an evaluator-only path. Production Orchestrate remains policy-exact and
  cannot use experiment-only challenger routes.
- Q83 — Preserve experiment campaign/run provenance validation, but remove fields and validation
  obligations that exist only to prove temporary profile materialization. Simplification deletes
  the mechanism, not evidence integrity.
- Q84 — Keep the safe production installer/Doctor ownership model for the three persistent role
  profiles. Production profile provisioning, drift detection, ownership conflict handling and
  fresh-session/restart semantics remain current product obligations.
- Q85 — Make the three-role transition a clean pre-1.0 break. Do not ship role aliases, profile
  aliases, old manifest migration, or automatic translation from reader/worker/investigator/
  solver/advisor or their calibration materialization schema. Historical evidence remains
  historical.
- Q86 — Any future production managed-route model/effort promotion requires calibration evidence
  plus an explicit product/policy decision and appropriate qualification. Calibration never
  automatically edits production policy.

### Frontier 10 — production policy, installation, updater, and release contract

Status: SETTLED

- Q87 — `contracts/policy.json` becomes the single current three-role route owner. Remove the old
  capability-dedup graph, old fixed-execution-profile projection, five role entries, and dynamic
  effort-routing leftovers. Policy directly owns Programmer, Product Manager, Department
  Director routes plus decision/review/acceptance trigger sets.
- Q88 — Production custom-Agent TOMLs do not pin model or reasoning effort. They own stable role
  identity, role-specific developer instructions, leaf-agent/configuration intent and any other
  genuine role-level Host configuration. Exact route comes only from policy-backed explicit spawn.
- Q89 — Preserve first-use automatic safe profile provisioning. If Plugin-owned profiles are
  safely absent, Orchestrate may provision the three profiles, verify them, and return
  `RESTART_REQUIRED`. Ownership/filesystem conflicts remain `USER_ACTION_REQUIRED` rather than
  being overwritten.
- Q90 — First-public-release Host qualification tests all four executable production routes for
  both exact route materialization (N0) and managed leaf/no-descendant behavior (N1): Programmer
  Luna Max, Product Manager Sol Medium, Product Manager Sol High, Department Director Astra High.
  Future unchanged evidence may use the existing per-probe carry-forward model where valid.
- Q91 — The formal release Final Review/release authority object binds Department Director /
  Astra High only. Product Manager Standard Review may occur during development but cannot satisfy
  the release Final Review gate and does not become the final release-review authority object.
- Q92 — Exact installed package/source identity, not semantic version alone, determines whether an
  installed Plugin is current. Same-semver byte/source drift is a 1.0.0 correctness blocker and
  must no longer report `already current`.
- Q93 — Explicit update becomes transactional. Freeze the exact previous installed identity,
  switch, verify the exact new package, reconcile Plugin-owned profiles, run post-switch gates,
  and on any failure restore and verify the exact previous installed product rather than leaving
  a partial update.
- Q94 — Plugin package and Plugin-owned managed profiles form one updater compatibility unit. The
  update transaction covers profile reconciliation/rollback but does not snapshot or overwrite
  unrelated user Agents, user configuration, or other non-Plugin-owned Codex state.

Derived constraints from Frontiers 9-10:

- The three-role simplification is expected to remove a substantial amount of calibration-only
  profile transaction machinery while retaining current experiment provenance and production
  profile ownership safety.
- Model/effort has one production truth owner: policy-backed explicit spawn. Neither TOML nor Main
  inheritance is a second route source.
- Review assurance and parallel-read containment reuse one artifact-binding concept rather than
  inventing unrelated integrity mechanisms.
- Update correctness and three-profile reconciliation are release-blocking installed-product
  concerns, but remain implementation slices separate from the routing-generation rewrite.

### Frontier 9 — parallel-read containment and calibration simplification

Status: SETTLED

- Q70 — Parallel semantic-read work remains allowed. Q79 below supplies the required
  containment/detection mechanism for broader-permission Hosts; Q70 itself does not restore
  the old conservative-serial rule.
- Q71 — Workspace mutation during a broader-permission semantic-read batch fails closed.
  Do not guess which child caused the change and do not auto-rollback the user's workspace.
  The whole batch's workspace-dependent evidence is invalidated, the affected executions are
  quarantined, new managed mutation pauses, and Main must re-establish current workspace truth.
- Q72 — Semantic roles are not singleton Agent instances. Multiple Programmer or Product
  Manager executions may coexist when their WorkUnits are independent and normal managed-child,
  WriterLease, and duplicate-responsibility constraints allow it. Department Director remains
  single-active per exact candidate/acceptance obligation.
- Q73 — WriterLease remains role-independent and is owned by the exact ExecutionBinding.
  Programmer or Product Manager may hold the one canonical-workspace WriterLease when their
  responsibility grants bounded mutation authority. Department Director never holds one.
- Q74 — A Product Manager that participated in decision/implementation cannot later satisfy the
  independent Standard Review for that candidate. Required review uses a fresh Product Manager
  execution with review-only authority and exact-candidate binding.
- Q75 — Preserve the existing three assurance paths for Standard Review and Department Director
  acceptance: Host-proven read-only when available; artifact-immutability fallback when Host
  positively reports broader permission and hard isolation is not required; otherwise
  `INSUFFICIENT_EVIDENCE` / review pending. A role/profile label is not effective-isolation proof.
- Q76 — Department Director has no runtime fallback. If a highest-consequence acceptance trigger
  requires Astra High and that exact route is unavailable, keep the acceptance obligation pending
  rather than silently downgrading to Product Manager/Sol High.
- Q77 — Do not add a near-mandatory Product Manager routing preflight solely to protect against a
  theoretically weak Main. The user expects Main to normally be a capable model. Keep the Q49
  ambiguity/consequence-triggered routing check and accept that Main retains a bounded routing-
  judgment quality dependency while managed-role model/effort itself remains independent of Main.
- Q78 — Semantic-read batches may overlap with each other but not, by default, with an active
  canonical-workspace WriterLease when Host isolation is not independently proven. This avoids
  reading an in-flight partial candidate and keeps the broader-permission concurrency exception
  scoped to read/read overlap. Future Host-verifiable immutable snapshots/isolated workspaces may
  reopen this without changing role semantics.
- Q79 — Broader-permission parallel semantic-read batches require an artifact-immutability guard:
  bind the canonical workspace artifact before the batch, run the parallel semantic-read
  executions, then re-bind/verify the same artifact afterward. Any change follows Q71. When the
  Host positively proves the required effective read-only/isolation, this fallback guard need not
  be the assurance basis.
- Q80 — If the guarded workspace changes during the batch, invalidate the batch even when the
  mutation may have come from the user. The reason is evidence-baseline ambiguity, not an
  attribution claim against a child. Main must bind current truth again before reuse/acceptance.
- Q81 — Delete the current temporary/profile-only calibration materialization architecture.
  Calibration must no longer create campaign-specific Agent TOMLs in the real Codex agents
  directory merely to vary model/effort. Retire the staging, temporary materialized-agent
  identity, active-task nonce, rollout-prefix binding, cleanup/recovery, and transaction logic
  whose sole obligation was safe temporary profile materialization. Preserve any independently
  required generic evidence/security helpers only if a remaining consumer still proves need.
- Q82 — Calibration may explicitly test campaign-frozen model/effort challenger routes that are
  outside current production policy. This authority exists only inside evaluator/calibration
  execution, cannot create production WorkUnit acceptance, and cannot rewrite production policy.
  Production Orchestrate still rejects any route outside current policy.
- Q83 — Keep experiment campaign/run validation and provenance assurance, but simplify their
  schemas and implementations by deleting fields and checks that exist only for temporary profile
  materialization. Frozen campaign/candidate/workload/arm identity, actual input, requested /
  accepted / observed route evidence, result/oracle provenance, and measurement provenance remain.
- Q84 — Keep the normal production managed-profile installer and Doctor ownership checks for the
  three persistent role profiles. Simplify them to three behavior/configuration profiles whose
  model/effort is supplied explicitly at spawn rather than pinned in TOML. Preserve ownership-
  conflict, profile-drift, missing-profile, fresh-session and `RESTART_REQUIRED` safety behavior.
- Q85 — Clean break from the five-role and old calibration schemas before first public 1.0.0.
  Do not ship Reader/Worker/Investigator/Solver/Advisor aliases, automatic role translation, old
  manifest migration, or old experiment-run schema translation. Historical evidence remains
  historical and is not promoted into the new current schema.
- Q86 — Any future production managed-route model/effort promotion requires calibration evidence
  before policy change. Calibration never auto-promotes. The route change remains an explicit
  product decision followed by policy update, focused verification, required real-Host
  qualification, and the normal release gates.

Derived constraints from Frontier 9:

- The three-role architecture keeps useful read/read parallelism without multiplying profiles:
  broader-permission parallel reads are protected by artifact immutability and excluded from
  concurrent canonical-workspace writing unless stronger Host isolation is proven.
- Calibration is now an evidence workflow over explicit spawn routes, not a profile-provisioning
  workflow. This removes an entire class of persistent-environment mutation obligations while
  retaining campaign/run provenance.
- Production profile installation and evaluator calibration are separate concerns. The first
  remains because current role configuration is persistent Host state; the second no longer needs
  to mutate that state to compare model/effort routes.
- Pre-1.0 compatibility does not constrain the new three-role or simplified calibration schemas.

### Frontier 9 — parallel semantic-read safety and review continuity

Status: SUPERSEDED BY THE SETTLED Q78-Q80 DECISIONS ABOVE. Retained only as historical
decision-tree context; it no longer carries an open frontier.

- Q70 — Parallel semantic-read work was initially reaffirmed before the concrete guard was
  settled. Q78-Q80 later closed this branch: broader-permission read/read parallelism requires
  no active canonical-workspace managed writer plus before/after artifact-immutability binding;
  workspace drift invalidates the batch without automatic rollback.
- Q71 — Mutation detected during a parallel semantic-read batch: accepted fail-closed handling.
  Do not guess which child or actor changed the workspace and do not auto-rollback user files.
  Invalidate the batch's child evidence, quarantine the affected executions, pause new managed
  mutation, and have Main re-establish current workspace truth before reuse.
- Q72 — Role multiplicity: accepted. Programmer and Product Manager are role types, not singleton
  Agent instances; multiple independent responsibilities may use the same role concurrently within
  the global managed-child ceiling and ownership rules. For one exact Department Director
  acceptance obligation/candidate, only one active review execution is needed.
- Q73 — WriterLease ownership: accepted. WriterLease remains bound to the exact ExecutionBinding,
  not to a role name. Programmer or Product Manager may hold the sole canonical-workspace managed
  WriterLease when their responsibility grants bounded mutation authority. Department Director
  never holds WriterLease.
- Q74 — Reviewer independence: accepted. A Product Manager that participated in a candidate's
  decision-coupled implementation cannot later satisfy that candidate's independent standard
  review. A fresh Product Manager execution/context must perform the exact-candidate-bound
  review-only responsibility.
- Q75 — Review assurance: accepted reuse of the current three-path assurance model for Product
  Manager standard review and Department Director acceptance review: Host-proven effective
  read-only is strongest; positively observed broader permission may use exact artifact
  immutability fallback when hard isolation is not required and no-edit/no-external-side-effect
  semantics are explicit; unknown/ambiguous permission, required hard isolation without effective
  read-only, artifact mutation, or observed boundary violation remains INSUFFICIENT_EVIDENCE.
- Q76 — Highest-tier unavailability: accepted no downgrade. A candidate that requires Department
  Director / Astra High cannot satisfy that obligation with Product Manager / Sol High when the
  exact Astra route is unavailable. Product Manager evidence may still be useful, but highest-tier
  review remains pending / insufficient.
- Q77 — Weak-Main residual dependency: the user does not want extra architecture to defend against
  an unusually weak Main selection because users are generally expected to choose a reasonably
  capable Main. Therefore do **not** introduce a near-mandatory Product Manager / Sol Medium
  routing preflight solely as a quality floor. Retain the already accepted Q49 rule: routing checks
  are triggered by genuine ambiguity/consequence, never by Main model identity. Main remains a
  real orchestration judgment owner and some residual Main-quality dependency is accepted.

Derived constraints from the settled part of Frontier 9:

- Parallel semantic-read execution is a deliberate optimization, but it may not silently broaden
  semantic mutation authority or weaken WriterLease ownership.
- Independent review is execution/context independence, not model-family independence.
- Highest-tier acceptance never has a lower-model fallback.

### Frontier 11 — runtime schema, qualification, and implementation sequencing

Status: SETTLED

- Q95 — Runtime identity: accepted cleanly replacing `profile_id` with `role_id` in the current
  ExecutionBinding/state contract. Runtime truth records `role_id`, exact `agent_type`, exact
  requested/realized model and reasoning effort as applicable, and granted mutation authority as
  separate concepts. A custom Agent profile is Host materialization/configuration, not a bundle
  that owns runtime route and authority truth.
- Q96 — Persisted pre-1.0 state: accepted explicit rejection rather than migration or silent
  cleanup. Old five-role/profile-based state is `UNSUPPORTED_STATE`; the Plugin does not translate
  reader/worker/investigator/solver/advisor state into the three-role schema and does not delete
  user data to make it fit.
- Q97 — Route resolution ownership: accepted two-layer control. Main owns semantic
  classification/confirmation of task facts and trigger codes. Deterministic policy code owns the
  legal mapping from those accepted triggers to role/model/effort and rejects attempts to bypass
  the route contract. Deterministic code does not infer product semantics from source on its own.
- Q98 — Review trigger tiers: accepted explicit separate sets. Standard Review is Product Manager
  / Sol High for `user_requested_review`, `public_contract_change`, `material_behavior_change`,
  ordinary `persistent_state_change`, or `verification_gap`. Highest Acceptance is Department
  Director / Astra High for `security_boundary`, `authorization_boundary`, `data_integrity`,
  `critical_concurrency_or_ownership`, `migration`, `irreversible_external_effect`, formal
  `release`, or `user_requested_highest_assurance`. Highest-tier presence substitutes for routine
  Standard Review unless a separate concrete evidence/decision gap independently warrants Product
  Manager work.
- Q99 — Real-Host qualification: keep the established N0-N7 framework. Rewrite only the affected
  current probe contracts/bases for the three-role architecture rather than replacing proven Host
  lifecycle qualification. N0 and N1 cover all four executable production routes; later probes
  retain their existing lifecycle/identity/writer/privacy purpose and are rerun only when the
  deterministic per-probe classifier says their current basis changed.
- Q100 — User-visible route rationale: accepted showing localized job title plus model/effort,
  e.g. `程序员 · Luna Max`, `产品经理 · Sol Medium`, `部门总监 · Astra High` and corresponding
  English labels. Runtime evidence uses exact protocol identifiers. Department Director routing
  also exposes the concrete highest-consequence reason; UI does not invent intelligence rankings.
- Q101 — Implementation sequence: accepted seven verified slices in this order: (1) contract /
  routing policy, (2) Native Core runtime schema and explicit route spawn, (3) three profiles /
  installer / Doctor, (4) two-tier review plus parallel-read containment, (5) calibration
  simplification, (6) updater exact-identity transaction/rollback, (7) Host/release integration.
  Each slice starts with the smallest behavior-sensitive tests and expands only for failure,
  cross-module impact, or an architecture boundary. Full pytest/Ruff/package-integrity/official
  validator runs after the source architecture stabilizes, before real-Host affected probes.
- Q102 — Local commits: accepted one semantically coherent local commit per verified slice. Do not
  push, tag, publish, or create a release without later explicit user authorization.

Derived constraints from Frontier 11:

- The refactor is now a real runtime-schema clean break, not a five-role implementation hidden
  behind new labels.
- Main supplies semantic judgment; deterministic helpers supply policy enforcement. Neither a
  second AI scheduler nor a numeric routing score is introduced.
- Host qualification preserves prior investment in native identity/lifecycle/writer evidence while
  refreshing the exact route and leaf-agent surfaces that actually changed.
- The development process is intentionally reviewable and bisectable through seven local slices,
  while public publication authority remains outside those local commits.

## Grilling completion state

The decision frontier is empty. No implementation has begun from this design record. The next
authorized step is to summarize the settled architecture back to the user and obtain explicit
shared-understanding confirmation. Only after that confirmation may implementation Slice 1 begin.

## Implementation progress

Status: IMPLEMENTATION IN PROGRESS

### Slices 1-3 — architecture foundation

Implemented together as one runnable foundation because the new three-role policy is intentionally
incompatible with both the old five-role Native Core state schema and the old five-profile package;
a policy-only intermediate commit would therefore be knowingly non-runnable.

Implemented:

- three-role production policy and deterministic exact-route/review resolvers;
- current routing/review/guardrail/interaction/receipt/Orchestrate contracts updated to the
  Programmer / Product Manager / Department Director architecture;
- Native Core state schema `4.1` with ExecutionBinding `role_id`, `agent_type`, `model`, and
  `reasoning_effort`; old `profile_id`/`effort` state is unsupported;
- every managed spawn now carries exact policy `model` and `reasoning_effort` explicitly;
- Product Manager effort omission/out-of-policy effort fails before Host spawn;
- Department Director cannot receive semantic mutation authority;
- package reduced from five route-pinning Agent TOMLs to three behavior/configuration profiles;
- production profiles no longer pin model or reasoning effort; Department Director requests
  read-only sandbox intent while Programmer/Product Manager remain permission-flexible;
- installer manifest schema advanced to the clean-break three-profile generation while preserving
  ownership/no-clobber/rollback semantics;
- Doctor validates the three behavior profiles rather than duplicate model/effort truth.

Focused/expanded verification before the foundation commit: 158 relevant tests PASS. Package
integrity manifest was regenerated for the current candidate; it will be regenerated again after
later runtime slices and checked formally in Slice 7.

### Implementation amendment — Host release qualification

Status: SETTLED DURING IMPLEMENTATION, 2026-09-05

The user explicitly revised the Host verification method after Slices 1-6 were underway. The
first public `1.0.0` must **not** repeat a project-owned real-Host N0-N7 campaign. Instead, release
Host integration is based on the mature Native Codex patterns in these exact reference sources:

```text
sol-advisor
https://github.com/DannyMac180/sol-advisor
37b75cad535abdd46531f0227483a8842d045ab8

astra-advisor
https://github.com/DannyMac180/astra-advisor
c72d3280551f118eba51a5884e3971a0c0058aa6
```

This amendment supersedes Q90/Q99 only with respect to **release Host testing and evidence
machinery**. The production routes, Native Core lifecycle/state safety, current-Host authority,
requested/accepted/observed separation, and fail-closed unavailability rules remain unchanged.

Consequences:

- `docs/v4/host-reference.json` replaces the tracked N0-N7 Host campaign as release authority;
- retire the project-specific Host campaign oracle, single-probe guard, rollout evidence collector,
  staged Host procedure and carry-forward/reuse verifier complexity;
- runtime must still inspect the current callable Host surface when a concrete delegation or review
  claim requires it and must fail the affected operation closed on missing/conflicting/unobservable
  required facts;
- depth one remains a semantic managed-child rule, not a claim of Host-hard collaboration-tool
  removal; a user requirement for hard isolation still requires direct current-Host evidence;
- the exact-source Department Director / Astra High release Final Review remains required.

### Slices 4-6 — verified implementation

```text
91d577e  feat: guard parallel semantic reads
3801479  refactor: simplify calibration evidence plane
988c50e  fix: make plugin updates exact and transactional
```

Slice 4 added the broader-permission semantic-read artifact-immutability guard. Slice 5 removed
temporary calibration-profile materialization and simplified experiment validation. Slice 6 fixed
same-semver exact-identity blindness and made Plugin/profile update rollback transactional.

Before the Host-reference amendment work, the stabilized repository passed 510/510 tests, Ruff,
package-integrity checks, managed-profile lifecycle/Doctor checks, and the pinned official OpenAI
Plugin validator. Slice 7 is now the Host-reference/release-contract closure described above.

### Slice 7 — Host-reference/release closure verification

Status: SOURCE VERIFIED

Implemented:

- added `docs/v4/host-reference.json` pinned to the mature `sol-advisor` and `astra-advisor`
  commits named in the implementation amendment;
- removed the project-owned N0-N7 Host campaign oracle, qualification guard, Host rollout
  qualification collector, staged qualification procedure and their campaign-only tests;
- reduced `scripts/release_evidence_v4.py` from a Host campaign/carry-forward verifier to an
  exact-source verifier binding package integrity, the pinned Host-reference digest, the Main-owned
  pre-review request and the fresh Department Director / Astra High result;
- made release evidence reject dirty working trees so the reviewed/released source must be an exact
  clean Git commit;
- preserved ordinary runtime Host capability, lifecycle, identity, permission, UNKNOWN and
  requested/accepted/observed tests instead of deleting runtime safety together with release-only
  qualification machinery;
- updated architecture, release, installation, experiment and developer-facing contracts so no
  current authority points back to the retired Host campaign.

Verification after the architecture stabilized:

```text
release/reference focused tests   14/14 PASS
affected Slice 7 tests            122/122 PASS
full pytest                       428/428 PASS
Ruff                              PASS
package integrity                 PASS
managed profile lifecycle/Doctor PASS
official OpenAI Plugin validator  PASS
git diff --check                  PASS
```

The lower full-suite count is intentional: campaign-only Host qualification tests were deleted.
Runtime Host safety tests remain in the suite.
