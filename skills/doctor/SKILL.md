---
name: doctor
description: Diagnose subagents-dispatch V4 package integrity, profiles, state, lifecycle guards, migration blockers, Host capability evidence, and supported-execution release readiness.
---

# Doctor

Use this Skill for deterministic V4 diagnostics and explicit maintenance operations. Doctor does not perform orchestration work.

The default path is read-only. Preserve the package-integrity bootstrap in `../../scripts/doctor.py`, then use the V4 diagnostics in `../../scripts/doctor_runtime.py`.

Check the packaged V4 identity, exactly two public Skills, five fixed profiles, V4 state validity, WriterLease and PendingControl integrity, the three managed lifecycle Hook surfaces, supplied Host capability evidence, V3.x migration blockers, and the real Host smoke release gate.

Treat Luna Max, Terra High, and Sol High as fixed V4.0.0 profile settings. Profile drift is a diagnostic failure.

If unresolved V3.x state exists for the target thread, report it as a hard V4 execution blocker. Never silently convert active V3.x state into V4. Terminal legacy cleanup remains explicit.

If H01 through H07 real Host smoke evidence is not PASS, report managed execution as blocked while plan-only Orchestrate and Doctor remain available. Offline tests, package integrity, source inspection, and packaged Hook presence do not satisfy the real Host gate.

`--repair`, `--migrate-legacy`, `--cleanup-stale`, and `--update` are explicit lifecycle operations. Do not run them from the default diagnostic path.

When Host evidence is supplied, normalize only the evidence actually provided. Missing Host facts remain UNKNOWN. Do not infer runtime Hook execution merely because `hooks/hooks.json` is packaged.
