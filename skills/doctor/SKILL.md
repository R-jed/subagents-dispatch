---
name: doctor
description: Diagnose the installed subagents-dispatch Plugin and perform only explicitly requested ownership-safe maintenance.
---

# Doctor

Use `../../scripts/doctor.py --check` as the deterministic diagnostic owner and display its user-facing output verbatim. Preserve `[OK]`, `[WARN]`, `[FAIL]`, and `[UNKNOWN]` exactly.

Normal diagnosis is read-only and offline. It must not refresh the Marketplace, install or remove profiles, change Hook trust, mutate orchestration state, spawn children, or modify unrelated Codex configuration.

Before diagnostics start, `../../scripts/doctor.py` verifies the shipped runtime package against `.codex-plugin/package-integrity.json`. An integrity failure stops safely.

The user-facing diagnosis covers five product areas: Plugin package, Managed Agents, Host integration, Orchestration state, and Legacy compatibility. Use the deterministic runtime result as the source of truth instead of reproducing those checks in this Skill.

Host configuration and observed Host truth remain separate. A local Hook definition or caller-supplied capability snapshot does not prove that the current Host discovered, trusted, or executed it. Missing current Host evidence stays `UNKNOWN`.

Only explicit user intent may run maintenance. Supported owned actions are managed-profile repair, migration of proven-owned legacy profile installation state, stale terminal legacy-state cleanup, owned managed-profile uninstall, update checking, and Plugin update. Refused ownership or filesystem checks must stay refused; do not replace them with manual deletion or wildcard cleanup.

Normal diagnosis does not use the network. Update checking and Plugin update are separate explicit flows and may refresh the configured Marketplace. Plugin update remains protected by package-integrity and canonical-source verification.

Repository publication checks, candidate evidence, CI status, H00-H20 Host campaigns, runtime-attestation campaigns, benchmark/calibration work, and other maintainer workflows stay outside Doctor. Runtime attestation remains a separate compatibility tool.