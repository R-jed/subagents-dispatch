# Runtime package integrity

subagents-dispatch ships a deterministic package-consistency contract at `.codex-plugin/package-integrity.json`.

The manifest records SHA-256 digests for the shipped runtime files selected by `scripts/package_integrity.py`. UTF-8 text is normalized to LF before hashing so equivalent Windows and Unix checkouts do not produce false mismatches. CI regenerates the expected manifest in memory and fails when the committed contract is stale.

This check is designed to detect partial, stale, or accidentally modified Plugin packages. It is not a signature, provenance proof, or protection against an attacker who can rewrite both the package and its manifest.

## Doctor bootstrap

`scripts/doctor.py` is a small stdlib-only bootstrap. Before loading the normal Doctor runtime it:

1. requires a regular `.codex-plugin/package-integrity.json`;
2. verifies `scripts/package_integrity.py` against the digest recorded in that manifest before importing the helper;
3. runs the helper's full package verification;
4. starts `scripts/doctor_runtime.py` only after those checks pass.

A bootstrap failure is reported as `Plugin package integrity` before the normal report exists. It is not a twelfth Doctor layer. A healthy Doctor still has exactly eleven production layers.

## Explicit update

`doctor.py --update` uses the smaller `update-bootstrap` profile. That profile protects only the files required to reach the canonical updater safely, so a missing non-bootstrap runtime file does not make the supported recovery path impossible.

After Codex installs a newer Plugin package, `scripts/plugin_update.py` runs the new package's full integrity verifier before reconciling managed Agent profiles or running the new Doctor. A failed package verification stops the update lifecycle.

If the currently selected Marketplace release is already the installed version, explicit update may be a no-op. A damaged same-version package can therefore still require reinstalling the canonical Marketplace release.

## Release maintenance

When a runtime file changes, regenerate the manifest with:

```text
python scripts/package_integrity.py --write
```

Then verify it without changing the checkout:

```text
python scripts/package_integrity.py --check-generated
python scripts/package_integrity.py
```

The four-platform CI runs the generated-manifest check before lint and tests. Runtime files must not be added by maintaining an independent manual digest list; `scripts/package_integrity.py` owns runtime-scope discovery and manifest generation.
