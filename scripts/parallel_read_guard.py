#!/usr/bin/env python3
"""Artifact-immutability guard for parallel semantic-read managed executions.

This helper does not create scheduler state. Main carries the returned begin token
until the parallel read batch is integrated. The canonical workspace identity uses
the same review-artifact helper as independent review.
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Sequence

import dispatch_state_v4 as state

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_HELPER = ROOT / "scripts" / "review-artifact.py"
TOKEN_SCHEMA = 1
SEMANTIC_READ_ROLES = {"programmer", "product_manager"}


class ParallelReadGuardError(RuntimeError):
    """A parallel semantic-read batch cannot be proven safe enough to run."""


def _execution_map(payload: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(item["execution_id"]): item
        for item in payload.get("executions", [])
        if isinstance(item, Mapping) and isinstance(item.get("execution_id"), str)
    }


def _validate_batch_executions(
    payload: Mapping[str, Any], execution_ids: Sequence[str]
) -> tuple[str, ...]:
    if not isinstance(execution_ids, Sequence) or isinstance(execution_ids, (str, bytes)):
        raise ParallelReadGuardError("execution_ids must be an array")
    normalized = tuple(execution_ids)
    if len(normalized) < 2 or any(not isinstance(value, str) or not value for value in normalized):
        raise ParallelReadGuardError("parallel semantic-read batch requires at least two execution ids")
    if len(set(normalized)) != len(normalized):
        raise ParallelReadGuardError("parallel semantic-read batch contains duplicate execution ids")
    executions = _execution_map(payload)
    for execution_id in normalized:
        execution = executions.get(execution_id)
        if execution is None:
            raise ParallelReadGuardError(f"unknown parallel semantic-read execution: {execution_id}")
        if execution.get("role_id") not in SEMANTIC_READ_ROLES:
            raise ParallelReadGuardError("parallel semantic-read guard supports Programmer/Product Manager only")
        if execution.get("granted_authority") != "none" or execution.get("granted_write_scope") != []:
            raise ParallelReadGuardError("parallel semantic-read execution has mutation authority")
    return tuple(sorted(normalized))


def _blocking_writer(payload: Mapping[str, Any]) -> bool:
    lease = payload.get("writer_lease")
    return isinstance(lease, Mapping) and lease.get("state") in state.WRITER_BLOCKING_STATES


def _artifact_receipt(repo: Path, *, verify: str | None = None) -> tuple[bool, dict[str, Any]]:
    args = [sys.executable, str(ARTIFACT_HELPER), "--repo", os.fspath(repo)]
    if verify is not None:
        args.extend(["--verify", verify])
    result = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    receipt: dict[str, Any] = {}
    if result.stdout.strip():
        try:
            decoded = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise ParallelReadGuardError("review-artifact helper returned invalid JSON") from exc
        if not isinstance(decoded, dict):
            raise ParallelReadGuardError("review-artifact helper returned a non-object receipt")
        receipt = decoded
    if verify is None and result.returncode != 0:
        detail = result.stderr.strip() or f"exit {result.returncode}"
        raise ParallelReadGuardError(f"could not bind parallel-read workspace artifact: {detail}")
    return result.returncode == 0, receipt


def begin_parallel_read_batch(
    thread_id: str,
    *,
    execution_ids: Sequence[str],
    repo: Path,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Bind one parallel semantic-read batch before any guarded child work proceeds."""
    current = state.load_state(thread_id, temp_root=temp_root)
    if current is None:
        raise ParallelReadGuardError("parallel semantic-read batch requires current orchestration state")
    state.validate_state_payload(current, thread_id=thread_id)
    normalized = _validate_batch_executions(current, execution_ids)
    if _blocking_writer(current):
        raise ParallelReadGuardError("parallel semantic-read batch cannot overlap an active canonical WriterLease")
    _, receipt = _artifact_receipt(repo)
    artifact_id = receipt.get("review_artifact_id")
    if not isinstance(artifact_id, str) or not artifact_id:
        raise ParallelReadGuardError("parallel-read artifact receipt is missing review_artifact_id")
    return {
        "schema_version": TOKEN_SCHEMA,
        "thread_id": thread_id,
        "execution_ids": list(normalized),
        "artifact_id": artifact_id,
        "writer_lease": copy.deepcopy(current.get("writer_lease")),
    }


