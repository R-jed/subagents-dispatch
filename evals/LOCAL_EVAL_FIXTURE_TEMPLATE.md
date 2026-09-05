# Local Eval Fixture Template

Use this template before starting a formal paired live behavioral run.

The workload registry defines experiment shapes. This file freezes the minimum local information needed to compare a baseline and candidate reproducibly. Experimental labels in `evals/` do not define the runtime router.

```text
fixture_id:
workload_id:
pair_id:
workload_definition_hash:

repository:
base_revision:

exact_user_prompt:
<verbatim prompt bytes used by both modes>

starting_state:
<setup commands, fixture files, seed data, or other deterministic preconditions>

acceptance_rubric_id:
acceptance_rubric:
<observable scoring / pass-fail criteria>

allowed_verification:
- <command or inspection>

main_session_route:
permissions_fingerprint:
tool_surface_fingerprint:
codex_runtime_version:

baseline_mode:
baseline_execution_route:
candidate_mode:
candidate_execution_route:
<execution placement may differ when it is the experimental variable>

sanitization_notes:
<what was removed from the report without changing the executable task>
```

Rules:

- Freeze this definition before the first run in a pair.
- Baseline and candidate use the same exact prompt, repository revision, starting state, acceptance rubric, main-session conditions, permissions, and tool surface.
- The compared strategy/execution route may differ only when that difference is the declared experimental factor.
- Compute `workload_definition_hash` from the frozen executable definition, not from the generic workload id alone.
- If a controlled input changes, create a new fixture version, pair id, and workload-definition hash.
- Missing runtime telemetry remains missing. Do not invent main-route or token facts merely to complete the fixture.
- Do not place credentials, private transcripts, hidden reasoning, or unrelated local paths in the fixture.
- Keep the sanitized fixture or equivalent reproduction data with the corresponding eval result when safe.
