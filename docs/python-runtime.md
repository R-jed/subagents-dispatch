# Python Helper Runtime

subagents-dispatch ships several local Python helpers for managed-profile lifecycle, deterministic diagnostics, runtime attestation, and repository validation. These helpers require Python 3.11 or newer.

This requirement belongs to subagents-dispatch. Codex Host availability does not imply that a command named `python` exists in the task shell.

## Resolve once from the actual environment

Before invoking any bundled Python helper outside a CI job that already provisions Python explicitly, resolve one supported Python invocation from the actual environment that will run the helper.

Accepted command names or launchers may include `python3`, `python`, or a platform launcher such as `py -3.11`, provided the resolved interpreter reports Python 3.11 or newer. Do not treat any command name as universally available.

Record both:

```text
resolved invocation
sys.executable
Python version
```

Then use that same resolved interpreter for every subagents-dispatch Python helper in the current validation, provisioning, diagnosis, or attestation operation.

In protocol snippets, this resolved invocation is written as:

```text
<python-3.11+>
```

That token is a placeholder for the already resolved invocation. It is never a literal command to execute.

## Resolution is environment adaptation

Choosing an available supported interpreter name or launcher does not change the candidate, role, model, Agent type, permission evidence, or acceptance semantics. Resolving `python3` after discovering that `python` is absent is environment adaptation, not semantic substitution and not a retry of a Host Agent attempt.

Do not loosen any role, route, permission, provenance, mutation, or release requirement while resolving the interpreter.

## Fail closed before Host work

If no Python 3.11+ interpreter can be resolved from the actual environment, report:

```text
PYTHON_PREREQUISITE_UNMET
```

Stop before any child spawn or Python-backed repair/provisioning mutation that depends on the helper. Classify downstream Host route, runtime attestation, inspector, and behavioral gates as `NOT TESTED` or `INVALIDATED` according to the enclosing protocol. Do not report a Host role rejection or candidate route failure when the helper never ran.

A single `command not found` for one candidate command name is not by itself proof that the prerequisite is unavailable. Check the supported environment for another Python 3.11+ invocation before concluding `PYTHON_PREREQUISITE_UNMET`.

## CI distinction

The canonical GitHub Actions workflow uses `actions/setup-python`, so its later use of a command named `python` is valid inside that provisioned CI environment. That CI guarantee does not establish which Python command names exist inside a real Codex App task shell.
