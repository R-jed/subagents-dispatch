# Writer Boundary

subagents-dispatch treats writer ownership as a workspace boundary.

The current product manages one canonical mutable workspace. Inside that workspace, at most one managed writing actor may be active at a time. The possible writers are Main, a Luna Worker, or a Sol Solver when the responsibility explicitly grants write authority.

This rule is intentionally stricter than checking whether two tasks claim different file lists. Planned write scopes do not isolate the physical checkout. Two writers can still interact through the Git index, untracked files, generated artifacts, formatter or build output, lockfiles, migrations, schemas, shared configuration, caches, or files that one task discovers only after it starts. A stale assumption can also create a semantic conflict even when the final changed paths do not overlap.

The durable rule is therefore:

```text
one active writer per mutable workspace
```

For the current V4 runtime there is one managed workspace, so the effective writer limit is one. WriterLease exists to make that ownership explicit and to prevent `UNKNOWN`, interrupt acknowledgement, or ambiguous Host state from becoming accidental authority for a conflicting write.

## Why this is a workspace rule

Parallel read-only investigation is cheap to reconcile because no child changes the shared checkout. Parallel writing changes the environment while other actors are reasoning about it. The risk is larger than a textual merge conflict:

```text
filesystem collision
shared generated output
Git/index interaction
schema or API invalidation
migration ordering
lockfile or dependency changes
accepted evidence becoming stale
uncertain ownership after interruption or Host failure
```

A declared disjoint file list helps planning, but it does not prove these hazards are absent.

## When multiple writers could become safe

Multiple concurrent writers should require genuinely independent mutable workspaces, such as separate worktrees, workspaces, or repositories, plus a Host contract that binds each child to the intended workspace.

Before such a mode can be enabled, all of the following need evidence:

1. The Host exposes a reliable way to bind each writable child to one exact workspace and does not silently fall back to the canonical checkout.
2. Each writer has a bounded write scope inside its own workspace.
3. Shared semantic surfaces are classified before parallel execution, including APIs, schemas, migrations, lockfiles, generated artifacts, persistent state, and external systems.
4. Integration order and conflict handling are deterministic and owned by Main.
5. Failure, interruption, takeover, and `UNKNOWN` ownership are tracked independently per workspace.
6. Product benchmarks show that the additional write parallelism improves useful outcomes enough to justify the extra coordination and merge cost.

Filesystem isolation alone is insufficient. Two isolated branches can still make mutually invalid assumptions about the same interface.

## Current decision

V4.0.0 keeps the canonical workspace single-writer contract. The product language should describe this as a workspace-scoped safety boundary, leaving room for a future isolated-workspace mode when Codex exposes the required Host controls and real workload evidence supports it.
