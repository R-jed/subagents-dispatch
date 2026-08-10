#!/usr/bin/env python3
from pathlib import Path

PATH = Path("docs/release-checklist.md")
text = PATH.read_text(encoding="utf-8")

old_roles = '''At minimum, prove real Host spawn for:

```text
subagents_dispatch_reader
subagents_dispatch_worker
```

For each new project child, inspect the first actual `spawn_agent` call and confirm:
'''
new_roles = '''For the v3 formal Host route gate, prove controlled real Host spawn for all five exact project roles:

```text
subagents_dispatch_reader
subagents_dispatch_worker
subagents_dispatch_solver
subagents_dispatch_investigator
subagents_dispatch_advisor
```

Use one bounded smoke child per role with `fork_turns = none`, no broader authority than the route check requires, and settle every child before returning. For each role, record configured route intent separately from Host-accepted identity and observed runtime evidence for model, reasoning effort, permission/sandbox, ancestry, and child identity when the supported Host exposes those facts.

An accepted exact `agent_type` proves role acceptance only. It does not prove observed model, reasoning effort, or permission. Missing runtime evidence remains `UNKNOWN`; an observed mismatch is `FAIL`. Never copy configured values into observed columns.

For each new project child, inspect the first actual `spawn_agent` call and confirm:
'''
if text.count(old_roles) != 1:
    raise SystemExit("expected two-role Host gate exactly once")
text = text.replace(old_roles, new_roles, 1)

old_blocker = '''Luna Reader or Worker cannot be spawned on the supported Host
'''
new_blocker = '''any of the five configured project roles cannot be spawned as its exact `agent_type` on the supported Host
'''
if text.count(old_blocker) != 1:
    raise SystemExit("expected Reader/Worker blocker exactly once")
text = text.replace(old_blocker, new_blocker, 1)

PATH.write_text(text, encoding="utf-8")
