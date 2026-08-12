#!/usr/bin/env python3
"""Materialize isolated Reader calibration Agent profiles.

This is an evaluator-side helper.  It never changes the production policy or
the five packaged profiles; it only creates an explicitly scoped, owned set
under an evaluator-owned CODEX_HOME.
"""

from __future__ import annotations

import argparse
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
from typing import Any, Iterator, NoReturn

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
MANIFEST_SCHEMA = 1
LOCK_MARKER = b"subagents-dispatch calibration lock v1\n"


def fail(message: str) -> NoReturn:
    raise SystemExit(f"ERROR: {message}")


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


def _validate_roots(evaluator_root_arg: Path, codex_home_arg: Path) -> tuple[Path, Path]:
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
    if codex_home == (Path.home() / ".codex").resolve():
        fail("refusing production ~/.codex as calibration CODEX_HOME")
    if codex_home.exists() and codex_home.is_symlink():
        fail(f"refusing symlinked calibration CODEX_HOME: {codex_home}")
    # Do not allow an existing symlink anywhere below the evaluator-owned root.
    # Resolving only the final path would otherwise make an escaped/interposed
    # component appear to be an ordinary child of the resolved root.
    try:
        lexical_relative = codex_home.relative_to(evaluator_root)
    except ValueError:
        lexical_relative = None
    if lexical_relative is not None:
        current = evaluator_root
        for component in lexical_relative.parts:
            current = current / component
            if current.is_symlink():
                fail(f"refusing symlinked calibration path component: {current}")
    codex_resolved = codex_home.resolve()
    try:
        relative = codex_resolved.relative_to(evaluator_root)
    except ValueError:
        fail("calibration CODEX_HOME must remain inside --evaluator-root")
    if not relative.parts:
        fail("calibration CODEX_HOME must be a dedicated child of --evaluator-root")
    if any(part in {"", ".", ".."} for part in relative.parts):
        fail("calibration CODEX_HOME path escapes evaluator root")
    _directory(codex_home, "calibration CODEX_HOME")
    return evaluator_root, codex_resolved


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
        records.append(
            {
                "route": route,
                "route_id": route_id,
                "semantic_role": "reader",
                "materialized_agent_type": agent_type,
                "role_contract_digest": digest,
                "configured_model": route["model"],
                "configured_effort": route["effort"],
                "profile_bytes": _render_profile(template, agent_type, route["model"], route["effort"]),
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
    finally:
        staged.unlink(missing_ok=True)


@contextmanager
def _lock(codex_home: Path, *, check_only: bool) -> Iterator[Path]:
    _directory(codex_home, "calibration CODEX_HOME", missing_ok=check_only)
    path = _safe_child(codex_home, LOCK_NAME, "calibration lock")
    if path.is_symlink():
        fail(f"refusing symlinked calibration lock: {path}")
    if check_only and not path.exists():
        fail(f"missing calibration lock: {path}")
    flags = os.O_RDWR | (0 if check_only else os.O_CREAT)
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


def _manifest_path(codex_home: Path) -> Path:
    return _safe_child(codex_home, MANIFEST_NAME, "calibration manifest")


def _load_manifest(codex_home: Path) -> dict[str, Any]:
    path = _manifest_path(codex_home)
    payload = _load_json(path, "calibration manifest")
    if payload.get("schema_version") != MANIFEST_SCHEMA or payload.get("managed_by") != "subagents-dispatch-calibration":
        fail(f"unsupported calibration manifest: {path}")
    if not isinstance(payload.get("profiles"), list) or not payload["profiles"]:
        fail(f"calibration manifest has no owned profiles: {path}")
    return payload


def _existing_profile_identities(agents_dir: Path) -> dict[str, Path]:
    _directory(agents_dir, "calibration agents directory")
    identities: dict[str, Path] = {}
    for path in agents_dir.glob("*.toml"):
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
        if identities.get(agent_type) != path:
            fail(f"owned calibration profile identity drifted: {path}")
        expected_names.add(agent_type)
    if len(expected_names) != len(manifest["profiles"]):
        fail("calibration manifest contains duplicate Agent identities")


def _manifest_payload(
    evaluator_root: Path,
    codex_home: Path,
    campaign_path: Path,
    campaign_sha256: str,
    campaign_raw_sha256: str,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": MANIFEST_SCHEMA,
        "managed_by": "subagents-dispatch-calibration",
        "evaluator_root": str(evaluator_root),
        "codex_home": str(codex_home),
        "campaign_path": str(campaign_path),
        "campaign_sha256": campaign_sha256,
        "campaign_raw_sha256": campaign_raw_sha256,
        "profiles": _manifest_profiles(records),
    }


def _manifest_profiles(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "filename": f"{record['materialized_agent_type']}.toml",
            "materialized_agent_type": record["materialized_agent_type"],
            "semantic_role": record["semantic_role"],
            "role_contract_digest": record["role_contract_digest"],
            "configured_model": record["configured_model"],
            "configured_effort": record["configured_effort"],
            "sha256": _sha256(record["profile_bytes"]),
        }
        for record in records
    ]


def _require_exact_manifest_profiles(
    manifest: dict[str, Any], records: list[dict[str, Any]]
) -> None:
    if manifest.get("profiles") != _manifest_profiles(records):
        fail("calibration manifest does not match the recomputed owned profile set")


def create(evaluator_root_arg: Path, codex_home_arg: Path, campaign_path_arg: Path) -> None:
    evaluator_root, codex_home = _validate_roots(evaluator_root_arg, codex_home_arg)
    codex_home.mkdir(parents=True, exist_ok=True)
    campaign_path = campaign_path_arg.expanduser()
    if not campaign_path.is_absolute():
        fail("--campaign must be an explicit absolute path")
    _regular(campaign_path, "campaign", missing_ok=False)
    campaign_path = campaign_path.resolve()
    try:
        campaign_path.relative_to(evaluator_root)
    except ValueError:
        fail("campaign must be under --evaluator-root")
    with calibration_lock(codex_home, check_only=False):
        campaign, summary, campaign_raw_sha256 = _validated_campaign(campaign_path)
        policy = _load_policy()
        records, _ = _profile_records(campaign, policy)
        agents_dir = codex_home / "agents"
        _directory(agents_dir, "calibration agents directory")
        agents_dir.mkdir(parents=True, exist_ok=True)
        identities = _existing_profile_identities(agents_dir)
        manifest_path = _manifest_path(codex_home)
        if manifest_path.exists() or manifest_path.is_symlink():
            existing = _load_manifest(codex_home)
            _verify_manifest_files(codex_home, existing)
            if Path(existing.get("evaluator_root", "")).resolve() != evaluator_root or Path(existing.get("codex_home", "")).resolve() != codex_home:
                fail("existing calibration manifest owner root drifted")
            if Path(existing.get("campaign_path", "")).resolve() != campaign_path:
                fail("existing calibration manifest campaign path drifted")
            if existing.get("campaign_sha256") != summary["campaign_sha256"] or existing.get("campaign_raw_sha256") != campaign_raw_sha256:
                fail("existing calibration manifest belongs to a different campaign")
            _require_exact_manifest_profiles(existing, records)
            print("RESTART_REQUIRED: calibration profiles already owned and exact")
            return
        targets = [
            _safe_child(agents_dir, f"{record['materialized_agent_type']}.toml", "calibration profile")
            for record in records
        ]
        for record, target in zip(records, targets, strict=True):
            if record["materialized_agent_type"] in identities or target.exists() or target.is_symlink():
                fail(f"calibration Agent identity/path collides with existing profile: {target}")
        campaign_sha = summary["campaign_sha256"]
        created: list[Path] = []
        try:
            for record, target in zip(records, targets, strict=True):
                _atomic_write(target, record["profile_bytes"])
                created.append(target)
            if _campaign_bytes(campaign_path)[1] != campaign_raw_sha256:
                fail("campaign changed before manifest publication; refusing a TOCTOU race")
            manifest = _manifest_payload(
                evaluator_root,
                codex_home,
                campaign_path,
                campaign_sha,
                campaign_raw_sha256,
                records,
            )
            _atomic_write(manifest_path, (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        except BaseException:
            for path in created:
                path.unlink(missing_ok=True)
            manifest_path.unlink(missing_ok=True)
            raise
        print("RESTART_REQUIRED: calibration profiles created; run only from a fresh isolated CODEX_HOME with fork_turns=none")


def check(evaluator_root_arg: Path, codex_home_arg: Path, campaign_path_arg: Path) -> None:
    evaluator_root, codex_home = _validate_roots(evaluator_root_arg, codex_home_arg)
    campaign_path = campaign_path_arg.expanduser()
    if not campaign_path.is_absolute():
        fail("--campaign must be an explicit absolute path")
    _regular(campaign_path, "campaign", missing_ok=False)
    campaign_path = campaign_path.resolve()
    try:
        campaign_path.relative_to(evaluator_root)
    except ValueError:
        fail("campaign must be under --evaluator-root")
    with calibration_lock(codex_home, check_only=True):
        manifest = _load_manifest(codex_home)
        _verify_manifest_files(codex_home, manifest)
        if Path(manifest["evaluator_root"]).resolve() != evaluator_root or Path(manifest["codex_home"]).resolve() != codex_home:
            fail("calibration manifest owner root drifted")
        if Path(manifest["campaign_path"]).resolve() != campaign_path:
            fail("calibration manifest campaign path drifted")
        campaign, summary, campaign_raw_sha256 = _validated_campaign(campaign_path)
        policy = _load_policy()
        records, _ = _profile_records(campaign, policy)
        _require_exact_manifest_profiles(manifest, records)
        if summary["campaign_sha256"] != manifest["campaign_sha256"] or campaign_raw_sha256 != manifest["campaign_raw_sha256"]:
            fail("campaign drifted from owned calibration manifest")
        print("CHECK PASSED: calibration profiles and ownership are exact")


def cleanup(evaluator_root_arg: Path, codex_home_arg: Path, campaign_path_arg: Path) -> None:
    evaluator_root, codex_home = _validate_roots(evaluator_root_arg, codex_home_arg)
    campaign_path = campaign_path_arg.expanduser()
    if not campaign_path.is_absolute():
        fail("--campaign must be an explicit absolute path")
    _regular(campaign_path, "campaign", missing_ok=False)
    campaign_path = campaign_path.resolve()
    try:
        campaign_path.relative_to(evaluator_root)
    except ValueError:
        fail("campaign must be under --evaluator-root")
    with calibration_lock(codex_home, check_only=True):
        manifest = _load_manifest(codex_home)
        _verify_manifest_files(codex_home, manifest)
        if Path(manifest["evaluator_root"]).resolve() != evaluator_root or Path(manifest["codex_home"]).resolve() != codex_home:
            fail("calibration manifest owner root drifted")
        if Path(manifest["campaign_path"]).resolve() != campaign_path:
            fail("calibration manifest campaign path drifted")
        campaign, summary, campaign_raw_sha256 = _validated_campaign(campaign_path)
        policy = _load_policy()
        records, _ = _profile_records(campaign, policy)
        _require_exact_manifest_profiles(manifest, records)
        if summary["campaign_sha256"] != manifest["campaign_sha256"] or campaign_raw_sha256 != manifest["campaign_raw_sha256"]:
            fail("refusing cleanup after campaign drift")
        for item in manifest["profiles"]:
            path = _safe_child(codex_home / "agents", item["filename"], "owned profile")
            path.unlink()
        _manifest_path(codex_home).unlink()
    print("CLEANUP COMPLETE: only owned calibration profiles and manifest were removed; lock retained")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create/check/cleanup isolated Reader calibration profiles.")
    parser.add_argument("command", choices=("init", "create", "check", "cleanup"))
    parser.add_argument("--evaluator-root", required=True, type=Path)
    parser.add_argument("--codex-home", type=Path)
    parser.add_argument("--campaign", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "init":
        init_evaluator(args.evaluator_root)
        return
    if args.codex_home is None or args.campaign is None:
        fail("--codex-home and --campaign are required for create/check/cleanup")
    {
        "create": create,
        "check": check,
        "cleanup": cleanup,
    }[args.command](args.evaluator_root, args.codex_home, args.campaign)


if __name__ == "__main__":
    main()
