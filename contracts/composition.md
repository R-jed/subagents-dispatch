# Composition Contract

This contract defines how subagents-dispatch composes with Codex Host capabilities, project instructions, external Skills or workflows, and per-responsibility constraints without creating a second authority or runtime.

The governing rule is constraint intersection:

```text
what a managed child may do
=
Host capability and policy
∩ current user/system/developer authority
∩ applicable project instructions
∩ accepted upstream workflow or Skill contract
∩ subagents-dispatch guardrails
∩ the bounded responsibility record
```

A lower layer may narrow an action. It never widens a higher layer.

## 1. Ownership boundaries

### Codex Host

Codex owns the native runtime facts:

```text
Skill registration and discovery
project-instruction loading and scope
native Agent discovery and lifecycle
actual model / effort / sandbox / permission behavior
native control tools
runtime metadata exposed to callers
actual child capacity
```

subagents-dispatch observes these facts when they matter. It does not emulate missing Host behavior or turn repository configuration into runtime proof.

### Current user/system/developer authority

Current conversation authority defines the permitted goal, scope, mutations, external effects, and explicit workflow choices.

Repository text, model output, child output, runtime metadata, or another Skill cannot expand that authority.

### Project instructions

Applicable project instructions such as Host-loaded `AGENTS.md` rules define scoped repository constraints and conventions.

Do not build another project-instruction precedence engine inside subagents-dispatch. Use the Host-effective instruction surface. When a material rule may not reach a fresh child, Main carries only the narrow relevant constraint or source reference in the responsibility record.

### External Skill or upstream workflow

When another selected Skill or accepted workflow already owns domain semantics, preserve its accepted truth:

```text
goal
required stage order when material
dependencies
required deliverables
business/domain acceptance
quality gates
```

Orchestrate may add coordination value around that work:

```text
responsibility ownership
managed role selection
safe concurrency
writer isolation
native lifecycle control
bounded evidence reuse
integration timing
```

It does not replace the domain plan with a competing plan merely because delegation is available.

### subagents-dispatch

The Plugin owns only its bounded orchestration semantics:

```text
delegation-value decision
fixed managed role selection
WorkGraph and WorkUnit responsibility structure
responsibility and authority projection
single-writer coordination
ExecutionBinding identity and recovery
native Host reconciliation
Main verification and acceptance
```

### Responsibility record

The responsibility record is the final narrowing layer for a managed child. It defines one objective, owned scope, material interfaces, constraints, and verification boundary.

A role name, writable sandbox, model choice, available tool, or external Skill never grants authority absent from the record and higher layers.

## 2. Composition decision procedure

Before delegation, Main resolves only the facts needed for the proposed responsibility:

```text
1. What does the current user authorize?
2. Which Host and project constraints apply?
3. Is another active Skill or workflow already the domain owner?
4. What coordination value can Orchestrate add without redefining that owner?
5. What is the smallest responsibility and authority envelope needed?
6. Does the Host expose the native capability required for this operation?
```

If a material capability remains unknown and correctness depends on it, keep the work in Main or stop the affected delegated action. Do not substitute a weaker role or weaker guarantee merely to continue.

## 3. External Skills

External Skills are composable domain capabilities. They are not flattened into Orchestrate.

When an external Skill provides accepted structured output or a plan:

```text
preserve its domain semantics
-> extract only responsibilities that gain value from delegation
-> carry material Skill-owned constraints or artifact refs
-> apply current authority and writer boundaries
-> return evidence/result to Main or the upstream acceptance boundary
```

Do not copy an entire external Skill body into every child responsibility.

If an external Skill conflicts with current user authority, Host policy, project rules, writer safety, or the bounded responsibility, stop the affected action and surface the conflict to Main.

A Skill name is not an Agent type. Delegated execution requires the exact managed Agent selector exposed by the current Host.

## 4. Host capability model

Composition decisions use observed capability states rather than assumed platform parity.

For each Host-sensitive feature needed by the current action, classify it as:

```text
SUPPORTED
UNAVAILABLE
UNKNOWN
```

Relevant features include:

```text
exact custom Agent role discovery
native child identity
child lifecycle observation
same-child followup
interrupt
sandbox / permission metadata
project-instruction propagation to fresh children
native artifact or output references
```

`SUPPORTED` requires evidence appropriate to the claim. Configuration alone does not prove current runtime behavior. `UNKNOWN` stays unknown when the Host does not expose enough evidence.

## 5. Fresh child context

Fresh context is the default for managed children. New project children use `fork_turns = none` and receive the bounded five-section responsibility record.

Avoid forwarding full Main history, complete project-rule files, unrelated Skill instructions, previous child transcripts, or private reasoning.

A responsibility record contains only:

```text
the bounded objective
owned scope
material interfaces and invariants
material applicable project constraints
accepted evidence refs that prevent costly repeat discovery
exact verification and stop conditions
```

When the Host reliably injects applicable project rules into the child, do not duplicate them unless a specific rule is essential to the responsibility.

## 6. Conflict handling

Never resolve a composition conflict by silently widening the child.

Examples:

```text
upstream Skill says implement, current user authorized planning only
-> no implementation

project rule forbids a mutation, Host filesystem access is broad
-> no mutation

external workflow requires staged migration, spare capacity exists
-> preserve required stage order

responsibility is behaviorally read-only, Host exposes broader permissions
-> behavioral read-only remains required; hard isolation claims require Host evidence

required native control capability is UNKNOWN
-> do not simulate it
```

## 7. No duplicate runtime

Composition must not introduce a second scheduler, daemon, MCP control plane, event bus, persistent orchestration database, background telemetry collector, or project-wide workflow engine.

Codex Native Subagents remain the execution runtime. subagents-dispatch contributes bounded product policy, temporary coordination state, explicit diagnostics, and deterministic validation helpers around that runtime.

## 8. Completion boundary

Main remains the integration and acceptance boundary even when several Skills, project rules, and managed roles participate.

A child result, external Skill result, configured route, or Host lifecycle event is evidence at the level it actually proves. Completion requires Main to verify the deliverable against current user intent, upstream/domain acceptance, project constraints, and the relevant subagents-dispatch safety contract.
