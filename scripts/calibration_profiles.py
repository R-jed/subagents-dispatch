#!/usr/bin/env python3
"""Materialize isolated Reader calibration Agent profiles.

This is an evaluator-side helper.  It never changes the production policy or
the five packaged profiles; it only creates an explicitly scoped, owned set
under an evaluator-owned CODEX_HOME.
"""

from __future__ import annotations

import argparse
import ctypes
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import tomllib
from typing import Any, Callable, Iterator, NoReturn

from calibration_profile_contract import (
    PRODUCTION_AGENT_TYPES,
    materialized_agent_type,
    role_contract_digest,
)


ROOT = Path(__file__).resolve().parents[1]
READER_TEMPLATE = ROOT / "agent-profiles" / "subagents-dispatch-reader.toml"
POLICY = ROOT / "contracts" / "policy.json"
CAMPAIGN_VALIDATOR = ROOT / "scripts" / "validate-experiment-campaign.py"
MANIFEST_NAME = ".subagents-dispatch-calibration.json"
LOCK_NAME = ".subagents-dispatch-calibration.lock"
EVALUATOR_MARKER = ".subagents-dispatch-evaluator-root.json"
EVALUATOR_MARKER_SCHEMA = 1
MANIFEST_SCHEMA = 4
LOCK_MARKER = b"subagents-dispatch calibration lock v1\n"
PROFILE_STATUSES = {"PREPARED", "APPLIED", "COMMITTED", "CLEANED"}


def fail(message: str) -> NoReturn:
    raise SystemExit(f"ERROR: {message}")


def _crash_at(boundary: str) -> None:
    if os.environ.get("SUBAGENTS_DISPATCH_CALIBRATION_CRASH_AT") == boundary:
        os._exit(86)


def _regular(path: Path, label: str, *, missing_ok: bool = True) -> None:
    if path.is_symlink():
        fail(f"refusing symlinked {label}: {path}")
    if not path.exists():
        if missing_ok:
            return
        fail(f"missing {label}: {path}")
    if not path.is_file():
        fail(f"{label} is not a regular file: {path}")


def _directory(path: Path, label: str, *, missing_ok: bool = True) -> None:
    if path.is_symlink():
        fail(f"refusing symlinked {label}: {path}")
    if not path.exists():
        if missing_ok:
            return
        fail(f"missing {label}: {path}")
    if not path.is_dir():
        fail(f"{label} is not a directory: {path}")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_json(path: Path, label: str) -> dict[str, Any]:
    _regular(path, label, missing_ok=False)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(f"could not load {label}: {exc}")
    if not isinstance(payload, dict):
        fail(f"{label} must be a JSON object")
    return payload


def _campaign_bytes(path: Path) -> tuple[bytes, str]:
    _regular(path, "campaign", missing_ok=False)
    try:
        data = path.read_bytes()
    except OSError as exc:
        fail(f"could not read campaign: {exc}")
    return data, _sha256(data)


def _evaluator_marker_path(evaluator_root: Path) -> Path:
    return _safe_child(evaluator_root, EVALUATOR_MARKER, "evaluator marker")


def _marker_payload(evaluator_root: Path) -> dict[str, Any]:
    return {
        "schema_version": EVALUATOR_MARKER_SCHEMA,
        "managed_by": "subagents-dispatch-calibration",
        "evaluator_root": str(evaluator_root),
    }


def _require_evaluator_marker(evaluator_root: Path) -> None:
    path = _evaluator_marker_path(evaluator_root)
    marker = _load_json(path, "evaluator marker")
    if marker != _marker_payload(evaluator_root):
        fail(f"evaluator marker ownership drifted: {path}")


def init_evaluator(evaluator_root_arg: Path) -> None:
    evaluator_root = evaluator_root_arg.expanduser()
    if not evaluator_root.is_absolute():
        fail("--evaluator-root must be an explicit absolute path")
    if evaluator_root.is_symlink() or not evaluator_root.exists() or not evaluator_root.is_dir():
        fail(f"evaluator root must be an existing regular directory: {evaluator_root}")
    evaluator_root = evaluator_root.resolve()
    marker = _evaluator_marker_path(evaluator_root)
    if marker.exists() or marker.is_symlink():
        _require_evaluator_marker(evaluator_root)
        print("EVALUATOR READY: ownership marker already exact")
        return
    if any(evaluator_root.iterdir()):
        fail("refusing to claim a non-empty evaluator root without an ownership marker")
    _atomic_write(marker, (json.dumps(_marker_payload(evaluator_root), sort_keys=True) + "\n").encode("utf-8"))
    print("EVALUATOR READY: dedicated calibration evaluator root claimed")


def _load_policy() -> dict[str, Any]:
    policy = _load_json(POLICY, "policy contract")
    try:
        reader = policy["roles"]["reader"]
        expected = (reader["agent_type"], reader["model"], reader["effort"], reader["mutation_authority"])
    except (KeyError, TypeError) as exc:
        fail(f"policy does not define a complete reader route: {exc}")
    if expected != ("subagents_dispatch_reader", "gpt-5.6-luna", "max", "none"):
        fail("Reader calibration requires the production Luna Max read-only control route")
    return policy


