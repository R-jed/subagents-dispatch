# Historical documentation archive

Files under `docs/history/` preserve superseded release, review, experiment, and remediation records for provenance only.

They do not define current V4 product behavior, public Skill surface, runtime authority, scheduler policy, recovery authorization, Host containment guarantees, model/effort policy, or release gates. Normative current behavior comes from the active `contracts/` directory, current non-history files under `docs/`, machine-readable contracts under `docs/v4/`, the two public Skills, and the current runtime implementation.

Historical documents may intentionally contain retired terms and rules such as Dispatch as a standalone Skill, Hook/Guard lifecycle authority, PendingControl, TeamPlan runtime authority, fixed 2/3 fanout phases, fixed retry/followup budgets, or earlier Host campaigns. Those statements describe the historical artifact only and must not be promoted into current implementation or release decisions.

Every historical Markdown document should begin with the same archive warning so direct file reads and semantic retrieval preserve this authority boundary.
