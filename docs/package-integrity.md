# Runtime Package Integrity

subagents-dispatch ships a deterministic package-consistency manifest at `.codex-plugin/package-integrity.json`.

`scripts/package_integrity.py` discovers the installed-product runtime allowlist, normalizes UTF-8 text to LF, and records SHA-256 digests. CI regenerates the expected manifest in memory and fails when the committed manifest is stale.

This detects partial, stale or accidentally modified packages. It is not a signature or protection against an attacker who can rewrite both files and the manifest.

## Doctor startup

Current Native Core Doctor has one implementation owner: `scripts/doctor.py`.

At startup it runs full package verification before diagnosis. If package integrity fails, Doctor exits safely before reporting normal product layers.

A healthy normal report contains exactly five product layers:

```text
Plugin package
Managed Agents
Host integration
Orchestration state
Legacy compatibility
```

`scripts/doctor_runtime.py` and `scripts/doctor_runtime_core.py` are compatibility aliases only. They are not separate diagnostic engines.

## Explicit update

The explicit updater is:

```text
<python-3.11+> scripts/plugin_update.py --codex-home <active-codex-home>
```

The updater verifies canonical installed identity before changing anything. After Codex installs a newer package it verifies the new package integrity, reconciles Plugin-owned managed profiles, verifies those profiles, and runs the newly installed Doctor JSON contract as post-write validation.

The current Doctor machine contract is:

```text
layers
actions
```

Post-update verification requires the exact five current product layers, no maintenance actions, no blocking layer state, and matching installed version identity.

Update checking without installation is owned separately by `scripts/check-plugin-update.py`.

## Release maintenance

When a runtime file changes, regenerate the manifest:

```text
python scripts/package_integrity.py --write
```

Then verify without changing the checkout:

```text
python scripts/package_integrity.py --check-generated
python scripts/package_integrity.py
```

The canonical CI performs generated-manifest verification before lint and tests.