def _validate_token(token: Mapping[str, Any]) -> tuple[str, tuple[str, ...], str, Any]:
    if not isinstance(token, Mapping) or set(token) != {
        "schema_version",
        "thread_id",
        "execution_ids",
        "artifact_id",
        "writer_lease",
    }:
        raise ParallelReadGuardError("parallel-read guard token is malformed")
    if token.get("schema_version") != TOKEN_SCHEMA:
        raise ParallelReadGuardError("parallel-read guard token schema is unsupported")
    thread_id = token.get("thread_id")
    artifact_id = token.get("artifact_id")
    if not isinstance(thread_id, str) or not thread_id:
        raise ParallelReadGuardError("parallel-read guard token thread_id is invalid")
    if not isinstance(artifact_id, str) or not artifact_id:
        raise ParallelReadGuardError("parallel-read guard token artifact_id is invalid")
    ids_raw = token.get("execution_ids")
    if not isinstance(ids_raw, list):
        raise ParallelReadGuardError("parallel-read guard token execution_ids is invalid")
    ids = tuple(ids_raw)
    if tuple(sorted(ids)) != ids or len(ids) < 2 or len(set(ids)) != len(ids):
        raise ParallelReadGuardError("parallel-read guard token execution_ids are not canonical")
    return thread_id, ids, artifact_id, token.get("writer_lease")


def _quarantine_batch(
    thread_id: str,
    *,
    execution_ids: Sequence[str],
    temp_root: str | os.PathLike[str] | None,
) -> dict[str, Any]:
    changed: dict[str, Any] = {}

    def mutate(current: dict[str, Any]) -> None:
        executions = _execution_map(current)
        for execution_id in execution_ids:
            execution = executions.get(execution_id)
            if execution is None:
                raise ParallelReadGuardError("guarded execution disappeared before quarantine")
            mutable = execution  # same dictionaries owned by current state
            assert isinstance(mutable, dict)
            mutable["lifecycle"] = "UNKNOWN"
            mutable["failure_origin"] = "runtime_ambiguous"
            mutable["blocker"] = "investigation"
            mutable["quarantine_reason"] = "workspace_baseline_drift"
        changed["executions"] = list(execution_ids)

    state.mutate_state(thread_id, mutate, temp_root=temp_root)
    return changed


def verify_parallel_read_batch(
    token: Mapping[str, Any],
    *,
    repo: Path,
    temp_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Verify workspace/writer immutability and quarantine the whole batch on drift."""
    thread_id, execution_ids, artifact_id, writer_before = _validate_token(token)
    current = state.load_state(thread_id, temp_root=temp_root)
    if current is None:
        raise ParallelReadGuardError("parallel semantic-read state disappeared before verification")
    state.validate_state_payload(current, thread_id=thread_id)
    _validate_batch_executions(current, execution_ids)
    writer_unchanged = current.get("writer_lease") == writer_before
    artifact_unchanged, receipt = _artifact_receipt(repo, verify=artifact_id)
    if writer_unchanged and artifact_unchanged:
        return {
            "status": "verified",
            "artifact_unchanged": True,
            "writer_lease_unchanged": True,
            "pause_managed_mutation": False,
            "review_artifact_id": artifact_id,
        }

    _quarantine_batch(
        thread_id,
        execution_ids=execution_ids,
        temp_root=temp_root,
    )
    return {
        "status": "quarantined",
        "artifact_unchanged": artifact_unchanged,
        "writer_lease_unchanged": writer_unchanged,
        "pause_managed_mutation": True,
        "review_artifact_id": receipt.get("review_artifact_id"),
    }