def _load_template() -> dict[str, Any]:
    _regular(READER_TEMPLATE, "canonical Reader profile", missing_ok=False)
    try:
        data = tomllib.loads(READER_TEMPLATE.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        fail(f"invalid canonical Reader profile: {exc}")
    required = {"name", "description", "model", "model_reasoning_effort", "developer_instructions"}
    if not required <= set(data):
        fail("canonical Reader profile is missing required contract fields")
    if "sandbox_mode" in data:
        fail("canonical Reader profile must inherit Host permissions")
    return data


def _normal_codex_home() -> Path:
    if os.name == "posix":
        import pwd

        return (Path(pwd.getpwuid(os.getuid()).pw_dir) / ".codex").resolve()
    return (Path.home() / ".codex").resolve()


def _host_home_identity(
    codex_home: Path,
    evidence_path_arg: Path,
    provisioning_task_id: str,
    *,
    require_active_task: bool,
) -> dict[str, str]:
    if require_active_task and os.environ.get("CODEX_THREAD_ID") != provisioning_task_id:
        fail("provisioning task identity does not match the active Codex task")
    evidence_path = evidence_path_arg.expanduser()
    if not evidence_path.is_absolute() or evidence_path.is_symlink():
        fail("--host-home-evidence must be an absolute regular file")
    evidence = _load_json(evidence_path, "Host-home evidence")
    if set(evidence) != {"active_codex_home", "provisioning_rollout_path", "provisioning_rollout_sha256"}:
        fail(
            "Host-home evidence must contain only active_codex_home, "
            "provisioning_rollout_path, and provisioning_rollout_sha256"
        )
    active = evidence.get("active_codex_home")
    rollout_value = evidence.get("provisioning_rollout_path")
    rollout_sha256 = evidence.get("provisioning_rollout_sha256")
    if (
        not isinstance(active, str) or not active
        or not isinstance(rollout_value, str) or not rollout_value
        or not isinstance(rollout_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", rollout_sha256)
    ):
        fail("Host-home evidence is incomplete")
    active_path = Path(active).expanduser()
    if not active_path.is_absolute() or active_path.is_symlink():
        fail("active Codex home evidence is not an absolute regular path")
    normal_home = _normal_codex_home()
    if active_path.resolve() != codex_home or codex_home != normal_home:
        fail("requested Codex home does not match the confirmed active normal ~/.codex home")
    rollout = Path(rollout_value).expanduser()
    if not rollout.is_absolute() or rollout.is_symlink():
        fail("provisioning rollout evidence must be an absolute regular file")
    _regular(rollout, "provisioning rollout evidence", missing_ok=False)
    try:
        rollout = rollout.resolve(strict=True)
        rollout.relative_to((codex_home / "sessions").resolve(strict=True))
    except (OSError, ValueError):
        fail("provisioning rollout evidence is not under the requested normal Codex home")
    raw = rollout.read_bytes()
    if _sha256(raw) != rollout_sha256:
        fail("provisioning rollout evidence SHA256 does not match")
    if not rollout.name.startswith("rollout-") or not rollout.name.endswith(
        f"-{provisioning_task_id}.jsonl"
    ):
        fail("provisioning rollout evidence does not use the Host rollout identity name")
    session_ids: list[str] = []
    turn_contexts = 0
    try:
        for line in raw.decode("utf-8").splitlines():
            record = json.loads(line)
            if record.get("type") == "session_meta":
                payload = record.get("payload")
                if not isinstance(payload, dict) or not isinstance(payload.get("id"), str):
                    fail("provisioning rollout session_meta is incomplete")
                session_ids.append(payload["id"])
            elif record.get("type") == "turn_context" and isinstance(record.get("payload"), dict):
                turn_contexts += 1
    except (UnicodeError, json.JSONDecodeError) as exc:
        fail(f"provisioning rollout evidence is malformed: {exc}")
    if session_ids != [provisioning_task_id] or turn_contexts == 0:
        fail("provisioning rollout does not identify the preparation task")
    return {
        "active_codex_home": str(codex_home),
        "provisioning_rollout_path": str(rollout),
        "provisioning_rollout_sha256": rollout_sha256,
    }


def _validate_roots(
    evaluator_root_arg: Path,
    codex_home_arg: Path,
    host_home_evidence_arg: Path,
    provisioning_task_id: str,
    *,
    require_active_task: bool = False,
) -> tuple[Path, Path, dict[str, str]]:
    evaluator_root = evaluator_root_arg.expanduser()
    codex_home = codex_home_arg.expanduser()
    if not evaluator_root.is_absolute() or not codex_home.is_absolute():
        fail("--evaluator-root and --codex-home must be explicit absolute paths")
    if evaluator_root.is_symlink() or not evaluator_root.exists() or not evaluator_root.is_dir():
        fail(f"evaluator root must be an existing regular directory: {evaluator_root}")
    evaluator_root = evaluator_root.resolve()
    _require_evaluator_marker(evaluator_root)
    if evaluator_root == (Path.home() / ".codex").resolve():
        fail("refusing production ~/.codex as evaluator root")
    if codex_home.exists() and codex_home.is_symlink():
        fail(f"refusing symlinked calibration CODEX_HOME: {codex_home}")
    current = Path(codex_home.anchor)
    for component in codex_home.parts[1:]:
        current = current / component
        if current.is_symlink():
            fail(f"refusing symlinked calibration path component: {current}")
    codex_resolved = codex_home.resolve()
    try:
        codex_resolved.relative_to(evaluator_root)
    except ValueError:
        pass
    else:
        fail("profile-only Codex home must remain outside the Experiment Plane")
    _directory(codex_home, "calibration CODEX_HOME")
    return evaluator_root, codex_resolved, _host_home_identity(
        codex_resolved, host_home_evidence_arg, provisioning_task_id,
        require_active_task=require_active_task,
    )


def _safe_child(parent: Path, child: str, label: str) -> Path:
    if not child or Path(child).name != child or child in {".", ".."}:
        fail(f"unsafe {label} name: {child!r}")
    path = parent / child
    try:
        resolved_parent = parent.resolve()
        resolved = path.resolve() if path.exists() else path
        resolved.relative_to(resolved_parent)
    except ValueError:
        fail(f"{label} escapes its owner directory: {path}")
    return path


def _render_profile(template: dict[str, Any], agent_type: str, model: str, effort: str) -> bytes:
    # Replace only the route identity fields in the canonical file.  Contract
    # prose remains byte-for-byte sourced from the shipped Reader template.
    text = READER_TEMPLATE.read_text(encoding="utf-8")
    replacements = {
        "name": agent_type,
        "model": model,
        "model_reasoning_effort": effort,
    }
    for key, value in replacements.items():
        pattern = rf"(?m)^{re.escape(key)}\s*=\s*\"[^\"]*\"\s*$"
        text, count = re.subn(pattern, f'{key} = "{value}"', text, count=1)
        if count != 1:
            fail(f"canonical Reader profile has no unique {key!r} field")
    return text.encode("utf-8")


def _validated_campaign(path: Path) -> tuple[dict[str, Any], dict[str, Any], str]:
    initial, raw_sha256 = _campaign_bytes(path)
    fd, frozen_name = tempfile.mkstemp(prefix=".frozen-campaign-", suffix=".json", dir=path.parent)
    frozen_path = Path(frozen_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(initial)
            handle.flush()
            os.fsync(handle.fileno())
        result = subprocess.run(
            [sys.executable, str(CAMPAIGN_VALIDATOR), str(frozen_path), "--json"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    finally:
        frozen_path.unlink(missing_ok=True)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or str(result.returncode)
        fail(f"campaign validation failed: {detail}")
    try:
        summary = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        fail(f"campaign validator returned invalid JSON: {exc}")
    if not isinstance(summary, dict):
        fail("campaign validator summary must be a JSON object")
    current, current_sha256 = _campaign_bytes(path)
    if current != initial or current_sha256 != raw_sha256:
        fail("campaign changed while it was being validated; refusing a TOCTOU race")
    try:
        campaign = json.loads(initial)
    except (UnicodeError, json.JSONDecodeError) as exc:
        fail(f"could not load frozen campaign: {exc}")
    if not isinstance(campaign, dict):
        fail("frozen campaign must be a JSON object")
    if campaign.get("experiment", {}).get("type") != "role_calibration":
        fail("calibration profiles require a role_calibration campaign")
    roles = campaign["experiment"].get("roles", [])
    if len(roles) != 1 or roles[0].get("role") != "reader":
        fail("initial calibration profiles support exactly the Reader role")
    return campaign, summary, raw_sha256


def _profile_records(campaign: dict[str, Any], policy: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    template = _load_template()
    spec = campaign["experiment"]["roles"][0]
    control, challengers = spec["control"], spec["challengers"]
    description = str(template["description"])
    instructions = str(template["developer_instructions"])
    digest = role_contract_digest("reader", description, instructions, policy["roles"]["reader"]["mutation_authority"])
    routes = [control, *challengers]
    records: list[dict[str, Any]] = []
    seen_types: set[str] = set()
    for route in routes:
        route_id = str(route["id"])
        agent_type = materialized_agent_type(campaign["campaign_id"], "reader", route_id)
        if agent_type in PRODUCTION_AGENT_TYPES or agent_type in seen_types:
            fail(f"calibration Agent identity collides: {agent_type}")
        seen_types.add(agent_type)
        profile_bytes = _render_profile(template, agent_type, route["model"], route["effort"])
        try:
            parsed_profile = tomllib.loads(profile_bytes.decode("utf-8"))
        except (UnicodeError, tomllib.TOMLDecodeError) as exc:
            fail(f"generated calibration profile is invalid: {exc}")
        if parsed_profile.get("name") != agent_type:
            fail("generated calibration profile name does not match materialized_agent_type")
        records.append(
            {
                "campaign_id": campaign["campaign_id"],
                "candidate_sha": campaign["plugin_candidate_sha"],
                "route": route,
                "route_id": route_id,
                "semantic_role": "reader",
                "materialized_agent_type": agent_type,
                "role_contract_digest": digest,
                "configured_model": route["model"],
                "configured_effort": route["effort"],
                "profile_bytes": profile_bytes,
            }
        )
    return records, {"description": description, "developer_instructions": instructions, "digest": digest}


def _atomic_write(path: Path, data: bytes) -> None:
    _directory(path.parent, "owner directory", missing_ok=False)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    staged = Path(name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(staged, path)
        _fsync_directory(path.parent)
    finally:
        staged.unlink(missing_ok=True)


def _fsync_directory(path: Path, *, platform: str = os.name) -> None:
    if platform == "nt":
        return
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _lock_open_flags(*, platform: str = os.name) -> int:
    return os.O_RDWR | getattr(os, "O_BINARY", 0) if platform == "nt" else os.O_RDWR


def _rename_no_replace(source: Path, destination: Path) -> None:
    if destination.exists() or destination.is_symlink():
        fail(f"owned cleanup quarantine already exists: {destination}")
    if os.name == "nt":
        os.rename(source, destination)
        return
    libc = ctypes.CDLL(None, use_errno=True)
    source_bytes, destination_bytes = os.fsencode(source), os.fsencode(destination)
    if sys.platform == "darwin" and hasattr(libc, "renamex_np"):
        result = libc.renamex_np(source_bytes, destination_bytes, 0x00000004)
    elif hasattr(libc, "renameat2"):
        result = libc.renameat2(-2, source_bytes, -2, destination_bytes, 0x00000001)
    else:
        fail("platform lacks atomic no-replace rename required for profile cleanup")
    if result != 0:
        error = ctypes.get_errno()
        fail(f"atomic profile cleanup rename failed: {os.strerror(error)}")


@contextmanager
def _lock(codex_home: Path, *, check_only: bool) -> Iterator[Path]:
    _directory(codex_home, "calibration CODEX_HOME", missing_ok=check_only)
    path = _safe_child(codex_home, LOCK_NAME, "calibration lock")
    if path.is_symlink():
        fail(f"refusing symlinked calibration lock: {path}")
    if check_only and not path.exists():
        fail(f"missing calibration lock: {path}")
    flags = _lock_open_flags() | (0 if check_only else os.O_CREAT)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except OSError as exc:
        fail(f"could not open calibration lock {path}: {exc}")
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            fail(f"calibration lock is not a regular file: {path}")
        if os.fstat(fd).st_size == 0:
            if check_only:
                fail(f"calibration lock has no ownership marker: {path}")
            os.write(fd, LOCK_MARKER)
            os.fsync(fd)
        if os.pread(fd, len(LOCK_MARKER), 0) != LOCK_MARKER:
            fail(f"calibration lock ownership marker drifted: {path}")
        if os.name == "nt":
            import msvcrt

            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            opened = os.fstat(fd)
            linked = os.stat(path, follow_symlinks=False)
        except OSError as exc:
            fail(f"calibration lock path changed while acquiring ownership: {path}: {exc}")
        if (opened.st_dev, opened.st_ino) != (linked.st_dev, linked.st_ino):
            fail(f"calibration lock path changed while acquiring ownership: {path}")
        yield path
    finally:
        if os.name == "nt":
            import msvcrt

            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


@contextmanager
def calibration_lock(codex_home: Path, *, check_only: bool) -> Iterator[Path]:
    with _lock(codex_home, check_only=check_only) as path:
        yield path


def _manifest_path(evaluator_root: Path) -> Path:
    return _safe_child(evaluator_root, MANIFEST_NAME, "calibration manifest")


def _load_manifest(evaluator_root: Path) -> dict[str, Any]:
    path = _manifest_path(evaluator_root)
    payload = _load_json(path, "calibration manifest")
    if payload.get("schema_version") != MANIFEST_SCHEMA or payload.get("managed_by") != "subagents-dispatch-calibration":
        fail(f"unsupported calibration manifest: {path}")
    if not isinstance(payload.get("profiles"), list) or not payload["profiles"]:
        fail(f"calibration manifest has no owned profiles: {path}")
    if payload.get("materialization_mode") != "profile_only":
        fail(f"unsupported calibration materialization mode: {path}")
    if payload.get("shared_config_mutations") != []:
        fail(f"profile-only manifest contains shared config ownership: {path}")
    expected_fields = {
        "schema_version", "managed_by", "evaluator_root", "codex_home",
        "campaign_path", "campaign_sha256", "campaign_raw_sha256", "candidate_sha",
        "materialization_mode", "profiles", "owned_objects", "shared_config_mutations",
        "environment_baseline",
        "host_home_identity",
        "campaign_id", "provisioning_task_id",
    }
    if set(payload) != expected_fields:
        fail(f"calibration manifest contains unknown or missing fields: {path}")
    return payload


def _existing_profile_identities(agents_dir: Path) -> dict[str, Path]:
    _directory(agents_dir, "calibration agents directory")
    identities: dict[str, Path] = {}
    for path in agents_dir.rglob("*.toml"):
        if path.is_symlink() or not path.is_file():
            fail(f"unsafe Agent profile in calibration directory: {path}")
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
            fail(f"invalid Agent profile {path}: {exc}")
        identity = data.get("name")
        if not isinstance(identity, str) or not identity.strip():
            fail(f"Agent profile has no unique name: {path}")
        identity = identity.strip()
        if identity in identities:
            fail(f"duplicate Agent identity {identity!r}: {path} and {identities[identity]}")
        identities[identity] = path
    return identities


def _verify_manifest_files(codex_home: Path, manifest: dict[str, Any]) -> None:
    agents_dir = codex_home / "agents"
    _directory(agents_dir, "calibration agents directory", missing_ok=False)
    identities = _existing_profile_identities(agents_dir)
    expected_names: set[str] = set()
    for item in manifest["profiles"]:
        if not isinstance(item, dict):
            fail("calibration manifest profile entry is not an object")
        filename = item.get("filename")
        agent_type = item.get("materialized_agent_type")
        digest = item.get("sha256")
        if not all(isinstance(value, str) and value for value in (filename, agent_type, digest)):
            fail("calibration manifest profile entry is incomplete")
        path = _safe_child(agents_dir, filename, "owned profile")
        _regular(path, "owned calibration profile", missing_ok=False)
        if _sha256(path.read_bytes()) != digest:
            fail(f"owned calibration profile drifted: {path}")
        identity = path.stat()
        if (identity.st_dev, identity.st_ino) != (item.get("device"), item.get("inode")):
            fail(f"owned calibration profile identity drifted: {path}")
        if identities.get(agent_type) != path:
            fail(f"owned calibration profile identity drifted: {path}")
        expected_names.add(agent_type)
    if len(expected_names) != len(manifest["profiles"]):
        fail("calibration manifest contains duplicate Agent identities")


def _verify_cleanup_profiles(codex_home: Path, manifest: dict[str, Any]) -> None:
    for item in manifest["profiles"]:
        path = _safe_child(codex_home / "agents", item["filename"], "owned profile")
        if not path.exists() and not path.is_symlink():
            continue
        _regular(path, "owned calibration profile", missing_ok=False)
        if _sha256(path.read_bytes()) != item["sha256"]:
            fail(f"owned calibration profile drifted: {path}")


def _manifest_payload(
    evaluator_root: Path,
    codex_home: Path,
    campaign_path: Path,
    campaign_sha256: str,
    campaign_raw_sha256: str,
    records: list[dict[str, Any]],
    environment_baseline: dict[str, Any],
    host_home_identity: dict[str, str],
    provisioning_task_id: str,
) -> dict[str, Any]:
    profiles = _manifest_profiles(records)
    return {
        "schema_version": MANIFEST_SCHEMA,
        "managed_by": "subagents-dispatch-calibration",
        "evaluator_root": str(evaluator_root),
        "codex_home": str(codex_home),
        "campaign_path": str(campaign_path),
        "campaign_id": records[0]["campaign_id"],
        "campaign_sha256": campaign_sha256,
        "campaign_raw_sha256": campaign_raw_sha256,
        "candidate_sha": records[0]["candidate_sha"],
        "materialization_mode": "profile_only",
        "profiles": profiles,
        "owned_objects": [
            {"object_type": "file", "path": str(codex_home / "agents" / item["filename"]), "sha256": item["sha256"]}
            for item in profiles
        ],
        "shared_config_mutations": [],
        "environment_baseline": environment_baseline,
        "host_home_identity": host_home_identity,
        "provisioning_task_id": provisioning_task_id,
    }


def _persist_manifest(evaluator_root: Path, manifest: dict[str, Any]) -> None:
    _atomic_write(
        _manifest_path(evaluator_root),
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )


def _manifest_profiles(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "campaign_id": record["campaign_id"],
            "campaign_sha256": record["campaign_sha256"],
            "candidate_sha": record["candidate_sha"],
            "route_id": record["route_id"],
            "filename": f"{record['materialized_agent_type']}.toml",
            "path": record["path"],
            "materialized_agent_type": record["materialized_agent_type"],
            "semantic_role": record["semantic_role"],
            "role_contract_digest": record["role_contract_digest"],
            "configured_model": record["configured_model"],
            "configured_effort": record["configured_effort"],
            "sha256": _sha256(record["profile_bytes"]),
            "staging_path": record["staging_path"],
            "device": record["device"],
            "inode": record["inode"],
            "parent_device": record["parent_device"],
            "parent_inode": record["parent_inode"],
            "status": record["status"],
        }
        for record in records
    ]


def _require_exact_manifest_profiles(
    manifest: dict[str, Any], records: list[dict[str, Any]]
) -> None:
    profiles = manifest.get("profiles")
    if not isinstance(profiles, list) or len(profiles) != len(records):
        fail("calibration manifest does not contain the exact profile set")
    immutable = {
        "campaign_id", "campaign_sha256", "candidate_sha", "route_id", "filename", "path",
        "materialized_agent_type", "semantic_role", "role_contract_digest", "configured_model",
        "configured_effort", "sha256", "staging_path",
    }
    for item, record in zip(profiles, records, strict=True):
        expected = _manifest_profiles([record])[0]
        if any(item.get(field) != expected[field] for field in immutable):
            fail("calibration manifest does not match the recomputed owned profile set")
        if item.get("status") not in PROFILE_STATUSES:
            fail("calibration profile transaction status is invalid")
        if not all(isinstance(item.get(field), int) for field in (
            "device", "inode", "parent_device", "parent_inode"
        )):
            fail("calibration profile transaction identity is invalid")
    expected_objects = [
        {"object_type": "file", "path": item["path"], "sha256": item["sha256"]}
        for item in profiles
    ]
    if manifest.get("owned_objects") != expected_objects:
        fail("calibration manifest filesystem ownership is incomplete")


def _path_inventory(root: Path) -> list[str]:
    if not root.exists():
        return []
    if root.is_symlink() or not root.is_dir():
        fail(f"unsafe inventory root: {root}")
    paths: list[str] = []
    for path in root.rglob("*"):
        if path.is_symlink():
            fail(f"refusing symlink in environment inventory: {path}")
        paths.append(str(path.relative_to(root)))
    return sorted(paths)


def _environment_baseline(codex_home: Path) -> dict[str, Any]:
    config = codex_home / "config.toml"
    if config.is_symlink():
        fail(f"refusing symlinked config.toml: {config}")
    _regular(config, "config.toml")
    config_sha256 = _sha256(config.read_bytes()) if config.exists() else None
    agents = codex_home / "agents"
    profile_hashes: dict[str, str] = {}
    if agents.exists():
        _directory(agents, "Agent directory", missing_ok=False)
        for path in sorted(agents.rglob("*.toml")):
            _regular(path, "Agent profile", missing_ok=False)
            profile_hashes[str(path.relative_to(agents))] = _sha256(path.read_bytes())
    return {
        "config_exists": config.exists(),
        "config_sha256": config_sha256,
        "marketplace_inventory": _path_inventory(codex_home / "local-marketplaces"),
        "plugin_inventory": _path_inventory(codex_home / "plugins" / "installed"),
        "plugin_cache_inventory": _path_inventory(codex_home / "plugins" / "cache"),
        "profile_hashes": profile_hashes,
    }


def _verify_environment_baseline(
    codex_home: Path, baseline: dict[str, Any], allowed_profiles: set[str]
) -> None:
    current = _environment_baseline(codex_home)
    for field in (
        "config_exists", "config_sha256", "marketplace_inventory",
        "plugin_inventory", "plugin_cache_inventory",
    ):
        if current[field] != baseline[field]:
            fail(f"profile-only environment invariant changed: {field}")
    current_profiles = current["profile_hashes"]
    original_profiles = baseline["profile_hashes"]
    unexpected = {
        name for name in current_profiles
        if name.startswith("subagents_dispatch_calibration_") and name not in allowed_profiles
    }
    if unexpected:
        fail("unexpected third calibration profile blocks readiness")
    if {name: digest for name, digest in current_profiles.items() if name not in allowed_profiles} != original_profiles:
        fail("production or unrelated Agent profile inventory changed")


def _guard_staging_file(path: Path) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except OSError:
        print("ERROR: staging path already exists", flush=True)
        raise SystemExit(1)
    identity = os.fstat(fd)
    print(f"{identity.st_dev} {identity.st_ino}", flush=True)
    if sys.stdin.readline() == "commit\n":
        os.close(fd)
        return
    os.close(fd)
    if path.exists() and not path.is_symlink():
        current = path.stat()
        if (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
            path.unlink()


def _prepare_profile_intent(
    record: dict[str, Any], evaluator_root: Path, persist: Callable[[], None]
) -> None:
    staging = Path(record["staging_path"])
    guard = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--profile-staging-guard", str(staging)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    assert guard.stdin is not None and guard.stdout is not None
    identity = guard.stdout.readline().strip()
    if not identity or identity.startswith("ERROR:"):
        guard.wait()
        fail(identity or f"could not create profile staging file: {staging}")
    record["device"], record["inode"] = map(int, identity.split())
    try:
        persist()
    except BaseException:
        guard.stdin.close()
        guard.wait()
        raise
    guard.stdin.write("commit\n")
    guard.stdin.close()
    if guard.wait() != 0:
        fail(f"could not commit profile staging intent: {staging}")


def _apply_profile(record: dict[str, Any], data: bytes, persist: Callable[[], None]) -> None:
    target = Path(record["path"])
    staging = Path(record["staging_path"])
    parent = target.parent
    parent_identity = os.stat(parent, follow_symlinks=False)
    if not stat.S_ISDIR(parent_identity.st_mode) or (
        parent_identity.st_dev, parent_identity.st_ino
    ) != (record["parent_device"], record["parent_inode"]):
        fail(f"calibration Agent directory identity drifted: {parent}")
    _regular(staging, "owned profile staging file", missing_ok=False)
    identity = staging.stat()
    if (identity.st_dev, identity.st_ino) != (record["device"], record["inode"]):
        fail(f"profile staging identity drifted: {staging}")
    flags = os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(staging, flags)
    except OSError as exc:
        fail(f"could not reopen owned profile staging file: {staging}: {exc}")
    opened = os.fstat(fd)
    if (opened.st_dev, opened.st_ino) != (record["device"], record["inode"]):
        os.close(fd)
        fail(f"profile staging identity drifted while opening: {staging}")
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    if _sha256(staging.read_bytes()) != record["sha256"]:
        fail("profile staging verification failed")
    linked_staging = os.stat(staging, follow_symlinks=False)
    if not stat.S_ISREG(linked_staging.st_mode) or (
        linked_staging.st_dev, linked_staging.st_ino
    ) != (record["device"], record["inode"]):
        fail(f"profile staging identity drifted before publication: {staging}")
    if target.exists() or target.is_symlink():
        fail(f"refusing pre-existing calibration profile: {target}")
    parent_before_link = os.stat(parent, follow_symlinks=False)
    if (
        parent_before_link.st_dev, parent_before_link.st_ino
    ) != (record["parent_device"], record["parent_inode"]):
        fail(f"calibration Agent directory identity drifted before publication: {parent}")
    os.link(staging, target, follow_symlinks=False)
    parent_after_link = os.stat(parent, follow_symlinks=False)
    if (
        parent_after_link.st_dev, parent_after_link.st_ino
    ) != (record["parent_device"], record["parent_inode"]):
        fail(f"calibration Agent directory identity drifted during publication: {parent}")
    published = os.stat(target, follow_symlinks=False)
    if not stat.S_ISREG(published.st_mode) or (
        published.st_dev, published.st_ino
    ) != (record["device"], record["inode"]):
        fail(f"published calibration profile identity is unsafe: {target}")
    _fsync_directory(target.parent)
    _crash_at(f"after_profile_{record['route_id']}_link")
    record["status"] = "APPLIED"
    persist()
    _crash_at(f"after_profile_{record['route_id']}_applied")
    staging.unlink()
    record["status"] = "COMMITTED"
    persist()


def _cleanup_profile(record: dict[str, Any], persist: Callable[[], None]) -> None:
    target = Path(record["path"])
    staging = Path(record["staging_path"])
    quarantine = target.parent / f".{record['materialized_agent_type']}.calibration-cleanup"
    parent = target.parent
    parent_identity = os.stat(parent, follow_symlinks=False)
    if not stat.S_ISDIR(parent_identity.st_mode) or (
        parent_identity.st_dev, parent_identity.st_ino
    ) != (record["parent_device"], record["parent_inode"]):
        fail(f"calibration Agent directory identity drifted: {parent}")
    if target.exists() or target.is_symlink():
        _rename_no_replace(target, quarantine)
        moved = os.stat(quarantine, follow_symlinks=False)
        if not stat.S_ISREG(moved.st_mode) or (
            moved.st_dev, moved.st_ino
        ) != (record["device"], record["inode"]):
            fail(f"owned calibration profile changed during cleanup; preserved at {quarantine}")
        if _sha256(quarantine.read_bytes()) != record["sha256"]:
            if not target.exists() and not target.is_symlink():
                _rename_no_replace(quarantine, target)
                fail(f"owned calibration profile drifted: {target}")
            fail(f"owned calibration profile drifted; preserved at {quarantine}")
        _crash_at(f"after_profile_{record['route_id']}_cleanup_unlink")
    for path in (staging, quarantine):
        if not path.exists() and not path.is_symlink():
            continue
        _regular(path, "owned calibration profile", missing_ok=False)
        identity = path.stat()
        if (identity.st_dev, identity.st_ino) != (record["device"], record["inode"]):
            fail(f"owned calibration profile identity drifted: {path}")
        if path == quarantine and _sha256(path.read_bytes()) != record["sha256"]:
            fail(f"owned calibration profile drifted: {path}")
        path.unlink()
    record["status"] = "CLEANED"
    persist()


def _campaign_context(
    evaluator_root: Path, campaign_path_arg: Path
) -> tuple[Path, dict[str, Any], dict[str, Any], str, list[dict[str, Any]]]:
    campaign_path = campaign_path_arg.expanduser()
    if not campaign_path.is_absolute():
        fail("--campaign must be an explicit absolute path")
    _regular(campaign_path, "campaign", missing_ok=False)
    campaign_path = campaign_path.resolve()
    try:
        campaign_path.relative_to(evaluator_root)
    except ValueError:
        fail("campaign must be under --evaluator-root")
    campaign, summary, campaign_raw_sha256 = _validated_campaign(campaign_path)
    if campaign["materialization_mode"] != "profile_only":
        fail("formal model_effort calibration requires materialization_mode=profile_only")
    records, _ = _profile_records(campaign, _load_policy())
    return campaign_path, campaign, summary, campaign_raw_sha256, records


def create(
    evaluator_root_arg: Path,
    codex_home_arg: Path,
    campaign_path_arg: Path,
    host_home_evidence_arg: Path,
    provisioning_task_id: str,
    *_: Path,
) -> None:
    if not provisioning_task_id.strip():
        fail("--provisioning-task-id must be concrete")
    evaluator_root, codex_home, host_home_identity = _validate_roots(
        evaluator_root_arg, codex_home_arg, host_home_evidence_arg, provisioning_task_id,
        require_active_task=True,
    )
    campaign_path, campaign, summary, campaign_raw_sha256, records = _campaign_context(
        evaluator_root, campaign_path_arg
    )
    agents_dir = codex_home / "agents"
    _directory(agents_dir, "Agent directory", missing_ok=False)
    lock_root = evaluator_root
    with calibration_lock(lock_root, check_only=False):
        agents_dir = codex_home / "agents"
        identities = _existing_profile_identities(agents_dir)
        manifest_path = _manifest_path(evaluator_root)
        if manifest_path.exists() or manifest_path.is_symlink():
            existing = _load_manifest(evaluator_root)
            if existing["host_home_identity"] != host_home_identity:
                fail("existing calibration manifest Host-home evidence drifted")
            if Path(existing.get("evaluator_root", "")).resolve() != evaluator_root or Path(existing.get("codex_home", "")).resolve() != codex_home:
                fail("existing calibration manifest owner root drifted")
            if Path(existing.get("campaign_path", "")).resolve() != campaign_path:
                fail("existing calibration manifest campaign path drifted")
            if existing.get("campaign_sha256") != summary["campaign_sha256"] or existing.get("campaign_raw_sha256") != campaign_raw_sha256:
                fail("existing calibration manifest belongs to a different campaign")
            for record, item in zip(records, existing["profiles"], strict=True):
                record.update(item)
            _require_exact_manifest_profiles(existing, records)
            if all(record["status"] == "COMMITTED" for record in existing["profiles"]):
                _verify_manifest_files(codex_home, existing)
                _verify_environment_baseline(
                    codex_home, existing["environment_baseline"],
                    {item["filename"] for item in existing["profiles"]},
                )
                print("NEW TASK REQUIRED: YES")
                return
            if all(record["status"] == "CLEANED" for record in existing["profiles"]):
                _verify_environment_baseline(codex_home, existing["environment_baseline"], set())
            else:
                fail("unresolved profile transaction; run recover")
        targets = [
            _safe_child(agents_dir, f"{record['materialized_agent_type']}.toml", "calibration profile")
            for record in records
        ]
        for record, target in zip(records, targets, strict=True):
            if record["materialized_agent_type"] in identities or target.exists() or target.is_symlink():
                fail(f"calibration Agent identity/path collides with existing profile: {target}")
        baseline = _environment_baseline(codex_home)
        agents_identity = agents_dir.stat()
        for index, (record, target) in enumerate(zip(records, targets, strict=True)):
            record.update(
                campaign_sha256=summary["campaign_sha256"],
                path=str(target),
                staging_path=str(agents_dir / f".{record['materialized_agent_type']}.calibration-staging"),
                device=-1,
                inode=-1,
                parent_device=agents_identity.st_dev,
                parent_inode=agents_identity.st_ino,
                status="PREPARED",
                sha256=_sha256(record["profile_bytes"]),
            )
        manifest = _manifest_payload(
            evaluator_root,
            codex_home,
            campaign_path,
            summary["campaign_sha256"],
            campaign_raw_sha256,
            records,
            baseline,
            host_home_identity,
            provisioning_task_id,
        )
        def persist() -> None:
            manifest["profiles"] = _manifest_profiles(records)
            manifest["owned_objects"] = [
                {"object_type": "file", "path": item["path"], "sha256": item["sha256"]}
                for item in manifest["profiles"]
            ]
            _persist_manifest(evaluator_root, manifest)

        persist()
        try:
            for index, record in enumerate(records):
                _prepare_profile_intent(record, evaluator_root, persist)
                if os.environ.get("SUBAGENTS_DISPATCH_CALIBRATION_FAIL_AT") == f"profile_{index + 1}_prepared":
                    fail(f"injected failure after profile {index + 1} preparation")
                _apply_profile(record, record["profile_bytes"], persist)
                if os.environ.get("SUBAGENTS_DISPATCH_CALIBRATION_FAIL_AT") == f"profile_{index + 1}_committed":
                    fail(f"injected failure after profile {index + 1} commit")
            if _campaign_bytes(campaign_path)[1] != campaign_raw_sha256:
                fail("campaign changed before manifest publication; refusing a TOCTOU race")
            _verify_environment_baseline(
                codex_home, baseline, {item["filename"] for item in manifest["profiles"]}
            )
        except BaseException:
            conflicts: list[str] = []
            for record in reversed(records):
                try:
                    _cleanup_profile(record, persist)
                except SystemExit as exc:
                    conflicts.append(str(exc))
            if conflicts:
                fail("profile rollback conflict: " + "; ".join(conflicts))
            raise
        print("NEW TASK REQUIRED: YES")


def check(evaluator_root_arg: Path, codex_home_arg: Path, campaign_path_arg: Path, host_home_evidence_arg: Path, provisioning_task_id: str, *_: Path) -> None:
    evaluator_root, codex_home, host_home_identity = _validate_roots(
        evaluator_root_arg, codex_home_arg, host_home_evidence_arg, provisioning_task_id
    )
    campaign_path, campaign, summary, campaign_raw_sha256, records = _campaign_context(
        evaluator_root, campaign_path_arg
    )
    with calibration_lock(evaluator_root, check_only=True):
        manifest = _load_manifest(evaluator_root)
        if manifest["provisioning_task_id"] != provisioning_task_id:
            fail("provisioning task identity drifted from preparation")
        if manifest["host_home_identity"] != host_home_identity:
            fail("active Host-home evidence drifted from preparation")
        _verify_manifest_files(codex_home, manifest)
        if Path(manifest["evaluator_root"]).resolve() != evaluator_root or Path(manifest["codex_home"]).resolve() != codex_home:
            fail("calibration manifest owner root drifted")
        if Path(manifest["campaign_path"]).resolve() != campaign_path:
            fail("calibration manifest campaign path drifted")
        for record, item in zip(records, manifest["profiles"], strict=True):
            record.update(item)
        _require_exact_manifest_profiles(manifest, records)
        if any(item["status"] != "COMMITTED" for item in manifest["profiles"]):
            fail("calibration profile transaction is not COMMITTED")
        if summary["campaign_sha256"] != manifest["campaign_sha256"] or campaign_raw_sha256 != manifest["campaign_raw_sha256"]:
            fail("campaign drifted from owned calibration manifest")
        _verify_environment_baseline(
            codex_home, manifest["environment_baseline"],
            {item["filename"] for item in manifest["profiles"]},
        )
        print("CHECK PASSED: calibration profiles and ownership are exact")


def cleanup(evaluator_root_arg: Path, codex_home_arg: Path, campaign_path_arg: Path, host_home_evidence_arg: Path, provisioning_task_id: str, *_: Path) -> None:
    evaluator_root, codex_home, _ = _validate_roots(
        evaluator_root_arg, codex_home_arg, host_home_evidence_arg, provisioning_task_id
    )
    campaign_path, _, summary, campaign_raw_sha256, records = _campaign_context(
        evaluator_root, campaign_path_arg
    )
    with calibration_lock(evaluator_root, check_only=True):
        manifest = _load_manifest(evaluator_root)
        if Path(manifest["evaluator_root"]).resolve() != evaluator_root or Path(manifest["codex_home"]).resolve() != codex_home:
            fail("calibration manifest owner root drifted")
        if Path(manifest["campaign_path"]).resolve() != campaign_path:
            fail("calibration manifest campaign path drifted")
        for record, item in zip(records, manifest["profiles"], strict=True):
            record.update(item)
        _require_exact_manifest_profiles(manifest, records)
        if summary["campaign_sha256"] != manifest["campaign_sha256"] or campaign_raw_sha256 != manifest["campaign_raw_sha256"]:
            fail("refusing cleanup after campaign drift")
        def persist() -> None:
            manifest["profiles"] = _manifest_profiles(records)
            _persist_manifest(evaluator_root, manifest)
        for record in reversed(records):
            _cleanup_profile(record, persist)
        _verify_environment_baseline(codex_home, manifest["environment_baseline"], set())
    print("CLEANUP COMPLETE: exact owned profiles removed; journal and lock retained")


def recover(evaluator_root_arg: Path, codex_home_arg: Path, campaign_path_arg: Path, host_home_evidence_arg: Path, provisioning_task_id: str, *_: Path) -> None:
    evaluator_root, codex_home, _ = _validate_roots(
        evaluator_root_arg, codex_home_arg, host_home_evidence_arg, provisioning_task_id
    )
    _, _, _, _, records = _campaign_context(evaluator_root, campaign_path_arg)
    with calibration_lock(evaluator_root, check_only=True):
        manifest = _load_manifest(evaluator_root)
        if Path(manifest["evaluator_root"]).resolve() != evaluator_root or Path(manifest["codex_home"]).resolve() != codex_home:
            fail("calibration manifest owner root drifted")
        for record, item in zip(records, manifest["profiles"], strict=True):
            record.update(item)
        _require_exact_manifest_profiles(manifest, records)
        def persist() -> None:
            manifest["profiles"] = _manifest_profiles(records)
            _persist_manifest(evaluator_root, manifest)
        for record in reversed(records):
            _cleanup_profile(record, persist)
        _verify_environment_baseline(codex_home, manifest["environment_baseline"], set())
    print("RECOVERY COMPLETE: exact profile transactions reconciled")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create/check/cleanup isolated Reader calibration profiles.")
    parser.add_argument("command", choices=("init", "create", "check", "cleanup", "recover"))
    parser.add_argument("--evaluator-root", required=True, type=Path)
    parser.add_argument("--codex-home", type=Path)
    parser.add_argument("--campaign", type=Path)
    parser.add_argument("--host-home-evidence", type=Path)
    parser.add_argument("--provisioning-task-id")
    parser.add_argument("--shared-config", type=Path)
    parser.add_argument("--marketplace-source", type=Path)
    return parser.parse_args()


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--profile-staging-guard":
        _guard_staging_file(Path(sys.argv[2]))
        return
    args = parse_args()
    if args.command == "init":
        init_evaluator(args.evaluator_root)
        return
    if args.codex_home is None or args.campaign is None or args.host_home_evidence is None or args.provisioning_task_id is None:
        fail("--codex-home, --campaign, --host-home-evidence, and --provisioning-task-id are required")
    if args.shared_config is not None or args.marketplace_source is not None:
        fail("profile_only rejects Marketplace, Plugin, and shared-config arguments")
    {
        "create": create,
        "check": check,
        "cleanup": cleanup,
        "recover": recover,
    }[args.command](
        args.evaluator_root,
        args.codex_home,
        args.campaign,
        args.host_home_evidence,
        args.provisioning_task_id,
        args.shared_config,
        args.marketplace_source,
    )


if __name__ == "__main__":
    main()
