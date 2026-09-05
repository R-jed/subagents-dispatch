---
name: doctor
description: Diagnose the installed subagents-dispatch Plugin and perform only explicitly requested ownership-safe maintenance.
---

# Doctor

Use a resolved Python 3.11+ interpreter to run `../../scripts/doctor.py --check` as the deterministic diagnostic owner and display its user-facing output verbatim. Preserve `[OK]`, `[WARN]`, `[FAIL]`, and `[UNKNOWN]` exactly.

Normal diagnosis is read-only and offline. It must not refresh the Marketplace, install or remove profiles, mutate orchestration state, spawn children, or modify unrelated Codex configuration.

Before diagnostics start, `../../scripts/doctor.py` verifies the shipped runtime package against `.codex-plugin/package-integrity.json`. An integrity failure stops safely.

The user-facing diagnosis covers four product areas: Plugin package, Managed Agents, Host integration, and Orchestration state. Use the deterministic runtime result as the source of truth instead of reproducing those checks in this Skill.

Host configuration and observed Host truth remain separate. A caller-supplied capability snapshot must describe the current Native Subagent surface and does not prove more than the fields it contains. Missing current Host evidence stays `UNKNOWN`.

Only explicit user intent may run maintenance. Supported owned actions are managed-profile repair and owned managed-profile uninstall. Refused ownership or filesystem checks must stay refused. Do not replace them with manual deletion, wildcard cleanup, migration guesses, or fallback paths.

The public product line begins at `1.0.0`. Doctor does not interpret, migrate, or clean pre-1.0 product state. Unsupported state and ownership ambiguity fail explicitly.

Normal diagnosis does not use the network. Update checking and Plugin update are separate explicit flows and may refresh the configured Marketplace. Plugin update remains protected by package-integrity and canonical-source verification.

Repository publication checks, release-candidate evidence, CI status, runtime-attestation campaigns, benchmark/calibration work, and other maintainer workflows stay outside Doctor.
